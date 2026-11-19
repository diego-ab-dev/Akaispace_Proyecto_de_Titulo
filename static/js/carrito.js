// Carrito
const datosCarrito = document.currentScript.dataset;

const regionesCiudades = JSON.parse(document.getElementById('regiones-ciudades').textContent);

function cargarRegiones() {
    const selectRegion = document.getElementById("input-region");
    selectRegion.innerHTML = '<option value="">Selecciona una región</option>';
    for (const region in regionesCiudades) {
        selectRegion.innerHTML += `<option value="${region}">${region}</option>`;
    }
}

function cargarCiudades() {
    const region = document.getElementById("input-region").value;
    const selectCiudad = document.getElementById("input-ciudad");
    const ciudades = regionesCiudades[region] || [];
    selectCiudad.innerHTML = `<option value="">${ciudades.length ? 'Selecciona una ciudad' : 'Primero elige una región'}</option>`;
    ciudades.forEach(ciudad => {
        selectCiudad.innerHTML += `<option value="${ciudad}">${ciudad}</option>`;
    });
}

function formatoChileno(valor) {
    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency: 'CLP',
        minimumFractionDigits: 0, 
    }).format(valor);
}

// Opciones de entrega
const opcionesEnvio = JSON.parse(document.getElementById('opciones-envio').textContent);
const CIUDAD_TIENDA = datosCarrito.ciudadTienda;
let subtotalActual = Number(datosCarrito.subtotal);

function opcionEnvio(clave) {
    return opcionesEnvio.find(opcion => opcion.clave === clave);
}

function costoEnvio(opcion, subtotal) {
    if (opcion.precio === null) return 0;
    if (opcion.gratis_desde !== null && subtotal >= opcion.gratis_desde) return 0;
    return opcion.precio;
}

function textoPrecioEnvio(opcion, subtotal) {
    if (opcion.precio === null) return 'Por pagar';
    const costo = costoEnvio(opcion, subtotal);
    return costo === 0 ? 'Gratis' : formatoChileno(costo);
}

function disponibleEn(opcion, ciudad) {
    if (opcion.disponible_en === 'valdivia') return ciudad === CIUDAD_TIENDA;
    if (opcion.disponible_en === 'regiones') return ciudad !== '' && ciudad !== CIUDAD_TIENDA;
    return true;
}

function actualizarEntrega() {
    const ciudadElem = document.getElementById('envio-ciudad');
    if (!ciudadElem) return;
    const ciudad = ciudadElem.innerText.trim();

    document.querySelectorAll('.entrega-opcion').forEach(label => {
        const opcion = opcionEnvio(label.dataset.clave);
        const radio = label.querySelector('input');
        const disponible = disponibleEn(opcion, ciudad);
        label.hidden = !disponible;
        if (!disponible) radio.checked = false;
        label.classList.toggle('seleccionada', radio.checked);
        label.querySelector('.entrega-precio').textContent = textoPrecioEnvio(opcion, subtotalActual);
    });

    const delivery = opcionEnvio('delivery');
    const nota = document.getElementById('entrega-nota');
    if (ciudad === CIUDAD_TIENDA && delivery && delivery.gratis_desde !== null && subtotalActual < delivery.gratis_desde) {
        nota.textContent = `Te faltan ${formatoChileno(delivery.gratis_desde - subtotalActual)} para tener delivery gratis.`;
    } else if (ciudad !== CIUDAD_TIENDA) {
        nota.textContent = 'El Delivery Express es solo para Valdivia.';
    } else {
        nota.textContent = '';
    }

    const elegido = document.querySelector('input[name="envio"]:checked');
    const opcion = elegido ? opcionEnvio(elegido.value) : null;
    document.getElementById('envio-resumen').textContent = opcion ? textoPrecioEnvio(opcion, subtotalActual) : 'Por elegir';
    const totalFinalElem = document.getElementById('total-final');
    if (totalFinalElem) {
        totalFinalElem.textContent = formatoChileno(subtotalActual + (opcion ? costoEnvio(opcion, subtotalActual) : 0));
    }
}

document.querySelectorAll('input[name="envio"]').forEach(radio => {
    radio.addEventListener('change', actualizarEntrega);
});

function mostrarError(mensaje) {
const errorBox = document.getElementById("mensaje-error");
errorBox.textContent = mensaje;
errorBox.style.display = "block";

setTimeout(() => {
    errorBox.style.display = "none";
}, 3000);
}

// Contadores y totales
function textoItems(cantidad) {
    return cantidad + (cantidad === 1 ? ' ítem' : ' ítems');
}

function recalcularResumen() {
    const inputs = Array.from(document.querySelectorAll('.input-cantidad'));
    const totalItems = inputs.reduce((suma, input) => suma + parseInt(input.value, 10), 0);
    const subtotal = inputs.reduce((suma, input) =>
        suma + parseInt(input.value, 10) * parseInt(input.dataset.precio || '0', 10), 0);

    ['total-items-count', 'total-items-count-summary'].forEach(id => {
        const elem = document.getElementById(id);
        if (elem) elem.textContent = textoItems(totalItems);
    });
    const subtotalElem = document.getElementById('subtotal-resumen');
    if (subtotalElem) subtotalElem.textContent = formatoChileno(subtotal);
    subtotalActual = subtotal;

    if (inputs.length === 0) {
        mostrarCarritoVacio();
        return;
    }
    actualizarEntrega();
}

// Cantidades del carrito
const guardadosPendientes = new Map();
const temporizadores = new Map();

function stepperDe(input) {
    return input.form.querySelector('.cantidad-stepper');
}

function mostrarCantidad(input, cantidad) {
    input.value = cantidad;
    const stepper = stepperDe(input);
    stepper.querySelector('.cantidad-valor').textContent = cantidad;
    stepper.querySelector('[data-paso="-1"]').disabled = cantidad <= 1;
    stepper.querySelector('[data-paso="1"]').disabled = cantidad >= parseInt(input.dataset.stock, 10);
}

function marcarError(input, mensaje) {
    const elem = document.getElementById(`error-${input.dataset.item}`);
    if (elem) elem.textContent = mensaje;
}

function volverACantidadGuardada(input, mensaje) {
    if (!input.isConnected) return;
    mostrarCantidad(input, parseInt(input.dataset.confirmada, 10));
    marcarError(input, mensaje);
    recalcularResumen();
}

function actualizarCantidad(input) {
    const form = input.form;
    const formData = new FormData(form);

    const guardado = fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': formData.get('csrfmiddlewaretoken') },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            input.dataset.confirmada = formData.get('cantidad');
            return true;
        }
        volverACantidadGuardada(input, data.error || 'No se pudo actualizar la cantidad.');
        return false;
    })
    .catch(error => {
        console.error('Error:', error);
        volverACantidadGuardada(input, 'No se pudo actualizar la cantidad. Inténtalo de nuevo.');
        return false;
    })
    .finally(() => {
        if (guardadosPendientes.get(input.dataset.item) === guardado) {
            guardadosPendientes.delete(input.dataset.item);
        }
    });

    guardadosPendientes.set(input.dataset.item, guardado);
    return guardado;
}

function guardarAhora(input) {
    clearTimeout(temporizadores.get(input.dataset.item));
    temporizadores.delete(input.dataset.item);
    const pendiente = guardadosPendientes.get(input.dataset.item);
    if (pendiente && input.dataset.enviando === input.value) {
        return pendiente;
    }
    if (input.value !== input.dataset.confirmada) {
        input.dataset.enviando = input.value;
        return actualizarCantidad(input);
    }
    return pendiente || Promise.resolve(true);
}

document.querySelectorAll('.input-cantidad').forEach(input => {
    mostrarCantidad(input, parseInt(input.value, 10));
});

document.querySelectorAll('.btn-cantidad').forEach(boton => {
    boton.addEventListener('click', function () {
        const input = this.closest('form').querySelector('.input-cantidad');
        const stock = parseInt(input.dataset.stock, 10);
        const nueva = Math.max(Math.min(parseInt(input.value, 10) + parseInt(this.dataset.paso, 10), stock), 1);
        mostrarCantidad(input, nueva);
        marcarError(input, '');
        recalcularResumen();
        clearTimeout(temporizadores.get(input.dataset.item));
        temporizadores.set(input.dataset.item, setTimeout(() => guardarAhora(input), 500));
    });
});

const formProceder = document.getElementById('form-proceder');
if (formProceder) {
    formProceder.addEventListener('submit', function (e) {
        e.preventDefault();
        const datosCompra = document.getElementById('datos-compra');
        if (datosCompra && (!datosCompra.dataset.tieneRut || !datosCompra.dataset.tieneTelefono)) {
            abrirModal('Completa tu RUT y tu teléfono para continuar con la compra.');
            return;
        }
        if (!document.querySelector('input[name="envio"]:checked')) {
            mostrarError('Elige cómo quieres recibir tu compra.');
            return;
        }
        const inputs = Array.from(document.querySelectorAll('.input-cantidad'));
        Promise.all(inputs.map(guardarAhora)).then(resultados => {
            if (resultados.every(Boolean)) {
                formProceder.submit();
            } else {
                mostrarError('Revisa las cantidades marcadas antes de continuar.');
            }
        });
    });
}

// Eliminar productos
const csrfCarrito = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

function mostrarCarritoVacio() {
    document.querySelector('.acciones-carrito')?.remove();
    const lista = document.querySelector('.products-scroll-container');
    if (lista) {
        lista.innerHTML = '<div class="text-center py-5"><h5 class="text-muted">Tu carrito está vacío.</h5>' +
                          '<a href="/menu" class="btn btn-explorar mt-3">Explorar Productos</a></div>';
    }
    const resumenCompra = document.getElementById('resumen-compra');
    if (resumenCompra) {
        const aviso = document.createElement('p');
        aviso.className = 'text-muted mt-3 text-center';
        aviso.textContent = 'Tu carrito está vacío.';
        resumenCompra.replaceWith(aviso);
    }
}

function quitarItems(ids) {
    ids.forEach(id => {
        clearTimeout(temporizadores.get(String(id)));
        temporizadores.delete(String(id));
        const row = document.getElementById(`item-${id}`);
        if (row) row.remove();
    });
    recalcularResumen();
    actualizarSeleccion();
}

function enviarEliminacion(url, ids) {
    const datos = new FormData();
    ids.forEach(id => datos.append('ids', id));

    return fetch(url, {
        method: 'POST',
        body: datos,
        headers: { 'X-CSRFToken': csrfCarrito },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            quitarItems(data.eliminados || ids);
        } else {
            mostrarError(data.error || 'No se pudieron eliminar los productos.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarError('No se pudieron eliminar los productos. Inténtalo de nuevo.');
    });
}

function eliminarItem(itemId, element) {
    enviarEliminacion(element.getAttribute('data-url'), [itemId]);
}

function actualizarSeleccion() {
    const checks = document.querySelectorAll('.check-item');
    const marcados = document.querySelectorAll('.check-item:checked').length;

    const todos = document.getElementById('check-todos');
    if (todos) {
        todos.checked = checks.length > 0 && marcados === checks.length;
        todos.indeterminate = marcados > 0 && marcados < checks.length;
    }
    const contador = document.getElementById('contador-seleccionados');
    if (contador) contador.textContent = marcados;
    const btnEliminar = document.getElementById('btn-eliminar-seleccionados');
    if (btnEliminar) {
        btnEliminar.disabled = marcados === 0;
        if (marcados === 0) bootstrap.Tooltip.getInstance(btnEliminar)?.hide();
    }
}

document.querySelectorAll('.btn-icono-carrito').forEach(boton => new bootstrap.Tooltip(boton));

document.getElementById('check-todos')?.addEventListener('change', function () {
    document.querySelectorAll('.check-item').forEach(check => check.checked = this.checked);
    actualizarSeleccion();
});

document.querySelectorAll('.check-item').forEach(check => {
    check.addEventListener('change', actualizarSeleccion);
});

const modalConfirmarElem = document.getElementById('modal-confirmar-eliminar');
const modalConfirmar = modalConfirmarElem ? new bootstrap.Modal(modalConfirmarElem) : null;
let accionPendiente = null;

function confirmarEliminacion(texto, accion) {
    if (!modalConfirmar) {
        if (confirm(texto)) accion();
        return;
    }
    document.getElementById('texto-confirmar-eliminar').textContent = texto;
    accionPendiente = accion;
    modalConfirmar.show();
}

modalConfirmarElem?.addEventListener('show.bs.modal', () => {
    document.querySelectorAll('.btn-icono-carrito').forEach(boton => bootstrap.Tooltip.getInstance(boton)?.hide());
});

document.getElementById('btn-confirmar-eliminar')?.addEventListener('click', function () {
    modalConfirmar.hide();
    const accion = accionPendiente;
    accionPendiente = null;
    if (accion) accion();
});

document.getElementById('btn-eliminar-seleccionados')?.addEventListener('click', function () {
    const ids = Array.from(document.querySelectorAll('.check-item:checked')).map(check => check.value);
    if (ids.length === 0) {
        mostrarError('Selecciona al menos un producto.');
        return;
    }
    const texto = ids.length === 1
        ? 'Se eliminará 1 producto de tu carrito.'
        : `Se eliminarán ${ids.length} productos de tu carrito.`;
    confirmarEliminacion(texto, () => enviarEliminacion(datosCarrito.urlEliminarSeleccionados, ids));
});

document.getElementById('btn-vaciar-carrito')?.addEventListener('click', function () {
    confirmarEliminacion('Se eliminarán todos los productos de tu carrito.',
        () => enviarEliminacion(datosCarrito.urlVaciar, []));
});

actualizarSeleccion();

// "Complementa tu compra"
document.querySelectorAll('.reco-agregar').forEach(boton => {
    boton.addEventListener('click', function () {
        const datos = new FormData();
        datos.append('cantidad', '1');
        if (this.dataset.recomendacion) datos.append('recomendacion', this.dataset.recomendacion);
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Agregando';

        fetch(this.dataset.url, {
            method: 'POST',
            body: datos,
            headers: { 'X-CSRFToken': csrfCarrito || datosCarrito.csrf, 'X-Requested-With': 'XMLHttpRequest' },
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) throw new Error(data.error || 'No se pudo agregar el producto.');
            this.classList.add('agregado');
            this.innerHTML = '<i class="fas fa-check" aria-hidden="true"></i> Agregado';
            const inputs = Array.from(document.querySelectorAll('.input-cantidad'));
            return Promise.all(inputs.map(guardarAhora)).then(() => setTimeout(() => window.location.reload(), 500));
        })
        .catch(error => {
            mostrarError(error.message || 'No se pudo agregar el producto.');
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-cart-plus" aria-hidden="true"></i> Agregar';
        });
    });
});

    function limpiarErroresModal() {
        const errorGeneral = document.getElementById('modal-envio-error');
        errorGeneral.hidden = true;
        errorGeneral.textContent = '';
        document.querySelectorAll('.campo-error-modal').forEach(elem => elem.textContent = '');
    }

    function abrirModal(aviso) {
        const modal = document.getElementById("modal-envio");
        modal.style.display = "flex";
        limpiarErroresModal();
        if (typeof aviso === 'string' && aviso) {
            const errorGeneral = document.getElementById('modal-envio-error');
            errorGeneral.textContent = aviso;
            errorGeneral.hidden = false;
        }

        let regionActual = document.getElementById("envio-region").innerText;
        let ciudadActual = document.getElementById("envio-ciudad").innerText;
        let direccionActual = document.getElementById("envio-direccion").innerText;

        const regionSelect = document.getElementById("input-region");
        const ciudadSelect = document.getElementById("input-ciudad");
        const direccionInput = document.getElementById("input-direccion");
        const counter = document.getElementById("address-counter");

        cargarRegiones(); 
        regionSelect.value = regionActual;
        cargarCiudades(); 
        ciudadSelect.value = ciudadActual;

        direccionInput.value = direccionActual;

        const actualizarContador = () => {
            const len = direccionInput.value.length;
            const max = direccionInput.getAttribute('maxlength') || 100;
            counter.textContent = `${len}/${max}`;

            if(len >= max) {
                counter.classList.add('text-danger');
                counter.classList.remove('text-muted');
            } else {
                counter.classList.remove('text-danger');
                counter.classList.add('text-muted');
            }
        };

        actualizarContador();
        direccionInput.oninput = actualizarContador;
    }

    actualizarEntrega();

    function cerrarModal() {
        document.getElementById("modal-envio").style.display = "none";
    }

    function guardarEnvio() {
        limpiarErroresModal();
        const data = new FormData();
        const inputRut = document.getElementById("input-rut");
        if (inputRut && !inputRut.disabled) data.append("rut", inputRut.value);
        data.append("telefono", document.getElementById("input-telefono").value);
        data.append("region", document.getElementById("input-region").value);
        data.append("ciudad", document.getElementById("input-ciudad").value);
        data.append("direccion", document.getElementById("input-direccion").value);

        fetch(datosCarrito.urlGuardarEnvio, {
            method: "POST",
            body: data,
            headers: { 'X-CSRFToken': csrfCarrito || datosCarrito.csrf },
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById("envio-rut").innerText = data.rut || '';
                document.getElementById("envio-telefono").innerText = data.telefono;
                document.getElementById("envio-region").innerText = data.region;
                document.getElementById("envio-ciudad").innerText = data.ciudad;
                document.getElementById("envio-direccion").innerText = data.direccion;
                if (inputRut && data.rut) {
                    inputRut.value = data.rut;
                    inputRut.disabled = true;
                    inputRut.readOnly = true;
                }
                const datosCompra = document.getElementById('datos-compra');
                datosCompra.dataset.tieneRut = data.rut ? '1' : '';
                datosCompra.dataset.tieneTelefono = data.telefono ? '1' : '';
                ['falta-rut', 'falta-telefono', 'btn-completar-datos'].forEach(id => document.getElementById(id)?.remove());
                cerrarModal();
                actualizarEntrega();
            } else {
                const errores = data.errors || {};
                let porCampo = false;
                Object.keys(errores).forEach(campo => {
                    const elem = document.querySelector(`.campo-error-modal[data-error-de="${campo}"]`);
                    if (elem) { elem.textContent = errores[campo][0]; porCampo = true; }
                });
                if (!porCampo) {
                    const errorGeneral = document.getElementById('modal-envio-error');
                    errorGeneral.textContent = data.error || 'No pudimos guardar tus datos. Inténtalo de nuevo.';
                    errorGeneral.hidden = false;
                }
            }
        })
        .catch(() => {
            const errorGeneral = document.getElementById('modal-envio-error');
            errorGeneral.textContent = 'No pudimos guardar tus datos. Inténtalo de nuevo.';
            errorGeneral.hidden = false;
        });
    }
