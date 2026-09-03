# b) Pasarelas de pago

---

## 1. Qué es una pasarela de pago y quiénes intervienen

Una **pasarela de pago** es el servicio que conecta una tienda en línea con el sistema financiero
para cobrar de forma electrónica. Su función esencial no es solo "cobrar": es **sacar los datos
sensibles del dominio del comercio**. La tienda nunca ve ni almacena el número de tarjeta; el
cliente los ingresa en la infraestructura de la pasarela, que está certificada para ello.

**Actores de una transacción con tarjeta:**

| Actor | Rol |
|---|---|
| **Titular** | El cliente que paga |
| **Comercio** | La tienda que cobra |
| **Pasarela** | Transporta y cifra los datos de la operación |
| **Adquirente** | El banco del comercio; procesa el cobro y liquida el dinero |
| **Marca** | Visa, Mastercard: la red que enruta la operación |
| **Emisor** | El banco del cliente; autoriza o rechaza según saldo, límite y riesgo |

**Las tres etapas de un cobro con tarjeta:**

1. **Autorización** — se consulta al emisor si hay fondos o cupo. Si acepta, **retiene** el monto,
   pero todavía no lo mueve.
2. **Captura** — el comercio confirma el cobro. Puede ser inmediata (compra) o diferida (reserva
   de hotel, alquiler de auto).
3. **Liquidación** — el dinero se acredita al comercio, típicamente días después.

Esta separación explica una situación frecuente: el cliente ve el cargo "pendiente" en su tarjeta
y el comercio todavía no tiene el dinero.

**PCI DSS.** Es el estándar de seguridad de la industria de tarjetas. Cumplirlo es costoso y
exigente, y es la razón por la cual **ningún comercio pequeño debe almacenar datos de tarjeta**:
delegar el cobro en una pasarela certificada traslada esa carga.

---

## 2. Formas de pago en línea

### 2.1 Tarjeta de débito

Debita **directamente del saldo** de la cuenta del cliente. La autorización verifica fondos
disponibles en el momento. Al no haber crédito de por medio, el riesgo de impago es menor y las
comisiones suelen ser algo más bajas, pero el margen de disputa del cliente (contracargo) también
es más limitado en varias plazas.

### 2.2 Tarjeta de crédito

El emisor adelanta el dinero contra la línea de crédito del cliente. Introduce dos elementos que
el débito no tiene:

- **Contracargo (chargeback)** — el cliente puede disputar el cargo ante su emisor. Si prospera,
  el dinero se le devuelve y el comercio lo pierde, además de pagar una penalidad. Es el
  principal riesgo económico del comercio electrónico.
- **Autenticación reforzada (3-D Secure)** — un paso adicional de verificación con el emisor que
  traslada la responsabilidad del fraude al banco.

### 2.3 Pago con QR

El comercio genera un código bidimensional que contiene los datos del cobro; el cliente lo escanea
desde la aplicación de su banco y confirma. Hay dos variantes:

- **QR estático** — codifica solo la cuenta destino; el cliente escribe el monto. Sirve para un
  mostrador, no para un e-commerce.
- **QR dinámico** — se genera por operación e incluye monto y referencia. Es el que sirve para
  comercio electrónico, porque permite conciliar automáticamente qué pedido pagó cada cliente.

**En Bolivia el QR es un caso destacado a nivel regional.** El sistema **QR Simple** se implementó
en 2019 y convirtió a Bolivia en el **primer país de Latinoamérica en adoptar pagos
interoperables** bajo esta tecnología. El Banco Central de Bolivia opera **QR BCB Bolivia**, un
estándar único y universal que integra a todo el sistema financiero: un usuario de cualquier
entidad —banco, cooperativa, entidad financiera de vivienda o institución financiera de
desarrollo— puede pagar y cobrar con el mismo instrumento, sin importar dónde tenga su cuenta.

Su adopción es masiva: según los informes de vigilancia del sistema de pagos, los pagos con QR
representan **cerca de cuatro de cada diez transacciones** en el país. En octubre de 2025 el BCB
lanzó **OpenBCB**, y anunció avances para integrar billeteras digitales y sistemas como el PIX
brasileño.

La acreditación es prácticamente **inmediata** y no hay contracargo, lo que lo vuelve muy
atractivo para el comercio — y menos protegido para el comprador.

### 2.4 Transferencias

El cliente ordena una transferencia desde su banca en línea a la cuenta del comercio. Es el método
más barato y el **más difícil de automatizar**: el comercio no se entera de que le pagaron hasta
que revisa su extracto, y debe **conciliar** manualmente qué transferencia corresponde a qué
pedido. Se mitiga exigiendo una referencia única por pedido, pero depende de que el cliente la
escriba bien. Por eso las plataformas serias lo ofrecen solo como respaldo.

### 2.5 Entornos de prueba (sandbox)

Toda pasarela ofrece un **entorno de pruebas**: credenciales y tarjetas ficticias que recorren el
flujo completo sin mover dinero real. Es lo que permite desarrollar y demostrar una integración
sin una cuenta comercial habilitada, y es el modo que usa este proyecto conforme al **RNF09**.

---

## 3. LIBÉLULA — la pasarela del medio boliviano

**Qué es.** Libélula se presenta como la primera solución **multicanal** de pagos y facturación en
línea de Bolivia. Permite a negocios digitales cobrar directamente con tarjetas nacionales e
internacionales y con los demás medios electrónicos disponibles en el mercado local.

**Cómo funciona.** Opera sobre el concepto de **deuda**: la empresa registra en la plataforma una
cuenta pendiente de cobro de su cliente final, y Libélula la expone para que se pague por
cualquiera de sus canales. Ese modelo —cobrar una deuda registrada, en lugar de procesar un
carrito— es lo que la hace natural para servicios y facturación recurrente, y no solo para
tiendas.

**Métodos de pago que ofrece:**

- Tarjetas de **crédito y débito**, bolivianas y del exterior.
- **QR Simple**, pagable desde la banca móvil de múltiples bancos.
- **Tigo Money** (billetera móvil).
- **Botón de Pago BCP**.

**Integración.** La empresa hace una llamada **POST HTTP** a la plataforma con los datos de la
deuda a cobrar, y Libélula devuelve la URL donde el cliente completa el pago. Además de la API,
ofrece **plugins y extensiones para WooCommerce, Magento, PrestaShop y OpenCart**. Su manual de
integración es público —la versión 2.145 es de abril de 2023— lo que facilita evaluarla antes de
contratarla.

**Seguridad.** Procesamiento en tiempo real, cifrado de datos y cumplimiento de la normativa
**PCI DSS**.

### Por qué el proyecto no la integra

Libélula es **la opción correcta para un comercio boliviano real**: cubre los medios de pago que
la gente usa aquí, sobre todo el QR, que ninguna pasarela internacional resuelve bien en Bolivia.

Sin embargo, habilitar una cuenta exige un **convenio comercial** con la empresa y documentación
de un negocio constituido. Eso la vuelve inviable para un proyecto académico con tres semanas de
plazo. Por eso se documenta aquí conforme al enunciado, pero la integración se hace con Stripe en
modo de pruebas — ver [`docs/06-decisiones-tecnicas.md`](../06-decisiones-tecnicas.md) §6.7.

---

## 4. PayPal

**Qué es.** Una de las plataformas de pago en línea más reconocidas del mundo, con casi tres
décadas de operación. Funciona a la vez como **billetera digital** (el usuario carga saldo o
vincula su tarjeta) y como **procesador de pagos** para comercios.

**Cómo se integra.** Botón de pago, checkout alojado, SDK para varios lenguajes y **webhooks**
para notificar el resultado. Su entorno de pruebas —**PayPal Sandbox**— permite crear cuentas
ficticias de comprador y vendedor y recorrer el flujo completo sin dinero real. El sandbox es
específico por región: al registrarse se elige el país.

**Comisiones.** Para el vendedor, las transacciones internacionales rondan el **4,4 % más una
tarifa fija** según la moneda; las comisiones exactas varían por país y por tipo de operación, y
deben consultarse en la tabla oficial vigente.

### ⚠️ La limitación que importa para Bolivia

**PayPal no permite recibir pagos en Bolivia de forma directa.** Un usuario boliviano puede
*pagar* con PayPal, pero una cuenta boliviana no puede *cobrar* y retirar fondos como lo haría
una de otro país. Esta restricción es determinante: descarta a PayPal como pasarela de una tienda
boliviana real, con independencia de sus comisiones.

Para este proyecto, PayPal queda como **plan de respaldo únicamente en su entorno sandbox**, por
si Stripe presentara alguna restricción durante el desarrollo.

---

## 5. Stripe

**Qué es.** Plataforma de infraestructura de pagos orientada a desarrolladores. Es la pasarela que
**este proyecto integra** (en modo de pruebas).

**Comisiones.** El cargo estándar para tarjetas nacionales en línea es **2,9 % + $0,30** por
transacción. Las tarjetas internacionales agregan **+1,5 %**, y la conversión de moneda **+1 %**.
No cobra costo de alta, ni mensualidad, ni cargos ocultos por cierre de cuenta.

**Por qué se eligió para este proyecto:**

1. **Cuenta inmediata en modo de pruebas**, sin trámite comercial ni documentación de empresa.
2. **Checkout alojado** — el cliente ingresa la tarjeta en el dominio de Stripe, de modo que el
   sistema **nunca ve ni almacena datos de tarjeta**. Esto realiza el RNF09 sin esfuerzo propio.
3. **Webhooks firmados**, que permiten confirmar el pago de forma verificable.
4. **Tarjetas de prueba documentadas** para simular aprobación, rechazo y fondos insuficientes.
5. **SDK oficial de Python**, que es el lenguaje del backend.

### Flujo de pago implementado (CU-27 y CU-28)

```
1. El cliente confirma el pedido
       ↓
2. El backend crea la Venta en estado "pendiente de pago"
   y solicita a Stripe una Checkout Session
       ↓
3. Stripe devuelve una URL; el cliente es redirigido allí
   e ingresa la tarjeta de prueba          ← los datos NUNCA pasan por FashionStore
       ↓
4. Stripe notifica el resultado al backend por WEBHOOK FIRMADO
       ↓
5. El backend VERIFICA LA FIRMA, marca la venta como pagada,
   registra el Pago y descuenta el inventario — todo en una
   transacción IDEMPOTENTE
       ↓
6. La redirección de vuelta al navegador solo muestra el resultado
```

La **Checkout Sessions API** es la vía recomendada por Stripe para este tipo de integración.

### Dos reglas que no se negocian

**1. El estado del pago lo determina el webhook, nunca el navegador.** La URL de retorno es solo
una dirección: cualquiera puede escribirla y "confirmar" un pago que nunca ocurrió. Solo el
webhook, con su firma verificada contra el secreto de firma, es prueba de que Stripe cobró. Ésta
es la decisión **D5** del análisis.

**2. El procesamiento del webhook debe ser idempotente.** Stripe reintenta la notificación si no
recibe respuesta exitosa. Sin idempotencia, un reintento descontaría el inventario dos veces por
la misma venta.

### Advertencia práctica sobre las claves

Stripe mantiene **claves y secretos de firma distintos para el modo de prueba y el modo real**.
Copiar un secreto de test en producción —o al revés— hace que la verificación de firma falle, y
el error no dice que el problema sea ése. Hay que confirmar en qué modo está el panel antes de
copiar cualquier clave.

---

## 6. Cuadro comparativo

| | **Libélula** | **PayPal** | **Stripe** |
|---|---|---|---|
| Origen / alcance | Bolivia | Global | Global |
| **¿Cobra en Bolivia?** | Sí, es su mercado | **No directamente** | Requiere entidad en un país soportado |
| Tarjetas | Nacionales e internacionales | Sí | Sí |
| **QR** | Sí (QR Simple) | No | No en Bolivia |
| Billeteras locales | Tigo Money, Botón BCP | — | — |
| Comisión de referencia | Según convenio | ~4,4 % + fija (internacional) | 2,9 % + $0,30 |
| Alta de cuenta | Convenio comercial | Registro en línea | Registro en línea |
| Entorno de pruebas | Sí | Sandbox | Test mode |
| Plugins para CMS | WooCommerce, Magento, PrestaShop, OpenCart | Muchos | Muchos |
| **Uso en este proyecto** | Documentada, no integrada | Respaldo (sandbox) | **Integrada (test mode)** |

**Conclusión.** Para una tienda boliviana real la elección sería **Libélula**, por el QR y por los
medios de pago locales. Para este proyecto académico la elección es **Stripe**, porque su modo de
pruebas se habilita sin trámite comercial y su documentación permite implementar el flujo completo
—incluida la verificación de firma del webhook— en el plazo disponible.

---

## Bibliografía de esta sección

- Libélula. *Suite de pagos y facturación en Bolivia*. <https://libelula.bo/>
- Libélula. *Pasarela Multicanal*. <https://libelula.bo/pasarela-multi-canal/>
- Libélula. *Guía de Integración para Empresas, v2.145* (abril 2023).
  <https://libelula.bo/Libelula%20Manual%20de%20Integraci%C3%B3n%20v2.145.pdf>
- Banco Central de Bolivia. *Pagos QR BCB Bolivia*.
  <https://www.bcb.gob.bo/?q=pagos_qr_bcb_bolivia>
- ASFI. *El uso del QR ha dinamizado el sistema de pagos en Bolivia* (julio 2025).
  <https://www.asfi.gob.bo/sites/default/files/2025-07/El%20uso%20del%20QR%20ha%20dinamizado%20el%20sistema%20de%20pagos%20en%20Bolivia.pdf>
- Mobile Time. *Banco Central de Bolivia lanza OpenBCB para pagos con QR* (octubre 2025).
  <https://mobiletime.la/noticias/20/10/2025/bolivia-lanza-openbcb/>
- Stripe. *Pricing & Fees*. <https://stripe.com/pricing>
- Stripe Docs. *Checkout Sessions*. <https://docs.stripe.com/payments/checkout>
- PayPal. *Comisiones de PayPal para vendedores (Bolivia)*.
  <https://www.paypal.com/bo/business/paypal-business-fees>
- PayPal Developer. *Sandbox testing guide*. <https://developer.paypal.com/tools/sandbox/>
- Kiero. *8 pasarelas de pago en Bolivia efectivas y eficientes*.
  <https://kiero.io/blog/tienda-online/8-pasarelas-de-pago-en-bolivia-efectivas-y-eficientes/>

*Consultado el 02/09/2026. Las comisiones cambian: verificar en la página oficial antes de la
defensa.*
