from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from refrendo.models import BusinessType, License, Tariff, Contribution, ShippingRate, AuditHead
class Command(BaseCommand):
    help = 'Carga un padrón ficticio y catálogos académicos sin modificar trámites existentes.'
    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO_MODE: raise CommandError('Solo disponible en DEMO_MODE=1.')
        types = [('PAP', 'Papelería y artículos de oficina', True, '', '680.00'),
                 ('ART', 'Venta de artesanías', True, '', '740.00'),
                 ('ABA', 'Abarrotes sin venta de alcohol', True, '', '820.00'),
                 ('RES', 'Restaurante con instalaciones de gas', False, 'Protección Civil', '1200.00'),
                 ('TAL', 'Taller con emisiones y maquinaria', False, 'Ecología e Inspección y Vigilancia', '1400.00')]
        catalog = {}
        for code, name, risk, department, base in types:
            bt, _ = BusinessType.objects.get_or_create(code=code, defaults={'name':name,'low_risk':risk,'required_department':department})
            catalog[code] = bt
            Tariff.objects.get_or_create(year=settings.REFRENDO_YEAR, business_type=bt, defaults={
                'base':base, 'document_fee':'331.00', 'mandatory_waste':'674.00', 'surcharge':'0.00',
                'source':'Tabulador académico v1; referencia Ley 2026 art. 91 I c (cédula). Base y recargos simulados, sin validación fiscal.', 'academic':True})
        rows = [('TON-0001','María López García','Papelería La Ilusión','PAP',True,2025),
                ('TON-0002','Artesanías del Sol SA de CV','Artesanías del Sol','ART',True,2025),
                ('TON-0003','Comercial La Plaza SA de CV','Restaurante La Plaza','RES',True,2025),
                ('TON-0004','Taller El Roble SA de CV','Taller El Roble','TAL',True,2025),
                ('TON-0005','Juan Pérez Ruiz','Papelería Juan','PAP',False,2025),
                ('TON-0006','Ana Torres Díaz','Artesanías Ana','ART',True,2023),
                ('TON-0007','Luis Ramírez Soto','Abarrotes La Esquina','ABA',True,2025)]
        for number,taxpayer,trade,code,active,last in rows:
            License.objects.get_or_create(number=number, defaults={'taxpayer':taxpayer,'trade_name':trade,
                'business_type':catalog[code],'active':active,'last_renewed_year':last,
                'address':'Calle de Demostración 123, Centro, Tonalá, Jalisco'})
        for name, amount in [('Cruz Roja','25.00'),('Bomberos y Protección Civil','30.00'),('Mejoramiento de espacios públicos','20.00')]:
            Contribution.objects.get_or_create(name=name, defaults={'amount':amount})
        for prefix, name, amount in [('454','Zona Tonalá','120.00'),('455','Zona metropolitana convenida','160.00'),('45400','Tonalá Centro','95.00')]:
            ShippingRate.objects.get_or_create(postal_prefix=prefix, defaults={'name':name,'amount':amount})
        AuditHead.objects.get_or_create(pk=1)
        self.stdout.write(self.style.SUCCESS('7 licencias ficticias y catálogos de demostración disponibles.'))
