Proyecto SD Games

Para el desarrollo de nuestra aplicación se utilizó un entorno virtual (venv) para aislar las dependencias de la aplicación y evitar conflictos con otras aplicaciones o dependencias en el sistema global.
Para crear el entorno virtual y usarlo se debe: 

Primero, en caso de nunca haber usado un ambiente virtual, ya sea porque es un pc nuevo o si nunca has ejecutado Scripts en PowerShell, se debe ir a:

PowerShell con privilegios de administrador (clic derecho sobre el ícono de PowerShell y seleccionar "Ejecutar como administrador").

Y ejecutar:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

Remover en caso de que existan cambios en venv (Estando dentro de la carpeta del proyecto):
Remove-Item -Recurse -Force venv

Se instala (Estando dentro de la carpeta del proyecto): 
python -m venv venv

Se ingresa al entorno virtual por medio del comando (Estando dentro de la carpeta del proyecto): 
.\venv\Scripts\activate 

Ya dentro de venv se debe ejecutar: 
pip install -r requirements.txt
Ya que este archivo de texto contiene todas las instalaciones osea los “pip”.

Posterior a esto se puede realizar el inicio del programa sin problemas:
python manage.py runserver
