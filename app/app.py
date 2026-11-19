"""API piloto de MediSur.

Toda la configuracion viene de variables de entorno (nada fijo en el codigo).
"""
import os
import time
import threading

from flask import Flask, jsonify, request, g, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# Estas tres variables las inyecta el Dockerfile en la construccion (--build-arg)
APP_VERSION = os.getenv("APP_VERSION", "dev")
GIT_SHA = os.getenv("GIT_SHA", "local")
BUILD_DATE = os.getenv("BUILD_DATE", "unknown")

# Segundos que tarda en quedar "listo" (simula calentamiento). 0 = inmediato.
READY_DELAY = float(os.getenv("READY_DELAY_SECONDS", "0"))
MAX_ITEMS = int(os.getenv("MAX_ITEMS", "1000"))

REQUESTS = Counter(
    "http_requests_total",
    "Total de peticiones por endpoint y codigo de respuesta",
    ["method", "endpoint", "status", "version"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Duracion de las peticiones en segundos",
    ["endpoint"],
)
BUILD_INFO = Gauge(
    "app_build_info",
    "Informacion de la version desplegada (valor siempre 1)",
    ["version", "sha"],
)
BUILD_INFO.labels(version=APP_VERSION, sha=GIT_SHA).set(1)

_started_at = time.time()
_items = []
_lock = threading.Lock()


def create_app():
    app = Flask(__name__)

    @app.before_request
    def _start_timer():
        g.start = time.perf_counter()

    @app.after_request
    def _record(response):
        endpoint = request.url_rule.rule if request.url_rule else "unmatched"
        if endpoint != "/metrics":
            elapsed = time.perf_counter() - getattr(g, "start", time.perf_counter())
            LATENCY.labels(endpoint=endpoint).observe(elapsed)
            REQUESTS.labels(
                method=request.method,
                endpoint=endpoint,
                status=str(response.status_code),
                version=APP_VERSION,
            ).inc()
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.get("/ready")
    def ready():
        if time.time() - _started_at < READY_DELAY:
            return jsonify(status="starting"), 503
        return jsonify(status="ready"), 200

    @app.get("/version")
    def version():
        return jsonify(version=APP_VERSION, sha=GIT_SHA, build_date=BUILD_DATE), 200

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    @app.get("/api/items")
    def list_items():
        with _lock:
            return jsonify(items=list(_items), total=len(_items)), 200

    @app.post("/api/items")
    def create_item():
        data = request.get_json(silent=True)
        if not data or not isinstance(data.get("name"), str) or not data["name"].strip():
            return jsonify(error="El campo 'name' es obligatorio"), 400
        with _lock:
            if len(_items) >= MAX_ITEMS:
                return jsonify(error="Limite de registros alcanzado"), 507
            item = {"id": len(_items) + 1, "name": data["name"].strip()}
            _items.append(item)
        return jsonify(item), 201

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
