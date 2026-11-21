# Refrendo Tonalá · Proyecto integrador

Sistema académico desarrollado con **Python 3.12 y Django 5.2 LTS**. Permite demostrar el refrendo completo con un padrón ficticio, sin cuentas externas ni cobros reales.

## Empezar en Windows

1. Instala Python 3.12 o superior desde python.org, con pip. Si ejecutas en la computadora de esta conversación, el iniciador también puede encontrar el Python incluido con Codex.
2. Abre **INICIAR.cmd**. La primera ejecución descarga las dependencias; las siguientes reutilizan `.packages`.
3. Entra a **http://127.0.0.1:8000/**. Mantén abierta la ventana del servidor durante la demostración.
4. Para administración entra a `/admin/`. El iniciador genera un usuario `demo_admin` y una contraseña aleatoria en `.demo-access.txt`.
5. Consulta `TON-0001` con `María López García`. También hay casos de ejemplo visibles en el inicio.

No se necesita activar un entorno virtual. La instalación inicial necesita Internet; el portal funciona después sin conexión en modo demostración. `Ctrl+C` detiene el servidor. No abras dos servidores en el mismo puerto. No elimines `.local-settings.json`: conserva las claves de documentos y auditoría.

## Instalación convencional (Windows, macOS o Linux)

```text
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py collectstatic --noinput
python -m waitress --listen=127.0.0.1:8000 config.wsgi:application
```

Para esta vía, exporta claves persistentes `SECRET_KEY`, `DOCUMENT_SIGNING_KEY` y `AUDIT_KEY`. En ausencia de variables se usan valores de desarrollo, exclusivamente para ejecución local. `.env` lo consume Docker Compose; `manage.py` no lo carga automáticamente. El iniciador `bootstrap.py` establece sus propias claves desde `.local-settings.json` para el proceso y sus hijos.

## Qué incluye

- Consulta con dos campos; normalización de mayúsculas, espacios y acentos, sin coincidencias parciales de nombre.
- Bloqueo de giros que requieren dictamen, licencias inactivas y ejercicios anteriores pendientes.
- Liquidación con Decimal, conceptos obligatorios, donaciones desmarcadas y envío según CP.
- Liquidación guardada e inalterada al confirmar; protección contra doble registro por licencia y año.
- Pago demostrable con tarjeta, SPEI y efectivo; estados aprobado, pendiente y rechazado.
- Adaptador REST de Mercado Pago Checkout Pro, validación HMAC de webhooks, consulta autenticada del pago, control de importe/moneda/referencia y reembolsos.
- Carátula PDF, QR con sello HMAC-SHA256 y verificación pública con datos mínimos.
- Administración de catálogos, gestión de entregas, guía y conciliación CSV protegida contra fórmulas.
- Bitácora con cadena HMAC y prohibición de UPDATE/DELETE mediante disparadores de base de datos.
- Pruebas automatizadas, documentación, migraciones, configuración Docker/PostgreSQL/Caddy TLS 1.3 y flujo GitFlow.

## Alcance comprobado y dependencias externas

El **modo académico local está implementado y probado**. No se debe confundir con un sistema oficial en operación. Consulta la matriz completa en `docs/RTM.md`.

- **Padrón:** siete licencias ficticias. No hay acceso a datos ni servicios internos municipales.
- **Tarifas:** tabuladores académicos versionados por año/giro. La cédula toma como referencia el art. 91 I c de la Ley 2026; la base, aportaciones, envío y recargos son supuestos académicos. No se liquida una deuda fiscal real. Los tabuladores académicos bloquean el modo de pagos externos hasta que un administrador valide y marque el catálogo correspondiente. No basta copiar una tarifa para certificar cumplimiento fiscal.
- **Mercado Pago:** integración escrita y probada con respuestas controladas. Requiere credenciales, una aplicación del proveedor y URL HTTPS pública para validación real. Las opciones SPEI/efectivo dependen de la habilitación de la cuenta mexicana; no se certificó su disponibilidad para una cuenta particular.
- **Dominio oficial:** no podemos publicar bajo `tonala.gob.mx`. El QR utiliza `PUBLIC_BASE_URL`. En local apunta a la misma computadora; para escanearlo desde un teléfono debe usarse una URL accesible desde ese teléfono, preferiblemente el despliegue HTTPS.
- **HTTPS y disponibilidad:** el servidor local utiliza HTTP en loopback. Se entrega configuración TLS 1.3 para Caddy y un diseño de disponibilidad, pero no se certifican 99.5% ni infraestructura municipal. Docker/PostgreSQL/TLS no se ejecutaron en esta computadora.
- **Identidad y accesibilidad:** logo obtenido del portal oficial y tipografías Montserrat/Open Sans locales; adaptación institucional en vino y dorado. Reproducción exacta y conformidad WCAG AA requieren validación visual y auditoría especializada. Se verificaron controles básicos y recorrido a ancho móvil.

## Pruebas y operación

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test refrendo
python manage.py verify_audit
```

El iniciador instala dependencias en `.packages`; si usas esa instalación para comandos manuales define `PYTHONPATH=.packages` y las mismas claves de `.local-settings.json`, o ejecuta los comandos dentro de tu entorno convencional. En demo local, settings.py también lee las claves de .local-settings.json si existe. Para evitar mezclar instalaciones, se recomienda el entorno virtual al desarrollar.

## Documentación para entregar

| Archivo | Contenido |
|---|---|
| `docs/ARQUITECTURA.md` | Componentes, decisiones, seguridad, DER y diccionario de datos |
| `docs/RTM.md` y `docs/RTM.csv` | Requisito → implementación → prueba → estado y pendientes |
| `docs/PLAN_DE_PRUEBAS.md` | Casos, escenarios, evidencias y criterios de aceptación |
| `docs/MANUAL_DEMO.md` | Guion de exposición, datos y respuestas para defender el proyecto |
| `docs/DESPLIEGUE.md` | Instalación de pruebas HTTPS y configuración del proveedor |
| `docs/GESTION_PROYECTO.md` | Alcance, EDT, cronograma propuesto, riesgos y GitFlow |
| `docs/DECISIONES_Y_FUENTES.md` | Supuestos, discrepancias del enunciado y fuentes primarias |
| `docs/REQUERIMIENTOS_ORIGINALES.md` | Copia del documento recibido |

El repositorio local incluye ramas `main` y `develop`, etiqueta de entrega y una rama de funcionalidad/release para mostrar GitFlow. No se ha subido a una cuenta remota. `docs/GESTION_PROYECTO.md` explica cómo continuarlo. Si recibiste el ZIP, incluye un respaldo `repositorio.bundle` que conserva commits, ramas y etiquetas.

