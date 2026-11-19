"""Genera los 2 tableros de Grafana (JSON) para provisioning.
Uso: python3 tools/gen_dashboards.py
"""
import json
import os

DS = {"type": "prometheus", "uid": "prometheus"}
OUT = os.path.join(os.path.dirname(__file__), "..", "grafana", "dashboards")

_next_id = [0]


def _id():
    _next_id[0] += 1
    return _next_id[0]


def panel(title, exprs, x, y, w=8, h=8, kind="timeseries", unit=None, legend=None,
          mn=None, mx=None, thresholds=None, desc=None):
    """exprs: lista de (expr, leyenda)."""
    defaults = {"custom": {}}
    if unit:
        defaults["unit"] = unit
    if mn is not None:
        defaults["min"] = mn
    if mx is not None:
        defaults["max"] = mx
    if thresholds:
        defaults["thresholds"] = {"mode": "absolute", "steps": thresholds}
    p = {
        "id": _id(),
        "type": kind,
        "title": title,
        "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "targets": [
            {"datasource": DS, "expr": e, "legendFormat": l, "refId": chr(65 + i)}
            for i, (e, l) in enumerate(exprs)
        ],
        "options": {},
    }
    if desc:
        p["description"] = desc
    if kind == "stat":
        p["options"] = {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "background"}
    return p


def dashboard(uid, title, panels):
    return {
        "uid": uid,
        "title": title,
        "tags": ["medisur"],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "refresh": "10s",
        "time": {"from": "now-30m", "to": "now"},
        "panels": panels,
        "templating": {"list": []},
        "annotations": {"list": []},
    }


GREEN_RED = [{"color": "red", "value": None}, {"color": "green", "value": 1}]
PCT = [{"color": "green", "value": None}, {"color": "orange", "value": 70}, {"color": "red", "value": 80}]

# ------------------------------------------------------------------ Infraestructura
CPU = '100 - (avg by (vm) (rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)'
MEM_AVAIL = 'node_memory_MemAvailable_bytes'
MEM_PCT = '(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100'
DISK = ('(1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} '
        '/ node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}) * 100')
NET_RX = 'sum by (vm) (rate(node_network_receive_bytes_total{device!~"lo|docker.*|veth.*|br-.*|cni.*|flannel.*"}[2m]))'
NET_TX = 'sum by (vm) (rate(node_network_transmit_bytes_total{device!~"lo|docker.*|veth.*|br-.*|cni.*|flannel.*"}[2m]))'
UPTIME = 'time() - node_boot_time_seconds'

infra = [
    panel("CPU por VM (%)", [(CPU, "{{vm}}")], 0, 0, 8, 8, unit="percent", mn=0, mx=100, thresholds=PCT),
    panel("Memoria usada por VM (%)", [(MEM_PCT, "{{vm}}")], 8, 0, 8, 8, unit="percent", mn=0, mx=100, thresholds=PCT),
    panel("Disco raíz usado por VM (%)", [(DISK, "{{vm}}")], 16, 0, 8, 8, unit="percent", mn=0, mx=100, thresholds=PCT,
          desc="La alerta DiscoPorLlenarse se activa arriba de 80 %."),
    panel("Memoria disponible (bytes)", [(MEM_AVAIL, "{{vm}}")], 0, 8, 8, 8, unit="bytes"),
    panel("Red recibida (bytes/s)", [(NET_RX, "{{vm}} rx")], 8, 8, 8, 8, unit="Bps"),
    panel("Red enviada (bytes/s)", [(NET_TX, "{{vm}} tx")], 16, 8, 8, 8, unit="Bps"),
    panel("Tiempo encendido", [(UPTIME, "{{vm}}")], 0, 16, 8, 5, kind="stat", unit="s"),
    panel("Jenkins arriba", [('probe_success{instance=~".*:8080.*"}', "Jenkins")], 8, 16, 5, 5, kind="stat",
          thresholds=GREEN_RED),
    panel("SonarQube arriba", [('probe_success{instance=~".*:9000.*"}', "SonarQube")], 13, 16, 5, 5, kind="stat",
          thresholds=GREEN_RED),
    panel("Grafana arriba", [('probe_success{instance=~".*grafana.*"}', "Grafana")], 18, 16, 3, 5, kind="stat",
          thresholds=GREEN_RED),
    panel("Prometheus arriba", [('up{job="prometheus"}', "Prometheus")], 21, 16, 3, 5, kind="stat",
          thresholds=GREEN_RED),
    panel("Targets en línea (up)", [("up", "{{job}} {{instance}}")], 0, 21, 24, 6,
          desc="Si un target cae a 0 se pierde visibilidad de esa VM o de la app."),
]

# ------------------------------------------------------------------ Aplicación
DEP = 'namespace="medisur",deployment="medisur-api"'
app = [
    panel("Réplicas listas", [(f"kube_deployment_status_replicas_ready{{{DEP}}}", "listas")], 0, 0, 4, 5,
          kind="stat", thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 1}, {"color": "green", "value": 2}]),
    panel("Réplicas deseadas", [(f"kube_deployment_spec_replicas{{{DEP}}}", "deseadas")], 4, 0, 4, 5, kind="stat"),
    panel("Reinicios de contenedor (últimos 10 min)",
          [('sum(increase(kube_pod_container_status_restarts_total{namespace="medisur"}[10m]))', "reinicios")],
          8, 0, 5, 5, kind="stat",
          thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 1}, {"color": "red", "value": 4}]),
    panel("Versión desplegada", [("app_build_info", "{{version}} ({{sha}})")], 13, 0, 11, 5, kind="stat",
          desc="Etiqueta de la métrica app_build_info: permite correlacionar un pico de error con un despliegue."),
    panel("Réplicas listas vs deseadas (en el tiempo)",
          [(f"kube_deployment_status_replicas_ready{{{DEP}}}", "listas"),
           (f"kube_deployment_spec_replicas{{{DEP}}}", "deseadas")], 0, 5, 12, 8, mn=0,
          desc="Demo: al borrar un pod, 'listas' baja y vuelve a 2 sin intervención."),
    panel("Reinicios acumulados por pod",
          [('kube_pod_container_status_restarts_total{namespace="medisur"}', "{{pod}}")], 12, 5, 12, 8, mn=0),
    panel("Peticiones por segundo (por endpoint)",
          [('sum by (endpoint) (rate(http_requests_total{endpoint!="unmatched"}[1m]))', "{{endpoint}}")],
          0, 13, 8, 8, unit="reqps"),
    panel("Tasa de error 5xx (%)",
          [('100 * sum(rate(http_requests_total{status=~"5.."}[2m])) / clamp_min(sum(rate(http_requests_total[2m])), 1e-9)',
            "5xx %")], 8, 13, 8, 8, unit="percent", mn=0,
          thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 1}, {"color": "red", "value": 5}]),
    panel("Latencia p95 (s)",
          [('histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[2m])))', "p95"),
           ('histogram_quantile(0.50, sum by (le) (rate(http_request_duration_seconds_bucket[2m])))', "p50")],
          16, 13, 8, 8, unit="s", mn=0),
    panel("Peticiones por versión (para correlacionar con despliegues)",
          [('sum by (version) (rate(http_requests_total[1m]))', "{{version}}")], 0, 21, 12, 8, unit="reqps"),
    panel("Memoria: solicitada vs límite por pod (kube-state-metrics)",
          [('kube_pod_container_resource_requests{namespace="medisur",resource="memory"}', "{{pod}} solicitada"),
           ('kube_pod_container_resource_limits{namespace="medisur",resource="memory"}', "{{pod}} límite")],
          12, 21, 6, 8, unit="bytes",
          desc="PENDIENTE: el uso REAL de CPU/memoria por pod requiere raspar cAdvisor (kubelet). Coordinar con Persona 1."),
    panel("CPU: solicitada vs límite por pod (kube-state-metrics)",
          [('kube_pod_container_resource_requests{namespace="medisur",resource="cpu"}', "{{pod}} solicitada"),
           ('kube_pod_container_resource_limits{namespace="medisur",resource="cpu"}', "{{pod}} límite")],
          18, 21, 6, 8,
          desc="PENDIENTE: uso real vía cAdvisor (ver panel anterior)."),
]

os.makedirs(OUT, exist_ok=True)
for fname, d in [
    ("infraestructura.json", dashboard("medisur-infra", "MediSur · Infraestructura (VM-TOOLS y VM-K8S)", infra)),
    ("aplicacion.json", dashboard("medisur-app", "MediSur · Aplicación en Kubernetes", app)),
]:
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print("OK", fname, len(d["panels"]), "paneles")
