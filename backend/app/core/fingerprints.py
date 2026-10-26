import numpy as np
from PIL import Image
from scipy.fft import dctn


def fingerprints(image):
    gray = image.convert("L")
    small = np.asarray(gray.resize((9, 8), Image.Resampling.LANCZOS)).astype(float)
    dhash = small[:, 1:] > small[:, :-1]
    block = dctn(
        np.asarray(gray.resize((32, 32), Image.Resampling.LANCZOS)).astype(float), norm="ortho"
    )[:8, :8]
    threshold = np.median(block.ravel()[1:])
    phash = block > threshold
    phash[0, 0] = False

    def pack(bits):
        return f"{int(''.join('1' if b else '0' for b in bits.ravel()), 2):016x}"

    return {
        "phash": pack(phash),
        "dhash": pack(dhash),
        "definition": "64-bit DCT pHash (DC bit cleared), 64-bit horizontal dHash; Hamming distance is a candidate heuristic, never proof of equality.",
    }


def hamming(left, right):
    return (int(left, 16) ^ int(right, 16)).bit_count()
