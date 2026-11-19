#!/bin/bash
# Ejecuta un comando en una instancia con Session Manager y espera el resultado (Fase 9.3).
# Uso: deploy/ssm.sh <instance-id> "<comando>"
set -euo pipefail
INSTANCIA=$1
COMANDO=$2
CMD_ID=$(aws ssm send-command --instance-ids "$INSTANCIA" --document-name AWS-RunShellScript \
  --comment "GitHub Actions ${GITHUB_REF_NAME:-manual}" \
  --parameters "$(jq -n --arg c "$COMANDO" '{commands: [$c]}')" \
  --query Command.CommandId --output text)
for _ in $(seq 1 60); do
  sleep 10
  ESTADO=$(aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCIA" \
    --query Status --output text 2>/dev/null || echo Pending)
  case "$ESTADO" in
    Success)
      aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCIA" \
        --query StandardOutputContent --output text | tail -n 20
      exit 0 ;;
    Failed|Cancelled|TimedOut)
      aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$INSTANCIA" \
        --query StandardErrorContent --output text
      exit 1 ;;
  esac
done
echo "Tiempo de espera agotado"; exit 1
