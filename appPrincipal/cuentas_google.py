"""Inicio de sesión y registro con Google."""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.forms import SignupForm
from django.urls import reverse
from django.utils import timezone

from appPrincipal import correos
from appPrincipal.constants import POLITICA_PRIVACIDAD_VERSION
from appPrincipal.forms import UsuarioCustomForm


class AdaptadorCuenta(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False

    def get_login_redirect_url(self, request):
        return reverse('admin_dashboard' if request.user.is_staff else 'home')

    def render_mail(self, template_prefix, email, context, headers=None):
        mensaje = super().render_mail(template_prefix, email, context, headers)
        mensaje.reply_to = correos.responder_a() or []
        return mensaje


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


class RegistroGoogleForm(SignupForm):
    declaracion_edad = UsuarioCustomForm.base_fields['declaracion_edad']
    acepta_privacidad = UsuarioCustomForm.base_fields['acepta_privacidad']
    autoriza_datos_navegacion = UsuarioCustomForm.base_fields['autoriza_datos_navegacion']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'email' in self.fields:
            self.fields['email'].disabled = True

    def custom_signup(self, request, user):
        momento_consentimiento = timezone.now()
        user.declaracion_edad = self.cleaned_data['declaracion_edad']
        user.privacidad_aceptada_en = momento_consentimiento
        user.privacidad_version = POLITICA_PRIVACIDAD_VERSION
        if self.cleaned_data['autoriza_datos_navegacion']:
            user.datos_navegacion_autorizados_en = momento_consentimiento
        user.save(update_fields=['declaracion_edad', 'privacidad_aceptada_en', 'privacidad_version',
                                 'datos_navegacion_autorizados_en'])
        correos.enviar_bienvenida(user, con_google=True)
