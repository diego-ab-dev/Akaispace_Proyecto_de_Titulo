// Skeleton de imágenes de producto (estilos en styles/styles_skeleton.css).
// A cada contenedor de imagen de producto cuya foto aún no ha cargado le pone .img-skeleton,
// y se lo quita cuando la imagen carga (o falla, para no dejar el brillo para siempre).
// Las imágenes que ya venían cargadas (caché) se dejan tal cual, sin parpadeo.

(function () {
    // contenedores de imagen de producto en la tienda
    const CONTENEDORES = [
        '.single-product .part-1',        // catálogo, categoría y búsqueda
        '.card-rel-img-wrapper',          // relacionados y recomendados (home y ficha)
        '.reco-img',                      // recomendaciones del carrito
        '.promo-image-wrapper',           // destacado del menú del navbar
        '.wishlist-item .item-image'      // favoritos
    ].join(',');

    function terminar(contenedor, img) {
        if (!contenedor.classList.contains('img-skeleton')) return;
        contenedor.classList.remove('img-skeleton');
        img.classList.add('img-skeleton-aparece');
        img.addEventListener('animationend', function () {
            img.classList.remove('img-skeleton-aparece');
        }, { once: true });
    }

    function activar(raiz) {
        (raiz || document).querySelectorAll(CONTENEDORES).forEach(function (contenedor) {
            const img = contenedor.querySelector('img');
            if (!img || (img.complete && img.naturalWidth > 0)) return;

            contenedor.classList.add('img-skeleton');
            img.addEventListener('load', function () { terminar(contenedor, img); }, { once: true });
            img.addEventListener('error', function () { terminar(contenedor, img); }, { once: true });
        });
    }

    // para listas que se reemplazan por JS (p. ej. favoritos.js)
    window.activarSkeletonImagenes = activar;

    activar(document);
})();
