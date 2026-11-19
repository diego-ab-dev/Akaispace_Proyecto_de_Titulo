#!/bin/bash
# Pagina de mantencion (secciones 11.2.1 y 11.2.4 y Anexo VIII, escenario 2).
# Uso: deploy/mantencion.sh on|off|estado
#   on     agrega en los listeners 443 y 80 una regla de prioridad 1 que responde 503 con una pagina corta.
#   off    quita esa regla de los dos listeners.
#   estado muestra si esta activa.
# Las comprobaciones del balanceador van directo a las instancias y no se ven afectadas; la de Route 53 y la
# alarma akaispace-alb-5xx si marcan la caida mientras esta activa.
set -euo pipefail
export MSYS_NO_PATHCONV=1
export AWS_PROFILE=${AWS_PROFILE:-akaispace}
export AWS_REGION=${AWS_REGION:-sa-east-1}
export AWS_PAGER=""

exportado() { aws cloudformation list-exports --query "Exports[?Name=='$1'].Value" --output text; }
LISTENERS=("$(exportado akaispace-listener-https)" "$(exportado akaispace-listener-http)")

# Maximo 1 KB (limite del balanceador). Sin comillas dobles ni barras invertidas: va dentro de un JSON.
PAGINA="<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Akai Space - En mantenci&oacute;n</title><style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:system-ui,sans-serif;background:#111;color:#eee;text-align:center}main{max-width:32rem;padding:1.5rem}h1{color:#e63946}</style></head><body><main><h1>Estamos en mantenci&oacute;n</h1><p>Akai Space vuelve en unos minutos. Gracias por tu paciencia.</p></main></body></html>"

regla_de() {
  aws elbv2 describe-rules --listener-arn "$1" --query "Rules[?Priority=='1'].RuleArn" --output text
}

case "${1:-}" in
  on)
    [ "${#PAGINA}" -le 1024 ] || { echo "La pagina supera 1 KB"; exit 1; }
    ACCION=$(printf '[{"Type":"fixed-response","FixedResponseConfig":{"StatusCode":"503","ContentType":"text/html","MessageBody":"%s"}}]' "$PAGINA")
    for L in "${LISTENERS[@]}"; do
      if [ -n "$(regla_de "$L")" ]; then echo "Ya estaba activa en ${L##*/}"; continue; fi
      aws elbv2 create-rule --listener-arn "$L" --priority 1 \
        --conditions '[{"Field":"path-pattern","PathPatternConfig":{"Values":["/*"]}}]' \
        --actions "$ACCION" --tags Key=Proyecto,Value=akaispace --query 'Rules[0].Priority' --output text >/dev/null
      echo "Mantencion activada en ${L##*/}"
    done
    echo "El cambio tarda unos segundos en llegar a los 2 nodos del balanceador." ;;
  off)
    for L in "${LISTENERS[@]}"; do
      R=$(regla_de "$L")
      if [ -z "$R" ]; then echo "No estaba activa en ${L##*/}"; continue; fi
      aws elbv2 delete-rule --rule-arn "$R"
      echo "Mantencion desactivada en ${L##*/}"
    done
    echo "El cambio tarda unos segundos en llegar a los 2 nodos del balanceador." ;;
  estado)
    for L in "${LISTENERS[@]}"; do
      if [ -n "$(regla_de "$L")" ]; then echo "${L##*/}: ACTIVA"; else echo "${L##*/}: apagada"; fi
    done ;;
  *)
    echo "Uso: $0 on|off|estado"; exit 2 ;;
esac
