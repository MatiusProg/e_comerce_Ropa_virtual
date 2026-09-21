param(
    # Borra el paquete de este capítulo y lo vuelve a generar.
    [switch]$Rehacer,
    # Genera solo este actor (p. ej. -Actor Administrador). Vacío = todos.
    [string]$Actor = '',
    # Para probar sobre una copia sin tocar el modelo bueno.
    [string]$Modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
)

# =========================================================================
# CAP. 3 - 3.2 DIAGRAMA DE NAVEGACIÓN  (uno POR ACTOR)
#
# ---- DE DÓNDE SALE ESTE FORMATO ----
#   Del ejemplo de cátedra, pág. 11 de «todos los diagramas.pdf», titulado
#   `class navegacion cliente`. Tres cosas lo definen, y las tres son
#   correcciones a la primera versión de este generador:
#
#     1. Va UNO POR ACTOR, no uno por sistema. El título del ejemplo nombra
#        al actor, y el actor está dibujado dentro.
#     2. Lleva LOS CONTROLADORES, no solo las pantallas. El ejemplo dibuja
#        `seguimientoController` con sus operaciones al lado de las vistas.
#     3. Los enlaces van rotulados `build` (se construye una vista) y
#        `submit` (una vista postea al controlador). No son saltos de menú.
#        Y van en CADENA, como en el ejemplo --tablero build-> lista
#        build-> formulario submit-> controlador--, no en idas y vueltas:
#        ver el comentario de la sección de enlaces, más abajo.
#
#   OJO, Y HAY QUE DECIRLO EN LA DEFENSA: el diagrama de navegación NO
#   EXISTE EN UML 2.5. No es uno de los catorce de la norma. Es un diagrama
#   de CLASES con un perfil de navegación --la extensión UWE (UML-based Web
#   Engineering)-- y por eso el tipo en EA es 'Logical' y los elementos son
#   Class. Si preguntan qué diagrama UML es, la respuesta honesta es que no
#   lo es.
#
# ---- DE DÓNDE SALE EL CONTENIDO ----
#   frontend-web/src/app/app.routes.ts -> las rutas y sus guardas
#     `sesionGuard` + `rolGuard(...)`. La guarda del rol es lo que decide de
#     qué actor es cada pantalla, y por eso partir por actor no es una
#     elección estética: es el corte que ya hace el código.
#   frontend-web/src/app/features/<zona>/ -> los componentes, que son las
#     vistas. Un `*.ts` de lista y un `*-formulario.ts` por área.
#   backend/app/modules/<módulo>/router.py -> los controladores. Las
#     operaciones de la clase son los endpoints, con su verbo HTTP.
#
# ---- EN QUÉ SE APARTA DEL EJEMPLO, Y POR QUÉ ----
#   1. El ejemplo pone el controlador del servidor pegado a la vista. Acá
#      hay un salto más --el servicio de Angular (core/services/*.ts)--,
#      que NO se dibuja como clase para no duplicar cada fila: va en la nota
#      del controlador. Dibujarlo sumaría siete cajas que no deciden nada.
#   2. La ruta va como ATRIBUTO `ruta` de la vista, no en el nombre: el nodo
#      se lee «Usuarios» y debajo «+ ruta: /admin/usuarios».
#   3. Los atributos de un formulario son SUS CAMPOS REALES, y los de una
#      lista son sus FILTROS reales (los `Query` del endpoint de listado).
#      Son los que hay que llenar para que el `submit` valga.
#
# ADITIVO: abre el modelo y solo agrega los diagramas que faltan.
# =========================================================================

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }

$NOMBRE_PKG = '3.2 Diagramas de Navegacion'

# ---- Constantes de dibujo (todas juntas, arriba) ----
$W_ACTOR = 110; $H_ACTOR = 110
$W       = 300
# OJO CON EL ALTO. EA trata el alto pedido como un MÍNIMO: si la clase tiene
# más atributos u operaciones de los que entran, agranda la caja hacia abajo
# sin avisar y se come la fila siguiente. Por eso el alto NO es una constante:
# se calcula del contenido con Alto-Caja. El caso peor de este diagrama es
# `catalogo/maestros/router.py`, con dieciséis operaciones.
$H_CAB   = 46                       # cabecera: «estereotipo» + nombre
$H_FILA  = 17                       # cada atributo u operación
$H_MIN   = 90                       # alto mínimo de una caja
$GAP     = 30                       # entre la vista y su formulario
$GAP_BANDA = 60                     # entre una banda y la siguiente

# El corredor entre el menú y la columna de vistas tiene que ser ANCHO: por ahí
# se abren en abanico las siete flechas `build` del tablero, y si es angosto
# cruzan por encima de los formularios que quedan en el camino.
$COL_ACTOR = 40; $COL_MENU = 220; $COL_VISTA = 900; $COL_CTRL = 1280

# ---- Estereotipos ----
# OJO: «view» y «form» son ESTEREOTIPOS RESERVADOS de EA. Si se usan, EA
# cambia la forma de la caja por la de su perfil de interfaz de usuario, no
# escribe el «...» y --lo grave-- DEJA DE DIBUJAR LOS ATRIBUTOS: el formulario
# sale como una caja vacía, sin sus campos, que es justo lo que había que
# mostrar. Por eso se usan los del perfil UWE, que EA no toca.
$EST_VISTA = 'navigationClass'
$EST_FORM  = 'formClass'
$EST_CTRL  = 'controller'
$EST_MENU  = 'menu'

# =========================================================================
# LOS DATOS: un bloque por actor.
#
#   menu  -> la pantalla eje del actor, la que deja el login
#   areas -> una por zona funcional. Cada una tiene su vista de lista, su
#            formulario y su controlador:
#              vista -> n, ruta, attrs (los FILTROS del endpoint de listado)
#              form  -> n, attrs (los CAMPOS del formulario)
#              ctrl  -> n, archivo, ops (los ENDPOINTS, con su verbo)
# =========================================================================
$ACTORES = @(
    @{
        actor  = 'Administrador'
        ciclo  = '#1'
        guarda = '[sesion + ADMINISTRADOR]'
        nota   = 'Navegacion del Administrador en el Ciclo 1. Extension UWE (no es UML 2.5). Espejo de app.routes.ts: cada vista es un componente y cada controlador es el router.py de su modulo. Los enlaces build/submit son las dos direcciones del ciclo peticion/respuesta.'
        menu   = @{ n = 'admin-layout.ts'; ruta = '/admin'
                    carpeta = 'features/admin/admin-layout'
                    ops = @() }
        areas = @(
            @{
                k = 'usuarios'; cu = 'CU-03'
                vista = @{ n = 'usuarios.ts'; ruta = '/admin/usuarios'
                           carpeta = 'features/admin/usuarios'
                           attrs = @('busqueda', 'rol', 'activo', 'pagina', 'tamano') }
                form  = @{ n = 'usuario-formulario.ts'
                           carpeta = 'features/admin/usuarios'
                           attrs = @('correo', 'nombres', 'apellidos', 'rol', 'sucursal_id', 'contrasena') }
                ctrl  = @{ n = 'seguridad/router.py'
                           ops = @('listar_usuarios', 'crear_usuario', 'obtener_usuario',
                                   'editar_usuario', 'cambiar_estado', 'eliminar_usuario') }
            },
            @{
                k = 'ciudades'; cu = 'CU-05'
                vista = @{ n = 'ciudades.ts'; ruta = '/admin/ciudades'
                           carpeta = 'features/admin/ciudades'
                           attrs = @('busqueda') }
                form  = @{ n = 'ciudad-formulario.ts'
                           carpeta = 'features/admin/ciudades'
                           attrs = @('nombre') }
                # Ciudades y sucursales son el MISMO archivo. Comparten caja: es
                # la consecuencia de nombrar por archivo (regla de oro 10).
                ctrl  = @{ n = 'organizacion/router.py'
                           ops = @('listar_ciudades', 'crear_ciudad', 'obtener_ciudad',
                                   'editar_ciudad', 'eliminar_ciudad',
                                   'listar_sucursales', 'crear_sucursal', 'obtener_sucursal',
                                   'editar_sucursal', 'cambiar_estado_sucursal') }
            },
            @{
                k = 'sucursales'; cu = 'CU-05'
                vista = @{ n = 'sucursales.ts'; ruta = '/admin/sucursales'
                           carpeta = 'features/admin/sucursales'
                           attrs = @('ciudad_id', 'activa') }
                form  = @{ n = 'sucursal-formulario.ts'
                           carpeta = 'features/admin/sucursales'
                           attrs = @('nombre', 'ciudad_id', 'direccion', 'telefono') }
                ctrl  = @{ n = 'organizacion/router.py'
                           ops = @('listar_ciudades', 'crear_ciudad', 'obtener_ciudad',
                                   'editar_ciudad', 'eliminar_ciudad',
                                   'listar_sucursales', 'crear_sucursal', 'obtener_sucursal',
                                   'editar_sucursal', 'cambiar_estado_sucursal') }
            },
            @{
                k = 'empleados'; cu = 'CU-06'
                vista = @{ n = 'empleados.ts'; ruta = '/admin/empleados'
                           carpeta = 'features/admin/empleados'
                           attrs = @('sucursal_id', 'cargo', 'activo') }
                form  = @{ n = 'empleado-formulario.ts'
                           carpeta = 'features/admin/empleados'
                           attrs = @('usuario_id', 'documento', 'cargo', 'sucursal_id') }
                ctrl  = @{ n = 'organizacion/empleados/router.py'
                           ops = @('listar_empleados', 'listar_cargos', 'listar_usuarios_vinculables',
                                   'crear_empleado', 'obtener_empleado', 'editar_empleado',
                                   'dar_de_baja') }
            },
            @{
                k = 'proveedores'; cu = 'CU-07'
                vista = @{ n = 'proveedores.ts'; ruta = '/admin/proveedores'
                           carpeta = 'features/admin/proveedores'
                           attrs = @('busqueda', 'activo') }
                form  = @{ n = 'proveedor-formulario.ts'
                           carpeta = 'features/admin/proveedores'
                           attrs = @('razon_social', 'identificacion_tributaria', 'contacto', 'telefono') }
                ctrl  = @{ n = 'organizacion/proveedores_router.py'
                           ops = @('listar_proveedores', 'crear_proveedor', 'obtener_proveedor',
                                   'editar_proveedor', 'cambiar_estado_proveedor',
                                   'habilitar_acceso') }
            },
            @{
                k = 'maestros'; cu = 'CU-08'
                vista = @{ n = 'maestros.ts'; ruta = '/admin/maestros'
                           carpeta = 'features/admin/maestros'
                           attrs = @('pestana', 'busqueda', 'activo') }
                form  = @{ n = 'categoria-formulario.ts'
                           carpeta = 'features/admin/maestros'
                           attrs = @('nombre', 'categoria_padre_id') }
                ctrl  = @{ n = 'catalogo/maestros/router.py'
                           ops = @('listar_categorias', 'crear_categoria', 'editar_categoria',
                                   'cambiar_estado_categoria', 'eliminar_categoria',
                                   'listar_tallas', 'listar_tipos_de_prenda', 'crear_talla',
                                   'editar_talla', 'cambiar_estado_talla', 'eliminar_talla',
                                   'listar_colores', 'crear_color', 'editar_color',
                                   'cambiar_estado_color', 'eliminar_color') }
            },
            @{
                k = 'temporadas'; cu = 'CU-09'
                vista = @{ n = 'temporadas.ts'; ruta = '/admin/temporadas'
                           carpeta = 'features/admin/temporadas'
                           attrs = @('activa') }
                form  = @{ n = 'temporada-formulario.ts'
                           carpeta = 'features/admin/temporadas'
                           attrs = @('nombre', 'fecha_inicio', 'fecha_fin', 'activa') }
                ctrl  = @{ n = 'catalogo/temporadas_router.py'
                           ops = @('listar_temporadas', 'crear_temporada', 'obtener_temporada',
                                   'editar_temporada', 'cambiar_estado_temporada',
                                   'eliminar_temporada', 'listar_colecciones', 'crear_coleccion',
                                   'obtener_coleccion', 'editar_coleccion',
                                   'cambiar_estado_coleccion') }
            }
        )
    },

    @{
        actor  = 'Cliente'
        ciclo  = '#1'
        guarda = '[sesion + CLIENTE]'
        nota   = 'Navegacion del Cliente en el Ciclo 1. Es el unico actor con pantallas PUBLICAS: /login y /registro no declaran canActivate, y por eso cuelgan del actor y no del eje del rol. El perfil es UNA pantalla con dos formularios encima, sin lista propia.'
        menu   = @{ n = 'perfil.ts'; ruta = '/mi-cuenta'
                    carpeta = 'features/cliente/perfil'
                    ops = @() }
        areas = @(
            @{
                k = 'acceso'; cu = 'CU-01'; publica = $true
                vista = @{ n = 'login.ts'; ruta = '/login'
                           carpeta = 'features/auth/login'
                           attrs = @('correo', 'contrasena') }
                form  = @{ n = 'registro.ts'
                           carpeta = 'features/auth/registro'
                           attrs = @('correo', 'documento', 'nombres', 'apellidos', 'contrasena') }
                ctrl  = @{ n = 'seguridad/router.py'
                           ops = @('registrar_cliente', 'iniciar_sesion', 'cerrar_sesion',
                                   'usuario_autenticado') }
            },
            @{
                k = 'direcciones'; cu = 'CU-04'
                form  = @{ n = 'direccion-formulario.ts'
                           carpeta = 'features/cliente/perfil'
                           attrs = @('ciudad_id', 'calle', 'referencia', 'predeterminada') }
                ctrl  = @{ n = 'seguridad/router.py'
                           ops = @('obtener_perfil', 'editar_perfil', 'guardar_preferencias',
                                   'agregar_direccion', 'marcar_predeterminada',
                                   'eliminar_direccion', 'cambiar_contrasena') }
            },
            @{
                k = 'contrasena'; cu = 'CU-04'
                form  = @{ n = 'cambio-contrasena.ts'
                           carpeta = 'features/cliente/perfil'
                           attrs = @('contrasena_actual', 'contrasena_nueva') }
                ctrl  = @{ n = 'seguridad/router.py'
                           ops = @('obtener_perfil', 'editar_perfil', 'guardar_preferencias',
                                   'agregar_direccion', 'marcar_predeterminada',
                                   'eliminar_direccion', 'cambiar_contrasena') }
            }
        )
    },

    @{
        actor  = 'Encargado de Sucursal'
        ciclo  = '#1'
        guarda = '[sesion + ENCARGADO]'
        nota   = 'Navegacion del Encargado en el Ciclo 1. Se reduce a la pantalla de bienvenida con el nombre de su sucursal: sus funciones propias llegan con las reservas y el inventario del Ciclo 2. Se dibuja igual para mostrar que la guarda por rol ya esta operando.'
        menu   = @{ n = 'bienvenida.ts'; ruta = '/sucursal'
                    carpeta = 'shared/bienvenida'
                    ops = @() }
        areas = @()
    },

    @{
        actor  = 'Cajero'
        ciclo  = '#1'
        guarda = '[sesion + CAJERO]'
        # OJO: NO es el mismo componente que el del Encargado. /sucursal monta
        # shared/bienvenida y /caja monta features/inicio; se ven parecidos pero
        # son dos archivos, y por la regla de oro 10 el nombre es el archivo.
        nota   = 'Navegacion del Cajero en el Ciclo 1. Solo la pantalla de inicio: el punto de venta es del Ciclo 3. Se dibuja igual para mostrar que la guarda por rol ya esta operando.'
        menu   = @{ n = 'inicio.ts'; ruta = '/caja'
                    carpeta = 'features/inicio'
                    ops = @() }
        areas = @()
    },

    @{
        actor  = 'Cliente'
        ciclo  = '#2'
        guarda = '[sesion + CLIENTE]'
        nota   = 'Navegacion del Cliente en el Ciclo 2. ACUMULATIVA: lleva lo del Ciclo 1 mas la vitrina y las reservas, porque un mapa de navegacion es la foto de todo lo que el actor puede alcanzar, no solo lo nuevo. OJO: /tienda y /tienda/producto/:id son PUBLICAS --no declaran canActivate-- y por eso cuelgan del actor; que desde la zona con sesion no salga ninguna flecha de vuelta a /tienda es el defecto de navegacion detectado el 13/09.'
        menu   = @{ n = 'perfil.ts'; ruta = '/mi-cuenta'
                    carpeta = 'features/cliente/perfil'
                    ops = @() }
        areas = @(
            @{
                k = 'acceso'; cu = 'CU-01'; publica = $true
                vista = @{ n = 'login.ts'; ruta = '/login'
                           carpeta = 'features/auth/login'
                           attrs = @('correo', 'contrasena') }
                form  = @{ n = 'registro.ts'
                           carpeta = 'features/auth/registro'
                           attrs = @('correo', 'documento', 'nombres', 'apellidos', 'contrasena') }
                ctrl  = @{ n = 'seguridad/router.py'
                           ops = @('registrar_cliente', 'iniciar_sesion', 'cerrar_sesion',
                                   'usuario_autenticado') }
            },
            @{
                k = 'vitrina'; cu = 'CU-17'; publica = $true
                vista = @{ n = 'catalogo.ts'; ruta = '/tienda'
                           carpeta = 'features/tienda/catalogo'
                           attrs = @('busqueda', 'categoria_id', 'talla_id', 'color_id', 'pagina') }
                ctrl  = @{ n = 'catalogo_publico/router.py'
                           ops = @('listar_catalogo', 'ficha_de_producto',
                                   'disponibilidad_por_sucursal') }
            },
            @{
                k = 'favoritos'; cu = 'CU-20'
                vista = @{ n = 'favoritos.ts'; ruta = '/tienda/favoritos'
                           carpeta = 'features/tienda/favoritos'
                           attrs = @('pagina') }
                ctrl  = @{ n = 'catalogo_publico/router.py'
                           ops = @('listar_catalogo', 'ficha_de_producto',
                                   'disponibilidad_por_sucursal') }
            },
            @{
                k = 'reservas'; cu = 'CU-22'
                vista = @{ n = 'reservas.ts'; ruta = '/mi-cuenta/reservas'
                           carpeta = 'features/cliente/reservas'
                           attrs = @('estado') }
                form  = @{ n = 'reserva-formulario.ts'
                           carpeta = 'features/cliente/reservas'
                           attrs = @('sucursal_id', 'franja_inicio', 'franja_fin', 'variantes') }
                ctrl  = @{ n = 'reservas/router.py'
                           ops = @('listar_mis_reservas', 'crear_reserva', 'obtener_reserva',
                                   'cancelar_reserva') }
            },
            @{
                k = 'direcciones'; cu = 'CU-04'
                form  = @{ n = 'direccion-formulario.ts'
                           carpeta = 'features/cliente/perfil'
                           attrs = @('ciudad_id', 'calle', 'referencia', 'predeterminada') }
                ctrl  = @{ n = 'seguridad/router.py'
                           ops = @('obtener_perfil', 'editar_perfil', 'guardar_preferencias',
                                   'agregar_direccion', 'marcar_predeterminada',
                                   'eliminar_direccion', 'cambiar_contrasena') }
            },
            @{
                k = 'contrasena'; cu = 'CU-04'
                form  = @{ n = 'cambio-contrasena.ts'
                           carpeta = 'features/cliente/perfil'
                           attrs = @('contrasena_actual', 'contrasena_nueva') }
                ctrl  = @{ n = 'seguridad/router.py'
                           ops = @('obtener_perfil', 'editar_perfil', 'guardar_preferencias',
                                   'agregar_direccion', 'marcar_predeterminada',
                                   'eliminar_direccion', 'cambiar_contrasena') }
            }
        )
    },

    @{
        actor  = 'Encargado de Sucursal'
        ciclo  = '#2'
        guarda = '[sesion + ENCARGADO]'
        nota   = 'Navegacion del Encargado en el Ciclo 2. Aqui aparece su zona propia: /sucursal con reservas, disponibilidad e inventario. El ambito de datos sale del token, no de la ruta: el Encargado solo ve su sucursal.'
        menu   = @{ n = 'sucursal-layout.ts'; ruta = '/sucursal'
                    carpeta = 'features/sucursal/sucursal-layout'
                    ops = @() }
        areas = @(
            @{
                # Un archivo montado en DOS rutas: el Encargado lo ve en
                # /sucursal/reservas y el Administrador en /admin/reservas. Es
                # el mismo elemento del modelo, asi que el atributo `ruta` lleva
                # las dos.
                k = 'reservas'; cu = 'CU-24'
                vista = @{ n = 'reservas-sucursal.ts'; ruta = '/sucursal/reservas y /admin/reservas'
                           carpeta = 'features/sucursal/reservas'
                           attrs = @('estado', 'fecha') }
                form  = @{ n = 'atencion-formulario.ts'
                           carpeta = 'features/sucursal/reservas'
                           attrs = @('resultado_por_prenda', 'observacion') }
                ctrl  = @{ n = 'reservas/router.py'
                           ops = @('listar_reservas_de_sucursal', 'obtener_reserva_de_sucursal',
                                   'preparar_reserva', 'atender_reserva') }
            },
            @{
                k = 'disponibilidad'; cu = 'CU-16'
                vista = @{ n = 'disponibilidad.ts'; ruta = '/sucursal/disponibilidad'
                           carpeta = 'features/sucursal/disponibilidad'
                           attrs = @('busqueda', 'solo_alertas') }
                form  = @{ n = 'minimo-formulario.ts'
                           carpeta = 'features/admin/inventario'
                           attrs = @('stock_minimo') }
                ctrl  = @{ n = 'inventario/router.py'
                           ops = @('listar_existencias', 'alertas_de_stock', 'fijar_stock_minimo',
                                   'listar_movimientos', 'listar_tipos_de_movimiento') }
            },
            @{
                # Igual que las reservas: un archivo en dos rutas.
                k = 'inventario'; cu = 'CU-13'
                vista = @{ n = 'inventario.ts'; ruta = '/sucursal/inventario y /admin/inventario'
                           carpeta = 'features/admin/inventario'
                           attrs = @('sucursal_id', 'tipo', 'desde', 'hasta') }
                form  = @{ n = 'ingreso-formulario.ts'
                           carpeta = 'features/admin/inventario'
                           attrs = @('proveedor_id', 'sucursal_id', 'lineas') }
                ctrl  = @{ n = 'inventario/router.py'
                           ops = @('registrar_ingreso', 'listar_ingresos', 'detalle_de_ingreso',
                                   'registrar_ajuste', 'registrar_transferencia') }
            }
        )
    },

    @{
        actor  = 'Administrador'
        ciclo  = '#2'
        guarda = '[sesion + ADMINISTRADOR]'
        nota   = 'Navegacion del Administrador en el Ciclo 2. ACUMULATIVA: lleva las siete areas del Ciclo 1 mas las cinco nuevas (productos, imagenes, inventario, consolidado y reservas de la red), porque un mapa de navegacion es la foto de todo lo que el actor puede alcanzar. Es el diagrama mas grande del capitulo; para el .docx conviene partirlo o apretarlo.'
        menu   = @{ n = 'admin-layout.ts'; ruta = '/admin'
                    carpeta = 'features/admin/admin-layout'
                    ops = @() }
        areas = @(
            @{
                k = 'usuarios'; cu = 'CU-03'
                vista = @{ n = 'usuarios.ts'; ruta = '/admin/usuarios'
                           carpeta = 'features/admin/usuarios'
                           attrs = @('busqueda', 'rol', 'activo', 'pagina', 'tamano') }
                form  = @{ n = 'usuario-formulario.ts'
                           carpeta = 'features/admin/usuarios'
                           attrs = @('correo', 'nombres', 'apellidos', 'rol', 'sucursal_id', 'contrasena') }
                ctrl  = @{ n = 'seguridad/router.py'
                           ops = @('listar_usuarios', 'crear_usuario', 'obtener_usuario',
                                   'editar_usuario', 'cambiar_estado', 'eliminar_usuario') }
            },
            @{
                k = 'ciudades'; cu = 'CU-05'
                vista = @{ n = 'ciudades.ts'; ruta = '/admin/ciudades'
                           carpeta = 'features/admin/ciudades'
                           attrs = @('busqueda') }
                form  = @{ n = 'ciudad-formulario.ts'
                           carpeta = 'features/admin/ciudades'
                           attrs = @('nombre') }
                ctrl  = @{ n = 'organizacion/router.py'
                           ops = @('listar_ciudades', 'crear_ciudad', 'obtener_ciudad',
                                   'editar_ciudad', 'eliminar_ciudad',
                                   'listar_sucursales', 'crear_sucursal', 'obtener_sucursal',
                                   'editar_sucursal', 'cambiar_estado_sucursal') }
            },
            @{
                k = 'sucursales'; cu = 'CU-05'
                vista = @{ n = 'sucursales.ts'; ruta = '/admin/sucursales'
                           carpeta = 'features/admin/sucursales'
                           attrs = @('ciudad_id', 'activa') }
                form  = @{ n = 'sucursal-formulario.ts'
                           carpeta = 'features/admin/sucursales'
                           attrs = @('nombre', 'ciudad_id', 'direccion', 'telefono') }
                ctrl  = @{ n = 'organizacion/router.py'
                           ops = @('listar_ciudades', 'crear_ciudad', 'obtener_ciudad',
                                   'editar_ciudad', 'eliminar_ciudad',
                                   'listar_sucursales', 'crear_sucursal', 'obtener_sucursal',
                                   'editar_sucursal', 'cambiar_estado_sucursal') }
            },
            @{
                k = 'empleados'; cu = 'CU-06'
                vista = @{ n = 'empleados.ts'; ruta = '/admin/empleados'
                           carpeta = 'features/admin/empleados'
                           attrs = @('sucursal_id', 'cargo', 'activo') }
                form  = @{ n = 'empleado-formulario.ts'
                           carpeta = 'features/admin/empleados'
                           attrs = @('usuario_id', 'documento', 'cargo', 'sucursal_id') }
                ctrl  = @{ n = 'organizacion/empleados/router.py'
                           ops = @('listar_empleados', 'listar_cargos', 'listar_usuarios_vinculables',
                                   'crear_empleado', 'obtener_empleado', 'editar_empleado',
                                   'dar_de_baja') }
            },
            @{
                k = 'proveedores'; cu = 'CU-07'
                vista = @{ n = 'proveedores.ts'; ruta = '/admin/proveedores'
                           carpeta = 'features/admin/proveedores'
                           attrs = @('busqueda', 'activo') }
                form  = @{ n = 'proveedor-formulario.ts'
                           carpeta = 'features/admin/proveedores'
                           attrs = @('razon_social', 'identificacion_tributaria', 'contacto', 'telefono') }
                ctrl  = @{ n = 'organizacion/proveedores_router.py'
                           ops = @('listar_proveedores', 'crear_proveedor', 'obtener_proveedor',
                                   'editar_proveedor', 'cambiar_estado_proveedor',
                                   'habilitar_acceso') }
            },
            @{
                k = 'maestros'; cu = 'CU-08'
                vista = @{ n = 'maestros.ts'; ruta = '/admin/maestros'
                           carpeta = 'features/admin/maestros'
                           attrs = @('pestana', 'busqueda', 'activo') }
                form  = @{ n = 'categoria-formulario.ts'
                           carpeta = 'features/admin/maestros'
                           attrs = @('nombre', 'categoria_padre_id') }
                ctrl  = @{ n = 'catalogo/maestros/router.py'
                           ops = @('listar_categorias', 'crear_categoria', 'editar_categoria',
                                   'cambiar_estado_categoria', 'eliminar_categoria',
                                   'listar_tallas', 'listar_tipos_de_prenda', 'crear_talla',
                                   'editar_talla', 'cambiar_estado_talla', 'eliminar_talla',
                                   'listar_colores', 'crear_color', 'editar_color',
                                   'cambiar_estado_color', 'eliminar_color') }
            },
            @{
                k = 'temporadas'; cu = 'CU-09'
                vista = @{ n = 'temporadas.ts'; ruta = '/admin/temporadas'
                           carpeta = 'features/admin/temporadas'
                           attrs = @('activa') }
                form  = @{ n = 'temporada-formulario.ts'
                           carpeta = 'features/admin/temporadas'
                           attrs = @('nombre', 'fecha_inicio', 'fecha_fin', 'activa') }
                ctrl  = @{ n = 'catalogo/temporadas_router.py'
                           ops = @('listar_temporadas', 'crear_temporada', 'obtener_temporada',
                                   'editar_temporada', 'cambiar_estado_temporada',
                                   'eliminar_temporada', 'listar_colecciones', 'crear_coleccion',
                                   'obtener_coleccion', 'editar_coleccion',
                                   'cambiar_estado_coleccion') }
            },
            @{
                k = 'productos'; cu = 'CU-10'
                vista = @{ n = 'productos.ts'; ruta = '/admin/productos'
                           carpeta = 'features/admin/productos'
                           attrs = @('busqueda', 'categoria_id', 'temporada_id', 'activo', 'pagina') }
                form  = @{ n = 'producto-formulario.ts'
                           carpeta = 'features/admin/productos'
                           attrs = @('codigo', 'nombre', 'categoria_id', 'temporada_id', 'coleccion_id', 'precio') }
                ctrl  = @{ n = 'catalogo/router.py'
                           ops = @('listar_productos', 'crear_producto', 'obtener_producto',
                                   'editar_producto', 'cambiar_estado_producto', 'eliminar_producto',
                                   'generar_variantes', 'crear_variante', 'editar_variante',
                                   'eliminar_variante') }
            },
            @{
                k = 'imagenes'; cu = 'CU-11'
                vista = @{ n = 'galeria.ts'; ruta = '/admin/productos'
                           carpeta = 'features/admin/productos'
                           attrs = @('producto_id', 'variante_id') }
                ctrl  = @{ n = 'catalogo/imagenes_router.py'
                           ops = @('listar', 'subir', 'editar', 'marcar_principal',
                                   'marcar_transparente', 'reordenar', 'eliminar') }
            },
            @{
                k = 'inventario'; cu = 'CU-13'
                vista = @{ n = 'inventario.ts'; ruta = '/sucursal/inventario y /admin/inventario'
                           carpeta = 'features/admin/inventario'
                           attrs = @('sucursal_id', 'tipo', 'desde', 'hasta') }
                form  = @{ n = 'ingreso-formulario.ts'
                           carpeta = 'features/admin/inventario'
                           attrs = @('proveedor_id', 'sucursal_id', 'lineas') }
                ctrl  = @{ n = 'inventario/router.py'
                           ops = @('registrar_ingreso', 'listar_ingresos', 'detalle_de_ingreso',
                                   'registrar_ajuste', 'registrar_transferencia') }
            },
            @{
                # Consulta pura (CU-14): no tiene formulario ni escribe nada.
                # Entra en el mapa igual, porque el actor puede alcanzarla.
                k = 'consolidado'; cu = 'CU-14'
                vista = @{ n = 'consolidado.ts'; ruta = '/admin/consolidado'
                           carpeta = 'features/admin/consolidado'
                           attrs = @('categoria_id', 'sucursal_id', 'solo_con_stock') }
                ctrl  = @{ n = 'inventario/consolidado_router.py'
                           ops = @('consultar_consolidado') }
            },
            @{
                k = 'reservas'; cu = 'CU-24'
                vista = @{ n = 'reservas-sucursal.ts'; ruta = '/sucursal/reservas y /admin/reservas'
                           carpeta = 'features/sucursal/reservas'
                           attrs = @('estado', 'fecha') }
                form  = @{ n = 'atencion-formulario.ts'
                           carpeta = 'features/sucursal/reservas'
                           attrs = @('resultado_por_prenda', 'observacion') }
                ctrl  = @{ n = 'reservas/router.py'
                           ops = @('listar_reservas_de_sucursal', 'obtener_reserva_de_sucursal',
                                   'preparar_reserva', 'atender_reserva') }
            }
        )
    },

    # ================= CICLO 3 =================================
    #
    # PILOTO DEL 20/09. Un solo caso de uso, para revisar el patron antes de
    # escribir los demas.
    #
    # ESTE BLOQUE NO ES UN ACTOR, ES UN CASO DE USO, y por eso trae `nombre`.
    # El auxiliar pide la navegacion POR CU; los diagramas de los Ciclos 1 y 2
    # se hicieron POR ACTOR, que es la otra forma que el mismo generador
    # soporta. Se deja el bloque acumulativo como esta y el nuevo se dibuja
    # aparte: si el patron por CU convence, los del Ciclo 3 salen todos asi.
    #
    # CU-27 es el mejor candidato del ciclo para probarlo porque es el unico
    # recorrido con las cuatro clases de enlace que el auxiliar describe:
    # link entre paginas, build de la lista, submit al controlador y
    # redirect de vuelta.

    @{
        actor  = 'Cliente'
        ciclo  = '#3'
        nombre = '3.2 Diagrama de Navegacion - CU-27 Realizar pedido y pagar en linea'
        guarda = '[sesion + CLIENTE]'
        nota   = 'Navegacion de CU-27, POR CASO DE USO y no por actor: es el piloto del patron que pide el auxiliar. Extension UWE (no es UML 2.5). El recorrido es carrito -> checkout -> pasarela -> retorno. La vuelta desde la pasarela NO es un link: el estado del pedido lo fija el webhook de CU-28, y la pantalla de retorno solo consulta. Espejo de app.routes.ts.'
        menu   = @{ n = 'carrito.ts'; ruta = '/tienda/carrito'
                    carpeta = 'features/tienda/carrito'
                    ops = @() }
        areas = @(
            @{
                k = 'checkout'; cu = 'CU-27'
                vista = @{ n = 'checkout.ts'; ruta = '/tienda/checkout'
                           carpeta = 'features/tienda/checkout'
                           attrs = @('modalidad_entrega', 'sucursal_id', 'total_visto') }
                form  = @{ n = 'entrega-formulario.ts'
                           carpeta = 'features/tienda/checkout'
                           attrs = @('modalidad_entrega', 'sucursal_id', 'direccion', 'telefono') }
                ctrl  = @{ n = 'ventas/pedidos_router.py'
                           ops = @('opciones_de_pedido', 'confirmar_pedido',
                                   'estado_del_pedido', 'cancelar_pedido') }
            },
            @{
                k = 'retorno'; cu = 'CU-27'
                vista = @{ n = 'pago-retorno.ts'; ruta = '/pago/exito'
                           carpeta = 'features/tienda/pago'
                           attrs = @('codigo') }
                ctrl  = @{ n = 'ventas/pedidos_router.py'
                           ops = @('estado_del_pedido') }
            }
        )
    }
)

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }

function Get-OCrearPaquete($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}
function BuscarDiagrama($p, $n) {
    foreach ($d in $p.Diagrams) { if ($d.Name -eq $n) { return $d } }
    foreach ($s in $p.Packages) { $r = BuscarDiagrama $s $n; if ($r) { return $r } }
    return $null
}
function Poner($dia, $elid, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $ancho);t=$t;b=$($t - $alto);", '')
    $do.ElementID = $elid
    [void]$do.Update()
    return $do
}
# Alto que necesita una caja para mostrar todo su contenido sin que EA la
# agrande por su cuenta. Los compartimentos de atributos y de operaciones son
# independientes: si la clase tiene los dos, se suman.
function AltoCaja($nAttrs, $nOps) {
    $alto = $H_CAB + ($H_FILA * ($nAttrs + $nOps))
    if ($alto -lt $H_MIN) { return $H_MIN }
    return $alto
}
# Crea una clase con estereotipo, sus atributos y sus operaciones.
# Los dos estereotipos (Stereotype y StereotypeEx) SIEMPRE: si no, queda el
# ícono redondo del perfil en vez de la caja. Ver §5.9 de la guía.
#
# REUTILIZA POR NOMBRE. Un archivo es UN elemento del modelo, aunque aparezca
# en los diagramas de varios actores: `seguridad/router.py` atiende al
# Administrador y al Cliente, y tiene que ser la misma caja en los dos. Sin
# esto EA crearía un elemento por diagrama y el explorador se llenaría de
# duplicados con el mismo nombre.
function NuevaClase($pkg, $nombre, $estereotipo, $nota, $attrs, $ops) {
    foreach ($e in $pkg.Elements) {
        if ($e.Name -eq $nombre -and $e.Type -eq 'Class') {
            # Al reutilizar se AGREGAN las operaciones que falten. Un mismo
            # archivo aparece en varios diagramas con distinto subconjunto de
            # funciones --`seguridad/router.py` atiende el registro, el login,
            # los usuarios y el perfil-- y la caja tiene que terminar con la
            # union de todas, no con las del diagrama que la creo primero.
            $yaEstan = @()
            foreach ($m in $e.Methods) { $yaEstan += $m.Name }
            # [int] a la fuerza: Methods.Count llega como un tipo COM que
            # Pos no acepta, y el error --«La conversión especificada no es
            # válida»-- no dice de dónde sale.
            $i = [int]$e.Methods.Count
            foreach ($o in $ops) {
                if ($yaEstan -contains $o) { continue }
                $op = $e.Methods.AddNew($o, '')
                $op.Visibility = 'Public'
                $op.Pos = $i; $i++
                [void]$op.Update()
            }
            $e.Methods.Refresh()
            return $e.ElementID
        }
    }
    $el = $pkg.Elements.AddNew($nombre, 'Class')
    $el.Stereotype   = $estereotipo
    $el.StereotypeEx = $estereotipo
    $el.Notes        = $nota
    [void]$el.Update()
    $i = 0
    foreach ($a in $attrs) {
        $at = $el.Attributes.AddNew($a, '')
        $at.Visibility = 'Public'
        $at.Pos = $i; $i++
        [void]$at.Update()
    }
    $el.Attributes.Refresh()
    $i = 0
    foreach ($o in $ops) {
        # Los nombres van EXACTOS, como están en el código (regla de oro 10):
        # `listar_usuarios`, no `listar(): PaginaUsuarios`. Sin tipo de retorno
        # inventado: el contrato real lo dan los esquemas Pydantic del router,
        # y ponerlo acá obligaría a mantener dos fuentes.
        $nom = $o; $ret = ''
        if ($o -match '^(.*?)\(\)\s*:\s*(.+)$') { $nom = $Matches[1]; $ret = $Matches[2] }
        elseif ($o -match '^(.*?)\(\)') { $nom = $Matches[1] }
        $op = $el.Methods.AddNew($nom, $ret)
        $op.Visibility = 'Public'
        $op.Pos = $i; $i++
        [void]$op.Update()
    }
    $el.Methods.Refresh()
    return $el.ElementID
}
# Enlace rotulado. 'build' y 'submit' son estereotipos del perfil, igual que
# 'navigationLink'.
function Enlazar($ea, $desdeId, $hastaId, $rotulo, $estereotipo) {
    $src = $ea.GetElementByID($desdeId)
    $c = $src.Connectors.AddNew($rotulo, 'Association')
    $c.SupplierID   = $hastaId
    if ($estereotipo) {
        $c.Stereotype   = $estereotipo
        $c.StereotypeEx = $estereotipo
    }
    $c.Direction    = 'Source -> Destination'
    [void]$c.Update()
    $src.Connectors.Refresh()
}

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaquete $root 'Violet Boutique'
$pCap  = Get-OCrearPaquete $pRaiz 'CAP. 3 - Flujo de Trabajo: Diseno'

if ($Rehacer) {
    for ($i = $pCap.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pCap.Packages.GetAt($i).Name -eq $NOMBRE_PKG) {
            $pCap.Packages.DeleteAt($i, $false)
            Write-Output '  paquete anterior eliminado (-Rehacer)'
        }
    }
    $pCap.Packages.Refresh()
}

$pkg = Get-OCrearPaquete $pCap $NOMBRE_PKG
$hechos = 0

foreach ($a in $ACTORES) {
    if ($Actor -and $a.actor -ne $Actor) { continue }

    # Un bloque puede nombrar su propio diagrama. Se agrego el 20/09 porque
    # el auxiliar pide la navegacion POR CASO DE USO y este generador estaba
    # agrupado POR ACTOR: sin esto, un bloque de un solo CU se dibujaria con
    # el nombre del actor y se pisaria con el mapa acumulativo del ciclo.
    $NOMBRE_DIA = if ($a.nombre) { $a.nombre }
                  else { "3.2 Diagrama de Navegacion - $($a.actor) - CICLO $($a.ciclo)" }
    if (BuscarDiagrama $pkg $NOMBRE_DIA) {
        Write-Output "  $NOMBRE_DIA ya existe, no se toca"
        continue
    }

    $dia = $pkg.Diagrams.AddNew($NOMBRE_DIA, 'Logical')
    $dia.Notes = $a.nota
    [void]$dia.Update(); $pkg.Diagrams.Refresh()

    # ---- El actor: se REUTILIZA el del CAP. 1, no se copia. Si se renombra
    #      allá, se renombra acá. Es la misma regla que siguen los 2.2.
    $actorId = 0
    $r = $ea.SQLQuery("SELECT TOP 1 Object_ID FROM t_object WHERE Object_Type='Actor' AND Name='$($a.actor)' ORDER BY Object_ID")
    if ($r -match '<Object_ID>(\d+)</Object_ID>') {
        $actorId = [int]$Matches[1]
    } else {
        Write-Output "  AVISO: no hay actor '$($a.actor)' en el modelo; se crea uno nuevo"
        $el = $pkg.Elements.AddNew($a.actor, 'Actor'); [void]$el.Update()
        $actorId = $el.ElementID
        $pkg.Elements.Refresh()
    }

    # ---- Los elementos. Se guarda el ID, NUNCA la referencia COM.
    $menuId = NuevaClase $pkg $a.menu.n $EST_MENU `
        "Eje de navegacion del actor. frontend-web/src/app/$($a.menu.carpeta)/. Ruta $($a.menu.ruta)." `
        @("ruta: $($a.menu.ruta)") $a.menu.ops

    # Los controladores se crean UNA VEZ POR ARCHIVO, no por área: dos áreas
    # que comparten `router.py` comparten la caja. Es la consecuencia de la
    # regla de oro 10 --el nombre es el archivo-- y es verdad: ciudades y
    # sucursales las atiende el mismo módulo.
    #
    # Un área puede venir SIN vista o SIN formulario. No es un caso raro: el
    # perfil del Cliente es una sola pantalla con dos formularios encima
    # (`direccion-formulario.ts` y `cambio-contrasena.ts`), sin lista propia.
    $ids   = @{}
    $ctrls = @{}
    foreach ($ar in $a.areas) {
        if ($ar.vista) {
            $ids["$($ar.k)|vista"] = NuevaClase $pkg $ar.vista.n $EST_VISTA `
                "$($ar.cu). Ruta $($ar.vista.ruta). frontend-web/src/app/$($ar.vista.carpeta)/$($ar.vista.n) y su .html. Los atributos son los filtros reales del endpoint de listado." `
                (@("ruta: $($ar.vista.ruta)") + $ar.vista.attrs) @()
        }
        if ($ar.form) {
            $ids["$($ar.k)|form"] = NuevaClase $pkg $ar.form.n $EST_FORM `
                "$($ar.cu). frontend-web/src/app/$($ar.form.carpeta)/$($ar.form.n). Los atributos son los campos reales del formulario." `
                $ar.form.attrs @()
        }
        if (-not $ctrls.ContainsKey($ar.ctrl.n)) {
            $ctrls[$ar.ctrl.n] = NuevaClase $pkg $ar.ctrl.n $EST_CTRL `
                "backend/app/modules/$($ar.ctrl.n). Las operaciones son los nombres EXACTOS de las funciones del router. El navegador llega hasta aca por core/services/*.service.ts, que no se dibuja para no duplicar cada fila." `
                @() $ar.ctrl.ops
        }
        $ids["$($ar.k)|ctrl"] = $ctrls[$ar.ctrl.n]
    }
    $pkg.Elements.Refresh()

    # ---- al lienzo. Una banda por área: vista arriba, formulario debajo y
    #      el controlador a la derecha, centrado entre los dos. Así ninguna
    #      flecha cruza una caja.
    #
    #      El alto de cada caja se CALCULA a partir de su contenido. El alto
    #      que se le pide a EA es un mínimo: si no entra, agranda la caja hacia
    #      abajo sin avisar y se come la banda siguiente. Acá el caso peor es
    #      `catalogo/maestros/router.py`, con dieciséis operaciones.
    $baseY = -60
    $y     = $baseY
    $puestos = @{}
    foreach ($ar in $a.areas) {
        $hV = 0; $hF = 0
        if ($ar.vista) { $hV = AltoCaja ($ar.vista.attrs.Count + 1) 0 }
        if ($ar.form)  { $hF = AltoCaja $ar.form.attrs.Count 0 }
        $hC = AltoCaja 0 $ar.ctrl.ops.Count
        $hPila = $hV + $hF
        if ($hV -gt 0 -and $hF -gt 0) { $hPila += $GAP }
        $hBanda = [Math]::Max($hPila, $hC)

        if ($ar.vista) { [void](Poner $dia $ids["$($ar.k)|vista"] $COL_VISTA $y $W $hV) }
        if ($ar.form) {
            $yForm = $y
            if ($hV -gt 0) { $yForm = $y - $hV - $GAP }
            [void](Poner $dia $ids["$($ar.k)|form"] $COL_VISTA $yForm $W $hF)
        }
        # El controlador compartido se dibuja una sola vez, en la primera banda
        # que lo usa: un elemento no puede estar dos veces en el mismo lienzo.
        if (-not $puestos.ContainsKey($ar.ctrl.n)) {
            [void](Poner $dia $ids["$($ar.k)|ctrl"] $COL_CTRL ($y - [int](($hBanda - $hC) / 2)) $W $hC)
            $puestos[$ar.ctrl.n] = $true
        }

        $y -= ($hBanda + $GAP_BANDA)
    }

    $altoTotal = $baseY - $y
    [void](Poner $dia $actorId $COL_ACTOR ($baseY - [int](($altoTotal - $H_ACTOR) / 2)) $W_ACTOR $H_ACTOR)
    [void](Poner $dia $menuId  $COL_MENU  ($baseY - [int](($altoTotal - 110) / 2))      $W       110)

    # ---- los enlaces
    # La navegación se dibuja como una CADENA, igual que el ejemplo de cátedra
    # (`build` hacia la vista, `submit` hacia el controlador), no como idas y
    # vueltas. Dos razones:
    #   1. Si la vista apunta al controlador y el controlador de vuelta a la
    #      vista, EA escribe los dos rótulos en el MISMO punto medio y sale un
    #      amasijo ilegible (`sbuild:` encima de `submit`).
    #   2. La vuelta ya está contada: `Tablero --build--> Vista` es el mismo
    #      `build` que hace el controlador al devolver la página.
    # Los enlaces llevan el rótulo en el NOMBRE y sin estereotipo: con los dos
    # puestos, EA escribe `build` y debajo `«build»`, que es lo mismo dos veces.
    Enlazar $ea $actorId $menuId $a.guarda 'navigationLink'
    $enlaces = 1
    foreach ($ar in $a.areas) {
        $v = $ids["$($ar.k)|vista"]; $f = $ids["$($ar.k)|form"]; $c = $ids["$($ar.k)|ctrl"]
        # La cabeza de la cadena es la vista si la hay; si no, el formulario.
        $cabeza = $v; if (-not $cabeza) { $cabeza = $f }
        # Un área PÚBLICA cuelga del actor, no del menú: `/login` y `/registro`
        # se alcanzan SIN sesión, así que dibujarlas colgando del eje del rol
        # sería mentir sobre la guarda.
        if ($ar.publica) { Enlazar $ea $actorId $cabeza '[sin sesion]' 'navigationLink' }
        else             { Enlazar $ea $menuId  $cabeza 'build' '' }
        $enlaces++
        if ($v) { Enlazar $ea $v $c 'submit' ''; $enlaces++ }   # los filtros -> listar_*
        if ($v -and $f) { Enlazar $ea $v $f 'build' ''; $enlaces++ }  # abre el alta o la edicion
        if ($f) { Enlazar $ea $f $c 'submit' ''; $enlaces++ }   # crear / editar / eliminar
    }

    $pkg.Elements.Refresh()
    $dia.DiagramObjects.Refresh()
    $huerfanos = $ea.SQLQuery("SELECT COUNT(*) AS n FROM t_diagramobjects WHERE Diagram_ID=$($dia.DiagramID) AND Object_ID=0")
    # $enlaces se fue contando al enlazar.
    Write-Output "  $NOMBRE_DIA : $($dia.DiagramObjects.Count) elementos, $enlaces enlaces"
    if ($huerfanos -match '<n>([1-9]\d*)</n>') { Write-Output "  AVISO: $($Matches[1]) objetos con Object_ID=0" }
    $hechos++
}

Write-Output "  $hechos diagrama(s) generado(s)"
$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Write-Output 'OK'
