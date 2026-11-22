#!/bin/sh
set -eu

if [ "${REQUIRE_POSTGRES16:-0}" = "1" ]; then
    python - <<'PY'
import os
import time
import psycopg

url = os.environ["DATABASE_URL"]

for attempt in range(60):
    try:
        with psycopg.connect(url, connect_timeout=5) as conn:
            version = conn.info.server_version

            if not 160000 <= version < 170000:
                raise SystemExit(
                    f"Se requiere PostgreSQL 16. Versión detectada: {version}"
                )

            print("PostgreSQL 16 conectado correctamente.")
            break

    except psycopg.OperationalError:
        print(f"Esperando PostgreSQL: {attempt + 1}/60", flush=True)
        time.sleep(5)
else:
    raise SystemExit("No fue posible conectar con PostgreSQL 16.")
PY
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Waitress 3.0 elimina encabezados de proxy no confiables.
# Confiar únicamente cuando el servidor está detrás de Caddy
# y el puerto 8000 no está publicado hacia Internet.

if [ "${TRUST_PROXY:-0}" = "1" ]; then
    exec waitress-serve \
        --listen=0.0.0.0:8000 \
        --threads=8 \
        --trusted-proxy="*" \
        --trusted-proxy-headers="x-forwarded-proto" \
        --clear-untrusted-proxy-headers \
        config.wsgi:application
else
    exec waitress-serve \
        --listen=0.0.0.0:8000 \
        --threads=8 \
        config.wsgi:application
fi