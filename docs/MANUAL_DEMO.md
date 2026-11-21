# Manual de uso y guion de exposición

## Preparación

Abre INICIAR.cmd con antelación. Prueba el inicio y conserva abierta la ventana. Si usas el proyecto ya preparado en esta conversación, la URL local se encuentra activa mientras siga ejecutándose el servidor. Si se cierra, vuelve a iniciar el proyecto.

En el paquete ZIP no se incluye una base de datos con contraseñas. El primer inicio aplica migraciones, carga el padrón ficticio y genera una cuenta local. Lee `.demo-access.txt` dentro de la carpeta del proyecto. Para una cuenta convencional ejecuta `python manage.py createsuperuser`.

## Datos ficticios

| Número | Nombre exacto | Resultado esperado |
|---|---|---|
| TON-0001 | María López García | Papelería elegible |
| TON-0002 | Artesanías del Sol SA de CV | Artesanías elegibles |
| TON-0003 | Comercial La Plaza SA de CV | Detiene y deriva a Protección Civil |
| TON-0004 | Taller El Roble SA de CV | Detiene y deriva a Ecología e Inspección |
| TON-0005 | Juan Pérez Ruiz | Licencia inactiva |
| TON-0006 | Ana Torres Díaz | Ejercicios anteriores pendientes |
| TON-0007 | Luis Ramírez Soto | Abarrotes elegibles |

Se aceptan variaciones de mayúsculas, espacios y acentos; el nombre debe coincidir completo. Los domicilios y nombres son ficticios. Para entrega escribe un destinatario ficticio, Calle de Demostración, 123, Centro, CP 45400, Tonalá, Jalisco y un teléfono ficticio de diez dígitos.

## Guion de 8 a 12 minutos

1. **Problema (1 min):** el ciudadano necesita renovar su licencia sin filas y obtener un documento verificable. Solo se permite el flujo digital para giros que no requieren inspección previa.
2. **Filtro (1 min):** consulta TON-0003; muestra la dependencia requerida. Usa un nombre incorrecto y muestra que no se autoriza el acceso.
3. **Consulta (1 min):** consulta TON-0001. Explica que el padrón se simula porque no se recibió una BD municipal.
4. **Liquidación (2 min):** muestra los conceptos y el total inicial de $1,685.00. Marca Cruz Roja: $1,710.00. Selecciona envío CP 45400: $1,805.00. Quita la aportación y muestra el cambio. Un CP 99999 produce falta de cobertura. Puedes volver a ventanilla sin dirección.
5. **Confirmación (1 min):** completa datos, acepta el aviso y confirma. Explica que se guarda un snapshot y que cambiar el total en el navegador no altera el cobro del servidor.
6. **Pago (1 min):** simula SPEI pendiente y regresa. Aún no hay PDF. Reabre el pago de demostración y aprueba el mismo pago; aparece el documento. No ingreses tarjetas reales.
7. **Documento (1 min):** descarga el PDF, muestra folio, licencia, vigencia, marca académica, QR y sello. Abre “Verificar documento”. Modifica un carácter del sello: debe indicar no válido.
8. **Operación (1 min):** ingresa al admin y abre `/gestion/`. Muestra registro, CSV, bitácora y estado logístico. Marca lista en ventanilla o enviada con guía, según la modalidad seleccionada.
9. **Cierre técnico (1 min):** presenta el DER, matriz RTM, pruebas y las dependencias externas pendientes de validar.

Si TON-0001 ya tiene un trámite, el portal lo recupera en lugar de cobrar nuevamente. Usa TON-0002 o TON-0007 para un flujo nuevo. Para reiniciar una demostración completa, conserva primero una copia de la base y de las claves, detén el servidor y usa otra carpeta del proyecto extraída del ZIP. No borres registros financieros individuales para forzar un nuevo pago.

## Preguntas que conviene saber responder

**¿Por qué Django?** Integra formularios, sesiones, permisos, ORM, migraciones y administración; permite concentrarse en las reglas de negocio y probar el flujo dentro del plazo.

**¿Dónde está el cálculo?** En `services.quote()`. Obtiene tarifas del ejercicio/giro y aportaciones activas, agrega el envío por el prefijo postal más específico y suma con Decimal. El servidor vuelve a calcular antes de guardar.

**¿Qué confirma el pago?** El webhook autenticado, seguido de una consulta al API privado del proveedor. La pantalla de regreso no es prueba de pago.

**¿Qué pasa si llega dos veces el webhook?** Se identifica el pago por ID único y fecha del proveedor. No duplica certificado ni movimiento idéntico.

**¿Qué hace el QR?** Abre una URL con el sello. El servidor comprueba firma y pago vigente. El sello no contiene datos personales legibles.

**¿Es un sistema oficial terminado?** Es un entregable académico funcional. La validación de tarifas, habilitación real del proveedor, identidad exacta, dominio oficial y SLA requieren intervención municipal y pruebas externas. Señalarlo con claridad demuestra control de alcance.

**¿Puede escanearlo el profesor desde su teléfono?** El QR local de 127.0.0.1 funciona únicamente en la computadora anfitriona. Para teléfono configura PUBLIC_BASE_URL con la URL HTTPS pública de pruebas antes de generar nuevos PDFs; consulta DESPLIEGUE.md.

**¿Por qué la bitácora no se puede editar?** La aplicación y la base impiden UPDATE/DELETE. Los eventos se encadenan con HMAC. Un administrador de infraestructura sigue siendo una autoridad privilegiada; para defenderse de él hace falta anclaje externo.

## Problemas frecuentes

- **Puerto 8000 ocupado:** usa el servidor que ya esté abierto o detén el anterior antes de abrir otro.
- **No hay Internet al primer inicio:** instala antes de clase; las dependencias no están incluidas dentro del ZIP.
- **Firma inválida tras reiniciar:** verifica que estás usando la misma DOCUMENT_SIGNING_KEY y AUDIT_KEY. No mezcles bootstrap con comandos manuales sin sus claves.
- **El envío no cotiza:** usa un CP de cinco dígitos con cobertura, por ejemplo 45400.
- **El admin pide acceso:** lee `.demo-access.txt` o crea un superusuario. Las credenciales no se publican en el código.
- **El pago real no aparece:** revisa firma, URL HTTPS, aplicación del proveedor y usa `reconcile_payment` con el ID real para recuperar una notificación perdida.
