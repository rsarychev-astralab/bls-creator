from fastapi.testclient import TestClient

from app.main import DIST, app

client = TestClient(app)


def test_health_not_captured_by_spa():
    assert client.get("/health").json() == {"ok": True}


def test_index_serves_react_dist():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "BLS Creator" in resp.text
    assert "/assets/" in resp.text
    assert DIST.joinpath("index.html").is_file()


def test_logo_and_assets_from_dist():
    logo = client.get("/logo.svg")
    assert logo.status_code == 200
    assert "svg" in logo.headers.get("content-type", "")
    index = (DIST / "index.html").read_text(encoding="utf-8")
    asset = next(part for part in index.split('"') if part.startswith("/assets/"))
    resp = client.get(asset)
    assert resp.status_code == 200
