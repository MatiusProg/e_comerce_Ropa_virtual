param(
    # Borra el paquete de este capítulo y lo vuelve a generar.
    [switch]$Rehacer,
    # Genera solo este actor (p. ej. -Actor Administrador). Vacío = todos.
    [string]$Actor = '',
    # Genera solo este caso de uso (p. ej. -CU CU-27). Vacío = todos.
    #
    # Existe desde el 20/09, cuando el capítulo pasó a llevar también
    # bloques POR CASO DE USO: sin este filtro, pedir el de CU-27 por su
    # actor arrastraba de vuelta los mapas acumulativos del Cliente.
    [string]$CU = '',
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
    # Los siete mapas POR ACTOR se quitaron el 20/09: el auxiliar pide la
    # navegacion POR CASO DE USO, y ademas el acumulativo crecia hasta ser
    # ilegible. Los que vuelven, por CU, estan mas abajo.

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
        cu     = 'CU-27'
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
    },

    @{
        actor  = 'Cliente'
        ciclo  = '#3'
        cu     = 'CU-33'
        nombre = '3.2 Diagrama de Navegacion - CU-33 Recibir recomendaciones de prendas'
        guarda = '[sesion + CLIENTE]'
        nota   = 'Navegacion de CU-33, POR CASO DE USO. Extension UWE (no es UML 2.5). Es el recorrido mas corto del ciclo y eso es el hallazgo: `Para vos` no tiene formulario --el cliente no pide nada, el sistema propone-- asi que no hay <submit>. La unica salida es el <link> a la ficha de una prenda sugerida.'
        menu   = @{ n = 'para-vos.ts'; ruta = '/tienda/para-vos'
                    carpeta = 'features/tienda/para-vos'
                    ops = @() }
        areas = @(
            @{
                k = 'sugerencias'; cu = 'CU-33'
                vista = @{ n = 'para-vos.ts'; ruta = '/tienda/para-vos'
                           carpeta = 'features/tienda/para-vos'
                           attrs = @('prenda', 'motivo', 'precio') }
                ctrl  = @{ n = 'ia/router.py'
                           ops = @('mis_recomendaciones') }
            },
            @{
                k = 'ficha'; cu = 'CU-33'
                vista = @{ n = 'ficha.ts'; ruta = '/tienda/producto/:id'
                           carpeta = 'features/tienda/ficha'
                           attrs = @('producto_id') }
                ctrl  = @{ n = 'catalogo_publico/router.py'
                           ops = @('ficha_de_producto') }
            }
        )
    },

    @{
        actor  = 'Cliente'
        ciclo  = '#3'
        cu     = 'CU-34'
        nombre = '3.2 Diagrama de Navegacion - CU-34 Conversar con el asistente virtual'
        guarda = '[sesion + CLIENTE]'
        nota   = 'Navegacion de CU-34, POR CASO DE USO. Extension UWE (no es UML 2.5). El <submit> de la pregunta NO redirige: el controlador devuelve a la MISMA pantalla, que es lo que permite seguir conversando. Los enlaces a las fichas salen de los codigos que el servidor valido; un codigo inventado por el modelo no llega a dibujarse.'
        menu   = @{ n = 'asistente.ts'; ruta = '/tienda/asistente'
                    carpeta = 'features/tienda/asistente'
                    ops = @() }
        areas = @(
            @{
                k = 'conversacion'; cu = 'CU-34'
                vista = @{ n = 'asistente.ts'; ruta = '/tienda/asistente'
                           carpeta = 'features/tienda/asistente'
                           attrs = @('turnos', 'ejemplos', 'pensando') }
                form  = @{ n = 'redaccion.html'
                           carpeta = 'features/tienda/asistente'
                           attrs = @('pregunta', 'historial') }
                ctrl  = @{ n = 'ia/asistente_router.py'
                           ops = @('esta_disponible', 'preguntar') }
            },
            @{
                k = 'ficha'; cu = 'CU-34'
                vista = @{ n = 'ficha.ts'; ruta = '/tienda/producto/:id'
                           carpeta = 'features/tienda/ficha'
                           attrs = @('producto_id') }
                ctrl  = @{ n = 'catalogo_publico/router.py'
                           ops = @('ficha_de_producto') }
            }
        )
    },

    @{
        actor  = 'Cajero'
        ciclo  = '#3'
        cu     = 'CU-31'
        nombre = '3.2 Diagrama de Navegacion - CU-31 Registrar venta presencial'
        guarda = '[sesion + CAJERO]'
        nota   = 'Navegacion de CU-31, POR CASO DE USO. Extension UWE (no es UML 2.5). El eje NO es el mostrador sino la CAJA: sin turno abierto no se llega a cobrar, y por eso la apertura de turno (CU-30) esta dibujada como la puerta. Las dos entradas al mostrador --buscar prendas y cargar una reserva atendida-- terminan en el mismo <submit>.'
        menu   = @{ n = 'caja.ts'; ruta = '/caja'
                    carpeta = 'features/caja/turno'
                    ops = @() }
        areas = @(
            @{
                k = 'mostrador'; cu = 'CU-31'
                vista = @{ n = 'mostrador.ts'; ruta = '/caja/venta'
                           carpeta = 'features/caja/mostrador'
                           attrs = @('busqueda', 'sucursal_id') }
                form  = @{ n = 'venta-formulario.ts'
                           carpeta = 'features/caja/mostrador'
                           attrs = @('detalle', 'medio_pago', 'total') }
                ctrl  = @{ n = 'pos/router.py'
                           ops = @('prendas_del_mostrador', 'registrar_venta', 'ver_venta') }
            },
            @{
                k = 'reservas'; cu = 'CU-31'
                vista = @{ n = 'reservas-por-cobrar.ts'; ruta = '/caja/reservas'
                           carpeta = 'features/caja/reservas'
                           attrs = @('sucursal_id', 'estado') }
                ctrl  = @{ n = 'pos/router.py'
                           ops = @('reservas_por_cobrar', 'ver_reserva') }
            },
            @{
                k = 'comprobante'; cu = 'CU-31'
                vista = @{ n = 'comprobante.ts'; ruta = '/caja/venta/:codigo'
                           carpeta = 'features/caja/comprobante'
                           attrs = @('codigo') }
                ctrl  = @{ n = 'pos/router.py'
                           ops = @('comprobante') }
            }
        )
    },

    @{
        actor  = 'Cajero'
        ciclo  = '#3'
        cu     = 'CU-32'
        nombre = '3.2 Diagrama de Navegacion - CU-32 Registrar devolucion o cambio'
        guarda = '[sesion + CAJERO]'
        nota   = 'Navegacion de CU-32, POR CASO DE USO. Extension UWE (no es UML 2.5). UNA SOLA VISTA para los dos flujos, y es una decision: el cliente elige entre devolver y cambiar DESPUES de que el cajero busco la venta y vio que queda por devolver. Dos pantallas obligarian a elegir antes de tener esa informacion y a volver atras cuando cambia de idea. El buscador de la prenda nueva reusa el de CU-31.'
        menu   = @{ n = 'caja.ts'; ruta = '/caja'
                    carpeta = 'features/caja/turno'
                    ops = @() }
        areas = @(
            @{
                k = 'devolucion'; cu = 'CU-32'
                vista = @{ n = 'devolucion.ts'; ruta = '/caja/devoluciones'
                           carpeta = 'features/caja/devolucion'
                           attrs = @('codigo', 'venta', 'lineas', 'dentro_de_plazo') }
                form  = @{ n = 'devolucion-formulario.ts'
                           carpeta = 'features/caja/devolucion'
                           attrs = @('motivo', 'lineas') }
                ctrl  = @{ n = 'pos/devolucion_router.py'
                           ops = @('venta_a_devolver', 'registrar_devolucion') }
            },
            @{
                k = 'cambio'; cu = 'CU-32'
                vista = @{ n = 'cambio-prendas.ts'; ruta = '/caja/devoluciones'
                           carpeta = 'features/caja/devolucion'
                           attrs = @('busqueda', 'llevadas', 'diferencia', 'a_favor_de') }
                form  = @{ n = 'cambio-formulario.ts'
                           carpeta = 'features/caja/devolucion'
                           attrs = @('devueltas', 'llevadas', 'metodo_diferencia', 'diferencia_esperada') }
                ctrl  = @{ n = 'pos/devolucion_router.py'
                           ops = @('registrar_cambio') }
            },
            @{
                k = 'prendas'; cu = 'CU-31'
                vista = @{ n = 'mostrador.ts'; ruta = '/caja/venta'
                           carpeta = 'features/caja/mostrador'
                           attrs = @('busqueda', 'sucursal_id') }
                ctrl  = @{ n = 'pos/router.py'
                           ops = @('prendas_del_mostrador') }
            }
        )
    },

    @{
        actor  = 'Cliente'
        ciclo  = '#3'
        cu     = 'CU-21'
        base   = 'mobile/lib'
        nombre = '3.2 Diagrama de Navegacion - CU-21 Utilizar vestidor virtual (RA)'
        guarda = '[sesion + CLIENTE, solo movil]'
        nota   = 'Navegacion de CU-21, POR CASO DE USO. Extension UWE (no es UML 2.5). OJO: este es el UNICO del capitulo que NO esta en la web --el vestidor existe solo en el telefono--, asi que las rutas son de go_router y las carpetas de mobile/lib, no de frontend-web. El <submit> de las medidas es el unico que escribe; el vestidor en si no persiste nada.'
        menu   = @{ n = 'pantalla_vestidor.dart'; ruta = '/vestidor'
                    carpeta = 'features/vestidor'
                    ops = @() }
        areas = @(
            @{
                k = 'medidas'; cu = 'CU-21'
                vista = @{ n = 'pantalla_medidas.dart'; ruta = '/vestidor/medidas'
                           carpeta = 'features/vestidor'
                           attrs = @('busto_cm', 'cintura_cm', 'cadera_cm', 'altura_cm') }
                form  = @{ n = 'formulario_medidas.dart'
                           carpeta = 'features/vestidor'
                           attrs = @('busto_cm', 'cintura_cm', 'cadera_cm', 'altura_cm') }
                ctrl  = @{ n = 'medidas/router.py'
                           ops = @('ver_mis_medidas', 'guardar_mis_medidas') }
            },
            @{
                k = 'probable'; cu = 'CU-21'
                vista = @{ n = 'pantalla_catalogo.dart'; ruta = '/catalogo?solo_vestidor'
                           carpeta = 'features/catalogo'
                           attrs = @('solo_vestidor', 'busqueda', 'pagina') }
                ctrl  = @{ n = 'catalogo_publico/router.py'
                           ops = @('listar_catalogo', 'ajuste_del_producto') }
            },
            @{
                k = 'derivar'; cu = 'CU-21'
                vista = @{ n = 'pantalla_carrito.dart'; ruta = '/carrito'
                           carpeta = 'features/compra'
                           attrs = @('variante_id', 'cantidad') }
                ctrl  = @{ n = 'ventas/carrito_router.py'
                           ops = @('agregar_al_carrito') }
            }
        )
    },

    # ============ CICLO 1 y 2, rehechos POR CASO DE USO ==================
    #
    # Los siete mapas por actor se quitaron el 20/09. El auxiliar los pide
    # por caso de uso, y ademas un mapa acumulativo por rol crecia hasta ser
    # ilegible: el del Administrador del Ciclo 2 tenia doce areas en un solo
    # lienzo. Estos tres son los recorridos que vale la pena dibujar.

    @{
        actor  = 'Cliente'
        ciclo  = '#1'
        cu     = 'CU-02'
        nombre = '3.2 Diagrama de Navegacion - CU-02 Iniciar y cerrar sesion'
        guarda = '[publica]'
        nota   = 'Navegacion de CU-02, POR CASO DE USO. Extension UWE (no es UML 2.5). Es la unica del capitulo cuya puerta es PUBLICA: /login y /registro no declaran canActivate. Lo que hay que mirar es el <redirect> de salida: el mismo controlador manda a un area distinta segun el rol que traiga el token, y por eso sale una sola flecha hacia el eje.'
        menu   = @{ n = 'login.ts'; ruta = '/login'
                    carpeta = 'features/auth/login'
                    ops = @() }
        areas = @(
            @{
                k = 'acceso'; cu = 'CU-02'; publica = $true
                vista = @{ n = 'login.ts'; ruta = '/login'
                           carpeta = 'features/auth/login'
                           attrs = @('correo', 'contrasena') }
                form  = @{ n = 'login.html'
                           carpeta = 'features/auth/login'
                           attrs = @('correo', 'contrasena') }
                ctrl  = @{ n = 'seguridad/router.py'
                           ops = @('iniciar_sesion', 'cerrar_sesion', 'usuario_autenticado') }
            },
            @{
                k = 'recuperar'; cu = 'CU-41'; publica = $true
                vista = @{ n = 'olvide.ts'; ruta = '/olvide'
                           carpeta = 'features/auth/olvide'
                           attrs = @('correo') }
                form  = @{ n = 'restablecer.ts'
                           carpeta = 'features/auth/restablecer'
                           attrs = @('token', 'contrasena') }
                ctrl  = @{ n = 'seguridad/recuperacion_router.py'
                           ops = @('solicitar_recuperacion', 'confirmar_contrasena') }
            }
        )
    },

    @{
        actor  = 'Cliente'
        ciclo  = '#2'
        cu     = 'CU-17'
        nombre = '3.2 Diagrama de Navegacion - CU-17 Consultar catalogo'
        guarda = '[publica]'
        nota   = 'Navegacion de CU-17, POR CASO DE USO. Extension UWE (no es UML 2.5). Las dos paginas son PUBLICAS y por eso cuelgan del actor y no de un eje con sesion. AQUI SE VE EL DEFECTO DEL 13/09: desde la vitrina se entra a todo, pero una vez con sesion ninguna flecha vuelve a /tienda. El <build> de la grilla y el de la ficha salen del mismo controlador.'
        menu   = @{ n = 'catalogo.ts'; ruta = '/tienda'
                    carpeta = 'features/tienda/catalogo'
                    ops = @() }
        areas = @(
            @{
                k = 'vitrina'; cu = 'CU-17'; publica = $true
                vista = @{ n = 'catalogo.ts'; ruta = '/tienda'
                           carpeta = 'features/tienda/catalogo'
                           attrs = @('busqueda', 'categoria_id', 'talla_id', 'color_id', 'pagina') }
                ctrl  = @{ n = 'catalogo_publico/router.py'
                           ops = @('listar_catalogo', 'maestros_de_la_vitrina') }
            },
            @{
                k = 'ficha'; cu = 'CU-18'; publica = $true
                vista = @{ n = 'ficha.ts'; ruta = '/tienda/producto/:id'
                           carpeta = 'features/tienda/ficha'
                           attrs = @('producto_id', 'talla_id', 'color_id') }
                ctrl  = @{ n = 'catalogo_publico/router.py'
                           ops = @('ficha_de_producto', 'disponibilidad_por_sucursal') }
            }
        )
    },

    @{
        actor  = 'Cliente'
        ciclo  = '#2'
        cu     = 'CU-22'
        nombre = '3.2 Diagrama de Navegacion - CU-22 Crear reserva de prendas'
        guarda = '[sesion + CLIENTE]'
        nota   = 'Navegacion de CU-22, POR CASO DE USO. Extension UWE (no es UML 2.5). El recorrido empieza en la ficha ---publica--- y cruza a la zona con sesion al confirmar: ese cruce es el que obliga a iniciar sesion a mitad del camino. El <redirect> del controlador lleva a `Mis reservas`, no de vuelta a la ficha, porque lo que el cliente quiere ver despues es el codigo de su reserva.'
        menu   = @{ n = 'mis-reservas.ts'; ruta = '/mi-cuenta/reservas'
                    carpeta = 'features/cliente/reservas'
                    ops = @() }
        areas = @(
            @{
                k = 'nueva'; cu = 'CU-22'
                vista = @{ n = 'reserva-formulario.ts'; ruta = '/reservas/nueva'
                           carpeta = 'features/tienda/reservas'
                           attrs = @('sucursal_id', 'fecha', 'franja') }
                form  = @{ n = 'reserva-formulario.html'
                           carpeta = 'features/tienda/reservas'
                           attrs = @('variantes', 'sucursal_id', 'franja_inicio') }
                ctrl  = @{ n = 'reservas/router.py'
                           ops = @('franjas_disponibles', 'crear_reserva') }
            },
            @{
                k = 'mias'; cu = 'CU-23'
                vista = @{ n = 'mis-reservas.ts'; ruta = '/mi-cuenta/reservas'
                           carpeta = 'features/cliente/reservas'
                           attrs = @('estado', 'pagina') }
                ctrl  = @{ n = 'reservas/router.py'
                           ops = @('mis_reservas', 'obtener_reserva', 'cancelar_reserva') }
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
    if ($CU    -and $a.cu    -ne $CU)    { continue }

    # De que arbol salen las pantallas. Por omision la web; CU-21 vive
    # solo en el telefono y decir `frontend-web` ahi seria mentir sobre
    # donde esta el codigo, que es la regla de oro 10.
    $BASE = if ($a.base) { $a.base } else { 'frontend-web/src/app' }
    # Sin -CU no se dibujan los bloques POR CASO DE USO: son muchos y
    # cada uno es su propio diagrama. Se piden de a uno, a proposito.
    if (-not $CU -and $a.cu) { continue }

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
        "Eje de navegacion del actor. $BASE/$($a.menu.carpeta)/. Ruta $($a.menu.ruta)." `
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
                "$($ar.cu). Ruta $($ar.vista.ruta). $BASE/$($ar.vista.carpeta)/$($ar.vista.n) y su .html. Los atributos son los filtros reales del endpoint de listado." `
                (@("ruta: $($ar.vista.ruta)") + $ar.vista.attrs) @()
        }
        if ($ar.form) {
            $ids["$($ar.k)|form"] = NuevaClase $pkg $ar.form.n $EST_FORM `
                "$($ar.cu). $BASE/$($ar.form.carpeta)/$($ar.form.n). Los atributos son los campos reales del formulario." `
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
