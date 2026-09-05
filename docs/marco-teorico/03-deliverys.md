# c) Deliverys

---

## 1. Qué es una plataforma de delivery

Una plataforma de delivery es un **intermediario logístico de tres lados** que coordina a actores
que antes no tenían forma de encontrarse:

| Actor | Qué aporta | Qué recibe |
|---|---|---|
| **Cliente** | Demanda y pago | El producto en su domicilio |
| **Comercio** | El producto | Ventas sin montar logística propia |
| **Repartidor** | El vehículo y el tiempo | Pago por entrega |
| **Plataforma** | La coordinación, la app y la confianza | Comisión y tarifas |

El valor de la plataforma no es transportar: es **resolver el problema de asignación** —qué
repartidor toma qué pedido, en qué orden y por qué ruta— y **garantizar la transacción** a las
tres partes.

## 2. Cómo funciona el ciclo de un pedido

```
1. Descubrimiento    El cliente ve los comercios disponibles en su zona de cobertura
        ↓
2. Pedido            Arma el carrito y paga (o elige pagar contra entrega)
        ↓
3. Confirmación      El comercio acepta e informa el tiempo de preparación
        ↓
4. Asignación        La plataforma asigna un repartidor cercano y disponible
        ↓
5. Recolección       El repartidor retira el pedido en el comercio
        ↓
6. Traslado          El cliente sigue el recorrido en el mapa, en tiempo real
        ↓
7. Entrega           Confirmación de entrega y calificación de las tres partes
```

**La asignación** es el problema técnico central. No basta con "el repartidor más cercano": los
algoritmos consideran la distancia al comercio, el tiempo restante de preparación, la dirección
hacia la que ya se dirige el repartidor y la posibilidad de **agrupar pedidos** cercanos en un
mismo viaje.

**El seguimiento en tiempo real** cumple una función que se subestima: reduce la ansiedad del
cliente y, con ella, las consultas al servicio de atención. Es una decisión de producto tanto
como técnica.

**Modelo de ingresos de la plataforma:**

1. **Comisión al comercio** — un porcentaje del valor del pedido. Es la fuente principal.
2. **Tarifa de envío al cliente** — total o parcialmente trasladada.
3. **Tarifa de servicio** — un cargo fijo adicional por pedido.
4. **Publicidad** — los comercios pagan por aparecer destacados.
5. **Suscripciones** — planes que eliminan el costo de envío a cambio de una cuota mensual.

Las comisiones a comercios en el sector se ubican habitualmente entre el **15 % y el 30 %** del
valor del pedido, con la mayoría de los acuerdos en el rango del **20 % al 25 %**. Es un
porcentaje alto que sale directo del margen del comercio, y la razón por la que muchos negocios
mantienen su propio canal en paralelo.

## 3. El caso boliviano

### 3.1 Yaigo

Plataforma **de origen boliviano**, nacida en Sucre. Su modelo inicial ilustra bien cómo arranca
un delivery local:

- **Cobertura por radio** — operaba en un radio de **siete kilómetros** desde la Plaza 25 de Mayo
  de Sucre. Definir la zona por un radio desde un punto céntrico es la forma más simple de acotar
  la operación cuando la flota es chica.
- **Tarifa por distancia** — **Bs 7** de 0 a 1,5 km, y **Bs 3 adicionales por cada kilómetro**
  siguiente.
- **Tiempo de entrega** — entre **20 y 35 minutos** de promedio en Oruro.
- **Pago** — inicialmente solo en efectivo, con el pago en línea con tarjeta incorporado después.

> ⚠️ **Estos datos corresponden a la etapa inicial de Yaigo (2019)** y son los que están
> documentados públicamente. Sirven para ilustrar la estructura de una tarifa —base + costo por
> kilómetro—, que es lo que pide el enunciado, pero **no deben presentarse como vigentes**. Si se
> quieren cifras actuales hay que consultarlas en la app.

### 3.2 Yummy

**Super app de origen venezolano** que se expandió a Bolivia. Opera como agregador: toma el
pedido, asigna repartidores propios y gestiona la logística y el cobro. Su estructura de ingresos
reportada combina una **tarifa de servicio de alrededor de USD 1 adicional al envío** con una
**comisión cercana al 18 %** al comercio. Además del delivery de comida ofrece otros verticales
—viajes, envíos, mercado— bajo la misma aplicación, que es lo que la define como *super app*.

### 3.3 El resto del mercado

El sector boliviano se volvió competitivo en los últimos años:

- **PedidosYa** (grupo Delivery Hero) es el actor dominante en buena parte del Cono Sur, incluida
  Bolivia, con la cobertura más amplia y mejor aceptación de tarjetas extranjeras.
- **Yango** lanzó su servicio de delivery de comida en Bolivia en **2024**, la primera vez que la
  multinacional ofreció este servicio en Latinoamérica a través de su super app.

## 4. Cómo se calcula el pago de una entrega

El enunciado pide explicar los factores: **distancia, peso, frecuencia y tamaño**. La tarifa
resulta de combinarlos sobre una estructura común:

```
Tarifa = Base + (Distancia × Costo/km) + Ajuste por peso/volumen
         + Ajuste por demanda + Recargos
```

### 4.1 Distancia

El componente principal. Se cobra una **tarifa base** que cubre el primer tramo, y a partir de
ahí un **costo por kilómetro**. El caso de Yaigo lo muestra con claridad: Bs 7 hasta 1,5 km, y
Bs 3 por cada kilómetro adicional.

Un detalle que importa: la distancia relevante es la **de ruta real**, no la línea recta. Dos
puntos separados por 2 km en el mapa pueden estar a 5 km de recorrido si hay un río, una avenida
sin retorno o una zona peatonal en el medio. Las plataformas serias calculan sobre la red vial.

### 4.2 Peso

Encarece por dos vías: el vehículo necesario —una mochila de moto tiene un límite— y el esfuerzo
de manipulación. Suele aplicarse por **escalones** (hasta 5 kg, de 5 a 10 kg, etc.) más que de
forma continua.

### 4.3 Tamaño y peso volumétrico

Un paquete voluminoso pero liviano ocupa el espacio que impediría llevar otros pedidos. Por eso el
sector usa el **peso volumétrico**:

```
Peso volumétrico = (largo × ancho × alto) / factor
```

Se cobra sobre el **mayor** entre el peso real y el volumétrico. Es la razón por la que enviar una
almohada cuesta como enviar algo mucho más pesado: **no se paga el peso, se paga el espacio**.

El tamaño también determina la **viabilidad**: si entra en una mochila va en moto; si no, exige
un vehículo mayor, con otra tarifa. Y condiciona el **agrupamiento**: solo los pedidos pequeños
pueden combinarse en un mismo viaje, lo que abarata el costo por entrega.

### 4.4 Frecuencia y demanda

Aquí entra la **tarifa dinámica**, el mismo principio del *surge pricing* de los viajes: cuando
hay más pedidos que repartidores disponibles, el precio sube. Cumple dos funciones a la vez:
modera la demanda y atrae repartidores a conectarse. Los factores típicos son la hora pico, el
clima adverso, eventos masivos y días festivos.

La **frecuencia** actúa en el sentido contrario: un comercio con volumen alto y sostenido negocia
comisiones más bajas, y un cliente frecuente accede a suscripciones que eliminan el costo de
envío.

### 4.5 Otros componentes

- **Tiempo de espera** en el comercio, cuando la preparación se demora más de lo previsto.
- **Zona** — algunas áreas tienen recargo por distancia, acceso difícil o seguridad.
- **Propina** al repartidor, opcional y directa.

### 4.6 Ejemplo de cálculo

Pedido de 3 kg, en caja de 40 × 30 × 30 cm, a 4,2 km, en hora pico:

```
Peso volumétrico = (40 × 30 × 30) / 5000 = 7,2 kg
Peso facturable  = máx(3 ; 7,2) = 7,2 kg        ← manda el volumen, no el peso

Base (0 – 1,5 km)               Bs  7,00
Distancia (2,7 km × Bs 3)       Bs  8,10
Escalón de peso (5 – 10 kg)     Bs  5,00
Factor de demanda (×1,3)        Bs  6,03
                                ─────────
Total                           Bs 26,13
```

*(Estructura ilustrativa, construida sobre el esquema tarifario documentado de Yaigo. Los
escalones de peso y el factor de demanda son supuestos para mostrar el mecanismo.)*

---

## 5. Relación con Violet Boutique

El delivery **está fuera del alcance** de este proyecto, y conviene decirlo con precisión para no
generar una expectativa que el sistema no cumple.

**Lo que Violet Boutique sí hace.** En la compra digital, el cliente elige entre **retiro en
sucursal** y **envío a domicilio**; en el segundo caso registra su dirección y el pedido guarda un
costo de envío. Esa información queda en el pedido y aparece en los reportes.

**Lo que no hace.** No asigna repartidores, no calcula rutas ni distancias, no aplica tarifa
dinámica y no ofrece seguimiento en tiempo real. Está declarado en el alcance negativo
([`docs/01-perfil.md`](../01-perfil.md) §1.4.2).

**Por qué se excluyó.** Un módulo de logística exige geolocalización, cálculo de rutas, una
aplicación para el repartidor y asignación en tiempo real. Es un sistema completo en sí mismo, y
no es lo que el enunciado pide demostrar: los diferenciadores exigidos son el vestidor virtual con
realidad aumentada y la inteligencia artificial.

**Cómo se integraría, si el proyecto continuara.** La vía realista no sería construir la logística,
sino **integrarse con una plataforma existente** —PedidosYa, Yango o un operador local— mediante
su API: Violet Boutique emitiría la orden de entrega y recibiría por webhook los cambios de estado.
Sería el mismo patrón de adaptador que ya se usa con la pasarela de pago (paquete P8): un servicio
externo aislado tras un adaptador propio, de modo que cambiar de operador no afecte al resto del
sistema.

---

## Bibliografía de esta sección

- Correo del Sur. *Yaigo Delivery transaccionó 30 mil dólares en dos meses* (agosto 2019).
  <https://correodelsur.com/capitales/20190813/yaigo-delivery-transacciono-30-mil-dolares-en-dos-meses.html>
- Yummy. *La SuperApp de Venezuela*. <https://www.yummysuperapp.com/>
- TechCrunch. *Yummy bags $18M as it expands delivery app across Latin America* (octubre 2021).
  <https://techcrunch.com/2021/10/21/yummy-bags-18m-as-its-expands-delivery-app-across-latin-america>
- Yango. *Yango Food Delivery in Bolivia: Winning Restaurant Partners*.
  <https://yango.com/career/blog/yango-food-delivery-in-bolivia-winning-restaurant-partners>
- Nomada. *Bolivia food delivery 2026: PedidosYa vs Uber Eats*.
  <https://nomada.tools/directory/food-delivery/bolivia>
- Growth Delivery App. *Rappi, PedidosYa & Uber Eats Fees 2026: Real Comparison*.
  <https://blog.growthdeliveryapp.com/blog/comisiones-rappi-pedidosya-uber-eats>
- Economy. *Se mueve el tablero del delivery y el sector se hace más competitivo* (noviembre 2024).
  <https://www.economy.com.bo/articulo/business/mueve-tablero-delivery-sector-hace-mas-competitivo/20241107092450015834.html>

*Consultado el 02/09/2026. Las tarifas de Yaigo citadas son de 2019 y se presentan como
ilustración de la estructura tarifaria, no como valores vigentes.*
