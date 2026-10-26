import time
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from skimage.color import rgb2lab
from skimage.metrics import structural_similarity

from backend.app.core.diagnostics import diagnostics
from backend.app.core.information import shannon
from backend.app.core.spatial import spatial_statistics
from backend.app.services.images import capabilities, decode, png_bytes


def reconstruction_metrics(original, reconstructed):
    a, b = np.asarray(original.convert("RGB")), np.asarray(reconstructed.convert("RGB"))
    gray_a = np.asarray(original.convert("L"))
    gray_b = np.asarray(reconstructed.convert("L"))
    same_size = a.shape == b.shape
    metrics = {
        "aligned": same_size,
        "pixel_equal": bool(np.array_equal(a, b)),
        "entropy_before": shannon(np.bincount(gray_a.ravel(), minlength=256)),
        "entropy_after": shannon(np.bincount(gray_b.ravel(), minlength=256)),
        "histogram_equal": bool(
            np.array_equal(
                np.bincount(gray_a.ravel(), minlength=256),
                np.bincount(gray_b.ravel(), minlength=256),
            )
        ),
        "diagnostics_before": diagnostics(gray_a),
        "diagnostics_after": diagnostics(gray_b),
        "spatial_before": spatial_statistics(gray_a),
        "spatial_after": spatial_statistics(gray_b),
        "evaluation": "RGB8, no alpha compositing; PSNR null means +infinity when MSE=0, unavailable if dimensions differ.",
        "mae": None,
        "mse": None,
        "psnr": None,
        "ssim": None,
        "delta_e76_mean": None,
    }
    difference = None
    if same_size:
        delta = a.astype(np.float64) - b.astype(np.float64)
        mse = float(np.mean(delta**2))
        metrics.update(
            mae=float(np.abs(delta).mean()),
            mse=mse,
            psnr=float(10 * np.log10(255**2 / mse)) if mse else None,
        )
        if min(a.shape[:2]) >= 3:
            window = min(7, min(a.shape[:2]))
            window -= 1 - window % 2
            metrics["ssim"] = float(
                structural_similarity(a, b, channel_axis=2, data_range=255, win_size=window)
            )
        lab_delta = rgb2lab(a / 255) - rgb2lab(b / 255)
        metrics["delta_e76_mean"] = float(np.linalg.norm(lab_delta, axis=2).mean())
        d = np.abs(delta).mean(axis=2)
        metrics["difference_display_max"] = float(d.max())
        maximum = float(d.max())
        normalized = (
            np.round(d / maximum * 255).astype(np.uint8) if maximum else np.zeros(d.shape, np.uint8)
        )
        difference = Image.fromarray(cv2.applyColorMap(normalized, cv2.COLORMAP_INFERNO)[..., ::-1])
    return metrics, difference


def compress(stored, settings, request):
    if stored.info.width * stored.info.height > settings.max_analysis_pixels:
        raise ValueError(
            "Compression experiment exceeds the working pixel budget. Resize the source before running the experiment."
        )
    original = decode(stored.data, settings, stored.info.frame).image
    if request.codec not in capabilities()["encode_formats"]:
        raise ValueError("Requested encoder is unavailable in the installed imaging stack.")
    alpha = "A" in original.getbands()
    evaluation = original.convert("RGB") if request.codec == "JPEG" else original
    kwargs = (
        {"compress_level": request.compress_level}
        if request.codec == "PNG"
        else {"quality": request.quality}
    )
    if request.codec == "WEBP":
        kwargs["lossless"] = request.lossless
        kwargs["exact"] = True
    stream = BytesIO()
    start = time.perf_counter()
    evaluation.save(stream, request.codec, **kwargs)
    encode_ms = (time.perf_counter() - start) * 1000
    encoded = stream.getvalue()
    start = time.perf_counter()
    with Image.open(BytesIO(encoded)) as source:
        source.load()
        reconstructed = source.copy()
    decode_ms = (time.perf_counter() - start) * 1000
    metrics, difference = reconstruction_metrics(evaluation, reconstructed)
    return (
        {
            "codec": request.codec,
            "configuration": request.model_dump(),
            "source_bytes": len(stored.data),
            "encoded_bytes": len(encoded),
            "size_ratio": len(encoded) / len(stored.data),
            "encode_ms": encode_ms,
            "decode_ms": decode_ms,
            "lossless_encoding": request.codec == "PNG"
            or (request.codec == "WEBP" and request.lossless),
            "source_pixel_equal": bool(
                np.array_equal(
                    np.asarray(evaluation), np.asarray(reconstructed.convert(evaluation.mode))
                )
            ),
            "source_bytes_equal": encoded == stored.data,
            "notice": "Standardized 8-bit experiment; JPEG drops alpha without compositing."
            if alpha and request.codec == "JPEG"
            else "Standardized 8-bit experiment; source image is preserved.",
            **metrics,
        },
        encoded,
        difference,
    )


def transform(stored, settings, steps):
    if stored.info.width * stored.info.height > settings.max_analysis_pixels and steps[
        0
    ].kind not in ("resize", "crop"):
        raise ValueError("Start with resize or crop to fit the working pixel budget.")
    original = decode(stored.data, settings, stored.info.frame).image
    image = original.copy()
    for step in steps:
        value = step.value
        if (
            step.kind in ("resize", "crop")
            and step.width * step.height > settings.max_analysis_pixels
        ):
            raise ValueError("Requested dimensions exceed the pixel limit.")
        if step.kind == "grayscale":
            image = image.convert("L")
        elif step.kind == "resize":
            image = image.resize(
                (step.width, step.height), getattr(Image.Resampling, step.resampling.upper())
            )
        elif step.kind == "crop":
            if step.x + step.width > image.width or step.y + step.height > image.height:
                raise ValueError("Crop exceeds image boundaries.")
            image = image.crop((step.x, step.y, step.x + step.width, step.y + step.height))
        elif step.kind == "blur":
            image = image.filter(ImageFilter.GaussianBlur(min(value, 50)))
        elif step.kind == "sharpen":
            image = ImageEnhance.Sharpness(image).enhance(min(value, 10))
        elif step.kind in ("brightness", "contrast", "saturation"):
            enhancer = {
                "brightness": ImageEnhance.Brightness,
                "contrast": ImageEnhance.Contrast,
                "saturation": ImageEnhance.Color,
            }[step.kind]
            image = enhancer(image).enhance(min(value, 10))
        elif step.kind == "gamma":
            if value <= 0 or value > 10:
                raise ValueError("Gamma must be in (0,10].")
            rgb = np.asarray(image.convert("RGB")) / 255
            image = Image.fromarray(np.round(rgb**value * 255).astype(np.uint8))
        elif step.kind in ("noise", "shuffle"):
            a = np.asarray(image).copy()
            rng = np.random.default_rng(step.seed)
            if step.kind == "shuffle":
                flat = a.reshape((-1,) + a.shape[2:])
                a = flat[rng.permutation(len(flat))].reshape(a.shape)
            else:
                a = np.clip(
                    a.astype(float) + rng.normal(0, min(value, 100), a.shape), 0, 255
                ).astype(np.uint8)
            image = Image.fromarray(a)
        elif step.kind == "denoise":
            image = Image.fromarray(cv2.medianBlur(np.asarray(image.convert("RGB")), 5))
        elif step.kind == "equalize":
            image = ImageOps.equalize(image.convert("RGB"))
        elif step.kind == "quantize":
            levels = int(value)
            if not 2 <= levels <= 256:
                raise ValueError("Quantization levels must be 2–256.")
            a = np.asarray(image.convert("RGB")).astype(float)
            image = Image.fromarray(
                np.round(np.floor(a * levels / 256) * 255 / (levels - 1)).astype(np.uint8)
            )
        elif step.kind == "rotate":
            radians = np.deg2rad(value % 360)
            expected_w = (
                abs(image.width * np.cos(radians)) + abs(image.height * np.sin(radians)) + 2
            )
            expected_h = (
                abs(image.height * np.cos(radians)) + abs(image.width * np.sin(radians)) + 2
            )
            if expected_w * expected_h > settings.max_analysis_pixels:
                raise ValueError("Rotated image would exceed the working pixel budget.")
            image = image.rotate(value % 360, resample=Image.Resampling.BICUBIC, expand=True)
            if image.width * image.height > settings.max_pixels:
                raise ValueError("Rotated image exceeds pixel limit.")
        elif step.kind == "flip":
            image = ImageOps.flip(image) if value else ImageOps.mirror(image)
        elif step.kind in ("hsv", "lab"):
            # Diagnostic component visualization, explicitly not an sRGB photograph.
            a = np.asarray(image.convert("RGB"))
            image = Image.fromarray(
                cv2.cvtColor(a, cv2.COLOR_RGB2HSV if step.kind == "hsv" else cv2.COLOR_RGB2LAB)
            )
    metrics, difference = reconstruction_metrics(original, image)
    return (
        {
            "pipeline": [s.model_dump() for s in steps],
            **metrics,
            "notice": "8-bit processing pipeline; edits may discard alpha. HSV/Lab steps visualize encoded components as RGB. Shuffle permutes whole pixel tuples; quantization and ordinary edits are destructive. Original retained.",
        },
        png_bytes(image),
        difference,
    )
