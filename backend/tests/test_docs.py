def test_offline_reference_contract(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "cdn.jsdelivr" not in response.text
    assert "fastapi.tiangolo.com" not in response.text
    schema = client.get("/api/v1/openapi.json")
    assert schema.status_code == 200
    assert "/api/v1/analysis" in schema.json()["paths"]
