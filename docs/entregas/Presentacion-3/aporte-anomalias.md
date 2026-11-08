# Aporte propio · Detectar anomalías en caja y devoluciones (ML)

Funcionalidad que **no pide el enunciado**. Usa la infraestructura de la analítica (CU-29/CU-30) para vigilar
la plata: marca los **turnos de caja** y las **devoluciones** que se apartan de lo habitual y explica por qué.

## Descripción estilo caso de uso

| Campo | Contenido |
|---|---|
| **Nombre** | Detectar anomalías en caja y devoluciones |
| **Actor** | Administrador |
| **Propósito** | Encontrar a tiempo descuadres de arqueo, devoluciones en serie o fuera de hora, sin revisar turno por turno |
| **Precondiciones** | Sesión de Administrador. El plan de la empresa incluye `analitica_ml` (Empresarial). Hay al menos 20 turnos de caja cerrados en el último año |
| **Disparador** | El administrador presiona «Buscar anomalías» en Analítica inteligente |
| **Postcondición** | Queda guardado un análisis (`modelo_analitica` de tipo `ANOMALIAS`) con lo marcado, su puntaje y su explicación |

**Flujo principal**
1. El administrador entra a Analítica inteligente (CU-30) y presiona «Buscar anomalías».
2. El sistema junta los turnos cerrados del último año con sus variables:
   - el arqueo (lo contado contra lo esperado);
   - las devoluciones del turno y su monto;
   - el descuento sobre lo vendido;
   - la parte cobrada en efectivo;
   - la cantidad de ventas;
   - la duración del turno.
3. El sistema entrena un **Isolation Forest** y marca alrededor del 5 % más aislado.
4. Si hay al menos 15 devoluciones, hace lo mismo con ellas. Las variables son:
   - el valor devuelto;
   - las horas desde la venta (o desde la entrega);
   - la tasa de devoluciones por venta de quien la atendió;
   - si la prenda ya venía de un cambio;
   - si es un cambio;
   - la hora del día.
5. Para cada fila marcada calcula qué variables se apartan más de la mediana y arma la explicación, por ejemplo «Diferencia de arqueo 8× la habitual (Bs 80,00 contra Bs 10,00)».
6. Guarda el análisis y lo muestra en dos pestañas, *Turnos de caja* y *Devoluciones*. Cada fila trae el puntaje (0–1), la fecha, el cajero, la sucursal, el detalle y el motivo.
7. El administrador revisa cada caso y lo marca como «revisada». Queda registrado quién y cuándo.

**Flujos alternos**
- **A1. Pocos turnos.** Con menos de 20 turnos cerrados, responde 409: «Hacen falta al menos 20 turnos de caja cerrados para buscar anomalías; hay N en el último año». No se guarda nada.
- **A2. Pocas devoluciones.** Analiza solo los turnos. La pestaña Devoluciones dice cuántas faltan.
- **A3. Plan sin `analitica_ml`.** Responde 403 `plan_limit` y la pantalla muestra el candado con «Ver mi plan».
- **A4. Otro rol.** Un CLIENTE, CAJERO o ENCARGADO recibe 403.
- **A5. Volver a buscar.** Se entrena de nuevo con los datos de hoy y las revisiones anteriores se conservan para los mismos turnos y devoluciones.

**Reglas de negocio**
- **RN-A1.** Una anomalía es una **alerta para revisar**, no una prueba de fraude. La pantalla lo dice.
- **RN-A2.** Solo se usan **datos reales** de la empresa, sin sintéticos: marcar un turno inventado no le sirve a nadie.
- **RN-A3.** La explicación se calcula **de los datos** (mediana y MAD). No interviene un modelo de lenguaje.
- **RN-A4.** El análisis es de la empresa: el RLS deja fuera los turnos y los modelos de las otras.
- **RN-A5.** Se conservan los últimos 5 análisis (igual que los demás modelos, `CONSERVAR`).

## Clases y tablas, para los diagramas de EA

**Tabla:** se reutiliza `modelo_analitica`, de la migración 0040. La migración **0043_anomalias** solo amplía el CHECK del tipo a `('DEMANDA', 'SEGMENTOS', 'ANOMALIAS')`. En `resultado` (JSONB) quedan `turnos` y `devoluciones`, cada uno con `{suficientes, muestras, mensaje, medianas, marcadas[]}`, y cada marcada lleva su `revision {por, en}`.

**Tablas que se leen y no se escriben:**
- `turno_caja`, `caja`, `sucursal` y `usuario`;
- `venta` (el turno, el descuento, el método de pago y el total);
- `devolucion`, `detalle_devolucion` y `detalle_venta` (para el valor devuelto).

| Estereotipo | Clase | Archivo |
|---|---|---|
| «boundary» | PanelAnomalias | `frontend-web/.../analitica/anomalias/anomalias-panel.ts` |
| «control» | AnaliticaRouter (`/analitica/anomalias`, `.../{grupo}/{id}/revisada`) | `backend/app/modules/analitica/router.py` |
| «control» | ServicioAnalitica (`entrenar_anomalias`, `consultar_anomalias`, `marcar_revisada`) | `backend/app/modules/analitica/service.py` |
| «control» | DetectorAnomalias (`detectar`, `explicar`) | `backend/app/modules/analitica/anomalias.py` |
| «entity» | ModeloAnalitica (tipo ANOMALIAS) | `backend/app/modules/analitica/models.py` |
| «entity» | TurnoCaja, Devolucion, Venta (lectura) | `backend/app/modules/ventas/models.py` |

**Secuencia (resumen):**

PanelAnomalias → `POST /analitica/anomalias` → ServicioAnalitica.entrenar_anomalias →
1. `repo.turnos_cerrados`;
2. DetectorAnomalias.detectar (IsolationForest.fit, predict y score_samples), y luego explicar para cada fila marcada;
3. `repo.devoluciones_recientes` y `repo.ventas_por_cajero`, y otra vez detectar;
4. `repo.guardar(ModeloAnalitica)` y commit.

Después se devuelve AnomaliasOut.

## Isolation Forest, para la defensa

El Isolation Forest es un algoritmo **no supervisado**: no necesita que nadie haya etiquetado antes qué turno es «sospechoso».

**Cómo funciona.** Construye muchos árboles, 200 en nuestro caso. Cada árbol parte los datos al azar: elige una variable al azar y un punto de corte al azar entre su mínimo y su máximo, y repite hasta dejar cada fila sola.
- **Fila rara:** queda aislada en muy pocos cortes. Un turno con Bs 500 de faltante cuando lo normal es ±5 se separa del resto en el primer corte que cae sobre el arqueo.
- **Fila normal:** necesita muchos cortes, porque se parece a todas las demás.

El largo promedio del camino hasta aislar una fila, normalizado, da el **puntaje de 0 a 1**: cerca de 1 es muy anómala y alrededor de 0,5 o menos es normal.

**Contaminación.** El parámetro `contamination = 0.05` dice qué proporción esperamos marcar.

**Por qué no hace falta escalar.** Cada corte se hace dentro del rango de una sola variable, así que los bolivianos no tapan a los conteos como pasaría con una distancia.

**La explicación.** El bosque no dice *por qué* una fila es rara, así que la explicación la calculamos aparte. Para cada variable medimos cuántas desviaciones robustas (MAD) se aleja de la mediana y nombramos las dos que más se apartan. Así el administrador ve «diferencia de arqueo 8× la habitual» y no un número suelto.
