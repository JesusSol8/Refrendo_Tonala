# Decisiones, supuestos y fuentes

## Decisiones de alcance

1. **Académico:** el sistema funciona sin datos reales, dominio gubernamental ni cobros. Todos los ejemplos se identifican como ficticios.
2. **Monolito Django:** autenticación, permisos, formularios, ORM y migraciones integrados reducen complejidad y tiempo.
3. **Dos campos de consulta:** número/nombre no equivalen a identificación fuerte. Sesión y límite de consultas reducen exposición; una operación real debe revisar identidad y privacidad.
4. **Tabulador configurable:** catálogo por ejercicio/giro, con fuente y marca academic. Se rechazan pagos externos con tablas académicas. No se inventa un dictamen jurídico sobre todo el articulado.
5. **Aseo obligatorio vs aportación:** la Ley 2026 contempla residuos para ciertos giros y el SRS menciona aseo como ejemplo voluntario. Se separa el cargo obligatorio configurado de donaciones a Cruz Roja, Bomberos y mejora de espacios públicos. Confirmar interpretación con profesor y Tesorería.
6. **Tarifas demo:** bases papelería 680, artesanías 740, abarrotes 820 MXN; cédula 331, residuos configurados 674, recargos cero; aportaciones 25/30/20; envíos 95/120/160. Son datos académicos, no una liquidación tributaria certificada ni una oferta de paquetería. La norma contempla un periodo anual de refrendo; los recargos reales requieren reglas aprobadas. No se inventó una fórmula legal sin base suficiente.
7. **Mercado Pago Checkout Pro:** captura bancaria delegada al proveedor. Token privado exclusivamente en servidor.
8. **Webhooks:** HMAC, consulta autenticada del pago y control de monto/moneda/referencia. No se implementa IPN heredado sin autenticación de origen.
9. **QR HMAC:** un SHA-256 sin secreto se podría recalcular tras alterar datos. HMAC aporta autenticación simétrica; no es firma electrónica avanzada gubernamental.
10. **Carátula académica:** no se recibió formato oficial. Se creó un formato propio con datos esenciales, QR y marca visible sin validez oficial.
11. **Paquetería:** cotización por zonas y guía manual, sin compra de etiquetas ni convenio real.
12. **RNF:** código/configuración no prueban por sí solos un SLA ni conformidad integral WCAG; la RTM declara esos límites.

## Fuentes primarias consultadas el 5 de noviembre de 2026

- **SRS del profesor:** copia en REQUERIMIENTOS_ORIGINALES.md, utilizada como especificación del producto, no como autorización para publicar servicios o modificar cuentas externas.
- **Portal oficial de Tonalá:** https://tonala.gob.mx/portal/ . Referencia institucional; sus estilos usan Montserrat y Open Sans. No se certificó reproducción exacta del portal de Pago de Predial.
- **Logo:** https://tonala.gob.mx/portal/wp-content/uploads/2021/10/cropped-icono-1.png . Referencia del cliente simulado sin afirmar afiliación oficial.
- **Ley de Ingresos de Tonalá 2026**, decreto 30093/LXIV/25: https://congresoweb.congresojal.gob.mx/bibliotecavirtual/legislacion/Ingresos/Documentos_PDF-Ingresos/Ley%20de%20Ingresos%20del%20Municipio%20de%20Tonal%C3%A1,%20Jalisco%20para%20el%20ejercicio%20fiscal%202026-300126.pdf . Referencias acotadas: art. 13 (periodo), art. 61 numeral 5 (residuos) y art. 91 I c (cédula). No se certifica su aplicabilidad a cada licencia.
- **Mercado Pago, notificaciones Checkout Pro mediante Preferences API:** https://www.mercadopago.com.mx/developers/en/docs/checkout-pro-preferences/payment-notifications . Referencia para firma, consulta y evento payment.
- **Google Fonts:** Montserrat/Open Sans para uso local; licencias OFL incluidas en static/portal.

## Limitaciones técnicas conocidas

- No se recibió padrón real, reglas completas de recargos, clasificador oficial de riesgo ni tablas aprobadas.
- La creación de preferencia ocurre dentro de una transacción con timeout de red. Una interrupción entre aceptación externa y persistencia exige conciliación por external_reference. Para alto volumen se recomienda outbox/worker con reintentos persistentes; no se incluye una cola distribuida.
- Sin MFA ni identidad ciudadana adicional a los dos campos exigidos por el SRS.
- Sin correos, compra de guías, certificados oficiales, sellado de tiempo externo o firma electrónica municipal.
- Sin medición histórica de disponibilidad ni prueba de carga; Compose es un solo host.
- Sin llavero histórico para rotación: preservar claves durante la vida de documentos y bitácora.
- Mercado Pago se verificó mediante contratos controlados; faltan cuenta real, habilitación de medios y recepción por Internet.
