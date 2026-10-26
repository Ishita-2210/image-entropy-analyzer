import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.services.images import png_bytes


@pytest.fixture
def settings(tmp_path):
    return Settings(history=True, history_path=tmp_path / "history.sqlite3", max_pixels=1_000_000)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def image_bytes():
    return png_bytes(Image.fromarray(np.tile(np.arange(64, dtype=np.uint8), (64, 1))))


@pytest.fixture
def uploaded(client, image_bytes):
    response = client.post("/api/v1/images", files={"file": ("ramp.png", image_bytes, "image/png")})
    assert response.status_code == 201, response.text
    return response.json()
