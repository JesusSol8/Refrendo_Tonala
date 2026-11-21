# Despliegue y configuración de integración

## Entorno local ya probado

Waitress + Django + SQLite, enlazado exclusivamente a 127.0.0.1:8000. Se utiliza para presentar el flujo sin credenciales ni pagos reales. Sigue README.md o INICIAR.cmd.

## Pruebas públicas con HTTPS (configuración entregada, no ejecutada aquí)

Requiere un servidor con Docker Compose, dominio de pruebas bajo tu control y registros DNS hacia el servidor. No intentes usar tonala.gob.mx sin autorización. Puertos 80/443 deben ser alcanzables para obtener el certificado. PostgreSQL y Waitress no publican puertos directamente.

1. Copia `.env.example` a `.env`.
2. Configura `PUBLIC_HOST`, `PUBLIC_BASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` con tu dominio real. Mantén DEBUG=0.
3. Genera tres claves distintas (SECRET_KEY, DOCUMENT_SIGNING_KEY, AUDIT_KEY) y una contraseña PostgreSQL; por ejemplo `python -c "import secrets; print(secrets.token_hex(32))"` para cada variable. La contraseña de BD en hexadecimal evita caracteres especiales en DATABASE_URL.
4. Conserva DEMO_MODE=1 para la primera demostración pública. No se crean usuarios con contraseña por defecto.
5. Ejecuta:

```text
docker compose up -d --build
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py check --deploy
docker compose exec web python manage.py verify_audit
docker compose logs --tail=100 web proxy
```

6. Abre la URL HTTPS, crea un refrendo de prueba y verifica el QR desde un teléfono. Caddy está configurado para aceptar exclusivamente TLS 1.3; navegadores antiguos que no lo soporten no podrán conectar.

El Compose es de un solo servidor. Para acercarse al objetivo 99.5% se requiere implementar la arquitectura redundante y medirla; consulta ARQUITECTURA.md. Prueba backups y restauración antes de usar datos reales.

## Integración Mercado Pago (sin simular aprobación)

1. Crea una aplicación en Mercado Pago México y cuentas de prueba según su documentación.
2. Habilita Checkout Pro vía Preferences API y obtiene el access token privado correspondiente al ambiente de pruebas.
3. Configura Webhooks, evento `payment`, a `https://TU-DOMINIO/api/v1/mercadopago/webhook/`. Obtén la clave secreta de firma de esa aplicación.
4. Establece `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `MP_SANDBOX=1`, `DEMO_MODE=0`.
5. Antes de cambiar a pagos externos valida el catálogo de tarifas del ejercicio y marca `academic=False` únicamente si corresponde a una liquidación aprobada para la prueba. El bloqueo evita cobrar con tarifas ficticias por accidente. El entorno ya no crea el padrón demo automáticamente.
6. Reinicia con `docker compose up -d`. Confirma que el endpoint `/pago-demostracion/.../` devuelve 404.
7. Ejecuta una compra de prueba en el checkout alojado por el proveedor. Valida el webhook en sus registros y en la bitácora. Prueba tarjeta aprobada/rechazada, SPEI/efectivo pendiente y posterior acreditación, según habilitación de la cuenta.
8. No captures datos de tarjeta en tu app. No apruebes pagos basándote en parámetros de la URL de regreso.

El código verifica x-signature con el manifest de ID, request-id y timestamp; consulta `/v1/payments/{id}`; verifica external_reference, MXN, importe exacto y live_mode; luego aplica el estado transaccionalmente. Se rechazan firmas con más de diez minutos de diferencia. Sincroniza el reloj del servidor. Comprueba en sandbox el comportamiento de reintentos de tu integración; si el proveedor repite una firma antigua, se debe revisar su política y recuperar el pago por conciliación autenticada, no eliminar la validación sin análisis.

### Conciliación de una notificación perdida

```text
docker compose exec web python manage.py reconcile_payment ID_REAL_DEL_PAGO
```

El comando consulta al proveedor con token privado y aplica las mismas comprobaciones. Nunca acepta un estado escrito por el operador. Se puede incorporar posteriormente una tarea de búsqueda/reconciliación periódica; no existe scheduler activo en este paquete.

## Operación y continuidad

- Respalda base de datos y claves; ambos son necesarios para conservar la verificación. No cambies DOCUMENT_SIGNING_KEY ni AUDIT_KEY sin una migración planificada: el paquete aún no tiene llavero histórico.
- Acceso administrativo solo para operadores autorizados; restringe login por red o un proxy de identidad cuando corresponda.
- El rol de aplicación PostgreSQL debería tener privilegios mínimos y un rol de migración distinto. El Compose usa un solo rol para simplificar el entorno de pruebas.
- Exporta conciliación y sellos de auditoría a almacenamiento independiente para evidenciar una restauración antigua o intervención de un administrador de BD.
- Monitorea `/salud/`, errores de webhook, cola de pagos pendientes, pagos duplicados y certificados revocados.
- Define retención de datos, respaldos, recuperación, aviso legal municipal y contratos de paquetería antes de operación real.

## QR desde un teléfono

`PUBLIC_BASE_URL` se fija en el servidor. No depende del encabezado Host del navegador. Una URL 127.0.0.1 identifica al mismo dispositivo que escanea; por eso el PDF local no abre el servidor de tu PC desde un teléfono. Configura una URL HTTPS pública accesible y genera/descarga el PDF nuevamente en ese despliegue. Cambiar de URL no cambia el sello, pero el QR se vuelve a dibujar con la URL configurada.

El Compose habilita TRUST_PROXY=1 porque solo Caddy puede alcanzar Waitress desde Internet. Caddy sobrescribe X-Real-IP con la dirección del cliente; Django la usa para el límite de consultas. No habilites TRUST_PROXY si permites acceso directo a Waitress desde una red no confiable.
