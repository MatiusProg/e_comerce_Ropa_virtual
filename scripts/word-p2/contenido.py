# Contenido del documento del 2do parcial, en el orden del índice de la ing (págs. 11-12 del enunciado).
# Cada entrada: (acción, ...). Ver ACCIONES en gen_doc.py.

from casos_uso import BLOQUE_25, BLOQUE_26

RF3 = [1100, 7182, 1500]

CONTENIDO = [
    # =====================================================================
    ('salto',),
    ('cap', 'CAPÍTULO I. ASPECTOS GENERALES'),

    ('h1', '1.1. Introducción'),
    ('p', 'En el primer examen parcial el grupo construyó Violet Boutique (la FashionStore del enunciado), '
          'una plataforma inteligente de comercio electrónico para una cadena de tiendas de ropa con varias '
          'sucursales. El prototipo cubre 42 casos de uso: catálogo, tallas, colores y temporadas, proveedores, '
          'inventario multisucursal, reservas, ventas presenciales y en línea, pagos, vestidor con realidad '
          'aumentada, recomendaciones y reportes con inteligencia artificial, y aplicaciones web y móvil. '
          'Está desplegado en la nube y lo respaldan más de 800 pruebas automatizadas.'),
    ('p', 'Para el segundo parcial la empresa cambia de modelo de negocio. Ya no quiere usar la plataforma solo '
          'para sus propias tiendas, sino **venderla como servicio (SaaS)** a otras empresas de ropa, que la '
          'contratan mediante planes de suscripción. Cada empresa trabaja en su propio entorno lógico y nunca '
          've los datos de otra.'),
    ('p', 'El cambio trae tres capacidades nuevas. Las tiendas deben seguir vendiendo y reservando **sin '
          'conexión a Internet**, desde la web instalada como PWA y desde la aplicación Flutter, y sincronizar '
          'después sin duplicar ni perder operaciones. Los usuarios autorizados deben poder pedir **reportes en '
          'lenguaje natural**, escrito o por voz, construidos con los datos reales de su empresa. Y se suma un '
          'módulo de **analítica con aprendizaje automático**.'),
    ('p', 'El trabajo no parte de cero: evoluciona el prototipo existente. Por eso se aplica **ICONIX**, un '
          'proceso dirigido por casos de uso que mantiene la trazabilidad entre requisitos, análisis, diseño, '
          'código y pruebas, concentrado en los requisitos nuevos y en los componentes que cambian.'),

    ('h1', '1.2. Planteamiento del problema'),
    ('p', 'La plataforma del primer parcial resuelve bien la operación de una sola cadena, pero no sirve para '
          'el negocio que la empresa quiere ahora. Los problemas concretos son cinco.'),
    ('p', '**Una sola empresa por instalación.** Todos los datos pertenecen a un único negocio: no existe el '
          'concepto de empresa contratante, ni planes, ni suscripciones. Ofrecer el sistema a una segunda '
          'empresa obligaría a desplegar otra copia completa, con su propia base y su propio mantenimiento.'),
    ('p', '**Sin aislamiento entre clientes del servicio.** Si varias empresas compartieran la base actual, '
          'nada en el backend impediría que el usuario de una consulte o modifique los datos de otra. Ocultar '
          'opciones en la interfaz no basta: la restricción tiene que estar en el servidor y en la base.'),
    ('p', '**Dependencia total de Internet.** Cuando una tienda pierde la conexión, la caja deja de vender y '
          'de reservar. La web y el móvil consultan siempre al servidor y no guardan nada localmente, así que '
          'una caída de red significa ventas perdidas.'),
    ('p', '**Reportes rígidos.** Los reportes de gestión existentes tienen filtros fijos. Un administrador '
          'que necesita una pregunta distinta, por ejemplo comparar sucursales en los últimos tres meses, '
          'depende de que alguien programe un reporte nuevo.'),
    ('p', '**Procesos que todavía son manuales.** Los cambios de prenda solo se hacen en caja; el cliente que '
          'compró en línea no puede pedirlos. Las sucursales no tienen forma de pedirse mercadería entre sí. '
          'Y el vestidor virtual acomoda la prenda al cuerpo sin importar la talla, de modo que no ayuda a '
          'elegir la talla correcta.'),

    ('h1', '1.3. Objetivos del proyecto'),
    ('h2', '1.3.1. Objetivo general'),
    ('p', 'Evolucionar Violet Boutique hacia una plataforma de comercio electrónico **SaaS multitenant**, con '
          'planes de suscripción, aplicación web progresiva, operación offline en web y móvil, sincronización '
          'de datos y reportes generativos con inteligencia artificial, aplicando la metodología ICONIX y '
          'manteniendo la coherencia entre los modelos UML 2.5+ y la implementación.'),
    ('h2', '1.3.2. Objetivos específicos'),
    ('ol', [
        'Recolectar los requerimientos del nuevo sistema a partir del enunciado, de lo pedido por la docente '
        'en clase y del funcionamiento actual de Violet Boutique.',
        'Especificar los requisitos funcionales y no funcionales y asociar cada uno a un caso de uso, como '
        'pide ICONIX.',
        'Elaborar el modelo de dominio y los diagramas de robustez de los casos de uso nuevos y de los que se '
        'modifican.',
        'Diseñar los diagramas de secuencia y refinar el diagrama de clases hasta el nivel de implementación.',
        'Diseñar el modelo de datos multitenant, con la empresa en cada tabla del tenant y Row Level Security '
        'en PostgreSQL, para garantizar el aislamiento entre empresas.',
        'Diseñar un contrato de sincronización común para la PWA y Flutter, con un identificador único y un '
        'estado por operación.',
        'Implementar el registro de empresas, los planes de suscripción y el control de límites y funciones '
        'en el backend.',
        'Evolucionar la aplicación Angular hacia una Progressive Web App (PWA) con persistencia en IndexedDB '
        'y operación offline.',
        'Incorporar SQLite en la aplicación Flutter para registrar reservas y ventas sin conexión.',
        'Implementar la sincronización de las operaciones pendientes, con reintentos, sin duplicados y con la '
        'detección y resolución de los conflictos de inventario.',
        'Incorporar reportes generativos con inteligencia artificial, pedidos por texto o por voz y resueltos '
        'con consultas controladas por el backend.',
        'Desarrollar un módulo de analítica con un modelo supervisado y uno no supervisado, con su dashboard.',
        'Implementar las devoluciones vía web pedidas en clase y los aportes propios del grupo: traspasos '
        'entre sucursales y un probador virtual que distinga tallas.',
        'Verificar el sistema con pruebas funcionales, de integración y de reglas críticas de negocio, '
        'incluido el aislamiento entre empresas.',
        'Desplegar la nueva versión en la nube con empresas de prueba independientes, una por cada plan.',
        'Actualizar la documentación técnica y los modelos UML 2.5+ para que reflejen el software construido.',
    ]),

    ('h1', '1.4. Justificación'),
    ('p', '**Justificación económica.** Vender la plataforma como servicio convierte un desarrollo hecho para '
          'una sola cadena en un producto con ingresos recurrentes. Una única instalación atiende a muchas '
          'empresas, y los planes permiten cobrar más a quien usa más sucursales o funciones avanzadas.'),
    ('p', '**Justificación operativa.** En Bolivia la conexión a Internet de un local comercial no es '
          'confiable. Poder vender y reservar sin conexión evita perder ventas durante un corte, y la '
          'sincronización posterior mantiene el inventario central correcto.'),
    ('p', '**Justificación técnica.** El multitenant con una base compartida y aislamiento lógico es el '
          'modelo más barato de operar a esta escala. PostgreSQL ofrece seguridad a nivel de fila (Row Level '
          'Security) para que el aislamiento lo garantice la propia base y no solo el código.'),
    ('p', '**Justificación para la toma de decisiones.** Los reportes en lenguaje natural ponen la '
          'información en manos de quien decide, sin pasar por un programador. La analítica con aprendizaje '
          'automático agrega predicciones y patrones que un reporte convencional no muestra.'),
    ('p', '**Justificación académica.** El proyecto obliga a aplicar ICONIX sobre un sistema real que ya '
          'funciona, con la exigencia de que cada requisito llegue, por trazabilidad, hasta el código y la '
          'prueba que lo verifica.'),

    ('h1', '1.5. Alcance y limitaciones'),
    ('h2', '1.5.1. Alcance'),
    ('p', 'Se conserva todo lo construido en el primer parcial, incluidos la realidad aumentada y el comercio '
          'electrónico. Sobre esa base se agregan los siguientes módulos.'),
    ('p', '**Módulo 1 — Plataforma SaaS.** Registro de empresas contratantes, administrador por empresa, '
          'asociación de usuarios y sucursales, y un administrador de la plataforma por encima de todas.'),
    ('p', '**Módulo 2 — Planes y suscripciones.** Planes Básico, Profesional y Empresarial con límites y funciones '
          'configurables desde el backend; asignación, cambio, renovación y suspensión de la suscripción, con '
          'el cobro simulado.'),
    ('p', '**Módulo 3 — Aislamiento multitenant.** Cada tabla del tenant lleva la empresa, y la base aplica '
          'Row Level Security. Al menos dos empresas de prueba independientes demuestran que no hay acceso '
          'cruzado.'),
    ('p', '**Módulo 4 — PWA offline.** La aplicación Angular se instala, guarda en IndexedDB el catálogo y '
          'las operaciones, y registra reservas y ventas de contado sin conexión.'),
    ('p', '**Módulo 5 — Móvil offline.** La aplicación Flutter guarda en SQLite un subconjunto del catálogo, '
          'la sucursal autorizada, los clientes mínimos y las operaciones pendientes.'),
    ('p', '**Módulo 6 — Sincronización.** Un contrato común para la PWA y Flutter: cada operación lleva un '
          'identificador único y un estado (local, enviada, confirmada, rechazada o en conflicto), con '
          'reintentos y sin duplicados.'),
    ('p', '**Módulo 7 — Ventas offline y cambios de prenda.** El servidor confirma o rechaza cada venta '
          'offline contra el inventario central, y se gestionan los cambios de prenda dentro de un plazo.'),
    ('p', '**Módulo 8 — Reportes generativos.** Pedidos en lenguaje natural, escritos o por voz, '
          'interpretados por un modelo de IA y resueltos con consultas controladas por el backend; resultado '
          'en tabla o gráfico, exportable a Excel y PDF. Se demuestran al menos cuatro tipos de reporte.'),
    ('p', '**Módulo 9 — Analítica con aprendizaje automático.** Datos sintéticos, un modelo supervisado, uno '
          'no supervisado, sus métricas y un dashboard analítico.'),
    ('p', '**Módulo 10 — Devoluciones vía web.** Pedido de la docente en clase: el cliente solicita el cambio '
          'o la devolución desde la tienda en línea, dentro de una ventana configurable por empresa, y el '
          'inventario registra notas de devolución que se ven en los reportes.'),
    ('p', '**Módulo 11 — Aportes propios.** Traspasos entre sucursales por pedido, sugeridos por las prendas '
          'más vendidas; un probador virtual que dibuja la prenda con sus medidas reales y sugiere la talla; '
          'la contratación de un plan desde la web; la marca de cada empresa en su tienda; la cuenta única '
          'del cliente; y la exportación de los datos de la empresa.'),
    ('h2', '1.5.2. Limitaciones'),
    ('ul', [
        'El cobro de las suscripciones se simula: no hay cobro recurrente real ni integración con '
        'plataformas de facturación SaaS.',
        'Las ventas offline son solo de contado; el pago electrónico requiere conexión.',
        'Los límites de los planes son valores de prototipo académico, configurables desde el backend.',
        'La inteligencia artificial usa un modelo gratuito consumido por API (Gemini); no se entrena ni '
        'aloja un modelo propio, porque el servidor en la nube no tiene GPU.',
        'Los modelos de aprendizaje automático se entrenan con datos sintéticos, no con historia real de '
        'varias empresas.',
        'La foto realista del probador con IA y los reportes con IA tienen un cupo mensual por plan, para '
        'acotar el costo.',
        'La aplicación móvil se prueba en Android; no se publica en las tiendas de aplicaciones.',
    ]),

    ('h1', '1.6. Metodología de desarrollo ICONIX'),
    ('p', 'ICONIX es un proceso de desarrollo dirigido por casos de uso, iterativo e incremental, que se ubica '
          'entre el Proceso Unificado y las metodologías ágiles. Parte de una idea simple: con una fracción '
          'pequeña de UML se resuelve la mayor parte de los casos, siempre que cada requisito quede asociado a '
          'un caso de uso y se pueda seguir hasta el código. Esa **trazabilidad** es su medida de calidad: un '
          'sistema es bueno en la proporción de requisitos que satisface.'),
    ('p', 'El proceso tiene cuatro fases:'),
    ('ol', [
        '**Análisis de requisitos.** Modelo de dominio (un diagrama de clases muy simplificado), prototipo '
        'de interfaz y casos de uso, con cada requisito asociado a un caso de uso.',
        '**Análisis y diseño preliminar.** Ficha de cada caso de uso (descripción, precondición, '
        'postcondición, flujo normal y alternativo) y diagrama de robustez con objetos frontera, entidad y '
        'control. La robustez refina el diagrama de clases.',
        '**Diseño.** Diagramas de secuencia derivados de las fichas, y un nuevo refinamiento del diagrama de '
        'clases.',
        '**Implementación.** Código, diagrama de componentes cuando hace falta, y pruebas planeadas a partir '
        'de los requisitos iniciales.',
    ]),
    ('p', '**Cómo se aplica en este proyecto.** El trabajo se organiza en tres ciclos, uno por presentación. '
          'Cada ciclo recorre las cuatro fases solo para sus casos de uso: los nuevos y los existentes que '
          'cambian. Según la docente, el diagrama de comunicación equivale al de robustez, así que los '
          'diagramas de análisis del primer parcial sirven de base. Los diagramas se terminan sobre el código '
          'ya escrito, para que representen lo realmente implementado. Se modelan en Enterprise Architect.'),
    ('tabla', ['Ciclo', 'Fechas', 'Contenido', 'Cierra en'], [
        ['Ciclo 1', 'mar 20/10 a dom 25/10', 'Empresas, planes y suscripciones; aislamiento con RLS; '
         'contratación desde la web y marca de la tienda; capítulos I y II del documento (CU-43 a CU-54)',
         'Presentación 1, dom 25/10'],
        ['Ciclo 2', 'lun 26/10 a dom 01/11', 'Contrato de sincronización; PWA con IndexedDB; Flutter con '
         'SQLite; ventas offline, cambios de prenda, devoluciones web y avisos por correo (CU-55 a CU-66)',
         'Presentación 2, dom 01/11'],
        ['Ciclo 3', 'lun 02/11 a dom 08/11', 'Reportes con IA y voz; analítica con ML; traspasos y probador '
         'por talla; exportación de datos (CU-67 a CU-77)', 'Presentación 3, dom 08/11'],
        ['Defensa', 'mar 10/11', 'Sistema completo desplegado y documentación final', 'Defensa, 7:00'],
    ], [1300, 1900, 4482, 2100]),

    # =====================================================================
    ('salto',),
    ('cap', 'CAPÍTULO II. ANÁLISIS DE REQUISITOS'),

    ('h1', '2.1. Descripción del sistema propuesto'),
    ('p', 'Violet Boutique pasa de servir a una sola cadena a venderse como **SaaS multitenant**. Una sola '
          'instalación (backend FastAPI, base PostgreSQL compartida, web Angular y aplicación Flutter) atiende '
          'a muchas empresas de ropa. Cada empresa es un tenant con sus propias sucursales, empleados, '
          'clientes, productos, inventario, reservas y ventas. Una sucursal no es un tenant: pertenece a una '
          'empresa, y una empresa puede tener varias.'),
    ('p', 'La tabla resume qué agrega cada desafío del enunciado.'),
    ('tabla', ['Desafío', 'Qué agrega al sistema'], [
        ['I. ICONIX', 'Modelo de dominio, robustez, secuencia y clases para los requisitos nuevos y lo que se '
         'modifica'],
        ['II. PWA', 'Angular instalable, con Service Worker, IndexedDB y operación offline'],
        ['III. Flutter + SQLite', 'El móvil guarda catálogo y operaciones en local y sincroniza después'],
        ['IV. Ventas offline', 'Venta de contado sin conexión, confirmada por el servidor sin romper el '
         'inventario; cambios de prenda en un plazo'],
        ['V. Reportes con IA y ML', 'Reportes en lenguaje natural (texto o voz) sobre datos reales, y un '
         'módulo de analítica con modelos supervisado y no supervisado'],
        ['VI. SaaS multitenant', 'Empresas, planes, suscripciones y aislamiento de datos entre tenants en el '
         'backend'],
    ], [2400, 7382]),

    ('h2', '2.1.1. Planes de suscripción'),
    ('p', 'El enunciado define dos planes, **Básico** y **Profesional**, y el grupo agrega un tercero, '
          '**Empresarial**. El Básico trae todo lo que el enunciado le asigna. El Profesional suma los '
          'reportes con IA y las funciones de IA que ya existían desde el primer parcial. El Empresarial quita '
          'los límites y suma la analítica con ML. Las filas marcadas como propias, los límites que no figuran '
          'en el enunciado y los precios simulados son una propuesta del grupo.'),
    ('tabla', ['Característica', 'Básico', 'Profesional', 'Empresarial'], [
        ['Precio mensual simulado (propio)', 'Bs 300', 'Bs 750', 'Bs 1.500'],
        ['Sucursales activas', 'Hasta 2', 'Hasta 10', 'Ilimitadas'],
        ['Empleados activos (propio)', 'Hasta 10', 'Hasta 60', 'Ilimitados'],
        ['Gestión de productos, ventas y reservas', 'Sí', 'Sí', 'Sí'],
        ['Operación offline (PWA y móvil)', 'Sí', 'Sí', 'Sí'],
        ['Reportes convencionales', 'Sí', 'Sí', 'Sí'],
        ['Cambios de prenda en caja y devoluciones vía web', 'Sí', 'Sí', 'Sí'],
        ['Traspasos entre sucursales a pedido', 'Sí', 'Sí', 'Sí'],
        ['Probador con realidad aumentada del 1er parcial', 'Sí', 'Sí', 'Sí'],
        ['Avisos dentro del sistema', 'Sí', 'Sí', 'Sí'],
        ['Reportes generativos con IA (texto y voz, exportar a Excel y PDF)', 'No', 'Sí, 300 por mes',
         'Sí, sin límite'],
        ['Avisos por correo a clientes y empleados (propio)', 'No', 'Sí', 'Sí'],
        ['Recomendaciones y asistente virtual con IA (propio)', 'No', 'Sí', 'Sí'],
        ['Tienda en línea con el logo y los colores de la empresa (propio)', 'No', 'Sí', 'Sí'],
        ['Traspasos sugeridos por lo más vendido (propio)', 'No', 'Sí', 'Sí'],
        ['Consulta del consumo de cupos y límites (propio)', 'Sí', 'Sí', 'Sí'],
        ['Probador que distingue tallas y sugiere la correcta (propio)', 'Sí', 'Sí', 'Sí'],
        ['Foto realista con IA en el probador (propio)', 'No', 'Sí, 10 por mes', 'Sí, 100 por mes'],
        ['Historial de la bitácora (propio)', '30 días', '6 meses', 'Completo'],
        ['Analítica con ML y su dashboard (propio)', 'No', 'No', 'Sí'],
        ['Exportación completa de los datos de la empresa (propio)', 'No', 'No', 'Sí'],
    ], [4082, 1900, 1900, 1900]),
    ('p', '**Cómo se aplican los planes:**'),
    ('ul', [
        'Cada plan guarda sus límites (máximo de sucursales, de empleados, etc.; vacío significa ilimitado) y '
        'su lista de funciones. Se cambian desde el backend, sin tocar código.',
        'El backend controla cada operación con una dependencia de FastAPI que verifica la función y el '
        'límite del plan, y responde 403 cuando no corresponde. Ocultar el botón en la interfaz no alcanza.',
        'Al bajar de plan no se borra nada: lo que ya existe se conserva y solo se impide crear por encima '
        'del nuevo límite.',
        'El cobro se simula: el administrador de la plataforma asigna, renueva o cambia el plan.',
    ]),

    ('h1', '2.2. Identificación de actores'),
    ('p', 'Se suma un solo actor nuevo, el **administrador de la plataforma**. Los cinco roles que ya existían '
          'pasan a trabajar dentro de una empresa.'),
    ('tabla', ['Actor', 'Ámbito', 'Responsabilidad', 'Rol en el sistema'], [
        ['Administrador de la plataforma', 'Toda la plataforma, fuera de los tenants', 'Registra empresas, '
         'define planes y sus límites, asigna y renueva suscripciones', 'Nuevo'],
        ['Administrador de la empresa', 'Su empresa y todas sus sucursales', 'Gestiona sucursales, empleados, '
         'catálogo, inventario y reportes; ordena traspasos', 'ADMINISTRADOR'],
        ['Encargado de sucursal', 'Su sucursal', 'Inventario de su tienda; pide traspasos y aprueba '
         'devoluciones', 'ENCARGADO'],
        ['Cajero', 'Su sucursal', 'Ventas y reservas en caja, también sin conexión', 'CAJERO'],
        ['Cliente', 'La tienda en línea de una empresa', 'Compra, reserva, se prueba prendas y pide '
         'devoluciones por la web', 'CLIENTE'],
        ['Proveedor', 'Las empresas con las que trabaja', 'Consulta y actualiza sus productos', 'PROVEEDOR'],
        ['Empresa interesada', 'La página pública de la plataforma', 'Contrata un plan y da de alta su '
         'empresa', 'Nuevo (visitante)'],
        ['Sistema', 'Procesos automáticos del backend', 'Verifica el plan, sincroniza, notifica y entrena '
         'los modelos', 'Proceso interno'],
        ['Servicio de IA (externo)', 'Llamado por el backend', 'Interpreta el pedido de reporte; nunca accede '
         'a la base', 'Gemini'],
    ], [2300, 2200, 3482, 1800]),
    ('p', 'El cambio de fondo está en el administrador: en el primer parcial veía todo el sistema; con el '
          'multitenant ve solo lo de su empresa.'),

    ('h1', '2.3. Requisitos funcionales y no funcionales'),
    ('h2', '2.3.1. Requisitos funcionales del enunciado'),
    ('p', 'Son 33 requisitos en cinco módulos. La columna Origen indica la sección del enunciado, para '
          'rastrearlos en ICONIX. La asociación con los casos de uso se completa en la sección 2.5.'),
    ('h3', 'Módulo SaaS: empresas, planes y suscripciones'),
    ('tabla', ['RF', 'El sistema deberá permitir…', 'Origen'], [
        ['RF-01', 'Registrar empresas contratantes (tenants), con al menos dos empresas de prueba', '9.3'],
        ['RF-02', 'Designar un administrador por empresa al darla de alta', '9.3'],
        ['RF-03', 'Asociar usuarios y sucursales a su empresa', '9.3'],
        ['RF-04', 'Definir planes con límites y funciones configurables desde el backend', '9.4'],
        ['RF-05', 'Asignar un plan a una empresa, con fecha de inicio y de vencimiento', '9.5'],
        ['RF-06', 'Consultar el plan contratado y el estado de la suscripción', '9.3, 9.5'],
        ['RF-07', 'Cambiar de plan y renovar la suscripción, con el cobro simulado', '9.5'],
        ['RF-08', 'Suspender o reactivar una suscripción', '9.3'],
        ['RF-09', 'Verificar límites y funciones habilitadas y rechazar lo que el plan no permite', '9.5, 9.6'],
    ], RF3),
    ('h3', 'Módulo offline: PWA y móvil'),
    ('tabla', ['RF', 'El sistema deberá permitir…', 'Origen'], [
        ['RF-10', 'Instalar la aplicación web como PWA', '5.2'],
        ['RF-11', 'Descargar y guardar en local un subconjunto del catálogo, la sucursal autorizada y los datos '
         'mínimos de clientes', '5.3, 6.2, 6.3'],
        ['RF-12', 'Consultar sin conexión productos, precios, tallas, colores y la existencia conocida',
         '5.3, 6.2'],
        ['RF-13', 'Avisar cuando la información consultada puede estar desactualizada', '5.3'],
        ['RF-14', 'Registrar una reserva sin conexión', '5.3, 6.2'],
        ['RF-15', 'Registrar una venta de contado sin conexión, con todos los datos de la sección 7.2',
         '5.3, 7.2'],
        ['RF-16', 'Consultar las reservas y ventas locales pendientes', '5.3, 6.2'],
        ['RF-17', 'Conservar las operaciones locales al cerrar y volver a abrir la aplicación', '5.3, 6.2'],
    ], RF3),
    ('h3', 'Módulo de sincronización'),
    ('tabla', ['RF', 'El sistema deberá permitir…', 'Origen'], [
        ['RF-18', 'Enviar al backend las operaciones pendientes al recuperar la conexión, con reintentos',
         '5.4, 6.4'],
        ['RF-19', 'Identificar cada operación con un identificador único, su empresa y su sucursal', '5.4, 6.4'],
        ['RF-20', 'Seguir el estado de cada operación: local, enviada, confirmada, rechazada o en conflicto',
         '5.4, 6.4'],
        ['RF-21', 'Confirmar una venta offline contra el inventario central, o rechazarla con su motivo', '7.1'],
        ['RF-22', 'Detectar y resolver conflictos, como vender más de lo que hay en existencia', 'Obj. 9'],
        ['RF-23', 'Consultar el resultado de cada sincronización', '5.2, 6.2'],
        ['RF-24', 'Gestionar cambios de prenda dentro de un plazo determinado', '7.2'],
    ], RF3),
    ('h3', 'Módulo de reportes generativos'),
    ('tabla', ['RF', 'El sistema deberá permitir…', 'Origen'], [
        ['RF-25', 'Pedir un reporte en lenguaje natural, escrito o por voz', '8.3'],
        ['RF-26', 'Interpretar el tipo de reporte y sus filtros: fechas, sucursales, categorías y productos',
         '8.3'],
        ['RF-27', 'Armar el reporte con datos reales del tenant, mediante consultas controladas por el backend',
         '8.3, 8.4'],
        ['RF-28', 'Mostrar el resultado en tabla o gráfico y exportarlo a Excel y PDF', '8.1, 8.3'],
        ['RF-29', 'Responder a pedidos ambiguos, incompletos o no soportados sin inventar datos', '8.3'],
        ['RF-30', 'Demostrar al menos cuatro tipos de reporte con filtros variables', '8.3'],
    ], RF3),
    ('h3', 'Módulo de analítica con aprendizaje automático'),
    ('tabla', ['RF', 'El sistema deberá permitir…', 'Origen'], [
        ['RF-31', 'Generar datos sintéticos y entrenar un modelo supervisado y uno no supervisado', '8.4, 8.5'],
        ['RF-32', 'Mostrar las predicciones, los patrones detectados y las métricas de evaluación', '8.5'],
        ['RF-33', 'Mostrar un dashboard analítico con indicadores y gráficos', '8.5'],
    ], RF3),

    ('h2', '2.3.2. Requisitos funcionales pedidos en clase'),
    ('p', 'La docente los pidió en clase, aunque no figuran en el enunciado. En caja el cambio de prenda ya '
          'funciona desde el primer parcial (CU-32); ahora el cliente también puede pedirlo desde la tienda en '
          'línea.'),
    ('h3', 'Devoluciones vía web'),
    ('tabla', ['RF', 'El sistema deberá permitir…'], [
        ['RF-34', 'Que el cliente solicite por la web el cambio o la devolución de una prenda de un pedido '
         'entregado'],
        ['RF-35', 'Configurar por empresa la ventana de devolución, en horas desde la entrega (por ejemplo, 24 '
         'o 48 horas)'],
        ['RF-36', 'Que el encargado apruebe o rechace la solicitud con su motivo'],
        ['RF-37', 'Registrar una nota de devolución que mueve el inventario y mantiene coherentes los ingresos '
         'y egresos'],
        ['RF-38', 'Reportar las devoluciones por hora, motivo, tienda, prenda y tiempo entre la entrega y la '
         'devolución'],
    ], [1100, 8682]),
    ('h2', '2.3.3. Requisitos funcionales propios'),
    ('p', 'El enunciado pide «otras funcionalidades como aporte propio» (sección 7.2). El grupo propone 13 '
          'requisitos en tres frentes.'),
    ('h3', 'Plataforma y planes'),
    ('p', 'Completan el SaaS y le dan contenido a los planes superiores (sección 2.1.1).'),
    ('tabla', ['RF', 'El sistema deberá permitir…'], [
        ['RF-46', 'Personalizar la tienda en línea de la empresa con su logo y sus colores (Profesional y '
         'Empresarial)'],
        ['RF-47', 'Que una empresa interesada contrate un plan desde la web, elija su slug y quede con su '
         'administrador, con el cobro simulado'],
        ['RF-48', 'Exportar todos los datos de la empresa a Excel o CSV (Empresarial)'],
        ['RF-49', 'Enviar avisos por correo a clientes y empleados solo en los planes que lo incluyen'],
        ['RF-50', 'Consultar el consumo del mes de los cupos (reportes y fotos con IA) y de los límites del plan'],
        ['RF-51', 'Que un cliente use una sola cuenta para comprar en las tiendas de varias empresas'],
    ], [1100, 8682]),
    ('h3', 'Traspasos entre sucursales'),
    ('p', 'Desde el primer parcial se registran transferencias entre sucursales (CU-15). Ahora pasan a ser un '
          'pedido con su propio seguimiento.'),
    ('tabla', ['RF', 'El sistema deberá permitir…'], [
        ['RF-39', 'Que una sucursal pida a otra una cantidad de una prenda, en una talla y un color'],
        ['RF-40', 'Que el administrador de la empresa ordene un traspaso sin pedido previo'],
        ['RF-41', 'Seguir el traspaso (solicitado, aprobado, enviado, recibido o rechazado), con su movimiento '
         'de inventario en el origen y en el destino'],
        ['RF-42', 'Sugerir traspasos a partir de las prendas más vendidas por sucursal y de la existencia de '
         'cada una'],
    ], [1100, 8682]),
    ('h3', 'Probador que distingue tallas'),
    ('p', 'La prenda no se estira para acomodarse al cuerpo: se dibuja con sus medidas reales y se compara '
          'con las de la persona, de modo que una talla chica se vea apretada.'),
    ('tabla', ['RF', 'El sistema deberá permitir…'], [
        ['RF-43', 'Cargar una prenda para el probador con foto sin fondo, puntos de referencia y medidas en cm '
         'por talla (busto, cintura, ruedo y largo)'],
        ['RF-44', 'Dibujar la prenda a escala sobre el cuerpo del cliente, con una malla de triángulos que '
         'sigue sus movimientos, marcando las zonas apretadas y sugiriendo la talla correcta'],
        ['RF-45', 'Generar una foto realista de la prueba con IA, descontada del cupo mensual de la empresa'],
    ], [1100, 8682]),
    ('p', 'La escala en centímetros por píxel sale de la estatura registrada en las medidas del cliente; las '
          'medidas de cada talla ya se guardan desde el primer parcial.'),

    ('h2', '2.3.4. Requisitos no funcionales'),
    ('p', 'Los doce primeros son los obligatorios del enunciado. Para cada uno se indica cómo se va a '
          'cumplir, de modo que sea verificable. Del RNF13 en adelante son propios.'),
    ('tabla', ['RNF', 'Requisito', 'Cómo se cumple'], [
        ['RNF01', 'Seguridad', 'JWT con la empresa y el rol como claims; cada endpoint valida rol y plan'],
        ['RNF02', 'Aislamiento de datos', 'Columna de empresa en cada tabla del tenant y Row Level Security '
         'de PostgreSQL con FORCE: sin empresa en el contexto, la consulta devuelve cero filas'],
        ['RNF03', 'Persistencia offline', 'IndexedDB en la PWA y SQLite en Flutter; nada queda solo en '
         'memoria'],
        ['RNF04', 'Integridad transaccional', 'La venta y su movimiento de inventario se confirman en una '
         'sola transacción'],
        ['RNF05', 'Idempotencia', 'Cada operación viaja con un UUID creado en el cliente; si llega dos veces, '
         'el backend devuelve el resultado ya registrado'],
        ['RNF06', 'Recuperación ante fallos', 'Una operación sale de la cola local solo cuando el servidor la '
         'confirma o la rechaza'],
        ['RNF07', 'Mantenibilidad', 'Capas separadas de presentación, negocio, persistencia y sincronización '
         'en la web, el móvil y el backend'],
        ['RNF08', 'Compatibilidad', 'PWA en las versiones actuales de Chrome, Edge y Firefox; Flutter en '
         'Android 10 o superior'],
        ['RNF09', 'Rendimiento', 'Catálogo paginado y descarga incremental para el modo offline; reportes '
         'con agregaciones en la base y no en Python'],
        ['RNF10', 'Observabilidad', 'Bitácora de sincronización por operación, sin contraseñas ni datos de '
         'pago'],
        ['RNF11', 'Calidad', 'Pruebas automatizadas de aislamiento entre empresas, límites de plan, '
         'idempotencia y conflictos de inventario'],
        ['RNF12', 'Coherencia documental', 'Los diagramas ICONIX se terminan sobre el código ya escrito de '
         'cada caso de uso'],
        ['RNF13', 'Costo de la IA (propio)', 'Gemini en su capa gratuita para los reportes; la foto realista '
         'del probador y los reportes con IA, solo en los planes superiores y con cupo mensual'],
        ['RNF14', 'Privacidad de las fotos (propio)', 'La foto del cliente en el probador se procesa en el '
         'celular y no se sube al servidor, salvo la foto realista que el cliente pide'],
        ['RNF15', 'Disponibilidad (propio)', 'Backend y web en Railway, base en Supabase, accesibles desde '
         'cualquier red'],
        ['RNF16', 'Hora local (propio)', 'Fechas guardadas con zona horaria y mostradas en hora de Bolivia '
         '(UTC-4)'],
    ], [1000, 2500, 6282]),

    ('h1', '2.4. Reglas de negocio'),
    ('p', 'Son las reglas que el código hace cumplir y que las pruebas verifican.'),
    ('tabla', ['RN', 'Regla'], [
        ['RN-01', 'Una sucursal no es un tenant: pertenece a una sola empresa, y una empresa tiene una o más '
         'sucursales'],
        ['RN-02', 'Una empresa tiene como máximo una suscripción vigente a la vez'],
        ['RN-03', 'Con la suscripción vencida o suspendida, la empresa solo consulta: no registra ventas, '
         'reservas ni traspasos'],
        ['RN-04', 'Al pasar a un plan menor no se borra nada; solo se impide crear por encima del nuevo límite'],
        ['RN-05', 'Una venta offline es siempre de contado. Recibir el efectivo no la confirma: la confirma el '
         'servidor'],
        ['RN-06', 'Si al sincronizar no alcanza la existencia, la venta queda en conflicto y la resuelve el '
         'encargado, nunca el sistema por su cuenta'],
        ['RN-07', 'Una operación con un UUID ya registrado no se vuelve a aplicar'],
        ['RN-08', 'Un cambio o devolución fuera de la ventana configurada se rechaza'],
        ['RN-09', 'Un traspaso descuenta del origen al enviarse y suma al destino al recibirse; nunca queda '
         'existencia negativa'],
        ['RN-10', 'Los reportes con IA solo leen datos de la empresa del usuario, y solo mediante consultas '
         'predefinidas por el backend'],
        ['RN-11', 'La foto realista y los reportes con IA no se generan si la empresa agotó su cupo del mes'],
        ['RN-12', 'Para iniciar sesión hay que indicar el slug de la empresa; sin slug solo entra el '
         'administrador de la plataforma, que no ve los datos de ninguna empresa'],
        ['RN-13', 'Un cliente tiene una sola cuenta en la plataforma; sus pedidos, reservas y favoritos se '
         'guardan por empresa, y una empresa no ve lo que el cliente hizo en otra'],
        ['RN-14', 'El slug de una empresa es único en la plataforma y no se cambia después del alta'],
    ], [1100, 8682]),

    *BLOQUE_25,
    *BLOQUE_26,

    # =====================================================================
    ('salto',),
    ('cap', 'CAPÍTULO III. ANÁLISIS Y DISEÑO CON ICONIX'),
    ('h1', '3.1. Modelo de dominio'),
    ('pend', 'Entidades nuevas (plataforma, empresa, plan, suscripción, operación de sincronización, '
             'traspaso, nota de devolución) y su relación con las del primer parcial.'),
    ('h1', '3.2. Diagramas de robustez'),
    ('pend', 'Uno por caso de uso nuevo o modificado. Se dibujan sobre el código terminado.'),
    ('h1', '3.3. Diagramas de secuencia UML'),
    ('pend', 'Uno por caso de uso nuevo o modificado, derivado de su ficha.'),
    ('h1', '3.4. Diagrama de clases UML'),
    ('pend', 'Diagrama de clases refinado tras la robustez y la secuencia.'),
    ('h1', '3.5. Diseño de la base de datos'),
    ('pend', 'Tablas nuevas, columna de empresa en las tablas del tenant y políticas de Row Level Security.'),
    ('h1', '3.6. Diseño de interfaces de usuario'),
    ('pend', 'Pantallas nuevas: administración de la plataforma, plan y suscripción, estado de '
             'sincronización, reportes con IA y dashboard analítico.'),

    # =====================================================================
    ('salto',),
    ('cap', 'CAPÍTULO IV. DESARROLLO E IMPLEMENTACIÓN'),
    ('h1', '4.1. Herramientas y tecnologías utilizadas'),
    ('p', 'Se mantienen las tecnologías del primer parcial, que coinciden con las obligatorias del enunciado, '
          'y se suman las que piden la PWA, el móvil offline y los reportes con IA.'),
    ('tabla', ['Componente', 'Tecnología exigida', 'Tecnología usada'], [
        ['Backend', 'Python + FastAPI', 'FastAPI 0.141, SQLAlchemy 2.0, Alembic, Pydantic 2; Gunicorn con '
         'Uvicorn'],
        ['Frontend web', 'Angular', 'Angular 22 con TypeScript 6'],
        ['PWA', 'Service Worker, Web App Manifest, IndexedDB', 'Service Worker y manifest de Angular; '
         'IndexedDB para el almacenamiento local'],
        ['Aplicación móvil', 'Flutter + Dart', 'Flutter con Dart 3.5 o superior; Dio como cliente HTTP'],
        ['Persistencia móvil', 'SQLite', 'SQLite en el dispositivo'],
        ['Base de datos central', 'PostgreSQL', 'PostgreSQL 17 en Supabase, con Row Level Security'],
        ['Integración', 'API REST', 'API REST con JWT, documentada con OpenAPI'],
        ['Inteligencia artificial', 'Modelo o servicio por API', 'Gemini (capa gratuita) para interpretar '
         'los pedidos de reporte'],
        ['Visión en el móvil', '—', 'Google ML Kit (detección de pose) para el probador'],
        ['Correo', '—', 'API de Brevo para los avisos y la recuperación de contraseña'],
        ['Modelado', 'UML 2.5+', 'Enterprise Architect'],
        ['Metodología', 'ICONIX', 'ICONIX en tres ciclos'],
        ['Despliegue', 'Nube, accesible externamente', 'Railway (backend y web) y Supabase (base de datos)'],
        ['Control de versiones', '—', 'Git y GitHub, con un pull request por caso de uso'],
    ], [2200, 3000, 4582]),
    ('h1', '4.2. Diseño de la arquitectura del sistema'),
    ('pend', 'Arquitectura en capas y despliegue, con el contexto de empresa en cada petición y el módulo de '
             'sincronización.'),
    ('h1', '4.3. Implementación de la base de datos'),
    ('pend', 'Migraciones Alembic del multitenant y políticas de Row Level Security.'),
    ('h1', '4.4. Desarrollo de los módulos del sistema'),
    ('pend', 'Un apartado por módulo del alcance, con su evidencia.'),
    ('h1', '4.5. Integración de componentes'),
    ('pend', 'Cómo se conectan la PWA, Flutter, el backend, la IA y el módulo de analítica.'),

    # =====================================================================
    ('salto',),
    ('cap', 'CAPÍTULO V. PRUEBAS Y RESULTADOS'),
    ('h1', '5.1. Plan de pruebas'),
    ('p', 'Las pruebas siguen la trazabilidad de ICONIX: cada requisito crítico tiene al menos una prueba '
          'automatizada que lo verifica. Se parte de la batería del primer parcial (más de 800 pruebas con '
          'pytest sobre una base PostgreSQL local) y se agregan cuatro familias nuevas:'),
    ('ul', [
        '**Aislamiento:** un usuario de la empresa A no puede consultar, modificar ni eliminar datos de la '
        'empresa B, en ningún endpoint; y ninguna tabla del tenant queda sin Row Level Security.',
        '**Planes:** cada límite y cada función del plan se rechaza al excederse, y nada se borra al bajar '
        'de plan.',
        '**Sincronización:** reenviar una operación ya confirmada no la duplica; una falla de red no la saca '
        'de la cola local.',
        '**Conflictos de inventario:** una venta offline sin existencia suficiente queda en conflicto y no '
        'deja existencia negativa.',
    ]),
    ('h1', '5.2. Pruebas funcionales'),
    ('pend', 'Resultados por caso de uso.'),
    ('h1', '5.3. Pruebas de integración'),
    ('pend', 'PWA y Flutter contra el backend, en línea y sin conexión.'),
    ('h1', '5.4. Corrección de errores'),
    ('pend', 'Errores encontrados y cómo se corrigieron.'),
    ('h1', '5.5. Resultados de las pruebas'),
    ('pend', 'Cantidad de pruebas, aprobadas y cobertura de requisitos.'),
    ('h1', '5.6. Casos de prueba'),
    ('pend', 'Tabla de casos de prueba asociados a cada requisito.'),

    # =====================================================================
    ('salto',),
    ('cap', 'CAPÍTULO VI. CONCLUSIONES Y RECOMENDACIONES'),
    ('h1', '6.1. Conclusiones'),
    ('pend', 'Se escriben al cerrar el Ciclo 3.'),
    ('h1', '6.2. Recomendaciones'),
    ('pend', 'Se escriben al cerrar el Ciclo 3.'),

    ('salto',),
    ('cap', '7. BIBLIOGRAFÍA'),
    ('ul', [
        'Rosenberg, D. y Stephens, M. (2007). Use Case Driven Object Modeling with UML: Theory and Practice. '
        'Apress.',
        'Rosenberg, D. y Scott, K. (1999). Use Case Driven Object Modeling with UML: A Practical Approach. '
        'Addison-Wesley.',
        'Object Management Group (2017). OMG Unified Modeling Language (OMG UML), versión 2.5.1.',
        'Garzón Cuéllar, A. (2026). Examen Parcial 2 — Sistemas de Información 2, S2-2026. UAGRM.',
        'Manual introductorio de ICONIX. Material de la materia.',
        'PostgreSQL Global Development Group. PostgreSQL Documentation: Row Security Policies.',
        'Angular. Documentación oficial: Service Workers y PWA.',
        'Flutter. Documentación oficial: persistencia de datos con SQLite.',
        'FastAPI. Documentación oficial: dependencias y seguridad.',
    ]),

    ('salto',),
    ('cap', '8. ANEXOS'),
    ('pend', 'Enlaces al sistema desplegado, al repositorio y a los diagramas exportados.'),
]
