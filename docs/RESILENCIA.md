Pruebas de resiliencia de Refrendo Tonalá
El 23 de noviembre de 2026 se ejecutaron tres simulaciones controladas sobre el código del ZIP y se volvió a correr la suite de Django. El ambiente fue Windows, Python 3.12, Django 5.2.19, Waitress, HTTP en la interfaz local y una base SQLite temporal con siete licencias ficticias.
Resultados locales
ID	Falla o condición	Método	Resultado observado
R1	Tabla de licencias inaccesible	Se renombró temporalmente la tabla en una copia SQLite mientras el servidor seguía escuchando	/salud/ devolvió 200 → 503 (unavailable) → 200 al restaurarla
R2	Caída del proceso web	Se terminó Waitress y luego se inició manualmente con la misma base	Hubo pérdida de conexión y volvió HTTP 200. Las mismas siete licencias permanecieron disponibles
R3	Escritura de auditoría rechazada	Se sustituyó el cliente S3 por un doble local que primero devolvió AccessDenied y luego aceptó el reintento	La exportación falló sin escribir objetos y Django respondió 200. Al reintentar manualmente se verificó la cadena y se generaron dos claves JSON en memoria
R4	Regresión funcional	Se volvió a ejecutar la suite de Django	44 pruebas aprobadas, incluido el webhook con pasarela simulada indisponible y la confirmación repetida sin duplicar carátulas


Bitácora de ejecución local · Simulador · Guía de repetición y validación AWS
R5 · Prueba de recuperación manual en AWS
Momento	Evidencia observada
Antes	/salud/ respondió HTTP/2 200 con {"status":"ok"} por HTTPS a las 00:59:20 UTC del 25 de noviembre
Durante	Docker confirmó Stopped después de stop web. Caddy devolvió HTTP/2 502 en /salud/ a la 01:09:24 UTC. La pantalla principal también mostró 502
Después	Docker confirmó Started después de start web. /salud/ respondió HTTP/2 200 con {"status":"ok"} a la 01:14:42 UTC. La pantalla principal volvió a cargar en el mismo dominio


La prueba se realizó el 24 de noviembre, hora de Ciudad de México. El anexo del PDF contiene las capturas. Las horas documentan el momento de cada solicitud. La duración exacta de la caída y la persistencia de un folio quedan pendientes.
Validación pendiente en AWS
Escenario	Implementación revisada	Qué falta registrar
Reinicio automático de Django en EC2	Docker Compose configura restart: always y un chequeo de /salud/	Observar el contador de reinicios después de una falla del proceso, sin ejecutar un arranque manual
Detención y arranque de EC2 con otra IPv4	El ZIP incluye una tarea @reboot que calcula el dominio y vuelve a levantar Compose	IPv4 antes y después, certificado TLS en el dominio vigente y QR recién generado
Interrupción de Amazon RDS	La aplicación intenta una consulta a la tabla de licencias en /salud/. RDS se aprovisiona en una zona	Respuesta bajo interrupción real, recuperación de una consulta y persistencia de un trámite ficticio
Rechazo del perfil IAM o de S3	El script exporta un JSON histórico y otro de estado más reciente	Permisos del perfil y confirmación de los objetos en el bucket de laboratorio
Pérdida de instancia o datos	El script solicita un día de retención de respaldo en RDS y habilita el versionado de S3	Recuperación del host y restauración de un respaldo de RDS en un ambiente aislado


La copia revisada configura una sola EC2 y RDS sin Multi-AZ. RDS available y EC2 running se reportaron durante el despliegue anterior.