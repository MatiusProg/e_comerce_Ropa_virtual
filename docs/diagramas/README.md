# Modelo UML en Enterprise Architect

Todos los diagramas del proyecto viven en un único modelo, **`FashionStore.eapx`**.
Se generan por automatización (COM) con los scripts de [`scripts/`](../../scripts/), y
después se acomodan y se exportan a mano desde EA.

| Script | Qué genera |
|---|---|
| `ea-cu-ciclo1.ps1` | 1.3.2 (un diagrama por caso de uso) y 1.5 (modelo estructurado) |
| `ea-analisis-2-1.ps1` | 2.1.1 paquetes · 2.1.2 trazas paquete–caso de uso · 2.1.3 vista por paquete |
| `ea-comunicacion-2-2.ps1` | 2.2 diagramas de comunicación, uno por caso de uso |
| `ea-clases-2-3.ps1` | 2.3 diagramas de clases, uno por caso de uso |

**Los scripts son aditivos.** Abren el modelo y solo agregan lo que falta; un diagrama que
ya existe no se toca. Es deliberado: a esta altura hay diagramas acomodados a mano y un
generador que rehiciera el archivo borraría ese trabajo. Se pueden correr las veces que
haga falta.

---

## Estructura del modelo

```
FashionStore
├── CAP. 1 - Captura de Requisitos
│   ├── Modelo de Casos de Uso      los 9 actores y los 37 casos de uso
│   └── Ciclo 1                     los diagramas 1.3.2 y 1.5
└── CAP. 2 - Flujo de Trabajo: Analisis
    ├── 2.1 Analisis de Arquitectura    los 11 paquetes y los diagramas 2.1.1 y 2.1.2
    │   └── 2.1.3 Vista de Paquetes     un diagrama por paquete
    ├── 2.2 Analizar Casos de Uso
    │   └── Clases de Analisis          clases «boundary» «control» «entity» + diagramas 2.2
    └── 2.3 Analisis de Clases          clases «frontera» «controlador» «entidad» + diagramas 2.3
```

**Un diagrama y los elementos que muestra deben vivir en el mismo paquete.** Si no, EA
rotula cada elemento con `(from OtroPaquete)` debajo del nombre y el dibujo se ensucia.

---

## Por qué las clases de 2.2 y las de 2.3 son elementos distintos

*Decisión del 04/09/2026.*

EA dibuja el **ícono redondo de robustez** solo para los estereotipos que se llaman
exactamente `boundary`, `control` y `entity`. Con cualquier otro nombre —`frontera`,
`controlador`, `entidad`— dibuja la clase como **tabla**, con sus atributos y operaciones.

No hay forma de desactivar el ícono por diagrama. Se probaron `StereoIcon`,
`UseStereoIcon`, `ShowIcon`, `UCRect`, `SPT`, `NoIcon`, `ShapeScript` e `IsIcon` en
`DiagramObject.Style`, y ninguna surte efecto.

Como **2.2 necesita el formato redondo y 2.3 el de tabla**, y un mismo elemento no puede
verse de las dos maneras, se decidió que sean **elementos separados con el mismo nombre**,
en paquetes distintos. El lector ve `Usuario` en los dos capítulos; el modelo tiene dos
elementos.

> **Cuidado si cambiás un estereotipo a mano.** EA guarda además la aplicación del perfil,
> y el elemento queda con `StereotypeEx = "entidad,entity"`: el viejo sigue activo por
> debajo y el ícono no desaparece. Hay que asignar también `StereotypeEx`.

---

## Cómo se arma un mensaje en un diagrama de comunicación

Costó averiguarlo y no está documentado con claridad:

1. **El enlace** entre dos objetos es un conector **`Association`**. Es lo que dibuja la
   línea, y va **uno solo por par** de objetos, aunque intercambien varios mensajes.
2. **Cada mensaje** es un conector **`Collaboration`**. Su nombre es **solo la operación**;
   nada de numerarlo a mano.
3. **El número lo pone EA**, y sale del campo `PDATA4` del conector, con el formato
   `<grupo>.<orden>`. Ese campo es el ***Start New Group*** de la interfaz: al cambiar de
   grupo, EA reinicia la numeración y dibuja el grupo nuevo en otro color.

`PDATA4` es de **solo lectura** por la API (`MiscData(3)`), así que se escribe con
`Repository.Execute` contra `t_connector`. Es la única forma de fijar los grupos por
automatización.

> Numerar a mano dentro del nombre del mensaje —`"1: enviarDatos()"`— se ve parecido pero
> es peor: EA no sabe que son grupos, no los colorea, y amontona todas las etiquetas en el
> punto medio del enlace. Con `PDATA4` las apila ordenadas.

Un conector **`Sequence`** —el de los diagramas de secuencia— se crea sin error y **no
dibuja nada** en un diagrama de comunicación.

**La numeración de los grupos** sigue las etiquetas de la tabla de detalle: el grupo 1 es
el flujo principal, y los siguientes son los flujos alternativos y las excepciones. Cada
diagrama lleva una nota al pie diciendo qué es cada grupo.

---

## Otras cosas que hay que saber

**EA dibuja toda relación que exista entre los elementos presentes en el lienzo.** Como las
clases de análisis se comparten entre casos de uso, sin filtrar, el diagrama de CU-06
mostraba también los mensajes de CU-02. Los scripts ocultan por diagrama lo que no
crearon para él; en el modelo no se borra nada.

**El orden Z viene sin definir** (secuencia 999999). En 2.1.3 el paquete, que es un
rectángulo relleno, tapaba los casos de uso que contiene: se veía una caja vacía con líneas
entrando a la nada. Número más bajo = más al frente.

**Los estereotipos de robustez se dibujan como un círculo inscrito en la caja**, así que la
caja tiene que ser **cuadrada** y la separación entre elementos, mayor que su alto. Con una
caja ancha y baja el círculo se desborda y tapa a los vecinos.

**Borrar un diagrama no borra sus conectores.** Regenerar sin deduplicar dejó 471 conectores
de mensaje duplicados en el modelo. Los generadores ahora reutilizan el conector si ya
existe entre el mismo par con el mismo nombre.

---

## Lo que queda para hacer a mano en EA

Ninguna de estas se puede resolver por automatización:

- **Separar las etiquetas de mensajes que comparten enlace.** Con dos, EA las apila bien;
  con tres o cuatro se superponen. Un arrastre por etiqueta y quedan fijas. Se probó fijar
  la posición con `DiagramLink.Geometry` y EA la recalcula; `LayoutDiagramEx` empeora el
  diagrama.
- **El orden de los atributos.** Se les fija la posición, pero EA los muestra alfabéticos
  si está activa la opción *ordenar características alfabéticamente*. Se desactiva en las
  preferencias de EA.
- **El rótulo `(from Ciclo 1)`** bajo los actores, cuando el diagrama y el elemento están en
  paquetes distintos. Es opción de visualización de EA.
- **Acomodar y exportar.** Los generadores dejan una distribución razonable, no definitiva.

---

## Marca de agua

La versión instalada es **EA 15 Trial**. Algunas exportaciones salen con la marca
*"EA 15.0 Unregistered Trial Version"* y otras no, sin patrón claro. **Revisar cada PNG
antes de pegarlo en el documento.**
