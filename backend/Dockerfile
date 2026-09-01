# FashionStore - API REST
# Imagen usada tanto en local (docker compose) como en Railway.

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias primero: si no cambian, Docker reutiliza la capa y el build
# en Railway baja de minutos a segundos.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Punto de montaje del volumen persistente de Railway para las imagenes de
# producto. El sistema de archivos del contenedor es efimero: lo que no este
# en el volumen se pierde en cada despliegue.
RUN mkdir -p /app/media

EXPOSE 8000

# Railway inyecta $PORT. En local, docker-compose fija PORT=8000.
CMD ["sh", "-c", "alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
