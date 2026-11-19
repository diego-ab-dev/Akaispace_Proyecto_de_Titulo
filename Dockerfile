# Etapa 1: compila las dependencias (mysqlclient necesita gcc y los headers de MariaDB) en un entorno virtual
FROM python:3.12-slim-trixie AS compilar
ENV PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential default-libmysqlclient-dev pkg-config curl \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Certificado de RDS para TLS (curl queda solo en esta etapa)
RUN curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o /rds-global-bundle.pem

# Etapa 2: imagen final, sin compiladores ni headers
FROM python:3.12-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
# upgrade: parches de seguridad de Debian publicados después de la imagen base;
# libmariadb3: la biblioteca que usa mysqlclient al ejecutarse
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends libmariadb3 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=compilar /opt/venv /opt/venv
WORKDIR /app
COPY . .
# Certificado de RDS y archivos estáticos dentro de la imagen
COPY --from=compilar /rds-global-bundle.pem /app/certs/rds-global-bundle.pem
RUN mkdir -p /app/logs \
 && SECRET_KEY=solo-build DB_NAME=x DB_USER=x DB_PASSWORD=x DB_HOST=x ALLOWED_HOSTS=x \
    python manage.py collectstatic --noinput \
 && useradd --uid 1000 --create-home app && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["gunicorn", "Akaispace.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "/app/logs/gunicorn-access.log", "--error-logfile", "/app/logs/gunicorn-error.log", "--capture-output"]
