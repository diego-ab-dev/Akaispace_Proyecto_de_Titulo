from django.core.exceptions import ValidationError
from django.shortcuts import render

MENSAJE_LOGIN_INVALIDO = "Correo o contraseña incorrectos."
MENSAJE_LOGIN_BLOQUEADO = "Demasiados intentos fallidos. Espera 15 minutos antes de volver a intentarlo."


def email_para_axes(request, credentials):
    if credentials:
        email = credentials.get('username') or credentials.get('email')
    else:
        email = request.POST.get('email')
    return (email or '').strip().lower()


def ip_cliente(request):
    """IP del cliente para django-axes. En AWS, Nginx toma la IP que agrega el balanceador a X-Forwarded-For
    (solo si la petición viene de la VPC) y la reenvía en X-Real-IP; sin Nginx, se usa la IP de la conexión."""
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')


def login_bloqueado(request, original_response=None, credentials=None):
    """Respuesta de django-axes cuando se supera el límite de intentos de login."""
    return render(request, 'login.html', {'errors': {'email': MENSAJE_LOGIN_BLOQUEADO}}, status=429)


class LetraYNumeroValidator:
    def validate(self, password, user=None):
        tiene_letra = any(caracter.isalpha() for caracter in password)
        tiene_numero = any(caracter.isdigit() for caracter in password)
        if not (tiene_letra and tiene_numero):
            raise ValidationError(
                "La contraseña debe tener al menos una letra y un número.",
                code='password_sin_letra_y_numero',
            )

    def get_help_text(self):
        return "Tu contraseña debe tener al menos una letra y un número."
