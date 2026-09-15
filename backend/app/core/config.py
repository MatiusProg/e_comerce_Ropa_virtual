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
    # La base es Supabase (PostgreSQL gestionado); Railway solo hospeda la API
    # y la web. En produccion se carga la cadena del SESSION POOLER de Supabase
    # (puerto 5432), no la conexion directa. En local apunta al contenedor de
    # docker-compose. Ver backend/.env.example.
    DATABASE_URL: str = "postgresql+psycopg://violetboutique:violetboutique@localhost:5432/violetboutique"

    # --- Seguridad (RNF01) -----------------------------------------------
    JWT_SECRET_KEY: str = "cambiar-esta-clave-en-produccion"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ------------------------------------------------------------
    # Separadas por coma. En produccion: la URL de la web en Railway.
    CORS_ORIGINS: str = "http://localhost:4200,http://localhost:8100"

    # --- Reservas (regla de negocio del paquete P6) ----------------------
    #
    # Cuanto aguanta una reserva DESPUES de que su franja termino, antes de que
    # CU-25 la expire y devuelva el stock. Es la tolerancia para el cliente que
    # llega tarde.
    RESERVA_VIGENCIA_HORAS: int = 24

    # Con cuanta anticipacion se puede reservar. Existe para proteger el
    # inventario, no para incomodar al cliente: la reserva inmoviliza unidades
    # desde que se crea hasta que su franja vence, asi que reservar para dentro
    # de un mes dejaria stock apartado un mes. Tres dias es el equilibrio entre
    # planificar una visita y no congelar la vitrina (CU-22, excepcion E5).
    RESERVA_ANTICIPACION_MAXIMA_HORAS: int = 72

    # --- Pasarela de pago (P8, ciclo 3) ----------------------------------
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_SUCCESS_URL: str = "http://localhost:4200/pago/exito"
    STRIPE_CANCEL_URL: str = "http://localhost:4200/pago/cancelado"

    # --- Inteligencia artificial (P10, ciclo 3) --------------------------
    #
    # Los nombres NO llevan el proveedor adentro a proposito: con
    # ANTHROPIC_API_KEY, cambiar de proveedor obligaba a tocar el despliegue
    # ademas del codigo. El acuerdo del 11/09 lo fijo asi y .env.example ya lo
    # usaba; esto alinea la configuracion con el acuerdo y con el archivo.
    IA_PROVEEDOR: str = "gemini"
    IA_API_KEY: str = ""
    IA_MODELO: str = ""
    IA_MAX_PETICIONES_DIA: int = 50       # tope por usuario, control de costo

    # --- Correo saliente (CU-40 y CU-41, ciclo 3) ------------------------
    #
    # Misma leccion que la IA: los nombres no llevan la marca adentro, asi que
    # elegir proveedor es cambiar UNA variable en Railway y no tocar codigo.
    #
    # `consola` no envia nada: escribe el correo entero en el log. Es el valor
    # por defecto a proposito, porque permite construir y probar CU-41 completo
    # --- token de un solo uso, dos endpoints y dos pantallas --- sin haber
    # contratado ningun servicio. Cuando se elija uno, se agrega su modulo en
    # app/integrations/correo/ y se cambia esta variable.
    CORREO_PROVEEDOR: str = "consola"
    CORREO_API_KEY: str = ""

    # La direccion que figura como remitente. Es la trampa de los servicios
    # transaccionales: casi ninguno deja enviar desde una direccion cualquiera.
    # O se verifica un dominio propio, o se usa el dominio de prueba del
    # proveedor --- que en varios SOLO permite enviar a la casilla verificada
    # de la cuenta. Hay que averiguarlo ANTES de la demostracion.
    CORREO_REMITENTE: str = "no-responder@violetboutique.bo"
    CORREO_REMITENTE_NOMBRE: str = "Violet Boutique"

    # --- Recuperacion de contrasena (CU-41, RF39) ------------------------
    #
    # Cuanto vale el enlace. Corto a proposito: el enlace ES la credencial
    # mientras vive, y viaja por un correo que puede quedar abierto en una
    # maquina compartida. Media hora alcanza para leer el correo y cambiar la
    # contrasena, y no para mucho mas.
    RECUPERACION_VIGENCIA_MINUTOS: int = 30

    # A donde apunta el enlace del correo. Es la WEB, no la API: quien recibe
    # el correo tiene que aterrizar en el formulario de contrasena nueva. En
    # produccion es la URL publica de la web en Railway.
    WEB_BASE_URL: str = "http://localhost:4200"

    # --- Datos iniciales (app/db/seed.py) --------------------------------
    ADMIN_EMAIL: str = "admin@violetboutique.bo"
    ADMIN_PASSWORD: str = ""      # sin valor por defecto: ver seed.py

    # Contrasena unica de las personas de demostracion que crea
    # app/db/seed_operacion.py. Sigue la misma regla que ADMIN_PASSWORD y por
    # el mismo motivo: sin valor por defecto, porque un valor versionado seria
    # la credencial de quinientas cuentas en una base desplegada. Si falta, el
    # seed de operacion no crea ninguna persona y lo dice.
    DEMO_PASSWORD: str = ""

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
