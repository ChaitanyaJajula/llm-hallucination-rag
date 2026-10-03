import pytest
from fastapi.testclient import TestClient

from app import config, db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "API_KEY", "test-key")
    monkeypatch.setattr("app.llm.time.sleep", lambda s: None)
    from app.main import app

    with TestClient(app) as c:
        yield c
