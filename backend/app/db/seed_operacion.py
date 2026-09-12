"""Dataset de operacion: personas, inventario, favoritos y reservas.

Lo que siembran `seed.py` y `seed_catalogo.py` es el sistema *vacio*: los roles
para poder entrar y el catalogo para poder mirar. Este modulo siembra el sistema
**en uso**, que es lo que hace falta para defenderlo: sin existencias el catalogo
publica todo en cero, CU-19 no tiene disponibilidad que informar, CU-14 sale en
blanco y las reservas de CU-22 a CU-25 no se pueden demostrar aunque su codigo
este entero.

Que siembra, y de quien es cada tabla
-------------------------------------
  P1  ~500 clientes con su usuario, sus direcciones y sus categorias
      preferidas (CU-04), y 15 empleados repartidos en las cinco sucursales
  P4  existencias y miles de movimientos --- ingresos, ajustes y
      transferencias --- repartidos en los ultimos seis meses      [de Mateo]
  P5  favoritos de los clientes sobre el catalogo (CU-20)
  P6  ~300 reservas en los cinco estados, vivas e historicas        [de Mateo]

`existencia`, `movimiento_inventario`, `reserva` y `reserva_detalle` son tablas
de Mateo por la regla de propiedad del Ciclo 2. Este modulo **no las escribe a
mano**: llama a `inventario.registrar_ingreso`, `registrar_ajuste`,
`registrar_transferencia`, `apartar_para_reserva`, `liberar_de_reserva`,
`descontar_por_venta` y `reservas.crear_reserva`, que son suyas. No es una
formalidad: es lo que garantiza que el dataset cumpla las reglas de sus paquetes
--- el invariante `cantidad_disponible == suma(movimientos)`, la capacidad del
probador, el horario de la tienda --- en vez de inventarse filas que su propio
codigo rechazaria.

`permiso` y `rol_permiso` quedan vacias A PROPOSITO: estan declaradas en el
modelo pero ningun camino del codigo las lee --- la autorizacion se resuelve por
rol en `app/core/dependencies.py` ---, y sembrarlas simularia un control de
acceso que hoy no existe. Se llenan el dia que algo las consulte. `sesion_token`
tampoco: la escribe el login, no un seed.

POR QUE LOS MOVIMIENTOS SE FECHAN HACIA ATRAS
---------------------------------------------
`movimiento_inventario.creado_en` lo pone la base con `now()`, que en PostgreSQL
es el instante de la TRANSACCION. Eso es justamente lo que agrupa las lineas de
un ingreso en CU-13 --- ver la nota «POR QUE NO HAY TABLA `ingreso`» en
inventario/models.py --- pero tiene un efecto lateral en un seed: si los doce
remitos de una sucursal se cargan en la misma corrida quedan a segundos unos de
otros, y el historial de seis meses que la pantalla promete es en realidad de
seis minutos.

Asi que despues de cada remito se retrasan sus movimientos a la fecha que les
toca, con un UPDATE acotado por rango de id. Se hace por id y no por `creado_en`
porque el id es exacto: el seed corre en un solo hilo, asi que los ids que
escribio una llamada son un rango contiguo. Cada remito conserva una marca
distinta de los demas, que es lo que CU-13 necesita para seguir agrupandolo.

VOLUMEN
-------
Los numeros estan en `VOLUMEN`, al principio, para poder bajarlos sin leer el
resto. Con los valores de fabrica son ~515 personas, ~2.500 existencias,
~5.000 movimientos, ~1.500 favoritos y 300 reservas.

CONTRA QUE BASE CORRERLO
------------------------
Contra una base LOCAL. El `.env` del proyecto apunta a Supabase, que es la base
desplegada, y esto escribe miles de filas: correrlo ahi sin querer no se deshace
con un Ctrl+C. Ver la advertencia de `main()`.

Es idempotente como el resto del seed: las personas se reconocen por su correo,
los empleados por su documento, los favoritos por su par (cliente, producto), y
el bloque de inventario y el de reservas se saltan enteros si ya hay filas.
"""

import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.modules.catalogo.models import Categoria, Producto, VarianteProducto
from app.modules.catalogo_publico.models import Favorito
from app.modules.inventario import service as inventario
from app.modules.inventario.models import Existencia, MovimientoInventario
from app.modules.inventario.schemas import (
    AjusteIn,
    IngresoIn,
    LineaIngresoIn,
    TransferenciaIn,
)
from app.modules.organizacion.models import Ciudad, Empleado, Proveedor, Sucursal
from app.modules.reservas import service as reservas
from app.modules.reservas.models import DetalleReserva, Reserva
from app.modules.reservas.schemas import LineaReservaIn, ReservaCrearIn
from app.modules.seguridad.models import Cliente, DireccionCliente, Rol, Usuario

#: Semilla propia, distinta de la de `seed_catalogo`. Si las dos compartieran
#: generador, agregar un producto correria toda la secuencia y el dataset entero
#: saldria distinto; separadas, cada bloque es reproducible por su cuenta.
AZAR = random.Random(20260912)

#: Bolivia no aplica horario de verano, asi que un desfase fijo alcanza y evita
#: arrastrar una dependencia de zonas horarias solo para el seed. Importa porque
#: las franjas de reserva se comparan contra `sucursal.horario_apertura`, que es
#: un TIME sin zona y significa la hora de pared de ESA tienda.
BOLIVIA = timezone(timedelta(hours=-4))

VOLUMEN = {
    "clientes": 500,
    "cajeros_por_sucursal": 2,
    "lineas_por_remito": (25, 55),
    "remitos_de_reposicion": 40,
    "stock_minimo_fijados": 400,
    "ajustes": 200,
    "transferencias": 60,
    "quiebres": 45,
    "variantes_agotadas": 12,
    "favoritos_por_cliente": (0, 8),
    "reservas_historicas": 260,
    "reservas_vivas": 40,
    "meses_de_historia": 6,
}

#: Dominio propio de las cuentas de demostracion. Sirve para reconocerlas de un
#: vistazo en la tabla de usuarios y para poder borrarlas con un LIKE si hiciera
#: falta, sin rozar una cuenta real.
DOMINIO_DEMO = "demo.violetboutique.bo"

#: Que fraccion del catalogo tiene cada sucursal. La sucursal del centro
#: comercial trabaja con todo; las de barrio, con una seleccion. No es adorno:
#: si todas tuvieran todo, CU-19 --- que responde «en que sucursal hay esta
#: prenda» --- contestaria siempre lo mismo y no demostraria nada.
COBERTURA = {
    "Violet Ventura Mall": 1.00,
    "Violet Equipetrol": 0.85,
    "Violet Centro": 0.70,
    "Violet Sopocachi": 0.60,
    "Violet El Prado": 0.55,
}

NOMBRES_F = [
    "Maria", "Ana", "Rocio", "Gabriela", "Paola", "Lucia", "Valeria", "Carla",
    "Daniela", "Fernanda", "Andrea", "Camila", "Mariela", "Noelia", "Patricia",
    "Elizabeth", "Jimena", "Tatiana", "Vanessa", "Alejandra", "Silvia", "Karen",
    "Adriana", "Ximena", "Cecilia", "Miriam", "Sandra", "Lorena", "Natalia",
]
NOMBRES_M = [
    "Juan", "Carlos", "Luis", "Jorge", "Marco", "Ruben", "Diego", "Alvaro",
    "Mateo", "Sergio", "Ramiro", "Oscar", "Pablo", "Edgar", "Rodrigo", "Ivan",
    "Freddy", "Gonzalo", "Hernan", "Javier", "Nelson", "Mauricio", "Alfredo",
]
APELLIDOS = [
    "Quispe", "Mamani", "Flores", "Chavez", "Rojas", "Vargas", "Sanchez",
    "Justiniano", "Anez", "Suarez", "Roca", "Montero", "Cuellar", "Pena",
    "Arce", "Salvatierra", "Gutierrez", "Terceros", "Mendoza", "Ribera",
    "Paz", "Aguilera", "Banegas", "Zambrana", "Calderon", "Ortiz", "Melgar",
    "Antelo", "Parada", "Sandoval", "Vaca", "Guzman", "Torrico", "Ledezma",
]

#: El alias es lo que el cliente ve en el selector de direcciones de CU-04, asi
#: que no se genera como «Direccion 1».
ALIAS_DIRECCION = ["Casa", "Trabajo", "Casa de mis papas", "Departamento"]

CALLES = [
    "Av. Banzer", "Calle Sucre", "Av. Alemana", "Calle Ballivian",
    "Av. Cristo Redentor", "Calle Bolivar", "Av. Roca y Coronado",
    "Calle Independencia", "Av. Busch", "Calle Espana", "Av. Irala",
    "Calle Warnes", "Av. Paragua", "Calle Junin", "Av. Santos Dumont",
]

REFERENCIAS = [
    "Porton negro, al lado de la farmacia",
    "Edificio de ladrillo visto, timbre 3",
    "Frente a la plaza",
    "Casa esquinera de dos plantas",
    "Sobre el segundo anillo, pasando el surtidor",
    None,
    None,
]

#: `registrar_ajuste` exige un motivo legible y de una longitud minima: no le
#: sirve «ok». Son los textos que despues se leen en el historial de CU-15.
MOTIVOS_AJUSTE = [
    "Conteo fisico mensual del deposito",
    "Diferencia detectada en el arqueo semanal",
    "Prenda danada dada de baja del saldo",
    "Correccion de carga: el remito decia otra cantidad",
    "Recuento tras el inventario general",
    "Prenda extraviada, no aparecio en el conteo",
]

MOTIVOS_TRANSFERENCIA = [
    "Reposicion por quiebre de stock en destino",
    "Pedido desde la otra sucursal para una clienta",
    "Reequilibrio de talles entre locales",
    "Traslado de temporada saliente",
]

OBSERVACIONES_INGRESO = [
    None,
    "Recepcion completa",
    "Llego un bulto abierto, revisado y conforme",
    "Entrega parcial del pedido del mes",
    None,
]

#: Las tallas que un cliente declara en su perfil (CU-04). Son VARCHAR de texto
#: libre y no una clave foranea a `talla`: se siembran con los mismos codigos
#: que usa el catalogo para que el dia que CU-33 quiera cruzarlas el dato ya
#: coincida, aunque hoy la base no lo obligue.
TALLAS_SUPERIOR = ["XS", "S", "M", "L", "XL"]
TALLAS_INFERIOR = ["36", "38", "40", "42", "44"]
TALLAS_CALZADO = ["35", "36", "37", "38", "39", "40", "41", "42"]


# --- Utilidades ----------------------------------------------------------


def _sin_tildes(texto: str) -> str:
    """Para armar correos. No hay tildes en los nombres de arriba, pero el
    dia que se agregue uno el correo no debe salir con una."""
    tabla = str.maketrans("áéíóúñÁÉÍÓÚÑ", "aeiounAEIOUN")
    return texto.translate(tabla)


def _ahora() -> datetime:
    return datetime.now(BOLIVIA)


def _fecha_en_la_historia(meses: int) -> datetime:
    """Un instante al azar dentro de los ultimos `meses`, en horario de tienda.

    La hora importa: un movimiento a las cuatro de la manana en un local que
    abre a las nueve delata que el dato es inventado en la primera captura de
    pantalla que alguien mire.
    """
    dias = AZAR.randrange(0, meses * 30)
    return _ahora().replace(
        hour=AZAR.randrange(9, 20),
        minute=AZAR.randrange(0, 60),
        second=AZAR.randrange(0, 60),
        microsecond=0,
    ) - timedelta(days=dias)


def _retrasar_movimientos(db: Session, desde_id: int, cuando: datetime) -> None:
    """Fecha hacia atras los movimientos escritos despues de `desde_id`.

    Ver la nota del encabezado. El rango de id es exacto porque el seed es de un
    solo hilo: nadie mas esta escribiendo en esta tabla mientras corre.
    """
    db.execute(
        text(
            "UPDATE movimiento_inventario SET creado_en = :cuando "
            "WHERE id > :desde"
        ),
        {"cuando": cuando, "desde": desde_id},
    )
    db.commit()


def _ultimo_movimiento(db: Session) -> int:
    return db.scalar(select(func.coalesce(func.max(MovimientoInventario.id), 0)))


def _hash_de_demostracion() -> str | None:
    """Un solo hash bcrypt para las quinientas cuentas.

    bcrypt esta hecho para ser lento --- es su defensa --- y tarda del orden de
    un cuarto de segundo. Hashear quinientas veces la MISMA contrasena serian
    dos minutos de espera para obtener quinientas veces un valor equivalente.
    Se calcula una vez y se reparte.

    Compartir el hash no debilita nada que no estuviera ya debilitado por
    compartir la contrasena, y son cuentas de demostracion. Lo que si importa es
    que la contrasena no viva en el repositorio: se lee de DEMO_PASSWORD, igual
    que ADMIN_PASSWORD y por el mismo motivo, y sin ella no se crea ninguna
    persona.
    """
    if not settings.DEMO_PASSWORD:
        return None
    return hash_password(settings.DEMO_PASSWORD)


# --- P1 · Personas -------------------------------------------------------


def _clientes(
    db: Session,
    rol_id: int,
    ciudades: list[int],
    hojas: list[Categoria],
    hash_demo: str,
) -> int:
    """Los clientes con su ficha, sus direcciones y sus preferencias.

    La ficha de `cliente` y la cuenta de `usuario` son dos filas y no una porque
    asi lo fija el modelo: el usuario es quien entra al sistema y el cliente es
    a quien se le vende. Aqui se crean juntas, que es lo que hace CU-01.

    Un 4% queda inactivo y cerca de un tercio sin categorias preferidas. Las dos
    cosas son a proposito: la pantalla de CU-03 necesita cuentas dadas de baja
    para que el filtro de estado tenga algo que filtrar, y el recomendador del
    Ciclo 3 va a encontrarse con clientes que nunca llenaron el perfil. Un
    dataset donde todo esta completo esconde justo los casos que rompen.
    """
    # SE RECONOCE POR EL DOCUMENTO, NO POR EL CORREO. El documento se deriva del
    # indice y es el mismo en cada corrida; el correo lleva adentro un nombre
    # sorteado, y en la segunda corrida el generador esta en otro punto de su
    # secuencia y devuelve otro nombre. Comparando correos, ningun cliente se
    # reconoceria y la insercion moriria contra la unicidad del documento ---
    # que es exactamente como se descubrio esto.
    ya_estan = set(db.scalars(select(Cliente.documento)))
    creados = 0

    for indice in range(1, VOLUMEN["clientes"] + 1):
        documento = str(7_000_000 + indice)
        if documento in ya_estan:
            continue

        nombres = AZAR.choice(NOMBRES_F + NOMBRES_M)
        paterno = AZAR.choice(APELLIDOS)
        apellidos = f"{paterno} {AZAR.choice(APELLIDOS)}"
        correo = (
            f"{_sin_tildes(nombres).lower()}."
            f"{_sin_tildes(paterno).lower()}{indice:04d}@{DOMINIO_DEMO}"
        )

        # La cuenta se fecha hacia atras para que «altas del mes» signifique
        # algo. `creado_en` tiene server_default, asi que darle un valor en
        # Python es lo unico que hace falta para ganarle al now() de la base.
        alta = _fecha_en_la_historia(12)

        usuario = Usuario(
            correo=correo,
            hash_contrasena=hash_demo,
            nombres=nombres,
            apellidos=apellidos,
            rol_id=rol_id,
            activo=AZAR.random() > 0.04,
            creado_en=alta,
            actualizado_en=alta,
        )
        db.add(usuario)
        db.flush()

        cliente = Cliente(
            usuario_id=usuario.id,
            documento=documento,
            telefono=f"7{AZAR.randrange(1_000_000, 9_999_999)}",
            talla_superior=AZAR.choice(TALLAS_SUPERIOR),
            talla_inferior=AZAR.choice(TALLAS_INFERIOR),
            talla_calzado=AZAR.choice(TALLAS_CALZADO),
            creado_en=alta,
            actualizado_en=alta,
        )
        if hojas and AZAR.random() > 0.3:
            cliente.categorias_preferidas = AZAR.sample(
                hojas, k=AZAR.randrange(1, min(5, len(hojas) + 1))
            )
        db.add(cliente)
        db.flush()

        for orden in range(AZAR.choice([1, 1, 1, 2, 2, 3])):
            db.add(
                DireccionCliente(
                    cliente_id=cliente.id,
                    ciudad_id=AZAR.choice(ciudades),
                    alias=ALIAS_DIRECCION[orden % len(ALIAS_DIRECCION)],
                    direccion=f"{AZAR.choice(CALLES)} #{AZAR.randrange(100, 3500)}",
                    referencia=AZAR.choice(REFERENCIAS),
                    # Solo la primera. El indice parcial
                    # uq_direccion_predeterminada admite una por cliente, y
                    # marcar dos seria un error de la base, no del seed.
                    predeterminada=(orden == 0),
                    creado_en=alta,
                    actualizado_en=alta,
                )
            )

        creados += 1
        if creados % 50 == 0:
            db.commit()

    db.commit()
    return creados


def _empleados(
    db: Session, roles: dict[str, int], sucursales: list[Sucursal], hash_demo: str
) -> int:
    """Un encargado y sus cajeros en cada sucursal.

    Es lo que le da sentido al RNF26 --- el ambito de datos de un encargado es
    su propia sucursal ---: sin empleados, las pantallas de sucursal solo se
    pueden mirar con el usuario administrador, que las ve todas y por eso no
    demuestra que el recorte funcione.
    """
    documentos = set(db.scalars(select(Empleado.documento)))
    correos = set(db.scalars(select(Usuario.correo)))
    creados = 0
    numero = 0

    for sucursal in sucursales:
        cargos = ["ENCARGADO"] + ["CAJERO"] * VOLUMEN["cajeros_por_sucursal"]
        # Dos iniciales de la sucursal: distinguen el correo de dos empleados
        # homonimos en locales distintos sin inventarles un numero.
        siglas = "".join(p[0] for p in sucursal.nombre.split()[1:3]).lower() or "vb"

        for cargo in cargos:
            numero += 1
            documento = str(5_000_000 + numero)
            if documento in documentos:
                continue

            nombres = AZAR.choice(NOMBRES_F + NOMBRES_M)
            paterno = AZAR.choice(APELLIDOS)
            correo = (
                f"{_sin_tildes(nombres).lower()}."
                f"{_sin_tildes(paterno).lower()}.{siglas}@{DOMINIO_DEMO}"
            )
            if correo in correos:
                correo = f"{cargo.lower()}{numero}@{DOMINIO_DEMO}"
            correos.add(correo)

            ingreso = date.today() - timedelta(days=AZAR.randrange(120, 1500))
            usuario = Usuario(
                correo=correo,
                hash_contrasena=hash_demo,
                nombres=nombres,
                apellidos=f"{paterno} {AZAR.choice(APELLIDOS)}",
                rol_id=roles[cargo],
                activo=True,
            )
            db.add(usuario)
            db.flush()

            # Uno de cada quince ya no trabaja: el modelo admite `fecha_baja` y
            # sin ninguna fila que la use, el filtro de personal activo nunca se
            # prueba contra datos.
            #
            # SOLO CAJEROS. Dar de baja a un encargado deja su sucursal sin
            # nadie que responda por ella: los movimientos de ese local pasan a
            # firmarse con el administrador y no queda con quien iniciar sesion
            # para mostrar las pantallas de sucursal, que son las unicas donde
            # se ve el recorte por ambito del RNF26.
            de_baja = cargo == "CAJERO" and AZAR.randrange(15) == 0
            db.add(
                Empleado(
                    usuario_id=usuario.id,
                    sucursal_id=sucursal.id,
                    documento=documento,
                    telefono=f"7{AZAR.randrange(1_000_000, 9_999_999)}",
                    cargo=cargo,
                    fecha_ingreso=ingreso,
                    fecha_baja=(
                        ingreso + timedelta(days=AZAR.randrange(60, 400))
                        if de_baja
                        else None
                    ),
                )
            )
            creados += 1

    db.commit()
    return creados


# --- P4 · Inventario (tablas de Mateo, escritas por su servicio) ---------


def _remito(
    db: Session,
    *,
    sucursal_id: int,
    proveedor_id: int,
    variantes: list[int],
    usuario_id: int | None,
    cuando: datetime,
) -> int:
    """Un ingreso de mercaderia, fechado hacia atras. Devuelve las unidades."""
    desde = _ultimo_movimiento(db)
    salida = inventario.registrar_ingreso(
        db,
        IngresoIn(
            sucursal_id=sucursal_id,
            proveedor_id=proveedor_id,
            referencia=f"R-{AZAR.randrange(10_000, 99_999)}",
            observacion=AZAR.choice(OBSERVACIONES_INGRESO),
            lineas=[
                LineaIngresoIn(variante_id=v, cantidad=AZAR.randrange(4, 30))
                for v in variantes
            ],
        ),
        usuario_id=usuario_id,
    )
    _retrasar_movimientos(db, desde, cuando)
    return salida.unidades


def _agotar(
    db: Session,
    *,
    variante_id: int,
    sucursal_id: int,
    reservada: int,
    usuario_id: int | None,
    meses: int,
) -> bool:
    """Deja una existencia en cero con un ajuste por conteo.

    Se hace con `registrar_ajuste` y no bajando la columna, porque una prenda no
    desaparece del saldo sin que alguien lo registre: esa es la regla de P4 y el
    quiebre tiene que quedar en el historial como cualquier otro movimiento.

    Lo contado es lo RESERVADO, no cero: lo apartado para una reserva sigue
    fisicamente en la percha, asi que contar cero ahi seria decir que tambien
    desaparecio lo que esta comprometido.
    """
    desde = _ultimo_movimiento(db)
    try:
        inventario.registrar_ajuste(
            db,
            AjusteIn(
                variante_id=variante_id,
                sucursal_id=sucursal_id,
                cantidad_contada=reservada,
                motivo="Conteo fisico: no quedan unidades de esta prenda",
            ),
            usuario_id=usuario_id,
        )
    except inventario.ErrorDeInventario:
        db.rollback()
        return False
    _retrasar_movimientos(db, desde, _fecha_en_la_historia(meses))
    return True


def _encargados_por_sucursal(db: Session) -> dict[int, int]:
    """Quien firma los movimientos de cada local.

    Los ingresos, ajustes y transferencias quedan a nombre del ENCARGADO de esa
    sucursal, no del administrador. Es lo que pasa de verdad --- la mercaderia la
    recibe quien esta en el local --- y es lo unico que hace demostrable el
    RNF26: con todos los movimientos firmados por el administrador, el historial
    de CU-15 no distingue quien hizo que en que tienda.

    `usuario_id` nulo NO es un valor de repuesto: en esta tabla significa «lo
    hizo el sistema», que es cierto solo para la expiracion automatica de CU-25.
    """
    return {
        sucursal_id: usuario_id
        for sucursal_id, usuario_id in db.execute(
            select(Empleado.sucursal_id, Empleado.usuario_id).where(
                Empleado.cargo == "ENCARGADO", Empleado.fecha_baja.is_(None)
            )
        )
    }


def _inventario(
    db: Session,
    sucursales: list[Sucursal],
    proveedores: list[int],
    encargados: dict[int, int],
    respaldo: int | None,
) -> dict[str, int]:
    """Existencias y movimientos de los ultimos seis meses.

    El bloque entero se saltea si ya hay existencias. No se intenta completar a
    medias: los saldos son el resultado acumulado de una secuencia de
    movimientos, y agregarle movimientos nuevos a una historia que ya existe
    daria saldos correctos pero una historia que no se puede leer.
    """
    if db.scalar(select(func.count()).select_from(Existencia)):
        print("  = ya hay existencias: se saltea el inventario")
        return {}

    variantes = list(
        db.scalars(
            select(VarianteProducto.id)
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .where(VarianteProducto.activa.is_(True), Producto.activo.is_(True))
        )
    )
    if not variantes or not proveedores:
        print("  ! sin variantes o sin proveedores: no hay inventario que sembrar")
        return {}

    meses = VOLUMEN["meses_de_historia"]
    minimo, maximo = VOLUMEN["lineas_por_remito"]
    remitos = unidades = 0

    # --- La carga inicial: cada sucursal recibe su parte del catalogo ------
    for sucursal in sucursales:
        cobertura = COBERTURA.get(sucursal.nombre, 0.7)
        seleccion = AZAR.sample(variantes, int(len(variantes) * cobertura))

        indice = 0
        while indice < len(seleccion):
            lote = seleccion[indice : indice + AZAR.randrange(minimo, maximo)]
            indice += len(lote)
            unidades += _remito(
                db,
                sucursal_id=sucursal.id,
                proveedor_id=AZAR.choice(proveedores),
                variantes=lote,
                usuario_id=encargados.get(sucursal.id, respaldo),
                cuando=_fecha_en_la_historia(meses),
            )
            remitos += 1

    # --- Reposiciones: la mercaderia no llega una sola vez ----------------
    # Sin esto, cada variante tendria exactamente un movimiento y el historial
    # de CU-15 seria una lista de ingresos identicos. Las reposiciones son mas
    # recientes que la carga inicial, que es el orden en que pasan las cosas.
    for _ in range(VOLUMEN["remitos_de_reposicion"]):
        sucursal = AZAR.choice(sucursales)
        presentes = list(
            db.scalars(
                select(Existencia.variante_id)
                .where(Existencia.sucursal_id == sucursal.id)
                .order_by(func.random())
                .limit(AZAR.randrange(minimo, maximo))
            )
        )
        if not presentes:
            continue
        unidades += _remito(
            db,
            sucursal_id=sucursal.id,
            proveedor_id=AZAR.choice(proveedores),
            variantes=presentes,
            usuario_id=encargados.get(sucursal.id, respaldo),
            cuando=_fecha_en_la_historia(2),
        )
        remitos += 1

    # --- Stock minimo: solo donde el encargado se tomo el trabajo ---------
    # No se fija en todas las existencias a proposito. Cero significa «sin
    # alerta», y es lo que tiene una prenda sobre la que nadie decidio nada;
    # llenarlas todas volveria la pantalla de alertas de CU-16 un listado de
    # todo el inventario, que es lo contrario de una alerta.
    for existencia_id in db.scalars(
        select(Existencia.id).order_by(func.random()).limit(VOLUMEN["stock_minimo_fijados"])
    ):
        inventario.fijar_stock_minimo(db, existencia_id, AZAR.randrange(3, 14))

    # --- Ajustes por conteo fisico (CU-15) --------------------------------
    ajustes = 0
    for _ in range(VOLUMEN["ajustes"]):
        fila = db.execute(
            select(
                Existencia.variante_id,
                Existencia.sucursal_id,
                Existencia.cantidad_disponible,
                Existencia.cantidad_reservada,
            )
            .where(Existencia.cantidad_disponible >= 3)
            .order_by(func.random())
            .limit(1)
        ).first()
        if fila is None:
            break

        variante_id, sucursal_id, disponible, reservada = fila
        # Se cuenta el TOTAL FISICO, no el disponible: una prenda apartada para
        # una reserva sigue estando en la percha. Lo dice el docstring de
        # registrar_ajuste y es lo que hace que el ajuste no pise una reserva.
        diferencia = AZAR.choice([-2, -1, -1, 1, 2, 3])
        contada = disponible + reservada + diferencia
        if contada < reservada:
            continue

        desde = _ultimo_movimiento(db)
        try:
            inventario.registrar_ajuste(
                db,
                AjusteIn(
                    variante_id=variante_id,
                    sucursal_id=sucursal_id,
                    cantidad_contada=contada,
                    motivo=AZAR.choice(MOTIVOS_AJUSTE),
                ),
                usuario_id=encargados.get(sucursal_id, respaldo),
            )
        except inventario.ErrorDeInventario:
            db.rollback()
            continue
        _retrasar_movimientos(db, desde, _fecha_en_la_historia(meses))
        ajustes += 1

    # --- Transferencias entre sucursales (flujo 3a de CU-15) --------------
    transferencias = 0
    for _ in range(VOLUMEN["transferencias"]):
        fila = db.execute(
            select(Existencia.variante_id, Existencia.sucursal_id)
            .where(Existencia.cantidad_disponible >= 8)
            .order_by(func.random())
            .limit(1)
        ).first()
        if fila is None:
            break

        variante_id, origen_id = fila
        candidatas = [s.id for s in sucursales if s.id != origen_id]
        if not candidatas:
            break

        desde = _ultimo_movimiento(db)
        try:
            inventario.registrar_transferencia(
                db,
                TransferenciaIn(
                    variante_id=variante_id,
                    sucursal_origen_id=origen_id,
                    sucursal_destino_id=AZAR.choice(candidatas),
                    cantidad=AZAR.randrange(2, 6),
                    motivo=AZAR.choice(MOTIVOS_TRANSFERENCIA),
                ),
                usuario_id=encargados.get(origen_id, respaldo),
            )
        except inventario.ErrorDeInventario:
            db.rollback()
            continue
        _retrasar_movimientos(db, desde, _fecha_en_la_historia(meses))
        transferencias += 1

    # --- Quiebres de stock: algo tiene que faltar -------------------------
    # Un catalogo donde todo esta disponible en las cinco sucursales no ejercita
    # ninguna de las respuestas interesantes: CU-19 contesta siempre que si, la
    # vitrina no muestra un agotado nunca y la alerta de reposicion de CU-16 no
    # llega a dispararse por consumo. Faltan dos formas distintas de faltar: la
    # prenda que se acabo en UNA sucursal --- que es la que CU-19 tiene que
    # saber derivar a otra --- y la que no queda en NINGUNA, que es la unica que
    # obliga a la ficha a decirlo.
    quiebres = agotadas = 0
    for _ in range(VOLUMEN["quiebres"]):
        fila = db.execute(
            select(
                Existencia.variante_id,
                Existencia.sucursal_id,
                Existencia.cantidad_reservada,
            )
            .where(Existencia.cantidad_disponible.between(1, 10))
            .order_by(func.random())
            .limit(1)
        ).first()
        if fila is None:
            break
        if _agotar(
            db,
            variante_id=fila[0],
            sucursal_id=fila[1],
            reservada=fila[2],
            usuario_id=encargados.get(fila[1], respaldo),
            meses=meses,
        ):
            quiebres += 1

    for variante_id in list(
        db.scalars(
            select(Existencia.variante_id)
            .group_by(Existencia.variante_id)
            .order_by(func.random())
            .limit(VOLUMEN["variantes_agotadas"])
        )
    ):
        filas = db.execute(
            select(Existencia.sucursal_id, Existencia.cantidad_reservada).where(
                Existencia.variante_id == variante_id,
                Existencia.cantidad_disponible > 0,
            )
        ).all()
        for sucursal_id, reservada in filas:
            _agotar(
                db,
                variante_id=variante_id,
                sucursal_id=sucursal_id,
                reservada=reservada,
                usuario_id=encargados.get(sucursal_id, respaldo),
                meses=meses,
            )
        agotadas += 1

    return {
        "remitos": remitos,
        "unidades": unidades,
        "quiebres": quiebres,
        "variantes agotadas en todas": agotadas,
        "ajustes": ajustes,
        "transferencias": transferencias,
        "existencias": db.scalar(select(func.count()).select_from(Existencia)),
        "movimientos": db.scalar(select(func.count()).select_from(MovimientoInventario)),
    }


# --- P5 · Favoritos (CU-20) ----------------------------------------------


def _favoritos(db: Session, clientes: list[Cliente]) -> int:
    """Lo que cada cliente marco para volver a mirar.

    Los favoritos se sortean SESGADOS hacia las categorias preferidas del
    cliente en vez de al azar sobre todo el catalogo. Cuesta tres lineas mas y
    es la diferencia entre un dataset que se puede mirar y uno que se puede
    usar: el recomendador del CU-33 lee precisamente la categoria del producto
    favorito (RF31), y con favoritos uniformes no habria nada que recomendar
    porque todas las categorias pesarian igual.
    """
    ya_estan = {
        (c, p) for c, p in db.execute(select(Favorito.cliente_id, Favorito.producto_id))
    }
    por_categoria: dict[int, list[int]] = {}
    for producto_id, categoria_id in db.execute(
        select(Producto.id, Producto.categoria_id).where(Producto.activo.is_(True))
    ):
        por_categoria.setdefault(categoria_id, []).append(producto_id)
    todos = [p for lista in por_categoria.values() for p in lista]
    if not todos:
        return 0

    minimo, maximo = VOLUMEN["favoritos_por_cliente"]
    creados = 0

    for cliente in clientes:
        # UN GENERADOR POR CLIENTE, sembrado con su id.
        #
        # No es un capricho: con el generador global, un cliente al que le toco
        # cero favoritos queda sin ninguna fila, y en la corrida siguiente es
        # indistinguible de uno que todavia no se sembro --- vuelve a sortear,
        # esta vez le tocan cuatro, y la tabla crece cada vez que alguien corre
        # el seed. Sembrando con el id, a ese cliente le toca cero SIEMPRE, y a
        # los demas exactamente los mismos productos: la segunda corrida
        # encuentra todos los pares ya escritos y no agrega ninguno.
        azar = random.Random(cliente.id * 7919)
        cuantos = azar.randrange(minimo, maximo + 1)
        if not cuantos:
            continue

        preferidos: list[int] = []
        for categoria in cliente.categorias_preferidas:
            preferidos.extend(por_categoria.get(categoria.id, ()))

        elegidos: set[int] = set()
        while len(elegidos) < cuantos:
            # Dos de cada tres salen de sus categorias; el resto de todo el
            # catalogo, porque a nadie le gusta solo lo que declaro que le gusta.
            fuente = preferidos if preferidos and azar.random() < 0.66 else todos
            elegidos.add(azar.choice(fuente))

        for producto_id in sorted(elegidos):
            if (cliente.id, producto_id) in ya_estan:
                continue
            db.add(
                Favorito(
                    cliente_id=cliente.id,
                    producto_id=producto_id,
                    creado_en=_fecha_en_la_historia(8),
                )
            )
            creados += 1

        if creados % 200 == 0:
            db.commit()

    db.commit()
    return creados


# --- P6 · Reservas (tablas de Mateo, escritas por su servicio) -----------


def _prendas_con_stock(db: Session, sucursal_id: int, cuantas: int) -> list[tuple[int, int]]:
    """Variantes que esa sucursal puede apartar de verdad, con su cantidad."""
    filas = db.execute(
        select(Existencia.variante_id, Existencia.cantidad_disponible)
        .where(
            Existencia.sucursal_id == sucursal_id,
            Existencia.cantidad_disponible >= 3,
        )
        .order_by(func.random())
        .limit(cuantas)
    ).all()
    return [(variante_id, AZAR.choice([1, 1, 1, 2])) for variante_id, _ in filas]


def _franja_pasada(sucursal: Sucursal) -> tuple[datetime, datetime]:
    """Una franja de las ultimas semanas, dentro del horario de la tienda."""
    dia = _ahora() - timedelta(days=AZAR.randrange(2, 120))
    hora = AZAR.randrange(
        sucursal.horario_apertura.hour, max(sucursal.horario_cierre.hour - 1, sucursal.horario_apertura.hour + 1)
    )
    inicio = dia.replace(
        hour=hora, minute=AZAR.choice([0, 30]), second=0, microsecond=0
    )
    return inicio, inicio + timedelta(minutes=AZAR.choice([30, 45, 60]))


def _franja_futura(sucursal: Sucursal, duracion: int) -> datetime | None:
    """Una franja de las proximas 72 horas que el servicio vaya a aceptar.

    Las tres condiciones son las de `_validar_franja`: dentro del horario de
    pared de ESA tienda, ni en el pasado, ni mas alla de
    RESERVA_ANTICIPACION_MAXIMA_HORAS. Se sortea hasta dar con una en vez de
    calcularla porque a ultima hora de un dia el rango valido puede estar vacio,
    y reintentar es mas corto que el caso por caso.
    """
    ahora = _ahora()
    tope = ahora + timedelta(hours=settings.RESERVA_ANTICIPACION_MAXIMA_HORAS - 1)
    ultima_hora = sucursal.horario_cierre.hour - (duracion // 60) - 1

    for _ in range(30):
        dia = ahora + timedelta(days=AZAR.randrange(0, 3))
        inicio = dia.replace(
            hour=AZAR.randrange(sucursal.horario_apertura.hour, max(ultima_hora, sucursal.horario_apertura.hour + 1)),
            minute=AZAR.choice([0, 30]),
            second=0,
            microsecond=0,
        )
        if ahora + timedelta(hours=1) < inicio < tope:
            return inicio
    return None


def _reservas(
    db: Session, clientes: list[Cliente], sucursales: list[Sucursal]
) -> dict[str, int]:
    """Reservas historicas y vivas.

    LAS DOS MITADES SE CONSTRUYEN DISTINTO, Y NO POR COMODIDAD
    ----------------------------------------------------------
    Las **vivas** pasan por `reservas.crear_reserva`, que es CU-22 entero: valida
    el horario de la tienda, la capacidad del probador y el stock, y aparta las
    unidades. Es la unica forma de que una reserva PENDIENTE del dataset sea una
    que el sistema habria aceptado.

    Las **historicas** no pueden: el servicio rechaza toda franja en el pasado
    (excepcion E4), que es exactamente lo que una reserva del mes pasado tiene.
    Asi que la fila se arma aqui, pero el stock se mueve igual con los servicios
    de P4 y en la misma secuencia que usa CU-24 --- apartar, liberar, y descontar
    solo si el cliente se la llevo ---, de modo que el saldo de cada existencia
    sigue siendo la suma de sus movimientos. Una reserva historica escrita sin
    esos movimientos dejaria la tabla `existencia` diciendo una cosa y su
    historial otra, que es el unico invariante que P4 promete.
    """
    if db.scalar(select(func.count()).select_from(Reserva)):
        print("  = ya hay reservas: se saltea el bloque")
        return {}

    activos = [c for c in clientes if c.usuario.activo]
    if not activos:
        return {}

    por_estado: dict[str, int] = {}

    # --- Historicas -------------------------------------------------------
    for _ in range(VOLUMEN["reservas_historicas"]):
        cliente = AZAR.choice(activos)
        sucursal = AZAR.choice(sucursales)
        lineas = _prendas_con_stock(db, sucursal.id, AZAR.randrange(1, 4))
        if not lineas:
            continue

        inicio, fin = _franja_pasada(sucursal)
        estado = AZAR.choices(
            ["ATENDIDA", "CANCELADA", "EXPIRADA"], weights=[55, 25, 20]
        )[0]
        creada = inicio - timedelta(hours=AZAR.randrange(2, 48))
        desde = _ultimo_movimiento(db)

        try:
            reserva = Reserva(
                cliente_id=cliente.id,
                sucursal_id=sucursal.id,
                franja_inicio=inicio,
                franja_fin=fin,
                estado=estado,
                observacion=(
                    "Cancelada por el cliente" if estado == "CANCELADA" else None
                ),
                creado_en=creada,
                actualizado_en=fin,
            )
            db.add(reserva)
            db.flush()

            for variante_id, cantidad in lineas:
                comun = {
                    "variante_id": variante_id,
                    "sucursal_id": sucursal.id,
                    "cantidad": cantidad,
                    "usuario_id": cliente.usuario_id,
                }
                inventario.apartar_para_reserva(
                    db, **comun, motivo=f"Reserva #{reserva.id}"
                )

                resultado = None
                if estado == "ATENDIDA":
                    resultado = AZAR.choices(["LLEVA", "NO_LLEVA"], weights=[60, 40])[0]
                inventario.liberar_de_reserva(
                    db, **comun, motivo=f"Reserva #{reserva.id} atendida"
                )
                if resultado == "LLEVA":
                    inventario.descontar_por_venta(
                        db, **comun, motivo=f"Venta de la reserva #{reserva.id}"
                    )

                db.add(
                    DetalleReserva(
                        reserva_id=reserva.id,
                        variante_id=variante_id,
                        cantidad=cantidad,
                        resultado_prueba=resultado,
                        creado_en=creada,
                        actualizado_en=fin,
                    )
                )
            db.commit()
        except inventario.ErrorDeInventario:
            # Otra reserva de este mismo seed se llevo las ultimas unidades. No
            # es un fallo: es la condicion que el sistema tiene que rechazar.
            db.rollback()
            continue

        _retrasar_movimientos(db, desde, fin)
        por_estado[estado] = por_estado.get(estado, 0) + 1

    # --- Vivas ------------------------------------------------------------
    for _ in range(VOLUMEN["reservas_vivas"]):
        cliente = AZAR.choice(activos)
        sucursal = AZAR.choice(sucursales)
        duracion = AZAR.choice([30, 45, 60])
        inicio = _franja_futura(sucursal, duracion)
        if inicio is None:
            continue
        lineas = _prendas_con_stock(db, sucursal.id, AZAR.randrange(1, 4))
        if not lineas:
            continue

        try:
            salida = reservas.crear_reserva(
                db,
                ReservaCrearIn(
                    sucursal_id=sucursal.id,
                    franja_inicio=inicio,
                    franja_fin=inicio + timedelta(minutes=duracion),
                    lineas=[
                        LineaReservaIn(variante_id=v, cantidad=c) for v, c in lineas
                    ],
                ),
                usuario_id=cliente.usuario_id,
            )
        except reservas.ErrorDeReservas:
            # Franja llena, sin vestidores libres o sin stock. Son las tres
            # excepciones de CU-22 y aca significan que el dataset ya cargo esa
            # franja: se prueba con otra.
            db.rollback()
            continue

        estado = "PENDIENTE"
        if AZAR.random() < 0.35:
            reservas.preparar_reserva(db, salida.id, sucursal_id=sucursal.id)
            estado = "PREPARADA"
        por_estado[estado] = por_estado.get(estado, 0) + 1

    return por_estado


# --- Orquestacion ---------------------------------------------------------


def sembrar(db: Session) -> None:
    """Siembra el dataset de operacion. Requiere el catalogo ya sembrado."""
    hash_demo = _hash_de_demostracion()
    if hash_demo is None:
        print(
            "  ! DEMO_PASSWORD no esta definida: no se crea ninguna persona,\n"
            "    y sin personas no hay favoritos ni reservas. Definirla en\n"
            "    backend/.env y volver a ejecutar."
        )
        return

    roles = {r.nombre: r.id for r in db.scalars(select(Rol))}
    ciudades = list(db.scalars(select(Ciudad.id)))
    sucursales = list(db.scalars(select(Sucursal).where(Sucursal.activa.is_(True))))
    proveedores = list(db.scalars(select(Proveedor.id).where(Proveedor.activo.is_(True))))
    # Las hojas del arbol de categorias: son las que un cliente elige en su
    # perfil. Preferir «Mujer» y no «Blusas» no dice nada que el sistema pueda
    # usar despues.
    #
    # Hoja es la que NO TIENE HIJAS, no la que tiene padre. No son lo mismo: en
    # la taxonomia de la base desplegada, «Ropa Intima» y «Ropa de Descanso» son
    # raices sin hijas y cuelgan productos directamente. Mirando el padre se
    # quedaban fuera del selector del perfil justo las cuatro categorias que
    # mas ropa tienen.
    todas = list(db.scalars(select(Categoria)))
    con_hijas = {c.categoria_padre_id for c in todas if c.categoria_padre_id}
    hojas = [c for c in todas if c.id not in con_hijas]

    if not sucursales or "CLIENTE" not in roles:
        print("  ! falta el seed del Ciclo 1 y 2: no hay sucursales o no hay roles")
        return

    print("Sembrando el dataset de operacion...")

    creados = _clientes(db, roles["CLIENTE"], ciudades, hojas, hash_demo)
    print(f"  + clientes nuevos: {creados}")

    empleados = _empleados(db, roles, sucursales, hash_demo)
    print(f"  + empleados nuevos: {empleados}")

    # Cada movimiento lo firma el encargado de su sucursal; el administrador
    # solo cubre los locales que no tengan uno --- ver _encargados_por_sucursal.
    administrador = db.scalar(
        select(Usuario.id).where(Usuario.correo == settings.ADMIN_EMAIL)
    )
    resumen = _inventario(
        db, sucursales, proveedores, _encargados_por_sucursal(db), administrador
    )
    for clave, valor in resumen.items():
        print(f"  + {clave}: {valor}")

    clientes = list(
        db.scalars(
            select(Cliente).join(Usuario).where(Usuario.correo.like(f"%@{DOMINIO_DEMO}"))
        )
    )
    favoritos = _favoritos(db, clientes)
    print(f"  + favoritos nuevos: {favoritos}")

    por_estado = _reservas(db, clientes, sucursales)
    for estado, cuantas in sorted(por_estado.items()):
        print(f"  + reservas {estado}: {cuantas}")

    print("Dataset de operacion listo.")


def _base_desplegada() -> bool:
    """Reconoce la base de Railway o Supabase por la URL."""
    url = (settings.DATABASE_URL or "").lower()
    return "supabase" in url or "railway" in url or "rlwy.net" in url


def main() -> None:
    """Punto de entrada.

    Uso, desde backend/:

        python -m app.db.seed_operacion

    LA GUARDA DE LA BASE DESPLEGADA
    -------------------------------
    Se niega a correr contra Supabase o Railway salvo que se le insista con
    SEMBRAR_EN_DESPLEGADA=1. No es paranoia: el `.env` del proyecto apunta a
    Supabase, asi que la ejecucion sin pensar es justamente la que escribe medio
    millon de filas en la base que usa el tribunal. Es mas barato pedir una
    variable que deshacerlo.
    """
    import os

    if _base_desplegada() and os.getenv("SEMBRAR_EN_DESPLEGADA") != "1":
        print(
            "DATABASE_URL apunta a la base DESPLEGADA y este seed escribe miles\n"
            "de filas. Si es lo que se quiere:  SEMBRAR_EN_DESPLEGADA=1\n"
            "Si no, apuntar DATABASE_URL a la base local."
        )
        raise SystemExit(1)

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        sembrar(db)


if __name__ == "__main__":
    main()
