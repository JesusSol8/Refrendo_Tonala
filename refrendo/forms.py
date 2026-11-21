from django import forms
from .models import Contribution
class LookupForm(forms.Form):
    number = forms.CharField(label='Número de licencia municipal', max_length=40,
        widget=forms.TextInput(attrs={'placeholder': 'Ej. TON-0001', 'autocomplete': 'off'}))
    taxpayer = forms.CharField(label='Nombre o razón social del contribuyente', max_length=180,
        widget=forms.TextInput(attrs={'placeholder': 'Como aparece en tu licencia', 'autocomplete': 'organization'}))
class QuoteForm(forms.Form):
    contributions = forms.ModelMultipleChoiceField(label='Aportaciones voluntarias', queryset=Contribution.objects.none(),
        required=False, widget=forms.CheckboxSelectMultiple)
    delivery = forms.ChoiceField(label='Modalidad de entrega', choices=[('pickup', 'Recolección en ventanilla · sin costo'),
        ('shipping', 'Envío a domicilio · según código postal')], widget=forms.RadioSelect, initial='pickup')
    recipient = forms.CharField(label='Nombre de quien recibe', max_length=100, required=False)
    street = forms.CharField(label='Calle', max_length=100, required=False)
    exterior = forms.CharField(label='Número exterior', max_length=20, required=False)
    interior = forms.CharField(label='Número interior (opcional)', max_length=20, required=False)
    neighborhood = forms.CharField(label='Colonia', max_length=100, required=False)
    postal_code = forms.RegexField(label='Código postal', regex=r'^\d{5}$', max_length=5, required=False,
        error_messages={'invalid': 'Escribe un código postal de 5 dígitos.'}, widget=forms.TextInput(attrs={'inputmode': 'numeric'}))
    municipality = forms.CharField(label='Municipio', max_length=80, required=False, initial='Tonalá')
    state = forms.CharField(label='Estado', max_length=80, required=False, initial='Jalisco')
    phone = forms.RegexField(label='Teléfono de contacto', regex=r'^\d{10}$', max_length=10, required=False,
        error_messages={'invalid': 'Escribe un teléfono de 10 dígitos.'}, widget=forms.TextInput(attrs={'inputmode': 'tel'}))
    accept = forms.BooleanField(label='Revisé mis datos y acepto el aviso de privacidad y el uso académico del sistema.')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contributions'].queryset = Contribution.objects.filter(active=True)
        self.fields['contributions'].label_from_instance = lambda c: f'{c.name} · ${c.amount} MXN'
    def clean(self):
        data = super().clean()
        if data.get('delivery') == 'shipping':
            for field in ('recipient', 'street', 'exterior', 'neighborhood', 'postal_code', 'municipality', 'state', 'phone'):
                if not data.get(field) and field not in self.errors:
                    self.add_error(field, 'Este dato es obligatorio para el envío.')
        return data
    def address(self):
        if self.cleaned_data.get('delivery') != 'shipping': return {}
        return {k: self.cleaned_data.get(k, '') for k in
            ('recipient', 'street', 'exterior', 'interior', 'neighborhood', 'postal_code', 'municipality', 'state', 'phone')}
class DemoPaymentForm(forms.Form):
    method = forms.ChoiceField(label='Medio de pago de prueba', choices=[('card', 'Tarjeta de crédito / débito'),
        ('spei', 'Transferencia SPEI'), ('cash', 'Efectivo en punto autorizado')])
    outcome = forms.ChoiceField(label='Resultado a demostrar', choices=[('approved', 'Aprobado'),
        ('pending', 'Pendiente de acreditación'), ('rejected', 'Rechazado')])
class FulfillmentForm(forms.Form):
    fulfillment = forms.ChoiceField(label='Estado logístico', choices=[('processing', 'En preparación'),
        ('ready', 'Lista en ventanilla'), ('shipped', 'Enviada'), ('delivered', 'Entregada')])
    tracking_number = forms.CharField(label='Número de guía', max_length=100, required=False)
    def clean(self):
        data = super().clean()
        if data.get('fulfillment') == 'shipped' and not data.get('tracking_number'):
            self.add_error('tracking_number', 'Captura la guía del envío.')
        return data

