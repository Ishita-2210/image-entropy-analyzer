import numpy as np

from backend.app.core.fingerprints import fingerprints, hamming
from backend.app.core.information import distances, quantize
from backend.app.services.images import decode


def compare(items, settings, request, progress=lambda p, s: None):
    if request.distribution == "rgb" and request.metric == "wasserstein":
        raise ValueError("Wasserstein requires ordered intensities; RGB tuples are unordered.")
    distributions, hashes = [], []
    for i, item in enumerate(items):
        progress(i / len(items) * 0.5, "Computing distributions and fingerprints")
        image = decode(item.data, settings, item.info.frame).image
        a = np.asarray(image.convert("RGB"))
        if request.distribution == "rgb":
            q = quantize(a, request.levels)
            packed = (q[..., 0] * request.levels + q[..., 1]) * request.levels + q[..., 2]
            distribution = np.bincount(packed.ravel(), minlength=request.levels**3)
        else:
            a = (
                np.asarray(image.convert("L"))
                if request.distribution == "gray"
                else a[..., {"red": 0, "green": 1, "blue": 2}[request.distribution]]
            )
            distribution = np.bincount(a.ravel(), minlength=256)
        distributions.append(distribution)
        hashes.append(fingerprints(image))
    matrix = np.zeros((len(items), len(items)))
    pairs = []
    for i in range(len(items)):
        progress(0.5 + 0.5 * i / len(items), "Pairwise distribution distances")
        for j in range(i + 1, len(items)):
            d = distances(distributions[i], distributions[j], request.distribution != "rgb")
            matrix[i, j] = matrix[j, i] = d[request.metric]
            phash_distance = hamming(hashes[i]["phash"], hashes[j]["phash"])
            pairs.append(
                {
                    "left": items[i].info.id,
                    "right": items[j].info.id,
                    "left_name": items[i].info.filename,
                    "right_name": items[j].info.filename,
                    "byte_duplicate": items[i].info.sha256 == items[j].info.sha256,
                    "phash_distance": phash_distance,
                    "dhash_distance": hamming(hashes[i]["dhash"], hashes[j]["dhash"]),
                    "near_candidate": phash_distance <= request.near_threshold,
                    "distances": d,
                }
            )
    pairs.sort(key=lambda p: p["distances"][request.metric])
    # Connected components of candidate graph; transitive groups are exploratory.
    groups = [{item.info.id} for item in items]
    for pair in pairs:
        if pair["near_candidate"] or pair["byte_duplicate"]:
            matching = [g for g in groups if pair["left"] in g or pair["right"] in g]
            merged = set().union(*matching)
            groups = [g for g in groups if g not in matching] + [merged]
    return {
        "images": [x.info.model_dump() for x in items],
        "matrix": matrix.tolist(),
        "pairs": pairs,
        "groups": [sorted(g) for g in groups if len(g) > 1],
        "configuration": request.model_dump(),
        "fingerprints": hashes,
        "definition": "Full selected-frame 8-bit standardized distributions, independent of dimensions. Candidate groups use transitive pHash threshold links, not proof of identity.",
    }
