Guía para pruebas de resiliencia en AWS

Esta guía es un procedimiento para que el equipo lo ejecute durante una sesión de laboratorio. Las pruebas de reinicio interrumpen temporalmente el sitio. No las ejecutes durante una demostración activa ni con datos reales. **Todas las pruebas de esta guía están pendientes** salvo que el equipo complete y registre cada resultado.

## Preparación y evidencia

1. Inicia Learner Lab y confirma en CloudShell la región `us-east-1`.
2. Consulta y registra los estados de EC2 y RDS. Obtén la IP pública actual con AWS CLI y abre `https://<IP>.sslip.io/salud/`.
3. Comprueba que la pantalla principal carga, guarda la URL inicial, el código HTTP, hora local y hora UTC.
4. Mantén lista una segunda terminal de CloudShell. No copies a un informe la contraseña de RDS, el `.env`, credenciales temporales, llaves SSH ni datos de sesión.

## Prueba A: caída del contenedor web

Por SSH a EC2, comprueba los contenedores:

```bash
cd /opt/refrendo-tonala
docker compose -f compose.aws.yaml ps
```

Detén solo el contenedor de Django y observa recuperación automática:

```bash
docker compose -f compose.aws.yaml kill web
sleep 10
docker compose -f compose.aws.yaml ps
curl -i --max-time 15 -H 'Host: localhost' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/salud/
```

Revisa el log de Caddy y Django. Éxito significa que el contenedor vuelve a estar activo y una petición HTTP a `/salud/` recibe respuesta satisfactoria después de la interrupción. Registra el tiempo de recuperación. El script recibido `scripts/simulate_resilience.sh` no sustituye este chequeo porque actualmente no valida explícitamente el código HTTP.

## Prueba B: reinicio de EC2 y cambio de URL

Registra IP y respuesta antes. Desde CloudShell, reinicia EC2 usando el ID obtenido, nunca un ID inventado:

```bash
aws ec2 reboot-instances --region us-east-1 --instance-ids <i-INSTANCE_ID>
aws ec2 wait instance-status-ok --region us-east-1 --instance-ids <i-INSTANCE_ID>
aws ec2 describe-instances --region us-east-1 --instance-ids <i-INSTANCE_ID> \
  --query 'Reservations[0].Instances[0].[State.Name,PublicIpAddress]' --output table
```

Si la IP no cambió, documenta que esta prueba no simuló una liberación de IPv4. No detengas o termines la instancia para forzar el cambio sin planear la interrupción y revisar el efecto en el volumen y otros recursos. Cuando haya una IP nueva, espera el arranque, actualiza la URL y prueba `/salud/` y la página inicial. Registra que el certificado TLS funciona en el dominio nuevo. La configuración automática está escrita; no hay evidencia de ejecución previa de este escenario.

## Prueba C: disponibilidad y persistencia de RDS tras reiniciar la web

Después de que EC2 vuelva a responder, consulta RDS desde CloudShell y verifica el sitio. Haz un cambio no sensible en datos demo solo si el equipo ya estableció un caso de prueba seguro; vuelve a consultarlo tras el reinicio. No borres ni modifiques registros financieros para forzar el escenario. El objetivo es confirmar persistencia en RDS, no una alta disponibilidad que el diseño no incluye.

## Prueba D: interrupción de RDS (opcional, riesgo de indisponibilidad)

Solo con aprobación del equipo y fuera de una demostración, detén RDS temporalmente desde AWS CLI o causa una interrupción controlada, registra el inicio y observa el comportamiento del sitio. Restablece la instancia y espera `available`; después verifica `/salud/`, una lectura y una operación de escritura con datos ficticios. No hay failover Multi-AZ configurado. No afirmes que la aplicación “no se rompe”; la expectativa honesta es que pierda temporalmente la función que necesita base de datos y que recupere servicio cuando RDS esté disponible.

## Prueba E: exportación de evidencia S3

Desde EC2, confirma el perfil IAM y ejecuta el exportador de auditoría:

```bash
cd /opt/refrendo-tonala
docker compose -f compose.aws.yaml exec -T web python scripts/aws_s3_audit.py
```

Comprueba que el comando informa integridad válida y una clave de objeto de auditoría. Confirma la clave en S3 con AWS CLI, ocultando nombre de cuenta y datos sensibles. No elimines versiones para simular una falla. La exportación de evidencia no demuestra por sí sola una recuperación ante desastre ni retención inmutable.

## Registro de resultados

Completa una fila después de cada ejecución y adjunta capturas o salidas redactadas:

| Fecha | Escenario | Estado antes | Acción | HTTP/duración | Estado después | Resultado/evidencia |
|---|---|---|---|---|---|---|
| Pendiente | Caída de contenedor web | — | — | — | — | No ejecutada |
| Pendiente | Reinicio EC2/IP/HTTPS | — | — | — | — | No ejecutada |
| Pendiente | Persistencia RDS | — | — | — | — | No ejecutada |
| Pendiente | Exportación S3 | — | — | — | — | No ejecutada |
| Pendiente | Interrupción RDS (opcional) | — | — | — | — | No ejecutada |
