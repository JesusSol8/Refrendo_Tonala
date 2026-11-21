import os, json
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
import dj_database_url
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv('DEBUG', '1') == '1'
DEMO_MODE = os.getenv('DEMO_MODE', '1') == '1'
local_settings = BASE_DIR / '.local-settings.json'
if DEBUG and DEMO_MODE and local_settings.exists():
    local_data = json.loads(local_settings.read_text(encoding='utf-8'))
    for name in ('SECRET_KEY', 'DOCUMENT_SIGNING_KEY', 'AUDIT_KEY'):
        if name in local_data: os.environ.setdefault(name, local_data[name])
SECRET_KEY = os.getenv('SECRET_KEY', 'academico-local-cambiar-antes-de-publicar-2026')
DOCUMENT_SIGNING_KEY = os.getenv('DOCUMENT_SIGNING_KEY', SECRET_KEY)
AUDIT_KEY = os.getenv('AUDIT_KEY', SECRET_KEY)
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
CSRF_TRUSTED_ORIGINS = [s for s in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if s]
MP_ACCESS_TOKEN = os.getenv('MP_ACCESS_TOKEN', '')
MP_WEBHOOK_SECRET = os.getenv('MP_WEBHOOK_SECRET', '')
MP_SANDBOX = os.getenv('MP_SANDBOX', '1') == '1'
REFRENDO_YEAR = int(os.getenv('REFRENDO_YEAR', '2026'))
if not DEBUG:
    for name in ('SECRET_KEY', 'DOCUMENT_SIGNING_KEY', 'AUDIT_KEY'):
        if len(os.getenv(name, '')) < 32:
            raise ImproperlyConfigured(f'{name} debe tener al menos 32 caracteres.')
    if not PUBLIC_BASE_URL.startswith('https://'):
        raise ImproperlyConfigured('PUBLIC_BASE_URL debe usar HTTPS en despliegue.')
if not DEMO_MODE and (not MP_ACCESS_TOKEN or not MP_WEBHOOK_SECRET):
    raise ImproperlyConfigured('Configura credenciales de Mercado Pago o activa DEMO_MODE.')
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
                  'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'refrendo']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
              'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
              'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
              'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
              'refrendo.middleware.ResponsePolicyMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request',
              'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages',
              'refrendo.context.portal']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': dj_database_url.config(default=f'sqlite:///{BASE_DIR / "db.sqlite3"}', conn_max_age=60)}
if DATABASES['default']['ENGINE'].endswith('sqlite3'):
    DATABASES['default']['OPTIONS'] = {'timeout': 30}
AUTH_PASSWORD_VALIDATORS = [{'NAME': f'django.contrib.auth.password_validation.{n}'} for n in
    ['UserAttributeSimilarityValidator', 'MinimumLengthValidator', 'CommonPasswordValidator', 'NumericPasswordValidator']]
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/admin/login/'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
DATA_UPLOAD_MAX_MEMORY_SIZE = 32768
LOGGING = {'version': 1, 'disable_existing_loggers': False,
           'handlers': {'console': {'class': 'logging.StreamHandler'}},
           'root': {'handlers': ['console'], 'level': 'INFO'}}

TRUST_PROXY = os.getenv('TRUST_PROXY', '0') == '1'
