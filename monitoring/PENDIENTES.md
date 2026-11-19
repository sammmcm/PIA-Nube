# Pendientes de la Persona 3 (Jean)

## A. Bloqueados por las Personas 1 y 2 (PENDIENTE)
| # | Qué falta | De quién depende | Dónde afecta |
|---|-----------|------------------|--------------|
| 1 | IP pública de VM-K8S | Persona 1 | `prometheus/prometheus.yml` (3 targets con `IP_K8S`) |
| 2 | node_exporter corriendo en VM-K8S y puerto 9100 abierto en el NSG hacia la IP de VM-TOOLS | Persona 1 | Tablero de infraestructura (VM-K8S), alerta de disco |
| 3 | kube-state-metrics expuesto (propuesto: NodePort 30808) y abierto en el NSG | Persona 1 | Tablero de aplicación, alertas PodEnCicloDeReinicio y ServicioDegradado |
| 4 | App desplegada con 2 réplicas, namespace `medisur`, Deployment `medisur-api`, NodePort 30080 abierto | Personas 1 y 2 | Panel de peticiones, errores, latencia y versión; las alertas filtran por esos nombres |
| 5 | Confirmar que la app expone `http_requests_total`, `http_request_duration_seconds_bucket` y `app_build_info` | Persona 2 | Consultas de los tableros (si los nombres cambian, ajustar `tools/gen_dashboards.py`) |
| 6 | Jenkins en :8080 y SonarQube en :9000 en VM-TOOLS | Persona 2 | Paneles "Jenkins/SonarQube arriba" (blackbox) |
| 7 | Nombres reales: grupo de recursos y VMs de Azure | Personas 1 y 2 | `costos/control_costos.sh` (variables RG y VMS), documento |
| 8 | Discos de 64 GB y apagado automático al crear las VMs | Personas 1 y 2 | Sección 11 del Word |
| 9 | Decidir si se raspa cAdvisor/kubelet para CPU/memoria REAL por pod | Persona 1 | Hoy los paneles solo muestran solicitado vs límite |
| 10 | Secciones 6 (pipeline/Jenkinsfile), 10 (sus decisiones), inventario/CMDB de sus herramientas, sus filas de IA | Personas 1 y 2 | Word |
| 11 | Capturas del pipeline (rojo y verde), imagen en el registro, pods corriendo | Personas 1 y 2 | Sección 9 |
| 12 | Paso 9 de la demo: borrar un pod con tu tablero proyectado | Persona 1 (kubectl) + tú | Presentación y video |

## B. Solo tuyos (se hacen cuando existan las VMs)
1. Crear en VM-TOOLS: `cp .env.example .env` (poner contraseña), crear `alertmanager/secrets/discord_webhook` con la URL del webhook de Discord (una sola línea), luego `docker compose up -d`.
2. Instalar node_exporter en VM-TOOLS (`sudo apt-get install -y prometheus-node-exporter`).
3. Abrir en el NSG de VM-TOOLS: 3000 (Grafana) y 9090 (Prometheus), preferentemente solo a tu IP.
4. Sustituir `IP_K8S` en `prometheus.yml` y recargar: `curl -X POST localhost:9090/-/reload`.
5. Verificar en Prometheus → Status → Targets que todo esté UP; si algo no, es el dato que te falta de A.
6. Verificar los tableros con datos reales y generar tráfico para la app: `for i in $(seq 200); do curl -s http://IP_K8S:30080/api/items >/dev/null; done`.
7. Probar las 3 alertas: llenar disco no (riesgoso); mejor bajar temporalmente el umbral a 1 % en la regla, o escalar réplicas a 0 y esperar 5 min. Captura de Discord.
8. Costos: alerta de presupuesto de 50 USD y apagado automático el primer día; llenar `costos/registro_costos.md` cada semana.
9. Completar el Word: nombres, fecha, profesor, capturas, párrafo de IA en tus palabras, conclusiones.
10. Ensayar la presentación dos veces y grabar el video de respaldo (10–15 min).

## C. Sin validar todavía
- Los YAML y JSON tienen sintaxis válida, pero **no pude ejecutar Prometheus, Grafana ni Alertmanager** en mi entorno (no hay Docker daemon). Las consultas PromQL y los tableros se prueban por primera vez en VM-TOOLS.
- `discord_configs` de Alertmanager requiere v0.25 o superior (el compose usa 0.27.0).
- Si Azure for Students no permite crear presupuestos por CLI, hazlo desde el portal.
