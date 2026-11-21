# API REST v1

Rutas relativas al dominio configurado. Consultas ciudadanas usan cookie de sesión y CSRF. No constituyen una API pública anónima de acceso a domicilios del padrón. Obtén primero una cookie/token CSRF desde GET `/`. Cualquier POST de navegador debe enviar `X-CSRFToken` o el campo `csrfmiddlewaretoken` del formulario.

| Método y ruta | Entrada | Salida / estado |
|---|---|---|
| POST `/api/v1/licencias/consulta/` | JSON o formulario: `number`, `taxpayer` | 200: número, nombre comercial, giro, eligible y next; 400: datos inválidos; 429: límite de consultas |
| POST `/api/v1/cotizacion/` | Form-urlencoded: `contributions` repetido por ID, delivery pickup/shipping y postal_code | 200: items, total decimal como string, año y fundamento; 400 sin cobertura o catálogo inválido; requiere licencia autorizada en sesión |
| GET `/api/v1/tramites/{uuid}/` | Cookie de sesión con la licencia autorizada | status, label y paid; 404 sin autorización |
| POST `/api/v1/mercadopago/webhook/` | Query data.id, encabezados x-signature y x-request-id; JSON type/payment y data.id | 200 aplicado/idempotente; 401 firma; 400 incongruencia; 503 fallo transitorio; 404 en modo demo |
| GET `/verificar?hash={sello}` | Sello de 64 caracteres | HTML público con autenticidad/vigencia; 404 no válido; no expone dirección/teléfono |
| GET `/salud/` | Ninguna | 200 servicio/BD disponible; 503 fallo BD |

La creación y el pago de trámites se realizan mediante formularios POST `/liquidacion/` y `/tramite/{uuid}/pagar/` que redirigen con PRG (Post/Redirect/Get). La API no recibe un importe libre: el servidor calcula desde catálogos. La consulta de estado se limita a la sesión autorizada, y el front la actualiza cada diez segundos por un periodo limitado.

Ejemplo de consulta (obteniendo antes CSRF y cookie):

```json
{"number":"TON-0001","taxpayer":"María López García"}
```

Ejemplo de respuesta:

```json
{"license":"TON-0001","trade_name":"Papelería La Ilusión","business_type":"Papelería y artículos de oficina","eligible":true,"next":"/liquidacion/"}
```

El padrón está en la BD de demostración y se accede por ORM dentro del servicio de negocio. Una futura API municipal autenticada debe adaptarse en ese límite y contar con un contrato de datos real; no se inventó una conexión a un sistema del Ayuntamiento.
