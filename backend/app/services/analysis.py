"""The shared API/CLI engine. No web-framework dependencies or hidden sampling."""

import time
from collections.abc import Callable

import cv2
import numpy as np
from PIL import Image

from backend.app import ANALYSIS_VERSION
from backend.app.core.colour import colour_statistics
from backend.app.core.diagnostics import diagnostics
from backend.app.core.fingerprints import fingerprints
from backend.app.core.information import (
    entropy_family,
    histogram,
    quantize,
    rgb_information,
    shannon,
)
from backend.app.core.spatial import frequency_statistics, local_entropy, spatial_statistics
from backend.app.schemas.models import AnalysisOptions, AnalysisResult
from backend.app.services.images import Decoded, StoredImage, decode


def analyse(
    stored: StoredImage,
    settings,
    options: AnalysisOptions | None = None,
    progress: Callable[[float, str], None] = lambda p, s: None,
):
    started = time.perf_counter()
    options = options or AnalysisOptions()
    pixels = (
        options.region.width * options.region.height
        if options.region
        else stored.info.width * stored.info.height
    )
    if options.mode == "exact" and pixels > settings.max_analysis_pixels:
        raise ValueError(
            "Exact analysis exceeds the working pixel budget. Choose preview mode or a smaller region."
        )
    progress(0.02, "Decoding source")
    source = decode(stored.data, settings, stored.info.frame)
    image, native = source.image, source.native
    if options.region:
        r = options.region
        if r.x + r.width > image.width or r.y + r.height > image.height:
            raise ValueError("Selected region exceeds image boundaries.")
        image = image.crop((r.x, r.y, r.x + r.width, r.y + r.height))
        native = native[r.y : r.y + r.height, r.x : r.x + r.width]
    original_shape = native.shape[:2]
    if options.mode == "preview" and max(image.size) > options.preview_size:
        image = image.copy()
        image.thumbnail((options.preview_size, options.preview_size), Image.Resampling.LANCZOS)
        # Nearest-neighbour source-native subsampling preserves integer symbols for native stats.
        ys = np.linspace(0, native.shape[0] - 1, image.height).astype(int)
        xs = np.linspace(0, native.shape[1] - 1, image.width).astype(int)
        native = native[ys[:, None], xs[None, :]]
    if image.width * image.height > settings.max_analysis_pixels:
        raise ValueError("Selected preview exceeds the working pixel budget. Reduce preview size.")
    decoded = Decoded(
        image,
        native,
        source.bits,
        source.format,
        source.frames,
        source.source_mode,
        source.warnings,
    )
    gray_native = decoded.gray
    gray = np.asarray(image.convert("L"))
    bits = source.bits if native.ndim == 2 else 8
    _, counts = np.unique(gray_native, return_counts=True)
    entropy = entropy_family(counts, 2**bits, options.alpha)
    progress(0.12, "Joint information theory")
    if native.ndim == 3:
        rgb = native[..., :3]
        rgb_bits = source.bits
    else:
        rgb = np.asarray(image.convert("RGB"))
        rgb_bits = 8
    rgb_stats = rgb_information(rgb, options.levels, rgb_bits)
    rgb_stats["source"] = (
        "Source-native RGB"
        if native.ndim == 3
        else "Replicated 8-bit grayscale preview; not independent source channels"
    )
    progress(0.28, "Local entropy")
    # Explicit resource bound: no silent downsampling of expensive exact analysis.
    if gray.size * options.window > 250_000_000:
        raise ValueError(
            "Local window exceeds processing budget. Choose preview mode or a smaller window."
        )
    local = local_entropy(gray, options.window, options.stride, options.local_method)
    multiscale = []
    for scale in options.scales:
        progress(0.4, f"Multiscale window {scale}")
        if gray.size * scale > 250_000_000:
            raise ValueError("Multiscale window exceeds budget. Use preview mode.")
        values = local_entropy(gray, scale, max(options.stride, 8))
        coarse = cv2.resize(
            gray,
            (
                max(1, int(np.ceil(gray.shape[1] / scale))),
                max(1, int(np.ceil(gray.shape[0] / scale))),
            ),
            interpolation=cv2.INTER_AREA,
        )
        coarse_spatial = spatial_statistics(coarse, options.levels)
        neighbours = coarse_spatial["neighbours"]["horizontal"]
        multiscale.append(
            {
                **{k: values[k] for k in ["window", "mean", "std", "min", "max"]},
                "coarse_dimensions": [coarse.shape[1], coarse.shape[0]],
                "coarse_neighbour_mi": neighbours["mutual_information"] if neighbours else None,
                "coarse_neighbour_correlation": neighbours["correlation"] if neighbours else None,
                "coarse_definition": "Area-averaged 8-bit image at approximately 1/window resolution, quantized at the selected levels; horizontal neighbour measurements.",
            }
        )
    progress(0.55, "Spatial dependence and spectrum")
    spatial = spatial_statistics(gray, options.levels)
    frequency = frequency_statistics(gray)
    progress(0.7, "Colour science and diagnostics")
    colour = colour_statistics(image, options.palette_size)
    quality = diagnostics(gray)
    quantization = [
        {
            "levels": n,
            "entropy": shannon(
                np.bincount(quantize(gray_native, n, 2**bits - 1).ravel(), minlength=n)
            ),
            "maximum": float(np.log2(n)),
        }
        for n in [2, 4, 8, 16, 32, 64, 256]
    ]
    progress(0.95, "Assembling result")
    result = AnalysisResult(
        version=ANALYSIS_VERSION,
        image=stored.info,
        configuration=options,
        measurement={
            "mode": options.mode,
            "width": image.width,
            "height": image.height,
            "source_region_shape": list(original_shape),
            "native_entropy_bits": bits,
            "native_rgb_bits": rgb_bits,
            "spatial_colour_diagnostics_bits": 8,
            "preview_resampling": "Native symbols: nearest grid subsampling; visual/spatial preview: Lanczos"
            if options.mode == "preview"
            else None,
            "native_definition": "Source integer intensities for grayscale; Pillow encoded-luma conversion for colour. Native RGB tuple entropy measured separately.",
            "quantization_definition": "Equal-width floor(value × levels / 2^bits); no histogram-adaptive binning.",
        },
        entropy=entropy,
        histogram=histogram(gray_native, 2**bits),
        quantization=quantization,
        rgb=rgb_stats,
        spatial=spatial,
        local=local,
        multiscale=multiscale,
        frequency=frequency,
        colour=colour,
        diagnostics=quality,
        fingerprint=fingerprints(image),
        elapsed_ms=(time.perf_counter() - started) * 1000,
    )
    progress(1, "Complete")
    return result.model_dump(mode="json")
