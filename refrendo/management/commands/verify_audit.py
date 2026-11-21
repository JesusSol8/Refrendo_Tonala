from django.core.management.base import BaseCommand, CommandError
from refrendo.services import check_audit
class Command(BaseCommand):
    help = 'Verifica toda la cadena HMAC de la bitácora.'
    def handle(self, *args, **options):
        ok, event = check_audit()
        if not ok: raise CommandError(f'Cadena inconsistente. Evento: {event or "cabecera"}')
        self.stdout.write(self.style.SUCCESS('Integridad verificada.'))
