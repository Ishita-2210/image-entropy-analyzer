import numpy as np
from scipy.cluster.vq import kmeans2
from skimage.color import lab2rgb, rgb2hsv, rgb2lab

from backend.app.core.information import shannon


def colour_statistics(image, palette_size=6):
    rgb8 = np.asarray(image.convert("RGB"))
    flat8 = rgb8.reshape(-1, 3)
    # Palette sampling only. All distribution statistics use the complete selected input.
    rng = np.random.default_rng(42)
    indices = rng.choice(len(flat8), min(12000, len(flat8)), replace=False)
    sample_lab = rgb2lab((flat8[indices].astype(float) / 255).reshape(-1, 1, 3)).reshape(-1, 3)
    unique = np.unique(sample_lab, axis=0)
    k = min(palette_size, len(unique))
    if k == 1:
        centres, labels = unique, np.zeros(len(sample_lab), dtype=int)
    else:
        # Deterministic unique initial points avoid empty identical starting clusters.
        initial = unique[rng.choice(len(unique), k, replace=False)]
        centres, labels = kmeans2(sample_lab, initial, iter=25, minit="matrix", missing="warn")
    proportions = np.bincount(labels, minlength=k) / len(labels)
    colours = np.round(lab2rgb(centres.reshape(-1, 1, 3)).reshape(-1, 3) * 255).astype(np.uint8)
    palette = [
        {
            "hex": "#" + "".join(f"{v:02x}" for v in colour),
            "rgb": colour.tolist(),
            "lab": centre.tolist(),
            "proportion": float(fraction),
        }
        for colour, centre, fraction in zip(colours, centres, proportions, strict=True)
    ]
    palette.sort(key=lambda item: -item["proportion"])
    # Accumulate all pixels in bounded chunks. This is exact distribution analysis,
    # not a sampled approximation; only the palette above uses sampling.
    names = ["hue", "saturation", "value", "L*", "a*", "b*"]
    bounds = [(0, 1), (0, 1), (0, 1), (0, 100), (-128, 128), (-128, 128)]
    histograms = np.zeros((6, 64), np.int64)
    sums, squares = np.zeros(6), np.zeros(6)
    rgb_sum, rgb_product = np.zeros(3), np.zeros((3, 3))
    diff_sum, diff_square = np.zeros(2), np.zeros(2)
    luminance_sum = 0.0
    for start in range(0, len(flat8), 65536):
        rgb = flat8[start : start + 65536].astype(float) / 255
        pixels = rgb.reshape(-1, 1, 3)
        hsv, lab = rgb2hsv(pixels).reshape(-1, 3), rgb2lab(pixels).reshape(-1, 3)
        channels = np.concatenate([hsv, lab], axis=1)
        sums += channels.sum(axis=0)
        squares += np.einsum("ij,ij->j", channels, channels)
        for index, interval in enumerate(bounds):
            histograms[index] += np.histogram(channels[:, index], 64, range=interval)[0]
        rgb_sum += rgb.sum(axis=0)
        rgb_product += rgb.T @ rgb
        differences = (
            np.column_stack((rgb[:, 0] - rgb[:, 1], 0.5 * (rgb[:, 0] + rgb[:, 1]) - rgb[:, 2]))
            * 255
        )
        diff_sum += differences.sum(axis=0)
        diff_square += np.einsum("ij,ij->j", differences, differences)
        linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
        luminance_sum += float((linear @ np.array([0.2126, 0.7152, 0.0722])).sum())
    means = sums / len(flat8)
    deviations = np.sqrt(np.maximum(0, squares / len(flat8) - means**2))
    distributions = {}
    for index, (name, interval) in enumerate(zip(names, bounds, strict=True)):
        edges = np.linspace(*interval, 65)
        distributions[name] = {
            "counts": histograms[index].tolist(),
            "centres": ((edges[1:] + edges[:-1]) / 2).tolist(),
            "mean": float(means[index]),
            "std": float(deviations[index]),
        }
    diff_mean = diff_sum / len(flat8)
    diff_variance = np.maximum(0, diff_square / len(flat8) - diff_mean**2)
    colourfulness = np.sqrt(diff_variance.sum()) + 0.3 * np.linalg.norm(diff_mean)
    gray = np.asarray(image.convert("L"))
    mean_rgb = rgb_sum / len(flat8)
    covariance = rgb_product / len(flat8) - np.outer(mean_rgb, mean_rgb)
    variance = np.maximum(0, np.diag(covariance))
    varying = np.ptp(flat8, axis=0) > 0
    correlations = [
        [
            float(np.clip(covariance[i, j] / np.sqrt(variance[i] * variance[j]), -1, 1))
            if varying[i] and varying[j] and variance[i] > 0 and variance[j] > 0
            else None
            for j in range(3)
        ]
        for i in range(3)
    ]
    alpha = None
    if "A" in image.getbands():
        a = np.asarray(image.getchannel("A"))
        alpha = {
            "mean": float(a.mean()),
            "transparent_ratio": float((a == 0).mean()),
            "opaque_ratio": float((a == 255).mean()),
            "entropy": shannon(np.bincount(a.ravel(), minlength=256)),
        }
    return {
        "rgb_histograms": {
            c: np.bincount(rgb8[..., i].ravel(), minlength=256).tolist()
            for i, c in enumerate("RGB")
        },
        "distributions": distributions,
        "palette": palette,
        "palette_sample": len(sample_lab),
        "palette_method": "Approximate CIELAB k-means; deterministic seed 42; proportions from sampled pixels; Euclidean ΔE76.",
        "colourfulness": float(colourfulness),
        "channel_correlations": correlations,
        "gray_entropy": shannon(np.bincount(gray.ravel(), minlength=256)),
        "linear_luminance_mean": luminance_sum / len(flat8),
        "alpha": alpha,
        "assumption": "sRGB encoded RGB, D65 illuminant, 2° observer. CIELAB uses proper sRGB transfer decoding. Gray is Pillow encoded luma, distinct from linear relative luminance. Transparent pixels retain their RGB values; no background compositing.",
    }
