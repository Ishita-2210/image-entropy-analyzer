"""Validated decoding and bounded, expiring, memory-only source storage."""

import hashlib
import re
import threading
import time
import uuid
import warnings
from collections import OrderedDict
from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError, features

from backend.app.core.config import Settings
from backend.app.schemas.models import ImageInfo


class ImageError(ValueError):
    pass


# Inline raster decoders only. In particular, EPS/PS must never invoke Ghostscript.
RASTER_FORMATS = {
    "BMP",
    "DIB",
    "GIF",
    "JPEG",
    "PNG",
    "TIFF",
    "WEBP",
    "AVIF",
    "HEIF",
    "ICO",
    "PPM",
    "PCX",
    "TGA",
    "JPEG2000",
    "QOI",
}


def safe_name(name: str) -> str:
    return re.sub(r"[^\w. -]", "_", name.replace("\\", "/").split("/")[-1])[:120] or "image"


@dataclass
class Decoded:
    image: Image.Image
    native: np.ndarray
    bits: int
    format: str
    frames: int
    source_mode: str
    warnings: list[str]

    @property
    def gray(self):
        if self.native.ndim == 2:
            return self.native
        # A standardized sRGB encoded luma proxy, explicitly 8-bit for colour sources.
        return np.asarray(self.image.convert("L"))


def decode(data: bytes, settings: Settings, frame: int = 0) -> Decoded:
    if not data or len(data) > settings.max_upload_mb * 1024**2:
        raise ImageError("Image is empty or exceeds the upload limit.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                fmt = source.format or "unknown"
                if fmt not in RASTER_FORMATS:
                    raise ImageError("This format is not enabled for safe inline raster decoding.")
                if source.width * source.height > settings.max_pixels:
                    raise ImageError("Decoded image exceeds the pixel limit.")
                frames = getattr(source, "n_frames", 1)
                if frame < 0 or frame >= min(frames, 100):
                    raise ImageError("Frame index is unavailable (first 100 frames supported).")
                source.seek(frame)
                if source.width * source.height > settings.max_pixels:
                    raise ImageError("Selected frame exceeds the decoded pixel limit.")
                source.load()
                mode = source.mode
                if fmt == "TIFF" and source.tag_v2.get(339, (1,))[0] == 2:
                    raise ImageError("Signed integer intensities are unsupported.")
                orientation = source.getexif().get(274, 1)
                bits = 1 if mode == "1" else 16 if mode.startswith("I;16") else 8
                if mode == "I":
                    bits = 16 if fmt == "PNG" else 32
                if mode == "F":
                    raise ImageError(
                        "Floating-point images require explicit calibration; unsupported."
                    )
                notes = []
                # Pillow converts RGB16 to RGB8. Detect and recover native data through OpenCV.
                native16 = None
                high_colour = (
                    fmt == "PNG" and len(data) > 25 and data[24] == 16 and data[25] in (2, 4, 6)
                ) or (
                    fmt == "TIFF"
                    and max(source.tag_v2.get(258, (8,))) > 8
                    and mode in ("RGB", "RGBA")
                )
                if high_colour:
                    if frame != 0:
                        raise ImageError("High-bit-depth colour frame selection is unavailable.")
                    native16 = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_UNCHANGED)
                    if native16 is None or native16.dtype != np.uint16 or native16.ndim != 3:
                        raise ImageError(
                            "Installed decoder cannot preserve this high-bit-depth colour image."
                        )
                    native16 = native16[..., [2, 1, 0, 3] if native16.shape[-1] == 4 else [2, 1, 0]]
                    # PNG has no automatic EXIF orientation in IMREAD_UNCHANGED.
                    operations = {
                        2: lambda a: a[:, ::-1],
                        3: lambda a: a[::-1, ::-1],
                        4: lambda a: a[::-1],
                        5: lambda a: a.swapaxes(0, 1),
                        6: lambda a: np.rot90(a, 3),
                        7: lambda a: a.swapaxes(0, 1)[::-1, ::-1],
                        8: lambda a: np.rot90(a),
                    }
                    native16 = operations.get(orientation, lambda a: a)(native16).copy()
                    bits = 16
                image = ImageOps.exif_transpose(source).copy()
                if native16 is not None:
                    native = native16
                    image = Image.fromarray((native / 257).round().astype(np.uint8))
                elif mode in ("1", "I", "L") or mode.startswith("I;16"):
                    native = np.asarray(image).copy()
                    if native.min() < 0:
                        raise ImageError("Signed integer intensities are unsupported.")
                    image = Image.fromarray(
                        np.round(native.astype(np.float64) / (2**bits - 1) * 255).astype(np.uint8)
                    )
                else:
                    alpha = "A" in image.getbands() or "transparency" in image.info
                    image = image.convert("RGBA" if alpha else "RGB")
                    native = np.asarray(image).copy()
                if bits > 8:
                    notes.append(
                        "Native integer entropy preserved; spatial, colour, diagnostics and experiments use an explicitly standardized 8-bit preview."
                    )
                if source.info.get("icc_profile"):
                    notes.append(
                        "Embedded ICC profile is not applied; colour measurements assume sRGB / D65."
                    )
                if mode == "CMYK":
                    notes.append(
                        "CMYK converted by Pillow to RGB; no calibrated CMYK profile conversion."
                    )
                image.info.clear()
                return Decoded(image, native, bits, fmt, frames, mode, notes)
    except ImageError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ImageError("Invalid, unsafe or unsupported image data.") from exc


def png_bytes(image: Image.Image, maximum: int | None = None) -> bytes:
    if maximum:
        image = image.copy()
        image.thumbnail((maximum, maximum))
    stream = BytesIO()
    image.save(stream, "PNG")
    return stream.getvalue()


@dataclass
class StoredImage:
    data: bytes
    info: ImageInfo
    touched: float


class ImageStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.items: OrderedDict[str, StoredImage] = OrderedDict()
        self.lock = threading.RLock()

    def add(self, data: bytes, name: str, frame: int = 0) -> ImageInfo:
        decoded = decode(data, self.settings, frame)
        image_id = uuid.uuid4().hex
        info = ImageInfo(
            id=image_id,
            filename=safe_name(name),
            width=decoded.image.width,
            height=decoded.image.height,
            mode=decoded.source_mode,
            format=decoded.format,
            frames=decoded.frames,
            frame=frame,
            bytes=len(data),
            native_bits=decoded.bits,
            has_alpha="A" in decoded.image.getbands(),
            sha256=hashlib.sha256(data).hexdigest(),
            warnings=decoded.warnings,
        )
        with self.lock:
            self._expire()
            while self.items and (
                sum(len(x.data) for x in self.items.values()) + len(data)
                > self.settings.store_mb * 1024**2
                or len(self.items) >= 48
            ):
                self.items.popitem(last=False)
            self.items[image_id] = StoredImage(data, info, time.monotonic())
        return info

    def _expire(self):
        cutoff = time.monotonic() - 3600
        for key in [key for key, item in self.items.items() if item.touched < cutoff]:
            del self.items[key]

    def get(self, image_id: str) -> StoredImage:
        with self.lock:
            self._expire()
            if image_id not in self.items:
                raise KeyError("Image unavailable or expired; upload it again.")
            item = self.items[image_id]
            item.touched = time.monotonic()
            self.items.move_to_end(image_id)
            return item

    def remove(self, image_id: str):
        with self.lock:
            self.items.pop(image_id, None)


def capabilities():
    Image.init()
    return {
        "decode_formats": sorted(set(Image.OPEN) & RASTER_FORMATS),
        "encode_formats": sorted(Image.SAVE),
        "webp": features.check("webp"),
        "avif": "AVIF" in Image.OPEN,
        "heif": "HEIF" in Image.OPEN,
    }


def synthetic(kind: str = "landscape", size: int = 256, seed: int = 42) -> bytes:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[:size, :size] / max(size - 1, 1)
    if kind == "noise":
        a = rng.integers(0, 256, (size, size, 3), dtype=np.uint8)
    elif kind == "constant":
        a = np.full((size, size, 3), 128, np.uint8)
    elif kind == "gradient":
        a = np.repeat(np.round(x * 255)[..., None], 3, axis=2).astype(np.uint8)
    elif kind == "checkerboard":
        a = np.repeat(
            (((x * 16).astype(int) + (y * 16).astype(int)) % 2 * 255)[..., None], 3, axis=2
        ).astype(np.uint8)
    else:
        sky = np.stack((170 - y * 80, 198 - y * 65, 209 - y * 75), axis=-1)
        far = y > 0.43 + 0.09 * np.sin(x * 10) + 0.045 * np.sin(x * 25)
        near = y > 0.67 + 0.08 * np.sin(x * 7 + 1)
        sky[far] = np.stack((97 + y * 30, 125 + y * 25, 110 + y * 20), axis=-1)[far]
        sky[near] = np.stack((49 + y * 26, 78 + y * 29, 63 + y * 23), axis=-1)[near]
        sun = (x - 0.77) ** 2 + (y - 0.22) ** 2 < 0.055**2
        sky[sun] = (239, 222, 168)
        a = np.clip(sky + rng.normal(0, 1.5, sky.shape), 0, 255).astype(np.uint8)
    return png_bytes(Image.fromarray(a))
