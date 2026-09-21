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

    # Los bloques de los Ciclos 1 y 2 se quitaron el 20/09 junto con los
    # diagramas que producian. Los cuatro que vuelven, elegidos con el
    # criterio del auxiliar, estan al final.

    # ================= CICLO 3 =================================
    #
    # PILOTO DEL 20/09. Un solo caso de uso, para revisar el patron antes de
    # escribir los demas.
    #
    # CU-27 es el que mejor justifica un diagrama de tiempo del ciclo: es el
    # UNICO donde una entidad cambia de estado SIN que nadie la toque. El
    # pedido nace apartando stock y, si el pago no llega, la barrida lo
    # expira sola. Eso ---cuanto tarda un estado en cambiar--- es justo lo
    # que este diagrama existe para mostrar, y no se ve en el de estados.
    #
    # Por eso la linea del pedido y la de la existencia NO terminan en el
    # commit como en los CU de gestion: siguen hasta la resolucion.

    @{
        cu = 'CU-27'; ciclo = '#3'; escenario = 'Realizar pedido y pagar en linea'
        nota = "Escenario: el cliente confirma el carrito y el pedido queda esperando el pago. La transaccion cierra en el commit, pero LA VENTA NO: queda PENDIENTE_PAGO hasta que la pasarela confirme (CU-28) o venza el plazo y la barrida devuelva el stock. Las dos ultimas marcas de las lineas 2 y 3 son ese desenlace, fuera de la peticion. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /tienda/pedidos' 'total coincide y sin otro pendiente' 'INSERT venta + detalle_venta' '201' '8 h'),
            @{
                k = 'venta'; n = 'Pedido'; clasificador = 'Venta'
                estados = @('Inexistente', 'PENDIENTE_PAGO', 'PAGADA', 'EXPIRADA')
                marcas = @(
                    @{ t = $T.inicio; s = 'Inexistente';    ev = '';                                  tc = '' },
                    @{ t = $T.commit; s = 'PENDIENTE_PAGO'; ev = 'db.commit()  ';                     tc = 'RNF11' },
                    @{ t = 76;        s = 'PAGADA';         ev = 'webhook firmado  {CU-28}';          tc = '' },
                    @{ t = 84;        s = 'EXPIRADA';       ev = 'nadie pago  {expirar-vencidos}';    tc = '' }
                )
            },
            @{
                k = 'existencia'; n = 'Existencia'; clasificador = 'Existencia'
                estados = @('disponible', 'reservada', 'vendida')
                marcas = @(
                    @{ t = $T.inicio;  s = 'disponible'; ev = '';                              tc = '' },
                    @{ t = $T.escribe; s = 'reservada';  ev = 'apartar_para_reserva()  ';      tc = 'RNF10' },
                    @{ t = 76;         s = 'vendida';    ev = 'salida definitiva  {CU-28}';    tc = 'RNF10' },
                    @{ t = 84;         s = 'disponible'; ev = 'devuelta por la barrida  ';     tc = 'RNF10' }
                )
            }
        )
    },

    @{
        cu = 'CU-28'; ciclo = '#3'; escenario = 'Confirmar el pago del pedido'
        nota = "Escenario: la pasarela avisa que el cobro entro. La linea 1 no arranca autenticando por token sino VALIDANDO LA FIRMA: el que llama es una maquina. Las lineas 2 y 3 muestran el pedido cerrandose y el stock apartado volviendose salida definitiva, las dos en el mismo commit. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /pagos/webhook' 'firma valida y aviso no aplicado' 'UPDATE venta + movimiento_inventario' '200' ''),
            @{
                k = 'venta'; n = 'Pedido'; clasificador = 'Venta'
                estados = @('PENDIENTE_PAGO', 'PAGADA')
                marcas = @(
                    @{ t = $T.inicio; s = 'PENDIENTE_PAGO'; ev = 'creado por CU-27  '; tc = '' },
                    @{ t = $T.commit; s = 'PAGADA';         ev = 'db.commit()  ';      tc = 'RNF11' }
                )
            },
            @{
                k = 'existencia'; n = 'Existencia'; clasificador = 'Existencia'
                estados = @('reservada', 'vendida')
                marcas = @(
                    @{ t = $T.inicio; s = 'reservada'; ev = 'apartada por CU-27  '; tc = '' },
                    @{ t = $T.commit; s = 'vendida';   ev = 'SALIDA registrada  ';   tc = 'RNF10' }
                )
            }
        )
    },

    @{
        cu = 'CU-31'; ciclo = '#3'; escenario = 'Registrar una venta presencial'
        nota = "Escenario: el cajero cobra en el mostrador. La guarda de la linea 1 no es un rol sino el TURNO ABIERTO. La linea 3 es lo que justifica CU-30: el dinero entra a un turno concreto, y por eso al cierre se puede cuadrar. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /pos/ventas' 'turno abierto y existencia suficiente' 'INSERT venta + movimiento_inventario' '201' '8 h'),
            @{
                k = 'existencia'; n = 'Existencia'; clasificador = 'Existencia'
                estados = @('disponible', 'vendida')
                marcas = @(
                    @{ t = $T.inicio;  s = 'disponible'; ev = '';                     tc = '' },
                    @{ t = $T.escribe; s = 'vendida';    ev = 'SALIDA registrada  '; tc = 'RNF10' }
                )
            },
            @{
                k = 'turno'; n = 'Turno de caja'; clasificador = 'TurnoCaja'
                estados = @('Abierto', 'Cerrado')
                marcas = @(
                    @{ t = $T.inicio; s = 'Abierto'; ev = 'abierto por CU-30  '; tc = '' },
                    @{ t = 84;        s = 'Cerrado'; ev = 'arqueo del turno  ';  tc = '1 turno' }
                )
            }
        )
    },

    @{
        cu = 'CU-33'; ciclo = '#3'; escenario = 'Recibir recomendaciones de prendas'
        nota = "Escenario: el cliente abre `Para vos`. ESTE NO USA LA LINEA DE TRANSACCION porque no escribe nada: es una consulta asistida. Lo que hay que mirar es el ancho del tramo `Esperando al modelo`, que es casi todo el tiempo de la peticion --medido entre 3 y 25 segundos--, y el lazo de reintento cuando la validacion deja menos de tres prendas en pie. $LEYENDA"
        lineas = @(
            @{
                k = 'peticion'; n = 'Peticion'; clasificador = ''
                estados = @('Inactiva', 'Reuniendo la senal', 'Esperando al modelo', 'Validando', 'Respondida')
                marcas = @(
                    @{ t = $T.inicio; s = 'Inactiva';           ev = '';                             tc = '' },
                    @{ t = 8;         s = 'Reuniendo la senal'; ev = 'GET /tienda/recomendaciones';  tc = '' },
                    @{ t = 20;        s = 'Esperando al modelo'; ev = 'contexto armado  ';           tc = '3-25 s' },
                    @{ t = 70;        s = 'Validando';          ev = 'el modelo contesta  ';         tc = '' },
                    @{ t = 80;        s = 'Respondida';         ev = 'solo prendas reales  ';        tc = 'RNF02' }
                )
            },
            @{
                k = 'modelo'; n = 'Proveedor de IA'; clasificador = 'ProveedorRecomendador'
                estados = @('Ocioso', 'Generando', 'Saturado')
                marcas = @(
                    @{ t = $T.inicio; s = 'Ocioso';    ev = '';                          tc = '' },
                    @{ t = 20;        s = 'Generando'; ev = 'prompt enviado  ';          tc = '22 s' },
                    @{ t = 62;        s = 'Saturado';  ev = 'sin respuesta a tiempo  ';  tc = 'respaldo' },
                    @{ t = 70;        s = 'Ocioso';    ev = 'contesta el de respaldo  '; tc = '' }
                )
            },
            @{
                k = 'sugerencias'; n = 'Sugerencias'; clasificador = ''
                estados = @('Ninguna', 'Sin validar', 'Utiles')
                marcas = @(
                    @{ t = $T.inicio; s = 'Ninguna';     ev = '';                                tc = '' },
                    @{ t = 70;        s = 'Sin validar'; ev = 'lo que dijo el modelo  ';          tc = '' },
                    @{ t = 80;        s = 'Utiles';      ev = 'activas y con stock  ';            tc = 'min 3' }
                )
            }
        )
    },

    @{
        cu = 'CU-34'; ciclo = '#3'; escenario = 'Conversar con el asistente virtual'
        nota = "Escenario: el cliente hace una pregunta. Es el caso que el auxiliar uso de ejemplo para este diagrama, y aca con los tiempos MEDIDOS del sistema: armar el contexto es barato --tres consultas-- y esperar al modelo es casi toda la espera. La linea 3 muestra lo que define a este caso de uso: la conversacion NUNCA llega a la base. $LEYENDA"
        lineas = @(
            @{
                k = 'peticion'; n = 'Peticion'; clasificador = ''
                estados = @('Inactiva', 'Armando el contexto', 'Esperando al modelo', 'Validando codigos', 'Respondida')
                marcas = @(
                    @{ t = $T.inicio; s = 'Inactiva';            ev = '';                        tc = '' },
                    @{ t = 8;         s = 'Armando el contexto'; ev = 'POST /asistente';         tc = '' },
                    @{ t = 22;        s = 'Esperando al modelo'; ev = 'una sola llamada  ';      tc = '3-25 s' },
                    @{ t = 72;        s = 'Validando codigos';   ev = 'el modelo contesta  ';    tc = '' },
                    @{ t = 82;        s = 'Respondida';          ev = 'solo prendas del catalogo  '; tc = 'RNF02' }
                )
            },
            @{
                k = 'modelo'; n = 'Proveedor de IA'; clasificador = 'ProveedorAsistente'
                estados = @('Ocioso', 'Generando', 'Saturado')
                marcas = @(
                    @{ t = $T.inicio; s = 'Ocioso';    ev = '';                           tc = '' },
                    @{ t = 22;        s = 'Generando'; ev = 'contexto e historial  ';     tc = '22 s' },
                    @{ t = 64;        s = 'Saturado';  ev = 'se agota el tiempo  ';       tc = 'respaldo' },
                    @{ t = 72;        s = 'Ocioso';    ev = 'contesta el de respaldo  ';  tc = '' }
                )
            },
            @{
                k = 'conversacion'; n = 'Conversacion'; clasificador = ''
                estados = @('En la pantalla', 'Perdida')
                marcas = @(
                    @{ t = $T.inicio; s = 'En la pantalla'; ev = 'turnos anteriores  ';         tc = '6 turnos' },
                    @{ t = 82;        s = 'En la pantalla'; ev = 'se agrega el turno nuevo  ';  tc = '' },
                    @{ t = 84;        s = 'Perdida';        ev = 'al recargar  {NO va a la base}'; tc = '' }
                )
            }
        )
    },

    @{
        cu = 'CU-21'; ciclo = '#3'; escenario = 'Probarse una prenda en el vestidor'
        nota = "Escenario: el cliente se prueba una prenda. NO HAY LINEA DE TRANSACCION ni commit: todo ocurre en el telefono y nada se escribe, salvo lo que despues se derive al carrito. La escala aca NO es la de una peticion: es el ciclo de UN FOTOGRAMA, y lo que hay que mirar es que la deteccion y el dibujo entren dentro del cuadro para sostener los 12-20 fps medidos en el prototipo. $LEYENDA"
        lineas = @(
            @{
                k = 'camara'; n = 'Camara frontal'; clasificador = ''
                estados = @('Apagada', 'Pidiendo permiso', 'Transmitiendo')
                marcas = @(
                    @{ t = $T.inicio; s = 'Apagada';          ev = '';                       tc = '' },
                    @{ t = 10;        s = 'Pidiendo permiso'; ev = 'abrir el vestidor  ';    tc = '' },
                    @{ t = 24;        s = 'Transmitiendo';    ev = 'permiso concedido  ';    tc = '12-20 fps' }
                )
            },
            @{
                k = 'pose'; n = 'Deteccion de pose'; clasificador = 'PoseDetector'
                estados = @('Ociosa', 'Analizando', 'Con pose')
                marcas = @(
                    @{ t = $T.inicio; s = 'Ociosa';     ev = '';                        tc = '' },
                    @{ t = 30;        s = 'Analizando'; ev = 'fotograma recibido  ';    tc = 'en el telefono' },
                    @{ t = 52;        s = 'Con pose';   ev = 'hombros y cadera  ';      tc = '' },
                    @{ t = 80;        s = 'Analizando'; ev = 'siguiente fotograma  ';   tc = '' }
                )
            },
            @{
                k = 'prenda'; n = 'Prenda superpuesta'; clasificador = ''
                estados = @('Sin dibujar', 'Dibujada', 'Capturada')
                marcas = @(
                    @{ t = $T.inicio; s = 'Sin dibujar'; ev = '';                          tc = '' },
                    @{ t = 58;        s = 'Dibujada';    ev = 'escalada y rotada  ';       tc = 'PNG alfa' },
                    @{ t = 74;        s = 'Capturada';   ev = 'capturar()  {al telefono}'; tc = '' },
                    @{ t = 84;        s = 'Dibujada';    ev = 'sigue probandose  ';        tc = '' }
                )
            }
        )
    },

    # ============ CICLO 1 y 2, rehechos con el patron nuevo ==============
    #
    # Cuatro, no dieciocho. Un diagrama de tiempo contesta «cuanto tarda un
    # estado en cambiar», y en un alta-baja-modificacion la respuesta es
    # siempre la misma: lo que dura la peticion. Estos cuatro son los del
    # Ciclo 1 y 2 donde el tiempo dice algo que no se ve en otro diagrama.

    @{
        cu = 'CU-02'; ciclo = '#1'; escenario = 'Iniciar sesion y que el token caduque'
        nota = "Escenario: el usuario entra. Lo que justifica el diagrama es la linea 2: el token se emite en el commit y se apaga OCHO HORAS DESPUES sin que nadie haga nada. Es el unico plazo del Ciclo 1 que corre solo, y la escala del dibujo no es la de la peticion sino la de esas ocho horas. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /auth/sesion' 'verify_password y cuenta activa' 'INSERT sesion_token' '200' ''),
            @{
                k = 'token'; n = 'Token de acceso'; clasificador = 'SesionToken'
                estados = @('Inexistente', 'Vigente', 'Revocado', 'Vencido')
                marcas = @(
                    @{ t = $T.inicio; s = 'Inexistente'; ev = '';                          tc = '' },
                    @{ t = $T.commit; s = 'Vigente';     ev = 'emitir()  ';                tc = '8 h' },
                    @{ t = 78;        s = 'Revocado';    ev = 'cerrar sesion  {CU-02}';    tc = '' },
                    @{ t = 84;        s = 'Vencido';     ev = 'se cumplen las 8 h  ';      tc = 'nadie actua' }
                )
            },
            @{
                k = 'acceso'; n = 'Acceso a lo privado'; clasificador = ''
                estados = @('Denegado', 'Permitido')
                marcas = @(
                    @{ t = $T.inicio; s = 'Denegado';  ev = '';                         tc = '' },
                    @{ t = $T.commit; s = 'Permitido'; ev = 'segun el rol del token  '; tc = 'RNF01' },
                    @{ t = 78;        s = 'Denegado';  ev = 'el token deja de valer  '; tc = '' }
                )
            }
        )
    },

    @{
        cu = 'CU-17'; ciclo = '#2'; escenario = 'Consultar el catalogo'
        nota = "Escenario: un visitante navega la vitrina. Es el unico del capitulo donde lo que se mide NO es una transaccion sino un TIEMPO DE RESPUESTA: el RNF02 pide que el catalogo responda rapido, y esta es la unica consulta del sistema que lo compromete. Por eso la linea 1 no tiene fase de escritura ni de commit. $LEYENDA"
        lineas = @(
            @{
                k = 'consulta'; n = 'Consulta'; clasificador = ''
                estados = @('Inactiva', 'Filtrando', 'Paginando', 'Respondida')
                marcas = @(
                    @{ t = $T.inicio; s = 'Inactiva';   ev = '';                            tc = '' },
                    @{ t = 14;        s = 'Filtrando';  ev = 'GET /tienda/productos';       tc = '' },
                    @{ t = 44;        s = 'Paginando';  ev = 'categoria, talla, color  ';   tc = 'indices' },
                    @{ t = 70;        s = 'Respondida'; ev = 'una pagina, nunca todo  ';    tc = 'RNF02' }
                )
            },
            @{
                k = 'precio'; n = 'Precio mostrado'; clasificador = ''
                estados = @('Sin resolver', 'De lista', 'Con descuento')
                marcas = @(
                    @{ t = $T.inicio; s = 'Sin resolver';  ev = '';                              tc = '' },
                    @{ t = 50;        s = 'De lista';      ev = 'minimo de sus variantes  ';     tc = '' },
                    @{ t = 62;        s = 'Con descuento'; ev = 'promocion vigente hoy  {CU-12}'; tc = '' }
                )
            },
            @{
                k = 'imagen'; n = 'Imagen'; clasificador = 'ImagenProducto'
                estados = @('Sin cargar', 'Servida')
                marcas = @(
                    @{ t = $T.inicio; s = 'Sin cargar'; ev = '';                          tc = '' },
                    @{ t = 70;        s = 'Servida';    ev = 'fuera de la aplicacion  ';  tc = 'RNF02' }
                )
            }
        )
    },

    @{
        cu = 'CU-22'; ciclo = '#2'; escenario = 'Crear una reserva y que venza'
        nota = "Escenario: el cliente reserva y no va. Es el antecedente directo de CU-27: el stock se aparta en el commit y vuelve solo cuando la barrida corre. Las lineas 2 y 3 siguen mucho despues de que la peticion termino, que es justo lo que este diagrama muestra y el de estados no. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /reservas' 'franja futura y hay existencia' 'INSERT reserva + reserva_detalle' '201' '8 h'),
            @{
                k = 'reserva'; n = 'Reserva'; clasificador = 'Reserva'
                estados = @('Inexistente', 'PENDIENTE', 'ATENDIDA', 'EXPIRADA')
                marcas = @(
                    @{ t = $T.inicio; s = 'Inexistente'; ev = '';                            tc = '' },
                    @{ t = $T.commit; s = 'PENDIENTE';   ev = 'db.commit()  ';               tc = '24 h' },
                    @{ t = 76;        s = 'ATENDIDA';    ev = 'el encargado la atiende  {CU-24}'; tc = '' },
                    @{ t = 84;        s = 'EXPIRADA';    ev = 'vence la franja  {CU-25}';    tc = 'nadie actua' }
                )
            },
            @{
                k = 'existencia'; n = 'Existencia'; clasificador = 'Existencia'
                estados = @('disponible', 'reservada', 'vendida')
                marcas = @(
                    @{ t = $T.inicio;  s = 'disponible'; ev = '';                            tc = '' },
                    @{ t = $T.escribe; s = 'reservada';  ev = 'apartar_para_reserva()  ';    tc = 'RNF10' },
                    @{ t = 76;         s = 'vendida';    ev = 'se cobra en caja  {CU-31}';   tc = '' },
                    @{ t = 84;         s = 'disponible'; ev = 'liberada por la barrida  ';   tc = 'RNF10' }
                )
            }
        )
    },

    @{
        cu = 'CU-25'; ciclo = '#2'; escenario = 'Expirar una reserva vencida'
        nota = "Escenario: nadie fue a buscar la reserva. ES EL CASO MAS PURO DEL CAPITULO: el unico donde NINGUN actor interviene ---ni siquiera para disparar la peticion, que la lanza el planificador--- y donde el estado cambia solo porque paso el tiempo. La linea 3 es el reloj, y esta para que se vea que la transicion la dispara el, no una persona. $LEYENDA"
        lineas = @(
            (LineaTransaccion 'POST /mantenimiento/reservas/expiracion' 'franja_fin mas la vigencia ya paso' 'UPDATE reserva + movimiento' '200' ''),
            @{
                k = 'reserva'; n = 'Reserva'; clasificador = 'Reserva'
                estados = @('PENDIENTE', 'EXPIRADA')
                marcas = @(
                    @{ t = $T.inicio; s = 'PENDIENTE'; ev = 'creada por CU-22  '; tc = '24 h' },
                    @{ t = $T.commit; s = 'EXPIRADA';  ev = 'db.commit()  ';      tc = 'RNF11' }
                )
            },
            @{
                k = 'reloj'; n = 'Reloj'; clasificador = ''
                estados = @('Dentro de la franja', 'Vencida')
                marcas = @(
                    @{ t = $T.inicio; s = 'Dentro de la franja'; ev = '';                          tc = '' },
                    @{ t = 10;        s = 'Vencida';             ev = 'hora boliviana  ';          tc = 'no UTC' },
                    @{ t = 84;        s = 'Vencida';             ev = 'sigue corriendo  ';         tc = '' }
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
