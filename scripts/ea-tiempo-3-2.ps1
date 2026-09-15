param(
    # Borra el paquete de este capítulo y lo vuelve a generar.
    [switch]$Rehacer,
    # Genera solo este caso de uso (p. ej. -CU CU-03). Vacío = todos.
    [string]$CU = '',
    # Para probar sobre una copia sin tocar el modelo bueno.
    [string]$Modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
)

# =========================================================================
# CAP. 3 - 3.2 DIAGRAMA DE TIEMPO  (uno POR CASO DE USO TRANSACCIONAL)
#
# ---- DE DÓNDE SALE ESTE FORMATO ----
#   Timing diagram de UML 2.5 §17.4, con la forma del ejemplo de cátedra
#   (pág. 10 de «todos los diagramas.pdf», `sd DiagramaTiempo`): una línea
#   de vida con sus estados apilados en el eje Y, el evento rotulado sobre
#   cada escalón, la regla numérica abajo y las RESTRICCIONES DE DURACIÓN
#   `{n}` entre eventos.
#
#   Corrección de la ingeniera del 15/09/2026: va uno por caso de uso
#   TRANSACCIONAL, igual que secuencia y estado.
#
# ---- QUÉ SE MIDE ----
#   La línea de vida principal es LA TRANSACCIÓN: el viaje de una petición
#   por las cuatro capas del backend.
#
#       Inactiva -> Autenticando -> Validando -> Escribiendo -> Confirmada
#
#   Ese reparto no es decorativo: es exactamente el de los diagramas de
#   secuencia de 3.2 (frontera -> controlador -> entidad) y el de las capas
#   de 3.1.1. `Autenticando` es la dependencia `requiere_roles`,
#   `Validando` son los `raise` previos al try, `Escribiendo` es el cuerpo
#   del try y `Confirmada` es el `db.commit()`.
#
#   La SEGUNDA línea de vida solo se pone donde hay algo real que mostrar:
#   un objeto del dominio que cambia de estado en el mismo instante del
#   commit. En los casos de gestión (CU-05, CU-07, CU-08, CU-09, CU-10,
#   CU-11, CU-15, CU-16) no lo hay, y el diagrama va con una sola línea.
#
# ---- LA REGLA ES RELATIVA, Y HAY QUE DECIRLO ----
#   Los números de la regla (0 a 100) son INSTANTES DEL ESCENARIO, no
#   milisegundos medidos. Nadie corrió un perfilador sobre esto. Lo que sí
#   es real es lo que dicen las restricciones `{...}`: salen de una
#   constante del código o de un requisito no funcional. Si en la defensa
#   preguntan por los números de la regla, la respuesta honesta es que son
#   relativos y que lo medible son las restricciones.
#
#   Las debilidades de este diagrama, y qué contestar, están escritas en la
#   §3.4 de docs/diagramas/estado-navegacion-y-tiempo.md.
#
# ---- DE DÓNDE SALE EL CONTENIDO ----
#   backend/app/core/config.py:32          -> ACCESS_TOKEN_EXPIRE_MINUTES,
#     que es 60 * 8 = 8 horas. Es la cota de `{8 h}`.
#   backend/app/core/config.py             -> RESERVA_VIGENCIA_HORAS = 24.
#   backend/app/core/dependencies.py:110   -> requiere_roles.
#   backend/app/modules/<módulo>/service.py -> el bloque try/commit.
#   docs/03-captura-requisitos.md §3.4     -> RNF02 (rendimiento) y RNF11
#     (consistencia transaccional con bloqueo de fila).
#
# ADITIVO: abre el modelo y solo agrega los diagramas que faltan.
# =========================================================================

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }

$NOMBRE_PKG = '3.2 Diagramas de Tiempo'

# ---- Constantes de dibujo (todas juntas, arriba) ----
$X0    = 60     # borde izquierdo de las líneas de vida
# OJO CON EL ANCHO. EA dibuja el rótulo del evento HACIA LA DERECHA del
# instante, y la restricción `{...}` pegada al final del rótulo, sin cortar ni
# envolver. Con la línea de vida angosta, los rótulos consecutivos se pisan y
# el último se sale del marco. 1400 px da ~14 px por unidad de la regla, que
# es lo que necesitan seis marcas con rótulos de esta longitud.
$ANCHO = 1400   # ancho de una línea de vida (la regla se estira a este ancho)
$ALTO  = 210    # alto de una línea de vida
$PASO  = 265    # separación vertical entre líneas de vida
$SIZE  = 38     # alto de una franja de estado dentro de la línea de vida

# Los seis instantes de la transacción, siempre los mismos. Se eligieron para
# que los rótulos no se pisen con $ANCHO = 1400; la última no puede pasar de
# 84 o el texto se sale del marco.
$T = @{ inicio = 0; auth = 12; valida = 30; escribe = 50; commit = 68; fin = 84 }

# =========================================================================
# LA LÍNEA DE LA TRANSACCIÓN
#
# Es idéntica en los dieciocho casos de uso salvo por cuatro textos, así que
# se arma acá en vez de repetirla dieciocho veces. Los rótulos van CORTOS y
# las restricciones a una o dos palabras: EA los pega uno detrás de otro sin
# envolver. Lo que significa cada `{...}` está en la nota del diagrama.
#
# LA RESTRICCIÓN VA SIN LLAVES. Las pone EA al dibujar; si se escriben acá,
# salen dobles: `{{8 h}}`. Y el evento termina en dos espacios porque EA pega
# la restricción sin separación.
# =========================================================================
function LineaTransaccion($endpoint, $guarda, $escritura, $codigo, $tcGuarda) {
    return @{
        k = 'transaccion'; n = 'Transaccion'; clasificador = ''
        estados = @('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
        marcas = @(
            @{ t = $T.inicio;  s = 'Inactiva';     ev = '';                          tc = '' },
            @{ t = $T.auth;    s = 'Autenticando'; ev = $endpoint;                   tc = '' },
            @{ t = $T.valida;  s = 'Validando';    ev = "$guarda  ";                 tc = $tcGuarda },
            @{ t = $T.escribe; s = 'Escribiendo';  ev = $escritura;                  tc = '' },
            @{ t = $T.commit;  s = 'Confirmada';   ev = "db.commit() -> $codigo  ";  tc = 'RNF11' },
            @{ t = $T.fin;     s = 'Inactiva';     ev = 'respuesta enviada  ';       tc = 'RNF02' }
        )
    }
}

# Leyenda común de las restricciones, para la nota de cada diagrama.
$LEYENDA = 'LEYENDA: {8 h} = ACCESS_TOKEN_EXPIRE_MINUTES (core/config.py:32), la vida del token; {RNF11} = la fila queda bloqueada desde el UPDATE hasta el commit; {RNF02} = el tiempo de respuesta debe ser adecuado. La regla es RELATIVA: instantes del escenario, no milisegundos medidos.'

# =========================================================================
# LOS DATOS: un bloque por caso de uso transaccional.
#
#   Un diagrama de tiempo cuenta UN escenario, no el caso de uso entero.
#   Se elige el escenario donde el reloj MANDA; el resto ya lo cuentan los
#   diagramas de secuencia.
# =========================================================================
$CASOS = @(

    # ================= CICLO 1 =================================

    @{
        cu = 'CU-01'; ciclo = '#1'; escenario = 'Registrar un cliente'
        nota = "Escenario: un visitante crea su cuenta. No hay fase de autenticacion previa: la vitrina es publica, asi que `Autenticando` es solo la recepcion de la peticion. La segunda linea muestra la fila de usuario apareciendo en el instante del commit. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /auth/registro' 'correo y documento libres' 'INSERT usuario + cliente' '201' ''),
            @{
                k = 'usuario'; n = 'Usuario'; clasificador = 'Usuario'
                estados = @('Inexistente', 'Activo')
                marcas = @(
                    @{ t = $T.inicio; s = 'Inexistente'; ev = '';                          tc = '' },
                    @{ t = $T.commit; s = 'Activo';      ev = 'la fila existe y puede iniciar sesion'; tc = '' }
                )
            }
        )
    },

    @{
        cu = 'CU-02'; ciclo = '#1'; escenario = 'Iniciar sesion'
        nota = "Escenario: un usuario se autentica y recibe su token. Es el CU donde nace el reloj de todo el sistema: la restriccion {8 h} de la segunda linea es la que despues aparece en CU-03 y CU-06 como el plazo que la revocacion se adelanta. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /auth/sesion' 'verify_password y cuenta activa' 'INSERT sesion_token' '200' ''),
            @{
                k = 'token'; n = 'SesionToken'; clasificador = 'SesionToken'
                estados = @('Inexistente', 'Vigente')
                marcas = @(
                    @{ t = $T.inicio; s = 'Inexistente'; ev = '';              tc = '' },
                    @{ t = $T.commit; s = 'Vigente';     ev = 'emitir()  ';    tc = '8 h' }
                )
            }
        )
    },

    @{
        cu = 'CU-03'; ciclo = '#1'; escenario = 'Desactivar una cuenta'
        nota = "Escenario: el Administrador desactiva una cuenta. Se elige este y no el alta porque es el unico del CU donde el reloj es requisito: sin revocar las sesiones, el token del desactivado seguiria valiendo hasta 8 h. Las dos lineas escalonan en el MISMO instante, y eso es lo que el diagrama tiene que hacer ver. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'PATCH /usuarios/:id/estado' 'requiere_roles(ADMINISTRADOR)' 'revocar_sesiones_de_usuario()' '200' '8 h'),
            @{
                k = 'token'; n = 'SesionToken'; clasificador = 'SesionToken'
                estados = @('Vigente', 'Revocado')
                marcas = @(
                    @{ t = $T.inicio; s = 'Vigente';  ev = 'emitir()  {CU-02}';              tc = '' },
                    @{ t = $T.commit; s = 'Revocado'; ev = 'revocar_sesiones_de_usuario()  '; tc = '8 h' }
                )
            }
        )
    },

    @{
        cu = 'CU-04'; ciclo = '#1'; escenario = 'Cambiar la contrasena'
        nota = "Escenario: el Cliente cambia su contrasena. De las cinco ramas del CU es la unica con algo que medir: la comprobacion de la contrasena actual es bcrypt, que por diseno es LENTO, y por eso `Validando` es el tramo mas largo de la transaccion. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /perfil/contrasena' 'verify_password(actual)' 'UPDATE usuario.hash_contrasena' '204' '8 h')
        )
    },

    @{
        cu = 'CU-05'; ciclo = '#1'; escenario = 'Crear una sucursal'
        nota = "Escenario: el Administrador da de alta una sucursal. Una sola linea de vida: ninguna entidad del dominio cambia de estado, solo aparece una fila. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /organizacion/sucursales' 'nombre libre y horario valido' 'INSERT sucursal' '201' '8 h')
        )
    },

    @{
        cu = 'CU-06'; ciclo = '#1'; escenario = 'Dar de baja un empleado'
        nota = "Escenario: el Administrador da de baja a un empleado. Mismo efecto de reloj que CU-03: la baja revoca las sesiones vigentes del empleado en el instante del commit, en vez de esperar a que el token venza. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /organizacion/empleados/:id/baja' 'no estaba de baja y fecha valida' 'UPDATE empleado + revocar sesiones' '200' '8 h'),
            @{
                k = 'token'; n = 'SesionToken'; clasificador = 'SesionToken'
                estados = @('Vigente', 'Revocado')
                marcas = @(
                    @{ t = $T.inicio; s = 'Vigente';  ev = 'emitir()  {CU-02}';              tc = '' },
                    @{ t = $T.commit; s = 'Revocado'; ev = 'revocar_sesiones_de_usuario()  '; tc = '8 h' }
                )
            }
        )
    },

    @{
        cu = 'CU-07'; ciclo = '#1'; escenario = 'Habilitar el acceso de un proveedor'
        nota = "Escenario: el Administrador le crea al proveedor su usuario con rol PROVEEDOR. Dos filas en la misma transaccion: el usuario y el vinculo con la ficha. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /organizacion/proveedores/:id/acceso' 'sin acceso previo y correo libre' 'INSERT usuario + UPDATE proveedor' '200' '8 h')
        )
    },

    @{
        cu = 'CU-08'; ciclo = '#1'; escenario = 'Crear una categoria'
        nota = "Escenario: el Administrador agrega una categoria al arbol. `Validando` incluye la consulta recursiva que comprueba que el padre elegido no sea descendiente: el bucle corre en el motor, no en Python. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /catalogo/categorias' 'nombre libre y sin ciclo' 'INSERT categoria' '201' '8 h')
        )
    },

    @{
        cu = 'CU-09'; ciclo = '#1'; escenario = 'Crear una temporada'
        nota = "Escenario: el Administrador da de alta una temporada. `Validando` comprueba que el rango de fechas no se cruce con otra temporada activa; es la unica validacion del Ciclo 1 que mira el calendario. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /catalogo/temporadas' 'rango valido y sin solapamiento' 'INSERT temporada' '201' '8 h')
        )
    },

    # ================= CICLO 2 =================================

    @{
        cu = 'CU-10'; ciclo = '#2'; escenario = 'Generar las variantes de un producto'
        nota = "Escenario: el Administrador genera el producto cartesiano de tallas por colores. Es la escritura mas grande del Ciclo 2 en una sola transaccion --un producto de 6 tallas por 5 colores son 30 filas-- y por eso `Escribiendo` es el tramo largo. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /catalogo/productos/:id/variantes/generar' 'maestros existentes y SKU valido' 'INSERT variante_producto x N' '201' '8 h')
        )
    },

    @{
        cu = 'CU-11'; ciclo = '#2'; escenario = 'Subir una imagen de producto'
        nota = "Escenario: el Administrador sube una imagen. UNICO caso de uso con dos destinos en la misma operacion: el archivo va al almacen de objetos y la fila a la base. `Escribiendo` incluye la subida del archivo, que es lo que lo hace el tramo mas largo de todos. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /catalogo/productos/:id/imagenes' 'formato valido y producto existente' 'subir al almacen + INSERT imagen' '201' '8 h')
        )
    },

    @{
        cu = 'CU-13'; ciclo = '#2'; escenario = 'Registrar un ingreso de mercaderia'
        nota = "Escenario: el Encargado registra un ingreso. La segunda linea es la existencia de la sucursal, que pasa de estar bajo el minimo a tener stock en el instante del commit. El bloqueo de fila de RNF11 dura todo el tramo `Escribiendo`. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /inventario/ingresos' 'proveedor activo y variantes validas' '_aplicar_movimiento() x N' '201' '8 h'),
            @{
                k = 'existencia'; n = 'Existencia'; clasificador = 'Existencia'
                estados = @('bajo minimo', 'con stock')
                marcas = @(
                    @{ t = $T.inicio; s = 'bajo minimo'; ev = '';                      tc = '' },
                    @{ t = $T.commit; s = 'con stock';   ev = 'INGRESO aplicado  ';    tc = 'RNF10' }
                )
            }
        )
    },

    @{
        cu = 'CU-15'; ciclo = '#2'; escenario = 'Registrar una transferencia'
        nota = "Escenario: el Encargado transfiere unidades entre sucursales. Son DOS movimientos --una salida y una entrada-- en una sola transaccion, con las dos filas de existencia bloqueadas a la vez: es el caso donde RNF11 mas se nota. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /inventario/movimientos/transferencia' 'hay stock en el origen' 'dos movimientos, una transaccion' '201' '8 h')
        )
    },

    @{
        cu = 'CU-16'; ciclo = '#2'; escenario = 'Fijar el stock minimo'
        nota = "Escenario: el Encargado fija el minimo de una existencia de su sucursal. El ambito sale del token, no del pedido: por eso `Autenticando` es aqui mas que un tramite. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'PATCH /inventario/existencias/:id/stock-minimo' 'la existencia es de su sucursal' 'UPDATE existencia.stock_minimo' '200' '8 h')
        )
    },

    @{
        cu = 'CU-22'; ciclo = '#2'; escenario = 'Crear una reserva'
        nota = "Escenario: el Cliente reserva prendas. La segunda linea muestra el precio de la reserva: la existencia queda RETENIDA desde el commit, y no vuelve a estar disponible hasta CU-23 o CU-25. Aqui empieza el reloj de 24 h. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /reservas' 'franja valida y vestidor libre' 'INSERT reserva + apartar()' '201' '8 h'),
            @{
                k = 'existencia'; n = 'Existencia'; clasificador = 'Existencia'
                estados = @('disponible', 'reservada')
                marcas = @(
                    @{ t = $T.inicio; s = 'disponible'; ev = '';                       tc = '' },
                    @{ t = $T.commit; s = 'reservada';  ev = 'apartar_para_reserva()  '; tc = '24 h' }
                )
            }
        )
    },

    @{
        cu = 'CU-23'; ciclo = '#2'; escenario = 'Cancelar una reserva'
        nota = "Escenario: el Cliente cancela. Es el reverso exacto de CU-22: la existencia vuelve a estar disponible en el instante del commit, con un movimiento LIBERACION que deja rastro (RNF10). $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /reservas/:id/cancelacion' 'es su reserva y sigue viva' 'liberar_de_reserva()' '200' '8 h'),
            @{
                k = 'existencia'; n = 'Existencia'; clasificador = 'Existencia'
                estados = @('reservada', 'disponible')
                marcas = @(
                    @{ t = $T.inicio; s = 'reservada';  ev = 'apartar()  {CU-22}';        tc = '' },
                    @{ t = $T.commit; s = 'disponible'; ev = 'LIBERACION registrada  ';   tc = 'RNF10' }
                )
            }
        )
    },

    @{
        cu = 'CU-24'; ciclo = '#2'; escenario = 'Atender una reserva'
        nota = "Escenario: el cliente llega y el Encargado registra el resultado de cada prenda. Aqui la reserva se cierra por un EVENTO --que el cliente aparezca--, no por un plazo; el plazo es el de CU-25. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /sucursal/reservas/:id/atencion' 'viva y todas las prendas marcadas' 'UPDATE reserva + detalles' '200' '8 h'),
            @{
                k = 'reserva'; n = 'Reserva'; clasificador = 'Reserva'
                estados = @('PENDIENTE', 'ATENDIDA')
                marcas = @(
                    @{ t = $T.inicio; s = 'PENDIENTE'; ev = 'crearReserva()  {CU-22}';   tc = '' },
                    @{ t = $T.commit; s = 'ATENDIDA';  ev = 'atenderReserva()  ';        tc = '24 h' }
                )
            }
        )
    },

    @{
        cu = 'CU-25'; ciclo = '#2'; escenario = 'Expirar una reserva vencida'
        nota = "EL DIAGRAMA DE TIEMPO DEL SISTEMA. Es el unico sitio donde la duracion es un REQUISITO y no un adorno: la reserva vence a las RESERVA_VIGENCIA_HORAS (24 h) de franja_fin, y hasta ese instante la existencia queda retenida sin vender. La regla va aqui en ESCALA DE HORAS, no de milisegundos: 0 es la creacion de la reserva y 68 el corte. La tarea programada solo actua al final, y por eso su linea esta plana casi todo el diagrama. $LEYENDA"
        lineas = @(
            @{
                k = 'transaccion'; n = 'Transaccion'; clasificador = ''
                estados = @('Inactiva', 'Validando', 'Escribiendo', 'Confirmada')
                marcas = @(
                    @{ t = 0;  s = 'Inactiva';    ev = '';                          tc = '' },
                    @{ t = 56; s = 'Validando';   ev = 'buscar vencidas  ';          tc = '24 h' },
                    @{ t = 62; s = 'Escribiendo'; ev = 'liberar_de_reserva()';       tc = '' },
                    @{ t = 68; s = 'Confirmada';  ev = 'db.commit()  ';              tc = 'RNF11' },
                    @{ t = 80; s = 'Inactiva';    ev = 'tarea terminada';            tc = '' }
                )
            },
            @{
                k = 'reserva'; n = 'Reserva'; clasificador = 'Reserva'
                estados = @('PENDIENTE', 'EXPIRADA')
                marcas = @(
                    @{ t = 0;  s = 'PENDIENTE'; ev = 'crearReserva()  {CU-22}'; tc = '' },
                    @{ t = 68; s = 'EXPIRADA';  ev = 'expirar()  {CU-25}  ';    tc = '24 h' }
                )
            },
            @{
                k = 'existencia'; n = 'Existencia'; clasificador = 'Existencia'
                estados = @('reservada', 'disponible')
                marcas = @(
                    @{ t = 0;  s = 'reservada';  ev = 'apartar()  {CU-22}';      tc = '' },
                    @{ t = 68; s = 'disponible'; ev = 'LIBERACION registrada  '; tc = 'RNF10' }
                )
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

foreach ($caso in $CASOS) {
    if ($CU -and $caso.cu -ne $CU) { continue }

    $NOMBRE_DIA = "3.2 Diagrama de Tiempo - $($caso.cu) $($caso.escenario) - CICLO $($caso.ciclo)"
    if (BuscarDiagrama $pkg $NOMBRE_DIA) {
        Write-Output "  $NOMBRE_DIA ya existe, no se toca"
        continue
    }

    $dia = $pkg.Diagrams.AddNew($NOMBRE_DIA, 'Timing')
    $dia.Notes = $caso.nota
    [void]$dia.Update(); $pkg.Diagrams.Refresh()

    # Las clases del modelo de dominio, para enlazar la línea de vida con su
    # clasificador: así, si se renombra la clase, se renombra la línea de vida.
    # `Transaccion` NO es una clase del dominio y va sin clasificador: es la
    # petición en curso, no una fila de la base. Está asumido y explicado en la
    # §3.4 de docs/diagramas/estado-navegacion-y-tiempo.md.
    $clasePorNombre = @{}
    foreach ($nom in ($caso.lineas | ForEach-Object { $_.clasificador })) {
        if (-not $nom) { continue }
        if ($clasePorNombre.ContainsKey($nom)) { continue }
        $r = $ea.SQLQuery("SELECT TOP 1 Object_ID FROM t_object WHERE Object_Type='Class' AND Name='$nom' ORDER BY Object_ID")
        if ($r -match '<Object_ID>(\d+)</Object_ID>') { $clasePorNombre[$nom] = [int]$Matches[1] }
        else { Write-Output "  AVISO: no hay clase '$nom' en el modelo; la linea de vida va sin clasificador" }
    }

    # ---- Las líneas de vida. Se guarda el ID, NUNCA la referencia COM.
    $id = @{}
    foreach ($lv in $caso.lineas) {
        $el = $pkg.Elements.AddNew($lv.n, 'TimeLine')
        $el.Alias = $caso.cu
        if ($lv.clasificador -and $clasePorNombre.ContainsKey($lv.clasificador)) {
            # Con el clasificador puesto EA rotula la linea de vida ": SesionToken"
            # y el vinculo queda vivo. El nombre propio se deja VACIO o EA lo
            # escribe dos veces.
            $el.ClassifierID = $clasePorNombre[$lv.clasificador]
            $el.Name = ''
        }
        [void]$el.Update()
        $id[$lv.k] = $el.ElementID

        # Las franjas del eje Y. OJO: Partitions.AddNew PERSISTE SOLO (no tiene
        # Update() propio y la colección vuelve a leerse en 0), así que correr
        # esto dos veces sobre el MISMO elemento duplica las franjas. Por eso el
        # elemento se crea nuevo en cada corrida.
        foreach ($nom in $lv.estados) {
            $part = $el.Partitions.AddNew($nom, '')
            $part.Name = $nom
            $part.Size = $SIZE
        }
        [void]$el.Update()

        # Las transiciones: estado + instante. TxTime va en la escala de la regla.
        foreach ($m in $lv.marcas) {
            $tr = $el.StateTransitions.AddNew($m.s, '')
            $tr.TxState = $m.s
            $tr.TxTime  = $m.t
            $tr.Event   = $m.ev
            if ($m.tc) { $tr.TimeConstraint = $m.tc }
        }
        [void]$el.Update()
    }
    $pkg.Elements.Refresh()

    # ---- al lienzo
    $y = -50
    foreach ($lv in $caso.lineas) {
        [void](Poner $dia $id[$lv.k] $X0 $y $ANCHO $ALTO)
        $y -= $PASO
    }

    $dia.DiagramObjects.Refresh()
    $huerfanos = $ea.SQLQuery("SELECT COUNT(*) AS n FROM t_diagramobjects WHERE Diagram_ID=$($dia.DiagramID) AND Object_ID=0")
    $marcas = ($caso.lineas | ForEach-Object { $_.marcas.Count } | Measure-Object -Sum).Sum
    Write-Output "  $($caso.cu) : $($dia.DiagramObjects.Count) lineas de vida, $marcas marcas"
    if ($huerfanos -match '<n>([1-9]\d*)</n>') { Write-Output "  AVISO: $($Matches[1]) objetos con Object_ID=0" }
    $hechos++
}

Write-Output "  $hechos diagrama(s) generado(s)"
$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Write-Output 'OK'
