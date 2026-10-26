"""Discrete information theory: logarithms are base two, zero bins are excluded."""

import math

import numpy as np
from scipy.special import logsumexp
from scipy.stats import wasserstein_distance


def probabilities(counts):
    c = np.asarray(counts, dtype=np.float64)
    if c.size == 0 or not np.isfinite(c).all() or (c < 0).any() or c.sum() <= 0:
        raise ValueError("Distribution needs finite nonnegative counts and positive mass.")
    scaled = c / c.max()
    return scaled / scaled.sum()


def shannon(counts):
    p = probabilities(counts)
    p = p[p > 0]
    return float(-np.dot(p, np.log2(p)))


def entropy_family(counts, states=256, alpha=2.0, unit="bits / intensity symbol"):
    p = probabilities(counts)
    p = p[p > 0]
    if states < len(p) or states < 1 or alpha < 0 or math.isnan(alpha):
        raise ValueError("Invalid state count or Rényi order.")
    h = shannon(p)
    h0 = math.log2(len(p))
    hmin = -math.log2(float(p.max()))
    if alpha == 0:
        renyi = h0
    elif alpha == 1:
        renyi = h
    elif math.isinf(alpha):
        renyi = hmin
    elif abs(alpha - 1) < 1e-5:
        # expm1/log1p retain the limit without changing the requested order.
        delta = alpha - 1
        renyi = float(-np.log1p(np.dot(p, np.expm1(delta * np.log(p)))) / delta / np.log(2))
    else:
        renyi = float(logsumexp(alpha * np.log(p)) / (1 - alpha) / np.log(2))
    maximum = math.log2(states)
    return {
        "shannon": h,
        "hartley": h0,
        "renyi": renyi,
        "alpha": alpha,
        "collision": float(-np.log2(np.dot(p, p))),
        "min_entropy": hmin,
        "maximum": maximum,
        "normalized": h / maximum if maximum else 0,
        "effective_states": 2**h,
        "unique_symbols": len(p),
        "entropy_deficit": maximum - h,
        "unit": unit,
    }


def histogram(a, states=None):
    values, counts = np.unique(a, return_counts=True)
    return {
        "values": values.tolist(),
        "counts": counts.tolist(),
        "states": states,
        "display": "Observed symbols only; omitted symbols have zero count.",
    }


def quantize(a, levels, maximum=255):
    """Equal-width bins floor(value * L / (maximum+1)), clipped to [0,L-1]."""
    return np.minimum((a.astype(np.float64) * levels / (maximum + 1)).astype(np.int32), levels - 1)


def joint_counts(a, b, levels):
    return np.bincount(
        a.ravel().astype(np.int64) * levels + b.ravel(), minlength=levels**2
    ).reshape(levels, levels)


def pair_information(a, b, levels):
    c = joint_counts(a, b, levels)
    ha, hb, hab = shannon(c.sum(axis=1)), shannon(c.sum(axis=0)), shannon(c.ravel())
    correlation = None
    if a.std() > 0 and b.std() > 0:
        correlation = float(np.corrcoef(a.ravel(), b.ravel())[0, 1])
    return {
        "h_x": ha,
        "h_y": hb,
        "joint_entropy": hab,
        "mutual_information": max(0.0, ha + hb - hab),
        "conditional_y_given_x": max(0.0, hab - ha),
        "conditional_x_given_y": max(0.0, hab - hb),
        "correlation": correlation,
    }


def rgb_information(rgb, levels=16, bits=8):
    rgb = rgb[..., :3]
    native = [shannon(np.unique(rgb[..., i], return_counts=True)[1]) for i in range(3)]
    # Pack tuples in uint64; at most one count per observed colour, no dense RGB cube.
    factor = np.uint64(2**bits)
    packed = (rgb[..., 0].astype(np.uint64) * factor + rgb[..., 1]) * factor + rgb[..., 2]
    exact = shannon(np.unique(packed, return_counts=True)[1])
    q = quantize(rgb, levels, 2**bits - 1)
    packed_q = (q[..., 0].astype(np.int64) * levels + q[..., 1]) * levels + q[..., 2]
    joint_q = shannon(np.unique(packed_q, return_counts=True)[1])
    marginal_q = [shannon(np.bincount(q[..., i].ravel(), minlength=levels)) for i in range(3)]
    return {
        "marginal": dict(zip("RGB", native, strict=True)),
        "joint_exact": exact,
        "joint_maximum": 3 * bits,
        "joint_quantized": joint_q,
        "quantized_marginal": dict(zip("RGB", marginal_q, strict=True)),
        "pairs": {
            a + b: pair_information(q[..., i], q[..., j], levels)
            for i, j, a, b in [(0, 1, "R", "G"), (0, 2, "R", "B"), (1, 2, "G", "B")]
        },
        "total_correlation_quantized": max(0.0, sum(marginal_q) - joint_q),
        "levels": levels,
        "mode": "Exact observed tuples; pairwise statistics use labelled equal-width quantization.",
        "units": {
            "marginal": "bits / channel value",
            "joint": "bits / RGB tuple",
            "dependency": "bits",
        },
    }


def distances(p, q, ordered=True):
    p, q = probabilities(p), probabilities(q)
    if p.shape != q.shape:
        raise ValueError("Distributions need the same symbol support.")
    m = (p + q) / 2

    def kl(a, b):
        if np.any((a > 0) & (b == 0)):
            return None  # JSON-safe +infinity; explicitly labelled below.
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    js = (kl(p, m) + kl(q, m)) / 2
    return {
        "kl_p_q": kl(p, q),
        "kl_q_p": kl(q, p),
        "kl_null_means": "+infinity",
        "js_divergence": js,
        "js_distance": math.sqrt(max(0, js)),
        "hellinger": float(np.linalg.norm(np.sqrt(p) - np.sqrt(q)) / np.sqrt(2)),
        "total_variation": float(np.abs(p - q).sum() / 2),
        "wasserstein": float(wasserstein_distance(np.arange(p.size), np.arange(q.size), p, q))
        if ordered
        else None,
        "units": "KL and JS divergence: bits; JS distance: sqrt(bits); Hellinger and TV: dimensionless; Wasserstein: intensity-bin steps.",
        "symmetry": "All except directed KL are symmetric. KL may be infinite; other metrics accept zero bins. RGB tuples have no scalar ordering, so Wasserstein is unavailable.",
    }
