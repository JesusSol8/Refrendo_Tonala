#!/usr/bin/env bash
set -euo pipefail
umask 077

export AWS_PAGER=""

REGION="${AWS_DEFAULT_REGION:-us-east-1}"
PROJECT="refrendo-tonala"

REPO_URL="${1:-https://github.com/JesusSol8/Refrendo_Tonala.git}"

STAMP=$(date +%s)
KEY_NAME="${PROJECT}-key-${STAMP}"

DB_ID="${PROJECT}-db"
DB_NAME="refrendo"
DB_USER="refrendo"
DB_PASS=$(openssl rand -hex 24)

ADMIN_USER="admin_tonala"
ADMIN_PASS=$(openssl rand -hex 16)

SECRET_KEY=$(openssl rand -hex 32)
DOCUMENT_SIGNING_KEY=$(openssl rand -hex 32)
AUDIT_KEY=$(openssl rand -hex 32)

SSH_CIDR="${SSH_CIDR:-$(curl -fsS https://checkip.amazonaws.com | tr -d '\r\n')/32}"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Verificar credenciales temporales de AWS Learner Lab.

ACCOUNT_ID=$(aws sts get-caller-identity \
    --query Account \
    --output text)

echo "Cuenta AWS: $ACCOUNT_ID"
echo "Región: $REGION"

if [[ ! "$REPO_URL" =~ ^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$ ]]; then
    echo "ERROR: Proporciona una URL válida de GitHub."
    exit 1
fi

# No sobrescribir ni eliminar una base de datos existente.

EXISTING_DB=$(aws rds describe-db-instances \
    --region "$REGION" \
    --query "DBInstances[?DBInstanceIdentifier=='${DB_ID}'].DBInstanceIdentifier" \
    --output text)

if [ -n "$EXISTING_DB" ] && [ "$EXISTING_DB" != "None" ]; then
    echo "ERROR: Ya existe ${DB_ID}."
    echo "Actualiza la instancia EC2 existente para conservar los datos."
    exit 1
fi

# Seleccionar una versión PostgreSQL 16 disponible en Amazon RDS.

DB_VERSION=$(aws rds describe-orderable-db-instance-options \
    --region "$REGION" \
    --engine postgres \
    --db-instance-class db.t3.micro \
    --query 'OrderableDBInstanceOptions[].EngineVersion' \
    --output text |
    tr '\t' '\n' |
    awk '/^16\.[0-9]+$/' |
    sort -Vu |
    tail -n 1)

if [ -z "$DB_VERSION" ]; then
    echo "ERROR: PostgreSQL 16 no disponible para db.t3.micro."
    exit 1
fi

echo "PostgreSQL seleccionado: $DB_VERSION"

# Obtener VPC por defecto.

VPC_ID=$(aws ec2 describe-vpcs \
    --region "$REGION" \
    --filters Name=isDefault,Values=true \
    --query 'Vpcs[0].VpcId' \
    --output text)

if [ -z "$VPC_ID" ] || [ "$VPC_ID" = "None" ]; then
    echo "ERROR: No existe una VPC por defecto."
    exit 1
fi

# Obtener subredes.

mapfile -t SUBNETS < <(
    aws ec2 describe-subnets \
        --region "$REGION" \
        --filters \
            Name=vpc-id,Values="$VPC_ID" \
            Name=default-for-az,Values=true \
        --query 'Subnets[?State==`available`].SubnetId' \
        --output text |
        tr '\t' '\n'
)

if [ "${#SUBNETS[@]}" -lt 2 ]; then
    echo "ERROR: RDS requiere subredes en dos zonas de disponibilidad."
    exit 1
fi

PUBLIC_SUBNET="${SUBNETS[0]}"

# Crear llave SSH sin eliminar llaves anteriores.

aws ec2 create-key-pair \
    --region "$REGION" \
    --key-name "$KEY_NAME" \
    --query KeyMaterial \
    --output text > "${KEY_NAME}.pem"

chmod 400 "${KEY_NAME}.pem"

# Security Group para EC2.

WEB_SG=$(aws ec2 create-security-group \
    --region "$REGION" \
    --group-name "${PROJECT}-web-${STAMP}" \
    --description "Refrendo Tonala HTTP HTTPS SSH" \
    --vpc-id "$VPC_ID" \
    --query GroupId \
    --output text)

for PORT in 80 443; do
    aws ec2 authorize-security-group-ingress \
        --region "$REGION" \
        --group-id "$WEB_SG" \
        --protocol tcp \
        --port "$PORT" \
        --cidr 0.0.0.0/0 >/dev/null
done

aws ec2 authorize-security-group-ingress \
    --region "$REGION" \
    --group-id "$WEB_SG" \
    --protocol tcp \
    --port 22 \
    --cidr "$SSH_CIDR" >/dev/null

# Security Group privado para PostgreSQL.

DB_SG=$(aws ec2 create-security-group \
    --region "$REGION" \
    --group-name "${PROJECT}-db-${STAMP}" \
    --description "PostgreSQL 16 exclusivo desde EC2" \
    --vpc-id "$VPC_ID" \
    --query GroupId \
    --output text)

aws ec2 authorize-security-group-ingress \
    --region "$REGION" \
    --group-id "$DB_SG" \
    --protocol tcp \
    --port 5432 \
    --source-group "$WEB_SG" >/dev/null

# Grupo de subredes para RDS.

DB_SUBNET_GROUP="${PROJECT}-subnets-${STAMP}"

aws rds create-db-subnet-group \
    --region "$REGION" \
    --db-subnet-group-name "$DB_SUBNET_GROUP" \
    --db-subnet-group-description "Subredes PostgreSQL Refrendo Tonala" \
    --subnet-ids "${SUBNETS[@]}" >/dev/null

# Crear Amazon RDS PostgreSQL 16.

aws rds create-db-instance \
    --region "$REGION" \
    --db-instance-identifier "$DB_ID" \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version "$DB_VERSION" \
    --master-username "$DB_USER" \
    --master-user-password "$DB_PASS" \
    --db-name "$DB_NAME" \
    --allocated-storage 20 \
    --storage-type gp3 \
    --port 5432 \
    --db-subnet-group-name "$DB_SUBNET_GROUP" \
    --vpc-security-group-ids "$DB_SG" \
    --no-publicly-accessible \
    --no-multi-az \
    --auto-minor-version-upgrade \
    --backup-retention-period 1 >/dev/null

aws rds wait db-instance-available \
    --region "$REGION" \
    --db-instance-identifier "$DB_ID"

DB_ENDPOINT=$(aws rds describe-db-instances \
    --region "$REGION" \
    --db-instance-identifier "$DB_ID" \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)

echo "RDS disponible: $DB_ENDPOINT"

# Configurar respaldo S3 sin impedir el inicio del portal
# si Learner Lab restringe los permisos correspondientes.

BUCKET_NAME="${PROJECT}-respaldos-${ACCOUNT_ID}"

configure_s3() {
    if ! aws s3api head-bucket \
        --bucket "$BUCKET_NAME" >/dev/null 2>&1; then

        if [ "$REGION" = "us-east-1" ]; then
            aws s3api create-bucket \
                --region "$REGION" \
                --bucket "$BUCKET_NAME" || return 1
        else
            aws s3api create-bucket \
                --region "$REGION" \
                --bucket "$BUCKET_NAME" \
                --create-bucket-configuration \
                LocationConstraint="$REGION" || return 1
        fi
    fi

    aws s3api put-public-access-block \
        --region "$REGION" \
        --bucket "$BUCKET_NAME" \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" || return 1

    aws s3api put-bucket-versioning \
        --region "$REGION" \
        --bucket "$BUCKET_NAME" \
        --versioning-configuration Status=Enabled || return 1
}

if ! configure_s3; then
    echo "ADVERTENCIA: No fue posible configurar S3."
    BUCKET_NAME=""
fi

# Obtener Ubuntu 22.04 LTS.

AMI_ID=$(aws ssm get-parameter \
    --region "$REGION" \
    --name /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id \
    --query Parameter.Value \
    --output text)

# Configuración automática de EC2.
# El repositorio debe ser accesible para git clone.

cat > "$TMP_DIR/user_data.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
umask 077

export DEBIAN_FRONTEND=noninteractive

exec > >(tee -a /var/log/refrendo-bootstrap.log) 2>&1

apt-get update
apt-get install -y git curl ca-certificates

git clone --branch main "${REPO_URL}" /opt/refrendo-tonala

cd /opt/refrendo-tonala

cat > .env <<ENV
DEBUG=0
DEMO_MODE=1
REFRENDO_YEAR=2026
TRUST_PROXY=1
REQUIRE_POSTGRES16=1

SECRET_KEY=${SECRET_KEY}
DOCUMENT_SIGNING_KEY=${DOCUMENT_SIGNING_KEY}
AUDIT_KEY=${AUDIT_KEY}

PUBLIC_HOST=placeholder.sslip.io
PUBLIC_BASE_URL=https://placeholder.sslip.io

ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://placeholder.sslip.io

DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@${DB_ENDPOINT}:5432/${DB_NAME}?sslmode=require

AWS_DEFAULT_REGION=${REGION}
S3_BACKUP_BUCKET=${BUCKET_NAME}

MP_SANDBOX=1
ENV

chmod 600 .env

bash infra/configure_ec2.sh

docker compose -f compose.aws.yaml exec -T \
    -e DJANGO_SUPERUSER_USERNAME="${ADMIN_USER}" \
    -e DJANGO_SUPERUSER_EMAIL="admin@tonala.local" \
    -e DJANGO_SUPERUSER_PASSWORD="${ADMIN_PASS}" \
    web python manage.py createsuperuser --noinput

if [ -n "${BUCKET_NAME}" ]; then
    docker compose -f compose.aws.yaml exec -T \
        web python scripts/aws_s3_audit.py \
        || echo "ADVERTENCIA: Exportación S3 pendiente."
fi

echo "Configuración de EC2 finalizada."
EOF

# Lanzar instancia EC2 con IPv4 pública explícita.

INSTANCE_ID=$(aws ec2 run-instances \
    --region "$REGION" \
    --image-id "$AMI_ID" \
    --instance-type t3.small \
    --key-name "$KEY_NAME" \
    --subnet-id "$PUBLIC_SUBNET" \
    --associate-public-ip-address \
    --security-group-ids "$WEB_SG" \
    --iam-instance-profile Name=LabInstanceProfile \
    --metadata-options \
        HttpEndpoint=enabled,HttpTokens=required,HttpPutResponseHopLimit=2 \
    --user-data "file://${TMP_DIR}/user_data.sh" \
    --tag-specifications \
        "ResourceType=instance,Tags=[{Key=Name,Value=${PROJECT}-web}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

aws ec2 wait instance-running \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID"

PUBLIC_IP=$(aws ec2 describe-instances \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

if [ -z "$PUBLIC_IP" ] || [ "$PUBLIC_IP" = "None" ]; then
    echo "ERROR: EC2 no tiene IP pública."
    exit 1
fi

DOMAIN="${PUBLIC_IP}.sslip.io"

echo "========================================="
echo "Instancia EC2: ${INSTANCE_ID}"
echo "IP pública: ${PUBLIC_IP}"
echo "Portal: https://${DOMAIN}"
echo "Administrador: https://${DOMAIN}/admin/"
echo "Usuario: ${ADMIN_USER}"
echo "Contraseña: ${ADMIN_PASS}"
echo "PostgreSQL: ${DB_VERSION}"
echo "SSH: ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP}"
echo "========================================="

# Esperar una respuesta real del portal.

for ((i=1; i<=120; i++)); do

    if curl -fsS \
        --connect-timeout 5 \
        --max-time 10 \
        "http://${PUBLIC_IP}/salud/" >/dev/null; then

        echo "Conexión HTTP y PostgreSQL correctas."
        break
    fi

    if [ "$i" -eq 120 ]; then
        echo "ERROR: El portal no respondió por HTTP."
        echo "Revisar /var/log/refrendo-bootstrap.log en EC2."
        exit 1
    fi

    sleep 10
done

for ((i=1; i<=30; i++)); do

    if curl -fsS \
        --connect-timeout 5 \
        --max-time 10 \
        "https://${DOMAIN}/salud/" >/dev/null; then

        echo "DESPLIEGUE VERIFICADO."
        echo "https://${DOMAIN}"
        exit 0
    fi

    sleep 10
done

echo "ERROR: HTTP funciona, pero HTTPS todavía no responde."
echo "Revisar DNS y certificado en los registros de Caddy."
exit 1