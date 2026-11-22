import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import boto3
import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from refrendo.models import Renewal, Certificate, AuditEvent  # noqa: E402


def main():
    bucket = os.environ["S3_BACKUP_BUCKET"]
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    s3 = boto3.client("s3", region_name=region)

    # 1. Verificar integridad de cadena HMAC mediante comando nativo de Django
    audit_result = subprocess.check_output(
        [sys.executable, "manage.py", "verify_audit"], text=True
    ).strip()

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    last_event = AuditEvent.objects.order_by("-id").first()

    payload = {
        "timestamp_utc": now.isoformat(),
        "audit_integrity": audit_result,
        "metrics": {
            "total_renewals": Renewal.objects.count(),
            "issued_certificates": Certificate.objects.count(),
            "audit_events": AuditEvent.objects.count(),
            "latest_chain_digest": last_event.digest if last_event else None,
        },
    }

    body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    history_key = f"auditoria/sello-{ts}.json"
    latest_key = "auditoria/ultimo-estado.json"

    # 2. Subir evidencia histórica y estado actual a Amazon S3 (con versionado activo)
    for key in (history_key, latest_key):
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )

    print(f"[OK] {audit_result}")
    print(f"[OK] Evidencia exportada a s3://{bucket}/{history_key}")

    # 3. Listar últimos 5 sellos almacenados en S3
    objs = s3.list_objects_v2(Bucket=bucket, Prefix="auditoria/sello-").get("Contents", [])
    for obj in sorted(objs, key=lambda x: x["LastModified"], reverse=True)[:5]:
        print(f"  - {obj['Key']} ({obj['Size']} bytes)")


if __name__ == "__main__":
    main()