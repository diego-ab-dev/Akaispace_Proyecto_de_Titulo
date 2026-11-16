// Catálogo (menú, categoría, búsqueda y ficha de producto): agregar al carrito y marcar favorito sin recargar.
// Uso: <script src="{% static 'js/catalogo_acciones.js' %}" data-url-login="{% url 'login' %}" defer></script>
// - Formularios .form-agregar y .form-favorito: se envían con fetch y la vista responde JSON
//   {success, message} o {error}; error 'not_logged_in' lleva al login y vuelve a esta página.
// - El aviso usa el #notif-box de la página (clases notif show success | error | favorite).
(function () {
    'use strict';

    const urlLogin = document.currentScript.dataset.urlLogin || '/login/';

    function avisar(mensaje, tipo) {
        const notifBox = document.getElementById('notif-box');
        const notifMsg = document.getElementById('notif-msg');
        if (notifMsg) notifMsg.innerText = mensaje;
        if (notifBox) {
            notifBox.className = 'notif show ' + tipo;
            setTimeout(() => { notifBox.classList.remove('show'); }, 3000);
        }
    }

    function irAlLogin() {
        window.location.href = urlLogin + '?next=' + encodeURIComponent(window.location.pathname);
    }

    function enviar(form) {
        return fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).then((respuesta) => respuesta.json());
    }

    document.addEventListener('submit', function (evento) {
        const form = evento.target;

        if (form.matches('.form-agregar')) {
            evento.preventDefault();
            enviar(form).then((data) => {
                if (data.success) {
                    avisar(data.message, 'success');
                } else if (data.error === 'not_logged_in') {
                    irAlLogin();
                } else {
                    avisar(data.error, 'error');  // sin stock suficiente o cantidad inválida
                }
            }).catch((error) => console.error('Error carrito:', error));
        }

        if (form.matches('.form-favorito')) {
            evento.preventDefault();
            const icono = form.querySelector('button i');
            enviar(form).then((data) => {
                if (data.success) {
                    avisar(data.message, 'favorite');
                    icono.classList.toggle('fas', data.agregado);
                    icono.classList.toggle('far', !data.agregado);
                    icono.style.color = data.agregado ? 'red' : '';
                } else if (data.error === 'not_logged_in') {
                    irAlLogin();
                }
            }).catch((error) => console.error('Error favoritos:', error));
        }
    });
})();
