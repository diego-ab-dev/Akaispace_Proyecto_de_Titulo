// Skeleton de imágenes de producto (estilos en styles/styles_skeleton.css).
// Mientras una foto aún no ha cargado se le pone .img-skeleton y se le quita cuando carga
// (o falla, para no dejar el brillo para siempre).
// Las imágenes que ya venían cargadas (caché) se dejan tal cual, sin parpadeo.

(function () {
    // contenedores con alto fijo: el skeleton se pinta en el contenedor y la imagen se oculta dentro
    const CONTENEDORES = [
        '.single-product .part-1',        // catálogo, categoría y búsqueda
        '.card-rel-img-wrapper',          // relacionados y recomendados (home y ficha)
        '.reco-img',                      // recomendaciones del carrito
        '.promo-image-wrapper',           // destacado del menú del navbar
        '.wishlist-item .item-image',     // favoritos
        '.ficha-producto .zoom-container',// imagen principal de la ficha del producto
        '.redes-image-placeholder',       // imagen de la sección de redes (home)
        '.video-placeholder',             // imagen de nuevos lanzamientos (home); el alto lo da el CSS mientras carga
        '.carrusel-img',                  // imagen del carrusel del menú; el alto lo da el CSS mientras carga
        '.product-thumb',                 // mis devoluciones
        '.product-img-container',         // mis opiniones
        '.product-card .prod-img',        // compra exitosa
        '.product-image-box',             // solicitar devolución
        '.mini-preview'                   // solicitar devolución (barra lateral)
    ].join(',');

    // imágenes sin contenedor propio que ya tienen tamaño fijo: el skeleton se pinta en la misma imagen
    const IMAGENES_SOLAS = [
        '.ficha-miniaturas img',          // miniaturas de la ficha del producto
        '.main > .col-img img',           // productos del carrito
        '.product-item .mini-img'         // detalle de compra
    ].join(',');

    function terminar(elemento, img) {
        if (!elemento.classList.contains('img-skeleton')) return;
        elemento.classList.remove('img-skeleton');
        img.classList.add('img-skeleton-aparece');
        img.addEventListener('animationend', function () {
            img.classList.remove('img-skeleton-aparece');
        }, { once: true });
    }

    // marca el elemento si su imagen sigue cargando; devuelve true si quedó con skeleton
    function vigilar(elemento, img) {
        if (!img || !img.getAttribute('src') || (img.complete && img.naturalWidth > 0)) return false;

        elemento.classList.add('img-skeleton');
        img.addEventListener('load', function () { terminar(elemento, img); }, { once: true });
        img.addEventListener('error', function () { terminar(elemento, img); }, { once: true });
        return true;
    }

    // la raíz también cuenta si ella misma es un contenedor o una imagen sola
    function buscar(raiz, selector) {
        const encontrados = Array.from(raiz.querySelectorAll(selector));
        if (raiz.matches && raiz.matches(selector)) encontrados.unshift(raiz);
        return encontrados;
    }

    function activar(raiz) {
        raiz = raiz || document;
        buscar(raiz, CONTENEDORES).forEach(function (contenedor) {
            vigilar(contenedor, contenedor.querySelector('img'));
        });
        buscar(raiz, IMAGENES_SOLAS).forEach(function (img) {
            vigilar(img, img);
        });
    }

    // cambia el src de una imagen que ya está en la página (p. ej. la principal de la ficha al elegir
    // otra miniatura): si la nueva no está en caché muestra el skeleton, si ya estaba solo hace el fundido
    function cambiarImagen(img, nuevoSrc, contenedor) {
        contenedor = contenedor || img;
        contenedor.classList.remove('img-skeleton');
        img.src = nuevoSrc;
        if (!vigilar(contenedor, img)) {
            img.classList.remove('img-skeleton-aparece');
            void img.offsetWidth; // reinicia la animación si se hace clic seguido
            img.classList.add('img-skeleton-aparece');
            img.addEventListener('animationend', function () {
                img.classList.remove('img-skeleton-aparece');
            }, { once: true });
        }
    }

    // para listas que se reemplazan por JS (p. ej. favoritos.js)
    window.activarSkeletonImagenes = activar;
    window.cambiarImagenConSkeleton = cambiarImagen;

    activar(document);
})();
