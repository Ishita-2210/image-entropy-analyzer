import threading

import cv2
import numpy as np
from PIL import Image

from backend.app.services.experiments import reconstruction_metrics


def test_preview_waits_for_busy_workers(client, uploaded):
    gate = client.app.state.jobs.compute
    workers = client.app.state.settings.workers
    for _ in range(workers):
        assert gate.acquire(blocking=False)

    def release_workers():
        for _ in range(workers):
            gate.release()

    release = threading.Timer(0.15, release_workers)
    release.start()
    try:
        response = client.get(f"/api/v1/images/{uploaded['id']}/preview")
        assert response.status_code == 200
        assert response.content.startswith(b"\x89PNG")
    finally:
        release.join()


def test_subunit_difference_uses_full_display_scale():
    original = Image.new("RGB", (8, 8), (0, 0, 0))
    processed = original.copy()
    processed.putpixel((3, 3), (1, 0, 0))
    metrics, difference = reconstruction_metrics(original, processed)
    assert metrics["difference_display_max"] == 1 / 3
    endpoints = cv2.applyColorMap(np.array([[0, 255]], np.uint8), cv2.COLORMAP_INFERNO)[0, :, ::-1]
    assert np.array_equal(np.asarray(difference)[3, 3], endpoints[1])
    assert np.array_equal(np.asarray(difference)[0, 0], endpoints[0])
