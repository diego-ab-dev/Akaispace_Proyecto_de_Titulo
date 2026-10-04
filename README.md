# Guía de instalación y uso: Proyecto Akaispace

Guía para dejar el proyecto funcionando desde cero en un computador con Windows.

## Requisitos

| Programa | Versión | Dónde obtenerlo |
|---|---|---|
| Git | Cualquiera reciente | https://git-scm.com/download/win |
| Python | **3.12** | https://www.python.org/downloads/windows |
| MySQL Community Server | **8.4 LTS** | https://dev.mysql.com/downloads/mysql |

**Importante:**

- **No usar XAMPP.** Su MySQL es en realidad MariaDB 10.4, versión que Django 5.2 ya no soporta. Si tienes XAMPP instalado, deja su MySQL detenido (botón *Stop* en el panel de XAMPP).
- **No usar el Python de Microsoft Store.** Instala Python 3.12 desde python.org.
- **No clonar el proyecto dentro de OneDrive** (por ejemplo, en el Escritorio o Documentos si están sincronizados). OneDrive intenta sincronizar los miles de archivos del entorno virtual y vuelve todo lento.

---

## Paso 1: Instalar Python 3.12

1. Descarga el **Windows installer (64-bit)** de la versión 3.12 más reciente.
2. Al abrir el instalador, marca abajo la casilla **"Add python.exe to PATH"** y presiona **Install Now**.
3. Cierra y vuelve a abrir PowerShell.
4. Verifica la instalación ejecutando:

```powershell
py --list
```

Debe aparecer una línea con **3.12**.

## Paso 2: Instalar MySQL 8.4 LTS

1. Descarga el instalador MSI de **MySQL Community Server 8.4.x LTS** (no la versión "Innovation").
2. En **Choose Setup Type**, elige **Typical**.
3. Al terminar, deja marcada la casilla **"Run MySQL Configurator"** y presiona **Finish**.
4. En el configurador:
   - **Data Directory:** dejar la ruta por defecto.
   - **Type and Networking:** Config Type = **Development Computer**, puerto **3306**.
   - **Accounts and Roles:** crear la contraseña de **root** y **anotarla**.
   - **Windows Service:** dejar marcadas las opciones de servicio y de inicio automático.
   - **Sample Databases:** no marcar nada.
   - **Apply Configuration:** presionar **Execute** y luego **Finish**.

## Paso 3: Clonar el proyecto

En PowerShell:

```powershell
mkdir C:\Proyectos
cd C:\Proyectos
git clone URL_DEL_REPOSITORIO
cd Akaispace_Proyecto_de_Titulo
```

La URL se obtiene en GitHub, con el botón verde **Code**, pestaña **HTTPS**.

## Paso 4: Crear el entorno virtual e instalar librerías

En la carpeta del proyecto:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\activate
python --version
```

Debe decir **Python 3.12.x**, y la línea de la terminal debe comenzar con `(venv)`.

> **Si `activate` muestra un error sobre "scripts" o "execution policy":** abre PowerShell como administrador (clic derecho, "Ejecutar como administrador") y ejecuta una sola vez:
>
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
>
> Responde `S`, cierra esa ventana y vuelve a activar el entorno.

Luego instala las librerías:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Paso 5: Crear la base de datos

Con el entorno virtual activo o sin él (da lo mismo), entra a MySQL:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p
```

Ingresa la contraseña de root. Cuando aparezca `mysql>`, ejecuta:

```sql
CREATE DATABASE db_akaispace CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
exit
```

La base de datos queda vacía. Las tablas y los datos de prueba se crean en el Paso 7.

## Paso 6: Configurar la conexión (archivo .env)

La contraseña de la base de datos y la clave secreta de Django no se escriben en `settings.py`, sino en un archivo `.env` propio de cada computador. Este archivo **no se sube a GitHub**.

Crea tu `.env` copiando la plantilla:

```powershell
Copy-Item .env.example .env
notepad .env
```

Primero genera una clave secreta (con el entorno virtual activo):

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

En el Bloc de notas, pega esa clave en `SECRET_KEY=`, completa `DB_PASSWORD=` con tu contraseña de MySQL (sin comillas ni espacios) y guarda:

```
SECRET_KEY=la_clave_que_generaste
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=db_akaispace
DB_USER=root
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=3306
```

`DEBUG=True` es solo para desarrollo. En un servidor real va `DEBUG=False`, con una `SECRET_KEY` distinta y el dominio en `ALLOWED_HOSTS`.

## Paso 7: Ejecutar el proyecto

Con el entorno virtual activo:

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

`migrate` crea las tablas y `seed_demo` carga los productos de ejemplo (con sus imágenes) y los usuarios de prueba. `seed_demo` se puede ejecutar más de una vez sin duplicar datos.

Abre el navegador en: http://127.0.0.1:8000/

Para detener el servidor, presiona `Ctrl + C`.

---

## Credenciales de acceso (usuarios de prueba)

Estas cuentas las crea `python manage.py seed_demo` y existen solo en tu base de datos local.

**Rol administrador** (acceso total al panel y gestión):
- Correo: admin@gmail.com
- Contraseña: 12345

**Rol cliente** (usuario normal para comprar):
- Correo: user@gmail.com
- Contraseña: 12345

Las cuentas nuevas que se registren desde el sitio deben cumplir las reglas de contraseña: al menos 8 caracteres, no ser solo números, no ser una contraseña común y no parecerse al nombre ni al correo. Las cuentas de prueba usan `12345` solo por comodidad.

Si quieres otra cuenta de administrador, ejecuta `python manage.py createsuperuser`.

**Bloqueo por intentos fallidos:** después de 5 intentos de login fallidos con el mismo correo, ese correo queda bloqueado por 15 minutos. Para desbloquear todo durante el desarrollo, ejecuta `python manage.py axes_reset`.

---

## Si ya tenías el proyecto instalado

El proyecto pasó al sistema de usuarios de Django y **las migraciones se reiniciaron desde cero**. La base de datos antigua (`db_sdgames`) ya no es compatible. Después de hacer `git pull`:

1. Instala las librerías nuevas (con el entorno virtual activo):

   ```powershell
   pip install -r requirements.txt
   ```

2. Crea la base de datos nueva, como en el Paso 5:

   ```sql
   CREATE DATABASE db_akaispace CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
   ```

3. En tu `.env`, cambia `DB_NAME=db_sdgames` por `DB_NAME=db_akaispace`. Si aún no tienes `SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS`, agrégalos como se indica en el Paso 6.

4. Crea las tablas y carga los datos de prueba:

   ```powershell
   python manage.py migrate
   python manage.py seed_demo
   ```

La base `db_sdgames` puede quedarse ahí o puedes borrarla (`DROP DATABASE db_sdgames;`); el proyecto ya no la usa.

---

## Uso diario

Cada vez que vayas a trabajar en el proyecto:

```powershell
cd C:\Proyectos\Akaispace_Proyecto_de_Titulo
.\venv\Scripts\activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

`pip install` y `migrate` no hacen nada si no hubo cambios, así que ejecutarlos siempre es seguro.

---

## Solución de problemas

| Mensaje de error | Causa | Solución |
|---|---|---|
| `No module named 'django'` | El entorno virtual no está activo o faltan librerías | Ejecutar `.\venv\Scripts\activate` y luego `pip install -r requirements.txt` |
| `py` no se reconoce como comando | Python no se instaló desde python.org | Reinstalar Python 3.12 desde python.org y reabrir PowerShell |
| `MariaDB 10.5 or later is required` | El proyecto se está conectando al MySQL de XAMPP | Detener MySQL en XAMPP y verificar que el servicio MySQL 8.4 esté iniciado |
| `Access denied for user 'root'@'localhost'` | Contraseña incorrecta en `.env` | Revisar `DB_PASSWORD` en el archivo `.env` |
| `Unknown database 'db_akaispace'` | No se creó la base de datos | Repetir el Paso 5 |
| `SECRET_KEY not found` | Falta `SECRET_KEY` en el archivo `.env` | Agregarla como se indica en el Paso 6 |
| La página carga sin estilos ni imágenes | `DEBUG` no está en `True` en el `.env` | Agregar `DEBUG=True` al `.env` |
| `Table '...' doesn't exist` | Faltan las tablas | Ejecutar `python manage.py migrate` |
| `InconsistentMigrationHistory` | El `.env` apunta a la base de datos antigua | Seguir la sección "Si ya tenías el proyecto instalado" |
| `No module named 'axes'` | Faltan librerías nuevas | Ejecutar `pip install -r requirements.txt` |
| "Demasiados intentos fallidos" en el login | Se superó el límite de intentos | Esperar 15 minutos o ejecutar `python manage.py axes_reset` |
| `Unknown command` al usar manage.py | Comando mal escrito | Los comandos van en minúscula y separados: `python manage.py runserver` |


