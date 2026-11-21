import hashlib
import hmac
import time
from urllib.parse import urlparse
import requests
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from .models import PaymentAttempt, Renewal
from .services import BusinessError, apply_payment, audit

class ProviderUnavailable(BusinessError): pass

def api(method, path, **kwargs):
    try:
        response = requests.request(method, 'https://api.mercadopago.com' + path, timeout=(5, 20),
            headers={'Authorization': 'Bearer ' + settings.MP_ACCESS_TOKEN, 'Content-Type': 'application/json',
                     **kwargs.pop('headers', {})}, **kwargs)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ProviderUnavailable('Mercado Pago no está disponible por el momento. Tu trámite está guardado; intenta nuevamente.') from exc

@transaction.atomic
def checkout(renewal):
    renewal = Renewal.objects.select_for_update().get(pk=renewal.pk)
    if renewal.status in [Renewal.Status.PAID, Renewal.Status.REVOKED]:
        raise BusinessError('Este trámite ya no admite iniciar un pago.')
    attempt = renewal.attempts.order_by('created_at').first()
    if attempt: return attempt
    attempt = PaymentAttempt.objects.create(renewal=renewal, provider='demo' if settings.DEMO_MODE else 'mercadopago')
    if not settings.DEMO_MODE:
        url = settings.PUBLIC_BASE_URL + reverse('renewal', args=[renewal.pk])
        payload = {'external_reference': str(attempt.pk),
            'items': [{'id': str(renewal.pk), 'title': 'Refrendo municipal ' + renewal.folio,
                       'quantity': 1, 'currency_id': 'MXN', 'unit_price': float(renewal.total)}],
            'back_urls': {'success': url, 'pending': url, 'failure': url}, 'auto_return': 'approved',
            'notification_url': settings.PUBLIC_BASE_URL + reverse('mp_webhook') + '?source_news=webhooks',
            'metadata': {'renewal_id': str(renewal.pk)}}
        result = api('POST', '/checkout/preferences', json=payload,
                     headers={'X-Idempotency-Key': str(attempt.pk)})
        target = result.get('sandbox_init_point' if settings.MP_SANDBOX else 'init_point', '')
        parsed = urlparse(target)
        if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.mercadopago.com.mx'):
            raise ProviderUnavailable('La pasarela devolvió una dirección no válida.')
        attempt.preference_id, attempt.checkout_url = str(result['id']), target
        attempt.save(update_fields=['preference_id', 'checkout_url'])
    audit('checkout_created', renewal, {'attempt': str(attempt.pk), 'provider': attempt.provider})
    return attempt

def verify_webhook(request):
    data_id = request.GET.get('data.id', '')
    request_id = request.headers.get('x-request-id', '')
    try:
        parts = dict(p.strip().split('=', 1) for p in request.headers.get('x-signature', '').split(','))
        ts, supplied = parts['ts'], parts['v1']
        stamp = int(ts)
        seconds = stamp / 1000 if stamp > 10**11 else stamp
        if abs(time.time() - seconds) > 600: return False
    except (ValueError, KeyError): return False
    if not settings.MP_WEBHOOK_SECRET or not data_id or not request_id: return False
    manifest = f'id:{data_id.lower()};request-id:{request_id};ts:{ts};'
    expected = hmac.new(settings.MP_WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)

def reconcile(payment_id):
    if not str(payment_id).isdigit(): raise BusinessError('Identificador de pago no válido.')
    payload = api('GET', '/v1/payments/' + str(payment_id))
    try:
        if str(payload['id']) != str(payment_id): raise BusinessError('Identificador inconsistente.')
        attempt = PaymentAttempt.objects.get(pk=payload['external_reference'], provider='mercadopago')
        if settings.MP_SANDBOX and payload.get('live_mode') is not False:
            raise BusinessError('Se esperaba un pago de pruebas.')
        if not settings.MP_SANDBOX and payload.get('live_mode') is not True:
            raise BusinessError('Se esperaba un pago de producción.')
        stamp = parse_datetime(payload['date_last_updated'])
        if stamp is None: raise BusinessError('Fecha de pago inválida.')
        return apply_payment(attempt.pk, payload['id'], payload['status'], payload['transaction_amount'],
            payload['currency_id'], payload.get('payment_type_id', ''), stamp)
    except (KeyError, ValueError, ValidationError, PaymentAttempt.DoesNotExist) as exc:
        raise BusinessError('El pago no corresponde a una operación válida de este portal.') from exc

