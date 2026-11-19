#!/bin/bash
# Crea (o alinea) el usuario de la aplicacion en RDS, con TLS verificado y REQUIRE SSL.
# Se ejecuta como root en una instancia de produccion con:
#   aws ssm send-command --document-name AWS-RunShellScript (el texto de este archivo, sin secretos)
# Requisitos: pila 02-base con AccesoAdminDb=si mientras corre (luego volver a 'no').
#
# Ninguna contrasena aparece en el comando, en la salida ni en el historial de SSM:
# - la maestra se lee aqui de /akaispace/admin/DB_MASTER_PASSWORD (fuera del .env de la aplicacion);
# - la de la aplicacion se lee del .env que ya armo desplegar.sh (/akaispace/prod/DB_PASSWORD);
# - ambas van a archivos 0600 en una carpeta temporal que se borra al terminar.
set -euo pipefail
umask 077

source /opt/akaispace/ambiente.conf
cd /opt/akaispace

valor() { grep -m1 "^$1=" .env | cut -d= -f2-; }
DB_HOST=$(valor DB_HOST)
DB_NAME=$(valor DB_NAME)
DB_USER=$(valor DB_USER)
APP_PW=$(valor DB_PASSWORD)

[[ "$DB_NAME" =~ ^[A-Za-z0-9_]+$ && "$DB_USER" =~ ^[A-Za-z0-9_]+$ ]] || { echo "DB_NAME o DB_USER no validos"; exit 1; }
# token_urlsafe: solo letras, numeros, - y _ (seguro dentro de comillas simples de SQL)
[[ "$APP_PW" =~ ^[A-Za-z0-9_-]{20,}$ ]] || { echo "DB_PASSWORD vacia o con caracteres no esperados"; exit 1; }

MASTER_PW=$(/snap/bin/aws ssm get-parameter --region "$REGION" --name /akaispace/admin/DB_MASTER_PASSWORD \
  --with-decryption --query Parameter.Value --output text)
[[ -n "$MASTER_PW" ]] || { echo "No se pudo leer la contrasena maestra"; exit 1; }

TMP=$(mktemp -d)
trap 'shred -u "$TMP"/*.cnf "$TMP"/*.sql "$TMP"/*.log 2>/dev/null || true; rm -rf "$TMP"' EXIT

# Certificado de RDS: el mismo que usa la aplicacion (viene en la imagen web)
docker compose cp web:/app/certs/rds-global-bundle.pem "$TMP/ca.pem"

cat > "$TMP/admin.cnf" <<EOF
[client]
user=admin
password=$MASTER_PW
host=$DB_HOST
ssl-mode=VERIFY_IDENTITY
ssl-ca=/t/ca.pem
EOF
unset MASTER_PW

cat > "$TMP/usuario.sql" <<EOF
CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$APP_PW' REQUIRE SSL;
ALTER USER '$DB_USER'@'%' IDENTIFIED BY '$APP_PW' REQUIRE SSL;
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';
EOF

cat > "$TMP/revisar.sql" <<EOF
SELECT CONCAT('Servidor: MySQL ', VERSION());
SELECT CONCAT('TLS de esta conexion: ', VARIABLE_VALUE) FROM performance_schema.session_status WHERE VARIABLE_NAME = 'Ssl_version';
SELECT CONCAT('require_secure_transport = ', @@require_secure_transport);
SELECT CONCAT('Usuario ', user, '@', host, ' ssl_type=', ssl_type, ' plugin=', plugin) FROM mysql.user WHERE user = '$DB_USER';
SHOW GRANTS FOR '$DB_USER'@'%';
EOF

mysql() {
  docker run --rm -i --network host -v "$TMP":/t:ro mysql:8.4 \
    mysql --defaults-extra-file=/t/admin.cnf --batch --skip-column-names "$@"
}

docker pull -q mysql:8.4 >/dev/null
# Si MySQL devolviera un error que cite la sentencia, la contrasena se tapa antes de mostrarlo
if ! mysql < "$TMP/usuario.sql" 2> "$TMP/error.log"; then
  sed "s/$APP_PW/[oculta]/g" "$TMP/error.log"
  exit 1
fi
echo "Usuario $DB_USER listo (REQUIRE SSL, todos los privilegios sobre $DB_NAME)."
mysql < "$TMP/revisar.sql"
