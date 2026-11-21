# Plan de pruebas

## Objetivo y entorno

Validar que el prototipo académico complete el refrendo sin manipulación de importes, que impida giros no elegibles y que solo emita documentos después del pago confirmado. Ejecución local: Windows, Python 3.12, Django 5.2, SQLite de pruebas aislada. Pagos externos mediante respuestas controladas; no se realizaron cobros reales.

## Niveles

1. **Servicios:** normalización, riesgo, cálculo decimal, cobertura, congelación e idempotencia.
2. **Integración Django/BD:** formularios, sesiones, permisos, disparadores append-only, estado de pago y emisión.
3. **Contrato de Mercado Pago:** firma válida/inválida, consulta del pago, importe incorrecto, referencia ajena, fallos transitorios y no confiar en back_url. El cliente externo se sustituye; esto no prueba la configuración real de una cuenta.
4. **Aceptación visual:** recorrido real desde navegador, actualización de aportaciones/envío, pago de prueba, verificación pública y renderizado del PDF a imagen.

## Escenarios de aceptación

| Caso | Acción | Resultado |
|---|---|---|
| CP-01 | Consultar TON-0001 con María López García | Licencia y liquidación disponibles |
| CP-02 | Nombre incorrecto o solo un campo | Mensaje sin autorizar la licencia |
| CP-03 | Consultar TON-0003 / 0004 | Bloqueo y dependencia específica |
| CP-04 | Consultar TON-0005 / 0006 | Inactiva / adeudo previo, sin continuar |
| CP-05 | Refrendo sin aportaciones en ventanilla | Total $1,685.00 para TON-0001 |
| CP-06 | Activar Cruz Roja | Suma $25.00; al quitarla resta el mismo importe |
| CP-07 | Elegir envío CP 45400 / 45410 | Suma $95.00 / $120.00 respectivamente |
| CP-08 | Enviar CP 99999 o dirección incompleta | Rechazo; no guarda trámite |
| CP-09 | Manipular total enviado a 0.01 | Servidor conserva cálculo correcto |
| CP-10 | Confirmar dos veces | Solo un trámite por licencia/año |
| CP-11 | Pagar como pendiente | No hay PDF; indica esperar acreditación |
| CP-12 | Aprobar pago pendiente | Estado pagado, carátula y QR disponibles |
| CP-13 | Repetir aprobación y webhook | No duplica certificado ni evento idéntico |
| CP-14 | Firma falsa, antigua o sin secreto | Webhook 401; no consulta proveedor |
| CP-15 | Firma válida, monto incorrecto o moneda distinta | No se aplica el pago |
| CP-16 | Proveedor inaccesible temporalmente | Webhook 503 para permitir reintento |
| CP-17 | Otro navegador abre UUID del trámite | No expone datos ni PDF |
| CP-18 | QR correcto / sello alterado | Auténtico / no válido |
| CP-19 | Pago reembolsado | Documento no válido; bloquea nueva descarga |
| CP-20 | Editar/borrar bitácora o certificado vía ORM | Base de datos rechaza la mutación |
| CP-21 | Alterar cabecera de auditoría en prueba aislada | verify_audit detecta inconsistencia |
| CP-22 | Usuario sin permiso abre gestión/bitácora | 403 |
| CP-23 | Operador de entrega cambia licencia no pagada | Rechazo |
| CP-24 | Envío sin guía o ventanilla marcada enviada | Rechazo |
| CP-25 | Exportar conciliación autorizado | CSV con pagos, folios, importes y dirección |
| CP-26 | Cambio de año/vigencia del QR | Muestra vencimiento; no promete nueva vigencia |
| CP-27 | Recorrido móvil y formulario con etiquetas | Controles visibles y operables, sin desbordamiento de tarjetas |
| CP-28 | PDF generado | Una página legible en el ejemplo; sin recortes ni superposición |

CP-26 también está cubierto por expired_document_still_authenticated_but_not_current, que fija una fecha posterior a la vigencia. La auditoría completa WCAG, lectores de pantalla, teléfonos físicos y carga distribuida quedan pendientes.

## Ejecución repetible

```text
python manage.py collectstatic --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test refrendo --verbosity 2
python manage.py verify_audit
```

Los tests usan una base separada y no necesitan borrar los datos de presentación. No usar el padrón de pruebas contra un ambiente municipal. `.github/workflows/ci.yml` automatiza la suite cuando se publique el repositorio; el CI remoto no se ha ejecutado.

## Criterios de salida

- Suite completa sin errores y sin migraciones faltantes.
- Ningún PDF disponible antes del pago.
- Liquidación igual al total guardado y al importe conciliado.
- Reintentos no generan carátulas duplicadas.
- Bitácora verificable después del flujo aprobado.
- Interfaz y PDF revisados visualmente.
- Pendientes externos declarados en la RTM; no confundir pruebas controladas con certificación de Mercado Pago.

El registro exacto de la última suite ejecutada se conserva en RESULTADOS_PRUEBAS.txt. La carátula de ejemplo y la captura entregadas corresponden a una demostración real del prototipo local.

