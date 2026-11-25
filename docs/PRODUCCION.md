# Preparación de Refrendo Tonalá para producción

La instalación entregada corresponde a AWS Academy Learner Lab. Mantiene activos los datos y pagos de demostración. Los siguientes controles se aplican primero en un entorno de pruebas separado antes de incorporar datos o cobros reales.

| Área | Cambio requerido | Evidencia de aceptación |
|---|---|---|
| Código y despliegue | Fijar el despliegue a un commit o una imagen de contenedor identificada por digest. Declarar redes, cómputo, RDS, alertas e IAM con una plantilla versionada | Despliegue repetible desde un entorno vacío y reversión a la versión anterior ensayada |
| Acceso | Dominio propio y certificado administrado. Acceso de administración por Systems Manager si el entorno lo permite. Subredes privadas para web y datos detrás de un balanceador público | Validación HTTPS del dominio y reglas verificadas. PostgreSQL accesible solo desde el servicio web |
| Credenciales | Retirar contraseñas de User Data y archivos de arranque. Obtener secretos desde AWS Secrets Manager con un rol limitado. Dar a Django una cuenta PostgreSQL propia con permisos limitados | La aplicación se inicia con el rol asignado y los registros de arranque carecen de secretos. Las claves HMAC de documentos y auditoría tienen plan de custodia y rotación |
| Disponibilidad | Dos instancias web en zonas diferentes, balanceador, RDS Multi-AZ y alertas. Usar una prueba funcional externa además del chequeo `/salud/` | Se interrumpe una instancia web durante un ensayo y se comprueba el flujo de consulta. Las alertas llegan al operador |
| Respaldos | Definir retención y objetivos de pérdida de datos y recuperación. Conservar snapshots de RDS según la política. Limitar y registrar el acceso al bucket de auditoría | Se restaura una copia de RDS en un entorno aislado y se verifica un folio y su documento. Los JSON de S3 conservan evidencia de auditoría |
| Pago e identidad | Validar el padrón, autorización de uso de datos, aviso de privacidad y permisos. Probar el proveedor en su entorno de pruebas, conciliación, reintentos y aprobación repetida | Las pruebas cubren pago pendiente, aprobado y rechazado. La conciliación encuentra la referencia y la aprobación repetida conserva una carátula |
| Operación | Registrar responsables, tiempos de respuesta, instrucciones de recuperación, presupuesto y revisión de registros | Simulación documentada de caída, guardia asignada y revisión del presupuesto con el dimensionamiento de producción |

La estimación anual del PDF corresponde a la topología académica actual. Para presupuestar esta propuesta hay que recalcular EC2, balanceador, RDS Multi-AZ, red, respaldos, métricas y transferencia.

## Despliegue desde Git

La copia de entrega conserva el código y `infra/deploy_aws.sh` del ZIP original. Al integrar los documentos en una copia de trabajo del repositorio, conserva su historial y revisa el cambio antes de publicarlo. Verifica desde una sesión sin autenticación que el evaluador pueda leer el repositorio, o configura su acceso si es privado.

En el ZIP base se identifican tres commits del 21 de noviembre de 2026. `eb98689` corresponde al portal, `811182c` a la integración AWS y `d57ca4e` a la especificación de despliegue. El documento original `GESTION_PROYECTO.md` contiene el desglose y el cronograma propuesto. Para acreditar el periodo de trabajo, anexa evidencia fechada del equipo, como avances, tareas o revisiones. Los tres commits documentan los hitos registrados.