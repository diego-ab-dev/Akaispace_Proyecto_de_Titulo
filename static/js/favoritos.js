// Favoritos (templates/favorite.html): quitar uno o varios favoritos y agregarlos al carrito.
// La URL para quitar varios llega en el data- de su <script>.
const datosFavoritos = document.currentScript.dataset;

    function getCSRFToken() {
    let cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        let [key, value] = cookie.trim().split('=');
        if (key === 'csrftoken') return value;
    }
    return null;
}

// parte de seleccionar para eliminar
var confirmModal = null;
var toastNotification = null;

function ensureBootstrapInstances() {
    if (!confirmModal) {
    const modalEl = document.getElementById('confirmDeleteModal');
    if (modalEl) confirmModal = new bootstrap.Modal(modalEl);
    }
    if (!toastNotification) {
    const toastEl = document.getElementById('liveToast');
    if (toastEl) toastNotification = new bootstrap.Toast(toastEl);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    ensureBootstrapInstances();
});

function getCSRFToken() {
    let cookies = document.cookie.split(';');
    for (let cookie of cookies) {
    let [key, value] = cookie.trim().split('=');
    if (key === 'csrftoken') return value;
    }
    return null;
}

function mostrarToast(mensaje, claseFondo) {
    ensureBootstrapInstances();
    if (!toastNotification) {
    console.warn('Toast no disponible');
    return;
    }

    const toastEl = document.getElementById('liveToast');
    const toastBody = document.getElementById('toastMessage');

    toastEl.classList.remove("bg-success", "bg-danger", "bg-warning");
    toastEl.classList.add(claseFondo);

    toastBody.textContent = mensaje;
    toastNotification.show();
}

// boton de eliminar
function eliminarSeleccionados() {
    ensureBootstrapInstances();

    const checkboxes = document.querySelectorAll('.check-item:checked');

    if (checkboxes.length === 0) {
    mostrarToast("Selecciona al menos un producto.", "bg-warning");
    return;
    }

    if (!confirmModal) {
    if (!confirm("¿Eliminar los productos seleccionados?")) return;
    ejecutarEliminacion(checkboxes);
    return;
    }

    confirmModal.show();

    const btn = document.getElementById('confirmDeleteBtn');
    if (btn) {
    btn.onclick = function() {
        ejecutarEliminacion(checkboxes);
        confirmModal.hide();
    };
    }
}

// ejecutar
function actualizarListaFavoritos() {
    fetch(window.location.href)
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            const nuevaLista = doc.querySelector('.wishlist-container');
            const listaActual = document.querySelector('.wishlist-container');

            const nuevaPaginacion = doc.querySelector('.pagination-wrapper');
            const paginacionActual = document.querySelector('.pagination-wrapper');

            if (nuevaLista && listaActual) {
                listaActual.innerHTML = nuevaLista.innerHTML;
            }

            if (nuevaPaginacion && paginacionActual) {
                paginacionActual.innerHTML = nuevaPaginacion.innerHTML;
            } else if (!nuevaPaginacion && paginacionActual) {
                paginacionActual.innerHTML = '';
            }
        })
        .catch(err => console.error('Error actualizando la lista:', err));
}


function ejecutarEliminacion(checkboxes) {
    const idsToDelete = Array.from(checkboxes).map(cb => cb.value);

    fetch(datosFavoritos.urlEliminarSeleccionados, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({ ids: idsToDelete })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {

            idsToDelete.forEach(id => {
                const row = document.getElementById(`item-${id}`);
                if (row) {
                    row.style.transition = "all 0.3s ease";
                    row.style.opacity = "0";
                    row.style.transform = "translateX(20px)";
                }
            });

            mostrarToast("Productos eliminados correctamente.", "bg-success");

            setTimeout(() => {
                actualizarListaFavoritos(); 
            }, 300);

        } else {
            mostrarToast("Error al eliminar.", "bg-danger");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarToast("Error de conexión.", "bg-danger");
    });
}
