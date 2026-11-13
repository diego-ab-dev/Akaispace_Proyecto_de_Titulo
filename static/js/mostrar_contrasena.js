// Agrega el botón del ojo (mostrar/ocultar) a todos los campos de contraseña de la página.
// Se carga en base.html, así que cualquier <input type="password"> nuevo lo trae solo.
// Para excluir un campo: <input type="password" data-sin-ojo>.
(function () {
    function agregarOjo(input) {
        if (input.dataset.ojoListo || input.hasAttribute('data-sin-ojo')) return;
        input.dataset.ojoListo = '1';

        // En los form-floating el botón va dentro del mismo contenedor (para no romper la etiqueta);
        // en los demás se envuelve el campo en un contenedor propio.
        let contenedor = input.parentElement;
        if (!contenedor.classList.contains('form-floating')) {
            contenedor = document.createElement('div');
            input.parentNode.insertBefore(contenedor, input);
            contenedor.appendChild(input);
        }
        contenedor.classList.add('campo-contrasena');

        const boton = document.createElement('button');
        boton.type = 'button';
        boton.className = 'btn-ojo';
        boton.setAttribute('aria-label', 'Mostrar contraseña');
        boton.setAttribute('aria-pressed', 'false');
        boton.innerHTML = '<i class="fas fa-eye" aria-hidden="true"></i>';
        input.insertAdjacentElement('afterend', boton);

        const actualizarVisibilidad = function () {
            boton.hidden = input.value.length === 0;
        };

        boton.addEventListener('click', function () {
            const mostrar = input.type === 'password';
            input.type = mostrar ? 'text' : 'password';
            boton.querySelector('i').className = mostrar ? 'fas fa-eye-slash' : 'fas fa-eye';
            boton.setAttribute('aria-label', mostrar ? 'Ocultar contraseña' : 'Mostrar contraseña');
            boton.setAttribute('aria-pressed', String(mostrar));
            input.focus();
        });

        input.addEventListener('input', actualizarVisibilidad);
        actualizarVisibilidad();
    }

    function iniciar() {
        document.querySelectorAll('input[type="password"]').forEach(agregarOjo);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
