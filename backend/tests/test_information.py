import math

import numpy as np
import pytest

from backend.app.core.information import (
    distances,
    entropy_family,
    pair_information,
    probabilities,
    quantize,
    rgb_information,
    shannon,
)


@pytest.mark.parametrize(
    "counts, expected",
    [([1], 0), ([1, 1], 1), ([1, 1, 1, 1], 2), ([0, 1, 0, 1], 1), ([1] * 256, 8)],
)
def test_known_entropy(counts, expected):
    assert shannon(counts) == pytest.approx(expected)


@pytest.mark.parametrize("counts", [[], [0, 0], [-1, 2], [math.nan, 1], [math.inf, 1]])
def test_invalid_distribution(counts):
    with pytest.raises(ValueError):
        probabilities(counts)


@pytest.mark.parametrize("alpha", [0, 1, 1 - 1e-10, 1 + 1e-10, 2, 4, math.inf])
def test_uniform_renyi_limits(alpha):
    assert entropy_family([1] * 16, 16, alpha)["renyi"] == pytest.approx(4, abs=1e-8)


def test_nonuniform_family():
    e = entropy_family([3, 1], 256, 2)
    assert e["shannon"] == pytest.approx(0.8112781244591328)
    assert e["hartley"] == 1
    assert e["collision"] == pytest.approx(-math.log2(0.625))
    assert e["min_entropy"] == pytest.approx(-math.log2(0.75))
    assert e["normalized"] == pytest.approx(e["shannon"] / 8)
    assert e["effective_states"] == pytest.approx(2 ** e["shannon"])


def test_pair_dependence():
    a = np.array([0, 0, 1, 1])
    independent = pair_information(a, np.array([0, 1, 0, 1]), 2)
    assert independent["mutual_information"] == pytest.approx(0)
    dependent = pair_information(a, a, 2)
    assert dependent["mutual_information"] == pytest.approx(1)
    assert dependent["conditional_y_given_x"] == pytest.approx(0)
    assert pair_information(np.zeros(4, int), np.zeros(4, int), 2)["correlation"] is None


def test_sparse_rgb_exact():
    a = np.array([[[0, 0, 0], [255, 255, 255]]], dtype=np.uint8)
    r = rgb_information(a, 2)
    assert r["joint_exact"] == 1
    assert r["marginal"] == {"R": 1, "G": 1, "B": 1}
    assert r["pairs"]["RG"]["mutual_information"] == 1
    assert r["total_correlation_quantized"] == 2


def test_distances_zeros_and_symmetry():
    d = distances([1, 0], [0, 1])
    assert d["kl_p_q"] is None
    assert d["js_divergence"] == 1
    assert d["js_distance"] == 1
    assert d["hellinger"] == pytest.approx(1)
    assert d["total_variation"] == 1
    assert d["wasserstein"] == 1
    same = distances([0, 3, 1], [0, 3, 1])
    for k in ["kl_p_q", "js_distance", "hellinger", "total_variation", "wasserstein"]:
        assert same[k] == pytest.approx(0)


def test_quantization_definition():
    assert quantize(np.array([0, 63, 64, 127, 128, 255]), 4).tolist() == [0, 0, 1, 1, 2, 3]
    assert quantize(np.array([0, 32768, 65535], np.uint16), 2, 65535).tolist() == [0, 1, 1]
