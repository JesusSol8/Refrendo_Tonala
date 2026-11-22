#!/usr/bin/env bash
set -euo pipefail

# ================= CONFIGURACIÓN =================
REGION="us-east-1"
PROJECT="refrendo-tonala"
REPO_URL="${1:-https://github.com/JesusSol8/Refrendo_Tonala.git}"
KEY_NAME="${PROJECT}-key"
DB_USER="refrendo"
DB_NAME="refrendo"
DB_PASS=$(openssl rand -hex 16)
ADMIN_USER="admin_tonala"
ADMIN_PASS=$(openssl rand -hex 10)

echo "=== Verificando sesión activa de AWS Learner Lab ==="
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="${PROJECT}-respaldos-${ACCOUNT_ID}"
echo "Cuenta AWS: ${ACCOUNT_ID} | Región: ${REGION}"

echo "=== 1. Creando par de llaves SSH (${KEY_NAME}.pem) ==="
aws ec2 delete-key-pair --region "$REGION" --key-name "$KEY_NAME" >/dev/null 2>&1 || true
rm -f "${KEY_NAME}.pem"
aws ec2 create-key-pair --region "$REGION" --key-name "$KEY_NAME" \
  --query 'KeyMaterial' --output text > "${KEY_NAME}.pem"
chmod 400 "${KEY_NAME}.pem"

echo "=== 2. Configurando Security Groups en VPC por defecto ==="
VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' --output text)

WEB_SG=$(aws ec2 create-security-group --region "$REGION" \
  --group-name "${PROJECT}-web-sg-$(date +%s)" \
  --description "Acceso HTTP/HTTPS/SSH para Refrendo Tonala" \
  --vpc-id "$VPC_ID" --query 'GroupId' --output text)

for PORT in 22 80 443; do
  aws ec2 authorize-security-group-ingress --region "$REGION" \
    --group-id "$WEB_SG" --protocol tcp --port "$PORT" --cidr 0.0.0.0/0 >/dev/null
done

DB_SG=$(aws ec2 create-security-group --region "$REGION" \
  --group-name "${PROJECT}-db-sg-$(date +%s)" \
  --description "Acceso PostgreSQL exclusivo desde Web SG" \
  --vpc-id "$VPC_ID" --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress --region "$REGION" \
  --group-id "$DB_SG" --protocol tcp --port 5432 --source-group "$WEB_SG" >/dev/null

echo "=== 3. Creando Bucket S3 con versionado y bloqueo público (${BUCKET_NAME}) ==="
aws s3api create-bucket --region "$REGION" --bucket "$BUCKET_NAME" >/dev/null 2>&1 || true
aws s3api put-bucket-versioning --region "$REGION" --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled
aws s3api put-public-access-block --region "$REGION" --bucket "$BUCKET_NAME" \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "=== 4. Creando instancia Amazon RDS PostgreSQL 16 (db.t3.micro) ==="
aws rds create-db-instance --region "$REGION" \
  --db-instance-identifier "${PROJECT}-db" \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16.3 \
  --master-username "$DB_USER" \
  --master-user-password "$DB_PASS" \
  --db-name "$DB_NAME" \
  --allocated-storage 20 \
  --vpc-security-group-ids "$DB_SG" \
  --no-publicly-accessible \
  --backup-retention-period 1 >/dev/null

echo "Esperando disponibilidad de RDS (tarda ~4-6 minutos)..."
aws rds wait db-instance-available --region "$REGION" --db-instance-identifier "${PROJECT}-db"
DB_ENDPOINT=$(aws rds describe-db-instances --region "$REGION" \
  --db-instance-identifier "${PROJECT}-db" \
  --query 'DBInstances[0].Endpoint.Address' --output text)
echo "RDS activo en: ${DB_ENDPOINT}"

echo "=== 5. Lanzando instancia EC2 (t3.small) con despliegue automatizado ==="
AMI_ID=$(aws ssm get-parameter --region "$REGION" \
  --name /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id \
  --query 'Parameter.Value' --output text)

cat <<EOF > user_data.sh
#!/bin/bash
set -euxo pipefail
apt-get update -y
apt-get install -y docker.io docker-compose-v2 git curl
systemctl enable --now docker

git clone "${REPO_URL}" /opt/refrendo-tonala
cd /opt/refrendo-tonala

cat <<ENV > .env
DEBUG=0
DEMO_MODE=1
REFRENDO_YEAR=2026
TRUST_PROXY=1
PUBLIC_HOST=placeholder.sslip.io
PUBLIC_BASE_URL=https://placeholder.sslip.io
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://placeholder.sslip.io
SECRET_KEY=$(openssl rand -hex 32)
DOCUMENT_SIGNING_KEY=$(openssl rand -hex 32)
AUDIT_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgres://${DB_USER}:${DB_PASS}@${DB_ENDPOINT}:5432/${DB_NAME}
S3_BACKUP_BUCKET=${BUCKET_NAME}
AWS_DEFAULT_REGION=${REGION}
ENV

# Script que actualiza IP pública, sslip.io y certificado HTTPS en cada arranque
cat <<'REFRESH' > /usr/local/bin/refresh-refrendo-ip.sh
#!/bin/bash
set -euo pipefail
cd /opt/refrendo-tonala
TOKEN=\$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" || true)
if [ -n "\$TOKEN" ]; then
  PUBLIC_IP=\$(curl -s -H "X-aws-ec2-metadata-token: \$TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)
else
  PUBLIC_IP=\$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
fi
DOMAIN="\${PUBLIC_IP}.sslip.io"
sed -i "s|^PUBLIC_HOST=.*|PUBLIC_HOST=\${DOMAIN}|" .env
sed -i "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=https://\${DOMAIN}|" .env
sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=\${DOMAIN},\${PUBLIC_IP},localhost,127.0.0.1|" .env
sed -i "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://\${DOMAIN}|" .env
docker compose -f compose.aws.yaml up -d --build
echo "Portal activo en: https://\${DOMAIN}" > /etc/motd
REFRESH
chmod +x /usr/local/bin/refresh-refrendo-ip.sh
echo "@reboot root /usr/local/bin/refresh-refrendo-ip.sh >> /var/log/refrendo-boot.log 2>&1" > /etc/cron.d/refrendo-ip

/usr/local/bin/refresh-refrendo-ip.sh

# Inicializar datos demo, superusuario y primera auditoría hacia S3
docker compose -f compose.aws.yaml exec -T web python manage.py seed_demo
docker compose -f compose.aws.yaml exec -T -e DJANGO_SUPERUSER_USERNAME="${ADMIN_USER}" \
  -e DJANGO_SUPERUSER_EMAIL="admin@tonala.local" \
  -e DJANGO_SUPERUSER_PASSWORD="${ADMIN_PASS}" \
  web python manage.py createsuperuser --noinput || true
docker compose -f compose.aws.yaml exec -T web python scripts/aws_s3_audit.py

cat <<CREDS > /opt/refrendo-tonala/.admin-credentials.txt
Usuario Admin: ${ADMIN_USER}
Contraseña   : ${ADMIN_PASS}
CREDS
chmod 600 /opt/refrendo-tonala/.admin-credentials.txt
EOF

INSTANCE_ID=$(aws ec2 run-instances --region "$REGION" \
  --image-id "$AMI_ID" \
  --instance-type t3.small \
  --key-name "$KEY_NAME" \
  --security-group-ids "$WEB_SG" \
  --iam-instance-profile Name=LabInstanceProfile \
  --user-data file://user_data.sh \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${PROJECT}-web}]" \
  --query 'Instances[0].InstanceId' --output text)

aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE_ID"
PUBLIC_IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
rm -f user_data.sh

echo "============================================================"
echo "INFRAESTRUCTURA DESPLEGADA EXITOSAMENTE (Espera ~2 min para build Docker)"
echo "URL Pública HTTPS : https://${PUBLIC_IP}.sslip.io"
echo "Healthcheck       : https://${PUBLIC_IP}.sslip.io/salud/"
echo "Usuario Admin     : ${ADMIN_USER}"
echo "Contraseña Admin  : ${ADMIN_PASS}"
echo "Acceso SSH        : ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP}"
echo "Bucket S3         : s3://${BUCKET_NAME}"
echo "Endpoint RDS      : ${DB_ENDPOINT}"
echo "============================================================"