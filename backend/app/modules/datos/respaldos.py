"""
P18 - Datos de la empresa / CU-40 Gestionar copias de seguridad (RF-60 a RF-63)

LA COPIA
--------
Un JSON con las filas de cada tabla de la empresa (las de `TABLAS_DE_EMPRESA`
menos `FUERA_DE_LA_COPIA`), leídas con la sesión de la petición: el RLS
garantiza que no entra nada de otra empresa. Lleva:

- `empresa_id`, para que no se pueda restaurar en otra empresa (RN-19);
- `firma`: HMAC-SHA256 del contenido con la clave del servidor. Un SHA-256 a
  secas lo puede recalcular cualquiera que edite el archivo; la firma no, y
  así se detecta un archivo alterado (RF-62, RNF17).

Del archivo entregado se guarda además su SHA-256, para reconocerlo en el
historial.

MANUAL Y AUTOMÁTICA (RF-60, RF-61, RN-18, RNF17)
------------------------------------------------
- La MANUAL la pide el administrador y se descarga: no queda en el servidor,
  solo su registro. El plan limita cada cuánto (`respaldo_intervalo_horas`:
  semanal, diaria o a voluntad).
- La AUTOMATICA la crea `POST /mantenimiento/respaldos` (pensado para un cron,
  idempotente): una cada `respaldo_intervalo_horas` (diaria si el plan no lo
  limita), cifrada con Fernet, y se conservan solo las últimas
  `respaldo_retencion`. No gasta la cuota de las manuales.

LA RESTAURACIÓN (RF-62, RN-18, RN-19)
------------------------------------
Reemplaza TODOS los datos de la empresa por los de la copia, en una sola
transacción: borra en el orden inverso de las dependencias, inserta en el
directo, y si algo falla no cambia nada. No se mezcla con lo actual. El plan
nunca la limita. Queda en `restauracion` (y en la bitácora, por el middleware)
con quién, cuándo y de qué archivo.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.orm import Session

from app.core import tiempo
from app.core.config import settings
from app.modules.datos import tablas
from app.modules.datos.models import Respaldo, Restauracion
from app.modules.plataforma import verificador
from app.modules.plataforma.models import Empresa
from app.modules.seguridad.models import Usuario

FORMATO = "violet-boutique/respaldo"
VERSION = 1

#: Si el plan no fija intervalo (Empresarial: «a voluntad»), la automática
#: igual sale una vez por día.
INTERVALO_AUTOMATICO_POR_OMISION = 24
RETENCION_POR_OMISION = 7


class ErrorDeDatos(Exception):
    def __init__(self, mensaje: str, codigo: int = 422) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


# =====================================================================
#  Firma y cifrado
# =====================================================================

def _secretos() -> list[bytes]:
    """La clave de las copias primero; después, la del token, con la que se
    firmaron las copias hechas antes de que existiera `RESPALDO_SECRET`.

    Se firma y cifra siempre con la primera; se acepta cualquiera al leer.
    """
    propia = settings.RESPALDO_SECRET.strip()
    heredada = settings.JWT_SECRET_KEY
    if not propia or propia == heredada:
        return [heredada.encode()]
    return [propia.encode(), heredada.encode()]


def _canonico(cuerpo: dict) -> bytes:
    return json.dumps(cuerpo, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _firma_con(secreto: bytes, cuerpo: dict) -> str:
    return hmac.new(secreto, _canonico(cuerpo), hashlib.sha256).hexdigest()


def _firmar(cuerpo: dict) -> str:
    return _firma_con(_secretos()[0], cuerpo)


def _firma_valida(firma: str, cuerpo: dict) -> bool:
    return any(hmac.compare_digest(firma, _firma_con(s, cuerpo)) for s in _secretos())


def _fernet() -> MultiFernet:
    # Una clave de cifrado derivada de cada secreto. MultiFernet cifra con la
    # primera y descifra con cualquiera: las automáticas viejas se siguen
    # pudiendo restaurar después de configurar `RESPALDO_SECRET`.
    return MultiFernet([
        Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"violet-respaldos:" + s).digest()))
        for s in _secretos()
    ])


# =====================================================================
#  Armar la copia
# =====================================================================

def _empresa(db: Session, empresa_id: int) -> Empresa:
    return db.get(Empresa, empresa_id)


def armar(db: Session, empresa_id: int) -> tuple[bytes, dict[str, int], datetime]:
    """El archivo de la copia, sus filas por tabla y el momento de los datos."""
    generado = tiempo.ahora()
    datos: dict[str, list[dict]] = {}
    for tabla in tablas.tablas_de_empresa(tablas.FUERA_DE_LA_COPIA):
        datos[tabla.name] = [
            {k: tablas.a_json(v) for k, v in fila.items()} for fila in tablas.filas_de(db, tabla)
        ]
    # `usuario` no es tabla de empresa (el cliente es de la plataforma), pero
    # el rol propio de cada persona del personal sí es dato de la empresa.
    roles_del_personal = [
        {"usuario_id": u, "rol_empresa_id": r}
        for u, r in db.execute(
            select(Usuario.id, Usuario.rol_empresa_id).where(
                Usuario.empresa_id == empresa_id, Usuario.rol_empresa_id.is_not(None)
            )
        ).all()
    ]
    empresa = _empresa(db, empresa_id)
    cuerpo = {
        "formato": FORMATO,
        "version": VERSION,
        "empresa_id": empresa_id,
        "empresa_slug": empresa.slug if empresa else None,
        "generado_en": generado.isoformat(),
        "tablas": datos,
        "roles_del_personal": roles_del_personal,
    }
    archivo = json.dumps({**cuerpo, "firma": _firmar(cuerpo)}, ensure_ascii=False).encode()
    return archivo, {nombre: len(filas) for nombre, filas in datos.items()}, generado


def _nombre_de_archivo(db: Session, empresa_id: int, momento: datetime, tipo: str) -> str:
    empresa = _empresa(db, empresa_id)
    slug = empresa.slug if empresa else f"empresa-{empresa_id}"
    sufijo = "" if tipo == "MANUAL" else "-auto"
    return f"respaldo-{slug}-{momento.strftime('%Y%m%d-%H%M%S')}{sufijo}.json"


# =====================================================================
#  El plan (RN-18)
# =====================================================================

def _ajustes(db: Session) -> tuple[int | None, int, str]:
    """(intervalo de las manuales en horas o None, retención, nombre del plan)."""
    plan = verificador.plan_vigente(db)
    funciones = plan.funciones or {}
    retencion = funciones.get("respaldo_retencion") or RETENCION_POR_OMISION
    return funciones.get("respaldo_intervalo_horas"), int(retencion), plan.nombre


def _ultima(db: Session, tipo: str) -> datetime | None:
    return db.scalar(select(func.max(Respaldo.creado_en)).where(Respaldo.tipo == tipo))


def _texto_intervalo(horas: int) -> str:
    if horas % 168 == 0:
        semanas = horas // 168
        return "una por semana" if semanas == 1 else f"una cada {semanas} semanas"
    if horas % 24 == 0:
        dias = horas // 24
        return "una por día" if dias == 1 else f"una cada {dias} días"
    return f"una cada {horas} horas"


def proxima_manual(db: Session) -> datetime | None:
    """Desde cuándo se puede pedir la próxima copia manual; None = ya."""
    try:
        intervalo, _, _ = _ajustes(db)
    except verificador.SinSuscripcionVigente:
        return None
    ultima = _ultima(db, "MANUAL")
    if intervalo is None or ultima is None:
        return None
    proxima = ultima + timedelta(hours=intervalo)
    return proxima if proxima > tiempo.ahora() else None


# =====================================================================
#  RF-60 · Copia manual
# =====================================================================

def manual(db: Session, empresa_id: int, usuario_id: int) -> tuple[bytes, str]:
    """La copia que se descarga. **Hace commit** (solo del registro)."""
    intervalo, _, plan = _ajustes(db)
    proxima = proxima_manual(db)
    if proxima is not None:
        raise verificador.RechazoDelPlan(
            f"El plan {plan} permite {_texto_intervalo(intervalo)} copia manual. "
            f"La próxima se puede generar desde el {tiempo.formatear(proxima, '%d/%m %H:%M')}. "
            "Las copias automáticas siguen saliendo igual."
        )
    archivo, filas, momento = armar(db, empresa_id)
    nombre = _nombre_de_archivo(db, empresa_id, momento, "MANUAL")
    db.add(Respaldo(
        tipo="MANUAL", archivo=nombre, tamano_bytes=len(archivo),
        sha256=hashlib.sha256(archivo).hexdigest(), filas=filas, contenido=None,
        creado_por=usuario_id,
    ))
    db.commit()
    return archivo, nombre


# =====================================================================
#  RF-61 · Copia automática
# =====================================================================

def automatica(db: Session, empresa_id: int) -> dict:
    """Crea la automática si ya toca y poda las viejas. Idempotente. **Commit.**"""
    try:
        intervalo, retencion, _ = _ajustes(db)
    except verificador.SinSuscripcionVigente:
        return {"creada": False, "motivo": "La empresa no tiene suscripción vigente.",
                "borradas": 0}
    intervalo = intervalo or INTERVALO_AUTOMATICO_POR_OMISION
    ultima = _ultima(db, "AUTOMATICA")
    creada = False
    motivo = None
    if ultima is not None and tiempo.ahora() - ultima < timedelta(hours=intervalo):
        motivo = f"La última automática es de hace menos de {intervalo} horas."
    else:
        archivo, filas, momento = armar(db, empresa_id)
        db.add(Respaldo(
            tipo="AUTOMATICA", archivo=_nombre_de_archivo(db, empresa_id, momento, "AUTOMATICA"),
            tamano_bytes=len(archivo), sha256=hashlib.sha256(archivo).hexdigest(), filas=filas,
            contenido=_fernet().encrypt(archivo), creado_por=None,
        ))
        db.flush()
        creada = True

    # Se conservan solo las últimas que el plan indica.
    sobrantes = db.scalars(
        select(Respaldo.id)
        .where(Respaldo.tipo == "AUTOMATICA")
        .order_by(Respaldo.creado_en.desc(), Respaldo.id.desc())
        .offset(retencion)
    ).all()
    if sobrantes:
        db.execute(delete(Respaldo).where(Respaldo.id.in_(sobrantes)))
    db.commit()
    return {"creada": creada, "motivo": motivo, "borradas": len(sobrantes)}


def contenido_de(db: Session, respaldo_id: int) -> tuple[bytes, Respaldo]:
    """El JSON de una automática guardada, descifrado."""
    respaldo = db.get(Respaldo, respaldo_id)
    if respaldo is None:
        raise ErrorDeDatos("La copia no existe.", 404)
    if respaldo.contenido is None:
        raise ErrorDeDatos(
            "Las copias manuales no se guardan en el servidor: se descargaron al generarlas.",
            409,
        )
    try:
        return _fernet().decrypt(respaldo.contenido), respaldo
    except InvalidToken as e:
        raise ErrorDeDatos("La copia guardada no se pudo descifrar.", 500) from e


# =====================================================================
#  RF-62 · Restaurar
# =====================================================================

def _leer(archivo: bytes, empresa_id: int) -> dict:
    try:
        cuerpo = json.loads(archivo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ErrorDeDatos("El archivo no es una copia de seguridad (no es JSON).") from e
    if not isinstance(cuerpo, dict) or cuerpo.get("formato") != FORMATO:
        raise ErrorDeDatos("El archivo no es una copia de seguridad de Violet Boutique.")
    if cuerpo.get("version") != VERSION:
        raise ErrorDeDatos("La copia es de una versión que esta instalación no sabe leer.")
    firma = cuerpo.pop("firma", None)
    if not isinstance(firma, str) or not _firma_valida(firma, cuerpo):
        raise ErrorDeDatos("La copia fue alterada o está dañada: su firma no coincide.")
    if cuerpo.get("empresa_id") != empresa_id:
        raise ErrorDeDatos("La copia es de otra empresa: solo se restaura en la suya.")
    return cuerpo


def restaurar(
    db: Session,
    archivo: bytes,
    *,
    nombre: str,
    empresa_id: int,
    usuario_id: int,
    origen: str = "ARCHIVO",
    respaldo_id: int | None = None,
) -> Restauracion:
    """Reemplaza los datos de la empresa por los de la copia. **Commit.**

    Todo o nada: si una fila no entra, se deshace todo y los datos quedan
    como estaban.
    """
    cuerpo = _leer(archivo, empresa_id)
    orden = tablas.tablas_de_empresa(tablas.FUERA_DE_LA_COPIA)
    conocidas = {t.name: t for t in orden}
    datos: dict = cuerpo.get("tablas") or {}
    for nombre_tabla, filas in datos.items():
        tabla = conocidas.get(nombre_tabla)
        if tabla is None:
            raise ErrorDeDatos(f"La copia trae una tabla que no se restaura: {nombre_tabla}.")
        columnas = set(tabla.columns.keys())
        for fila in filas[:1]:
            sobran = set(fila) - columnas
            if sobran:
                raise ErrorDeDatos(
                    f"La copia es de otra versión: {nombre_tabla} trae {', '.join(sorted(sobran))}."
                )

    try:
        # 1. Borrar lo actual, de las que apuntan a las apuntadas.
        for tabla in reversed(orden):
            db.execute(delete(tabla).where(tabla.c.empresa_id == empresa_id))

        # 2. Reponer la copia, de las apuntadas a las que apuntan. Las columnas
        #    que apuntan a la MISMA tabla (la categoría madre) se ponen
        #    después, cuando ya están todas las filas.
        filas_por_tabla: dict[str, int] = {}
        for tabla in orden:
            filas = datos.get(tabla.name) or []
            filas_por_tabla[tabla.name] = len(filas)
            if not filas:
                continue
            propias = [fk.parent.name for fk in tabla.foreign_keys if fk.column.table is tabla]
            listas = []
            diferidas = []
            for fila in filas:
                valores = {
                    c.name: tablas.de_json(c, fila[c.name])
                    for c in tabla.columns
                    if c.name in fila
                }
                aparte = {col: valores.pop(col) for col in propias if valores.get(col) is not None}
                for col in aparte:
                    valores[col] = None
                if aparte:
                    diferidas.append((valores, aparte))
                listas.append(valores)
            db.execute(insert(tabla), listas)
            clave = list(tabla.primary_key.columns)
            for valores, aparte in diferidas:
                condicion = [c == valores[c.name] for c in clave]
                db.execute(update(tabla).where(*condicion).values(**aparte))

        # 3. El rol propio de cada persona del personal (CU-41).
        for asignacion in cuerpo.get("roles_del_personal") or []:
            db.execute(
                update(Usuario)
                .where(Usuario.id == asignacion["usuario_id"], Usuario.empresa_id == empresa_id)
                .values(rol_empresa_id=asignacion["rol_empresa_id"])
            )

        registro = Restauracion(
            origen=origen,
            archivo=nombre[:120],
            sha256=hashlib.sha256(archivo).hexdigest(),
            datos_del=datetime.fromisoformat(cuerpo["generado_en"]),
            filas=filas_por_tabla,
            respaldo_id=respaldo_id,
            restaurado_por=usuario_id,
        )
        db.add(registro)
        db.commit()
    except ErrorDeDatos:
        db.rollback()
        raise
    except Exception as e:  # noqa: BLE001 - cualquier fallo deshace todo
        db.rollback()
        detalle = getattr(e, "orig", e)
        raise ErrorDeDatos(
            f"No se pudo restaurar y no se cambió nada. Detalle: {str(detalle)[:300]}"
        ) from e
    return registro


def restaurar_copia_guardada(
    db: Session, respaldo_id: int, *, empresa_id: int, usuario_id: int
) -> Restauracion:
    archivo, respaldo = contenido_de(db, respaldo_id)
    return restaurar(
        db, archivo, nombre=respaldo.archivo, empresa_id=empresa_id, usuario_id=usuario_id,
        origen="COPIA", respaldo_id=respaldo.id,
    )


# =====================================================================
#  RF-63 · Historial
# =====================================================================

def historial(db: Session) -> dict:
    nombres = {
        u: f"{n} {a}".strip()
        for u, n, a in db.execute(select(Usuario.id, Usuario.nombres, Usuario.apellidos)).all()
    }
    copias = db.scalars(select(Respaldo).order_by(Respaldo.creado_en.desc(), Respaldo.id.desc()))
    restauraciones = db.scalars(
        select(Restauracion).order_by(Restauracion.creado_en.desc(), Restauracion.id.desc())
    )
    try:
        intervalo, retencion, plan = _ajustes(db)
    except verificador.SinSuscripcionVigente:
        intervalo, retencion, plan = None, RETENCION_POR_OMISION, None
    return {
        "plan": plan,
        "intervalo_manual_horas": intervalo,
        "retencion_automaticas": retencion,
        "proxima_manual": proxima_manual(db),
        "copias": [
            {
                "id": c.id, "tipo": c.tipo, "archivo": c.archivo, "tamano_bytes": c.tamano_bytes,
                "sha256": c.sha256, "filas": c.filas, "creado_en": c.creado_en,
                "creado_por": nombres.get(c.creado_por) if c.creado_por else None,
                "descargable": c.contenido is not None,
            }
            for c in copias
        ],
        "restauraciones": [
            {
                "id": r.id, "origen": r.origen, "archivo": r.archivo, "sha256": r.sha256,
                "datos_del": r.datos_del, "filas": r.filas, "creado_en": r.creado_en,
                "restaurado_por": nombres.get(r.restaurado_por) if r.restaurado_por else None,
            }
            for r in restauraciones
        ],
    }
