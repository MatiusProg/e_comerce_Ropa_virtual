# CU-21 · Qué entra y qué NO entra, para los diagramas

> **Escrito el 20/09/2026, antes de dibujar.** No es un documento de diseño:
> es la lista de lo que CU-21 hace de verdad en el código entregado, para que
> los diagramas no muestren un flujo que no existe.
>
> La regla del ciclo es que **los diagramas se hacen al final, sobre el código
> escrito**. Este archivo es el insumo de esa regla para CU-21.

---

## 1. El aviso, en una línea

**CU-21 NO tiene ayuda por foto.** Ni para medir el cuerpo, ni para amoldar la
prenda. Las dos cosas se descartaron de momento, y ninguna debe aparecer en
los diagramas de este caso de uso.

---

## 2. Lo que CU-21 SÍ hace

`mobile/lib/features/vestidor/pantalla_vestidor.dart`:

1. Abre la **cámara frontal**.
2. Corre **detección de pose** (`google_mlkit_pose_detection`) sobre los
   fotogramas.
3. Superpone el **PNG transparente** de una variante real del catálogo,
   escalado, ubicado y rotado siguiendo **hombros y cadera**.
4. Permite **cambiar talla y color en vivo**, sin volver a consultar al
   servidor.
5. **Captura** lo que se ve y lo guarda en el teléfono.
6. **Deriva al carrito o a la reserva** desde la propia captura.
7. Muestra los **fotogramas por segundo** que está procesando.

Y en la pantalla de medidas, `pantalla_medidas.dart`:

8. El cliente **escribe** busto, cintura, cadera y altura **a mano**, en un
   formulario de cuatro campos. Con eso el vestidor rotula cómo le queda cada
   talla.

---

## 3. Lo que CU-21 NO hace, y por qué importa acá

### 3.1 No estima medidas a partir de una foto

No hay ningún paso donde el sistema saque el busto, la cintura o la cadera de
una imagen. **Las medidas son un formulario que el cliente completa.**

La detección de pose que sí existe se usa **para colocar la prenda**, no para
medir: da posiciones de hombros y cadera en píxeles de la pantalla, que no se
convierten a centímetros en ninguna parte.

> **Para el diagrama:** el actor que aporta las medidas es el **Cliente**,
> escribiéndolas. No hay un paso «el sistema calcula las medidas», ni un
> objeto de control que las estime, ni una llamada a un servicio externo para
> obtenerlas.

### 3.2 No amolda la prenda por IA en el flujo entregado

El vestidor tiene un botón opcional de **«amoldar por IA»** que manda la
captura a un proveedor y devuelve la imagen con la prenda ajustada. **Está
apagado.**

- La costura es `backend/app/integrations/probador_ia/`, con el mismo patrón
  que las otras: `base.py`, un proveedor y un `no_disponible.py`.
- `backend/app/core/config.py` trae `PROBADOR_IA_PROVEEDOR = "no_disponible"`
  **por omisión**, y no se configuró otro.
- El móvil consulta `GET /vestidor/probador` al abrir la pantalla y, si la
  respuesta es que no hay, **esconde el botón**. Nunca se ofrece.

Está descartado *de momento*, no borrado: la costura queda escrita para que
encender el proveedor sea una variable de entorno y no un caso de uso nuevo.

> **Para el diagrama:** el flujo obligatorio de CU-21 **termina en la captura
> y la derivación al carrito o la reserva**. «Amoldar por IA» no va como paso,
> ni como flujo alternativo, ni como actor externo. Tampoco va el proveedor de
> IA en el diagrama de componentes de este caso de uso.

---

## 4. Checklist antes de dar por bueno un diagrama de CU-21

- [ ] ¿Aparece algún paso que **obtenga medidas de una foto**? → sacarlo.
- [ ] ¿Aparece un actor o componente de **IA** conectado al vestidor? → sacarlo.
- [ ] ¿La detección de pose está dibujada **como parte del móvil**, y no como
      un servicio externo? Corre **en el teléfono**, no en el servidor.
- [ ] ¿El **Cliente** es quien carga las medidas, en su propio paso? → así va.
- [ ] ¿El flujo cierra en **captura → carrito o reserva**? → así va.

---

## 5. Dónde está cada cosa

| Qué | Dónde |
|---|---|
| La pantalla del vestidor | `mobile/lib/features/vestidor/pantalla_vestidor.dart` |
| El formulario de medidas | `mobile/lib/features/vestidor/pantalla_medidas.dart` |
| Cómo se dibuja la prenda | `mobile/lib/features/vestidor/pintor_prenda.dart` |
| Cómo se carga una prenda probable | [`cu-21-cargar-prendas-del-vestidor.md`](cu-21-cargar-prendas-del-vestidor.md) |
| La costura del probador por IA (apagada) | `backend/app/integrations/probador_ia/` |
