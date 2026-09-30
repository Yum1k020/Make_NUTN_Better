from app import create_app


def test_health_and_documentation_are_available_locally():
    client = create_app({"TESTING": True}).test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    assert "/api/dev/echo" in spec.json["paths"]
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert b"/swagger-assets/" in docs.data
    for name in ("swagger-ui.css", "swagger-ui-bundle.js", "swagger-ui-standalone-preset.js"):
        assert client.get("/swagger-assets/" + name).status_code == 200


def test_json_validation_and_unicode_roundtrip():
    client = create_app({"TESTING": True}).test_client()
    good = client.post("/api/dev/echo", json={"message": "測試資料"})
    assert good.status_code == 200
    assert good.json == {"message": "測試資料"}
    for payload in ({}, {"message": ""}, {"message": 123}, {"message": "ok", "extra": True}):
        response = client.post("/api/dev/echo", json=payload)
        assert response.status_code == 422
        assert response.json["errors"]["json"]
