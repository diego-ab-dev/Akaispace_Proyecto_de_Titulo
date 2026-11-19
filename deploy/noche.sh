#!/bin/bash
# Apagado y encendido nocturno de produccion.
# Uso: deploy/noche.sh apagar|encender [--seco]
#   apagar    sin avisos de alarmas ni de Route 53, autoescalado a 0, instancia de pruebas y RDS detenidas.
#   encender  lo contrario y en orden: RDS, autoescalado a 1, espera /health/, Route 53 y avisos de alarmas.
#             La instancia de pruebas queda detenida (se enciende solo cuando se usa).
#   --seco    solo muestra lo que haria, con el estado actual de cada recurso; no cambia nada.
# RDS detenida se vuelve a encender sola a los 7 dias.
set -euo pipefail
export MSYS_NO_PATHCONV=1
export AWS_PROFILE=${AWS_PROFILE:-akaispace}
export AWS_PAGER=""

R=sa-east-1
ALARMAS=(akaispace-alb-5xx akaispace-instancias-no-sanas akaispace-rds-cpu)
ALARMA_DNS=akaispace-route53-health   # en us-east-1
ASG=akaispace-prod-asg
DB=akaispace-prod
URL=https://akaispace.shop/health/

ACCION=${1:-}
SECO=0
[ "${2:-}" = "--seco" ] && SECO=1

hacer() { if [ "$SECO" = 1 ]; then echo "  [seco] $*"; else echo "  > $*"; "$@"; fi; }
paso() { echo; echo "== $*"; }

HC=$(aws cloudformation describe-stacks --region $R --stack-name akaispace-04-app \
  --query "Stacks[0].Outputs[?OutputKey=='ComprobacionDns'].OutputValue" --output text 2>/dev/null || true)
estado_db() { aws rds describe-db-instances --region $R --db-instance-identifier $DB \
  --query 'DBInstances[0].DBInstanceStatus' --output text; }
pruebas_encendida() { aws ec2 describe-instances --region $R \
  --filters Name=tag:Name,Values=akaispace-pruebas Name=instance-state-name,Values=pending,running \
  --query 'Reservations[].Instances[].InstanceId' --output text; }
estado_asg() { aws autoscaling describe-auto-scaling-groups --region $R --auto-scaling-group-names $ASG \
  --query 'AutoScalingGroups[0].[MinSize,DesiredCapacity,length(Instances)]' --output text; }
estado_hc() { aws route53 get-health-check --health-check-id "$HC" --query 'HealthCheck.HealthCheckConfig.Disabled' --output text; }
estado_alarmas() {
  aws cloudwatch describe-alarms --region $R --alarm-names "${ALARMAS[@]}" --query 'MetricAlarms[].[AlarmName,ActionsEnabled]' --output text
  aws cloudwatch describe-alarms --region us-east-1 --alarm-names $ALARMA_DNS --query 'MetricAlarms[].[AlarmName,ActionsEnabled]' --output text
}
hay_hc() { [ -n "$HC" ] && [ "$HC" != "None" ]; }

apagar() {
  paso "1. Avisos de las alarmas (desactivados para que no lleguen correos de noche)"
  estado_alarmas | sed 's/^/  ahora: /'
  hacer aws cloudwatch disable-alarm-actions --region $R --alarm-names "${ALARMAS[@]}"
  hacer aws cloudwatch disable-alarm-actions --region us-east-1 --alarm-names $ALARMA_DNS

  paso "2. Comprobacion de estado de Route 53"
  if hay_hc; then
    echo "  ahora: desactivada=$(estado_hc)"
    hacer aws route53 update-health-check --health-check-id "$HC" --disabled --query HealthCheck.Id --output text
  else echo "  (no existe)"; fi

  paso "3. Autoescalado de produccion a 0"
  echo "  ahora: minimo, deseado, instancias = $(estado_asg)"
  hacer aws autoscaling update-auto-scaling-group --region $R --auto-scaling-group-name $ASG --min-size 0 --desired-capacity 0

  paso "4. Instancia de pruebas"
  P=$(pruebas_encendida)
  if [ -n "$P" ]; then hacer aws ec2 stop-instances --region $R --instance-ids $P --query 'StoppingInstances[].CurrentState.Name' --output text
  else echo "  ahora: detenida (nada que hacer)"; fi

  paso "5. RDS"
  E=$(estado_db); echo "  ahora: $E"
  if [ "$E" = "available" ]; then hacer aws rds stop-db-instance --region $R --db-instance-identifier $DB --query DBInstance.DBInstanceStatus --output text
  else echo "  (no esta 'available'; no se detiene)"; fi

  echo; echo "Apagado listo. El sitio responde 503 hasta encender."
}

encender() {
  paso "1. RDS"
  E=$(estado_db); echo "  ahora: $E"
  [ "$E" = "stopped" ] && hacer aws rds start-db-instance --region $R --db-instance-identifier $DB --query DBInstance.DBInstanceStatus --output text
  if [ "$SECO" = 1 ]; then echo "  [seco] esperaria a que RDS este 'available'"
  else echo "  esperando a que RDS este 'available' (5 a 10 minutos)..."; aws rds wait db-instance-available --region $R --db-instance-identifier $DB; fi

  paso "2. Autoescalado de produccion a 1"
  echo "  ahora: minimo, deseado, instancias = $(estado_asg)"
  hacer aws autoscaling update-auto-scaling-group --region $R --auto-scaling-group-name $ASG --min-size 1 --desired-capacity 1

  paso "3. Esperar a que $URL responda"
  if [ "$SECO" = 1 ]; then
    echo "  [seco] esperaria hasta 15 minutos; ahora responde $(curl -s -o /dev/null -w '%{http_code}' --max-time 10 $URL || true)"
  else
    CODIGO=000
    for _ in $(seq 1 60); do
      CODIGO=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 $URL || true)
      [ "$CODIGO" = "200" ] && break
      sleep 15
    done
    if [ "$CODIGO" != "200" ]; then
      echo "  /health/ no responde 200 (ultimo: $CODIGO). Los avisos siguen desactivados: revisar la instancia."; exit 1
    fi
    echo "  /health/ responde 200"
  fi

  paso "4. Comprobacion de estado de Route 53"
  if hay_hc; then
    echo "  ahora: desactivada=$(estado_hc)"
    hacer aws route53 update-health-check --health-check-id "$HC" --no-disabled --query HealthCheck.Id --output text
    if [ "$SECO" = 0 ]; then
      echo "  esperando que los verificadores de Route 53 vean el sitio sano..."
      for _ in $(seq 1 18); do
        OK=$(aws route53 get-health-check-status --health-check-id "$HC" \
          --query "length(HealthCheckObservations[?starts_with(StatusReport.Status,'Success')])" --output text)
        [ "$OK" -ge 10 ] && break
        sleep 10
      done
      echo "  verificadores con exito: $OK"
    fi
  else echo "  (no existe)"; fi

  paso "5. Avisos de las alarmas"
  estado_alarmas | sed 's/^/  ahora: /'
  hacer aws cloudwatch enable-alarm-actions --region $R --alarm-names "${ALARMAS[@]}"
  hacer aws cloudwatch enable-alarm-actions --region us-east-1 --alarm-names $ALARMA_DNS

  echo; echo "Encendido listo. La instancia de pruebas sigue detenida."
}

case "$ACCION" in
  apagar) apagar ;;
  encender) encender ;;
  *) echo "Uso: $0 apagar|encender [--seco]"; exit 2 ;;
esac
