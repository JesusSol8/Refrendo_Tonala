from django.db import migrations

def protect(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    tables = ['refrendo_auditevent', 'refrendo_certificate']
    for table in tables:
        if vendor == 'sqlite':
            for action in ('UPDATE','DELETE'):
                schema_editor.execute(f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'append-only record'); END;")
        elif vendor == 'postgresql':
            schema_editor.execute(f"CREATE FUNCTION {table}_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'append-only record'; END; $$;")
            schema_editor.execute(f'CREATE TRIGGER {table}_no_mutation BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION {table}_immutable();')

def unprotect(apps, schema_editor):
    for table in ['refrendo_auditevent', 'refrendo_certificate']:
        if schema_editor.connection.vendor == 'sqlite':
            for action in ('update','delete'): schema_editor.execute(f'DROP TRIGGER IF EXISTS {table}_no_{action}')
        elif schema_editor.connection.vendor == 'postgresql':
            schema_editor.execute(f'DROP TRIGGER IF EXISTS {table}_no_mutation ON {table}')
            schema_editor.execute(f'DROP FUNCTION IF EXISTS {table}_immutable()')

class Migration(migrations.Migration):
    dependencies = [('refrendo', '0001_initial')]
    operations = [migrations.RunPython(protect, unprotect)]
