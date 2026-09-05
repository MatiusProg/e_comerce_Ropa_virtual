# Modelo UML en Enterprise Architect

Todos los diagramas del proyecto viven en un único modelo, **`VioletBoutique.eapx`**.
Se generan por automatización (COM) con los scripts de [`scripts/`](../../scripts/), y
después se acomodan y se exportan a mano desde EA.

> **El manual completo está en [`GUIA-DIAGRAMAS-EA.md`](../../GUIA-DIAGRAMAS-EA.md)**, en la
> raíz del repositorio (con una copia fuera, en la carpeta `Si2/`). Ahí está todo: el recetario
> de la API COM, la segunda pasada por OLEDB, una receta por diagrama, el catálogo de errores y
> el orden en que hay que correr los generadores. Este README es el resumen.

| Script | Qué genera |
|---|---|
| `ea-cu-ciclo1.ps1` | 1.3.2 (un diagrama por caso de uso) y 1.5 (modelo estructurado) |
| `ea-analisis-2-1.ps1` | 2.1.1 paquetes · 2.1.2 trazas paquete–caso de uso · 2.1.3 vista por paquete |
| `ea-comunicacion-2-2.ps1` | 2.2 diagramas de comunicación, uno por caso de uso |
| `ea-clases-2-3.ps1` | 2.3 diagramas de clases, uno por caso de uso |
| `ea-paquetes-2-4.ps1` | 2.4 análisis de paquetes, un diagrama por ciclo |
| `ea-datos-3-3-1.ps1` | 3.3.1 modelo de dominio (diseño de datos lógico), un diagrama por ciclo |
| `ea-capas-3-1-1.ps1` | 3.1.1 diagrama de capas |
| `ea-despliegue-3-1-2.ps1` | 3.1.2 diagrama de despliegue |
| `ea-secuencia-3-2.ps1` | 3.2 diagramas de secuencia, uno por caso de uso |
| `ea-componentes-4-2.ps1` | 4.2 diagrama de componentes del sistema |
| `ea-componentes-4-3.ps1` | 4.3 diagramas de componentes por subsistema |

**Los scripts son aditivos.** Abren el modelo y solo agregan lo que falta; un diagrama que
ya existe no se toca. Es deliberado: a esta altura hay diagramas acomodados a mano y un
generador que rehiciera el archivo borraría ese trabajo. Se pueden correr las veces que
haga falta.

---

## Estructura del modelo

```
Violet Boutique
├── CAP. 1 - Captura de Requisitos
│   ├── Modelo de Casos de Uso      los 9 actores y los 37 casos de uso
│   └── Ciclo 1                     los diagramas 1.3.2 y 1.5
├── CAP. 2 - Flujo de Trabajo: Analisis
│   ├── 2.1 Analisis de Arquitectura    los 11 paquetes y los diagramas 2.1.1 y 2.1.2
│   │   └── 2.1.3 Vista de Paquetes     un diagrama por paquete
│   ├── 2.2 Analizar Casos de Uso
│   │   └── Clases de Analisis          clases «boundary» «control» «entity» + diagramas 2.2
│   ├── 2.3 Analisis de Clases          clases «frontera» «controlador» «entidad» + diagramas 2.3
│   └── 2.4 Analisis de Paquetes        los paquetes y las clases del ciclo + diagrama 2.4
└── CAP. 3 - Flujo de Trabajo: Diseno
    └── 3.3.1 Diseno de Datos Logico    las 16 entidades del ciclo + diagrama 3.3.1
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

## La unión entre clases es siempre una asociación

*Decisión del 04/09/2026.*

En los diagramas de clases, dos clases se unen **siempre con un conector `Association`**, con
nombre de rol en mayúsculas y cardinalidad en los dos extremos. No se usan `Dependency`,
`Usage`, `Aggregation` ni `Composition` entre clases.

El motivo es de lectura: con un solo tipo de línea el lector compara los diagramas del capítulo
entre sí sin interpretar la semántica de cada estilo, y no queda abierta la discusión de si algo
era agregación o composición. La función `New-Asociacion` de `ea-clases-2-3.ps1` ya lo hace y
deduplica por par más nombre.

**Los diagramas ya generados no se rehacen** —CU-01 y CU-02 del 2.3 quedan como están—; la regla
vale para los que faltan.

Alcanza solo a las relaciones **clase↔clase**. El acoplamiento entre paquetes de 2.4 se dibuja
con `Usage` («use»), y las trazas paquete–caso de uso de 2.1.2 con `Abstraction` «trace».

---

## El modelo de dominio de 3.3.1

Sigue las convenciones del modelo de referencia `MODELO DE DOMINIO.qea`: una clase por tabla
con el **nombre de la entidad en mayúsculas**, sin operaciones, atributos privados con la clave
primaria primero, y relaciones como `Association` con un **verbo en mayúsculas** por nombre y
cardinalidad en los dos extremos.

Se aparta de la referencia en dos cosas, porque el proyecto ya las tiene y la referencia no:

- **el tipo de cada columna**, para que 3.3.1 y el esquema físico de 3.3.2 digan lo mismo;
- **el estereotipo `«PK»` / `«FK»`** en cada columna que lo sea, sin el cual hay que adivinar
  qué columna cierra cada relación.

Los nombres de columna van en **minúsculas**, como en el código y como en 3.3.2; solo el nombre
de la entidad va en mayúsculas.

El contenido no se transcribe a mano: sale de los `models.py` de SQLAlchemy compilados con el
dialecto PostgreSQL, y se verifica columna por columna contra ellos después de generar.

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

## Cómo se arma un diagrama de secuencia

Es distinto al de comunicación y tiene sus propias trampas: **EA remaqueta el diagrama
entero cada vez que lo abre**, y ni el tipo de mensaje ni los operandos de un fragmento
combinado se pueden escribir por la API COM.

Todo eso, más la correspondencia entre cada mensaje y la línea de código de la que sale, y
de dónde sale cada fragmento de interacción (`alt`, `loop`, `critical`, `opt`, `break`),
está en **[`secuencia-y-codigo.md`](secuencia-y-codigo.md)**.

Los genera `scripts/ea-secuencia-3-2.ps1`.

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
