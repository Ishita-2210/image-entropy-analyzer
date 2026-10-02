"""
Core Information Theory calculations for the Image Entropy Analyzer.
"""

from __future__ import annotations

import numpy as np

MAX_GRAY_LEVELS = 256
MAX_ENTROPY = np.log2(MAX_GRAY_LEVELS)


def validate_grayscale_image(image: np.ndarray) -> np.ndarray:
    """
    Validate and normalize a grayscale image array.

    Parameters
    ----------
    image : np.ndarray
        2D grayscale image.

    Returns
    -------
    np.ndarray
        uint8 grayscale image.
    """
    if not isinstance(image, np.ndarray):
        raise TypeError("Image must be a NumPy array.")

    if image.ndim != 2:
        raise ValueError("Expected a 2D grayscale image.")

    if image.size == 0:
        raise ValueError("Image cannot be empty.")

    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)

    return image


def calculate_histogram(image: np.ndarray) -> np.ndarray:
    """
    Calculate the frequency of each grayscale intensity (0-255).
    """
    image = validate_grayscale_image(image)

    histogram = np.bincount(
        image.ravel(),
        minlength=MAX_GRAY_LEVELS
    )

    return histogram.astype(np.int64)


def calculate_probabilities(histogram: np.ndarray) -> np.ndarray:
    """
    Convert a histogram into a probability distribution.
    """
    histogram = np.asarray(histogram, dtype=np.float64)

    total = histogram.sum()

    if total <= 0:
        raise ValueError("Histogram must contain at least one pixel.")

    return histogram / total


def calculate_shannon_entropy(probabilities: np.ndarray) -> float:
    """
    Calculate Shannon entropy in bits per pixel.

    H(X) = -sum(p(x) * log2(p(x)))
    """
    probabilities = np.asarray(probabilities, dtype=np.float64)

    valid_probabilities = probabilities[probabilities > 0]

    if valid_probabilities.size == 0:
        return 0.0

    entropy = -np.sum(
        valid_probabilities * np.log2(valid_probabilities)
    )

    return float(entropy)


def calculate_maximum_entropy(levels: int = MAX_GRAY_LEVELS) -> float:
    """
    Maximum possible entropy for a source with `levels` symbols.
    """
    if levels <= 1:
        return 0.0

    return float(np.log2(levels))


def calculate_normalized_entropy(entropy: float) -> float:
    """
    Normalize entropy to the range [0, 1].
    """
    if MAX_ENTROPY == 0:
        return 0.0

    return float(np.clip(entropy / MAX_ENTROPY, 0.0, 1.0))


def calculate_redundancy(entropy: float) -> float:
    """
    Calculate source redundancy as a percentage.

    Redundancy = (1 - H/Hmax) * 100
    """
    normalized_entropy = calculate_normalized_entropy(entropy)

    return float((1.0 - normalized_entropy) * 100.0)


def calculate_information_content(probability: float) -> float:
    """
    Calculate self-information of an event:

    I(x) = -log2(p(x))

    Returns infinity for probability 0.
    """
    if probability < 0 or probability > 1:
        raise ValueError("Probability must lie between 0 and 1.")

    if probability == 0:
        return float("inf")

    return float(-np.log2(probability))


def analyze_image(image: np.ndarray) -> dict:
    """
    Perform complete entropy analysis on a grayscale image.

    Returns
    -------
    dict
        Calculated metrics and distributions.
    """
    image = validate_grayscale_image(image)

    height, width = image.shape
    total_pixels = image.size

    histogram = calculate_histogram(image)
    probabilities = calculate_probabilities(histogram)

    entropy = calculate_shannon_entropy(probabilities)
    maximum_entropy = calculate_maximum_entropy()
    normalized_entropy = calculate_normalized_entropy(entropy)
    redundancy = calculate_redundancy(entropy)

    unique_levels = int(np.count_nonzero(histogram))

    return {
        "width": int(width),
        "height": int(height),
        "total_pixels": int(total_pixels),
        "entropy": entropy,
        "maximum_entropy": maximum_entropy,
        "normalized_entropy": normalized_entropy,
        "redundancy": redundancy,
        "unique_levels": unique_levels,
        "histogram": histogram,
        "probabilities": probabilities,
    }