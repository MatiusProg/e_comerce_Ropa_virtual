"""Configuracion de la aplicacion.

Toda la configuracion entra por variables de entorno. Ningun secreto se
versiona en el repositorio: ver backend/.env.example para los nombres.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Aplicacion ------------------------------------------------------
    ENTORNO: str = "desarrollo"           # desarrollo | produccion
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # --- Base de datos ---------------------------------------------------
    # Railway inyecta DATABASE_URL automaticamente al vincular el servicio
    # PostgreSQL. En local apunta al contenedor de docker-compose.
    DATABASE_URL: str = "postgresql+psycopg://fashionstore:fashionstore@localhost:5432/fashionstore"

    # --- Seguridad (RNF01) -----------------------------------------------
    JWT_SECRET_KEY: str = "cambiar-esta-clave-en-produccion"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ------------------------------------------------------------
    # Separadas por coma. En produccion: la URL de la web en Railway.
    CORS_ORIGINS: str = "http://localhost:4200,http://localhost:8100"

    # --- Reservas (regla de negocio del paquete P6) ----------------------
    RESERVA_VIGENCIA_HORAS: int = 24      # tras la franja horaria, expira

    # --- Pasarela de pago (P8, ciclo 3) ----------------------------------
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_SUCCESS_URL: str = "http://localhost:4200/pago/exito"
    STRIPE_CANCEL_URL: str = "http://localhost:4200/pago/cancelado"

    # --- Inteligencia artificial (P10, ciclo 3) --------------------------
    ANTHROPIC_API_KEY: str = ""
    IA_MODELO: str = "claude-opus-5"
    IA_MAX_PETICIONES_DIA: int = 50       # tope por usuario, control de costo

    # --- Almacenamiento de imagenes --------------------------------------
    # Volumen persistente de Railway montado en el contenedor.
    MEDIA_ROOT: str = "/app/media"
    MEDIA_URL: str = "/media"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def es_produccion(self) -> bool:
        return self.ENTORNO.lower() == "produccion"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
