import uuid
from django.db import models
from django.core.validators import MinValueValidator
class BusinessType(models.Model):
    code = models.CharField('Código', max_length=30, unique=True)
    name = models.CharField('Giro comercial', max_length=150)
    low_risk = models.BooleanField('Bajo riesgo', default=True)
    required_department = models.CharField('Dependencia / dictamen requerido', max_length=250, blank=True)
    def __str__(self): return self.name
class License(models.Model):
    number = models.CharField('Número de licencia', max_length=40, unique=True)
    taxpayer = models.CharField('Nombre o razón social', max_length=180)
    trade_name = models.CharField('Nombre comercial', max_length=180)
    business_type = models.ForeignKey(BusinessType, on_delete=models.PROTECT, verbose_name='Giro')
    address = models.CharField('Domicilio del establecimiento', max_length=300)
    active = models.BooleanField('Activa', default=True)
    last_renewed_year = models.PositiveIntegerField('Último refrendo', default=2025)
    def __str__(self): return f'{self.number} · {self.trade_name}'
class Tariff(models.Model):
    year = models.PositiveIntegerField('Ejercicio')
    business_type = models.ForeignKey(BusinessType, on_delete=models.PROTECT)
    base = models.DecimalField('Refrendo', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    document_fee = models.DecimalField('Cédula', max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    mandatory_waste = models.DecimalField('Residuos obligatorios', max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    surcharge = models.DecimalField('Recargos liquidados', max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    source = models.CharField('Fundamento / versión', max_length=300)
    academic = models.BooleanField('Tabulador académico sin validar', default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['year', 'business_type'], name='tariff_year_type')]
    def __str__(self): return f'{self.year} · {self.business_type}'
class Contribution(models.Model):
    name = models.CharField('Aportación voluntaria', max_length=100)
    amount = models.DecimalField('Importe', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    active = models.BooleanField(default=True)
    def __str__(self): return self.name
class ShippingRate(models.Model):
    name = models.CharField('Zona', max_length=100)
    postal_prefix = models.CharField('Prefijo de CP', max_length=5, unique=True)
    amount = models.DecimalField('Tarifa', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    active = models.BooleanField(default=True)
    def __str__(self): return self.name
class Renewal(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente de pago'
        PAID = 'paid', 'Pagado'
        REJECTED = 'rejected', 'Pago rechazado'
        REVOKED = 'revoked', 'Revocado / pago revertido'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(License, on_delete=models.PROTECT, verbose_name='Licencia')
    year = models.PositiveIntegerField('Ejercicio')
    status = models.CharField('Estado', max_length=15, choices=Status.choices, default=Status.PENDING)
    snapshot = models.JSONField('Liquidación congelada', default=dict)
    total = models.DecimalField('Total MXN', max_digits=12, decimal_places=2)
    delivery = models.CharField('Entrega', max_length=10, choices=[('pickup', 'Ventanilla'), ('shipping', 'Domicilio')])
    shipping_address = models.JSONField('Dirección de entrega', default=dict)
    fulfillment = models.CharField('Logística', max_length=12, default='processing', choices=[
        ('processing', 'En preparación'), ('ready', 'Lista en ventanilla'), ('shipped', 'Enviada'), ('delivered', 'Entregada')])
    tracking_number = models.CharField('Guía de envío', max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['license', 'year'], name='one_renewal_per_year')]
    @property
    def folio(self): return f'TON-{self.year}-{str(self.id)[:8].upper()}'
    def __str__(self): return self.folio
class PaymentAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    renewal = models.ForeignKey(Renewal, on_delete=models.PROTECT, related_name='attempts')
    provider = models.CharField(max_length=20)
    preference_id = models.CharField(max_length=120, blank=True)
    checkout_url = models.URLField(max_length=1000, blank=True)
    provider_payment_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    status = models.CharField(max_length=30, default='created')
    method = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
class Certificate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    renewal = models.OneToOneField(Renewal, on_delete=models.PROTECT, related_name='certificate')
    payload = models.JSONField('Datos firmados')
    digest = models.CharField('HMAC-SHA256', max_length=64, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self._state.adding: raise ValueError('La carátula emitida es inmutable.')
        super().save(*args, **kwargs)
class AuditHead(models.Model):
    digest = models.CharField(max_length=64, default='0' * 64)
class AuditEvent(models.Model):
    created_at = models.DateTimeField()
    kind = models.CharField('Evento', max_length=50)
    renewal_id_text = models.CharField('Trámite', max_length=36, blank=True)
    details = models.JSONField('Datos', default=dict)
    previous_hash = models.CharField(max_length=64)
    digest = models.CharField(max_length=64, unique=True)
    def save(self, *args, **kwargs):
        if not self._state.adding: raise ValueError('Bitácora de solo adición.')
        super().save(*args, **kwargs)
    def delete(self, *args, **kwargs): raise ValueError('La bitácora no permite eliminar eventos.')
class LookupThrottle(models.Model):
    key = models.CharField(max_length=64, unique=True)
    window = models.BigIntegerField()
    count = models.PositiveIntegerField(default=0)

class PaymentRecord(models.Model):
    provider_id = models.CharField(max_length=100, unique=True)
    attempt = models.ForeignKey(PaymentAttempt, on_delete=models.PROTECT, related_name='payments')
    status = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=40, blank=True)
    provider_updated_at = models.DateTimeField()
    @property
    def status_label(self):
        return {'approved':'Aprobado','pending':'Pendiente de acreditación','in_process':'En proceso',
            'authorized':'Autorizado','rejected':'Rechazado','cancelled':'Cancelado','refunded':'Reembolsado',
            'charged_back':'Contracargo'}.get(self.status, 'En revisión')
    @property
    def method_label(self):
        return {'card':'Tarjeta','credit_card':'Tarjeta de crédito','debit_card':'Tarjeta de débito',
            'spei':'Transferencia SPEI','bank_transfer':'Transferencia bancaria','cash':'Efectivo',
            'ticket':'Efectivo en punto autorizado'}.get(self.method,'Medio registrado por la pasarela')
