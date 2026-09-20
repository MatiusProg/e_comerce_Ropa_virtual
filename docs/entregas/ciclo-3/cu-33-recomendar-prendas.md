# CU-33 · Recomendar prendas al cliente

> Realiza el **RF25** —«al menos una funcionalidad basada en inteligencia
> artificial»— junto con CU-35.

---

## 1. El enfoque híbrido, y por qué no se le pide al modelo que elija

Tres pasos, en orden:

1. **Un filtro determinista en SQL** saca las candidatas: producto activo, con
   variante activa, con existencia real, de la temporada vigente, de la talla
   del cliente y de las categorías que eligió.
2. **El modelo las ordena** y escribe una línea que explica cada una.
3. **Si el modelo falla, se muestra el paso 1** ordenado por popularidad.

La decisión de fondo está en el paso 1. A un modelo al que se le pide
«recomendale algo a esta clienta» le sale inventar prendas que no existen y
ofrecer tallas agotadas — y en una tienda eso no es un resultado malo, es una
promesa que no se puede cumplir.

Filtrando primero, **lo peor que puede hacer el modelo es ordenar mal**.

## 2. Los filtros son preferencias, no exigencias

La talla y las categorías **acotan cuando hay dato, y no vacían el resultado
cuando no lo hay**. Una clienta nueva, sin talla cargada ni categorías
elegidas, recibe recomendaciones igual: las más vendidas de la temporada.

Si los cuatro filtros a la vez dejan la lista vacía —categorías preferidas
agotadas, o una talla que no existe en la temporada— **se aflojan y se vuelve
a consultar**. Devolver nada sería correcto según el filtro y pésimo como
producto: la tienda tiene prendas, solo que ninguna cumple las cuatro
condiciones juntas.

La temporada se aplica con `OR temporada IS NULL`, porque hay productos sin
temporada asignada y excluirlos dejaría fuera medio catálogo.

**Nada de esto puede dejar la pantalla vacía.** Es la regla que gobierna el
módulo entero: sin talla, sin categorías, sin historial, sin modelo o sin
cuota, el cliente ve prendas. Lo que se pierde es la personalización, nunca la
funcionalidad.

## 3. Por qué se guarda, y qué se guarda

El paso 2 tarda segundos, depende de un tercero y consume cuota. Sin guardar,
entrar y salir cinco veces de la pantalla de inicio son cinco llamadas — y el
riesgo **R9** del plan es quedarse sin crédito antes de la defensa. La
recomendación vale **12 horas**.

**Se guarda solo el `producto_id` y el motivo.** Nombre, precio, categoría y
foto se leen del catálogo en cada lectura: guardarlos haría que una prenda que
cambió de precio siguiera mostrándose con el de hace doce horas.

### Lo que se corrigió el 20/09: la guardada tiene que seguir al catálogo

Se releían los datos, pero solo se comprobaba que el producto siguiera
`activo`. Doce horas son muchas: en el medio se da de baja la última variante,
se vende la última unidad, se descataloga una prenda.

Ahora, al servir una recomendación guardada, se salta la prenda que **dejó de
ser ofrecible por cualquiera de las cuatro vías** —borrada, desactivada, sin
variante activa o agotada—. Para quien mira la pantalla las cuatro son la
misma cosa: no la puede comprar.

La existencia se vuelve a preguntar **en bloque y por la costura C1**
(`inventario.service.productos_con_stock`), no leyendo `existencia` desde
P10.

**Y si quedan menos de tres, se regenera** aunque falten horas para que venza.
Saltar una o dos caídas está bien —quedan cinco tarjetas y nadie nota nada—,
pero con cinco de seis la pantalla queda con una sola y se lee como que la
tienda se vació.

La regeneración la dispara quien pide, no la lectura: meter una llamada al
modelo dentro de `_armar` la pondría dentro de cada lectura.

### Cuándo se tira antes de tiempo

Cuando el cliente **compra** o **cambia sus preferencias**: lo que se le
recomendaba se calculó con un perfil que ya no es el suyo.

## 4. Lo que el modelo no recibe

Ni nombre, ni correo, ni documento, ni identificador del cliente. Solo el
perfil de compra: talla habitual, categorías preferidas, nombres de prendas
que compró o marcó como favoritas, y la temporada.

Es lo que permite justificar con «combina con la chaqueta que compraste» sin
mandarle a un tercero quién es quien compró.

## 5. Se dice con qué se generó

La respuesta trae `motor`: `gemini` cuando las ordenó el modelo,
`popularidad` cuando no. **Una sugerencia hecha por un modelo tiene que poder
decir que lo es** — presentarla sin distinguir sería atribuirle a la tienda un
criterio que no eligió.

En el modo degradado **no se escribe motivo**. Se probó con uno fijo —«de lo
más vendido de la temporada»— y quedaba peor que nada: repetido seis veces se
lee como un error de la aplicación.

## 6. Límites conocidos

- **La talla que se usa es la superior.** Una recomendación de pantalones se
  filtra por la talla de blusa, que no es la misma. Se arregla cuando CU-21
  ponga las dos medidas en el perfil.
- **La popularidad no distingue temporada.** Un producto muy vendido hace un
  año pesa lo mismo que uno de este mes.
- **12 horas es un número elegido, no medido.** Nadie midió cuánto tarda en
  sentirse vieja una recomendación; se eligió para que entrar dos veces en un
  día no gaste dos llamadas.
