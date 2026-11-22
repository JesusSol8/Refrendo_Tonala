# Implementación en la Nube AWS — Refrendo Tonalá

## 1. Guía de Despliegue (Infraestructura como Código)
El despliegue se realiza de forma 100% automatizada mediante AWS CLI y `cloud-init` (`UserData`), cumpliendo la restricción de cero creación manual de recursos en consola web:
1. Clonar el repositorio Git que contiene `infra/deploy_aws.sh`, `compose.aws.yaml` y `scripts/aws_s3_audit.py`.
2. Cargar las credenciales temporales de AWS Academy Learner Lab en la terminal o abrir **AWS CloudShell**.
3. Ejecutar `bash infra/deploy_aws.sh <URL_DEL_REPOSITORIO_GIT>`.
4. El script aprovisiona automáticamente:
   - Dos **Security Groups** con principio de menor privilegio (`web-sg` para 80/443/22 y `db-sg` restringiendo el puerto `5432` exclusivamente al grupo web).
   - Un bucket **Amazon S3** privado con versionado habilitado para resguardo externo de sellos de auditoría.
   - Una instancia **Amazon RDS PostgreSQL 16 (`db.t3.micro`)** sin exposición pública.
   - Una instancia **Amazon EC2 (`t3.small`)** asociada al perfil IAM `LabInstanceProfile`, que instala Docker, configura HTTPS automático (TLS 1.3 con Caddy y `sslip.io`), ejecuta migraciones, carga el padrón ficticio y exporta la primera evidencia de auditoría a S3.

## 2. Diagrama de Arquitectura y Flujo de Datos

```mermaid
flowchart LR
  U[Ciudadano / Evaluador] -->|HTTPS TLS 1.3 :443| C[Caddy Reverse Proxy]
  subgraph VPC[AWS VPC - Learner Lab]
    subgraph SG_WEB[Security Group: web-sg]
      subgraph EC2[Amazon EC2 t3.small - LabInstanceProfile]
        C --> W[Django 5.2 + Waitress :8000]
        S[scripts/aws_s3_audit.py]
      end
    end
    subgraph SG_DB[Security Group: db-sg :5432]
      RDS[(Amazon RDS PostgreSQL 16)]
    end
  end
  S3[(Amazon S3 - Versionado)]
  W -->|SQL / Transacciones ACID| RDS
  S -->|Verifica HMAC y sube JSON| S3