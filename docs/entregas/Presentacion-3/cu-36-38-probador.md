# CU-36, CU-37 y CU-38 · El probador con la talla real

3ra presentación del 2do parcial. Paquete P9 (`backend/app/modules/vestidor_virtual`), migración `0041_cu36_probador`.

## La idea

Los probadores generativos acomodan la prenda al cuerpo y no respetan la talla. Acá la escala la ponen los **centímetros**:

- Los puntos de la imagen (CU-36) dicen cuántos píxeles de la imagen mide la prenda entre hombros y hasta el ruedo.
- Las medidas del cliente y sus hombros en la foto (CU-37) dicen cuántos píxeles mide un centímetro de su cuerpo.
- La prenda se dibuja con los centímetros de la talla elegida. Si le queda grande, **se ve** grande.
- La foto con IA (CU-38) parte de esa composición, y se le pide al modelo que **no** la cambie de tamaño.

Escala que usa la pantalla (`frontend-web/src/app/features/tienda/probador/probador.ts`):

```
px_por_cm      = hombros_en_la_foto_px / (busto_cliente_cm × 0.42)
ancho_prenda   = busto_talla_cm × 0.42 × px_por_cm   (entre los puntos de hombro)
largo_prenda   = largo_talla_cm × px_por_cm          (de la línea de hombros al ruedo)
```

El 0,42 (hombros sobre busto) se cancela en la razón ancho de prenda / ancho de cuerpo. Esa razón es la misma que usa `medidas.tallaje.factor_de_ancho`.

## Actores y recorrido

| CU | Actor | Recorrido |
|---|---|---|
| CU-36 Preparar prenda para el probador | Administrador (permiso `catalogo.gestionar`) | Admin → Probador → elige el producto → marca hombro izq., hombro der. y ruedo sobre cada PNG sin fondo → carga busto, cintura, cadera y largo por talla → «Lista». |
| CU-37 Probarse una prenda con su talla real | Cliente | Ficha → «Probármela» → (si faltan, carga sus medidas) → sube o toma una foto → MediaPipe Pose detecta los hombros (si no puede, dos clics) → elige talla y color → ve la prenda a escala y el «cómo le queda» → «Guardar esta prueba». |
| CU-38 Generar foto realista de la prueba | Cliente (incluye CU-05: plan con `foto_ia` y cupo `cupo_fotos_ia`) | En la misma pantalla, «Generar foto realista» → se sube la composición → proveedor (Gemini o simulado) → la foto se guarda en la prueba y se descuenta el cupo de la tienda. |

## Clases (para el 3.4 y los diagramas de secuencia)

- **Boundary:**
  - CU-36: `PantallaPrepararPrenda` (`probador-admin.ts`).
  - CU-37 y CU-38: `PantallaProbador` (`probador.ts`).
- **Control:**
  - `probador_router` (admin y cliente) y `probador_service`.
  - Se reusan `medidas.service.ajuste_de_producto`, `verificador` (plan y cupo) e `integrations.probador_ia`.
- **Entidad:**
  - Nuevas: `PuntoPrenda` (`punto_prenda`) y `SesionVestidorVirtual` (`sesion_probador`).
  - Se reusan `MedidaTalla`, `MedidaCliente`, `ImagenProducto`, `VarianteProducto` y `ConsumoCupo`.
- **Bitácora:** el middleware de CU-42 registra todos los POST, PUT y DELETE de estas rutas.

## API

| Método | Ruta | CU |
|---|---|---|
| GET | `/catalogo/probador/productos` | 36 |
| GET | `/catalogo/probador/productos/{id}` | 36 |
| PUT | `/catalogo/probador/imagenes/{id}/puntos` | 36 |
| PUT | `/catalogo/probador/productos/{id}/medidas` | 36 |
| GET | `/vestidor/productos/{id}/prueba` | 37 |
| POST, GET | `/vestidor/sesiones` | 37 |
| DELETE | `/vestidor/sesiones/{id}` | 37 |
| POST | `/vestidor/sesiones/{id}/foto` | 38 |

## Reglas

- Puntos:
  - Dentro de la imagen.
  - El hombro izquierdo a la izquierda del derecho.
  - Separación de al menos 10 % del ancho.
  - Desnivel máximo de 15 % del alto.
  - El ruedo al menos 10 % por debajo de los hombros.
  - Solo en PNG sin fondo asociado a una variante.
- Medidas:
  - Los mismos rangos que `medida_talla`.
  - Solo tallas en las que se vende el producto.
  - El busto no puede bajar al subir de talla.
- El ajuste y la talla recomendada de una prueba los calcula el **servidor**.
- Foto:
  - Una por prueba (409 si ya tiene).
  - El cupo se descuenta **solo si la foto salió**.
  - Si Gemini falla, sale la vista simulada, marcada como tal.
  - Borrar la prueba borra la foto.
- Proveedor por defecto: `simulado` (Pillow, sin costo; respeta R9). `gemini` necesita facturación (ver `integrations/probador_ia/gemini.py`).

## Pendiente

- **Móvil:** la pantalla de prueba con `google_mlkit_pose_detection` no se hizo; el vestidor RA del 1er parcial sigue como estaba. La API ya sirve para el móvil: `prueba`, `sesiones` y `foto` no dependen de la web.
