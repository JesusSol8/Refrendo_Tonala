# 📋 Especificación de Requerimientos de Software (SRS)
## Proyecto Integrador: Sistema de Refrendo de Licencias Municipales en Línea
**Materia:** Gestión de Proyectos | **Nivel:** 7.º Semestre - Ingeniería de Software  
**Cliente Simulado:** Ayuntamiento de Tonalá, Jalisco  

---

> 📌 **Objetivo del Proyecto:**  
> Desarrollar una plataforma web ciudadana para el **Ayuntamiento de Tonalá** que permita a los contribuyentes con giros comerciales de bajo riesgo realizar el refrendo de su licencia municipal en línea. El sistema integrará cálculo dinámico de impuestos, aportaciones voluntarias, pasarela de pagos con Mercado Pago, opción de envío a domicilio y verificación de autenticidad mediante código QR.

---

## 🎨 1. Requerimientos de Diseño e Identidad Visual (UI/UX)

* **UI-01 | Línea Gráfica Institucional:** La interfaz debe replicar de manera precisa la identidad visual oficial del Ayuntamiento de Tonalá (paleta de colores institucionales, isotipos/logotipos y tipografía utilizada en portales gubernamentales como el de Pago de Predial).
* **UI-02 | Responsividad y Accesibilidad:** Diseño 100% *Responsive* (adaptable a dispositivos móviles, tablets y computadoras) cumpliendo con pautas básicas de accesibilidad web (WCAG 2.1 AA).
* **UI-03 | Experiencia Ciudadana:** Interfaz intuitiva, en español claro, minimizando los clics necesarios para completar el trámite.

---

## ⚙️ 2. Requerimientos Funcionales (RF)

### 🔍 Módulo 1: Consulta y Elegibilidad
* **RF-01 | Búsqueda de Licencia:** El portal debe solicitar únicamente dos datos obligatorios para iniciar la consulta:
  * Número de Licencia Municipal.
  * Nombre o Razón Social del Contribuyente.
* **RF-02 | Validación de Giro Comercial (Filtro de Riesgo):**
  * El sistema debe verificar si la licencia pertenece a giros comerciales que **NO requieran verificación/inspección previa** (ej. Giros Tipo A / Bajo Riesgo).
  * *Regla de Negocio:* Si el giro requiere dictamen de Protección Civil, Ecología o Inspección, el sistema detendrá el proceso digital y mostrará una alerta indicando la dependencia a la que debe acudir el ciudadano.

### 💰 Módulo 2: Liquidación y Aportaciones
* **RF-03 | Aplicación de Ley de Ingresos:** Cálculo automático del costo del refrendo basado en la Ley de Ingresos vigente del Ayuntamiento de Tonalá y sus tabuladores vigentes.
* **RF-04 | Desglose y Aportaciones Voluntarias:**
  * Desglose detallado del monto base a pagar.
  * Opciones seleccionables (*checkboxes*) para aportaciones voluntarias configuradas por el Municipio (ej. Cruz Roja, Bomberos/Protección Civil, Aseo Público/Basura).
  * Actualización dinámica del total a pagar según las opciones seleccionadas o desmarcadas por el contribuyente.

### 📦 Módulo 3: Modalidad de Entrega (Logística)
* **RF-05 | Elección de Método de Entrega:** El usuario elegirá entre dos opciones para recibir su carátula física:
  1. **Recolección en Ventanilla:** Sin costo extra (recoge en las oficinas de la Dirección de Padrón y Licencias).
  2. **Envío a Domicilio:** Entrega a través de empresa de paquetería convenida.
* **RF-06 | Cálculo de Envío:** En caso de elegir envío a domicilio, se solicitará la dirección completa de entrega y se sumará automáticamente la tarifa de envío al costo total antes del pago.

### 💳 Módulo 4: Procesamiento de Pago
* **RF-07 | Integración con Mercado Pago:** Conexión vía API/SDK con Mercado Pago para aceptar:
  * Tarjetas de crédito y débito.
  * Transferencias bancarias (SPEI).
  * Depósitos en efectivo en puntos autorizados.
* **RF-08 | Notificación en Tiempo Real (Webhooks/IPN):** Escucha e interpretación de notificaciones de pago instantáneas para actualizar el estado del trámite a "Pagado" de forma automática y segura.

### 📄 Módulo 5: Emisión Digital y Trazabilidad QR
* **RF-09 | Emisión de Carátula Digital:** Generación de la carátula oficial en formato PDF descargable al confirmar el pago exitoso.
* **RF-10 | Generación de Código QR de Autenticidad:** La carátula digital debe incluir un código QR único codificado con un *hash* de verificación inmutable.
* **RF-11 | Portal de Verificación Pública:** Al escanear el QR desde cualquier smartphone, redirigirá a una URL oficial del Ayuntamiento (`https://tonala.gob.mx/verificar?...`) mostrando los datos públicos que confirman la autenticidad y vigencia del documento.

---

## 🛡️ 3. Requerimientos No Funcionales (RNF)

| Código | Dimensión | Especificación Técnica |
| :--- | :--- | :--- |
| **RNF-01** | **Seguridad** | Cifrado obligatorio en tránsito (**HTTPS / TLS 1.3**). Firmas digitales SHA-256 para validación de QRs. |
| **RNF-02** | **Disponibilidad** | Arquitectura con 99.5% de disponibilidad para soportar picos de alta demanda en periodos de refrendo masivo. |
| **RNF-03** | **Integración** | Comunicación mediante APIs RESTful estructuradas entre el portal web, la base de datos de Padrón y Licencias y Mercado Pago. |
| **RNF-04** | **Trazabilidad y Auditoría** | Registro inmutable en bitácora (*log*) de cada transacción, incluyendo ID de pago, folio de licencia, monto y datos de envío para la conciliación contable de Tesorería. |

---

## 🎯 4. Entregables del Proyecto

1. **Documento de Arquitectura y Modelo de Base de Datos (DER).**
2. **Repositorio Git** con estrategia de ramificación *GitFlow*.
3. **Plataforma Web Funcional** desplegada en entorno de pruebas.
4. **Matriz de Trazabilidad de Requerimientos (RTM)** y Plan de Pruebas.