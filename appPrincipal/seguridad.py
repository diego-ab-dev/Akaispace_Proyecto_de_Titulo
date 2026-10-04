from django.shortcuts import render

MENSAJE_LOGIN_INVALIDO = "Correo o contraseña incorrectos."
MENSAJE_LOGIN_BLOQUEADO = "Demasiados intentos fallidos. Espera 15 minutos antes de volver a intentarlo."


def email_para_axes(request, credentials):
    """Email con el que django-axes cuenta los intentos fallidos (en minúsculas)."""
    # axes entrega el email con la clave 'username' (al registrar un fallo) o
    # 'email' (al revisar si está bloqueado, porque es el USERNAME_FIELD del modelo)
    if credentials:
        email = credentials.get('username') or credentials.get('email')
    else:
        email = request.POST.get('email')
    return (email or '').strip().lower()


def login_bloqueado(request, original_response=None, credentials=None):
    """Respuesta de django-axes cuando se supera el límite de intentos de login."""
    return render(request, 'login.html', {'errors': {'email': MENSAJE_LOGIN_BLOQUEADO}}, status=429)
