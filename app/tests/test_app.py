import time

import pytest

import app.app as app_module


@pytest.fixture()
def client():
    app_module._items.clear()
    app_module.READY_DELAY = 0
    app_module._started_at = time.time() - 100
    return app_module.create_app().test_client()


def test_health_devuelve_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_ready_listo_devuelve_200(client):
    assert client.get("/ready").status_code == 200


def test_ready_en_calentamiento_devuelve_503(client):
    app_module.READY_DELAY = 60
    app_module._started_at = time.time()
    r = client.get("/ready")
    assert r.status_code == 503
    assert r.get_json()["status"] == "starting"


def test_version_expone_version_sha_y_fecha(client):
    body = client.get("/version").get_json()
    assert set(body) == {"version", "sha", "build_date"}
    assert body["version"] == app_module.APP_VERSION
    assert body["sha"] == app_module.GIT_SHA


def test_crear_item_y_listarlo(client):
    r = client.post("/api/items", json={"name": "  Paracetamol  "})
    assert r.status_code == 201
    assert r.get_json() == {"id": 1, "name": "Paracetamol"}
    lista = client.get("/api/items").get_json()
    assert lista["total"] == 1
    assert lista["items"][0]["name"] == "Paracetamol"


@pytest.mark.parametrize("payload", [{}, {"name": ""}, {"name": "   "}, {"name": 5}])
def test_crear_item_invalido_devuelve_400(client, payload):
    assert client.post("/api/items", json=payload).status_code == 400


def test_crear_item_sin_json_devuelve_400(client):
    assert client.post("/api/items", data="no es json").status_code == 400


def test_limite_de_items_devuelve_507(client, monkeypatch):
    monkeypatch.setattr(app_module, "MAX_ITEMS", 1)
    assert client.post("/api/items", json={"name": "a"}).status_code == 201
    assert client.post("/api/items", json={"name": "b"}).status_code == 507


def test_metrics_cuenta_peticiones_por_endpoint_y_codigo(client):
    client.get("/health")
    client.post("/api/items", json={})
    texto = client.get("/metrics").get_data(as_text=True)
    assert 'endpoint="/health"' in texto
    assert 'status="200"' in texto
    assert 'status="400"' in texto
    assert "http_request_duration_seconds_bucket" in texto
    assert "app_build_info" in texto
