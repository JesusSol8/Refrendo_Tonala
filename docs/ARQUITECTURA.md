# Arquitectura y modelo de datos

## 1. Contexto y alcance

Cliente simulado: Ayuntamiento de Tonalá, Jalisco. Plataforma académica de refrendo para giros de bajo riesgo, ejercicio parametrizable (2026 por defecto). No sustituye una licencia ni un recibo oficial.

Se adopta un **monolito modular Django**: reduce el tiempo de desarrollo y permite mantener liquidación, pago, emisión y auditoría en una transacción de base de datos. HTML renderizado en servidor y JavaScript progresivo para cotizar y actualizar el estado. No necesita una aplicación SPA ni un servidor Node en operación.

## 2. Componentes

```mermaid
flowchart LR
  C[Ciudadano / navegador] -->|HTTPS| P[Caddy TLS 1.3]
  T[Tesorería / operador] -->|HTTPS + sesión| P
  P --> W[Waitress / Django]
  W --> V[Vistas y API v1]
  V --> S[Servicios de negocio]
  S --> D[(SQLite local / PostgreSQL despliegue)]
  S --> A[Bitácora append-only]
  V --> G[Generador PDF y QR]
  W -->|Preferencia / consulta autenticada| MP[Mercado Pago]
  MP -->|Webhook firmado| V
  Q[Escaneo de QR] --> P
```

En modo demo, un adaptador interno sustituye la pasarela y aplica el mismo servicio transaccional de pagos. El formulario no simula ser la página de Mercado Pago ni solicita información de tarjeta.

## 3. Estructura de código

| Componente | Responsabilidad |
|---|---|
| `config/settings.py` | Entorno, sesiones, seguridad, PostgreSQL/SQLite y variables del proveedor |
| `refrendo/models.py` | Padrón simulado, catálogos, trámites, pagos, carátulas y bitácora |
| `refrendo/forms.py` | Validación de consulta, entrega, aportaciones y resultados de demostración |
| `refrendo/services.py` | Elegibilidad, cotización, congelación, pagos y auditoría |
| `refrendo/payments.py` | API Mercado Pago, preferencias, firmas y conciliación |
| `refrendo/documents.py` | Carátula, QR y URL de verificación |
| `refrendo/views.py` | Autorización por sesión, endpoints y panel de operación |
| `refrendo/admin.py` | Catálogos editables y registros financieros de solo consulta |
| `refrendo/migrations/0002_append_only.py` | Prohibición de cambios/borrados en bitácora y certificados |
| `templates/`, `static/portal/` | Interfaz responsive sin recursos remotos obligatorios |

## 4. Modelo entidad-relación (DER)

```mermaid
erDiagram
  BusinessType ||--o{ License : clasifica
  BusinessType ||--o{ Tariff : tabula
  License ||--o{ Renewal : refrenda
  Renewal ||--o{ PaymentAttempt : inicia
  PaymentAttempt ||--o{ PaymentRecord : registra
  Renewal ||--o| Certificate : emite
  Renewal ||..o{ AuditEvent : referencia_textual
  Contribution }o..o{ Renewal : copia_en_snapshot
  ShippingRate ||..o{ Renewal : copia_en_snapshot
  AuditHead ||..o{ AuditEvent : encadena
  BusinessType {
    bigint id PK
    string code UK
    string name
    boolean low_risk
    string required_department
  }
  License {
    bigint id PK
    string number UK
    string taxpayer
    string trade_name
    bigint business_type_id FK
    string address
    boolean active
    int last_renewed_year
  }
  Tariff {
    bigint id PK
    int year
    bigint business_type_id FK
    decimal base
    decimal document_fee
    decimal mandatory_waste
    decimal surcharge
    string source
    boolean academic
  }
  Renewal {
    uuid id PK
    bigint license_id FK
    int year
    string status
    json snapshot
    decimal total
    string delivery
    json shipping_address
    string fulfillment
    string tracking_number
    datetime created_at
    datetime paid_at
  }
  PaymentAttempt {
    uuid id PK
    uuid renewal_id FK
    string provider
    string preference_id
    string checkout_url
    string status
    string method
  }
  PaymentRecord {
    bigint id PK
    string provider_id UK
    uuid attempt_id FK
    string status
    decimal amount
    string method
    datetime provider_updated_at
  }
  Certificate {
    uuid id PK
    uuid renewal_id FK
    json payload
    string digest UK
    datetime issued_at
  }
  AuditEvent {
    bigint id PK
    datetime created_at
    string kind
    string renewal_id_text
    json details
    string previous_hash
    string digest UK
  }
  AuditHead {
    bigint id PK
    string digest
  }
```

Las relaciones punteadas indican datos copiados o referencias lógicas, no claves foráneas. El evento conserva sus datos aunque cambie un catálogo. `Contribution` contiene nombre, importe y disponibilidad; `ShippingRate` contiene prefijo postal único, zona, importe y disponibilidad. `LookupThrottle` guarda hash de IP, ventana de cinco minutos y contador; no almacena la IP en claro.

Restricciones: licencia única por número; tabulador único por giro/año; un trámite por licencia/año; ID de pago único global; una carátula por trámite; sello único. Los importes usan Decimal y dos decimales. FK financieras usan PROTECT para evitar borrados de registros referenciados. El folio corto mostrado es una referencia legible; el identificador autoritativo del trámite es su UUID completo.

## 5. Flujo transaccional

```mermaid
sequenceDiagram
  actor C as Ciudadano
  participant D as Django
  participant B as Base de datos
  participant M as Mercado Pago
  C->>D: Consulta licencia + nombre
  D->>B: Validar padrón, riesgo y adeudos
  C->>D: Confirmar aportaciones + entrega
  D->>B: Bloquear licencia, recalcular y guardar snapshot
  C->>D: Iniciar pago
  D->>M: Crear preferencia con total del servidor
  M-->>C: Checkout alojado por proveedor
  M->>D: Webhook firmado (payment)
  D->>D: Validar HMAC + antigüedad de firma
  D->>M: GET pago con token privado
  D->>D: Comparar referencia, monto, moneda y entorno
  D->>B: Registrar pago, actualizar trámite y emitir sello
  D->>B: Agregar evento de auditoría
  C->>D: Descargar PDF / verificar QR
```

La URL de regreso no modifica el pago. Los duplicados son idempotentes; notificaciones anteriores a `provider_updated_at` se ignoran. Para varios pagos de una preferencia se conservan registros independientes. Un pago reembolsado o con contracargo invalida el documento si no queda otro pago aprobado. Más de un pago aprobado produce un evento de revisión para Tesorería; no se ordenan reembolsos automáticamente.

La preferencia se reutiliza para evitar generar múltiples checkouts por doble clic. Si el proveedor deja una preferencia no reutilizable, Tesorería debe reconciliar antes de habilitar un nuevo intento; no se recrea a ciegas una preferencia con deuda potencialmente pagada.

## 6. Seguridad y privacidad

- CSRF en formularios y API por sesión; solo el webhook firmado está exento.
- Sesión de una hora para consultar trámites del ciudadano; UUID por sí solo no autoriza el acceso.
- La consulta se basa en los dos datos exigidos por RF-01. Esto es una verificación débil por diseño del enunciado, no autenticación fuerte. Se limita a 20 intentos por IP y cinco minutos. No se confía en X-Forwarded-For arbitrario.
- Permisos separados: `view_renewal`, `change_renewal`, `view_auditevent`. Login y contraseñas gestionados por Django.
- CSP, DENY para frames, política de referente, cookies HttpOnly/SameSite y, en despliegue, Secure/HSTS.
- QR con **HMAC-SHA256**, no un SHA-256 sin secreto. El documento contiene los datos firmados y el servidor compara en tiempo constante. HMAC es autenticación simétrica; no es una firma electrónica avanzada ni acredita autoría legal municipal.
- Certificados y eventos: inserción permitida, UPDATE/DELETE bloqueados por triggers en SQLite/PostgreSQL. Una cadena HMAC permite detectar modificaciones e inconsistencias en su cabecera.
- Un administrador de base de datos puede desactivar triggers o restaurar una copia antigua. Para inmutabilidad frente a administradores se requieren permisos separados, exportación de sellos y almacenamiento WORM externo. No se promete esa garantía con una sola base local.
- La verificación pública omite razón social, dirección y teléfono de envío. Se exponen únicamente folio, número, nombre comercial, año y vigencia.
- Exportación CSV neutraliza celdas que podrían interpretarse como fórmulas.

## 7. Disponibilidad

Objetivo RNF-02: 99.5% mensual (aproximadamente 3 h 36 min de indisponibilidad en 30 días). No es una medición lograda.

El paquete usa archivos estáticos locales y una aplicación sin archivos de sesión locales; las sesiones viven en base de datos y permiten múltiples instancias con claves compartidas. Escalado objetivo: balanceador, dos o más instancias web, PostgreSQL administrado con alta disponibilidad, backups diarios, retención y prueba de restauración, monitoreo de `/salud/`, alerta ante fallos y conciliación de notificaciones perdidas. El Compose incluido es una instalación de pruebas de un solo host y no elimina ese punto único de falla.

A mayor carga, mover throttling a un almacén compartido con TTL; revisar retención de contadores y logs, bloqueos de auditoría, índices y tiempo de consulta al proveedor. SQLite es apropiado para la presentación local; PostgreSQL es el destino para concurrencia. No se realizaron pruebas de carga ni de SLA.
