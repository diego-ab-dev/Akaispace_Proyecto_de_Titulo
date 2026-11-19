// Skeleton de imágenes de producto

(function () {
    const CONTENEDORES = [
        '.single-product .part-1',
        '.card-rel-img-wrapper',
        '.reco-img',
        '.promo-image-wrapper',
        '.wishlist-item .item-image',
        '.ficha-producto .zoom-container',
        '.redes-image-placeholder',
        '.video-placeholder',
        '.carrusel-img',
        '.product-thumb',
        '.product-img-container',
        '.product-card .prod-img',
        '.product-image-box',
        '.mini-preview'
    ].join(',');

    const IMAGENES_SOLAS = [
        '.ficha-miniaturas img',
        '.main > .col-img img',
        '.product-item .mini-img'
    ].join(',');

    function terminar(elemento, img) {
        if (!elemento.classList.contains('img-skeleton')) return;
        elemento.classList.remove('img-skeleton');
        img.classList.add('img-skeleton-aparece');
        img.addEventListener('animationend', function () {
            img.classList.remove('img-skeleton-aparece');
        }, { once: true });
    }

    function vigilar(elemento, img) {
        if (!img || !img.getAttribute('src') || (img.complete && img.naturalWidth > 0)) return false;

        elemento.classList.add('img-skeleton');
        img.addEventListener('load', function () { terminar(elemento, img); }, { once: true });
        img.addEventListener('error', function () { terminar(elemento, img); }, { once: true });
        return true;
    }

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

    function cambiarImagen(img, nuevoSrc, contenedor) {
        contenedor = contenedor || img;
        contenedor.classList.remove('img-skeleton');
        img.src = nuevoSrc;
        if (!vigilar(contenedor, img)) {
            img.classList.remove('img-skeleton-aparece');
            void img.offsetWidth;
            img.classList.add('img-skeleton-aparece');
            img.addEventListener('animationend', function () {
                img.classList.remove('img-skeleton-aparece');
            }, { once: true });
        }
    }

    window.activarSkeletonImagenes = activar;
    window.cambiarImagenConSkeleton = cambiarImagen;

    activar(document);
})();
