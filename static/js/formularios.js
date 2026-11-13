// Validación y avisos de los formularios (se carga en base.html para todas las páginas).
//
// Uso en una plantilla:
//   <form method="post" data-validar [data-ajax]>
//     <div data-campo> <input name="..." required ...> </div>   ← el mensaje de error va al final del contenedor
//   </form>
//
// - Antes de enviar revisa todos los campos, muestra cada error bajo su campo y lleva la vista y el
//   cursor al primero con error. Si hay errores, el formulario no se envía. Arriba del formulario
//   ([data-resumen-errores]) solo aparece un aviso breve para lo que no es de un campo y el de éxito.
// - Los mensajes salen de los atributos del campo: required, type="email", minlength, maxlength, pattern,
//   min, max, y de data-validacion="rut|nombre|telefono", data-igual-a="id de otro campo".
//   Se pueden cambiar con data-msg-requerido, data-msg-formato y data-msg-igual.
// - Con data-ajax el formulario se envía con fetch y espera JSON {success, message, errors, redirect};
//   los errores del servidor ({campo: [mensajes]}) se muestran igual que los del navegador.
// - Sin data-ajax el envío es normal; los errores que el servidor deja en la página con
//   data-error-de="campo" (partials/error_campo.html) se marcan igual al cargar la página.
// - Extras: data-contador (contador de caracteres con maxlength), data-formato="rut|digitos" y
//   data-ciudades-de="id del select de región" (carga las ciudades de la región elegida).
// La validación que vale es siempre la del servidor; esta solo avisa antes y con mensajes claros.
(function () {
    'use strict';

    // ---------- validadores ----------
    function rutValido(valor) {
        const limpio = (valor || '').replace(/[.\-\s]/g, '').toUpperCase();
        if (!/^\d{7,8}[\dK]$/.test(limpio)) return false;
        const cuerpo = limpio.slice(0, -1);
        let suma = 0;
        let multiplicador = 2;
        for (let i = cuerpo.length - 1; i >= 0; i--) {
            suma += Number(cuerpo[i]) * multiplicador;
            multiplicador = multiplicador === 7 ? 2 : multiplicador + 1;
        }
        const resto = 11 - (suma % 11);
        const esperado = resto === 11 ? '0' : resto === 10 ? 'K' : String(resto);
        return limpio.slice(-1) === esperado;
    }

    // mismas reglas que limpiar_nombre() en forms.py: letras de cualquier idioma (tildes, ñ, ü...),
    // espacios, apóstrofos, guiones y puntos
    const NOMBRE_VALIDO = /^[\p{L}\p{M}' ’.\-]+$/u;

    const VALIDADORES = {
        rut: function (valor) {
            if (!/^[\d.\-\skK]+$/.test(valor) || valor.replace(/[^\dkK]/g, '').length < 8) {
                return 'Escribe el RUT completo con dígito verificador (por ejemplo: 12.345.678-5).';
            }
            return rutValido(valor) ? '' : 'El RUT no es válido: revisa el dígito verificador.';
        },
        nombre: function (valor) {
            const nombre = valor.trim().replace(/\s+/g, ' ');
            if (!NOMBRE_VALIDO.test(nombre)) {
                return 'El nombre solo puede tener letras (con o sin tilde), espacios, guiones y apóstrofos.';
            }
            if ((nombre.match(/\p{L}/gu) || []).length < 2) return 'El nombre debe tener al menos 2 letras.';
            return '';
        },
        // mismas reglas que AUTH_PASSWORD_VALIDATORS (el servidor además revisa las contraseñas comunes)
        'contraseña': function (valor) {
            if (valor.length < 8) return 'La contraseña debe tener al menos 8 caracteres.';
            if (!/\p{L}/u.test(valor) || !/\d/.test(valor)) return 'La contraseña debe tener al menos una letra y un número.';
            return '';
        },
        telefono: function (valor) {
            return /^\d{8}$/.test(valor.trim()) ? '' : 'El teléfono debe tener 8 dígitos después del +56 9.';
        },
    };

    function esTexto(control) {
        return control.tagName === 'TEXTAREA' ||
            (control.tagName === 'INPUT' && !['checkbox', 'radio', 'file', 'hidden'].includes(control.type));
    }

    function controlesDe(form) {
        return Array.from(form.elements).filter(function (control) {
            return control.name && !control.disabled && control.willValidate !== false &&
                !['hidden', 'submit', 'button', 'reset'].includes(control.type) &&
                control.tagName !== 'BUTTON' && control.tagName !== 'FIELDSET';
        });
    }

    // devuelve el mensaje de error del campo, o '' si está bien
    function mensajeDe(control) {
        const d = control.dataset;
        const v = control.validity;

        if (control.type === 'radio') {
            const grupo = control.form.querySelectorAll('input[type="radio"][name="' + CSS.escape(control.name) + '"]');
            const requerido = Array.from(grupo).some(function (r) { return r.required; });
            const marcado = Array.from(grupo).some(function (r) { return r.checked; });
            const conMensaje = Array.from(grupo).find(function (r) { return r.dataset.msgRequerido; });
            return requerido && !marcado ? ((conMensaje && conMensaje.dataset.msgRequerido) || 'Selecciona una opción.') : '';
        }

        if (v.badInput) return d.msgFormato || 'Escribe un número válido.';
        const valor = esTexto(control) ? control.value.trim() : control.value;
        const vacio = control.type === 'checkbox' ? !control.checked : (control.type === 'file' ? control.files.length === 0 : valor === '');

        if (vacio) {
            if (!control.required) return '';
            if (d.msgRequerido) return d.msgRequerido;
            if (control.type === 'checkbox') return 'Debes marcar esta casilla para continuar.';
            if (control.tagName === 'SELECT') return 'Selecciona una opción de la lista.';
            return 'Completa este campo.';
        }
        // el navegador acepta "nombre@correo" sin dominio; el servidor no, así que se avisa antes
        if (control.type === 'email' && (v.typeMismatch || !/^[^@\s]+@[^@\s]+\.[^@\s.]{2,}$/.test(valor))) {
            return d.msgFormato || 'Escribe un correo válido (por ejemplo: nombre@correo.cl).';
        }
        if (control.minLength > 0 && valor.length < control.minLength) {
            return d.msgFormato || ('Debe tener al menos ' + control.minLength + ' caracteres.');
        }
        if (control.maxLength > 0 && control.value.length > control.maxLength) {
            return 'Puede tener hasta ' + control.maxLength + ' caracteres.';
        }
        if (v.patternMismatch) return d.msgFormato || 'El formato no es válido.';
        if (v.rangeUnderflow) return d.msgFormato || ('El valor mínimo es ' + control.min + '.');
        if (v.rangeOverflow) return d.msgFormato || ('El valor máximo es ' + control.max + '.');
        if (v.stepMismatch) return d.msgFormato || 'Escribe un número entero.';

        if (d.validacion && VALIDADORES[d.validacion]) {
            const mensaje = VALIDADORES[d.validacion](control.value);
            if (mensaje) return mensaje;
        }
        if (d.igualA) {
            const otro = document.getElementById(d.igualA);
            if (otro && otro.value && control.value !== otro.value) {
                return d.msgIgual || 'Los valores no coinciden.';
            }
        }
        return '';
    }

    // ---------- mensajes bajo cada campo ----------
    function contenedorDe(control) {
        return control.closest('[data-campo]') || control.parentElement;
    }

    function controlesDelMismoNombre(control) {
        if (!control.form || !control.name) return [control];
        return Array.from(control.form.querySelectorAll('[name="' + CSS.escape(control.name) + '"]'));
    }

    function idError(control) {
        return 'error-' + (control.form.id || 'form') + '-' + control.name.replace(/[^\w-]/g, '_');
    }

    function mostrarError(control, mensaje) {
        const contenedor = contenedorDe(control);
        let error = contenedor.querySelector('[data-error-de="' + CSS.escape(control.name) + '"]');
        if (!error) {
            error = document.createElement('div');
            error.className = 'invalid-feedback d-block mensaje-error';
            error.dataset.errorDe = control.name;
            // el aviso va pegado al campo, antes del contador de caracteres
            const contador = contenedor.querySelector('.contador-caracteres');
            if (contador) contador.insertAdjacentElement('beforebegin', error);
            else contenedor.appendChild(error);
        }
        error.id = error.id || idError(control);
        error.textContent = mensaje;
        controlesDelMismoNombre(control).forEach(function (c) {
            c.classList.add('is-invalid');
            c.setAttribute('aria-invalid', 'true');
            const descritos = (c.getAttribute('aria-describedby') || '').split(' ').filter(Boolean);
            if (!descritos.includes(error.id)) descritos.push(error.id);
            c.setAttribute('aria-describedby', descritos.join(' '));
        });
    }

    function limpiarError(control) {
        const contenedor = contenedorDe(control);
        const error = contenedor.querySelector('[data-error-de="' + CSS.escape(control.name) + '"]');
        if (error) error.remove();
        controlesDelMismoNombre(control).forEach(function (c) {
            c.classList.remove('is-invalid');
            c.removeAttribute('aria-invalid');
        });
    }

    // ---------- resumen arriba del formulario ----------
    function cajaResumen(form) {
        let caja = form.querySelector('[data-resumen-errores]');
        if (!caja) {
            caja = document.createElement('div');
            caja.dataset.resumenErrores = '';
            form.insertAdjacentElement('afterbegin', caja);
        }
        caja.setAttribute('tabindex', '-1');
        return caja;
    }

    function ocultarResumen(form) {
        const caja = form.querySelector('[data-resumen-errores]');
        if (caja) {
            caja.className = '';
            caja.replaceChildren();
            caja.hidden = true;
        }
    }

    function enfocarResumen(caja) {
        caja.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
        caja.focus({ preventScroll: true });
    }

    // errores: [{control, mensaje}] ; generales: [mensaje]
    // Los errores de un campo se muestran solo bajo ese campo: se lleva la vista y el cursor al primero.
    // Arriba del formulario solo aparece un aviso breve para lo que no es de un campo (p. ej. sin conexión).
    function mostrarResumen(form, errores, generales) {
        if (generales.length) {
            const caja = cajaResumen(form);
            caja.hidden = false;
            caja.className = 'alert resumen-errores';
            caja.setAttribute('role', 'alert');
            const icono = document.createElement('i');
            icono.className = 'fas fa-circle-exclamation me-2';
            icono.setAttribute('aria-hidden', 'true');
            caja.replaceChildren(icono, generales.join(' '));
        } else {
            ocultarResumen(form);
        }

        if (errores.length) {
            const primero = errores[0].control;
            const reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            primero.scrollIntoView({ behavior: reducido ? 'auto' : 'smooth', block: 'center' });
            primero.focus({ preventScroll: true });
        } else if (generales.length) {
            enfocarResumen(cajaResumen(form));
        }
    }

    // el aviso general de arriba se va cuando la persona corrige algo
    function actualizarResumen(form) {
        if (form.querySelector('[data-resumen-errores].resumen-errores')) ocultarResumen(form);
    }

    function mostrarExito(form, mensaje) {
        const caja = cajaResumen(form);
        caja.hidden = false;
        caja.className = 'alert alert-success resumen-exito';
        caja.setAttribute('role', 'status');
        const icono = document.createElement('i');
        icono.className = 'fas fa-circle-check me-2';
        icono.setAttribute('aria-hidden', 'true');
        caja.replaceChildren(icono, mensaje);
        enfocarResumen(caja);
    }

    // ---------- validar el formulario completo ----------
    function validar(form) {
        const errores = [];
        const vistos = new Set();
        controlesDe(form).forEach(function (control) {
            if (control.type === 'radio') {
                if (vistos.has(control.name)) return;
                vistos.add(control.name);
            }
            const mensaje = mensajeDe(control);
            if (mensaje) {
                mostrarError(control, mensaje);
                errores.push({ control: control, mensaje: mensaje });
            } else {
                limpiarError(control);
            }
        });
        if (errores.length) {
            mostrarResumen(form, errores, []);
        } else {
            ocultarResumen(form);
        }
        return errores.length === 0;
    }

    // errores del servidor: {campo: [mensajes]} (el campo "__all__" va solo en el resumen)
    function mostrarErroresServidor(form, errores, mensaje) {
        controlesDe(form).forEach(limpiarError);
        const lista = [];
        const generales = [];
        Object.keys(errores || {}).forEach(function (nombre) {
            const control = form.querySelector('[name="' + CSS.escape(nombre) + '"]');
            const texto = (errores[nombre] || [])[0];
            if (!texto) return;
            if (control && nombre !== '__all__') {
                mostrarError(control, texto);
                lista.push({ control: control, mensaje: texto });
            } else {
                generales.push(texto);
            }
        });
        if (!lista.length && !generales.length) generales.push(mensaje || 'No pudimos completar la acción. Inténtalo de nuevo.');
        mostrarResumen(form, lista, generales);
    }

    // ---------- envío ----------
    function botonesDe(form) {
        return Array.from(form.querySelectorAll('button[type="submit"], button:not([type]), input[type="submit"]'));
    }

    function bloquearEnvio(form, bloquear) {
        form.dataset.enviando = bloquear ? '1' : '';
        form.setAttribute('aria-busy', String(bloquear));
        botonesDe(form).forEach(function (boton) {
            if (bloquear) {
                boton.dataset.textoOriginal = boton.dataset.textoOriginal || boton.innerHTML;
                boton.disabled = true;
                boton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>' +
                    (boton.dataset.textoEnviando || 'Enviando…');
            } else {
                boton.disabled = false;
                if (boton.dataset.textoOriginal) boton.innerHTML = boton.dataset.textoOriginal;
            }
        });
    }

    function enviarConFetch(form) {
        bloquearEnvio(form, true);
        fetch(form.action || window.location.href, {
            method: 'POST',
            body: new FormData(form),
            headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
            credentials: 'same-origin',
        })
            .then(function (respuesta) {
                const tipo = respuesta.headers.get('content-type') || '';
                if (!tipo.includes('application/json')) {
                    throw new Error(respuesta.status === 403
                        ? 'Tu sesión expiró. Recarga la página e inténtalo de nuevo.'
                        : 'No pudimos procesar tu solicitud. Inténtalo de nuevo en unos minutos.');
                }
                return respuesta.json();
            })
            .then(function (datos) {
                if (datos.success) {
                    mostrarExito(form, datos.message || '¡Listo!');
                    form.dispatchEvent(new CustomEvent('formulario:exito', { detail: datos }));
                    if (datos.redirect) {
                        setTimeout(function () { window.location.href = datos.redirect; }, 1500);
                    } else {
                        bloquearEnvio(form, false);
                    }
                } else {
                    bloquearEnvio(form, false);
                    mostrarErroresServidor(form, datos.errors, datos.message);
                }
            })
            .catch(function (error) {
                bloquearEnvio(form, false);
                const mensaje = error instanceof TypeError
                    ? 'No hay conexión con el servidor. Revisa tu internet e inténtalo de nuevo.'
                    : error.message;
                mostrarResumen(form, [], [mensaje]);
            });
    }

    document.addEventListener('submit', function (evento) {
        const form = evento.target;
        if (!form.matches('form[data-validar]')) return;
        if (form.dataset.enviando === '1') {
            evento.preventDefault();
            return;
        }
        if (!validar(form)) {
            evento.preventDefault();
            evento.stopImmediatePropagation();
            return;
        }
        if (form.hasAttribute('data-ajax')) {
            evento.preventDefault();
            evento.stopImmediatePropagation();
            enviarConFetch(form);
            return;
        }
        // envío normal: se bloquea el botón para evitar enviarlo dos veces (después de los demás
        // manejadores de la página, por si alguno cancela el envío; y después de que el navegador
        // tome el valor del botón presionado)
        document.addEventListener('submit', function (final) {
            if (final.target === form && !final.defaultPrevented) {
                setTimeout(function () { bloquearEnvio(form, true); }, 0);
            }
        }, { once: true });
    }, true);

    // al volver con el botón "atrás" el navegador puede mostrar la página guardada con el botón bloqueado
    window.addEventListener('pageshow', function (evento) {
        if (!evento.persisted) return;
        document.querySelectorAll('form[data-validar][aria-busy="true"]').forEach(function (form) {
            bloquearEnvio(form, false);
        });
    });

    // al corregir un campo con error, el aviso se va solo; al salir de un campo que se editó, se revisa
    function revisarEnVivo(evento) {
        const control = evento.target;
        if (!control.form || !control.form.matches('form[data-validar]') || !control.name) return;
        const yaTieneError = control.classList.contains('is-invalid');
        const salio = evento.type === 'focusout';
        // si el foco pasa al botón de enviar no se avisa todavía: el aviso movería el botón y el clic
        // se perdería; al enviar se revisa todo el formulario de una vez
        const destino = evento.relatedTarget;
        if (salio && destino && destino.form === control.form &&
            (destino.type === 'submit' || (destino.tagName === 'BUTTON' && !destino.getAttribute('type')))) return;
        if (!yaTieneError && !(salio && control.dataset.editado)) return;
        if (salio && !yaTieneError && esTexto(control) && control.value.trim() === '') return;
        const mensaje = mensajeDe(control);
        if (mensaje) {
            mostrarError(control, mensaje);
        } else {
            limpiarError(control);
            actualizarResumen(control.form, control.name);
        }
        // al cambiar la contraseña también se revisa su confirmación
        control.form.querySelectorAll('[data-igual-a="' + CSS.escape(control.id) + '"]').forEach(function (otro) {
            if (otro.classList.contains('is-invalid') && !mensajeDe(otro)) {
                limpiarError(otro);
                actualizarResumen(control.form, otro.name);
            }
        });
    }

    document.addEventListener('input', function (evento) {
        if (evento.target.dataset) evento.target.dataset.editado = '1';
        revisarEnVivo(evento);
    });
    document.addEventListener('change', revisarEnVivo);
    document.addEventListener('focusout', revisarEnVivo);

    // ---------- extras ----------
    function formatearRut(input) {
        let valor = input.value.replace(/[^0-9kK]/g, '').toUpperCase().slice(0, 9);
        // la K solo puede ir al final
        valor = valor.slice(0, -1).replace(/K/g, '') + valor.slice(-1);
        if (valor.length < 2) {
            input.value = valor;
            return;
        }
        const cuerpo = valor.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        input.value = cuerpo + '-' + valor.slice(-1);
    }

    function iniciarContador(input) {
        const maximo = input.maxLength;
        if (!(maximo > 0)) return;
        const contador = document.createElement('small');
        contador.className = 'contador-caracteres';
        contador.setAttribute('aria-live', 'polite');
        // va después del campo y, si el servidor dejó un aviso de error, después de ese aviso
        const contenedor = input.closest('[data-campo]') || input.parentElement;
        const error = contenedor.querySelector('[data-error-de="' + CSS.escape(input.name) + '"]');
        (error || input.closest('.form-floating, .input-group') || input).insertAdjacentElement('afterend', contador);
        const actualizar = function () {
            const largo = input.value.length;
            contador.textContent = largo + '/' + maximo;
            contador.classList.toggle('al-limite', largo >= maximo);
        };
        input.addEventListener('input', actualizar);
        actualizar();
    }

    function iniciarCiudades(selectCiudad) {
        const selectRegion = document.getElementById(selectCiudad.dataset.ciudadesDe);
        if (!selectRegion) return;
        const textoVacio = selectCiudad.dataset.textoVacio || 'Selecciona una ciudad';

        function opcion(valor, texto, seleccionada) {
            const o = document.createElement('option');
            o.value = valor;
            o.textContent = texto;
            if (seleccionada) o.selected = true;
            return o;
        }

        function cargar(conservar) {
            const region = selectRegion.value;
            const anterior = conservar ? selectCiudad.value : '';
            if (!region) {
                selectCiudad.replaceChildren(opcion('', 'Primero selecciona una región', true));
                return;
            }
            selectCiudad.replaceChildren(opcion('', 'Cargando ciudades…', true));
            fetch('/obtener_ciudades/?region=' + encodeURIComponent(region))
                .then(function (r) { return r.json(); })
                .then(function (datos) {
                    const ciudades = datos.ciudades || [];
                    selectCiudad.replaceChildren(opcion('', textoVacio, !ciudades.includes(anterior)));
                    ciudades.forEach(function (ciudad) {
                        selectCiudad.appendChild(opcion(ciudad, ciudad, ciudad === anterior));
                    });
                })
                .catch(function () {
                    selectCiudad.replaceChildren(opcion('', 'No se pudieron cargar las ciudades', true));
                });
        }

        selectRegion.addEventListener('change', function () { cargar(false); });
        // si el servidor no trajo las ciudades de la región ya elegida (p. ej. al volver atrás), se cargan
        if (selectRegion.value && selectCiudad.options.length <= 1) cargar(true);
        if (!selectRegion.value && selectCiudad.options.length <= 1) cargar(false);
    }

    function iniciar() {
        document.querySelectorAll('form[data-validar]').forEach(function (form) {
            form.noValidate = true;
            // errores que dejó el servidor en la página: se arma el resumen con ellos
            const errores = [];
            form.querySelectorAll('[data-error-de]').forEach(function (error) {
                const control = form.querySelector('[name="' + CSS.escape(error.dataset.errorDe) + '"]');
                if (!control || !error.textContent.trim()) return;
                mostrarError(control, error.textContent.trim());
                errores.push({ control: control, mensaje: error.textContent.trim() });
            });
            const generales = Array.from(form.querySelectorAll('[data-error-general]'))
                .map(function (e) { return e.textContent.trim(); }).filter(Boolean);
            form.querySelectorAll('[data-error-general]').forEach(function (e) { e.remove(); });
            if (errores.length || generales.length) mostrarResumen(form, errores, generales);
        });
        document.querySelectorAll('input[data-formato="rut"]').forEach(function (input) {
            input.addEventListener('input', function () { formatearRut(input); });
            if (input.value) formatearRut(input);
        });
        // teléfono: solo dígitos; si se pega el número completo (+56 9 1234 5678) quedan los últimos 8
        document.querySelectorAll('input[data-formato="telefono"]').forEach(function (input) {
            input.addEventListener('input', function () {
                let digitos = input.value.replace(/\D/g, '');
                if (digitos.length > 8) digitos = digitos.slice(-8);
                if (digitos !== input.value) input.value = digitos;
            });
        });
        document.querySelectorAll('input[data-formato="digitos"]').forEach(function (input) {
            input.addEventListener('input', function () {
                const limpio = input.value.replace(/\D/g, '').slice(0, input.maxLength > 0 ? input.maxLength : undefined);
                if (limpio !== input.value) input.value = limpio;
            });
        });
        document.querySelectorAll('[data-contador]').forEach(iniciarContador);
        document.querySelectorAll('select[data-ciudades-de]').forEach(iniciarCiudades);
    }

    window.Formularios = {
        validar: validar,
        mostrarErrores: mostrarErroresServidor,
        mostrarExito: mostrarExito,
        rutValido: rutValido,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
