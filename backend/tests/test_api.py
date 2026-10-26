import json
import subprocess
import sys
import time
from io import BytesIO

import pytest
from PIL import Image

from backend.app.core.config import Settings
from backend.app.services.images import ImageStore
from backend.app.workers.jobs import BusyError, Jobs


def wait_job(client, job_id):
    for _ in range(300):
        result = client.get(f"/api/v1/jobs/{job_id}/results").json()
        if result["status"] in ("completed", "failed", "cancelled"):
            return result
        time.sleep(0.01)
    pytest.fail("Job did not finish")


def test_health_and_preview(client, uploaded):
    assert client.get("/api/v1/health").json()["status"] == "ok"
    preview = client.get(f"/api/v1/images/{uploaded['id']}/preview")
    assert preview.status_code == 200
    assert preview.content.startswith(b"\x89PNG")
    pixel = client.get(f"/api/v1/images/{uploaded['id']}/pixel?x=20&y=5").json()
    assert pixel["native"] == 20
    assert client.get(f"/api/v1/images/{uploaded['id']}/pixel?x=9999&y=0").status_code == 400


@pytest.mark.parametrize(
    "data", [b"", b"not image", b"<script>alert(1)</script>", b"\x89PNG\r\n\x1a\n"]
)
def test_bad_uploads(client, data):
    r = client.post("/api/v1/images", files={"file": ("safe.png", data)})
    assert r.status_code == 400
    assert "error" in r.json()


def test_limits_and_safe_filename(client, image_bytes):
    r = client.post("/api/v1/images", files={"file": ("../../unsafe.png", image_bytes)})
    assert r.json()["filename"] == "unsafe.png"
    stream = BytesIO()
    Image.new("L", (1100, 1100)).save(stream, "PNG")
    assert (
        client.post("/api/v1/images", files={"file": ("big.png", stream.getvalue())}).status_code
        == 400
    )


def test_analysis_contract_and_history(client, uploaded):
    result = client.post(
        "/api/v1/analysis", json={"image_id": uploaded["id"], "options": {"save_history": True}}
    )
    assert result.status_code == 200, result.text
    a = result.json()
    assert a["entropy"]["shannon"] == 6
    assert a["version"] == "iea-2.0.0"
    record_id = a["history_id"]
    assert client.get("/api/v1/history").json()["records"][0]["id"] == record_id
    assert client.get(f"/api/v1/history/{record_id}").json()["source_available"]
    client.delete(f"/api/v1/images/{uploaded['id']}")
    assert not client.get(f"/api/v1/history/{record_id}").json()["source_available"]
    assert client.delete(f"/api/v1/history/{record_id}").status_code == 200
    assert client.get(f"/api/v1/history/{record_id}").status_code == 404
    assert client.delete("/api/v1/history").status_code == 200


def test_schema_validation(client, uploaded):
    for options in [
        {"window": 4},
        {"alpha": -1},
        {"levels": 1000},
        {"mode": "fake"},
        {"unknown": True},
    ]:
        r = client.post("/api/v1/analysis", json={"image_id": uploaded["id"], "options": options})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"
    assert client.get("/api/v1/images/does-not-exist").status_code == 404


def test_batch_and_exports(client, uploaded, image_bytes):
    other = client.post("/api/v1/images", files={"file": ("copy.png", image_bytes)}).json()
    job = client.post(
        "/api/v1/jobs/batch", json={"image_ids": [uploaded["id"], other["id"]]}
    ).json()
    result = wait_job(client, job["id"])
    assert result["status"] == "completed", result
    assert len(result["result"]) == 2
    assert result["result"][1]["image"]["id"] == other["id"]
    for fmt in ["json", "csv"]:
        response = client.get(f"/api/v1/jobs/{job['id']}/export?format={fmt}")
        assert response.status_code == 200
        assert uploaded["filename"] in response.text


def test_compare_different_dimensions(client, uploaded):
    other = client.post("/api/v1/demo?kind=constant", json={}).json()
    result = client.post(
        "/api/v1/compare", json={"image_ids": [uploaded["id"], other["id"]]}
    ).json()
    assert result["matrix"][0][1] > 0
    assert len(result["pairs"]) == 1
    assert (
        client.post(
            "/api/v1/compare",
            json={
                "image_ids": [uploaded["id"], other["id"]],
                "distribution": "rgb",
                "metric": "wasserstein",
            },
        ).status_code
        == 400
    )


def test_compression_and_transformation_api(client, uploaded):
    for path, params in [
        ("compression", {"codec": "PNG"}),
        ("transforms", {"steps": [{"kind": "shuffle"}]}),
    ]:
        r = client.post(f"/api/v1/{path}", json={"image_id": uploaded["id"], **params})
        assert r.status_code == 200, r.text
        assert r.json()["histogram_equal"]
        assert client.get(f"/api/v1/images/{r.json()['image']['id']}/download").status_code == 200


def test_cli(tmp_path, image_bytes):
    source = tmp_path / "ramp.png"
    source.write_bytes(image_bytes)
    result = subprocess.run(
        [sys.executable, "-m", "backend.app.cli", str(source), "--mode", "preview"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["entropy"]["shannon"] == 6
    invalid = subprocess.run(
        [sys.executable, "-m", "backend.app.cli", str(source), "--alpha", "-1"],
        capture_output=True,
        text=True,
    )
    assert invalid.returncode == 1
    assert "error" in json.loads(invalid.stderr)


def test_cancel_and_capacity():
    jobs = Jobs(Settings(workers=1, max_jobs=1))

    def slow(progress):
        for i in range(100):
            time.sleep(0.005)
            progress(i / 100, "Working")
        return {"done": True}

    job = jobs.submit(slow)
    with pytest.raises(BusyError):
        jobs.submit(slow)
    jobs.cancel(job["id"])
    jobs.close()
    assert jobs.get(job["id"])["status"] == "cancelled"


def test_eviction_and_disabled_history(image_bytes):
    store = ImageStore(Settings())
    first = store.add(image_bytes, "a.png")
    store.items[first.id].touched -= 3601
    with pytest.raises(KeyError):
        store.get(first.id)
