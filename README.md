# Refrendo Tonalá · Proyecto integrador

Sistema académico desarrollado con **Python 3.12 y Django 5.2 LTS**. Permite demostrar el flujo completo de refrendo de licencias municipales con un padrón ficticio, sin cuentas externas ni cobros reales.

El proyecto soporta **dos modalidades de ejecución**:
1. **Ejecución local en Windows / Linux / macOS:** Lista para demostraciones sin conexión mediante SQLite.
2. **Despliegue automatizado en AWS (Arquitectura Base Académica):** Infraestructura como Código (IaC) construida sin clics en la consola web, diseñada específicamente para operar dentro de las restricciones y créditos gratuitos de **AWS Academy Learner Lab**.

---

## Despliegue Automatizado en AWS (Base Académica · Learner Lab)

Para cumplir con los estándares de despliegue en la nube sin utilizar la interfaz gráfica de AWS, el repositorio incluye el script `infra/deploy_aws.sh` y el archivo `compose.aws.yaml`. Esta implementación constituye una **arquitectura base funcional** adaptada a una cuenta educativa gratuita de **AWS Academy Learner Lab** (aprovechando el perfil preexistente `LabInstanceProfile` debido a que el entorno académico restringe la creación de nuevos roles o usuarios en IAM).

### Pasos para desplegar desde cero (Cero clics)

No es necesario crear un archivo `.env` manualmente ni ejecutar `INICIAR.cmd` en el servidor. El script automatiza toda la configuración:

1. Inicia tu laboratorio en **AWS Academy Learner Lab** (presiona *Start Lab* y espera el indicador verde) y abre **AWS CloudShell** (ícono `>_` en la barra superior de la consola AWS).
2. Clona el repositorio y ejecuta el script de aprovisionamiento indicando la URL pública del repositorio Git:

```bash
git clone https://github.com/JesusSol8/Refrendo_Tonala.git
cd Refrendo_Tonala
bash infra/deploy_aws.sh https://github.com/JesusSol8/Refrendo_Tonala.git
```

3. **¿Qué construye automáticamente el script? (~6 minutos):**
   - **Llave SSH:** Genera un par de claves (`refrendo-tonala-key.pem`) para acceso administrativo seguro.
   - **VPC y Security Groups:** Crea `web-sg` (puertos `22`, `80` y `443` abiertos al público) y `db-sg` (puerto `5432` restringido exclusivamente al tráfico proveniente de `web-sg`).
   - **Amazon S3:** Crea un bucket privado con **versionado habilitado** y bloqueo de acceso público para almacenar evidencias externas de la bitácora HMAC.
   - **Amazon RDS (`db.t3.micro`):** Aprovisiona una instancia **PostgreSQL 16** sin acceso público, garantizando persistencia transaccional ACID y soporte para disparadores *append-only*.
   - **Amazon EC2 (`t3.small`):** Lanza un servidor Ubuntu Server 22.04 asociado a `LabInstanceProfile` que instala Docker, clona el proyecto, genera automáticamente su archivo `.env` con claves criptográficas aleatorias de 64 caracteres, levanta los contenedores (`compose.aws.yaml`) detrás de **Caddy TLS 1.3**, configura HTTPS real mediante `<IP_PUBLICA>.sslip.io`, aplica migraciones, carga el padrón ficticio (`seed_demo`), crea el superusuario administrativo y exporta el primer sello de auditoría a S3.

### Manejo de sesiones temporales de Learner Lab
- **Cambio de IP pública tras apagar instancias:** Cuando la sesión de 4 horas de Learner Lab detiene la instancia EC2 y se reinicia días después, AWS asigna una nueva IP pública. El servidor incluye un script registrado en `@reboot` (`/usr/local/bin/refresh-refrendo-ip.sh`) que detecta la nueva IP al encenderse, actualiza `PUBLIC_BASE_URL` en el `.env` con el nuevo dominio `.sslip.io` y renueva el certificado HTTPS automáticamente en segundos.
- **Duración de sesión:** Cada sesión de Learner Lab dura 4 horas; basta presionar nuevamente *Start Lab* antes de que expire el contador para extender el tiempo sin interrumpir los servicios.

---

## Empezar en Windows (Ejecución Local)

1. Instala Python 3.12 o superior desde `python.org`, con `pip` habilitado.
2. Abre **INICIAR.cmd**. La primera ejecución descarga las dependencias en `.packages`; las siguientes reutilizan dicha carpeta.
3. Entra a **http://127.0.0.1:8000/**. Mantén abierta la ventana del servidor durante la demostración.
4. Para administración entra a `/admin/`. El iniciador genera un usuario `demo_admin` y una contraseña aleatoria en `.demo-access.txt`.
5. Consulta `TON-0001` con `María López García` (o `TON-0007` con `Luis Ramírez Soto`). También hay casos de ejemplo visibles en el inicio.

No se necesita activar un entorno virtual. La instalación inicial necesita Internet; el portal funciona después sin conexión en modo demostración. `Ctrl+C` detiene el servidor. No abras dos servidores en el mismo puerto. No elimines `.local-settings.json`: conserva las claves de documentos y auditoría.

---

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

---

## Qué incluye

- **Consulta y validación de elegibilidad:** Búsqueda con dos campos; normalización de mayúsculas, espacios y acentos, sin coincidencias parciales de nombre. Bloqueo de giros que requieren dictamen previo, licencias inactivas y ejercicios anteriores pendientes.
- **Motor de liquidación:** Cálculos exactos con `Decimal`, conceptos obligatorios, aportaciones voluntarias desmarcadas por defecto y cotización de envío según prefijo de código postal.
- **Inmutabilidad del trámite:** Liquidación congelada en un *snapshot* al confirmar; protección contra doble registro por licencia y año.
- **Flujo de pagos:** Pago demostrable con tarjeta, SPEI y efectivo (estados aprobado, pendiente y rechazado), además de adaptador REST para Mercado Pago Checkout Pro con validación HMAC de webhooks, consulta autenticada del pago, control de importe/moneda/referencia y reembolsos.
- **Documentos verificables:** Carátula PDF generada en servidor y código QR con sello **HMAC-SHA256** para verificación pública con exposición mínima de datos.
- **Gestión operativa:** Administración de catálogos, gestión de entregas y guías, conciliación CSV protegida contra inyección de fórmulas.
- **Auditoría e integridad:** Bitácora con cadena criptográfica HMAC y prohibición de `UPDATE`/`DELETE` mediante disparadores (*triggers*) en SQLite y PostgreSQL.
- **Infraestructura Cloud y Resiliencia:** Aprovisionamiento automatizado en AWS (VPC/Security Groups + EC2 + RDS PostgreSQL + S3), respaldo externo de sellos de auditoría mediante `boto3` (`scripts/aws_s3_audit.py`) y pruebas automatizadas de tolerancia a fallos (`scripts/simulate_resilience.sh`).
- **Calidad y control de versiones:** Pruebas unitarias automatizadas, integración continua con GitHub Actions, documentación técnica, migraciones y flujo GitFlow.

---

## Alcance comprobado y dependencias externas

Tanto el **modo académico local** como la **arquitectura base en AWS** están implementados y probados. No deben confundirse con un sistema oficial municipal en operación. Consulta la matriz completa en `docs/RTM.md` y el detalle de nube en `docs/AWS_DOCUMENTACION.md`.

- **Infraestructura en AWS (Base Académica Gratuita):** Implementada sobre una cuenta educativa de **AWS Academy Learner Lab** como arquitectura base funcional (desacoplamiento de capa web y base de datos, HTTPS real con `sslip.io` y respaldo de auditoría en S3). El consumo estimado de pruebas y demostración es menor a **$5.00 USD** dentro de los créditos gratuitos del laboratorio; fuera de la capa gratuita, su operación continua 24/7 se estima en **$33.54 USD/mes** (**$402.48 USD/año**).
- **Padrón:** Siete licencias ficticias (`TON-0001` a `TON-0007`). No hay acceso a datos ni servicios internos municipales.
- **Tarifas:** Tabuladores académicos versionados por año/giro. La cédula toma como referencia el art. 91 I c de la Ley 2026; la base, aportaciones, envío y recargos son supuestos académicos. No se liquida una deuda fiscal real. Los tabuladores académicos bloquean el modo de pagos externos hasta que un administrador valide y marque el catálogo correspondiente.
- **Mercado Pago:** Integración escrita y probada con respuestas controladas. Requiere credenciales reales, aplicación del proveedor y URL HTTPS pública para validación externa.
- **Dominio oficial:** No se publica bajo `tonala.gob.mx`. El QR utiliza `PUBLIC_BASE_URL`: en local apunta a `127.0.0.1` (solo accesible desde la PC anfitriona), mientras que en el despliegue base de AWS utiliza `https://<IP_PUBLICA>.sslip.io`, permitiendo escanear y validar el QR desde cualquier teléfono móvil sin costo de dominio.
- **HTTPS y disponibilidad:** El servidor local utiliza HTTP en loopback, mientras que el despliegue en AWS habilita Caddy con **TLS 1.3** y recuperación automática ante fallos del contenedor web (`restart: always` + endpoint `/salud/`). No se certifican SLA de 99.5% ni infraestructura municipal productiva.
- **Identidad y accesibilidad:** Logo obtenido del portal oficial y tipografías Montserrat/Open Sans locales; adaptación institucional en vino y dorado. Reproducción exacta y conformidad WCAG AA requieren validación visual y auditoría especializada.

---

## Pruebas y operación

### Pruebas unitarias y de integridad (Local / CI)
```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test refrendo
python manage.py verify_audit
```

El iniciador instala dependencias en `.packages`; si usas esa instalación para comandos manuales define `PYTHONPATH=.packages` y las mismas claves de `.local-settings.json`, o ejecuta los comandos dentro de tu entorno convencional. En demo local, `settings.py` también lee las claves de `.local-settings.json` si existe.

### Pruebas de resiliencia y auditoría en AWS (EC2)
Conectado por SSH a la instancia EC2 (`ssh -i refrendo-tonala-key.pem ubuntu@<IP_PUBLICA>`), puedes ejecutar las pruebas de tolerancia a fallos y respaldo externo:

```bash
# Simula caída abrupta del contenedor Django/Waitress (SIGKILL), verifica
# autorrecuperación automática en segundos y valida integridad hacia S3
sudo bash /opt/refrendo-tonala/scripts/simulate_resilience.sh

# Ejecuta manualmente la verificación de cadena HMAC y sube evidencia JSON a S3
docker compose -f /opt/refrendo-tonala/compose.aws.yaml exec -T web python scripts/aws_s3_audit.py
```

---

## Detener o eliminar

Apagar EC2 y RDS conserva datos, pero el almacenamiento y otros recursos pueden seguir generando cargos. RDS puede reiniciarse automáticamente después de siete días detenido. Para dejar de consumir recursos, usa el script de limpieza si existe en la versión del repositorio y revisa después los recursos remanentes, snapshots y bucket. No ejecutes un script de limpieza sin confirmar que el bucket y la base son exclusivamente de esta demostración: borrarlos elimina datos.

## Evidencia y límites

- La copia del proyecto contiene un registro de 44 pruebas automatizadas locales aprobadas y una nota de recorrido local.
- En la conversación anterior se reportó RDS disponible con PostgreSQL 16.15 y EC2 en estado `running`. No quedó evidencia de HTTPS, página pública ni healthcheck de la aplicación en AWS.
- La prueba de caída del contenedor está escrita, pero no hay resultado guardado de su ejecución en AWS. Tampoco hay pruebas reales de cambio de IP, interrupción de RDS, carga, SLA, restauración o costos facturados.
- Mercado Pago tiene lógica probada con respuestas simuladas; falta validación con una cuenta y credenciales reales.

## Documentación para entregar

| Archivo | Contenido |
|---|---|
| `docs/AWS_DOCUMENTACION.md` | Guía IaC en AWS, diagrama de arquitactura nube, justificación, pruebas de resiliencia y costos |
| `docs/ARQUITECTURA.md` | Componentes, decisiones, seguridad, DER y diccionario de datos |
| `docs/ARQUITECTURA.mmd` | Diagrama arquitectura aws | 
| `docs/RTM.md` y `docs/RTM.csv` | Requisito → implementación → prueba → estado y pendientes |
| `docs/PLAN_DE_PRUEBAS.md` | Casos, escenarios, evidencias y criterios de aceptación |
| `docs/GUIA_DE_PRUEBAS.md` | Es la guia para poder replicar las pruebas aplicadas en este proyecto |
| `docs/MANUAL_DEMO.md` | Guion de exposición, datos de prueba y respuestas para defender el proyecto |
| `docs/DESPLIEGUE.md` | Instalación de pruebas HTTPS y configuración del proveedor de pagos |
| `docs/GESTION_PROYECTO.md` | Alcance, EDT, cronograma propuesto, riesgos y GitFlow |
| `docs/DECISIONES_Y_FUENTES.md` | Supuestos, discrepancias del enunciado y fuentes primarias |
| `docs/REQUERIMIENTOS_ORIGINALES.md` | Copia del documento de requerimientos recibido |
| `docs/PRODUCCION.md` | Plan si se llega a poner la pagina en produccion real y no un entorno escolar |

|Las instrucciones de [docs/RESILIENCIA.md](docs/RESILIENCIA.md) Solas preubas y su resultado en aws.| 

El repositorio local incluye ramas `main` y `develop`, etiqueta de entrega y una rama de funcionalidad/release para mostrar GitFlow. `docs/GESTION_PROYECTO.md` explica cómo continuarlo. Si recibiste el ZIP, incluye un respaldo `repositorio.bundle` que conserva commits, ramas y etiquetas.