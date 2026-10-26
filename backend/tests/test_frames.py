from io import BytesIO

from PIL import Image


def test_selected_frame_api(client):
    stream = BytesIO()
    Image.new("RGB", (16, 16), "red").save(
        stream, "GIF", save_all=True, append_images=[Image.new("RGB", (16, 16), "blue")]
    )
    info = client.post("/api/v1/images", files={"file": ("frames.gif", stream.getvalue())}).json()
    assert info["frames"] == 2
    second = client.post(f"/api/v1/images/{info['id']}/frame?index=1").json()
    assert second["frame"] == 1
    sample = client.get(f"/api/v1/images/{second['id']}/pixel?x=0&y=0").json()
    assert sample["rgb8_preview"] == [0, 0, 255]
    assert client.post(f"/api/v1/images/{info['id']}/frame?index=2").status_code == 400
