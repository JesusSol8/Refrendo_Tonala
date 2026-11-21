import csv
import json
import logging
import uuid
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.db import transaction, DatabaseError
from django.db.models import Sum, Count
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from .documents import certificate_pdf, qr_bytes
from .forms import LookupForm, QuoteForm, DemoPaymentForm, FulfillmentForm
from .models import AuditEvent, Certificate, License, PaymentAttempt, PaymentRecord, Renewal
from .payments import checkout, verify_webhook, reconcile, ProviderUnavailable
from .services import BusinessError, audit, apply_payment, create_renewal, eligible, find_license, quote, throttle, valid_certificate, check_audit

log = logging.getLogger(__name__)

def client_ip(request):
    if settings.TRUST_PROXY:
        return request.headers.get('X-Real-IP', request.META.get('REMOTE_ADDR','unknown'))
    return request.META.get('REMOTE_ADDR','unknown')

def authorized_license(request):
    pk = request.session.get('license_id')
    if not pk: raise Http404('Primero consulta tu licencia.')
    return get_object_or_404(License.objects.select_related('business_type'), pk=pk)

def owned_renewal(request, pk):
    obj = get_object_or_404(Renewal.objects.select_related('license'), pk=pk)
    if obj.license_id not in request.session.get('authorized_licenses', []):
        raise Http404('Consulta tu licencia para acceder al trámite.')
    return obj

def home(request):
    form = LookupForm(request.POST or None)
    blocked = None
    if request.method == 'POST':
        if not throttle(client_ip(request)):
            form.add_error(None, 'Demasiados intentos. Espera cinco minutos antes de volver a consultar.')
        elif form.is_valid():
            try:
                license = find_license(**form.cleaned_data)
                eligible(license)
                request.session.cycle_key()
                request.session['license_id'] = license.pk
                allowed = request.session.get('authorized_licenses', [])
                request.session['authorized_licenses'] = list(dict.fromkeys(allowed + [license.pk]))[-10:]
                request.session.set_expiry(3600)
                existing = Renewal.objects.filter(license=license, year=settings.REFRENDO_YEAR).first()
                return redirect('renewal', pk=existing.pk) if existing else redirect('liquidation')
            except BusinessError as exc:
                blocked = str(exc)
                form.add_error(None, str(exc))
    return render(request, 'refrendo/home.html', {'form': form, 'blocked': blocked})

def liquidation(request):
    license = authorized_license(request)
    existing = Renewal.objects.filter(license=license, year=settings.REFRENDO_YEAR).first()
    if existing: return redirect('renewal', pk=existing.pk)
    form = QuoteForm(request.POST or None)
    try:
        initial = quote(license)
        if request.method == 'POST' and form.is_valid():
            obj = create_renewal(license, form)
            return redirect('renewal', pk=obj.pk)
    except BusinessError as exc:
        form.add_error(None, str(exc))
        initial = None
    return render(request, 'refrendo/liquidation.html', {'license': license, 'form': form, 'quote': initial})

@require_POST
def api_quote(request):
    license = authorized_license(request)
    try:
        result = quote(license, request.POST.getlist('contributions'), request.POST.get('delivery', 'pickup'),
                       {'postal_code': request.POST.get('postal_code', '')})
        return JsonResponse(result)
    except BusinessError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

def renewal(request, pk):
    obj = owned_renewal(request, pk)
    certificate = Certificate.objects.filter(renewal=obj).first()
    attempt = obj.attempts.order_by('created_at').first()
    return render(request, 'refrendo/renewal.html', {'renewal': obj, 'certificate': certificate, 'attempt': attempt,
        'payments': PaymentRecord.objects.filter(attempt__renewal=obj).order_by('-pk')})

@require_POST
def pay(request, pk):
    obj = owned_renewal(request, pk)
    try:
        attempt = checkout(obj)
        if settings.DEMO_MODE: return redirect('demo_payment', pk=attempt.pk)
        return redirect(attempt.checkout_url)
    except BusinessError as exc:
        messages.error(request, str(exc))
        return redirect('renewal', pk=obj.pk)

def demo_payment(request, pk):
    if not settings.DEMO_MODE: raise Http404()
    attempt = get_object_or_404(PaymentAttempt, pk=pk, provider='demo')
    obj = owned_renewal(request, attempt.renewal_id)
    if obj.status in [Renewal.Status.PAID, Renewal.Status.REVOKED]: return redirect('renewal', pk=obj.pk)
    form = DemoPaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        apply_payment(attempt.pk, 'DEMO-' + str(attempt.pk), form.cleaned_data['outcome'], obj.total,
                      'MXN', form.cleaned_data['method'])
        messages.success(request, 'Resultado de prueba registrado. No se realizó ningún cobro real.')
        return redirect('renewal', pk=obj.pk)
    return render(request, 'refrendo/payment.html', {'form': form, 'renewal': obj})

@require_GET
def api_status(request, pk):
    obj = owned_renewal(request, pk)
    return JsonResponse({'status': obj.status, 'label': obj.get_status_display(), 'paid': obj.status == Renewal.Status.PAID})

@csrf_exempt
@require_POST
def mp_webhook(request):
    if settings.DEMO_MODE: return JsonResponse({'error': 'Pasarela externa desactivada en demostración.'}, status=404)
    if not verify_webhook(request): return JsonResponse({'error': 'Firma inválida.'}, status=401)
    try:
        body = json.loads(request.body)
        if body.get('type') != 'payment': return JsonResponse({'received': True})
        payment_id = request.GET.get('data.id', '')
        if str(body.get('data', {}).get('id', '')) != payment_id:
            return JsonResponse({'error': 'Identificador inconsistente.'}, status=400)
        reconcile(payment_id)
        return JsonResponse({'received': True})
    except ProviderUnavailable:
        return JsonResponse({'error': 'Reintentar más tarde.'}, status=503)
    except (BusinessError, ValueError, TypeError, AttributeError):
        return JsonResponse({'error': 'Notificación no aplicable.'}, status=400)
    except DatabaseError:
        log.exception('Error transitorio al aplicar notificación')
        return JsonResponse({'error': 'Reintentar más tarde.'}, status=503)

def certificate_download(request, pk):
    obj = owned_renewal(request, pk)
    certificate = get_object_or_404(Certificate, renewal=obj)
    if obj.status != Renewal.Status.PAID or not valid_certificate(certificate): raise Http404()
    response = HttpResponse(certificate_pdf(certificate), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{obj.folio}.pdf"'
    return response

def certificate_qr(request, pk):
    obj = owned_renewal(request, pk)
    certificate = get_object_or_404(Certificate, renewal=obj)
    if obj.status != Renewal.Status.PAID or not valid_certificate(certificate): raise Http404()
    return HttpResponse(qr_bytes(certificate), content_type='image/png')

def verify(request):
    digest = request.GET.get('hash', '').strip()
    certificate = Certificate.objects.select_related('renewal').filter(digest=digest).first() if len(digest) == 64 else None
    valid = bool(certificate and valid_certificate(certificate) and certificate.renewal.status == Renewal.Status.PAID)
    expired = bool(valid and timezone.localdate().isoformat() > certificate.payload['valid_until'])
    return render(request, 'refrendo/verify.html', {'searched': bool(digest), 'certificate': certificate if valid else None,
        'valid': valid, 'expired': expired}, status=200 if not digest or valid else 404)

def privacy(request): return render(request, 'refrendo/privacy.html')

@require_GET
def health(request):
    try:
        License.objects.exists()
        return JsonResponse({'status': 'ok'})
    except DatabaseError: return JsonResponse({'status': 'unavailable'}, status=503)

@permission_required('refrendo.view_renewal', raise_exception=True)
def dashboard(request):
    rows = Renewal.objects.select_related('license').order_by('-created_at')
    status = request.GET.get('status', '')
    if status in dict(Renewal.Status.choices): rows = rows.filter(status=status)
    from django.core.paginator import Paginator
    page = Paginator(rows, 25).get_page(request.GET.get('page'))
    return render(request, 'refrendo/dashboard.html', {'page': page, 'status_filter': status,
        'statuses': Renewal.Status.choices, 'count': Renewal.objects.count(),
        'collected': Renewal.objects.filter(status='paid').aggregate(total=Sum('total'))['total'] or 0,
        'pending': Renewal.objects.filter(status='pending').count()})

@permission_required('refrendo.change_renewal', raise_exception=True)
def fulfillment(request, pk):
    obj = get_object_or_404(Renewal, pk=pk)
    form = FulfillmentForm(request.POST or None, initial={'fulfillment': obj.fulfillment, 'tracking_number': obj.tracking_number})
    if request.method == 'POST' and form.is_valid():
        if obj.status != Renewal.Status.PAID:
            form.add_error(None, 'Solo se puede entregar una licencia pagada.')
        elif (obj.delivery == 'pickup' and form.cleaned_data['fulfillment'] == 'shipped') or (obj.delivery == 'shipping' and form.cleaned_data['fulfillment'] == 'ready'):
            form.add_error(None, 'El estado no corresponde a la modalidad de entrega.')
        else:
            with transaction.atomic():
                obj = Renewal.objects.select_for_update().get(pk=pk)
                if obj.status != Renewal.Status.PAID: raise Http404()
                obj.fulfillment, obj.tracking_number = form.cleaned_data['fulfillment'], form.cleaned_data['tracking_number']
                obj.save(update_fields=['fulfillment', 'tracking_number'])
                audit('fulfillment_updated', obj, {'user': request.user.username, **form.cleaned_data})
            messages.success(request, 'Entrega actualizada.')
            return redirect('dashboard')
    return render(request, 'refrendo/fulfillment.html', {'form': form, 'renewal': obj})

@permission_required('refrendo.view_auditevent', raise_exception=True)
def audit_view(request):
    from django.core.paginator import Paginator
    integrity, bad = check_audit()
    return render(request, 'refrendo/audit.html', {'page': Paginator(AuditEvent.objects.order_by('-pk'), 30).get_page(request.GET.get('page')),
        'integrity': integrity, 'bad': bad})

@permission_required('refrendo.view_renewal', raise_exception=True)
def export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="conciliacion.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Folio', 'Licencia', 'Contribuyente', 'Estado', 'Total MXN', 'Entrega', 'Guía', 'Dirección', 'Pagos proveedor'])
    def cell(value):
        text = str(value)
        return "'" + text if text.startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text
    for r in Renewal.objects.select_related('license').prefetch_related('attempts__payments').order_by('created_at'):
        ids = ', '.join(p.provider_id + ':' + p.status for a in r.attempts.all() for p in a.payments.all())
        writer.writerow([cell(v) for v in [r.folio, r.snapshot['license_number'], r.snapshot['taxpayer'], r.get_status_display(),
            r.total, r.get_delivery_display(), r.tracking_number, json.dumps(r.shipping_address, ensure_ascii=False), ids]])
    audit('reconciliation_exported', details={'user': request.user.username})
    return response

@require_POST
def api_lookup(request):
    if not throttle(client_ip(request)):
        return JsonResponse({'error':'Demasiados intentos. Espera cinco minutos.'},status=429)
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        form = LookupForm(data)
        if not form.is_valid(): return JsonResponse({'errors':form.errors.get_json_data()},status=400)
        license = find_license(**form.cleaned_data)
        eligible(license)
        request.session.cycle_key()
        request.session['license_id'] = license.pk
        request.session['authorized_licenses'] = list(dict.fromkeys(request.session.get('authorized_licenses',[])+[license.pk]))[-10:]
        request.session.set_expiry(3600)
        return JsonResponse({'license':license.number,'trade_name':license.trade_name,'business_type':license.business_type.name,
                             'eligible':True,'next':reverse('liquidation')})
    except (BusinessError, ValueError, TypeError, AttributeError) as exc:
        return JsonResponse({'error':str(exc) if isinstance(exc,BusinessError) else 'Solicitud no válida.'},status=400)

