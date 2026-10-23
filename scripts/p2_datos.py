# Datos del 2do parcial para los generadores de Enterprise Architect (reemplaza a p2_ciclo1_datos.py):
#   - 2.5 diagramas de casos de uso: uno general y uno por caso de uso;
#   - 3.2 diagramas de robustez, al estilo de nuestros diagramas de comunicación del 1er parcial
#     (2.2): una pantalla, un Gestor por caso de uso y sus entidades.
#
# Correcciones de la ing del 22/10 y decisión de Luis del 23/10:
#   - los casos de uso se numeran desde el CU-01 y no hay ciclos;
#   - la robustez es como el diagrama de comunicación, pero NUNCA se comunican dos entidades;
#   - el generador dibuja el diagrama SIN los mensajes: solo los enlaces. Los mensajes van en
#     docs/diagramas/2do Parcial/3.2-robustez-mensajes.md y se cargan a mano en EA, porque así
#     quedan más prolijos que con el generador;
#   - sin controladores alternativos en rojo.
#
# Uso:  python -X utf8 scripts/p2_datos.py
#   escribe scripts/ea-p2.datos.json y el .md de los mensajes.
import json
from pathlib import Path

AQUI = Path(__file__).parent
MD = AQUI.parent / 'docs' / 'diagramas' / '2do Parcial' / '3.2-robustez-mensajes.md'

# ------------------------------------------------------------------ 2.5 ---
ACTORES = {
    'Usuario': {'abstracto': True,
                'notas': 'Actor abstracto: cualquiera que inicia sesión en una empresa (CU-06).'},
    'Administrador de la plataforma': {'padre': 'Usuario',
                                       'notas': 'Opera la plataforma SaaS, fuera de los tenants. Entra sin slug.'},
    'Administrador de la empresa': {'padre': 'Usuario',
                                    'notas': 'Administra su empresa (tenant) y todas sus sucursales.'},
    'Encargado de sucursal': {'padre': 'Usuario', 'notas': 'Opera su sucursal dentro de una empresa.'},
    'Cajero': {'padre': 'Usuario', 'notas': 'Vende en caja dentro de su sucursal.'},
    'Proveedor': {'padre': 'Usuario', 'notas': 'Consulta y actualiza sus productos.'},
    'Cliente': {'padre': 'Usuario', 'notas': 'Una sola cuenta en la plataforma, que usa en varias empresas (RN-13).'},
    'Empresa interesada': {'notas': 'Visitante de la página pública que contrata un plan (CU-11).'},
}

CASOS = [
    # (id, nombre, actores, incluye, notas)
    ('CU-01', 'Gestionar empresas', ['Administrador de la plataforma'], [],
     'Registrar, editar y dar de baja empresas, con su administrador. RF-01, RF-02, RF-03.'),
    ('CU-02', 'Gestionar planes', ['Administrador de la plataforma'], [],
     'Precio simulado, límites y funciones de cada plan. RF-04.'),
    ('CU-03', 'Gestionar suscripciones', ['Administrador de la plataforma'], [],
     'Asignar, cambiar, renovar, suspender y reactivar, con el cobro simulado. RF-05, RF-07, RF-08.'),
    ('CU-04', 'Consultar plan y consumo', ['Administrador de la empresa'], [],
     'Plan, estado de la suscripción, uso de límites y cupos. RF-06, RF-50.'),
    ('CU-05', 'Verificar límites y funciones del plan', [], [],
     'Lo incluyen los casos de uso que crean recursos limitados o usan funciones de pago. RF-09.'),
    ('CU-06', 'Iniciar sesión en una empresa', ['Usuario'], [],
     'Reemplaza al CU-02 del primer parcial. Login con el slug de la empresa; token con empresa y rol. RN-12.'),
    ('CU-07', 'Registrar cliente con cuenta única', ['Cliente'], [],
     'Reemplaza al CU-01 del primer parcial. Una cuenta por persona en toda la plataforma. RF-51, RN-13.'),
    ('CU-08', 'Gestionar usuarios de la empresa', ['Administrador de la empresa'], ['CU-05'],
     'Reemplaza al CU-03 del primer parcial. Solo los usuarios de su empresa, dentro del límite. RF-03, RF-09.'),
    ('CU-09', 'Gestionar sucursales de la empresa', ['Administrador de la empresa'], ['CU-05'],
     'Reemplaza al CU-05 del primer parcial. Límite de sucursales activas. RF-03, RF-09.'),
    ('CU-10', 'Gestionar empleados de la empresa', ['Administrador de la empresa'], ['CU-05'],
     'Reemplaza al CU-06 del primer parcial. Límite de empleados activos. RF-09.'),
    ('CU-11', 'Contratar un plan desde la web', ['Empresa interesada'], [],
     'Aporte propio. Alta de la empresa con el cobro simulado. RF-47.'),
    ('CU-12', 'Personalizar la tienda de la empresa', ['Administrador de la empresa'], ['CU-05'],
     'Aporte propio. Logo y colores en la tienda en línea. RF-46.'),
]

# ------------------------------------------------------------------ 3.2 ---
# Por caso de uso:
#   a = actores, f = fronteras, c = controladores (el primero es el Gestor del caso de uso),
#   e = entidades, grupos = qué es cada grupo de mensajes,
#   m = mensajes (grupo, de, a, operación). Un actor se escribe 'A:Nombre'.
# El generador dibuja un enlace por par de participantes que se mandan algún mensaje; los mensajes en sí
# van al .md. Reglas que se verifican: Actor-Frontera, Frontera-Control, Control-Control y
# Control-Entidad. Nunca Entidad-Entidad ni Frontera-Frontera.
PA, AE = 'A:Administrador de la plataforma', 'A:Administrador de la empresa'

ROBUSTEZ = [
    dict(cu='CU-01', n='Gestionar empresas', a=['Administrador de la plataforma'],
         f=['PantallaEmpresas', 'CanalDeCorreo'], c=['GestorEmpresas', 'GestorAutenticacion'],
         e=['Empresa', 'Plan', 'Suscripcion', 'Sucursal', 'Usuario'],
         grupos=['flujo principal: alta de la empresa', 'alternativo 3a: editar',
                 'alternativo 3b: dar de baja', 'alternativos 4a y 5a: datos inválidos o falla la creación'],
         m=[(1, PA, 'PantallaEmpresas', 'abrirListaEmpresas()'),
            (1, 'PantallaEmpresas', 'GestorEmpresas', 'listarEmpresas()'),
            (1, 'GestorEmpresas', 'GestorAutenticacion', 'autorizar("ADMIN_PLATAFORMA")'),
            (1, 'GestorEmpresas', 'Empresa', 'listar()'),
            (1, PA, 'PantallaEmpresas', 'registrarEmpresa(datos)'),
            (1, 'PantallaEmpresas', 'GestorEmpresas', 'crearEmpresa(datos)'),
            (1, 'GestorEmpresas', 'GestorEmpresas', 'validarDatos(datos)'),
            (1, 'GestorEmpresas', 'Empresa', 'existeSlug(slug)'),
            (1, 'GestorEmpresas', 'Plan', 'obtenerPlan(idPlan)'),
            (1, 'GestorEmpresas', 'Empresa', 'crear(empresa)'),
            (1, 'GestorEmpresas', 'Suscripcion', 'crear(empresa, plan, inicio, vencimiento)'),
            (1, 'GestorEmpresas', 'Sucursal', 'crearPrincipal(empresa)'),
            (1, 'GestorEmpresas', 'GestorEmpresas', 'generarContrasenaTemporal()'),
            (1, 'GestorEmpresas', 'Usuario', 'crearAdministrador(empresa, datos)'),
            (1, 'GestorEmpresas', 'CanalDeCorreo', 'enviarAcceso(correo, slug, contrasena)'),
            (1, 'GestorEmpresas', 'PantallaEmpresas', 'confirmar(empresa)'),
            (2, PA, 'PantallaEmpresas', 'editarEmpresa(id, datos)'),
            (2, 'PantallaEmpresas', 'GestorEmpresas', 'actualizarEmpresa(id, datos)'),
            (2, 'GestorEmpresas', 'Empresa', 'guardar(empresa)'),
            (3, PA, 'PantallaEmpresas', 'darDeBaja(id)'),
            (3, 'PantallaEmpresas', 'GestorEmpresas', 'darDeBajaEmpresa(id)'),
            (3, 'GestorEmpresas', 'Empresa', 'desactivar()'),
            (4, 'GestorEmpresas', 'PantallaEmpresas', 'datosInvalidos(campos)'),
            (4, 'GestorEmpresas', 'PantallaEmpresas', 'slugRepetido()'),
            (4, 'GestorEmpresas', 'GestorEmpresas', 'revertirTransaccion()')]),

    dict(cu='CU-02', n='Gestionar planes', a=['Administrador de la plataforma'],
         f=['PantallaPlanes'], c=['GestorPlanes', 'GestorAutenticacion'], e=['Plan', 'Suscripcion'],
         grupos=['flujo principal: crear o editar un plan', 'alternativo 3a: desactivar un plan',
                 'alternativo 5a: el límite nuevo queda por debajo de lo usado', 'alternativo 4a: datos inválidos'],
         m=[(1, PA, 'PantallaPlanes', 'abrirListaPlanes()'),
            (1, 'PantallaPlanes', 'GestorPlanes', 'listarPlanes()'),
            (1, 'GestorPlanes', 'GestorAutenticacion', 'autorizar("ADMIN_PLATAFORMA")'),
            (1, 'GestorPlanes', 'Plan', 'listar()'),
            (1, 'GestorPlanes', 'Suscripcion', 'contarEmpresasPorPlan()'),
            (1, PA, 'PantallaPlanes', 'guardarPlan(datos)'),
            (1, 'PantallaPlanes', 'GestorPlanes', 'guardarPlan(datos)'),
            (1, 'GestorPlanes', 'GestorPlanes', 'validarDatos(datos)'),
            (1, 'GestorPlanes', 'Plan', 'existeNombre(nombre)'),
            (1, 'GestorPlanes', 'Plan', 'guardar(plan)'),
            (1, 'GestorPlanes', 'PantallaPlanes', 'confirmar(plan)'),
            (2, PA, 'PantallaPlanes', 'desactivarPlan(id)'),
            (2, 'PantallaPlanes', 'GestorPlanes', 'desactivarPlan(id)'),
            (2, 'GestorPlanes', 'Plan', 'desactivar()'),
            (3, 'GestorPlanes', 'Suscripcion', 'empresasPorEncimaDelLimite(plan)'),
            (3, 'GestorPlanes', 'PantallaPlanes', 'avisarEmpresasPorEncima(lista)'),
            (4, 'GestorPlanes', 'PantallaPlanes', 'datosInvalidos(campos)')]),

    dict(cu='CU-03', n='Gestionar suscripciones', a=['Administrador de la plataforma', 'Sistema'],
         f=['PantallaSuscripcion', 'TareaProgramada'], c=['GestorSuscripciones', 'GestorAutenticacion'],
         e=['Empresa', 'Suscripcion', 'Plan', 'PagoSimulado', 'Sucursal', 'Empleado'],
         grupos=['flujo principal: asignar o cambiar el plan', 'alternativo 3a: renovar',
                 'alternativo 3b: suspender o reactivar', 'alternativo 5a: cambio a un plan menor',
                 'E1: vencimiento diario'],
         m=[(1, PA, 'PantallaSuscripcion', 'abrirFichaEmpresa(idEmpresa)'),
            (1, 'PantallaSuscripcion', 'GestorSuscripciones', 'obtenerSuscripciones(idEmpresa)'),
            (1, 'GestorSuscripciones', 'GestorAutenticacion', 'autorizar("ADMIN_PLATAFORMA")'),
            (1, 'GestorSuscripciones', 'Empresa', 'obtener(idEmpresa)'),
            (1, 'GestorSuscripciones', 'Suscripcion', 'historialDe(empresa)'),
            (1, PA, 'PantallaSuscripcion', 'asignarPlan(idPlan, inicio)'),
            (1, 'PantallaSuscripcion', 'GestorSuscripciones', 'asignarPlan(idEmpresa, idPlan, inicio)'),
            (1, 'GestorSuscripciones', 'Plan', 'obtenerPlan(idPlan)'),
            (1, 'GestorSuscripciones', 'GestorSuscripciones', 'calcularVencimiento(inicio, duracion)'),
            (1, 'GestorSuscripciones', 'PagoSimulado', 'registrar(empresa, plan, monto)'),
            (1, 'GestorSuscripciones', 'Suscripcion', 'cerrarVigente(empresa)'),
            (1, 'GestorSuscripciones', 'Suscripcion', 'crear(empresa, plan, inicio, vencimiento)'),
            (1, 'GestorSuscripciones', 'PantallaSuscripcion', 'mostrarEstado(suscripcion)'),
            (2, PA, 'PantallaSuscripcion', 'renovar()'),
            (2, 'PantallaSuscripcion', 'GestorSuscripciones', 'renovar(idEmpresa)'),
            (2, 'GestorSuscripciones', 'Suscripcion', 'extenderVencimiento()'),
            (3, PA, 'PantallaSuscripcion', 'suspenderOReactivar()'),
            (3, 'PantallaSuscripcion', 'GestorSuscripciones', 'cambiarEstado(idEmpresa, estado)'),
            (3, 'GestorSuscripciones', 'Suscripcion', 'cambiarEstado(estado)'),
            (4, 'GestorSuscripciones', 'Sucursal', 'contarActivas(empresa)'),
            (4, 'GestorSuscripciones', 'Empleado', 'contarActivos(empresa)'),
            (4, 'GestorSuscripciones', 'PantallaSuscripcion', 'avisarRecursosPorEncima(lista)'),
            (5, 'A:Sistema', 'TareaProgramada', 'ejecutarDiaria()'),
            (5, 'TareaProgramada', 'GestorSuscripciones', 'marcarVencidas(hoy)'),
            (5, 'GestorSuscripciones', 'Suscripcion', 'vencidasAl(hoy)'),
            (5, 'GestorSuscripciones', 'Suscripcion', 'marcarVencida()')]),

    dict(cu='CU-04', n='Consultar plan y consumo', a=['Administrador de la empresa'],
         f=['PantallaMiPlan'], c=['GestorConsumoPlan', 'GestorAutenticacion'],
         e=['Suscripcion', 'Plan', 'Sucursal', 'Empleado', 'ConsumoCupo'],
         grupos=['flujo principal: ver el plan, el uso de los límites y comparar planes',
                 'alternativo 2a: suscripción vencida o suspendida'],
         m=[(1, AE, 'PantallaMiPlan', 'abrirMiPlan()'),
            (1, 'PantallaMiPlan', 'GestorConsumoPlan', 'consultarPlan()'),
            (1, 'GestorConsumoPlan', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorConsumoPlan', 'Suscripcion', 'vigenteDe(empresa)'),
            (1, 'GestorConsumoPlan', 'Plan', 'obtenerLimitesYFunciones()'),
            (1, 'GestorConsumoPlan', 'Sucursal', 'contarActivas(empresa)'),
            (1, 'GestorConsumoPlan', 'Empleado', 'contarActivos(empresa)'),
            (1, 'GestorConsumoPlan', 'ConsumoCupo', 'consumoDelMes(empresa)'),
            (1, 'GestorConsumoPlan', 'PantallaMiPlan', 'mostrarPlanYConsumo(resumen)'),
            (1, AE, 'PantallaMiPlan', 'compararPlanes()'),
            (1, 'PantallaMiPlan', 'GestorConsumoPlan', 'listarPlanes()'),
            (1, 'GestorConsumoPlan', 'Plan', 'listarActivos()'),
            (2, 'GestorConsumoPlan', 'PantallaMiPlan', 'avisarModoSoloConsulta(estado)')]),

    dict(cu='CU-05', n='Verificar límites y funciones del plan', a=['Usuario'],
         f=['OperacionControlada'], c=['VerificadorPlan'], e=['Suscripcion', 'Plan', 'ConsumoCupo'],
         grupos=['flujo principal: la operación cumple el plan', 'alternativo 2a: sin suscripción vigente',
                 'alternativos 3a y 4a: función no incluida o límite alcanzado'],
         m=[(1, 'A:Usuario', 'OperacionControlada', 'solicitarOperacion(datos)'),
            (1, 'OperacionControlada', 'VerificadorPlan', 'verificar(empresa, funcion, recurso)'),
            (1, 'VerificadorPlan', 'Suscripcion', 'vigenteDe(empresa)'),
            (1, 'VerificadorPlan', 'Plan', 'incluyeFuncion(funcion)'),
            (1, 'VerificadorPlan', 'ConsumoCupo', 'usoActual(empresa, recurso)'),
            (1, 'VerificadorPlan', 'Plan', 'limiteDe(recurso)'),
            (1, 'VerificadorPlan', 'VerificadorPlan', 'compararConLimite(uso, limite)'),
            (1, 'VerificadorPlan', 'OperacionControlada', 'permitir()'),
            (2, 'VerificadorPlan', 'OperacionControlada', 'rechazarSinSuscripcion()'),
            (3, 'VerificadorPlan', 'OperacionControlada', 'rechazarPorPlan("plan_limit", limite, uso)')]),

    dict(cu='CU-06', n='Iniciar sesión en una empresa', a=['Usuario'],
         f=['PantallaInicioSesion', 'MenuPrincipal'], c=['GestorAutenticacion'],
         e=['Empresa', 'Suscripcion', 'Usuario', 'SesionToken'],
         grupos=['flujo principal: inicio de sesión con el slug', 'alternativo 1a: administrador de la plataforma, sin slug',
                 'alternativos 2a y 4a: empresa no encontrada o credenciales incorrectas',
                 'alternativo 3a: suscripción vencida, modo solo consulta', 'alternativo 6a: cerrar sesión'],
         m=[(1, 'A:Usuario', 'PantallaInicioSesion', 'ingresarCredenciales(slug, correo, contrasena)'),
            (1, 'PantallaInicioSesion', 'GestorAutenticacion', 'iniciarSesion(slug, credenciales)'),
            (1, 'GestorAutenticacion', 'Empresa', 'buscarPorSlug(slug)'),
            (1, 'GestorAutenticacion', 'Suscripcion', 'vigenteDe(empresa)'),
            (1, 'GestorAutenticacion', 'Usuario', 'buscarPorCorreo(empresa, correo)'),
            (1, 'GestorAutenticacion', 'GestorAutenticacion', 'verificarContrasena(hash)'),
            (1, 'GestorAutenticacion', 'GestorAutenticacion', 'emitirToken(usuario, empresa, rol)'),
            (1, 'GestorAutenticacion', 'SesionToken', 'registrarSesion(jti, expiraEn)'),
            (1, 'GestorAutenticacion', 'MenuPrincipal', 'mostrarMenuDelRol(rol, marca)'),
            (2, 'PantallaInicioSesion', 'GestorAutenticacion', 'iniciarSesionPlataforma(credenciales)'),
            (2, 'GestorAutenticacion', 'Usuario', 'buscarAdministradorPlataforma(correo)'),
            (3, 'GestorAutenticacion', 'PantallaInicioSesion', 'empresaNoEncontrada()'),
            (3, 'GestorAutenticacion', 'PantallaInicioSesion', 'credencialesInvalidas()'),
            (4, 'GestorAutenticacion', 'GestorAutenticacion', 'marcarSoloConsulta(token)'),
            (5, 'A:Usuario', 'MenuPrincipal', 'cerrarSesion()'),
            (5, 'MenuPrincipal', 'GestorAutenticacion', 'cerrarSesion(jti)'),
            (5, 'GestorAutenticacion', 'SesionToken', 'revocar(jti)')]),

    dict(cu='CU-07', n='Registrar cliente con cuenta única', a=['Cliente'],
         f=['FormularioRegistro'], c=['GestorRegistro', 'GestorAutenticacion'],
         e=['Usuario', 'Cliente', 'Empresa', 'ClienteEmpresa', 'SesionToken'],
         grupos=['flujo principal: cuenta nueva', 'alternativo 4a: datos inválidos',
                 'alternativo 4b: el correo ya tiene cuenta en otra empresa'],
         m=[(1, 'A:Cliente', 'FormularioRegistro', 'enviarDatos(nombres, apellidos, correo, contrasena)'),
            (1, 'FormularioRegistro', 'GestorRegistro', 'registrarCliente(slug, datos)'),
            (1, 'GestorRegistro', 'GestorRegistro', 'validarDatos(datos)'),
            (1, 'GestorRegistro', 'Usuario', 'existeCorreo(correo)'),
            (1, 'GestorRegistro', 'GestorRegistro', 'hashearContrasena(contrasena)'),
            (1, 'GestorRegistro', 'Usuario', 'crear(usuario)'),
            (1, 'GestorRegistro', 'Cliente', 'crear(cliente)'),
            (1, 'GestorRegistro', 'Empresa', 'buscarPorSlug(slug)'),
            (1, 'GestorRegistro', 'ClienteEmpresa', 'asociar(cliente, empresa)'),
            (1, 'GestorRegistro', 'GestorAutenticacion', 'iniciarSesion(usuario, empresa)'),
            (1, 'GestorAutenticacion', 'SesionToken', 'registrarSesion(jti, expiraEn)'),
            (1, 'GestorRegistro', 'FormularioRegistro', 'confirmarRegistro(token)'),
            (2, 'GestorRegistro', 'FormularioRegistro', 'datosInvalidos(campos)'),
            (3, 'GestorRegistro', 'FormularioRegistro', 'ofrecerIniciarSesion(correo)'),
            (3, 'A:Cliente', 'FormularioRegistro', 'iniciarSesionConSuCuenta(contrasena)'),
            (3, 'FormularioRegistro', 'GestorRegistro', 'asociarCuentaExistente(slug, credenciales)'),
            (3, 'GestorRegistro', 'GestorAutenticacion', 'validarCredenciales(credenciales)'),
            (3, 'GestorRegistro', 'ClienteEmpresa', 'asociar(cliente, empresa)')]),

    dict(cu='CU-08', n='Gestionar usuarios de la empresa', a=['Administrador de la empresa'],
         f=['PantallaUsuarios'], c=['GestorUsuarios', 'GestorAutenticacion', 'VerificadorPlan'],
         e=['Usuario', 'Rol', 'Sucursal'],
         grupos=['flujo principal: alta de usuario', 'alternativo 3a: editar o desactivar',
                 'alternativo 4a: límite alcanzado', 'alternativo 5a: rol no permitido'],
         m=[(1, AE, 'PantallaUsuarios', 'abrirListaUsuarios()'),
            (1, 'PantallaUsuarios', 'GestorUsuarios', 'listarUsuarios()'),
            (1, 'GestorUsuarios', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorUsuarios', 'Usuario', 'listarDeEmpresa(empresa)'),
            (1, AE, 'PantallaUsuarios', 'crearUsuario(datos)'),
            (1, 'PantallaUsuarios', 'GestorUsuarios', 'registrar(datos)'),
            (1, 'GestorUsuarios', 'VerificadorPlan', 'verificar(empresa, "usuarios")'),
            (1, 'GestorUsuarios', 'GestorUsuarios', 'validarDatos(datos)'),
            (1, 'GestorUsuarios', 'Rol', 'obtenerRol(rol)'),
            (1, 'GestorUsuarios', 'Sucursal', 'perteneceAEmpresa(idSucursal, empresa)'),
            (1, 'GestorUsuarios', 'Usuario', 'crear(usuario, empresa)'),
            (1, 'GestorUsuarios', 'PantallaUsuarios', 'confirmar()'),
            (2, AE, 'PantallaUsuarios', 'editarODesactivar(id, datos)'),
            (2, 'PantallaUsuarios', 'GestorUsuarios', 'actualizar(id, datos)'),
            (2, 'GestorUsuarios', 'Usuario', 'guardar(usuario)'),
            (3, 'GestorUsuarios', 'PantallaUsuarios', 'limiteAlcanzado(limite, uso)'),
            (4, 'GestorUsuarios', 'PantallaUsuarios', 'rolNoPermitido()')]),

    dict(cu='CU-09', n='Gestionar sucursales de la empresa', a=['Administrador de la empresa'],
         f=['PantallaSucursales'], c=['GestorOrganizacion', 'GestorAutenticacion', 'VerificadorPlan'],
         e=['Sucursal', 'Ciudad'],
         grupos=['flujo principal: alta de sucursal', 'alternativo 3a: editar', 'alternativo 3b: desactivar',
                 'alternativo 4a: límite alcanzado'],
         m=[(1, AE, 'PantallaSucursales', 'abrirListaSucursales()'),
            (1, 'PantallaSucursales', 'GestorOrganizacion', 'listarSucursales()'),
            (1, 'GestorOrganizacion', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorOrganizacion', 'Sucursal', 'listarDeEmpresa(empresa)'),
            (1, AE, 'PantallaSucursales', 'registrarSucursal(datos)'),
            (1, 'PantallaSucursales', 'GestorOrganizacion', 'crearSucursal(datos)'),
            (1, 'GestorOrganizacion', 'VerificadorPlan', 'verificar(empresa, "sucursales")'),
            (1, 'GestorOrganizacion', 'GestorOrganizacion', 'validarDatos(datos)'),
            (1, 'GestorOrganizacion', 'Ciudad', 'obtenerCiudad(id)'),
            (1, 'GestorOrganizacion', 'Sucursal', 'crear(sucursal, empresa)'),
            (1, 'GestorOrganizacion', 'PantallaSucursales', 'confirmar()'),
            (2, AE, 'PantallaSucursales', 'editarSucursal(id, datos)'),
            (2, 'PantallaSucursales', 'GestorOrganizacion', 'actualizarSucursal(id, datos)'),
            (2, 'GestorOrganizacion', 'Sucursal', 'guardar(sucursal)'),
            (3, AE, 'PantallaSucursales', 'desactivarSucursal(id)'),
            (3, 'PantallaSucursales', 'GestorOrganizacion', 'desactivarSucursal(id)'),
            (3, 'GestorOrganizacion', 'Sucursal', 'desactivar()'),
            (4, 'GestorOrganizacion', 'PantallaSucursales', 'limiteAlcanzado(limite, uso)')]),

    dict(cu='CU-10', n='Gestionar empleados de la empresa', a=['Administrador de la empresa'],
         f=['PantallaEmpleados'], c=['GestorEmpleados', 'GestorAutenticacion', 'VerificadorPlan'],
         e=['Empleado', 'Sucursal', 'Usuario', 'Rol'],
         grupos=['flujo principal: alta de empleado con su usuario', 'alternativo 3a: editar o desactivar',
                 'alternativo 4a: límite alcanzado'],
         m=[(1, AE, 'PantallaEmpleados', 'abrirListaEmpleados()'),
            (1, 'PantallaEmpleados', 'GestorEmpleados', 'listarEmpleados()'),
            (1, 'GestorEmpleados', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorEmpleados', 'Empleado', 'listarDeEmpresa(empresa)'),
            (1, AE, 'PantallaEmpleados', 'registrarEmpleado(datos)'),
            (1, 'PantallaEmpleados', 'GestorEmpleados', 'crearEmpleado(datos)'),
            (1, 'GestorEmpleados', 'VerificadorPlan', 'verificar(empresa, "empleados")'),
            (1, 'GestorEmpleados', 'Sucursal', 'perteneceAEmpresa(idSucursal, empresa)'),
            (1, 'GestorEmpleados', 'Rol', 'obtenerRol(cargo)'),
            (1, 'GestorEmpleados', 'Usuario', 'crear(usuario, empresa)'),
            (1, 'GestorEmpleados', 'Empleado', 'crear(empleado)'),
            (1, 'GestorEmpleados', 'PantallaEmpleados', 'confirmar()'),
            (2, AE, 'PantallaEmpleados', 'editarODesactivar(id, datos)'),
            (2, 'PantallaEmpleados', 'GestorEmpleados', 'actualizar(id, datos)'),
            (2, 'GestorEmpleados', 'Empleado', 'guardar(empleado)'),
            (2, 'GestorEmpleados', 'Usuario', 'desactivarSiCorresponde()'),
            (3, 'GestorEmpleados', 'PantallaEmpleados', 'limiteAlcanzado(limite, uso)')]),

    dict(cu='CU-11', n='Contratar un plan desde la web', a=['Empresa interesada'],
         f=['PaginaPlanes', 'FormularioContratacion', 'CanalDeCorreo'],
         c=['GestorContratacion', 'GestorEmpresas'],
         e=['Plan', 'Empresa', 'PagoSimulado', 'Suscripcion', 'Sucursal', 'Usuario'],
         grupos=['flujo principal: elegir el plan, pagar y dar de alta la empresa',
                 'alternativo 5a: slug ocupado', 'alternativo 6a: pago simulado rechazado'],
         m=[(1, 'A:Empresa interesada', 'PaginaPlanes', 'abrirPlanes()'),
            (1, 'PaginaPlanes', 'GestorContratacion', 'listarPlanesOfrecidos()'),
            (1, 'GestorContratacion', 'Plan', 'listarActivos()'),
            (1, 'A:Empresa interesada', 'PaginaPlanes', 'elegirPlan(idPlan)'),
            (1, 'PaginaPlanes', 'GestorContratacion', 'iniciarContratacion(idPlan)'),
            (1, 'GestorContratacion', 'FormularioContratacion', 'mostrarFormulario(plan)'),
            (1, 'A:Empresa interesada', 'FormularioContratacion', 'enviarDatos(empresa, slug, administrador)'),
            (1, 'FormularioContratacion', 'GestorContratacion', 'contratar(datos, idPlan)'),
            (1, 'GestorContratacion', 'GestorContratacion', 'validarDatos(datos)'),
            (1, 'GestorContratacion', 'Empresa', 'existeSlug(slug)'),
            (1, 'GestorContratacion', 'PagoSimulado', 'registrar(plan, monto)'),
            (1, 'GestorContratacion', 'GestorEmpresas', 'crearEmpresaConSuscripcion(datos, plan)'),
            (1, 'GestorEmpresas', 'Empresa', 'crear(empresa)'),
            (1, 'GestorEmpresas', 'Suscripcion', 'crear(empresa, plan, inicio, vencimiento)'),
            (1, 'GestorEmpresas', 'Sucursal', 'crearPrincipal(empresa)'),
            (1, 'GestorEmpresas', 'Usuario', 'crearAdministrador(empresa, datos)'),
            (1, 'GestorContratacion', 'CanalDeCorreo', 'enviarBienvenida(correo, slug)'),
            (1, 'GestorContratacion', 'FormularioContratacion', 'mostrarComprobante(pago, slug)'),
            (2, 'GestorContratacion', 'Empresa', 'sugerirSlugsLibres(slug)'),
            (2, 'GestorContratacion', 'FormularioContratacion', 'slugOcupado(sugerencias)'),
            (3, 'GestorContratacion', 'FormularioContratacion', 'pagoRechazado()')]),

    dict(cu='CU-12', n='Personalizar la tienda de la empresa', a=['Administrador de la empresa'],
         f=['PantallaMiTienda', 'TiendaEnLinea'], c=['GestorMarca', 'GestorAutenticacion', 'VerificadorPlan'],
         e=['Empresa'],
         grupos=['flujo principal: subir el logo y elegir los colores',
                 'alternativo 1a: el plan no incluye la función', 'alternativo 4a: imagen inválida'],
         m=[(1, AE, 'PantallaMiTienda', 'abrirMiTienda()'),
            (1, 'PantallaMiTienda', 'GestorMarca', 'obtenerMarca()'),
            (1, 'GestorMarca', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorMarca', 'VerificadorPlan', 'verificar(empresa, "marca_propia")'),
            (1, 'GestorMarca', 'Empresa', 'obtenerMarca()'),
            (1, 'GestorMarca', 'PantallaMiTienda', 'mostrarVistaPrevia(marca)'),
            (1, AE, 'PantallaMiTienda', 'guardarMarca(logo, colorPrincipal, colorSecundario)'),
            (1, 'PantallaMiTienda', 'GestorMarca', 'guardarMarca(logo, colores)'),
            (1, 'GestorMarca', 'GestorMarca', 'validarLogo(logo)'),
            (1, 'GestorMarca', 'Empresa', 'guardarMarca(logo, colores)'),
            (1, 'GestorMarca', 'TiendaEnLinea', 'aplicarMarca(marca)'),
            (2, 'GestorMarca', 'PantallaMiTienda', 'funcionNoIncluida()'),
            (3, 'GestorMarca', 'PantallaMiTienda', 'imagenInvalida()')]),
]

# Descripción de cada clase (va en las Notes del elemento en EA).
DESCRIPCION = {
    'GestorEmpresas': 'Coordina CU-01 y el alta de CU-11: crea empresa, suscripción, sucursal principal y administrador en una transacción.',
    'GestorPlanes': 'Coordina CU-02: planes con sus límites y funciones.',
    'GestorSuscripciones': 'Coordina CU-03: asigna, renueva, suspende y vence suscripciones.',
    'GestorConsumoPlan': 'Coordina CU-04: plan vigente, uso de los límites y consumo de los cupos.',
    'VerificadorPlan': 'CU-05: verifica función, límite y cupo del plan antes de una operación controlada; responde 403 plan_limit.',
    'GestorAutenticacion': 'CU-06 y la autorización del resto: login con slug, token con empresa y rol, cierre de sesión.',
    'GestorRegistro': 'Coordina CU-07: cuenta única del cliente y su asociación con la empresa.',
    'GestorUsuarios': 'Coordina CU-08: usuarios de la empresa, con su rol y su sucursal.',
    'GestorOrganizacion': 'Coordina CU-09: sucursales de la empresa dentro del límite del plan.',
    'GestorEmpleados': 'Coordina CU-10: crea el empleado y su usuario en una transacción.',
    'GestorContratacion': 'Coordina CU-11: elección del plan, pago simulado y alta de la empresa.',
    'GestorMarca': 'Coordina CU-12: logo y colores de la tienda de la empresa.',
    'Empresa': 'Tenant. Tiene slug único (RN-14), estado y marca (logo y colores).',
    'Plan': 'Precio simulado, límites max_* (vacío = ilimitado) y funciones habilitadas.',
    'Suscripcion': 'Plan de una empresa con inicio, vencimiento y estado. Una sola vigente por empresa (RN-02).',
    'PagoSimulado': 'Registro del cobro simulado de una suscripción.',
    'ConsumoCupo': 'Uso del mes de cada límite o cupo (reportes y fotos con IA) por empresa.',
    'ClienteEmpresa': 'Asocia la cuenta única de un cliente con cada empresa donde compra (RN-13).',
    'SesionToken': 'Sesión emitida: el JWT lleva usuario, empresa y rol.',
    'Usuario': 'Identidad y credencial de quien accede, dentro de una empresa.',
    'Cliente': 'Datos comerciales de la persona con rol Cliente.',
    'Rol': 'Conjunto de permisos de un tipo de usuario.',
    'Sucursal': 'Tienda física; pertenece a una sola empresa (RN-01).',
    'Ciudad': 'Agrupa las sucursales de una misma plaza.',
    'Empleado': 'Persona que trabaja en una sucursal de la empresa, con su cargo.',
    'OperacionControlada': 'Frontera técnica: cualquier endpoint que crea un recurso limitado o usa una función de pago.',
    'TareaProgramada': 'Frontera sin persona: el proceso diario del backend.',
    'CanalDeCorreo': 'Frontera de salida: el correo enviado por Brevo.',
    'TiendaEnLinea': 'La tienda pública de la empresa, que muestra su marca.',
}


def validar():
    ids = {c[0] for c in CASOS}
    for r in ROBUSTEZ:
        assert r['cu'] in ids, r['cu']
        tipos = {**{f'A:{x}': 'A' for x in r['a']}, **{x: 'F' for x in r['f']},
                 **{x: 'C' for x in r['c']}, **{x: 'E' for x in r['e']}}
        grupos = sorted({g for g, *_ in r['m']})
        assert grupos == list(range(1, len(r['grupos']) + 1)), (r['cu'], grupos)
        for g, de, a, op in r['m']:
            assert de in tipos and a in tipos, (r['cu'], de, a)
            par = {tipos[de], tipos[a]}
            # la regla de la ing: nunca entidad con entidad; tampoco frontera con frontera
            assert par in ({'A', 'F'}, {'F', 'C'}, {'C', 'E'}, {'C'}), (r['cu'], de, a, op)
        usados = {p for _, de, a, _ in r['m'] for p in (de, a)}
        assert usados == set(tipos), (r['cu'], set(tipos) - usados)


def escribir_md():
    out = ['# 3.2 Diagramas de robustez: los mensajes', '',
           '*Lo genera `scripts/p2_datos.py`; no se edita a mano.*', '',
           'El generador (`scripts/ea-p2.ps1`) dibuja cada diagrama **sin mensajes**: solo los enlaces entre',
           'los participantes. Los mensajes se cargan a mano en EA siguiendo estas tablas, porque así quedan',
           'más prolijos. El número es `grupo.orden`.', '',
           '**Cómo se carga un mensaje en EA.** Clic derecho sobre el enlace → *Add Message from A to B* (o',
           'el *Message* del cuadro de herramientas *Communication*). En el nombre va **solo la operación**:',
           'el número lo pone EA. Para empezar un grupo nuevo (el 2, el 3…), en las propiedades del primer',
           'mensaje del grupo se marca *Start New Group*. Los mensajes de un participante a sí mismo',
           '(`validarDatos`, etc.) se cargan como mensaje sobre el propio elemento.', '',
           '**La regla de la ing:** en la robustez **nunca se comunican dos entidades**; siempre habla la',
           'clase control. El actor habla solo con fronteras.', '']
    for r in ROBUSTEZ:
        out += [f'## {r["cu"]} — {r["n"]}', '']
        out += [f'- **Grupo {i}:** {g}' for i, g in enumerate(r['grupos'], 1)]
        out += ['', '| N.º | De | A | Mensaje |', '|---|---|---|---|']
        orden = {}
        for g, de, a, op in r['m']:
            orden[g] = orden.get(g, 0) + 1
            nom = lambda x: x[2:] + ' (actor)' if x.startswith('A:') else x
            out.append(f'| {g}.{orden[g]} | {nom(de)} | {nom(a)} | `{op}` |')
        out.append('')
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text('\n'.join(out), encoding='utf-8')


if __name__ == '__main__':
    validar()
    escribir_md()
    salida = {
        'actores': ACTORES,
        'casos': [dict(id=i, n=n, actores=a, incluye=inc, notas=nt) for i, n, a, inc, nt in CASOS],
        'robustez': [dict(cu=r['cu'], n=r['n'], a=r['a'], f=r['f'], c=r['c'], e=r['e'],
                          pares=sorted({tuple(sorted((de, a))) for _, de, a, _ in r['m'] if de != a}))
                     for r in ROBUSTEZ],
        'descripcion': DESCRIPCION,
    }
    destino = AQUI / 'ea-p2.datos.json'
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding='utf-8')
    print('ok', destino, len(ROBUSTEZ), 'robusteces,', len(CASOS), 'casos de uso;', MD)
