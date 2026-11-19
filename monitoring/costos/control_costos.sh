#!/usr/bin/env bash
# Control de costos de Azure (Persona 3). Ejecutar desde Azure Cloud Shell o con `az login`.
# Uso: RG=rg-medisur EMAIL=tu@correo.com bash control_costos.sh <accion>
#   acciones: apagado-auto | presupuesto | apagar | encender | estado | borrar-todo
set -euo pipefail

RG="${RG:-rg-medisur}"                       # nombre del grupo de recursos (confirmar con Personas 1 y 2)
VMS="${VMS:-vm-tools vm-k8s}"                # nombres reales de las VMs (PENDIENTE: confirmar)
SHUTDOWN_TIME="${SHUTDOWN_TIME:-2300}"       # hora UTC HHMM del apagado automático (2300 UTC = 17:00 CDMX)
EMAIL="${EMAIL:-}"
BUDGET_USD="${BUDGET_USD:-50}"

case "${1:-}" in
  apagado-auto)
    for vm in $VMS; do
      az vm auto-shutdown -g "$RG" -n "$vm" --time "$SHUTDOWN_TIME" ${EMAIL:+--email "$EMAIL"}
    done ;;
  presupuesto)
    # Alerta de presupuesto de 50 USD con avisos al 50 %, 80 % y 100 %.
    # En Azure for Students puede no estar permitido por CLI: hazlo en el portal
    # (Cost Management + Billing > Budgets > Add) y documenta la captura.
    az consumption budget create --budget-name presupuesto-medisur --amount "$BUDGET_USD" \
      --category cost --time-grain monthly \
      --start-date "$(date -u +%Y-%m-01)" --end-date "$(date -u -d '+3 months' +%Y-%m-01)" ;;
  apagar)       # "deallocate" = liberada: deja de cobrar cómputo (apagar desde dentro del SO NO lo hace)
    for vm in $VMS; do az vm deallocate -g "$RG" -n "$vm" --no-wait; done ;;
  encender)
    for vm in $VMS; do az vm start -g "$RG" -n "$vm" --no-wait; done ;;
  estado)
    az vm list -g "$RG" -d --query "[].{vm:name,estado:powerState,tamano:hardwareProfile.vmSize}" -o table
    az disk list -g "$RG" --query "[].{disco:name,GB:diskSizeGb,sku:sku.name}" -o table ;;
  borrar-todo)  # Al terminar TODO el proyecto: borra el grupo completo (VMs, discos, IPs, NICs)
    read -r -p "Se borrará el grupo $RG completo. Escribe BORRAR para continuar: " c
    [ "$c" = "BORRAR" ] && az group delete -n "$RG" --yes --no-wait ;;
  *) echo "Acciones: apagado-auto | presupuesto | apagar | encender | estado | borrar-todo"; exit 1 ;;
esac
