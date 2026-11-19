# ---------- Etapa 1: construccion (con herramientas de compilacion) ----------
FROM python:3.12-slim AS builder
WORKDIR /build
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Etapa 2: imagen final (sin herramientas de compilacion) ----------
FROM python:3.12-slim

ARG APP_VERSION=dev
ARG GIT_SHA=local
ARG BUILD_DATE=unknown

# Valores que /version leera en tiempo de ejecucion
ENV APP_VERSION=${APP_VERSION} \
    GIT_SHA=${GIT_SHA} \
    BUILD_DATE=${BUILD_DATE} \
    PORT=8000 \
    PYTHONUNBUFFERED=1

# Usuario sin privilegios
RUN useradd --system --uid 10001 --no-create-home appuser

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/app.py .

USER 10001
EXPOSE 8000

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 app:app"]
