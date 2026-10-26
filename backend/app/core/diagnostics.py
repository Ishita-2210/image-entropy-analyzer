import cv2
import numpy as np


def diagnostics(gray):
    a = gray.astype(np.float64)
    laplacian = cv2.Laplacian(a, cv2.CV_64F)
    gx, gy = cv2.Sobel(a, cv2.CV_64F, 1, 0), cv2.Sobel(a, cv2.CV_64F, 0, 1)
    gradient = np.hypot(gx, gy)
    counts, edges = np.histogram(gradient, 48, range=(0, max(1, float(gradient.max()))))
    noise = None
    if min(gray.shape) >= 2:
        h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
        detail = (a[:h:2, :w:2] - a[1:h:2, :w:2] - a[:h:2, 1:w:2] + a[1:h:2, 1:w:2]) / 2
        noise = float(np.median(np.abs(detail - np.median(detail))) / 0.6744897501960817)
    return {
        "mean": float(a.mean()),
        "std": float(a.std()),
        "min": int(a.min()),
        "max": int(a.max()),
        "dynamic_range": int(a.max() - a.min()),
        "underexposed_ratio": float((a <= 5).mean()),
        "overexposed_ratio": float((a >= 250).mean()),
        "black_clipped_ratio": float((a == 0).mean()),
        "white_clipped_ratio": float((a == 255).mean()),
        "rms_contrast": float(a.std() / 255),
        "laplacian_variance": float(laplacian.var()),
        "edge_density": float((cv2.Canny(gray, 100, 200) > 0).mean()),
        "noise_sigma": noise,
        "gradient_histogram": {
            "counts": counts.tolist(),
            "centres": ((edges[1:] + edges[:-1]) / 2).tolist(),
        },
        "definitions": {
            "brightness": "8-bit encoded luma [0,255]; not physical luminance.",
            "exposure": "Heuristic fractions ≤5 and ≥250; actual clipping counts exactly 0 and 255.",
            "rms_contrast": "Standard deviation / 255, dimensionless.",
            "laplacian_variance": "Variance of OpenCV ksize=1 Laplacian, reflect101 boundary, intensity²; content-dependent sharpness proxy.",
            "edge_density": "Fraction of Canny edge pixels, thresholds 100/200, dimensionless.",
            "noise_sigma": "Single-level orthonormal Haar diagonal-detail MAD / 0.67449, intensity units; textures and compression confound it. Null for images smaller than 2×2.",
        },
    }
