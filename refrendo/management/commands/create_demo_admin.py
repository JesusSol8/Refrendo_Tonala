import secrets
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
class Command(BaseCommand):
    help = 'Genera un administrador local de demostración con contraseña aleatoria.'
    def handle(self,*args,**options):
        if not settings.DEBUG or not settings.DEMO_MODE:
            raise CommandError('Solo permitido en demostración local con DEBUG=1.')
        path = settings.BASE_DIR / '.demo-access.txt'
        if User.objects.filter(username='demo_admin').exists():
            self.stdout.write('Administrador existente. Consulta .demo-access.txt o usa createsuperuser para una cuenta nueva.')
            return
        password = secrets.token_urlsafe(14)
        User.objects.create_superuser('demo_admin','demo@example.test',password)
        path.write_text('ACCESO LOCAL DE DEMOSTRACIÓN\nURL: http://127.0.0.1:8000/admin/\nUsuario: demo_admin\nContraseña: '+password+'\nNo publicar este archivo ni reutilizar la contraseña.\n',encoding='utf-8')
        self.stdout.write(self.style.SUCCESS('Cuenta local creada. Credenciales en .demo-access.txt'))
