from io import BytesIO

import cv2
import numpy as np
import pytest
from PIL import Image

from backend.app.core.information import shannon
from backend.app.core.spatial import frequency_statistics, local_entropy, spatial_statistics
from backend.app.schemas.models import AnalysisOptions, CompressionRequest, TransformStep
from backend.app.services.analysis import analyse
from backend.app.services.experiments import compress, transform
from backend.app.services.images import ImageStore, decode, png_bytes, synthetic


def test_local_boundary_and_blocks():
    a = np.array([[0, 255], [0, 255]], np.uint8)
    local = local_entropy(a, 3, 1)
    assert np.array(local["map"]) == pytest.approx(np.ones((2, 2)))
    assert local_entropy(a, 1, 1)["max"] == 0
    assert local_entropy(np.full((3, 4), 42, np.uint8), 3, method="block")["max"] == 0
    assert len(local_entropy(a, 3, method="block")["map"]) == 1


def test_local_matches_naive():
    a = np.random.default_rng(42).integers(0, 256, (12, 13), dtype=np.uint8)
    result = local_entropy(a, 5, 2)
    for iy, y in enumerate(result["y"]):
        for ix, x in enumerate(result["x"]):
            patch = a[max(0, y - 2) : y + 3, max(0, x - 2) : x + 3]
            assert result["map"][iy][ix] == pytest.approx(
                shannon(np.bincount(patch.ravel(), minlength=256))
            )


def test_spatial_and_spectral_constants():
    a = np.full((16, 16), 88, np.uint8)
    s = spatial_statistics(a)
    assert s["glcm"]["contrast"] == 0
    assert s["glcm"]["energy"] == 1
    assert s["glcm"]["correlation"] is None
    assert frequency_statistics(a)["spectral_entropy"] is None


@pytest.mark.parametrize("mode", ["L", "RGB", "RGBA", "P", "1", "CMYK"])
def test_unusual_modes(settings, mode):
    image = Image.new(mode, (16, 16))
    stream = BytesIO()
    image.save(stream, "TIFF" if mode == "CMYK" else "PNG")
    source = decode(stream.getvalue(), settings)
    assert source.image.size == (16, 16)
    if mode == "RGBA":
        assert "A" in source.image.getbands()


def test_native_16bit(settings):
    array = np.arange(4096, dtype=np.uint16).reshape(64, 64) * 16
    store = ImageStore(settings)
    info = store.add(png_bytes(Image.fromarray(array)), "16.png")
    result = analyse(store.get(info.id), settings)
    assert result["entropy"]["maximum"] == 16
    assert result["entropy"]["shannon"] == 12
    assert result["entropy"]["unique_symbols"] == 4096
    assert result["measurement"]["spatial_colour_diagnostics_bits"] == 8


def test_rgb_16bit(settings):
    a = np.zeros((8, 8, 3), np.uint16)
    a[::2] = [65535, 32768, 1024]
    ok, encoded = cv2.imencode(".png", a)
    assert ok
    store = ImageStore(settings)
    info = store.add(encoded.tobytes(), "rgb16.png")
    result = analyse(store.get(info.id), settings)
    assert info.native_bits == 16
    assert result["rgb"]["joint_exact"] == 1
    assert result["rgb"]["joint_maximum"] == 48


def test_shuffle_proof(settings):
    store = ImageStore(settings)
    info = store.add(synthetic("gradient", 64), "gradient.png")
    original = store.get(info.id)
    metrics, data, _ = transform(original, settings, [TransformStep(kind="shuffle", seed=42)])
    assert metrics["histogram_equal"]
    assert metrics["entropy_before"] == metrics["entropy_after"]
    before = metrics["spatial_before"]["neighbours"]["horizontal"]["mutual_information"]
    after = metrics["spatial_after"]["neighbours"]["horizontal"]["mutual_information"]
    assert before > after + 1
    assert data == transform(original, settings, [TransformStep(kind="shuffle", seed=42)])[1]


@pytest.mark.parametrize("codec,lossless", [("PNG", False), ("JPEG", False), ("WEBP", True)])
def test_real_compression(settings, codec, lossless):
    store = ImageStore(settings)
    info = store.add(synthetic("landscape", 64), "test.png")
    m, data, diff = compress(
        store.get(info.id),
        settings,
        CompressionRequest(image_id=info.id, codec=codec, lossless=lossless),
    )
    assert m["encoded_bytes"] == len(data)
    assert diff is not None
    if codec == "PNG" or lossless:
        assert m["mse"] == 0
        assert m["pixel_equal"]
        assert m["psnr"] is None
    else:
        assert m["mse"] > 0
        assert m["ssim"] is not None


@pytest.mark.parametrize(
    "kind,value",
    [
        ("grayscale", 1),
        ("blur", 2),
        ("sharpen", 2),
        ("noise", 8),
        ("denoise", 1),
        ("brightness", 1.2),
        ("contrast", 1.2),
        ("saturation", 0.5),
        ("gamma", 1.5),
        ("equalize", 1),
        ("quantize", 8),
        ("rotate", 90),
        ("flip", 0),
        ("hsv", 1),
        ("lab", 1),
    ],
)
def test_transforms(settings, kind, value):
    store = ImageStore(settings)
    info = store.add(synthetic("landscape", 32), "x.png")
    result, data, _ = transform(
        store.get(info.id), settings, [TransformStep(kind=kind, value=value)]
    )
    assert data
    assert result["entropy_after"] >= 0


def test_region_and_preview_explicit(settings):
    store = ImageStore(settings)
    info = store.add(synthetic("gradient", 256), "x.png")
    result = analyse(store.get(info.id), settings, AnalysisOptions(mode="preview", preview_size=64))
    assert result["measurement"]["width"] == 64
    assert result["measurement"]["mode"] == "preview"
    with pytest.raises(ValueError):
        analyse(
            store.get(info.id),
            settings,
            AnalysisOptions(region={"x": 250, "y": 0, "width": 20, "height": 20}),
        )


def test_frame_selection(settings):
    stream = BytesIO()
    Image.new("RGB", (16, 16), "red").save(
        stream, "GIF", save_all=True, append_images=[Image.new("RGB", (16, 16), "blue")]
    )
    first = decode(stream.getvalue(), settings, 0)
    second = decode(stream.getvalue(), settings, 1)
    assert first.frames == 2
    assert first.image.getpixel((0, 0)) != second.image.getpixel((0, 0))
