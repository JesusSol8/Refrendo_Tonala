Pruebas de Resistencia en AWS
Los ensayos de AWS Academy Learner Lab terminaron con éxito, según el registro del equipo. Consulta los procedimientos en la guía de pruebas.
R5 · Prueba de recuperación manual en AWS
Momento	Evidencia observada
Antes	/salud/ respondió HTTP/2 200 con {"status":"ok"} por HTTPS a las 00:59:20 UTC del 25 de noviembre
Durante	Docker confirmó Stopped después de stop web. Caddy devolvió HTTP/2 502 en /salud/ a la 01:09:24 UTC. La pantalla principal también mostró 502
Después	Docker confirmó Started después de start web. /salud/ respondió HTTP/2 200 con {"status":"ok"} a la 01:14:42 UTC. La pantalla principal volvió a cargar en el mismo dominio


La prueba se realizó el 24 de noviembre, hora de Ciudad de México. El anexo del PDF contiene las capturas. Las horas documentan el momento de cada solicitud. La duración exacta de la caída no consta en esas capturas.
Resultados de los demás ensayos en AWS
Registro de resultados comunicado por el equipo el 25 de noviembre de 2026.
ID	Escenario	Resultado reportado
R6	Reinicio automático de Django en EC2	Exitoso
R7	Detención y arranque de EC2, cambio de IPv4 y comprobación HTTPS	Exitoso
R8	Interrupción de Amazon RDS, recuperación y persistencia de un trámite	Exitoso
R9	Exportación de auditoría a Amazon S3	Exitosa
R10	Recuperación del host y restauración desde respaldo	Exitosas
R11	Ensayo de carga	Exitoso


La copia revisada configura una sola EC2 y RDS sin Multi-AZ. RDS available y EC2 running se reportaron durante el despliegue anterior.