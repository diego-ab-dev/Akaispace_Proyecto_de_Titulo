# Akaispace

Tienda web de Akaispace (Django 5.2 + MySQL 8.4).

## Acceso rápido

### Usuarios de prueba

Los crea `python manage.py seed_demo` (solo existen en tu base local).

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | admin@gmail.com | Akaispace-Admin-2026 |
| Cliente | user@gmail.com | Akaispace-Cliente-2026 |

### Tarjetas de prueba Webpay

| Tarjeta | Número | CVV | Resultado |
|---|---|---|---|
| VISA crédito | 4051 8856 0044 6623 | 123 | Aprobada |
| Mastercard crédito | 5186 0595 5959 0568 | 123 | Rechazada |

- Vencimiento: cualquier fecha futura.
- Si Webpay pide autenticación: RUT **11.111.111-1**, clave **123**.
- Más tarjetas en [Transbank Developers](https://www.transbankdevelopers.cl/documentacion/como_empezar#tarjetas-de-prueba).

### Comandos útiles

| Comando | Para qué |
|---|---|
| `python manage.py runserver` | Levantar el sitio en http://127.0.0.1:8000/ |
| `python manage.py axes_reset` | Desbloquear el login (se bloquea 15 min tras 5 intentos fallidos) |
| `python manage.py seed_demo` | Recargar productos de ejemplo y restablecer los usuarios de prueba |
| `python manage.py createsuperuser` | Crear otro administrador |

---

## Uso diario

```powershell
cd C:\Proyectos\Akaispace_Proyecto_de_Titulo
.\venv\Scripts\activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

`pip install` y `migrate` no hacen nada si no hubo cambios, así que siempre es seguro ejecutarlos.

---

## Instalación desde cero (Windows)

### Requisitos

| Programa | Versión | Dónde obtenerlo |
|---|---|---|
| Git | Reciente | https://git-scm.com/download/win |
| Python | **3.12** | https://www.python.org/downloads/windows |
| MySQL Community Server | **8.4 LTS** | https://dev.mysql.com/downloads/mysql |

- **No usar XAMPP**: su MySQL es MariaDB 10.4 y Django 5.2 no lo soporta.
- **No usar el Python de Microsoft Store.**
- **No clonar dentro de OneDrive** (Escritorio/Documentos sincronizados): se vuelve muy lento.

### 1. Instalar Python 3.12

Instalador **Windows installer (64-bit)**, marcando **"Add python.exe to PATH"**. Reabre PowerShell y verifica con `py --list` (debe aparecer 3.12).

### 2. Instalar MySQL 8.4 LTS

Instalador MSI (no la versión "Innovation"), tipo **Typical**, y en el configurador:
**Development Computer**, puerto **3306**, crea y **anota** la contraseña de root, deja el servicio con inicio automático.

### 3. Clonar el proyecto

```powershell
mkdir C:\Proyectos
cd C:\Proyectos
git clone URL_DEL_REPOSITORIO
cd Akaispace_Proyecto_de_Titulo
```

### 4. Entorno virtual y librerías

```powershell
py -3.12 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Si `activate` da error de "execution policy", ejecuta una vez en PowerShell como administrador:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### 5. Crear la base de datos

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p
```

```sql
CREATE DATABASE db_akaispace CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
exit
```

### 6. Archivo `.env`

```powershell
Copy-Item .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
notepad .env
```

Pega la clave generada en `SECRET_KEY=` y tu contraseña de MySQL en `DB_PASSWORD=` (sin comillas). El `.env` **no se sube a GitHub**. `DEBUG=True` es solo para desarrollo.

### 7. Cargar datos y ejecutar

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py seed_catalogo
python manage.py runserver
```

- `seed_demo`: productos de ejemplo, portada y usuarios de prueba.
- `seed_catalogo`: catálogo de ~115 productos (`appPrincipal/fixtures/catalogo.csv`) usado por las recomendaciones; al final calcula las similitudes.

Ambos se pueden repetir sin duplicar datos.

---

## Configuración opcional (`.env`)

Todo funciona sin esto; las variables están comentadas en `.env.example`.

| Función | Variables | Sin configurar |
|---|---|---|
| Envío real de correos | `EMAIL_BACKEND`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | Los correos se muestran en la terminal de `runserver` |
| Login con Google | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | No aparece el botón "Continuar con Google" |
| Webpay real | `WEBPAY_AMBIENTE=produccion`, `WEBPAY_CODIGO_COMERCIO`, `WEBPAY_API_KEY` | Usa el ambiente de integración (sin cobros reales) |

- **Correos**: la contraseña de aplicación de la cuenta de pruebas no está en el repositorio; pídesela al encargado del proyecto.
- **Google**: crea un ID de cliente OAuth (*Aplicación web*) en [Google Cloud Console](https://console.cloud.google.com/) con la URI de redirección `http://localhost:8000/accounts/google/login/callback/`.

Reinicia `runserver` después de cambiar el `.env`.

---

## Tareas programadas (solo servidor)

| Frecuencia | Comando | Qué hace |
|---|---|---|
| Diaria | `python manage.py mantener_recomendaciones` | Borra navegación de más de 24 meses y recalcula similitudes |
| Cada 15 min | `python manage.py reenviar_confirmaciones` | Reenvía confirmaciones de compra que fallaron |

Ejemplo cron: `*/15 * * * * cd /ruta/del/proyecto && venv/bin/python manage.py reenviar_confirmaciones`

---

## Pruebas y calidad

```powershell
pip install -r requirements-dev.txt
python manage.py test appPrincipal
coverage run manage.py test appPrincipal; coverage report
bandit -r . --ini .bandit
pip-audit -r requirements.txt
```

## Notebooks

Prototipos para el informe en `notebooks/` (no los necesita la web):

```powershell
pip install -r notebooks/requirements.txt
jupyter notebook notebooks
```

## Estructura

| Qué | Dónde |
|---|---|
| Vistas de la tienda / del panel | `appPrincipal/views/` / `appPrincipal/views/panel/` |
| Plantillas base | `templates/base.html`, `base_tienda.html`, `admin_panel/base_admin.html` |
| Recomendaciones (HU-07) | `appPrincipal/recomendaciones.py` |
| Reportes y KPI (HU-10) | `appPrincipal/reportes.py` |
| Rutas | `Akaispace/urls.py` |

---

## Solución de problemas

| Error | Solución |
|---|---|
| `No module named ...` | Activar el entorno (`.\venv\Scripts\activate`) y `pip install -r requirements.txt` |
| `py` no se reconoce | Reinstalar Python 3.12 desde python.org |
| `MariaDB 10.5 or later is required` | Está conectando al MySQL de XAMPP: detenerlo e iniciar MySQL 8.4 |
| `Access denied for user 'root'` | Revisar `DB_PASSWORD` en `.env` |
| `Unknown database 'db_akaispace'` | Repetir el paso 5 |
| `SECRET_KEY not found` | Agregarla al `.env` (paso 6) |
| Página sin estilos ni imágenes | Poner `DEBUG=True` en `.env` |
| `Table '...' doesn't exist` | `python manage.py migrate` |
| `SMTPAuthenticationError` | Usar la contraseña de aplicación, no la normal de Gmail |
| "Demasiados intentos fallidos" | Esperar 15 min o `python manage.py axes_reset` |
