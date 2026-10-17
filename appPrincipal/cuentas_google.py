"""Inicio de sesión con Google (HU-02, django-allauth).

- El registro con correo y contraseña es el propio (vista register, con los consentimientos de HU-01),
  así que el de allauth (/accounts/signup/) queda cerrado; solo se crean cuentas nuevas desde Google.
- Usuario no tiene username y exige `nombre`: al crear la cuenta desde Google se usa el nombre del
  perfil de Google (o la parte del correo antes de la @ si Google no lo entrega).
"""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AdaptadorCuenta(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False


class AdaptadorCuentaGoogle(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        usuario = super().populate_user(request, sociallogin, data)
        extra = sociallogin.account.extra_data or {}
        nombre = (data.get('name') or extra.get('name')
                  or ' '.join(filter(None, [data.get('first_name'), data.get('last_name')])))
        usuario.nombre = (nombre or (usuario.email or '').split('@')[0])[:100]
        return usuario
