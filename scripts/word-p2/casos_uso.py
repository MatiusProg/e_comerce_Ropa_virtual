# Secciones 2.5 (catálogo de casos de uso por ciclo) y 2.6 (fichas) del documento del 2do parcial.

CU_ANCHOS = [900, 3582, 2100, 1200, 2000]
CU_ENC = ['CU', 'Caso de uso', 'Actor principal', 'Evoluciona', 'RF']

CICLO_1 = [
    ['CU-43', 'Gestionar empresas', 'Administrador de la plataforma', '—', 'RF-01, RF-02, RF-03'],
    ['CU-44', 'Gestionar planes', 'Administrador de la plataforma', '—', 'RF-04'],
    ['CU-45', 'Gestionar suscripciones', 'Administrador de la plataforma', '—', 'RF-05, RF-07, RF-08'],
    ['CU-46', 'Consultar plan y consumo', 'Administrador de la empresa', '—', 'RF-06, RF-50'],
    ['CU-47', 'Verificar límites y funciones del plan', 'Sistema', '—', 'RF-09'],
    ['CU-48', 'Iniciar sesión en una empresa', 'Todos los usuarios', 'CU-02', 'RF-03'],
    ['CU-49', 'Registrar cliente con cuenta única', 'Cliente', 'CU-01', 'RF-51'],
    ['CU-50', 'Gestionar usuarios de la empresa', 'Administrador de la empresa', 'CU-03', 'RF-03, RF-09'],
    ['CU-51', 'Gestionar sucursales de la empresa', 'Administrador de la empresa', 'CU-05', 'RF-03, RF-09'],
    ['CU-52', 'Gestionar empleados de la empresa', 'Administrador de la empresa', 'CU-06', 'RF-09'],
    ['CU-53', 'Contratar un plan desde la web (propio)', 'Empresa interesada', '—', 'RF-47'],
    ['CU-54', 'Personalizar la tienda de la empresa (propio)', 'Administrador de la empresa', '—', 'RF-46'],
]
CICLO_2 = [
    ['CU-55', 'Preparar el dispositivo para trabajar offline', 'Cajero', '—', 'RF-10 a RF-13'],
    ['CU-56', 'Registrar venta offline', 'Cajero', 'CU-31', 'RF-15'],
    ['CU-57', 'Registrar reserva offline', 'Cajero', 'CU-22', 'RF-14'],
    ['CU-58', 'Sincronizar operaciones pendientes', 'Sistema', '—', 'RF-18 a RF-21'],
    ['CU-59', 'Consultar operaciones pendientes', 'Cajero', '—', 'RF-16, RF-17, RF-20, RF-23'],
    ['CU-60', 'Resolver conflictos de sincronización', 'Encargado de sucursal', '—', 'RF-22'],
    ['CU-61', 'Abrir y cerrar caja con ventas offline', 'Cajero', 'CU-30', 'RF-15, RF-21'],
    ['CU-62', 'Registrar cambio o devolución en caja', 'Cajero', 'CU-32', 'RF-24, RF-37'],
    ['CU-63', 'Configurar la ventana de devolución', 'Administrador de la empresa', '—', 'RF-35'],
    ['CU-64', 'Solicitar cambio o devolución por la web', 'Cliente', '—', 'RF-34'],
    ['CU-65', 'Atender solicitud de devolución', 'Encargado de sucursal', '—', 'RF-36, RF-37'],
    ['CU-66', 'Notificar eventos por correo según el plan', 'Sistema', 'CU-40', 'RF-49'],
]
CICLO_3 = [
    ['CU-67', 'Generar reporte con IA por texto o voz', 'Administrador de la empresa', 'CU-35',
     'RF-25 a RF-30'],
    ['CU-68', 'Generar reportes de gestión con devoluciones', 'Administrador de la empresa', 'CU-37',
     'RF-38'],
    ['CU-69', 'Entrenar los modelos de analítica', 'Sistema', '—', 'RF-31'],
    ['CU-70', 'Consultar el dashboard analítico', 'Administrador de la empresa', '—', 'RF-32, RF-33'],
    ['CU-71', 'Solicitar traspaso entre sucursales', 'Encargado de sucursal', 'CU-15', 'RF-39, RF-40'],
    ['CU-72', 'Atender traspaso', 'Encargado de sucursal', '—', 'RF-41'],
    ['CU-73', 'Consultar traspasos sugeridos (propio)', 'Administrador de la empresa', '—', 'RF-42'],
    ['CU-74', 'Preparar prenda para el probador (propio)', 'Administrador de la empresa', 'CU-11', 'RF-43'],
    ['CU-75', 'Probarse una prenda con su talla real (propio)', 'Cliente', 'CU-21', 'RF-44'],
    ['CU-76', 'Generar foto realista de la prueba (propio)', 'Cliente', '—', 'RF-45'],
    ['CU-77', 'Exportar los datos de la empresa (propio)', 'Administrador de la empresa', '—', 'RF-48'],
]

BLOQUE_25 = [
    ('h1', '2.5. Diagrama UML de casos de uso'),
    ('p', 'Son 35 casos de uso, numerados desde el CU-43 para seguir la lista del primer parcial. Los que '
          'tienen algo en la columna Evoluciona reemplazan a un caso de uso anterior: se vuelven a especificar '
          'y a modelar completos, porque el multitenant, los planes o el modo offline cambian su flujo. Los '
          'marcados como propios son aporte del grupo. La numeración sigue el orden de los ciclos, de modo '
          'que cada presentación cierra un bloque contiguo.'),
    ('p', 'Todos los RF, del RF-01 al RF-51, quedan asociados a por lo menos un caso de uso. Los casos de uso '
          'que el plan controla incluyen al CU-47, que verifica la función y el límite antes de continuar.'),
    ('h3', 'Ciclo 1 — Plataforma SaaS y aislamiento (presentación del dom 25/10)'),
    ('tabla', CU_ENC, CICLO_1, CU_ANCHOS),
    ('h3', 'Ciclo 2 — Offline, sincronización y devoluciones (presentación del dom 01/11)'),
    ('tabla', CU_ENC, CICLO_2, CU_ANCHOS),
    ('h3', 'Ciclo 3 — IA, analítica y aportes propios (presentación del dom 08/11)'),
    ('tabla', CU_ENC, CICLO_3, CU_ANCHOS),
    ('pend', 'Diagrama de casos de uso por paquete (Plataforma SaaS, Seguridad, Offline y sincronización, '
             'Devoluciones, Reportes y analítica, Inventario y probador), dibujado en Enterprise Architect.'),
]



def ficha(cu, nombre, descripcion, actores, iniciador, pre, flujo, alternos, post, rastreo):
    return ('tabla', ['Caso de uso', f'{cu} — {nombre}'], [
        ['Descripción', descripcion],
        ['Actores', actores],
        ['Iniciador', iniciador],
        ['Precondiciones', pre],
        ['Flujo principal', '\n'.join(f'{i}. {p}' for i, p in enumerate(flujo, 1))],
        ['Flujos alternativos', '\n'.join(alternos)],
        ['Postcondiciones', post],
        ['Rastreo', rastreo],
    ], [2300, 7482])


BLOQUE_26 = [
    ('h1', '2.6. Especificación de casos de uso'),
    ('p', 'Cada ficha sigue el formato de ICONIX: descripción, precondición, flujo normal, flujos '
          'alternativos y postcondición. De cada una sale su diagrama de robustez (3.2) y su diagrama de '
          'secuencia (3.3). Los flujos alternativos se numeran con el paso del flujo principal en que se '
          'desvían. La fila Rastreo une la ficha con sus requisitos y reglas de negocio.'),
    ('h2', '2.6.1. Ciclo 1'),

    ficha('CU-43', 'Gestionar empresas',
          'Permite al administrador de la plataforma registrar, consultar, editar y dar de baja las empresas '
          'contratantes, designando al administrador de cada una.',
          'Administrador de la plataforma', 'Administrador de la plataforma',
          'El administrador de la plataforma inició sesión sin slug de empresa.',
          ['El administrador abre la lista de empresas.',
           'El sistema muestra las empresas con su slug, su plan y su estado.',
           'El administrador elige «Nueva empresa» e ingresa la razón social, el NIT, el slug, el plan inicial '
           'y los datos del administrador de la empresa.',
           'El sistema valida los datos y verifica que el slug no exista.',
           'El sistema crea, en una sola transacción, la empresa, su suscripción al plan elegido, su sucursal '
           'principal y el usuario administrador con una contraseña temporal.',
           'El sistema envía por correo el acceso al administrador de la empresa y muestra la empresa en la '
           'lista.'],
          ['3a. Editar: el administrador modifica los datos, salvo el slug, y el sistema los guarda.',
           '3b. Dar de baja: la empresa queda inactiva y ninguno de sus usuarios puede iniciar sesión; no se '
           'borra ningún dato.',
           '4a. Slug repetido o datos inválidos: el sistema señala el campo y vuelve al paso 3.',
           '5a. Falla la creación: el sistema revierte la transacción y no queda nada a medias.'],
          'La empresa existe con su suscripción vigente, su sucursal principal y su administrador, y sus '
          'datos quedan aislados de las demás.',
          'RF-01, RF-02, RF-03 · RN-01, RN-02, RN-14'),

    ficha('CU-44', 'Gestionar planes',
          'Permite al administrador de la plataforma definir los planes con su precio simulado, sus límites y '
          'sus funciones habilitadas.',
          'Administrador de la plataforma', 'Administrador de la plataforma',
          'El administrador de la plataforma inició sesión.',
          ['El administrador abre la lista de planes.',
           'El sistema muestra cada plan con su precio, sus límites, sus funciones y cuántas empresas lo usan.',
           'El administrador elige crear o editar un plan e ingresa el nombre, el precio mensual, la duración, '
           'los límites (sucursales, empleados, cupos de IA; vacío significa ilimitado) y las funciones '
           'incluidas.',
           'El sistema valida que el nombre sea único y que los límites sean enteros positivos o vacíos.',
           'El sistema guarda el plan; los cambios rigen desde la siguiente verificación para todas las '
           'empresas del plan.'],
          ['3a. Desactivar un plan: deja de ofrecerse para contrataciones nuevas; las empresas que lo tienen '
           'lo conservan hasta su vencimiento.',
           '4a. Datos inválidos: el sistema señala el campo y vuelve al paso 3.',
           '5a. El nuevo límite queda por debajo de lo que una empresa ya tiene: no se borra nada, solo se '
           'impide crear más (RN-04).'],
          'El plan queda guardado y se aplica sin modificar el código.',
          'RF-04 · RN-04'),

    ficha('CU-45', 'Gestionar suscripciones',
          'Permite al administrador de la plataforma asignar un plan a una empresa con sus fechas, cambiarlo, '
          'renovarlo, suspenderlo y reactivarlo, con el cobro simulado.',
          'Administrador de la plataforma', 'Administrador de la plataforma',
          'La empresa está registrada.',
          ['El administrador abre la ficha de la empresa.',
           'El sistema muestra la suscripción vigente y el historial de suscripciones.',
           'El administrador elige asignar o cambiar el plan, e indica el plan y la fecha de inicio.',
           'El sistema calcula la fecha de vencimiento según la duración del plan y registra el pago '
           'simulado.',
           'El sistema cierra la suscripción anterior y deja la nueva como vigente, en una sola transacción.',
           'El sistema muestra el estado actualizado.'],
          ['3a. Renovar: el sistema extiende el vencimiento a partir de la fecha de vencimiento actual.',
           '3b. Suspender o reactivar: el sistema cambia el estado; con la suscripción suspendida, la empresa '
           'solo consulta (RN-03).',
           '5a. Cambio a un plan menor: el sistema avisa qué recursos superan el nuevo límite y conserva todo '
           '(RN-04).',
           'E1. Vencimiento: un proceso diario marca como vencidas las suscripciones cuya fecha pasó.'],
          'La empresa tiene exactamente una suscripción vigente y queda el historial.',
          'RF-05, RF-07, RF-08 · RN-02, RN-03, RN-04'),

    ficha('CU-46', 'Consultar plan y consumo',
          'Permite al administrador de la empresa ver su plan, el estado de la suscripción y cuánto usó de '
          'cada límite y cupo.',
          'Administrador de la empresa', 'Administrador de la empresa',
          'El administrador inició sesión en su empresa.',
          ['El administrador abre «Mi plan».',
           'El sistema muestra el plan, el estado de la suscripción, sus fechas y los días que faltan para el '
           'vencimiento.',
           'El sistema muestra cada límite con su uso (por ejemplo, 2 de 10 sucursales), los cupos del mes '
           'de reportes y fotos con IA, y las funciones incluidas y no incluidas.',
           'El administrador puede comparar con los otros planes.'],
          ['2a. Suscripción vencida o suspendida: el sistema la destaca y avisa que la empresa está en modo '
           'solo consulta.'],
          'No se modifica ningún dato.',
          'RF-06, RF-50'),

    ficha('CU-47', 'Verificar límites y funciones del plan',
          'Antes de cada operación controlada, el backend comprueba que la empresa tenga una suscripción '
          'vigente, que su plan incluya la función y que no supere el límite o el cupo. Lo incluyen los casos '
          'de uso que crean recursos limitados o usan funciones de pago.',
          'Sistema', 'Un caso de uso que lo incluye',
          'La petición llega autenticada con la empresa en el token.',
          ['Llega una operación controlada (crear sucursal o empleado, pedir un reporte o una foto con IA, '
           'etc.).',
           'El sistema obtiene la suscripción vigente de la empresa del token.',
           'El sistema verifica que el plan incluya la función.',
           'El sistema cuenta lo usado y lo compara con el límite o el cupo.',
           'El sistema deja continuar la operación.'],
          ['2a. Sin suscripción vigente: si la operación escribe, responde 403 y la empresa queda en modo solo '
           'consulta.',
           '3a. Función no incluida: responde 403 con el código plan_limit, y la interfaz ofrece ver los '
           'planes.',
           '4a. Límite o cupo alcanzado: responde 403 con el código plan_limit, el límite y el uso actual.'],
          'La operación continúa o se rechaza sin cambiar nada. El control vive en el backend, no solo en la '
          'interfaz.',
          'RF-09 · RN-03, RN-04, RN-11'),

    ficha('CU-48', 'Iniciar sesión en una empresa',
          'Evoluciona el CU-02. Permite a un usuario autenticarse dentro de una empresa, indicada por su slug, '
          'y obtener un token con la empresa y su rol.',
          'Administrador de la empresa, encargado, cajero, cliente, proveedor y administrador de la plataforma',
          'El usuario',
          'El usuario tiene una cuenta activa.',
          ['El usuario abre la pantalla de inicio de sesión e ingresa el slug de la empresa, su correo y su '
           'contraseña. En la tienda en línea el slug ya viene en la dirección.',
           'El sistema busca la empresa por su slug.',
           'El sistema verifica que la empresa tenga una suscripción vigente.',
           'El sistema valida las credenciales del usuario dentro de esa empresa.',
           'El sistema emite el token con el usuario, la empresa y el rol.',
           'El sistema muestra el menú del rol con la marca de la empresa.'],
          ['1a. Sin slug: solo puede entrar el administrador de la plataforma (RN-12).',
           '2a. El slug no existe o la empresa está dada de baja: el sistema muestra «empresa no encontrada».',
           '3a. Suscripción vencida o suspendida: el usuario entra en modo solo consulta (RN-03).',
           '4a. Credenciales incorrectas: el sistema muestra el error sin decir cuál dato falló.',
           '6a. Cerrar sesión: el sistema invalida el token.'],
          'El usuario tiene un token con la empresa como claim, y todas sus consultas quedan filtradas por '
          'Row Level Security.',
          'RF-03 · RN-12, RN-13 · RNF01, RNF02'),

    ficha('CU-49', 'Registrar cliente con cuenta única',
          'Evoluciona el CU-01. Permite a una persona crear una sola cuenta de cliente en la plataforma y '
          'usarla en las tiendas de varias empresas.',
          'Cliente', 'Cliente',
          'La persona está en la tienda en línea de una empresa.',
          ['El cliente elige «Crear cuenta».',
           'El sistema muestra el formulario de registro.',
           'El cliente ingresa sus nombres, apellidos, correo y contraseña.',
           'El sistema valida los datos y verifica que el correo no tenga cuenta en la plataforma.',
           'El sistema crea la cuenta del cliente y la asocia a la empresa de la tienda.',
           'El sistema inicia la sesión del cliente en esa empresa.'],
          ['4a. Datos inválidos: el sistema señala cada campo y vuelve al paso 3.',
           '4b. El correo ya tiene cuenta, creada en otra empresa: el sistema ofrece iniciar sesión con ella y '
           'la asocia a esta empresa, sin duplicarla (RN-13).'],
          'Existe una sola cuenta para ese correo, asociada a la empresa de la tienda.',
          'RF-51 · RN-13'),

    ficha('CU-50', 'Gestionar usuarios de la empresa',
          'Evoluciona el CU-03. Permite al administrador de la empresa crear, editar y desactivar los usuarios '
          'de su empresa, con su rol y su sucursal.',
          'Administrador de la empresa', 'Administrador de la empresa',
          'El administrador inició sesión en su empresa.',
          ['El administrador abre la lista de usuarios.',
           'El sistema muestra solo los usuarios de su empresa.',
           'El administrador elige «Nuevo usuario» e ingresa sus datos, su rol y su sucursal.',
           'El sistema verifica el límite del plan (incluye el CU-47).',
           'El sistema valida los datos y que la sucursal sea de la misma empresa.',
           'El sistema guarda el usuario con la empresa del token.'],
          ['3a. Editar o desactivar: el sistema guarda el cambio; un usuario desactivado no puede iniciar '
           'sesión.',
           '4a. Límite alcanzado: el sistema rechaza la creación e informa el límite del plan.',
           '5a. El rol de administrador de la plataforma no se puede asignar desde una empresa.'],
          'El usuario pertenece a la empresa y solo ve los datos de ella.',
          'RF-03, RF-09 · RNF02'),

    ficha('CU-51', 'Gestionar sucursales de la empresa',
          'Evoluciona el CU-05. Permite al administrador de la empresa registrar, editar y desactivar sus '
          'sucursales, dentro del límite de su plan.',
          'Administrador de la empresa', 'Administrador de la empresa',
          'El administrador inició sesión en su empresa.',
          ['El administrador abre la lista de sucursales.',
           'El sistema muestra las sucursales de su empresa, con el uso del límite (por ejemplo, 2 de 2).',
           'El administrador elige «Nueva sucursal» e ingresa la ciudad, la dirección, el horario y la '
           'capacidad de vestidores.',
           'El sistema verifica el límite de sucursales activas (incluye el CU-47).',
           'El sistema valida los datos y guarda la sucursal en la empresa del token.'],
          ['3a. Editar: el sistema guarda los cambios.',
           '3b. Desactivar: la sucursal deja de contar para el límite; no se borra su historia.',
           '4a. Límite alcanzado: el sistema rechaza la creación y ofrece ver los planes.'],
          'La sucursal pertenece a una sola empresa.',
          'RF-03, RF-09 · RN-01, RN-04'),

    ficha('CU-52', 'Gestionar empleados de la empresa',
          'Evoluciona el CU-06. Permite al administrador de la empresa registrar encargados y cajeros y '
          'asignarlos a una de sus sucursales, dentro del límite de su plan.',
          'Administrador de la empresa', 'Administrador de la empresa',
          'El administrador inició sesión y la empresa tiene al menos una sucursal.',
          ['El administrador abre la lista de empleados.',
           'El sistema muestra los empleados de su empresa y el uso del límite.',
           'El administrador ingresa los datos del empleado, su cargo y su sucursal.',
           'El sistema verifica el límite de empleados activos (incluye el CU-47).',
           'El sistema valida que la sucursal sea de la misma empresa y guarda al empleado con su usuario.'],
          ['3a. Editar o desactivar: el sistema guarda el cambio; un empleado desactivado deja de contar para '
           'el límite.',
           '4a. Límite alcanzado: el sistema rechaza el registro e informa el límite.'],
          'El empleado queda asignado a una sucursal de su empresa.',
          'RF-09 · RN-04'),

    ficha('CU-53', 'Contratar un plan desde la web',
          'Aporte propio. Permite a una empresa interesada elegir un plan, dar de alta su empresa y obtener su '
          'acceso, con el cobro simulado.',
          'Empresa interesada', 'Empresa interesada',
          'Ninguna.',
          ['La empresa interesada abre la página de planes.',
           'El sistema muestra los tres planes con su precio y sus funciones.',
           'La empresa elige un plan.',
           'La empresa ingresa sus datos, el slug que desea y los datos de su administrador.',
           'El sistema valida los datos y verifica que el slug esté libre.',
           'El sistema simula el pago y muestra el comprobante.',
           'El sistema crea la empresa, su suscripción, su sucursal principal y su administrador, igual que en '
           'el paso 5 del CU-43.',
           'El sistema envía el correo de bienvenida y lleva al inicio de sesión con el slug.'],
          ['5a. Slug ocupado: el sistema sugiere otros disponibles.',
           '6a. Pago simulado rechazado: no se crea nada.'],
          'La empresa queda registrada con su plan y su administrador.',
          'RF-47, RF-01, RF-02, RF-05 · RN-14'),

    ficha('CU-54', 'Personalizar la tienda de la empresa',
          'Aporte propio. Permite al administrador de la empresa poner su logo y sus colores en la tienda en '
          'línea.',
          'Administrador de la empresa', 'Administrador de la empresa',
          'El administrador inició sesión y su plan incluye la función.',
          ['El administrador abre «Mi tienda».',
           'El sistema muestra el logo y los colores actuales con una vista previa.',
           'El administrador sube el logo y elige el color principal y el secundario.',
           'El sistema valida el formato y el tamaño del logo.',
           'El sistema guarda la marca; la tienda en línea y la PWA la muestran.'],
          ['1a. El plan no incluye la función: el sistema la muestra como no incluida y ofrece ver los planes '
           '(CU-47).',
           '4a. Imagen inválida: el sistema la rechaza y vuelve al paso 3.'],
          'La tienda de la empresa muestra su marca.',
          'RF-46'),

    ('h2', '2.6.2. Ciclo 2'),
    ('pend', 'Fichas del CU-55 al CU-66. Se escriben al empezar el Ciclo 2 (lun 26/10).'),
    ('h2', '2.6.3. Ciclo 3'),
    ('pend', 'Fichas del CU-67 al CU-77. Se escriben al empezar el Ciclo 3 (lun 02/11).'),
]
