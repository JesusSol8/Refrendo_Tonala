"""Inicio local reproducible sin depender de PowerShell ni de activar entornos."""
import importlib.util
import os
from pathlib import Path
import secrets
import subprocess
import sys
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
packages = ROOT / '.packages'
temp = ROOT / '.temp'
packages.mkdir(exist_ok=True)
temp.mkdir(exist_ok=True)
os.environ['TEMP'] = os.environ['TMP'] = str(temp)
os.environ['PYTHONPATH'] = str(packages)
sys.path.insert(0, str(packages))
# Las claves persisten para que los documentos y la bitácora sobrevivan reinicios.
local = ROOT / '.local-settings.json'
import json
if not local.exists():
    local.write_text(json.dumps({key: secrets.token_urlsafe(48) for key in
        ['SECRET_KEY','DOCUMENT_SIGNING_KEY','AUDIT_KEY']}),encoding='utf-8')
for key,value in json.loads(local.read_text(encoding='utf-8')).items(): os.environ.setdefault(key,value)
os.environ.setdefault('DEBUG','1')
os.environ.setdefault('DEMO_MODE','1')
if not (packages / 'django').exists():
    print('Instalando dependencias locales. Solo se necesita Internet en esta primera ejecución.',flush=True)
    subprocess.run([sys.executable,'-m','pip','install','--no-cache-dir','--target',str(packages),'-r','requirements.txt'],check=True)
def manage(*args): subprocess.run([sys.executable,'manage.py',*args],check=True)
manage('migrate','--noinput')
if os.environ['DEMO_MODE']=='1':
    manage('seed_demo')
    if os.environ['DEBUG']=='1': manage('create_demo_admin')
manage('collectstatic','--noinput')
print('\nPortal: http://127.0.0.1:8000\nAdministración: http://127.0.0.1:8000/admin/\nPresiona Ctrl+C para detener.\n',flush=True)
subprocess.run([sys.executable,'-m','waitress','--listen=127.0.0.1:8000','--threads=4','config.wsgi:application'],check=True)
