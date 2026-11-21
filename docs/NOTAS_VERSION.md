# Versión 1.0.0 · Entrega académica

## Contenido

Consulta ciudadana, filtro de elegibilidad, liquidación decimal, aportaciones, envío, pagos demostrables, integración configurable Mercado Pago, webhooks firmados, PDF/QR, verificación pública, permisos, logística, conciliación y bitácora de solo adición.

## Validación

- 44 pruebas automatizadas aprobadas en Windows/Python 3.12/SQLite.
- Django check sin observaciones y sin migraciones faltantes.
- Recorrido real en navegador: consulta, aportación, envío, pago aprobado y verificación.
- PDF de ejemplo renderizado y revisado visualmente.
- Integridad de la bitácora local verificada.

## Dependencias pendientes de un entorno externo

No se probaron credenciales reales de Mercado Pago, conexión al padrón municipal, tarifas oficiales completas, dominio oficial, TLS en servidor público, SLA 99.5% ni auditoría integral WCAG. Docker Desktop no tenía disponible su motor durante esta revisión. Consultar RTM y DESPLIEGUE.
