from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from refrendo.payments import reconcile
from refrendo.services import BusinessError
class Command(BaseCommand):
    help = 'Recupera un pago desde Mercado Pago tras una notificación no recibida.'
    def add_arguments(self, parser): parser.add_argument('payment_id')
    def handle(self, *args, **options):
        if settings.DEMO_MODE: raise CommandError('Requiere DEMO_MODE=0 y credenciales.')
        try: renewal = reconcile(options['payment_id'])
        except BusinessError as exc: raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(renewal.folio + ': ' + renewal.get_status_display()))
