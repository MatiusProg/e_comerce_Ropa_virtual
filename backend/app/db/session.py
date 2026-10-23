"""Motor y sesion de SQLAlchemy."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _normalizar_url(url: str) -> str:
    """Railway entrega DATABASE_URL con el esquema 'postgresql://'.

    SQLAlchemy necesita saber que controlador usar. Este proyecto usa psycopg 3,
    asi que la URL debe decir 'postgresql+psycopg://'.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(
    _normalizar_url(settings.DATABASE_URL),
    pool_pre_ping=True,      # descarta conexiones muertas por inactividad
    echo=settings.DEBUG and not settings.es_produccion,
)



def asumir_rol_de_la_aplicacion(motor, rol: str) -> None:
    """Cada conexion nueva asume el rol sin BYPASSRLS (ver app/core/tenencia.py).

    Se hace por conexion y no por sesion: el pool reutiliza conexiones, y un
    `SET ROLE` (sin LOCAL) dura lo que dura la conexion.
    """

    @event.listens_for(motor, "connect")
    def _asumir(conexion_dbapi, _registro):
        cursor = conexion_dbapi.cursor()
        cursor.execute(f'SET ROLE "{rol}"')
        cursor.close()
        # psycopg abre una transaccion implicita con el SET; se cierra para que
        # la conexion entre limpia al pool.
        conexion_dbapi.commit()


if settings.APP_DB_ROLE:
    asumir_rol_de_la_aplicacion(engine, settings.APP_DB_ROLE)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: una sesion por peticion, siempre cerrada."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
