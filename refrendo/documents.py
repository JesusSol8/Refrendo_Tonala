from io import BytesIO
from xml.sax.saxutils import escape
import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from django.conf import settings
from django.urls import reverse

BURGUNDY = colors.HexColor('#671c36')

def verification_url(certificate):
    return settings.PUBLIC_BASE_URL + reverse('verify') + '?hash=' + certificate.digest

def qr_bytes(certificate):
    stream = BytesIO()
    qrcode.make(verification_url(certificate), error_correction=qrcode.constants.ERROR_CORRECT_M).save(stream, format='PNG')
    return stream.getvalue()

def certificate_pdf(certificate):
    out = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Label', fontName='Helvetica-Bold', fontSize=8, textColor=BURGUNDY, spaceAfter=4))
    styles.add(ParagraphStyle(name='Value', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=11))
    styles.add(ParagraphStyle(name='SmallNote', fontSize=8, leading=11, textColor=colors.HexColor('#50505a')))
    styles.add(ParagraphStyle(name='DocTitle', fontName='Helvetica-Bold', fontSize=22, leading=27, textColor=BURGUNDY, spaceAfter=9))
    p = certificate.payload
    doc = SimpleDocTemplate(out, pagesize=(210*mm, 297*mm), rightMargin=19*mm, leftMargin=19*mm,
        topMargin=17*mm, bottomMargin=21*mm, title='Carátula de refrendo ' + p['folio'], author='Proyecto académico Tonalá')
    logo = settings.BASE_DIR / 'static/portal/tonala.png'
    story = [Table([[Image(str(logo), width=30*mm, height=22*mm),
        Paragraph('TONALÁ<br/>Dirección de Padrón y Licencias<br/>Sistema de refrendo en línea', styles['Heading3'])]], colWidths=[40*mm, 132*mm]),
        Spacer(1, 7*mm), Paragraph('Refrendo de licencia municipal', styles['DocTitle']),
        Paragraph('EJERCICIO ' + str(p['year']) + ' · ' + p['folio'], styles['Heading3']), Spacer(1, 4*mm)]
    if p.get('academic'):
        note = Table([[Paragraph('DEMOSTRACIÓN ACADÉMICA · SIN VALIDEZ OFICIAL<br/>Datos ficticios. No acredita autorización municipal ni pago real.', styles['SmallNote'])]], colWidths=[172*mm])
        note.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f5e9dd')),('BOX',(0,0),(-1,-1),1,colors.HexColor('#b68c54')),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
        story += [note, Spacer(1, 6*mm)]
    for label, key in [('LICENCIA MUNICIPAL', 'license'), ('CONTRIBUYENTE', 'taxpayer'),
                        ('ESTABLECIMIENTO', 'trade_name'), ('GIRO COMERCIAL', 'business_type'), ('DOMICILIO DEL ESTABLECIMIENTO', 'business_address')]:
        story.append(KeepTogether([Paragraph(label, styles['Label']), Paragraph(escape(str(p[key])), styles['Value'])]))
    summary = Table([[Paragraph('IMPORTE PAGADO', styles['Label']), Paragraph('VIGENCIA HASTA', styles['Label'])],
        [Paragraph('$' + p['total'] + ' MXN', styles['Heading2']), Paragraph(p['valid_until'], styles['Heading2'])]], colWidths=[86*mm,86*mm])
    summary.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f3f2f0')),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story += [summary, Spacer(1, 5*mm)]
    qr = Image(BytesIO(qr_bytes(certificate)), width=36*mm, height=36*mm)
    qr.hAlign = 'LEFT'
    verify_note = Paragraph('VERIFICA LA AUTENTICIDAD<br/><br/>Escanea el código QR para consultar el estado y la vigencia del documento en el portal de verificación.<br/><br/>El sello HMAC-SHA256 permite detectar cambios en los datos emitidos.', styles['SmallNote'])
    block = Table([[qr, verify_note]], colWidths=[43*mm,129*mm])
    story += [KeepTogether([block, Spacer(1,3*mm), Paragraph('Sello: ' + certificate.digest, styles['SmallNote'])])]
    def footer(canvas, document):
        canvas.setStrokeColor(BURGUNDY)
        canvas.line(19*mm,17*mm,191*mm,17*mm)
        canvas.setFont('Helvetica',8)
        canvas.drawString(19*mm,12*mm,'Proyecto integrador · Gestión de Proyectos · Tonalá, Jalisco')
        canvas.drawRightString(191*mm,12*mm,str(document.page))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
