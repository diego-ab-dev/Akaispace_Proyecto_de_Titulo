// Aviso de cambios sin guardar
(function () {
    'use strict';

    const formularios = Array.from(document.querySelectorAll('form[data-avisar-cambios]'));
    if (!formularios.length) return;

    const estadoInicial = new Map();
    let enviando = false;
    let saliendo = false;
    let temporizadorEnvio = null;

    function foto(form) {
        const datos = [];
        Array.from(form.elements).forEach(campo => {
            if (!campo.name || campo.disabled || campo.name === 'csrfmiddlewaretoken') return;
            const tipo = (campo.type || '').toLowerCase();
            if (['submit', 'button', 'reset'].includes(tipo)) return;
            if (tipo === 'checkbox' || tipo === 'radio') {
                datos.push([campo.name, campo.value, campo.checked]);
            } else if (tipo === 'file') {
                datos.push([campo.name, Array.from(campo.files || []).map(f => f.name + ':' + f.size).join('|')]);
            } else if (campo.multiple && campo.options) {
                datos.push([campo.name, Array.from(campo.selectedOptions).map(o => o.value).join('|')]);
            } else {
                datos.push([campo.name, campo.value]);
            }
        });
        return JSON.stringify(datos);
    }

    function hayCambios() {
        if (enviando || saliendo) return false;
        return formularios.some(form => estadoInicial.has(form) && foto(form) !== estadoInicial.get(form));
    }

    window.addEventListener('load', () => {
        setTimeout(() => formularios.forEach(form => estadoInicial.set(form, foto(form))), 0);
    });

    formularios.forEach(form => {
        form.addEventListener('submit', () => {
            enviando = true;
            clearTimeout(temporizadorEnvio);
            temporizadorEnvio = setTimeout(() => { enviando = false; }, 5000);
        });
        form.addEventListener('input', () => { enviando = false; });
        form.addEventListener('change', () => { enviando = false; });
    });

    window.addEventListener('beforeunload', evento => {
        if (!hayCambios()) return;
        evento.preventDefault();
        evento.returnValue = '';
    });

    // Ventana propia para los enlaces
    let modal = null;
    let destino = null;

    function crearModal() {
        const elemento = document.createElement('div');
        elemento.className = 'modal fade';
        elemento.id = 'modal-cambios-sin-guardar';
        elemento.tabIndex = -1;
        elemento.setAttribute('aria-labelledby', 'titulo-cambios-sin-guardar');
        elemento.setAttribute('aria-hidden', 'true');
        elemento.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow" style="border-radius: 16px;">
                    <div class="modal-body text-center p-5">
                        <div class="mx-auto mb-4 d-flex align-items-center justify-content-center"
                             style="width: 72px; height: 72px; border-radius: 50%; background-color: #FFF4E0; color: #D98A00;">
                            <i class="fas fa-exclamation-triangle fa-2x" aria-hidden="true"></i>
                        </div>
                        <h4 class="fw-bold mb-3" id="titulo-cambios-sin-guardar" style="color: #1C253B;">Tienes cambios sin guardar</h4>
                        <p class="text-muted mb-4">Si sales ahora, se perderán los cambios que hiciste en esta página.</p>
                        <div class="d-flex justify-content-center flex-wrap gap-2">
                            <button type="button" class="btn px-4 rounded-3 fw-semibold" data-bs-dismiss="modal"
                                    style="background-color: #4E84A8; color: #fff;">Seguir editando</button>
                            <button type="button" class="btn btn-outline-danger px-4 rounded-3 fw-semibold"
                                    id="btn-salir-sin-guardar">Salir sin guardar</button>
                        </div>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(elemento);
        elemento.querySelector('#btn-salir-sin-guardar').addEventListener('click', () => {
            saliendo = true;
            window.location.href = destino;
        });
        return window.bootstrap ? new bootstrap.Modal(elemento) : null;
    }

    document.addEventListener('click', evento => {
        const enlace = evento.target.closest('a[href]');
        if (!enlace || evento.defaultPrevented) return;
        if (evento.button !== 0 || evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.altKey) return;
        if (enlace.target === '_blank' || enlace.hasAttribute('download')) return;
        const href = enlace.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:')) return;
        if (!hayCambios()) return;

        evento.preventDefault();
        destino = enlace.href;
        modal = modal || crearModal();
        if (modal) {
            modal.show();
        } else if (confirm('Tienes cambios sin guardar. Si sales ahora, se perderán. ¿Salir sin guardar?')) {
            saliendo = true;
            window.location.href = destino;
        }
    }, true);
})();
