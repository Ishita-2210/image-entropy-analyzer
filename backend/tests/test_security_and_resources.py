import json
import subprocess
import sys
import threading
import time
from io import BytesIO

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.core.colour import colour_statistics
from backend.app.core.config import Settings
from backend.app.core.information import shannon
from backend.app.main import create_app
from backend.app.services.images import decode, png_bytes, synthetic
from backend.app.workers.jobs import Jobs


def test_request_body_size_before_multipart():
    with TestClient(create_app(Settings(max_upload_mb=1))) as client:
        response = client.post(
            "/api/v1/images",
            content=b"x" * (1024**2 + 65537),
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "upload_limit"


def test_chunked_request_size_limit():
    async def exercise():
        import httpx

        app = create_app(Settings(max_upload_mb=1))

        async def chunks():
            yield b'--X\r\nContent-Disposition: form-data; name="file"; filename="big.png"\r\nContent-Type: image/png\r\n\r\n'
            for _ in range(20):
                yield b"x" * 65536
            yield b"\r\n--X--\r\n"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/api/v1/images",
                content=chunks(),
                headers={"Content-Type": "multipart/form-data; boundary=X"},
            )
            assert response.status_code == 413

    import asyncio

    asyncio.run(exercise())


def test_host_and_origin_checks(client, image_bytes):
    assert client.get("/api/v1/health", headers={"Host": "attacker.example"}).status_code == 400
    response = client.post(
        "/api/v1/images",
        files={"file": ("x.png", image_bytes)},
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_origin"
    allowed = client.options(
        "/api/v1/images",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"},
    )
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_history_disabled_is_explicit(image_bytes):
    with TestClient(create_app(Settings())) as client:
        info = client.post("/api/v1/images", files={"file": ("x.png", image_bytes)}).json()
        assert client.get("/api/v1/history").json() == {"enabled": False, "records": []}
        response = client.post(
            "/api/v1/jobs/analysis",
            json={"image_id": info["id"], "options": {"save_history": True}},
        )
        assert response.status_code == 400
        assert "disabled" in response.json()["error"]["message"]


def test_exact_budget_requires_explicit_preview(image_bytes):
    with TestClient(create_app(Settings(max_analysis_pixels=4096))) as client:
        info = client.post(
            "/api/v1/images", files={"file": ("x.png", synthetic("gradient", 128))}
        ).json()
        result = client.post("/api/v1/analysis", json={"image_id": info["id"]})
        assert result.status_code == 400
        assert "preview" in result.json()["error"]["message"]
        # Preview size is user controlled but must also fit working resources.
        assert (
            client.post(
                "/api/v1/analysis",
                json={"image_id": info["id"], "options": {"mode": "preview", "preview_size": 64}},
            ).status_code
            == 200
        )


def test_alpha_and_colour_constants():
    image = Image.new("RGBA", (8, 8), (255, 0, 0, 0))
    c = colour_statistics(image)
    assert c["alpha"]["transparent_ratio"] == 1
    assert c["alpha"]["entropy"] == 0
    assert c["palette"][0]["hex"] == "#ff0000"
    assert c["channel_correlations"] == [[None] * 3] * 3
    assert c["linear_luminance_mean"] == pytest.approx(0.2126)


def test_large_distribution_normalization():
    assert shannon([1e307, 1e307]) == pytest.approx(1)


def test_16bit_values_survive_decode(settings):
    a = np.array([[0, 1], [32768, 65535]], np.uint16)
    source = decode(png_bytes(Image.fromarray(a)), settings)
    assert np.array_equal(source.native, a)
    assert np.asarray(source.image).tolist() == [[0, 0], [128, 255]]


def test_exif_orientation(settings):
    image = Image.new("RGB", (8, 12), "red")
    exif = Image.Exif()
    exif[274] = 6
    stream = BytesIO()
    image.save(stream, "JPEG", exif=exif)
    source = decode(stream.getvalue(), settings)
    assert source.image.size == (12, 8)
    assert source.native.shape == (8, 12, 3)


def test_cli_batch_file_export(tmp_path):
    paths = [tmp_path / "a.png", tmp_path / "b.png"]
    for path in paths:
        path.write_bytes(synthetic("constant", 16))
    output = tmp_path / "results.json"
    result = subprocess.run(
        [sys.executable, "-m", "backend.app.cli", *map(str, paths), "--output", str(output)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert [r["entropy"]["shannon"] for r in json.loads(output.read_text())] == [0, 0]
    assert result.stdout == ""


def test_queued_cancellation_discards_result():
    jobs = Jobs(Settings(workers=1, max_jobs=2))
    barrier = threading.Event()
    first = jobs.submit(lambda progress: (barrier.wait(1), {"done": True})[1])
    queued = jobs.submit(lambda progress: {"should_not_run": True})
    jobs.cancel(queued["id"])
    barrier.set()
    for _ in range(200):
        if jobs.get(first["id"])["status"] == "completed":
            break
        time.sleep(0.005)
    jobs.close()
    assert jobs.get(first["id"])["status"] == "completed"
    assert jobs.get(queued["id"], result=True)["result"] is None
    assert jobs.get(queued["id"])["status"] == "cancelled"


def test_api_job_failures_are_observable(client, uploaded):
    response = client.post(
        "/api/v1/jobs/analysis",
        json={
            "image_id": uploaded["id"],
            "options": {"region": {"x": 999, "y": 0, "width": 1, "height": 1}},
        },
    )
    assert response.status_code == 202
    job_id = response.json()["id"]
    for _ in range(200):
        result = client.get(f"/api/v1/jobs/{job_id}/results").json()
        if result["status"] == "failed":
            break
        time.sleep(0.01)
    assert result["status"] == "failed"
    assert "boundaries" in result["error"]
    assert client.get(f"/api/v1/jobs/{job_id}/export?format=csv").status_code == 409


def test_decoder_pixel_bomb_protection(settings, monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(ValueError, match="unsafe"):
        decode(synthetic("constant", 16), settings)


def test_rgb16_alpha_preserved(settings):
    a = np.zeros((4, 4, 4), np.uint16)
    a[..., 0] = 65535
    a[..., 3] = 32768
    ok, data = cv2.imencode(".png", a)
    assert ok
    source = decode(data.tobytes(), settings)
    assert source.bits == 16
    assert source.native.shape[2] == 4
    assert source.native[0, 0].tolist() == [0, 0, 65535, 32768]


def test_postscript_never_executes_external_decoder(settings, monkeypatch):
    from PIL import EpsImagePlugin

    def forbidden(*args, **kwargs):
        pytest.fail("External PostScript interpreter must never be invoked")

    monkeypatch.setattr(EpsImagePlugin, "Ghostscript", forbidden)
    data = b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 16 16\n%%EndComments\nshowpage\n%%EOF\n"
    with pytest.raises(ValueError):
        decode(data, settings)
