FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential default-libmysqlclient-dev pkg-config curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Certificado de RDS para TLS y archivos estáticos dentro de la imagen
RUN mkdir -p /app/certs /app/logs \
 && curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o /app/certs/rds-global-bundle.pem \
 && SECRET_KEY=solo-build DB_NAME=x DB_USER=x DB_PASSWORD=x DB_HOST=x ALLOWED_HOSTS=x \
    python manage.py collectstatic --noinput \
 && useradd --uid 1000 --create-home app && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["gunicorn", "Akaispace.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "/app/logs/gunicorn-access.log", "--error-logfile", "/app/logs/gunicorn-error.log", "--capture-output"]
