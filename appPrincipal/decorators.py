from django.shortcuts import redirect
from appPrincipal.models import Usuario

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            print("Sesión no encontrada, redirigiendo al login.") 
            return redirect('login')

        usuario = Usuario.objects.filter(id=usuario_id, es_administrador=True).first()
        if not usuario:
            print(f"Acceso denegado. Usuario {usuario_id} no es administrador.") 
            return redirect('login')

        print(f"Acceso concedido. Usuario {usuario_id} es administrador.")  
        return view_func(request, *args, **kwargs)
    return wrapper

