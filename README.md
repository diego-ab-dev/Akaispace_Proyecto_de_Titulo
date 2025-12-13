GUÍA DE INSTALACIÓN Y USO - PROYECTO SD GAMES

REQUISITOS DEL SISTEMA:
- Python (versión 3.8 o superior).
- Servidor MySQL activo (XAMPP, WAMP o similar).

PASO 1: INSTALACIÓN DEL ENTORNO

1. Descomprima el proyecto.
2. Abra una terminal en la carpeta raíz del proyecto.
3. Cree y active el entorno virtual:
   python -m venv venv
   
   > En Windows: .\venv\Scripts\activate
   
   > En Mac/Linux: source venv/bin/activate

En caso de nunca haber usado un ambiente virtual, ya sea porque es un pc nuevo o si nunca has ejecutado Scripts en PowerShell, se debe ir a:

PowerShell con privilegios de administrador (clic derecho sobre el ícono de PowerShell y seleccionar "Ejecutar como administrador").
Y ejecutar:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

4. Instale las librerías necesarias:
   pip install -r requirements.txt


PASO 2: BASE DE DATOS (IMPORTACIÓN RÁPIDA)

El proyecto incluye un script SQL con datos de prueba (6 productos y usuarios listos).

1. Abra phpMyAdmin (o su gestor de MySQL favorito).
2. Cree una base de datos VACÍA llamada: db_sdgames
3. Seleccione la base de datos 'db_sdgames' e importe el archivo 'db_sdgames.sql' que se encuentra en la carpeta raíz de este proyecto.

NOTA IMPORTANTE SOBRE CONEXIÓN:
El archivo 'settings.py' está configurado para conectar a MySQL con:
- Host: localhost
- Puerto: 3306
- Usuario: root
- Contraseña: (vacía)
Si su configuración local de MySQL es diferente, por favor ajuste la sección DATABASES en 'SdGames/settings.py'.

PASO 3: EJECUCIÓN
1. Inicie el servidor:
   python manage.py runserver

2. Abra su navegador en: http://127.0.0.1:8000/

CREDENCIALES DE ACCESO (USUARIOS DE PRUEBA)

ROL ADMINISTRADOR (Acceso total al panel y gestión):
- Correo: admin@gmail.com
- Contraseña: 12345

ROL CLIENTE (Usuario normal para comprar):
- Correo: user@gmail.com
- Contraseña: 12345



