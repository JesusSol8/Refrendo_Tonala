#!/usr/bin/env bash
set -euo pipefail
cd /opt/refrendo-tonala

echo "=== 1. Estado inicial del servicio ==="
docker compose -f compose.aws.yaml ps

echo "=== 2. Simulando caída abrupta del contenedor Django/Waitress (SIGKILL) ==="
CONTAINER_ID=$(docker compose -f compose.aws.yaml ps -q web)
docker kill "$CONTAINER_ID"

echo "=== 3. Esperando autorrecuperación mediante Docker restart policy + Healthcheck ==="
sleep 6
docker compose -f compose.aws.yaml ps

echo "=== 4. Verificando endpoint /salud/ e integridad HMAC hacia Amazon S3 ==="
docker compose -f compose.aws.yaml exec -T web python scripts/aws_s3_audit.py
echo "=== PRUEBA DE RESILIENCIA SUPERADA ==="