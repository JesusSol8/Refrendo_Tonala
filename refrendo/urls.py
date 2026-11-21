from django.urls import path
from . import views
urlpatterns = [
    path('api/v1/licencias/consulta/', views.api_lookup, name='api_lookup'),
    path('', views.home, name='home'), path('liquidacion/', views.liquidation, name='liquidation'),
    path('api/v1/cotizacion/', views.api_quote, name='api_quote'),
    path('tramite/<uuid:pk>/', views.renewal, name='renewal'),
    path('tramite/<uuid:pk>/pagar/', views.pay, name='pay'),
    path('pago-demostracion/<uuid:pk>/', views.demo_payment, name='demo_payment'),
    path('api/v1/tramites/<uuid:pk>/', views.api_status, name='api_status'),
    path('api/v1/mercadopago/webhook/', views.mp_webhook, name='mp_webhook'),
    path('tramite/<uuid:pk>/caratula.pdf', views.certificate_download, name='certificate_pdf'),
    path('tramite/<uuid:pk>/qr.png', views.certificate_qr, name='certificate_qr'),
    path('verificar', views.verify, name='verify'), path('privacidad/', views.privacy, name='privacy'),
    path('salud/', views.health, name='health'), path('gestion/', views.dashboard, name='dashboard'),
    path('gestion/<uuid:pk>/entrega/', views.fulfillment, name='fulfillment'),
    path('gestion/bitacora/', views.audit_view, name='audit'), path('gestion/conciliacion.csv', views.export_csv, name='export_csv'),
]

