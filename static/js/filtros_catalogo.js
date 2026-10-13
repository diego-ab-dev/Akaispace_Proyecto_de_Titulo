// Filtros del catálogo: no envía los campos vacíos (URLs más limpias) y
// el selector "Ordenar" envía el mismo formulario para no perder los filtros.
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('form-filtros');
    if (!form) return;

    form.addEventListener('submit', function () {
        form.querySelectorAll('input[name], select[name]').forEach(function (campo) {
            if (campo.value.trim() === '') campo.disabled = true;
        });
        document.querySelectorAll('[form="form-filtros"]').forEach(function (campo) {
            if (campo.value === '' || campo.value === 'relevancia') campo.disabled = true;
        });
    });

    document.querySelectorAll('select[form="form-filtros"]').forEach(function (select) {
        select.addEventListener('change', function () {
            if (form.requestSubmit) form.requestSubmit();
            else form.submit();
        });
    });

    // si el usuario vuelve con el botón "atrás", reactiva los campos deshabilitados
    window.addEventListener('pageshow', function () {
        document.querySelectorAll('#form-filtros [disabled], [form="form-filtros"][disabled]').forEach(function (campo) {
            campo.disabled = false;
        });
    });
});
