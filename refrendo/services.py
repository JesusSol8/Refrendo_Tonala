import hashlib
import hmac
import json
import time
import unicodedata
from datetime import date
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import (AuditEvent, AuditHead, Certificate, Contribution, License, LookupThrottle,
                     PaymentAttempt, PaymentRecord, Renewal, ShippingRate, Tariff)

class BusinessError(ValueError): pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def sign(value, key):
    return hmac.new(key.encode(), canonical(value).encode(), hashlib.sha256).hexdigest()

def normalize(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c)).casefold().split())

@transaction.atomic
def throttle(ip):
    window = int(time.time()) // 300
    key = hashlib.sha256((settings.SECRET_KEY + ip).encode()).hexdigest()
    obj, _ = LookupThrottle.objects.get_or_create(key=key, defaults={'window': window})
    obj = LookupThrottle.objects.select_for_update().get(pk=obj.pk)
    if obj.window != window: obj.window, obj.count = window, 0
    obj.count += 1
    obj.save()
    return obj.count <= 20

def find_license(number, taxpayer):
    obj = License.objects.select_related('business_type').filter(number__iexact=number.strip()).first()
    if obj is None or normalize(obj.taxpayer) != normalize(taxpayer):
        raise BusinessError('No encontramos una licencia que coincida con ambos datos. Revisa tu licencia e intenta de nuevo.')
    return obj

def eligible(license):
    if not license.active:
        raise BusinessError('La licencia está inactiva. Acude a la Dirección de Padrón y Licencias.')
    bt = license.business_type
    if not bt.low_risk or bt.required_department:
        raise BusinessError('Este giro requiere revisión previa. Acude a: ' + (bt.required_department or 'Dirección de Inspección y Vigilancia') + '.')
    if license.last_renewed_year < settings.REFRENDO_YEAR - 1:
        raise BusinessError('La licencia tiene ejercicios anteriores pendientes. Acude a Tesorería y a Padrón y Licencias para regularizarla.')
    paid = Renewal.objects.filter(license=license, year=settings.REFRENDO_YEAR, status=Renewal.Status.PAID).exists()
    if license.last_renewed_year >= settings.REFRENDO_YEAR and not paid:
        raise BusinessError('Esta licencia ya cuenta con refrendo del ejercicio. Consulta a Padrón y Licencias.')

def quote(license, contribution_ids=(), delivery='pickup', address=None):
    eligible(license)
    tariff = Tariff.objects.filter(business_type=license.business_type, year=settings.REFRENDO_YEAR).first()
    if not tariff: raise BusinessError('No existe tabulador vigente para este giro. Contacta a Tesorería.')
    if tariff.academic and not settings.DEMO_MODE:
        raise BusinessError('El tabulador requiere validación municipal antes de habilitar pagos externos.')
    try: ids = {int(i) for i in contribution_ids}
    except (TypeError, ValueError): raise BusinessError('Aportaciones no válidas.')
    contributions = list(Contribution.objects.filter(active=True, pk__in=ids).order_by('pk'))
    if len(contributions) != len(ids): raise BusinessError('Una aportación ya no está disponible. Actualiza la página.')
    items = [{'label': label, 'amount': str(amount)} for label, amount in [
        ('Derechos de refrendo', tariff.base), ('Emisión de cédula', tariff.document_fee),
        ('Servicio obligatorio de residuos', tariff.mandatory_waste), ('Recargos liquidados', tariff.surcharge)]]
    items += [{'label': c.name + ' (voluntaria)', 'amount': str(c.amount)} for c in contributions]
    shipping = Decimal('0.00')
    if delivery == 'shipping':
        postal = (address or {}).get('postal_code', '')
        rates = [r for r in ShippingRate.objects.filter(active=True) if postal.startswith(r.postal_prefix)]
        if not rates: raise BusinessError('No tenemos cobertura para ese código postal. Puedes elegir recolección en ventanilla.')
        shipping = max(rates, key=lambda r: len(r.postal_prefix)).amount
    elif delivery != 'pickup': raise BusinessError('Selecciona una modalidad de entrega válida.')
    items.append({'label': 'Envío a domicilio' if delivery == 'shipping' else 'Recolección en ventanilla', 'amount': str(shipping)})
    total = sum((Decimal(i['amount']) for i in items), Decimal('0.00'))
    if total <= 0: raise BusinessError('La liquidación debe ser mayor a cero. Contacta a Tesorería.')
    return {'items': items, 'total': str(total), 'year': settings.REFRENDO_YEAR,
            'source': tariff.source, 'academic': tariff.academic,
            'license_number': license.number, 'taxpayer': license.taxpayer, 'trade_name': license.trade_name,
            'business_type': license.business_type.name, 'business_address': license.address}

@transaction.atomic
def audit(kind, renewal=None, details=None):
    AuditHead.objects.get_or_create(pk=1)
    head = AuditHead.objects.select_for_update().get(pk=1)
    now = timezone.now()
    data = {'at': now.isoformat(), 'kind': kind, 'renewal': str(renewal.pk) if renewal else '',
            'details': details or {}, 'previous': head.digest}
    digest = sign(data, settings.AUDIT_KEY)
    event = AuditEvent.objects.create(created_at=now, kind=kind, renewal_id_text=data['renewal'],
        details=data['details'], previous_hash=head.digest, digest=digest)
    head.digest = digest
    head.save(update_fields=['digest'])
    return event

def check_audit():
    previous = '0' * 64
    for row in AuditEvent.objects.order_by('pk'):
        data = {'at': row.created_at.isoformat(), 'kind': row.kind, 'renewal': row.renewal_id_text,
                'details': row.details, 'previous': previous}
        if row.previous_hash != previous or not hmac.compare_digest(row.digest, sign(data, settings.AUDIT_KEY)):
            return False, row.pk
        previous = row.digest
    head = AuditHead.objects.filter(pk=1).first()
    return (not head or head.digest == previous), None

@transaction.atomic
def create_renewal(license, form):
    license = License.objects.select_for_update().select_related('business_type').get(pk=license.pk)
    eligible(license)
    existing = Renewal.objects.filter(license=license, year=settings.REFRENDO_YEAR).first()
    if existing: return existing
    data = form.cleaned_data
    address = form.address()
    snapshot = quote(license, [c.pk for c in data['contributions']], data['delivery'], address)
    obj = Renewal.objects.create(license=license, year=settings.REFRENDO_YEAR, snapshot=snapshot,
        total=snapshot['total'], delivery=data['delivery'], shipping_address=address)
    audit('renewal_created', obj, {'license': license.number, 'amount': str(obj.total),
        'delivery': obj.delivery, 'shipping_address': address, 'quote': snapshot})
    return obj

def certificate_payload(renewal):
    s = renewal.snapshot
    return {'folio': renewal.folio, 'license': s['license_number'], 'trade_name': s['trade_name'],
            'taxpayer': s['taxpayer'], 'business_type': s['business_type'], 'business_address': s['business_address'],
            'year': renewal.year, 'valid_until': date(renewal.year, 12, 31).isoformat(),
            'paid_at': renewal.paid_at.isoformat(), 'total': str(renewal.total), 'academic': settings.DEMO_MODE}

def valid_certificate(certificate):
    return hmac.compare_digest(certificate.digest, sign(certificate.payload, settings.DOCUMENT_SIGNING_KEY))

@transaction.atomic
def apply_payment(attempt_id, provider_id, status, amount, currency, method='', updated_at=None):
    # Bloquear primero la licencia y luego el trámite en todo flujo que muta ambos.
    ref = PaymentAttempt.objects.select_related('renewal').get(pk=attempt_id)
    license = License.objects.select_for_update().get(pk=ref.renewal.license_id)
    renewal = Renewal.objects.select_for_update().get(pk=ref.renewal_id)
    attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt_id)
    if currency != 'MXN' or Decimal(str(amount)) != renewal.total:
        raise BusinessError('El importe o la moneda del pago no coincide con la liquidación.')
    updated_at = updated_at or timezone.now()
    record = PaymentRecord.objects.filter(provider_id=str(provider_id)).first()
    if record and record.attempt_id != attempt.id: raise BusinessError('El pago ya está asociado a otro trámite.')
    if record and updated_at <= record.provider_updated_at: return renewal
    if record and record.status == status: return renewal
    if not record:
        record = PaymentRecord(provider_id=str(provider_id), attempt=attempt)
    record.status, record.amount, record.method, record.provider_updated_at = status, renewal.total, method, updated_at
    record.save()
    attempt.status, attempt.method = status, method
    attempt.save(update_fields=['status', 'method', 'updated_at'])
    audit('payment_' + status, renewal, {'payment_id': str(provider_id), 'license': license.number,
        'amount': str(renewal.total), 'currency': currency, 'method': method, 'provider': attempt.provider})
    records = PaymentRecord.objects.filter(attempt__renewal=renewal)
    approved = records.filter(status='approved').count()
    if approved:
        if renewal.status != Renewal.Status.PAID:
            renewal.status = Renewal.Status.PAID
            renewal.paid_at = renewal.paid_at or timezone.now()
            renewal.save(update_fields=['status', 'paid_at'])
            license.last_renewed_year = max(license.last_renewed_year, renewal.year)
            license.save(update_fields=['last_renewed_year'])
            if not Certificate.objects.filter(renewal=renewal).exists():
                payload = certificate_payload(renewal)
                Certificate.objects.create(renewal=renewal, payload=payload, digest=sign(payload, settings.DOCUMENT_SIGNING_KEY))
                audit('certificate_issued', renewal, {'folio': renewal.folio})
        if approved > 1: audit('duplicate_payment_review', renewal, {'payment_id': str(provider_id)})
    elif records.filter(status__in=['refunded', 'charged_back', 'cancelled']).exists() and renewal.paid_at:
        renewal.status = Renewal.Status.REVOKED
        renewal.save(update_fields=['status'])
    elif renewal.status != Renewal.Status.REVOKED:
        renewal.status = Renewal.Status.PENDING if records.filter(status__in=['pending', 'in_process', 'authorized']).exists() else Renewal.Status.REJECTED
        renewal.save(update_fields=['status'])
    return renewal
