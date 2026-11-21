from django.conf import settings
def portal(request):
    return {'demo_mode': settings.DEMO_MODE, 'fiscal_year': settings.REFRENDO_YEAR}
