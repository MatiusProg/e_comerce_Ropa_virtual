"""Motor y sesion de SQLAlchemy."""

from collections.abc import Generator

from sqlalchemy import create_engine
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

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: una sesion por peticion, siempre cerrada."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
