# Registro de costos (llenar durante el proyecto — alimenta la sección 11 del Word)

Estimado del enunciado (8 semanas, ~10 h/semana): ~46 USD (VM-TOOLS ~14, VM-K8S ~7, discos ~20, IP/red ~5).
Verifica precios reales en la calculadora de Azure para tu región antes de crear las VMs.

| Fecha | Crédito restante (USD) | Gasto acumulado (USD) | Nota |
|-------|------------------------|-----------------------|------|
| PENDIENTE | | | Día 1: alerta de presupuesto en 50 USD + apagado automático configurados |
| | | | |

## Checklist (marca con fecha)
- [ ] Alerta de presupuesto en 50 USD (día 1) — captura del portal
- [ ] Apagado automático diario en VM-TOOLS y VM-K8S — captura
- [ ] Discos de 64 GB (no 128) — PENDIENTE Personas 1 y 2 al crear las VMs
- [ ] Retención de Prometheus = 15 d (ya en docker-compose.yml)
- [ ] VMs detenidas desde el portal/`az vm deallocate`, no con `shutdown`
- [ ] Captura de Cost Management con consumo real (para el Word)
- [ ] Al final: `borrar-todo` (borra el grupo de recursos completo)
