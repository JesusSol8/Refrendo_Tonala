from django.contrib import admin
from .models import BusinessType, License, Tariff, Contribution, ShippingRate, Renewal, PaymentAttempt, PaymentRecord, Certificate, AuditEvent
admin.site.site_header = 'Tonalá · Administración de refrendos'
admin.site.site_title = 'Gestión municipal'
admin.site.index_title = 'Catálogos y operación'
@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('number', 'trade_name', 'taxpayer', 'business_type', 'active', 'last_renewed_year')
    search_fields = ('number', 'trade_name', 'taxpayer')
    list_filter = ('active', 'business_type')
@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('year', 'business_type', 'base', 'document_fee', 'mandatory_waste', 'academic')
    list_filter = ('year', 'academic')
class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
@admin.register(Renewal)
class RenewalAdmin(ReadOnlyAdmin):
    list_display = ('id', 'license', 'year', 'status', 'total', 'delivery', 'created_at')
    list_filter = ('status', 'delivery', 'year')
    search_fields = ('license__number', 'license__taxpayer')
@admin.register(AuditEvent)
class AuditAdmin(ReadOnlyAdmin):
    list_display = ('id', 'created_at', 'kind', 'renewal_id_text')
    list_filter = ('kind',)
for model in (PaymentAttempt, PaymentRecord, Certificate): admin.site.register(model, ReadOnlyAdmin)
for model in (BusinessType, Contribution, ShippingRate): admin.site.register(model)
