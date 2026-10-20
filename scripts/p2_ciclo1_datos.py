# Datos del Ciclo 1 del 2do parcial para los generadores de Enterprise Architect:
#   - ea-p2-casos-de-uso-ciclo1.ps1  (2.5, diagramas de casos de uso)
#   - ea-p2-robustez-ciclo1.ps1      (3.2, diagramas de robustez ICONIX)
#
# Las dos salidas son JSON. Las fichas (2.6 del Word) son la fuente: cada
# controlador de la robustez es un verbo de un paso de la ficha, y la nota que
# acompaña cada diagrama es la ficha resumida.
#
# Uso:  python -X utf8 scripts/p2_ciclo1_datos.py
import json
from pathlib import Path

AQUI = Path(__file__).parent

# ------------------------------------------------------------------ 2.5 ---
ACTORES = {
    'Usuario': {'abstracto': True,
                'notas': 'Actor abstracto: cualquiera que inicia sesión en una empresa (CU-48).'},
    'Administrador de la plataforma': {'padre': 'Usuario',
                                       'notas': 'Opera la plataforma SaaS, fuera de los tenants. Entra sin slug.'},
    'Administrador de la empresa': {'padre': 'Usuario',
                                    'notas': 'Administra su empresa (tenant) y todas sus sucursales.'},
    'Encargado de sucursal': {'padre': 'Usuario', 'notas': 'Opera su sucursal dentro de una empresa.'},
    'Cajero': {'padre': 'Usuario', 'notas': 'Vende en caja dentro de su sucursal.'},
    'Proveedor': {'padre': 'Usuario', 'notas': 'Consulta y actualiza sus productos.'},
    'Cliente': {'padre': 'Usuario', 'notas': 'Una sola cuenta en la plataforma, que usa en varias empresas (RN-13).'},
    'Empresa interesada': {'notas': 'Visitante de la página pública que contrata un plan (CU-53).'},
}

CASOS = [
    # (id, nombre, actores, incluye, notas)
    ('CU-43', 'Gestionar empresas', ['Administrador de la plataforma'], [],
     'Registrar, editar y dar de baja empresas, con su administrador. RF-01, RF-02, RF-03.'),
    ('CU-44', 'Gestionar planes', ['Administrador de la plataforma'], [],
     'Precio simulado, límites y funciones de cada plan. RF-04.'),
    ('CU-45', 'Gestionar suscripciones', ['Administrador de la plataforma'], [],
     'Asignar, cambiar, renovar, suspender y reactivar, con el cobro simulado. RF-05, RF-07, RF-08.'),
    ('CU-46', 'Consultar plan y consumo', ['Administrador de la empresa'], [],
     'Plan, estado de la suscripción, uso de límites y cupos. RF-06, RF-50.'),
    ('CU-47', 'Verificar límites y funciones del plan', [], [],
     'Lo incluyen los casos de uso que crean recursos limitados o usan funciones de pago. RF-09.'),
    ('CU-48', 'Iniciar sesión en una empresa', ['Usuario'], [],
     'Evoluciona CU-02. Login con el slug de la empresa; token con empresa y rol. RN-12.'),
    ('CU-49', 'Registrar cliente con cuenta única', ['Cliente'], [],
     'Evoluciona CU-01. Una cuenta por persona en toda la plataforma. RF-51, RN-13.'),
    ('CU-50', 'Gestionar usuarios de la empresa', ['Administrador de la empresa'], ['CU-47'],
     'Evoluciona CU-03. Solo los usuarios de su empresa, dentro del límite. RF-03, RF-09.'),
    ('CU-51', 'Gestionar sucursales de la empresa', ['Administrador de la empresa'], ['CU-47'],
     'Evoluciona CU-05. Límite de sucursales activas. RF-03, RF-09.'),
    ('CU-52', 'Gestionar empleados de la empresa', ['Administrador de la empresa'], ['CU-47'],
     'Evoluciona CU-06. Límite de empleados activos. RF-09.'),
    ('CU-53', 'Contratar un plan desde la web', ['Empresa interesada'], [],
     'Aporte propio. Alta de la empresa con el cobro simulado. RF-47.'),
    ('CU-54', 'Personalizar la tienda de la empresa', ['Administrador de la empresa'], ['CU-47'],
     'Aporte propio. Logo y colores en la tienda en línea. RF-46.'),
]

# ------------------------------------------------------------------ 3.2 ---
# Por caso de uso:
#   f  = fronteras, c = controladores del flujo normal, ca = controladores de
#   los flujos alternativos (se pintan de rojo, como en el ejemplo del PDF),
#   e  = entidades, a = actores.
#   l  = enlaces 'X|Y' o 'X|Y|etiqueta'. Un actor se escribe 'A:Nombre'.
# Reglas que se verifican al generar: Actor-Frontera, Frontera-Control,
# Control-Entidad y Control-Control. Ninguna otra.
ROBUSTEZ = [
    dict(cu='CU-43', n='Gestionar empresas', a=['Administrador de la plataforma'],
         f=['PantallaEmpresas', 'CanalDeCorreo'],
         c=['Listar empresas', 'Validar datos de la empresa', 'Verificar slug libre',
            'Crear empresa con su suscripción', 'Generar contraseña temporal', 'Enviar acceso por correo'],
         ca=['Mostrar error en el formulario', 'Editar empresa', 'Dar de baja la empresa', 'Revertir el alta'],
         e=['Empresa', 'Plan', 'Suscripcion', 'Sucursal', 'Usuario'],
         l=['A:Administrador de la plataforma|PantallaEmpresas|abre la lista y registra',
            'PantallaEmpresas|Listar empresas', 'Listar empresas|Empresa',
            'PantallaEmpresas|Validar datos de la empresa',
            'Validar datos de la empresa|Verificar slug libre', 'Verificar slug libre|Empresa',
            'Verificar slug libre|Crear empresa con su suscripción',
            'Crear empresa con su suscripción|Empresa', 'Crear empresa con su suscripción|Plan',
            'Crear empresa con su suscripción|Suscripcion', 'Crear empresa con su suscripción|Sucursal',
            'Crear empresa con su suscripción|Generar contraseña temporal',
            'Generar contraseña temporal|Usuario', 'Generar contraseña temporal|Enviar acceso por correo',
            'Enviar acceso por correo|CanalDeCorreo',
            'Validar datos de la empresa|Mostrar error en el formulario|datos inválidos',
            'Verificar slug libre|Mostrar error en el formulario|slug repetido',
            'Mostrar error en el formulario|PantallaEmpresas',
            'PantallaEmpresas|Editar empresa', 'Editar empresa|Empresa',
            'PantallaEmpresas|Dar de baja la empresa', 'Dar de baja la empresa|Empresa',
            'Crear empresa con su suscripción|Revertir el alta|falla la creación',
            'Revertir el alta|Mostrar error en el formulario']),

    dict(cu='CU-44', n='Gestionar planes', a=['Administrador de la plataforma'],
         f=['PantallaPlanes'],
         c=['Listar planes', 'Validar datos del plan', 'Guardar plan'],
         ca=['Mostrar error en el formulario', 'Desactivar plan', 'Avisar empresas por encima del límite'],
         e=['Plan', 'Suscripcion'],
         l=['A:Administrador de la plataforma|PantallaPlanes|crea o edita un plan',
            'PantallaPlanes|Listar planes', 'Listar planes|Plan', 'Listar planes|Suscripcion',
            'PantallaPlanes|Validar datos del plan', 'Validar datos del plan|Guardar plan',
            'Guardar plan|Plan',
            'Validar datos del plan|Mostrar error en el formulario|datos inválidos',
            'Mostrar error en el formulario|PantallaPlanes',
            'PantallaPlanes|Desactivar plan', 'Desactivar plan|Plan',
            'Guardar plan|Avisar empresas por encima del límite|límite menor que lo usado',
            'Avisar empresas por encima del límite|Suscripcion',
            'Avisar empresas por encima del límite|PantallaPlanes']),

    dict(cu='CU-45', n='Gestionar suscripciones', a=['Administrador de la plataforma', 'Sistema'],
         f=['PantallaSuscripcion', 'TareaProgramada'],
         c=['Mostrar suscripción e historial', 'Calcular vencimiento', 'Registrar pago simulado',
            'Reemplazar suscripción vigente'],
         ca=['Renovar suscripción', 'Suspender o reactivar suscripción',
             'Avisar recursos por encima del límite', 'Marcar suscripciones vencidas'],
         e=['Empresa', 'Suscripcion', 'Plan', 'PagoSimulado'],
         l=['A:Administrador de la plataforma|PantallaSuscripcion|asigna o cambia el plan',
            'PantallaSuscripcion|Mostrar suscripción e historial',
            'Mostrar suscripción e historial|Empresa', 'Mostrar suscripción e historial|Suscripcion',
            'PantallaSuscripcion|Calcular vencimiento', 'Calcular vencimiento|Plan',
            'Calcular vencimiento|Registrar pago simulado', 'Registrar pago simulado|PagoSimulado',
            'Registrar pago simulado|Reemplazar suscripción vigente',
            'Reemplazar suscripción vigente|Suscripcion',
            'PantallaSuscripcion|Renovar suscripción', 'Renovar suscripción|Suscripcion',
            'PantallaSuscripcion|Suspender o reactivar suscripción',
            'Suspender o reactivar suscripción|Suscripcion',
            'Reemplazar suscripción vigente|Avisar recursos por encima del límite|plan menor',
            'Avisar recursos por encima del límite|PantallaSuscripcion',
            'A:Sistema|TareaProgramada|cada día',
            'TareaProgramada|Marcar suscripciones vencidas',
            'Marcar suscripciones vencidas|Suscripcion']),

    dict(cu='CU-46', n='Consultar plan y consumo', a=['Administrador de la empresa'],
         f=['PantallaMiPlan'],
         c=['Obtener suscripción vigente', 'Calcular uso de los límites', 'Calcular consumo de cupos',
            'Listar planes para comparar'],
         ca=['Avisar modo solo consulta'],
         e=['Suscripcion', 'Plan', 'Sucursal', 'Empleado', 'ConsumoCupo'],
         l=['A:Administrador de la empresa|PantallaMiPlan|abre «Mi plan»',
            'PantallaMiPlan|Obtener suscripción vigente',
            'Obtener suscripción vigente|Suscripcion', 'Obtener suscripción vigente|Plan',
            'Obtener suscripción vigente|Calcular uso de los límites',
            'Calcular uso de los límites|Sucursal', 'Calcular uso de los límites|Empleado',
            'Calcular uso de los límites|Calcular consumo de cupos',
            'Calcular consumo de cupos|ConsumoCupo', 'Calcular consumo de cupos|PantallaMiPlan',
            'PantallaMiPlan|Listar planes para comparar', 'Listar planes para comparar|Plan',
            'Obtener suscripción vigente|Avisar modo solo consulta|vencida o suspendida',
            'Avisar modo solo consulta|PantallaMiPlan']),

    dict(cu='CU-47', n='Verificar límites y funciones del plan', a=['Usuario'],
         f=['OperacionControlada'],
         c=['Obtener suscripción vigente', 'Verificar función del plan', 'Contar uso del recurso',
            'Comparar con el límite', 'Dejar continuar la operación'],
         ca=['Rechazar escritura sin suscripción', 'Rechazar por el plan'],
         e=['Suscripcion', 'Plan', 'ConsumoCupo'],
         l=['A:Usuario|OperacionControlada|crea o usa algo que el plan controla',
            'OperacionControlada|Obtener suscripción vigente',
            'Obtener suscripción vigente|Suscripcion',
            'Obtener suscripción vigente|Verificar función del plan',
            'Verificar función del plan|Plan', 'Verificar función del plan|Contar uso del recurso',
            'Contar uso del recurso|ConsumoCupo', 'Contar uso del recurso|Comparar con el límite',
            'Comparar con el límite|Plan', 'Comparar con el límite|Dejar continuar la operación',
            'Dejar continuar la operación|OperacionControlada',
            'Obtener suscripción vigente|Rechazar escritura sin suscripción|sin suscripción vigente',
            'Rechazar escritura sin suscripción|OperacionControlada',
            'Verificar función del plan|Rechazar por el plan|función no incluida',
            'Comparar con el límite|Rechazar por el plan|límite alcanzado',
            'Rechazar por el plan|OperacionControlada']),

    dict(cu='CU-48', n='Iniciar sesión en una empresa', a=['Usuario'],
         f=['PantallaInicioSesion', 'MenuPrincipal'],
         c=['Buscar empresa por slug', 'Verificar suscripción', 'Validar credenciales',
            'Emitir token con empresa y rol', 'Mostrar menú del rol'],
         ca=['Validar administrador de la plataforma', 'Mostrar error de acceso',
             'Activar modo solo consulta', 'Cerrar sesión'],
         e=['Empresa', 'Suscripcion', 'Usuario', 'SesionToken'],
         l=['A:Usuario|PantallaInicioSesion|ingresa slug, correo y contraseña',
            'PantallaInicioSesion|Buscar empresa por slug', 'Buscar empresa por slug|Empresa',
            'Buscar empresa por slug|Verificar suscripción', 'Verificar suscripción|Suscripcion',
            'Verificar suscripción|Validar credenciales', 'Validar credenciales|Usuario',
            'Validar credenciales|Emitir token con empresa y rol',
            'Emitir token con empresa y rol|SesionToken',
            'Emitir token con empresa y rol|Mostrar menú del rol', 'Mostrar menú del rol|MenuPrincipal',
            'PantallaInicioSesion|Validar administrador de la plataforma|sin slug',
            'Validar administrador de la plataforma|Usuario',
            'Validar administrador de la plataforma|Emitir token con empresa y rol',
            'Buscar empresa por slug|Mostrar error de acceso|empresa no existe',
            'Validar credenciales|Mostrar error de acceso|credenciales incorrectas',
            'Mostrar error de acceso|PantallaInicioSesion',
            'Verificar suscripción|Activar modo solo consulta|vencida o suspendida',
            'Activar modo solo consulta|Validar credenciales',
            'A:Usuario|MenuPrincipal', 'MenuPrincipal|Cerrar sesión|cierra sesión',
            'Cerrar sesión|SesionToken']),

    dict(cu='CU-49', n='Registrar cliente con cuenta única', a=['Cliente'],
         f=['FormularioRegistro'],
         c=['Validar datos del cliente', 'Buscar cuenta por correo', 'Crear cuenta de cliente',
            'Asociar cliente a la empresa', 'Iniciar sesión del cliente'],
         ca=['Mostrar error en el registro', 'Ofrecer iniciar sesión con su cuenta'],
         e=['Usuario', 'Cliente', 'ClienteEmpresa', 'Empresa', 'SesionToken'],
         l=['A:Cliente|FormularioRegistro|crea su cuenta',
            'FormularioRegistro|Validar datos del cliente',
            'Validar datos del cliente|Buscar cuenta por correo', 'Buscar cuenta por correo|Usuario',
            'Buscar cuenta por correo|Crear cuenta de cliente', 'Crear cuenta de cliente|Usuario',
            'Crear cuenta de cliente|Cliente', 'Crear cuenta de cliente|Asociar cliente a la empresa',
            'Asociar cliente a la empresa|ClienteEmpresa', 'Asociar cliente a la empresa|Empresa',
            'Asociar cliente a la empresa|Iniciar sesión del cliente',
            'Iniciar sesión del cliente|SesionToken', 'Iniciar sesión del cliente|FormularioRegistro',
            'Validar datos del cliente|Mostrar error en el registro|datos inválidos',
            'Mostrar error en el registro|FormularioRegistro',
            'Buscar cuenta por correo|Ofrecer iniciar sesión con su cuenta|el correo ya tiene cuenta',
            'Ofrecer iniciar sesión con su cuenta|FormularioRegistro',
            'Ofrecer iniciar sesión con su cuenta|Asociar cliente a la empresa']),

    dict(cu='CU-50', n='Gestionar usuarios de la empresa', a=['Administrador de la empresa'],
         f=['PantallaUsuarios'],
         c=['Listar usuarios de la empresa', 'Verificar límite del plan', 'Validar datos del usuario',
            'Guardar usuario en la empresa'],
         ca=['Rechazar por límite', 'Mostrar error en el formulario', 'Editar o desactivar usuario'],
         e=['Usuario', 'Rol', 'Sucursal', 'Plan'],
         l=['A:Administrador de la empresa|PantallaUsuarios|crea un usuario',
            'PantallaUsuarios|Listar usuarios de la empresa', 'Listar usuarios de la empresa|Usuario',
            'PantallaUsuarios|Verificar límite del plan', 'Verificar límite del plan|Plan',
            'Verificar límite del plan|Validar datos del usuario',
            'Validar datos del usuario|Rol', 'Validar datos del usuario|Sucursal',
            'Validar datos del usuario|Guardar usuario en la empresa',
            'Guardar usuario en la empresa|Usuario',
            'Verificar límite del plan|Rechazar por límite|límite alcanzado',
            'Rechazar por límite|PantallaUsuarios',
            'Validar datos del usuario|Mostrar error en el formulario|rol o sucursal inválidos',
            'Mostrar error en el formulario|PantallaUsuarios',
            'PantallaUsuarios|Editar o desactivar usuario', 'Editar o desactivar usuario|Usuario']),

    dict(cu='CU-51', n='Gestionar sucursales de la empresa', a=['Administrador de la empresa'],
         f=['PantallaSucursales'],
         c=['Listar sucursales con su uso', 'Verificar límite del plan', 'Validar datos de la sucursal',
            'Guardar sucursal en la empresa'],
         ca=['Rechazar por límite', 'Mostrar error en el formulario', 'Editar sucursal',
             'Desactivar sucursal'],
         e=['Sucursal', 'Ciudad', 'Plan'],
         l=['A:Administrador de la empresa|PantallaSucursales|registra una sucursal',
            'PantallaSucursales|Listar sucursales con su uso', 'Listar sucursales con su uso|Sucursal',
            'PantallaSucursales|Verificar límite del plan', 'Verificar límite del plan|Plan',
            'Verificar límite del plan|Validar datos de la sucursal',
            'Validar datos de la sucursal|Ciudad',
            'Validar datos de la sucursal|Guardar sucursal en la empresa',
            'Guardar sucursal en la empresa|Sucursal',
            'Verificar límite del plan|Rechazar por límite|límite alcanzado',
            'Rechazar por límite|PantallaSucursales',
            'Validar datos de la sucursal|Mostrar error en el formulario|datos inválidos',
            'Mostrar error en el formulario|PantallaSucursales',
            'PantallaSucursales|Editar sucursal', 'Editar sucursal|Sucursal',
            'PantallaSucursales|Desactivar sucursal', 'Desactivar sucursal|Sucursal']),

    dict(cu='CU-52', n='Gestionar empleados de la empresa', a=['Administrador de la empresa'],
         f=['PantallaEmpleados'],
         c=['Listar empleados con su uso', 'Verificar límite del plan', 'Validar sucursal de la empresa',
            'Guardar empleado con su usuario'],
         ca=['Rechazar por límite', 'Editar o desactivar empleado'],
         e=['Empleado', 'Sucursal', 'Usuario', 'Plan'],
         l=['A:Administrador de la empresa|PantallaEmpleados|registra un empleado',
            'PantallaEmpleados|Listar empleados con su uso', 'Listar empleados con su uso|Empleado',
            'PantallaEmpleados|Verificar límite del plan', 'Verificar límite del plan|Plan',
            'Verificar límite del plan|Validar sucursal de la empresa',
            'Validar sucursal de la empresa|Sucursal',
            'Validar sucursal de la empresa|Guardar empleado con su usuario',
            'Guardar empleado con su usuario|Empleado', 'Guardar empleado con su usuario|Usuario',
            'Verificar límite del plan|Rechazar por límite|límite alcanzado',
            'Rechazar por límite|PantallaEmpleados',
            'PantallaEmpleados|Editar o desactivar empleado', 'Editar o desactivar empleado|Empleado']),

    dict(cu='CU-53', n='Contratar un plan desde la web', a=['Empresa interesada'],
         f=['PaginaPlanes', 'FormularioContratacion', 'CanalDeCorreo'],
         c=['Listar planes ofrecidos', 'Validar datos de la contratación', 'Verificar slug libre',
            'Simular pago', 'Crear empresa con su suscripción', 'Enviar acceso por correo'],
         ca=['Sugerir slugs libres', 'Cancelar la contratación'],
         e=['Plan', 'Empresa', 'PagoSimulado', 'Suscripcion', 'Sucursal', 'Usuario'],
         l=['A:Empresa interesada|PaginaPlanes|elige un plan',
            'PaginaPlanes|Listar planes ofrecidos', 'Listar planes ofrecidos|Plan',
            'Listar planes ofrecidos|FormularioContratacion',
            'A:Empresa interesada|FormularioContratacion|ingresa sus datos y el slug',
            'FormularioContratacion|Validar datos de la contratación',
            'Validar datos de la contratación|Verificar slug libre', 'Verificar slug libre|Empresa',
            'Verificar slug libre|Simular pago', 'Simular pago|PagoSimulado',
            'Simular pago|Crear empresa con su suscripción',
            'Crear empresa con su suscripción|Empresa', 'Crear empresa con su suscripción|Suscripcion',
            'Crear empresa con su suscripción|Sucursal', 'Crear empresa con su suscripción|Usuario',
            'Crear empresa con su suscripción|Enviar acceso por correo',
            'Enviar acceso por correo|CanalDeCorreo',
            'Verificar slug libre|Sugerir slugs libres|slug ocupado',
            'Sugerir slugs libres|FormularioContratacion',
            'Simular pago|Cancelar la contratación|pago rechazado',
            'Cancelar la contratación|FormularioContratacion']),

    dict(cu='CU-54', n='Personalizar la tienda de la empresa', a=['Administrador de la empresa'],
         f=['PantallaMiTienda', 'TiendaEnLinea'],
         c=['Verificar función del plan', 'Mostrar marca actual', 'Validar logo',
            'Guardar marca de la empresa', 'Aplicar marca en la tienda'],
         ca=['Mostrar función no incluida', 'Rechazar imagen'],
         e=['Empresa', 'Plan'],
         l=['A:Administrador de la empresa|PantallaMiTienda|sube logo y elige colores',
            'PantallaMiTienda|Verificar función del plan', 'Verificar función del plan|Plan',
            'Verificar función del plan|Mostrar marca actual', 'Mostrar marca actual|Empresa',
            'Mostrar marca actual|PantallaMiTienda',
            'PantallaMiTienda|Validar logo', 'Validar logo|Guardar marca de la empresa',
            'Guardar marca de la empresa|Empresa',
            'Guardar marca de la empresa|Aplicar marca en la tienda',
            'Aplicar marca en la tienda|TiendaEnLinea',
            'Verificar función del plan|Mostrar función no incluida|el plan no la incluye',
            'Mostrar función no incluida|PantallaMiTienda',
            'Validar logo|Rechazar imagen|imagen inválida', 'Rechazar imagen|PantallaMiTienda']),
]

# Descripción de cada elemento (va en las Notes del elemento en EA).
DESCRIPCION = {
    'Empresa': 'Tenant. Tiene slug único (RN-14), estado y marca (logo y colores).',
    'Plan': 'Precio simulado, límites max_* (vacío = ilimitado) y funciones habilitadas.',
    'Suscripcion': 'Plan de una empresa con inicio, vencimiento y estado. Una sola vigente por empresa (RN-02).',
    'PagoSimulado': 'Registro del cobro simulado de una suscripción.',
    'ConsumoCupo': 'Uso del mes de cada cupo (reportes y fotos con IA) por empresa.',
    'ClienteEmpresa': 'Asocia la cuenta única de un cliente con cada empresa donde compra (RN-13).',
    'SesionToken': 'Sesión emitida: el JWT lleva usuario, empresa y rol.',
    'OperacionControlada': 'Frontera técnica: cualquier endpoint que crea un recurso limitado o usa una función de pago.',
    'TareaProgramada': 'Frontera sin persona: el proceso diario del backend.',
    'CanalDeCorreo': 'Frontera de salida: el correo enviado por Brevo.',
    'TiendaEnLinea': 'La tienda pública de la empresa, que muestra su marca.',
}


def validar():
    for r in ROBUSTEZ:
        tipos = {**{f'A:{x}': 'A' for x in r['a']}, **{x: 'F' for x in r['f']},
                 **{x: 'C' for x in r['c'] + r['ca']}, **{x: 'E' for x in r['e']}}
        assert len(r['c'] + r['ca']) == len(set(r['c'] + r['ca'])), r['cu']
        for enl in r['l']:
            x, y = enl.split('|')[:2]
            assert x in tipos and y in tipos, (r['cu'], enl)
            par = {tipos[x], tipos[y]}
            ok = par in ({'A', 'F'}, {'F', 'C'}, {'C', 'E'}, {'C'})
            assert ok, (r['cu'], enl, par)
        usados = {p for enl in r['l'] for p in enl.split('|')[:2]}
        assert usados == set(tipos), (r['cu'], set(tipos) - usados)


def notas_desde_fichas():
    """La ficha resumida de cada CU, desde casos_uso.py del Word si está a mano."""
    import sys
    rutas = [AQUI.parent / 'docs' / 'fichas', Path(sys.argv[1]) if len(sys.argv) > 1 else None]
    for ruta in rutas:
        if ruta and (ruta / 'casos_uso.py').exists():
            sys.path.insert(0, str(ruta))
            from casos_uso import BLOQUE_26
            notas = {}
            for b in BLOQUE_26:
                if b[0] != 'tabla' or not b[1][1].startswith('CU-'):
                    continue
                cu = b[1][1].split(' — ')[0]
                filas = dict(b[2])
                notas[cu] = ('FLUJO NORMAL\n' + filas['Flujo principal'] +
                             '\n\nFLUJOS ALTERNATIVOS\n' + filas['Flujos alternativos'])
            return notas
    raise SystemExit('No encontré casos_uso.py: pasá su carpeta como argumento.')


if __name__ == '__main__':
    validar()
    notas = notas_desde_fichas()
    for r in ROBUSTEZ:
        r['nota'] = notas[r['cu']]
    salida = {
        'actores': ACTORES,
        'casos': [dict(id=i, n=n, actores=a, incluye=inc, notas=nt) for i, n, a, inc, nt in CASOS],
        'robustez': ROBUSTEZ,
        'descripcion': DESCRIPCION,
    }
    destino = AQUI / 'ea-p2-ciclo1.datos.json'
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding='utf-8')
    print('ok', destino, len(ROBUSTEZ), 'robusteces,', len(CASOS), 'casos de uso')
