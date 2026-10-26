import numpy as np
from scipy.fft import fft2, fftshift
from skimage.feature import graycomatrix, graycoprops
from skimage.filters.rank import entropy as rank_entropy

from backend.app.core.information import pair_information, quantize, shannon


def local_entropy(gray, window=9, stride=4, method="sliding"):
    if gray.ndim != 2 or gray.size == 0 or gray.dtype != np.uint8:
        raise ValueError("Local entropy expects nonempty 8-bit grayscale.")
    if window < 1 or stride < 1:
        raise ValueError("Window and stride must be positive.")
    h, w = gray.shape
    if method == "block":
        if int(np.ceil(h / window)) * int(np.ceil(w / window)) > 25000:
            raise ValueError(
                "Block count exceeds 25,000. Increase window size or choose preview mode."
            )
        # Non-overlapping blocks, including partial blocks at right/bottom edges.
        xs, ys = list(range(0, w, window)), list(range(0, h, window))
        result = np.array(
            [
                [
                    shannon(
                        np.bincount(gray[y : y + window, x : x + window].ravel(), minlength=256)
                    )
                    for x in xs
                ]
                for y in ys
            ]
        )
        boundary = "Partial edge blocks included; no padding. Coordinates are block origins."
    elif method == "sliding":
        full = rank_entropy(
            np.array(gray, copy=True, order="C"), np.ones((window, window), np.uint8)
        )
        xs, ys = list(range(0, w, stride)), list(range(0, h, stride))
        result = full[::stride, ::stride]
        boundary = "Window centred on each coordinate, clipped at image boundaries; no padding."
    else:
        raise ValueError("Unknown local entropy method.")
    # Bound JSON maps without changing calculated statistics.
    display_step = max(1, int(np.ceil(max(result.shape) / 160)))
    return {
        "map": result[::display_step, ::display_step].tolist(),
        "x": xs[::display_step],
        "y": ys[::display_step],
        "mean": float(result.mean()),
        "std": float(result.std()),
        "min": float(result.min()),
        "max": float(result.max()),
        "window": window,
        "stride": stride if method == "sliding" else window,
        "method": method,
        "boundary": boundary,
        "display_decimation": display_step,
        "unit": "bits / 8-bit intensity symbol within each patch",
    }


def spatial_statistics(gray, levels=16):
    q = quantize(gray, levels).astype(np.uint8)
    result = {}
    for name, dx, dy in [
        ("horizontal", 1, 0),
        ("vertical", 0, 1),
        ("diagonal", 1, 1),
        ("lag_2", 2, 0),
        ("lag_4", 4, 0),
    ]:
        if q.shape[0] <= dy or q.shape[1] <= dx:
            result[name] = None
            continue
        a = q[: q.shape[0] - dy, : q.shape[1] - dx]
        b = q[dy:, dx:]
        result[name] = pair_information(a, b, levels)
    if min(q.shape) >= 2:
        matrix = graycomatrix(
            q, [1], [0, np.pi / 4, np.pi / 2], levels=levels, symmetric=True, normed=True
        )
        glcm = {
            key: float(graycoprops(matrix, key).mean())
            for key in ["contrast", "dissimilarity", "homogeneity", "ASM", "energy"]
        }
        glcm["correlation"] = (
            float(graycoprops(matrix, "correlation").mean()) if q.std() > 0 else None
        )
    else:
        glcm = None
    return {
        "neighbours": result,
        "glcm": glcm,
        "levels": levels,
        "definition": "Directed neighbour pairs without wrapping; GLCM averages symmetric matrices at 0°, 45°, 90°, distance 1. Constant-channel correlation is undefined (null).",
        "quantization": "floor(intensity × levels / 256); 8-bit standardized input",
    }


def frequency_statistics(gray):
    # Remove the mean, no windowing: retain periodic boundary discontinuities explicitly.
    centred = gray.astype(np.float64) - gray.mean()
    power = np.abs(fftshift(fft2(centred))) ** 2
    power[gray.shape[0] // 2, gray.shape[1] // 2] = 0
    total = power.sum()
    fy = fftshift(np.fft.fftfreq(gray.shape[0]))
    fx = fftshift(np.fft.fftfreq(gray.shape[1]))
    radius = np.hypot(fy[:, None], fx[None, :])
    edges = np.linspace(0, np.sqrt(0.5), 49)
    radial = np.histogram(radius, edges, weights=power)[0]
    bands = [radius < 0.1, (radius >= 0.1) & (radius < 0.3), radius >= 0.3]
    step = max(1, int(np.ceil(max(power.shape) / 160)))
    # Zero-power distribution has no probability measure: spectral entropy is undefined.
    entropy = shannon(power.ravel()) if total > 0 else None
    return {
        "spectral_entropy": entropy,
        "maximum": float(np.log2(max(1, power.size - 1))),
        "log_power": np.log1p(power[::step, ::step]).tolist(),
        "fx": fx[::step].tolist(),
        "fy": fy[::step].tolist(),
        "radial_frequency": ((edges[:-1] + edges[1:]) / 2).tolist(),
        "radial_energy": (radial / total if total else radial).tolist(),
        "energy": dict(
            zip(
                ["low", "mid", "high"],
                [float(power[b].sum() / total) if total else 0 for b in bands],
                strict=True,
            )
        ),
        "definition": "Mean-subtracted 2D FFT, DC removed, normalized power over individual frequency bins, base-2 entropy. No taper or padding; periodic boundaries. Zero AC energy gives null entropy. Bands: <0.1, 0.1–0.3, ≥0.3 cycles/pixel.",
        "unit": "bits / frequency-bin probability distribution; distinct from pixel entropy",
        "display_decimation": step,
    }
