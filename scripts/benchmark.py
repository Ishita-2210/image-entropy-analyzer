"""Reproducible measured benchmark, prints JSON; writes no reports or assets."""

import json
import platform
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.config import Settings
from backend.app.core.information import shannon
from backend.app.core.spatial import local_entropy
from backend.app.schemas.models import AnalysisOptions
from backend.app.services.analysis import analyse
from backend.app.services.images import ImageStore, synthetic


def timed(work):
    start = time.perf_counter()
    result = work()
    return result, (time.perf_counter() - start) * 1000


def main():
    rng = np.random.default_rng(42)
    a = rng.integers(0, 256, (256, 256), dtype=np.uint8)

    def naive():
        return np.array(
            [
                [
                    shannon(
                        np.bincount(
                            a[max(0, y - 4) : y + 5, max(0, x - 4) : x + 5].ravel(), minlength=256
                        )
                    )
                    for x in range(0, 256)
                ]
                for y in range(0, 256)
            ]
        )

    reference, baseline_ms = timed(naive)
    result, optimized_ms = timed(lambda: local_entropy(a, 9, 1))
    display = result["display_decimation"]
    assert np.allclose(reference[::display, ::display], result["map"], atol=1e-12)
    assert np.isclose(reference.mean(), result["mean"], atol=1e-12)
    store = ImageStore(Settings())
    info = store.add(synthetic("noise", 512), "noise.png")
    tracemalloc.start()
    analysis, full_ms = timed(
        lambda: analyse(store.get(info.id), store.settings, AnalysisOptions())
    )
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(
        json.dumps(
            {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "seed": 42,
                "local": {
                    "shape": [256, 256],
                    "window": 9,
                    "stride": 1,
                    "naive_ms": baseline_ms,
                    "rank_ms": optimized_ms,
                    "verified_equal": True,
                },
                "full": {
                    "shape": [512, 512],
                    "elapsed_ms": full_ms,
                    "python_tracked_peak_mb": peak / 1024**2,
                    "entropy": analysis["entropy"]["shannon"],
                },
                "note": "Single-run local measurements; Python-tracked allocations exclude some native-library memory. Not performance guarantees.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
