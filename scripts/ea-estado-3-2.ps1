param(
    # Borra el paquete de este capítulo y lo vuelve a generar.
    [switch]$Rehacer,
    # Genera solo este caso de uso (p. ej. -CU CU-03). Vacío = todos.
    [string]$CU = '',
    # Para probar sobre una copia sin tocar el modelo bueno.
    [string]$Modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
)

# =========================================================================
# CAP. 3 - 3.2 DIAGRAMA DE ESTADO  (uno POR CASO DE USO TRANSACCIONAL)
#
# ---- DE DÓNDE SALE ESTE FORMATO ----
#   Del ejemplo de cátedra, pág. 10 de «todos los diagramas.pdf», titulado
#   `CU1`. OJO: NO es el ciclo de vida de un objeto. Es el FLUJO DE UNA
#   TRANSACCIÓN, y va uno por caso de uso transaccional:
#
#       Inicio -> Autenticar -> Seleccionar operacion
#              -[listar|crear|modificar|eliminar]-> ... -> Transaccion
#              completada -> Fin
#
#   Los estados son ACTIVIDADES de la transacción (capturar, validar,
#   escribir), no valores de una columna. Las guardas son las condiciones
#   reales que evalúa el código, entre corchetes, y el estado sumidero
#   siempre es `Transaccion completada` seguido del estado final.
#
#   Corrección de la ingeniera del 15/09/2026: estado, tiempo y secuencia se
#   hacen SOLO de los casos de uso transaccionales, en los tres ciclos.
#   Quedan fuera las consultas puras (en el Ciclo 2: CU-14, CU-17, CU-18 y
#   CU-19).
#
# ---- DE DÓNDE SALE EL CONTENIDO ----
#   backend/app/modules/<módulo>/service.py -> cada `raise` es una guarda de
#     rechazo y cada `db.commit()` es la llegada a `Transaccion completada`.
#   backend/app/modules/<módulo>/router.py  -> el endpoint que dispara cada
#     rama del menú de operaciones.
#   backend/app/core/dependencies.py:110    -> `requiere_roles`, que es la
#     guarda del primer estado en todos los CU con sesión.
#
#   LAS RUTAS SE ESCRIBEN SIN EL PREFIJO `/api/v1`, que lo llevan todas
#   (core/config.py:19). Va dicho en la nota de cada diagrama.
#
# ---- EN QUÉ SE APARTA DEL EJEMPLO, Y POR QUÉ ----
#   1. Cada rótulo lleva su ancla al código entre llaves ({service.py:374},
#      {POST /usuarios}). El ejemplo no las tiene; acá sí, porque es lo que
#      hace defendible el diagrama: se puede abrir el archivo y mostrar la
#      línea.
#   2. El ejemplo repite `[correcto]`/`[incorrecto]` sin decir qué compara.
#      Acá la guarda es la condición literal del `if` que la produce.
#   3. Los rechazos van a UN sumidero (`Informar error`) y vuelven al menú
#      por UNA sola flecha. Si cada uno volviera por su cuenta al estado que
#      lo produjo, habría dos flechas entre las mismas dos cajas y EA
#      escribiría los dos rótulos en el mismo punto medio.
#
# ADITIVO: abre el modelo y solo agrega los diagramas que faltan.
# =========================================================================

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }

$NOMBRE_PKG = '3.2 Diagramas de Estado'

# ---- Constantes de dibujo (todas juntas, arriba) ----
$W_EST   = 230; $H_EST  = 60       # caja de estado
$W_NODO  = 30;  $H_NODO = 30       # pseudoestado inicial / estado final
$SUB_INI = 100                     # StateNode.Subtype = pseudoestado inicial
$SUB_FIN = 101                     # StateNode.Subtype = estado final

# LAS POSICIONES NO SE ESCRIBEN A MANO. Cada estado declara su COLUMNA y su
# FILA, y el generador calcula l y t. Con dieciocho casos de uso, poner las
# coordenadas una por una era garantía de error.
#
# El hueco entre `menu` y `oper` tiene que ser el más ancho de todos: por ahí
# salen las cinco flechas del menú de operaciones y ahí se dibujan sus
# rótulos, que son los más largos del diagrama.
$COL = @{ auth = 120; menu = 520; oper = 1120; vali = 1620; fin = 2080 }
$Y0    = -40                       # fila 0
$PASO  = 180                       # alto de una fila

# =========================================================================
# LOS DATOS: un bloque por caso de uso transaccional.
#
#   estados      -> n (nombre), col, fila (admite medios: 1.5), nota
#   transiciones -> d (desde), h (hasta), e (rótulo: guarda + ancla al código)
#
#   '(inicial)', '(final)' y '(final-rechazo)' son los pseudoestados; se
#   crean solos y se colocan solos. El de rechazo solo si alguien lo usa.
# =========================================================================

# Atajo: casi todos los CU de gestión terminan igual.
# Misma razón que la del sumidero de errores, un piso más abajo: con el cierre
# en la fila 2, el conector `oper/3 -> fin` comparte punto medio con el
# `Validar -> Informar error`, que es vertical y cae en la misma x. El medio
# punto los separa.
$FIN_OK = @{ n = 'Transaccion completada'; col = 'fin'; fila = 2.5
             nota = 'Es el db.commit() del bloque try/except de cada rama.' }
# La fila 3.5 no es capricho. `Informar error` vuelve al menú, y ese conector
# tiene su punto medio a media altura entre los dos. Con el error en la fila 3
# ese punto medio cae EXACTAMENTE sobre el de la rama `menu -> oper/3`, y los
# dos rótulos se dibujan encimados. El medio punto los separa 45 px.
$ERR    = @{ n = 'Informar error'; col = 'vali'; fila = 3.5
             nota = 'Sumidero de los rechazos. Es el _traducir() del router, que convierte cada error de gestion en su HTTPException.' }

$CASOS = @(

    # Los bloques de los Ciclos 1 y 2 se quitaron el 20/09: produjeron los
    # 43 diagramas que se descartaron por estar mal, y dejarlos vivos
    # reintroducia duplicados de CU-02, CU-22 y CU-25. Los que vuelven,
    # rehechos con el patron nuevo, estan al final.

    # ================= CICLO 3 =================================
    #
    # PILOTO DEL 20/09. Un solo caso de uso, para revisar que el patron sirve
    # tal cual antes de escribir los demas del ciclo.
    #
    # Se eligio CU-27 porque tiene la maquina de estados mas rica del ciclo
    # ---y porque cubre de una vez tres de los seis procesos que el auxiliar
    # nombra: venta, compra y pagos---. A diferencia de los CU de gestion del
    # Ciclo 1, aca la transaccion NO termina en el commit: el pedido queda
    # PENDIENTE_PAGO y su estado final lo decide otro actor ---la pasarela,
    # en CU-28--- o el paso del tiempo.

    @{
        cu = 'CU-27'; ciclo = '#3'; titulo = 'Realizar pedido y pagar en linea'
        nota = 'Flujo transaccional de CU-27. OJO: el commit NO es el final. El pedido nace PENDIENTE_PAGO y se resuelve por CU-28 (pago confirmado), por cancelacion del cliente o por la barrida de vencidos. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Revisar el carrito'; col = 'auth'; fila = 1
               nota = 'features/tienda/checkout. Exige sesion de CLIENTE.' },
            @{ n = 'Elegir entrega y sucursal'; col = 'menu'; fila = 1
               nota = 'GET /tienda/pedidos/opciones dice que sucursal puede abastecerlo completo.' },
            @{ n = 'Validar total y pendiente'; col = 'vali'; fila = 0.5
               nota = 'Bloquea la fila del CLIENTE antes de mirar: una consulta sin filas no bloquea nada.' },
            @{ n = 'Apartar stock'; col = 'oper'; fila = 1.5
               nota = 'Reusa apartar_para_reserva de P4, con FOR UPDATE por variante.' },
            @{ n = 'Crear venta PENDIENTE_PAGO'; col = 'oper'; fila = 2.5
               nota = 'Congela los precios en detalle_venta y vacia el carrito.' },
            @{ n = 'Esperando el pago'; col = 'fin'; fila = 1.5
               nota = 'Aca termina CU-27. El estado siguiente no lo decide el cliente.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 3.5
               nota = 'Sumidero de los rechazos: 409 total desactualizado, 409 ya hay pendiente, 409 ninguna sucursal completa.' },
            @{ n = 'Liberar stock apartado'; col = 'oper'; fila = 4
               nota = 'Cancelacion del cliente o barrida de vencidos. Sin esto, apartar seria un defecto.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 3.5
               nota = 'El pedido queda resuelto: pagado por CU-28, cancelado o expirado.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Revisar el carrito'; e = '' },
            @{ d = 'Revisar el carrito'; h = 'Elegir entrega y sucursal'
               e = '[el cliente decide comprar]  {GET /tienda/pedidos/opciones}' },
            @{ d = 'Elegir entrega y sucursal'; h = 'Validar total y pendiente'
               e = '[confirmar]  {POST /tienda/pedidos}' },
            @{ d = 'Validar total y pendiente'; h = 'Apartar stock'
               e = '[total coincide y no hay otro pendiente]' },
            @{ d = 'Validar total y pendiente'; h = 'Informar error'
               e = '[total desactualizado / ya hay pendiente / ninguna completa]  {409}' },
            @{ d = 'Apartar stock'; h = 'Crear venta PENDIENTE_PAGO'
               e = '[hay existencia en la sucursal elegida]  {FOR UPDATE por variante}' },
            @{ d = 'Apartar stock'; h = 'Informar error'
               e = '[existencia insuficiente]  {409}' },
            @{ d = 'Crear venta PENDIENTE_PAGO'; h = 'Esperando el pago'
               e = '{db.commit() -> 201 y URL de la pasarela}' },
            @{ d = 'Esperando el pago'; h = 'Transaccion completada'
               e = '[la pasarela confirma]  {CU-28: POST /pagos/webhook}' },
            @{ d = 'Esperando el pago'; h = 'Liberar stock apartado'
               e = '[el cliente cancela]  {POST /tienda/pedidos/:codigo/cancelar}' },
            @{ d = 'Esperando el pago'; h = 'Liberar stock apartado'
               e = '[vence el plazo sin pago]  {POST /pedidos/expirar-vencidos}' },
            @{ d = 'Liberar stock apartado'; h = 'Transaccion completada'
               e = '{el stock vuelve a disponible}' },
            @{ d = 'Informar error'; h = 'Revisar el carrito'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-21'; ciclo = '#3'; titulo = 'Utilizar vestidor virtual (RA)'
        nota = 'Flujo de CU-21. El unico del ciclo que NO escribe en la base: todo ocurre en el telefono, y lo unico que persiste es lo que se derive al carrito o a la reserva. Por eso no hay estado de commit.'
        estados = @(
            @{ n = 'Abrir el vestidor'; col = 'auth'; fila = 1
               nota = 'mobile/lib/features/vestidor/pantalla_vestidor.dart. Desde la ficha o desde el menu.' },
            @{ n = 'Pedir permiso de camara'; col = 'menu'; fila = 0.5
               nota = 'permission_handler. La camara FRONTAL: es la que sirve para probarse solo.' },
            @{ n = 'Detectar la pose'; col = 'oper'; fila = 0
               nota = 'google_mlkit_pose_detection sobre los fotogramas. Corre EN EL TELEFONO.' },
            @{ n = 'Superponer la prenda'; col = 'oper'; fila = 1.5
               nota = 'pintor_prenda.dart: escala por hombros, ubica y rota siguiendo hombros y cadera.' },
            @{ n = 'Capturar la imagen'; col = 'oper'; fila = 3
               nota = 'Se guarda en el telefono. Nada viaja al servidor.' },
            @{ n = 'Derivar al carrito o la reserva'; col = 'fin'; fila = 2.5
               nota = 'Lo unico que persiste de todo el caso de uso.' },
            @{ n = 'Informar que no se puede probar'; col = 'vali'; fila = 3.5
               nota = 'Sin permiso, sin PNG transparente o sin cuerpo detectado.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Abrir el vestidor'; e = '' },
            @{ d = 'Abrir el vestidor'; h = 'Pedir permiso de camara'; e = '[el cliente elige probarse]' },
            @{ d = 'Pedir permiso de camara'; h = 'Detectar la pose'; e = '[permiso concedido]' },
            @{ d = 'Pedir permiso de camara'; h = 'Informar que no se puede probar'
               e = '[permiso denegado]  {no se insiste}' },
            @{ d = 'Detectar la pose'; h = 'Superponer la prenda'
               e = '[hay un cuerpo en el cuadro]  {hombros y cadera}' },
            @{ d = 'Detectar la pose'; h = 'Informar que no se puede probar'
               e = '[no se detecta un cuerpo]' },
            @{ d = 'Superponer la prenda'; h = 'Superponer la prenda'
               e = 'cambiarTallaOColor()  [en vivo, sin consultar al servidor]' },
            @{ d = 'Superponer la prenda'; h = 'Informar que no se puede probar'
               e = '[la variante no tiene PNG transparente]' },
            @{ d = 'Superponer la prenda'; h = 'Capturar la imagen'; e = 'capturar()' },
            @{ d = 'Capturar la imagen'; h = 'Derivar al carrito o la reserva'
               e = '[el cliente decide llevarla]  {CU-26 o CU-22}' },
            @{ d = 'Informar que no se puede probar'; h = 'Abrir el vestidor'; e = 'probar otra prenda()' },
            @{ d = 'Derivar al carrito o la reserva'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-28'; ciclo = '#3'; titulo = 'Confirmar pago del pedido'
        nota = 'Flujo transaccional de CU-28. Lo INICIA UNA MAQUINA, no una persona: la pasarela llama al webhook. Por eso la guarda de entrada no es un token sino la firma, y por eso este caso de uso no deja asiento en la bitacora. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Recibir la notificacion'; col = 'auth'; fila = 1
               nota = 'POST /pagos/webhook. Sin sesion: el que llama es el cobrador.' },
            @{ n = 'Validar la firma'; col = 'vali'; fila = 0
               nota = 'Antes de LEER el contenido. Un webhook sin verificar deja a cualquiera marcar pedidos como pagados.' },
            @{ n = 'Buscar la transaccion y la venta'; col = 'menu'; fila = 1.5
               nota = 'transaccion_pasarela -> venta.' },
            @{ n = 'Comprobar si ya se aplico'; col = 'vali'; fila = 1.5
               nota = 'Las pasarelas reintentan. Sin esto se descuenta el inventario dos veces.' },
            @{ n = 'Marcar la venta PAGADA'; col = 'oper'; fila = 1.5
               nota = 'Es el unico lugar del sistema que mueve una venta a PAGADA.' },
            @{ n = 'Descontar inventario y emitir comprobante'; col = 'oper'; fila = 2.5
               nota = 'El apartado se vuelve salida definitiva, con su movimiento inmutable.' },
            @{ n = 'Descartar la notificacion'; col = 'vali'; fila = 3.5
               nota = 'Firma invalida o venta inexistente. No se crea nada a partir de un aviso.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 2
               nota = 'Se responde para que la pasarela deje de reintentar.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Recibir la notificacion'; e = '' },
            @{ d = 'Recibir la notificacion'; h = 'Validar la firma'; e = '{POST /pagos/webhook}' },
            @{ d = 'Validar la firma'; h = 'Buscar la transaccion y la venta'; e = '[firma valida]' },
            @{ d = 'Validar la firma'; h = 'Descartar la notificacion'; e = '[firma invalida]  {400}' },
            @{ d = 'Buscar la transaccion y la venta'; h = 'Comprobar si ya se aplico'
               e = '[la venta existe]' },
            @{ d = 'Buscar la transaccion y la venta'; h = 'Descartar la notificacion'
               e = '[no hay venta para ese aviso]' },
            @{ d = 'Comprobar si ya se aplico'; h = 'Marcar la venta PAGADA'; e = '[es la primera vez]' },
            @{ d = 'Comprobar si ya se aplico'; h = 'Transaccion completada'
               e = '[reintento de la pasarela]  {idempotente}' },
            @{ d = 'Marcar la venta PAGADA'; h = 'Descontar inventario y emitir comprobante'
               e = '[pago aprobado]' },
            @{ d = 'Marcar la venta PAGADA'; h = 'Transaccion completada'
               e = '[pago rechazado]  {la venta sigue pendiente}' },
            @{ d = 'Descontar inventario y emitir comprobante'; h = 'Transaccion completada'
               e = '{db.commit()}' },
            @{ d = 'Descartar la notificacion'; h = '(final-rechazo)'; e = '' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-31'; ciclo = '#3'; titulo = 'Registrar venta presencial'
        nota = 'Flujo transaccional de CU-31. La guarda de entrada NO es el rol sino el TURNO DE CAJA ABIERTO: sin turno el dinero cobrado no es atribuible. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Abrir el mostrador'; col = 'auth'; fila = 1
               nota = 'Exige rol CAJERO y sucursal asignada.' },
            @{ n = 'Verificar turno abierto'; col = 'vali'; fila = 0
               nota = 'GET /caja/turnos/mio. Sin turno no se cobra.' },
            @{ n = 'Buscar prendas del mostrador'; col = 'menu'; fila = 1.5
               nota = 'GET /pos/prendas: solo las que tienen existencia en SU sucursal.' },
            @{ n = 'Armar el detalle y el total'; col = 'oper'; fila = 0.5
               nota = 'El total aplica las promociones vigentes de CU-12.' },
            @{ n = 'Descontar inventario y registrar la venta'; col = 'oper'; fila = 2
               nota = 'FOR UPDATE sobre la existencia: dos cajeros no venden la misma ultima unidad.' },
            @{ n = 'Emitir el comprobante'; col = 'oper'; fila = 3
               nota = 'GET /pos/ventas/:codigo/comprobante. Se puede volver a descargar.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 3.5
               nota = 'Sin turno, existencia insuficiente o prenda de otra sucursal.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 2.5
               nota = 'La venta queda asociada al turno, que es lo que permite cuadrar la caja.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Abrir el mostrador'; e = '' },
            @{ d = 'Abrir el mostrador'; h = 'Verificar turno abierto'; e = '{GET /caja/turnos/mio}' },
            @{ d = 'Verificar turno abierto'; h = 'Buscar prendas del mostrador'; e = '[hay turno abierto]' },
            @{ d = 'Verificar turno abierto'; h = 'Informar error'
               e = '[sin turno]  {lleva a abrir caja, CU-30}' },
            @{ d = 'Buscar prendas del mostrador'; h = 'Armar el detalle y el total'
               e = '[elegir prendas y cantidades]' },
            @{ d = 'Buscar prendas del mostrador'; h = 'Armar el detalle y el total'
               e = 'cargarReservaAtendida()  {GET /pos/reservas}' },
            @{ d = 'Armar el detalle y el total'; h = 'Descontar inventario y registrar la venta'
               e = '[efectivo o tarjeta]  {POST /pos/ventas}' },
            @{ d = 'Descontar inventario y registrar la venta'; h = 'Informar error'
               e = '[existencia insuficiente]  {409, la venta no entra parcial}' },
            @{ d = 'Descontar inventario y registrar la venta'; h = 'Emitir el comprobante'
               e = '[descuento aplicado]  {movimiento de salida}' },
            @{ d = 'Emitir el comprobante'; h = 'Transaccion completada'; e = '{db.commit() -> 201}' },
            @{ d = 'Informar error'; h = 'Buscar prendas del mostrador'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-32'; ciclo = '#3'; titulo = 'Registrar devolucion o cambio'
        nota = 'Flujo transaccional de CU-32, con SUS DOS CAMINOS. La guarda de entrada son DOS: el turno de caja abierto (igual que CU-31) y el PLAZO --- dos dias desde el cobro, contados en horas ---. La bifurcacion no esta al principio sino despues de ver que queda por devolver: el cliente elige con la prenda ya sobre el mostrador. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Abrir devoluciones'; col = 'auth'; fila = 1
               nota = 'Exige rol CAJERO o ENCARGADO y sucursal asignada.' },
            @{ n = 'Verificar turno abierto'; col = 'vali'; fila = 0
               nota = 'GET /caja/turnos/mio. Sin turno no hay cajon al que imputar la plata.' },
            @{ n = 'Buscar la venta'; col = 'menu'; fila = 1.5
               nota = 'GET /pos/devoluciones/ventas/:codigo. Solo PAGADA o ENTREGADA, y solo de SU sucursal.' },
            @{ n = 'Verificar el plazo'; col = 'vali'; fila = 1.5
               nota = 'venta.creado_en + DEVOLUCION_PLAZO_DIAS. Una venta vencida SE MUESTRA igual: el cajero necesita el dato para explicarselo al cliente.' },
            @{ n = 'Marcar lo que vuelve'; col = 'menu'; fila = 2.5
               nota = 'El tope de cada linea es lo que QUEDA por devolver, no lo vendido.' },
            @{ n = 'Reingresar y reintegrar'; col = 'oper'; fila = 1
               nota = 'POST /pos/devoluciones. La prenda vuelve SIEMPRE; la plata sale del cajon solo si la venta se cobro en efectivo.' },
            @{ n = 'Elegir la prenda nueva'; col = 'menu'; fila = 3.5
               nota = 'GET /pos/prendas: precio y promociones de HOY, no los de la venta original.' },
            @{ n = 'Calcular la diferencia'; col = 'oper'; fila = 2.5
               nota = 'total de lo nuevo menos valor de lo devuelto, CON SIGNO. Positiva la pone el cliente, negativa la tienda.' },
            @{ n = 'Cambiar la prenda'; col = 'oper'; fila = 3.5
               nota = 'POST /pos/devoluciones/cambios. PRIMERO entra lo viejo y DESPUES sale lo nuevo: es lo unico que deja cambiar una prenda fallada por otra identica cuando era la ultima.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 4.5
               nota = 'Sin turno, fuera de plazo, se devuelve de mas, falta el metodo de la diferencia o no hay stock de la prenda nueva.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 2.5
               nota = 'La devolucion queda colgada del turno. En un cambio ademas nace una venta con metodo_pago = CAMBIO, que el arqueo NO cuenta como efectivo.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Abrir devoluciones'; e = '' },
            @{ d = 'Abrir devoluciones'; h = 'Verificar turno abierto'; e = '{GET /caja/turnos/mio}' },
            @{ d = 'Verificar turno abierto'; h = 'Buscar la venta'; e = '[hay turno abierto]' },
            @{ d = 'Verificar turno abierto'; h = 'Informar error'
               e = '[sin turno]  {lleva a abrir caja, CU-30}' },
            @{ d = 'Buscar la venta'; h = 'Verificar el plazo'; e = '[la venta existe y es de su sucursal]' },
            @{ d = 'Buscar la venta'; h = 'Informar error'; e = '[no existe o es de otra sucursal]  {404}' },
            @{ d = 'Verificar el plazo'; h = 'Marcar lo que vuelve'; e = '[dentro de plazo]' },
            @{ d = 'Verificar el plazo'; h = 'Informar error'
               e = '[vencido]  {409, pero la venta se sigue viendo}' },
            @{ d = 'Marcar lo que vuelve'; h = 'Reingresar y reintegrar'
               e = 'devolver()  {POST /pos/devoluciones}' },
            @{ d = 'Marcar lo que vuelve'; h = 'Elegir la prenda nueva'
               e = 'cambiar()  [el cliente elige acá, no antes]' },
            @{ d = 'Elegir la prenda nueva'; h = 'Calcular la diferencia'; e = '[precio y promocion de hoy]' },
            @{ d = 'Calcular la diferencia'; h = 'Cambiar la prenda'
               e = '[parejo, o con el metodo dicho]  {POST /pos/devoluciones/cambios}' },
            @{ d = 'Calcular la diferencia'; h = 'Informar error'
               e = '[hay diferencia y falta el metodo]  {422}' },
            @{ d = 'Reingresar y reintegrar'; h = 'Informar error'
               e = '[se devuelve mas de lo que queda]  {409}' },
            @{ d = 'Cambiar la prenda'; h = 'Informar error'
               e = '[sin stock de la nueva]  {409, no queda la vieja reingresada}' },
            @{ d = 'Reingresar y reintegrar'; h = 'Transaccion completada'; e = '{db.commit() -> 201}' },
            @{ d = 'Cambiar la prenda'; h = 'Transaccion completada'; e = '{db.commit() -> 201}' },
            @{ d = 'Informar error'; h = 'Buscar la venta'; e = 'reintentar()' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-33'; ciclo = '#3'; titulo = 'Recibir recomendaciones de prendas'
        nota = 'Flujo de CU-33. NO ESCRIBE EN LA BASE: es una consulta asistida. Lo que lo distingue es `Validar contra el catalogo`, que descarta lo que el modelo invente, y el reintento cuando sobreviven menos de tres. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Abrir Para vos'; col = 'auth'; fila = 1
               nota = 'Exige rol CLIENTE. Web y movil.' },
            @{ n = 'Reunir la senal del cliente'; col = 'menu'; fila = 1
               nota = 'Favoritos, compras, reservas, talla habitual y temporada vigente.' },
            @{ n = 'Armar el contexto'; col = 'oper'; fila = 0
               nota = 'Catalogo ya filtrado, con el par id -> nombre. Se arma en CADA pedido, sin cache.' },
            @{ n = 'Consultar al modelo'; col = 'oper'; fila = 1.5
               nota = 'El modelo elige y ordena; no consulta la base.' },
            @{ n = 'Validar contra el catalogo'; col = 'vali'; fila = 1.5
               nota = 'Descarta lo inventado, lo desactivado y lo agotado. La existencia entra por la costura C1.' },
            @{ n = 'Mostrar las prendas sugeridas'; col = 'fin'; fila = 1.5
               nota = 'Cada una con su motivo.' },
            @{ n = 'Informar que no esta disponible'; col = 'vali'; fila = 3.5
               nota = 'Sin proveedor de IA no se dibuja una version degradada.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Abrir Para vos'; e = '' },
            @{ d = 'Abrir Para vos'; h = 'Reunir la senal del cliente'
               e = '{GET /tienda/recomendaciones}' },
            @{ d = 'Reunir la senal del cliente'; h = 'Armar el contexto'; e = '' },
            @{ d = 'Armar el contexto'; h = 'Consultar al modelo'; e = '[hay proveedor de IA]' },
            @{ d = 'Armar el contexto'; h = 'Informar que no esta disponible'; e = '[sin proveedor de IA]' },
            @{ d = 'Consultar al modelo'; h = 'Validar contra el catalogo'; e = '[el modelo contesta]' },
            @{ d = 'Consultar al modelo'; h = 'Consultar al modelo'
               e = '[saturado o agotado el tiempo]  {modelo de respaldo}' },
            @{ d = 'Consultar al modelo'; h = 'Informar que no esta disponible'
               e = '[tampoco contesta el de respaldo]' },
            @{ d = 'Validar contra el catalogo'; h = 'Consultar al modelo'
               e = '[sobreviven menos de MINIMO_UTIL]  {se vuelve a pedir}' },
            @{ d = 'Validar contra el catalogo'; h = 'Mostrar las prendas sugeridas'
               e = '[quedan suficientes prendas reales]' },
            @{ d = 'Informar que no esta disponible'; h = '(final-rechazo)'; e = '' },
            @{ d = 'Mostrar las prendas sugeridas'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-34'; ciclo = '#3'; titulo = 'Conversar con el asistente virtual'
        nota = 'Flujo de CU-34. NO ESCRIBE EN LA BASE, ni siquiera la conversacion: los turnos viven en la pantalla y se pierden al recargar, a proposito. El bucle sobre `Esperando la pregunta` es lo que lo hace conversacional. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Abrir el asistente'; col = 'auth'; fila = 1
               nota = 'Exige rol CLIENTE. GET /asistente/disponible.' },
            @{ n = 'Esperando la pregunta'; col = 'menu'; fila = 1
               nota = 'Ofrece seis preguntas de ejemplo y el campo libre.' },
            @{ n = 'Armar el contexto'; col = 'oper'; fila = 0
               nota = 'Catalogo, promociones vigentes, tallas en cm, y SUS pedidos, reservas y medidas. Entero, en cada pregunta.' },
            @{ n = 'Consultar al modelo'; col = 'oper'; fila = 1.5
               nota = 'Una sola llamada, con los ultimos turnos. Tarda entre 3 y 25 segundos.' },
            @{ n = 'Validar los codigos citados'; col = 'vali'; fila = 1.5
               nota = 'Un codigo inventado no llega a la pantalla.' },
            @{ n = 'Mostrar la respuesta'; col = 'fin'; fila = 1.5
               nota = 'Con las prendas mencionadas como enlaces. El turno se guarda EN MEMORIA.' },
            @{ n = 'Informar que no esta disponible'; col = 'vali'; fila = 3.5
               nota = 'Sin proveedor de IA no se contesta una version degradada.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Abrir el asistente'; e = '' },
            @{ d = 'Abrir el asistente'; h = 'Esperando la pregunta'
               e = '[hay proveedor de IA]  {GET /asistente/disponible}' },
            @{ d = 'Abrir el asistente'; h = 'Informar que no esta disponible'
               e = '[sin proveedor de IA]' },
            @{ d = 'Esperando la pregunta'; h = 'Armar el contexto'
               e = '[pregunta de 1 a 500 caracteres]  {POST /asistente}' },
            @{ d = 'Esperando la pregunta'; h = 'Esperando la pregunta'
               e = '[vacia o muy larga]  {422, sin gastar una llamada al modelo}' },
            @{ d = 'Armar el contexto'; h = 'Consultar al modelo'; e = '{contexto y los ultimos turnos}' },
            @{ d = 'Consultar al modelo'; h = 'Validar los codigos citados'; e = '[el modelo contesta]' },
            @{ d = 'Consultar al modelo'; h = 'Consultar al modelo'
               e = '[saturado o agotado el tiempo]  {modelo de respaldo}' },
            @{ d = 'Consultar al modelo'; h = 'Informar que no esta disponible'
               e = '[tampoco contesta el de respaldo]' },
            @{ d = 'Validar los codigos citados'; h = 'Mostrar la respuesta'
               e = '[solo los codigos que existen]' },
            @{ d = 'Mostrar la respuesta'; h = 'Esperando la pregunta'
               e = 'repreguntar()  [el historial viaja con la siguiente]' },
            @{ d = 'Informar que no esta disponible'; h = '(final-rechazo)'; e = '' },
            @{ d = 'Mostrar la respuesta'; h = '(final)'; e = 'cerrar  [la conversacion se pierde]' }
        )
    },

    # ============ CICLO 1 y 2, rehechos con el patron nuevo ==============
    #
    # Los 43 viejos se borraron el 20/09 por estar mal. Estos NO son los
    # mismos: se eligieron con el criterio del auxiliar ---caer en uno de
    # los seis procesos y tener una maquina de estados de verdad--- y por
    # eso son cuatro y no dieciocho. Un alta-baja-modificacion no tiene
    # estados que dibujar: tiene un formulario que valida.

    @{
        cu = 'CU-02'; ciclo = '#1'; titulo = 'Iniciar y cerrar sesion'
        nota = 'Flujo transaccional de CU-02. El unico del Ciclo 1 con una maquina de estados real: lo que cambia de estado no es una fila de negocio sino el TOKEN, y puede caducar solo. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Pedir credenciales'; col = 'auth'; fila = 1
               nota = 'features/auth/login. Publica: es la puerta.' },
            @{ n = 'Verificar identidad'; col = 'vali'; fila = 0.5
               nota = 'verify_password contra el hash, y que la cuenta este activa.' },
            @{ n = 'Emitir el token'; col = 'oper'; fila = 1.5
               nota = 'Lleva el usuario, su rol y su sucursal cuando la tiene.' },
            @{ n = 'Sesion vigente'; col = 'fin'; fila = 1.5
               nota = 'Ocho horas. El unico estado del ciclo que se abandona sin que nadie actue.' },
            @{ n = 'Revocar el token'; col = 'oper'; fila = 3
               nota = 'Cerrar sesion, o darse de baja la cuenta desde CU-03.' },
            @{ n = 'Informar error'; col = 'vali'; fila = 3.5
               nota = 'Mensaje GENERICO: uno distinto permitiria averiguar que correos tienen cuenta.' },
            @{ n = 'Sesion terminada'; col = 'fin'; fila = 3.5
               nota = 'El token deja de ser aceptado, haya vencido o lo hayan revocado.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Pedir credenciales'; e = '' },
            @{ d = 'Pedir credenciales'; h = 'Verificar identidad'
               e = '[enviar correo y contrasena]  {POST /auth/sesion}' },
            @{ d = 'Verificar identidad'; h = 'Emitir el token'
               e = '[credenciales validas y cuenta activa]' },
            @{ d = 'Verificar identidad'; h = 'Informar error'
               e = '[credenciales invalidas o cuenta inactiva]  {401 generico}' },
            @{ d = 'Emitir el token'; h = 'Sesion vigente'; e = '{db.commit() -> 200}' },
            @{ d = 'Sesion vigente'; h = 'Revocar el token'
               e = '[el usuario cierra sesion]  {POST /auth/logout}' },
            @{ d = 'Sesion vigente'; h = 'Revocar el token'
               e = '[un administrador desactiva la cuenta]  {CU-03}' },
            @{ d = 'Sesion vigente'; h = 'Sesion terminada'
               e = '[se cumplen las 8 horas]  {nadie actua: el token caduca solo}' },
            @{ d = 'Revocar el token'; h = 'Sesion terminada'; e = '{revocar_sesiones_de_usuario()}' },
            @{ d = 'Informar error'; h = 'Pedir credenciales'; e = 'reintentar()' },
            @{ d = 'Sesion terminada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-22'; ciclo = '#2'; titulo = 'Crear reserva de prendas'
        nota = 'Flujo transaccional de CU-22. La reserva es la entidad con mas estados del proyecto, y es el antecedente directo de CU-27: los dos apartan stock y los dos pueden expirar sin que nadie actue. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Elegir prendas'; col = 'auth'; fila = 1
               nota = 'Desde la vitrina o desde el vestidor. Exige rol CLIENTE.' },
            @{ n = 'Elegir sucursal y franja'; col = 'menu'; fila = 1
               nota = 'Solo franjas futuras de una sucursal activa.' },
            @{ n = 'Validar franja y existencia'; col = 'vali'; fila = 0.5
               nota = 'La franja no puede estar en el pasado y tiene que haber unidades libres.' },
            @{ n = 'Apartar las unidades'; col = 'oper'; fila = 1.5
               nota = 'FOR UPDATE por variante: disponible baja, reservada sube.' },
            @{ n = 'Reserva PENDIENTE'; col = 'fin'; fila = 1.5
               nota = 'Aca termina CU-22. Lo que sigue lo deciden otros.' },
            @{ n = 'Liberar las unidades'; col = 'oper'; fila = 3
               nota = 'Cancelacion del cliente (CU-23) o expiracion (CU-25).' },
            @{ n = 'Informar error'; col = 'vali'; fila = 3.5
               nota = 'Franja pasada, sucursal inactiva o sin existencia suficiente.' },
            @{ n = 'Reserva cerrada'; col = 'fin'; fila = 3.5
               nota = 'Atendida, cancelada o expirada. En los tres casos el stock ya no esta retenido.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Elegir prendas'; e = '' },
            @{ d = 'Elegir prendas'; h = 'Elegir sucursal y franja'; e = '[hay prendas elegidas]' },
            @{ d = 'Elegir sucursal y franja'; h = 'Validar franja y existencia'
               e = '[confirmar]  {POST /reservas}' },
            @{ d = 'Validar franja y existencia'; h = 'Apartar las unidades'
               e = '[franja futura y hay existencia]' },
            @{ d = 'Validar franja y existencia'; h = 'Informar error'
               e = '[franja pasada o sin existencia]  {409}' },
            @{ d = 'Apartar las unidades'; h = 'Reserva PENDIENTE'; e = '{db.commit() -> 201}' },
            @{ d = 'Reserva PENDIENTE'; h = 'Reserva cerrada'
               e = '[el encargado la atiende]  {CU-24}' },
            @{ d = 'Reserva PENDIENTE'; h = 'Liberar las unidades'
               e = '[el cliente cancela]  {CU-23}' },
            @{ d = 'Reserva PENDIENTE'; h = 'Liberar las unidades'
               e = '[vence la franja sin atencion]  {CU-25, nadie actua}' },
            @{ d = 'Liberar las unidades'; h = 'Reserva cerrada'
               e = '{el stock vuelve a disponible}' },
            @{ d = 'Informar error'; h = 'Elegir sucursal y franja'; e = 'reintentar()' },
            @{ d = 'Reserva cerrada'; h = '(final)'; e = '' }
        )
    },

    @{
        cu = 'CU-25'; ciclo = '#2'; titulo = 'Expirar reservas vencidas'
        nota = 'Flujo transaccional de CU-25. NO LO INICIA NADIE: es una barrida programada, y por eso el estado inicial no es una pantalla. Es el caso que mejor muestra por que apartar stock no es un defecto: sin esta barrida, cada reserva no atendida inmovilizaria inventario para siempre. Rutas sin el prefijo /api/v1.'
        estados = @(
            @{ n = 'Disparar la barrida'; col = 'auth'; fila = 1
               nota = 'POST /mantenimiento/reservas/expiracion. La llama el planificador, no una persona.' },
            @{ n = 'Buscar reservas vencidas'; col = 'menu'; fila = 1
               nota = 'franja_fin mas la vigencia, contra la hora boliviana.' },
            @{ n = 'Liberar las unidades'; col = 'oper'; fila = 1.5
               nota = 'reservada baja, disponible sube. Una por una, con su movimiento.' },
            @{ n = 'Marcar EXPIRADA'; col = 'oper'; fila = 2.5
               nota = 'El estado final de la reserva. No se borra: queda el rastro.' },
            @{ n = 'Transaccion completada'; col = 'fin'; fila = 2
               nota = 'Si no habia ninguna vencida, tambien se completa: no es un error.' }
        )
        transiciones = @(
            @{ d = '(inicial)'; h = 'Disparar la barrida'; e = '' },
            @{ d = 'Disparar la barrida'; h = 'Buscar reservas vencidas'
               e = '[se cumple el intervalo]  {POST /mantenimiento/reservas/expiracion}' },
            @{ d = 'Buscar reservas vencidas'; h = 'Liberar las unidades'
               e = '[hay reservas con la franja vencida]' },
            @{ d = 'Buscar reservas vencidas'; h = 'Transaccion completada'
               e = '[no hay ninguna vencida]  {no es un error}' },
            @{ d = 'Liberar las unidades'; h = 'Marcar EXPIRADA'; e = '{movimiento de liberacion}' },
            @{ d = 'Marcar EXPIRADA'; h = 'Buscar reservas vencidas'
               e = 'siguiente()  [quedan mas vencidas]' },
            @{ d = 'Marcar EXPIRADA'; h = 'Transaccion completada'; e = '{db.commit()}' },
            @{ d = 'Transaccion completada'; h = '(final)'; e = '' }
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
# La fila se admite con medios (1.5) para intercalar un estado entre otros dos.
function CoordY($fila) { return [int]($Y0 - ($fila * $PASO)) }

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

    $NOMBRE_DIA = "3.2 Diagrama de Estado - $($caso.cu) $($caso.titulo) - CICLO $($caso.ciclo)"
    if (BuscarDiagrama $pkg $NOMBRE_DIA) {
        Write-Output "  $NOMBRE_DIA ya existe, no se toca"
        continue
    }

    $dia = $pkg.Diagrams.AddNew($NOMBRE_DIA, 'Statechart')
    $dia.Notes = $caso.nota
    [void]$dia.Update(); $pkg.Diagrams.Refresh()

    # ---- Los elementos. Se guarda el ID, NUNCA la referencia COM: la regla
    #      del catálogo de errores dice que Elements.Refresh() la invalida y
    #      los DiagramObject quedan con Object_ID = 0, sin dar ningún error.
    #
    #      El Alias lleva el CU porque `Validar datos` y `Seleccionar
    #      operacion` se repiten en casi todos los casos de uso: sin el alias
    #      no hay forma de saber, mirando el explorador, de qué CU es cada
    #      estado.
    $id = @{}
    foreach ($e in $caso.estados) {
        $el = $pkg.Elements.AddNew($e.n, 'State')
        $el.Alias = $caso.cu
        $el.Notes = $e.nota
        [void]$el.Update()
        $id[$e.n] = $el.ElementID
    }
    $el = $pkg.Elements.AddNew('', 'StateNode'); $el.Subtype = $SUB_INI; [void]$el.Update()
    $id['(inicial)'] = $el.ElementID
    $el = $pkg.Elements.AddNew('', 'StateNode'); $el.Subtype = $SUB_FIN; [void]$el.Update()
    $id['(final)'] = $el.ElementID

    # Segundo estado final, para el rechazo de autorizacion. UML 2.5 admite
    # varios: la peticion sin rol muere ahi mismo, no llega a haber
    # transaccion. Dibujarlo al lado de la autenticacion evita una flecha que
    # cruce el lienzo entero. Solo se crea si alguna transicion lo usa: CU-01
    # y CU-25 no tienen autorizacion que rechazar.
    $usaRechazo = @($caso.transiciones | Where-Object { $_.h -eq '(final-rechazo)' }).Count -gt 0
    if ($usaRechazo) {
        $el = $pkg.Elements.AddNew('', 'StateNode'); $el.Subtype = $SUB_FIN; [void]$el.Update()
        $id['(final-rechazo)'] = $el.ElementID
    }
    $pkg.Elements.Refresh()

    # ---- al lienzo. Las coordenadas salen de la columna y la fila.
    foreach ($e in $caso.estados) {
        [void](Poner $dia $id[$e.n] $COL[$e.col] (CoordY $e.fila) $W_EST $H_EST)
    }

    # Los pseudoestados se cuelgan del primer estado y del de cierre.
    $primero = $caso.estados | Where-Object { $_.col -eq 'auth' } | Select-Object -First 1
    if (-not $primero) { $primero = $caso.estados | Select-Object -First 1 }
    $ultimo  = $caso.estados | Where-Object { $_.col -eq 'fin' }  | Select-Object -First 1
    if (-not $ultimo)  { $ultimo  = $caso.estados | Select-Object -Last 1 }

    $yIni = (CoordY $primero.fila) - 15
    $yFin = (CoordY $ultimo.fila)  - 15
    [void](Poner $dia $id['(inicial)'] ($COL[$primero.col] - 80)  $yIni $W_NODO $H_NODO)
    [void](Poner $dia $id['(final)']   ($COL[$ultimo.col] + 290)  $yFin $W_NODO $H_NODO)
    if ($usaRechazo) {
        [void](Poner $dia $id['(final-rechazo)'] ($COL[$primero.col] + 100) ($yIni - 225) $W_NODO $H_NODO)
    }

    # ---- transiciones: conector StateFlow
    foreach ($t in $caso.transiciones) {
        if (-not $id.ContainsKey($t.d)) { throw "$($caso.cu): no existe el estado origen '$($t.d)'" }
        if (-not $id.ContainsKey($t.h)) { throw "$($caso.cu): no existe el estado destino '$($t.h)'" }
        $src = $ea.GetElementByID($id[$t.d])
        $c = $src.Connectors.AddNew($t.e, 'StateFlow')
        $c.SupplierID = $id[$t.h]
        $c.Direction  = 'Source -> Destination'
        [void]$c.Update()
        $src.Connectors.Refresh()
    }

    $pkg.Elements.Refresh()
    $dia.DiagramObjects.Refresh()
    $huerfanos = $ea.SQLQuery("SELECT COUNT(*) AS n FROM t_diagramobjects WHERE Diagram_ID=$($dia.DiagramID) AND Object_ID=0")
    Write-Output "  $($caso.cu) : $($dia.DiagramObjects.Count) estados, $($caso.transiciones.Count) transiciones"
    if ($huerfanos -match '<n>([1-9]\d*)</n>') { Write-Output "  AVISO: $($Matches[1]) objetos con Object_ID=0" }
    $hechos++
}

Write-Output "  $hechos diagrama(s) generado(s)"
$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Write-Output 'OK'
