import hashlib
import hmac
import json
import time
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.management import call_command
from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import License, Contribution, Renewal, Certificate, PaymentAttempt, PaymentRecord, AuditEvent, AuditHead, Tariff
from .forms import QuoteForm
from .services import BusinessError, find_license, eligible, quote, create_renewal, apply_payment, check_audit, valid_certificate, audit
from .payments import checkout, reconcile, verify_webhook, ProviderUnavailable
from .documents import certificate_pdf, qr_bytes

class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)
        cls.license = License.objects.get(number='TON-0001')
    def login_license(self, client=None):
        c = client or self.client
        return c.post('/', {'number':'TON-0001','taxpayer':'María López García'})
    def form(self, **kwargs):
        data = {'delivery':'pickup','accept':'on',**kwargs}
        f = QuoteForm(data)
        self.assertTrue(f.is_valid(), f.errors)
        return f
    def renewal(self, **kwargs): return create_renewal(self.license, self.form(**kwargs))
    def paid(self):
        r = self.renewal()
        a = checkout(r)
        return apply_payment(a.pk, 'demo-1', 'approved', r.total, 'MXN', 'card')
    def test_lookup_only_two_fields_and_normalization(self):
        self.assertEqual(find_license('ton-0001','  MARIA   LOPEZ GARCIA ').pk, self.license.pk)
        response = self.login_license()
        self.assertRedirects(response, '/liquidacion/')
    def test_mismatch_does_not_authorize(self):
        self.client.post('/', {'number':'TON-0001','taxpayer':'Otra persona'})
        self.assertNotIn('license_id', self.client.session)
    def test_all_ineligible_cases(self):
        for number in ['TON-0003','TON-0004','TON-0005','TON-0006']:
            with self.subTest(number=number), self.assertRaises(BusinessError):
                eligible(License.objects.select_related('business_type').get(number=number))
    def test_lookup_throttled(self):
        for _ in range(20): self.client.post('/', {'number':'x','taxpayer':'x'})
        response = self.client.post('/', {'number':'TON-0001','taxpayer':'María López García'})
        self.assertContains(response,'Demasiados intentos')
        self.assertNotIn('license_id', self.client.session)
    def test_quote_decimal_and_optional_contributions(self):
        base = Decimal(quote(self.license)['total'])
        c = Contribution.objects.first()
        self.assertEqual(Decimal(quote(self.license, [c.pk,c.pk])['total']), base+c.amount)
        self.assertEqual(base, Decimal('1685.00'))
    def test_delivery_uses_longest_postal_prefix(self):
        a = Decimal(quote(self.license, delivery='shipping', address={'postal_code':'45400'})['total'])
        b = Decimal(quote(self.license, delivery='shipping', address={'postal_code':'45410'})['total'])
        self.assertEqual(a, Decimal('1780.00'))
        self.assertEqual(b-a, Decimal('25.00'))
    def test_no_coverage_and_unknown_contribution(self):
        with self.assertRaises(BusinessError): quote(self.license, delivery='shipping', address={'postal_code':'99999'})
        with self.assertRaises(BusinessError): quote(self.license, [9999])
        with self.assertRaises(BusinessError): quote(self.license, delivery='invalid')
    def test_missing_tariff_fails_closed(self):
        Tariff.objects.filter(business_type=self.license.business_type).delete()
        with self.assertRaises(BusinessError): quote(self.license)
    @override_settings(DEMO_MODE=False)
    def test_academic_tariff_blocked_for_external_payments(self):
        with self.assertRaises(BusinessError): quote(self.license)
    def test_complete_shipping_required(self):
        f = QuoteForm({'delivery':'shipping','accept':'on','postal_code':'bad','phone':'1'})
        self.assertFalse(f.is_valid())
        for key in ['recipient','street','exterior','postal_code','phone']: self.assertIn(key,f.errors)
    def test_duplicate_submit_one_renewal(self):
        a = self.renewal()
        b = self.renewal(contributions=[Contribution.objects.first().pk])
        self.assertEqual(a.pk,b.pk)
        self.assertEqual(Renewal.objects.count(),1)
    def test_client_amount_is_ignored(self):
        self.login_license()
        self.client.post('/liquidacion/', {'delivery':'pickup','accept':'on','total':'0.01'})
        self.assertEqual(Renewal.objects.get().total,Decimal('1685.00'))
    def test_another_browser_cannot_view_or_download(self):
        r = self.paid()
        for path in [reverse('renewal',args=[r.pk]),reverse('certificate_pdf',args=[r.pk]),reverse('api_status',args=[r.pk])]:
            self.assertEqual(Client().get(path).status_code,404)
    def test_csrf_on_checkout_and_quote(self):
        c = Client(enforce_csrf_checks=True)
        for path in ['/','/api/v1/cotizacion/','/liquidacion/']:
            self.assertEqual(c.post(path,{}).status_code,403)
    def test_pending_then_approved_issues_once(self):
        r = self.renewal(); a = checkout(r)
        apply_payment(a.pk,'p1','pending',r.total,'MXN','spei')
        self.assertEqual(Certificate.objects.count(),0)
        apply_payment(a.pk,'p1','approved',r.total,'MXN','spei')
        apply_payment(a.pk,'p1','approved',r.total,'MXN','spei')
        self.assertEqual(Certificate.objects.count(),1)
        self.assertEqual(AuditEvent.objects.filter(kind='payment_approved').count(),1)
        self.assertTrue(check_audit()[0])
    def test_all_demo_methods(self):
        self.login_license()
        r = self.renewal(); a = checkout(r)
        url = reverse('demo_payment',args=[a.pk])
        for method in ['card','spei','cash']:
            self.client.post(url,{'method':method,'outcome':'pending'})
        self.client.post(url,{'method':'cash','outcome':'approved'})
        r.refresh_from_db()
        self.assertEqual(r.status,'paid')
    def test_rejection_no_certificate(self):
        r = self.renewal(); a = checkout(r)
        apply_payment(a.pk,'p1','rejected',r.total,'MXN')
        r.refresh_from_db()
        self.assertEqual(r.status,'rejected')
        self.assertFalse(Certificate.objects.exists())
    def test_amount_currency_and_payment_reference(self):
        r = self.renewal(); a = checkout(r)
        for amount,currency in [('1.00','MXN'),(r.total,'USD')]:
            with self.assertRaises(BusinessError): apply_payment(a.pk,'p1','approved',amount,currency)
        self.assertFalse(PaymentRecord.objects.exists())
    def test_stale_notification_does_not_downgrade(self):
        r = self.renewal(); a = checkout(r)
        now = timezone.now()
        apply_payment(a.pk,'p1','approved',r.total,'MXN',updated_at=now)
        apply_payment(a.pk,'p1','pending',r.total,'MXN',updated_at=now-timedelta(seconds=10))
        r.refresh_from_db()
        self.assertEqual(r.status,'paid')
    def test_refund_invalidates_public_document_and_download(self):
        self.login_license()
        r = self.paid(); a = r.attempts.first(); c = r.certificate
        apply_payment(a.pk,'demo-1','refunded',r.total,'MXN')
        r.refresh_from_db()
        self.assertEqual(r.status,'revoked')
        self.assertEqual(self.client.get(reverse('verify')+'?hash='+c.digest).status_code,404)
        self.assertEqual(self.client.get(reverse('certificate_pdf',args=[r.pk])).status_code,404)
    def test_public_verification_minimizes_data(self):
        r = self.paid(); c = r.certificate
        response = Client().get(reverse('verify')+'?hash='+c.digest)
        self.assertContains(response,'Documento auténtico y vigente')
        self.assertNotContains(response,self.license.taxpayer)
        self.assertNotContains(response,self.license.address)
    def test_tampered_payload_detected(self):
        c = self.paid().certificate
        c.payload['year'] = 2030
        self.assertFalse(valid_certificate(c))
    def test_database_prevents_audit_and_certificate_mutation(self):
        c = self.paid().certificate
        for model,pk,changes in [(Certificate,c.pk,{'digest':'0'*64}), (AuditEvent,AuditEvent.objects.first().pk,{'kind':'tampered'})]:
            with self.assertRaises(DatabaseError), transaction.atomic(): model.objects.filter(pk=pk).update(**changes)
            with self.assertRaises(DatabaseError), transaction.atomic(): model.objects.filter(pk=pk).delete()
    def test_audit_tail_tamper_detected(self):
        self.paid()
        AuditHead.objects.filter(pk=1).update(digest='f'*64)
        self.assertFalse(check_audit()[0])
    def test_pdf_and_qr_generated(self):
        r = self.paid(); c = r.certificate
        pdf = certificate_pdf(c)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertIn(b'PNG', qr_bytes(c)[:10])
        self.login_license()
        response = self.client.get(reverse('certificate_pdf',args=[r.pk]))
        self.assertEqual(response['Content-Type'],'application/pdf')
    def test_pdf_blocked_before_payment(self):
        self.login_license(); r = self.renewal()
        self.assertEqual(self.client.get(reverse('certificate_pdf',args=[r.pk])).status_code,404)
    def test_checkout_idempotent(self):
        r = self.renewal()
        self.assertEqual(checkout(r).pk,checkout(r).pk)
        self.assertEqual(PaymentAttempt.objects.count(),1)
    @override_settings(DEMO_MODE=False)
    def test_demo_route_disabled(self):
        r = self.renewal_for_external()
        a = PaymentAttempt.objects.create(renewal=r,provider='demo')
        self.assertEqual(self.client.get(reverse('demo_payment',args=[a.pk])).status_code,404)
    def renewal_for_external(self):
        return Renewal.objects.create(license=self.license,year=2026,total='1685.00',delivery='pickup',snapshot=quote_for_test())
    def test_staff_permissions_and_export(self):
        self.assertEqual(self.client.get('/gestion/').status_code,403)
        user = User.objects.create_user('tesoreria',password='Ejemplo-2026!')
        user.user_permissions.add(Permission.objects.get(codename='view_renewal'))
        self.client.force_login(user)
        self.paid()
        self.assertEqual(self.client.get('/gestion/').status_code,200)
        self.assertEqual(self.client.get('/gestion/conciliacion.csv').status_code,200)
        self.assertEqual(self.client.get('/gestion/bitacora/').status_code,403)
    def test_fulfillment_requires_paid_and_matching_delivery(self):
        user = User.objects.create_superuser('operator','operator@example.test','Temporal-2026!')
        self.client.force_login(user)
        r = self.renewal()
        url = reverse('fulfillment',args=[r.pk])
        self.assertContains(self.client.post(url,{'fulfillment':'ready'}),'Solo se puede entregar')
        self.paid()
        self.assertContains(self.client.post(url,{'fulfillment':'shipped','tracking_number':'abc'}),'no corresponde')
        self.client.post(url,{'fulfillment':'ready'})
        r.refresh_from_db()
        self.assertEqual(r.fulfillment,'ready')
    def test_templates_and_security_headers(self):
        for url in ['/','/verificar','/privacidad/','/salud/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response['X-Frame-Options'],'DENY')
        self.login_license()
        self.assertContains(self.client.get('/liquidacion/'),'Resumen de pago')

@override_settings(DEMO_MODE=False,MP_ACCESS_TOKEN='TEST-token',MP_WEBHOOK_SECRET='test-secret',MP_SANDBOX=True)
class WebhookTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with override_settings(DEMO_MODE=True): call_command('seed_demo',verbosity=0)
        license = License.objects.get(number='TON-0001')
        cls.r = Renewal.objects.create(license=license,year=2026,total='1685.00',delivery='pickup',snapshot=quote_for_test())
        cls.a = PaymentAttempt.objects.create(renewal=cls.r,provider='mercadopago')
    def payload(self, **kwargs):
        return {'id':123,'external_reference':str(self.a.pk),'status':'approved','transaction_amount':1685,
            'currency_id':'MXN','payment_type_id':'credit_card','live_mode':False,
            'date_last_updated':timezone.now().isoformat(),**kwargs}
    def send(self,signature=True, timestamp=None, body=None):
        ts = str(timestamp or int(time.time()))
        digest = hmac.new(b'test-secret',f'id:123;request-id:req-1;ts:{ts};'.encode(),hashlib.sha256).hexdigest()
        return self.client.post('/api/v1/mercadopago/webhook/?data.id=123',
            json.dumps(body or {'type':'payment','data':{'id':'123'}}),content_type='application/json',
            HTTP_X_REQUEST_ID='req-1',HTTP_X_SIGNATURE=f'ts={ts},v1={digest if signature else "bad"}')
    def test_invalid_signature_no_provider_call(self):
        with patch('refrendo.payments.api') as provider:
            self.assertEqual(self.send(False).status_code,401)
            provider.assert_not_called()
    def test_stale_signature_rejected(self):
        self.assertEqual(self.send(timestamp=int(time.time())-700).status_code,401)
    @patch('refrendo.payments.api')
    def test_signed_notification_queries_provider_and_is_idempotent(self,provider):
        provider.return_value = self.payload()
        self.assertEqual(self.send().status_code,200)
        self.assertEqual(self.send().status_code,200)
        self.r.refresh_from_db()
        self.assertEqual(self.r.status,'paid')
        self.assertEqual(Certificate.objects.count(),1)
        provider.assert_called_with('GET','/v1/payments/123')
    @patch('refrendo.payments.api')
    def test_bad_amount_rejected(self,provider):
        provider.return_value = self.payload(transaction_amount=1)
        self.assertEqual(self.send().status_code,400)
        self.assertEqual(Certificate.objects.count(),0)
    @patch('refrendo.payments.api')
    def test_other_reference_rejected(self,provider):
        provider.return_value = self.payload(external_reference='bad')
        self.assertEqual(self.send().status_code,400)
    @patch('refrendo.payments.api')
    def test_provider_outage_requests_retry(self,provider):
        provider.side_effect=ProviderUnavailable('offline')
        self.assertEqual(self.send().status_code,503)
    @patch('refrendo.payments.api')
    def test_preference_contains_server_total_and_payment_reference(self,provider):
        self.a.delete()
        provider.return_value={'id':'pref-test','sandbox_init_point':'https://sandbox.mercadopago.com.mx/checkout/v1/test'}
        a = checkout(self.r)
        data = provider.call_args.kwargs['json']
        self.assertEqual(data['items'][0]['unit_price'],1685.0)
        self.assertEqual(data['external_reference'],str(a.pk))
        self.assertIn('/api/v1/mercadopago/webhook/',data['notification_url'])
    def test_return_url_does_not_mark_paid(self):
        session=self.client.session;session['authorized_licenses']=[self.r.license_id];session.save()
        self.client.get(reverse('renewal',args=[self.r.pk])+'?status=approved&payment_id=123')
        self.r.refresh_from_db()
        self.assertEqual(self.r.status,'pending')

def quote_for_test():
    return {'items':[{'label':'Refrendo académico','amount':'1685.00'}], 'total':'1685.00',
        'license_number':'TON-0001','taxpayer':'María López García','trade_name':'Papelería La Ilusión',
        'business_type':'Papelería','business_address':'Domicilio de prueba','academic':True,'year':2026}

class AdditionalContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo',verbosity=0)
    def test_json_lookup_authorizes_quote(self):
        c = Client(enforce_csrf_checks=True)
        c.get('/')
        token = c.cookies['csrftoken'].value
        response=c.post('/api/v1/licencias/consulta/',json.dumps({'number':'TON-0001','taxpayer':'María López García'}),
            content_type='application/json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['eligible'],True)
        response=c.post('/api/v1/cotizacion/',{'delivery':'pickup'},HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.json()['total'],'1685.00')
    def test_malformed_json_lookup(self):
        response=self.client.post('/api/v1/licencias/consulta/','{',content_type='application/json')
        self.assertEqual(response.status_code,400)
    def test_unknown_public_hash(self):
        self.assertEqual(self.client.get('/verificar?hash='+'f'*64).status_code,404)
    @override_settings(REFRENDO_YEAR=2027)
    def test_no_cross_year_tariff_fallback(self):
        license=License.objects.select_related('business_type').get(number='TON-0001')
        license.last_renewed_year=2026
        with self.assertRaises(BusinessError): quote(license)
    def test_expired_document_still_authenticated_but_not_current(self):
        license=License.objects.select_related('business_type').get(number='TON-0001')
        f=QuoteForm({'delivery':'pickup','accept':'on'})
        self.assertTrue(f.is_valid())
        r=create_renewal(license,f);a=checkout(r)
        apply_payment(a.pk,'expire-case','approved',r.total,'MXN')
        c=Certificate.objects.get(renewal=r)
        from datetime import date
        with patch('refrendo.views.timezone.localdate',return_value=date(2027,1,1)):
            response=self.client.get('/verificar?hash='+c.digest)
        self.assertContains(response,'vigencia concluida')
