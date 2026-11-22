#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/refrendo-tonala"
export DEBIAN_FRONTEND=noninteractive

cd "$APP_DIR"

if [ ! -f .env ]; then
    echo "ERROR: No existe el archivo .env"
    exit 1
fi

if [ "${1:-}" != "--refresh" ]; then

    apt-get update

    apt-get install -y \
        ca-certificates \
        curl \
        git \
        openssl

    if ! docker compose version >/dev/null 2>&1; then

        apt-get remove -y \
            docker.io \
            docker-compose \
            docker-compose-v2 \
            podman-docker \
            containerd \
            runc || true

        install -m 0755 -d /etc/apt/keyrings

        curl -fsSL \
            https://download.docker.com/linux/ubuntu/gpg \
            -o /etc/apt/keyrings/docker.asc

        chmod a+r /etc/apt/keyrings/docker.asc

        . /etc/os-release

        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
            > /etc/apt/sources.list.d/docker.list

        apt-get update

        apt-get install -y \
            docker-ce \
            docker-ce-cli \
            containerd.io \
            docker-buildx-plugin \
            docker-compose-plugin
    fi

    systemctl enable --now docker
fi

# Obtener IP pública mediante IMDSv2.

TOKEN=$(curl -fsS \
    --retry 5 \
    --connect-timeout 5 \
    -X PUT \
    "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

PUBLIC_IP=$(curl -fsS \
    --retry 5 \
    --connect-timeout 5 \
    -H "X-aws-ec2-metadata-token: $TOKEN" \
    "http://169.254.169.254/latest/meta-data/public-ipv4")

if [ -z "$PUBLIC_IP" ]; then
    echo "ERROR: EC2 no tiene IPv4 pública."
    exit 1
fi

DOMAIN="${PUBLIC_IP}.sslip.io"

export PUBLIC_IP DOMAIN

# Actualizar configuración sin modificar contraseñas ni claves existentes.

python3 - <<'PY'
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

path = Path(".env")
values = {}

for line in path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        key, value = line.split("=", 1)
        values[key] = value

ip = os.environ["PUBLIC_IP"]
domain = os.environ["DOMAIN"]

values.update({
    "DEBUG": "0",
    "TRUST_PROXY": "1",
    "REQUIRE_POSTGRES16": "1",
    "PUBLIC_IP": ip,
    "PUBLIC_HOST": domain,
    "PUBLIC_BASE_URL": f"https://{domain}",
    "ALLOWED_HOSTS": f"{domain},{ip},localhost,127.0.0.1",
    "CSRF_TRUSTED_ORIGINS": f"https://{domain}",
})

database_url = values.get("DATABASE_URL")

if not database_url:
    raise SystemExit("ERROR: DATABASE_URL no configurada.")

url = urlsplit(database_url)

if url.scheme not in ("postgres", "postgresql"):
    raise SystemExit("ERROR: AWS requiere PostgreSQL.")

parameters = dict(parse_qsl(url.query))
parameters["sslmode"] = "require"

values["DATABASE_URL"] = urlunsplit(
    url._replace(query=urlencode(parameters))
)

path.write_text(
    "\n".join(f"{k}={v}" for k, v in values.items()) + "\n"
)

path.chmod(0o600)
PY

COMPOSE=(docker compose -f compose.aws.yaml)

"${COMPOSE[@]}" config --quiet

if [ "${1:-}" = "--refresh" ]; then
    "${COMPOSE[@]}" up -d --wait --wait-timeout 600
else
    "${COMPOSE[@]}" up -d --build --wait --wait-timeout 600
fi

"${COMPOSE[@]}" exec -T web python manage.py check
"${COMPOSE[@]}" exec -T web python manage.py seed_demo

# Actualizar IP y dominio automáticamente después de reiniciar Learner Lab.

cat > /etc/systemd/system/refrendo.service <<'EOF'
[Unit]
Description=Refrendo Tonala AWS
Wants=network-online.target
Requires=docker.service
After=network-online.target docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/refrendo-tonala
ExecStart=/bin/bash /opt/refrendo-tonala/infra/configure_ec2.sh --refresh
RemainAfterExit=yes
TimeoutStartSec=900

[Install]
WantedBy=multi-user.target
EOF

rm -f /etc/cron.d/refrendo-ip

systemctl daemon-reload
systemctl enable refrendo.service

echo "Portal: https://${DOMAIN}"
echo "Diagnóstico: http://${PUBLIC_IP}/salud/"
echo "Administrador: https://${DOMAIN}/admin/"

"${COMPOSE[@]}" ps