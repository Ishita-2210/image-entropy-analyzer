"""
Image loading and preprocessing utilities.
"""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image, ImageOps


SUPPORTED_FORMATS = (
    "jpg",
    "jpeg",
    "png",
    "webp",
    "bmp",
    "tif",
    "tiff",
)


def load_image(file_bytes: bytes) -> Image.Image:
    """
    Load an image from raw bytes and correct EXIF orientation.
    """
    if not file_bytes:
        raise ValueError("No image data was provided.")

    try:
        with Image.open(BytesIO(file_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            return image.copy()

    except Exception as exc:
        raise ValueError(
            "The uploaded file is not a valid or supported image."
        ) from exc


def convert_to_grayscale(image: Image.Image) -> Image.Image:
    """
    Convert an image to 8-bit grayscale.
    """
    return image.convert("L")


def grayscale_array(image: Image.Image) -> np.ndarray:
    """
    Convert PIL image to a 2D uint8 NumPy grayscale array.
    """
    gray_image = convert_to_grayscale(image)
    return np.asarray(gray_image, dtype=np.uint8)


def rgb_channel_arrays(image: Image.Image) -> dict[str, np.ndarray]:
    """
    Extract R, G and B channels from an image.
    """
    rgb_image = image.convert("RGB")
    array = np.asarray(rgb_image, dtype=np.uint8)

    return {
        "Red": array[:, :, 0],
        "Green": array[:, :, 1],
        "Blue": array[:, :, 2],
    }


def get_image_metadata(
    image: Image.Image,
    file_bytes: bytes,
) -> dict:
    """
    Return useful image metadata.
    """
    width, height = image.size

    return {
        "format": image.format or "Unknown",
        "mode": image.mode,
        "width": width,
        "height": height,
        "pixels": width * height,
        "file_size_bytes": len(file_bytes),
    }


def format_file_size(size_bytes: int) -> str:
    """
    Convert bytes into a human-readable size.
    """
    size = float(size_bytes)

    units = ["B", "KB", "MB", "GB"]

    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} TB"