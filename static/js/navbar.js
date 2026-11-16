// Navbar de la tienda (templates/partials/navbar.html): buscador, menú lateral en pantallas chicas y submenús.
(function () {
  const nav = document.querySelector(".nav-tienda");
  if (!nav) return;
  const navbar = nav.querySelector(".navbar");
  const lupa = nav.querySelector(".search-box > i");
  const navLinks = nav.querySelector(".nav-links");
  const menuOpenBtn = nav.querySelector(".bx-menu");
  const menuCloseBtn = nav.querySelector(".nav-links .bx-x");
  const enMenuLateral = () => window.matchMedia("(max-width: 1200px)").matches;

  // los íconos con role="button" (menú, cerrar, lupa) también responden a Enter y Espacio
  nav.querySelectorAll('i[role="button"]').forEach(function (icono) {
    icono.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      icono.click();
    });
  });

  // "Hola, usuario" solo despliega su submenú: no salta al inicio de la página
  const linkCuenta = nav.querySelector('.login-desktop .link[href="#"]');
  if (linkCuenta) linkCuenta.addEventListener("click", function (e) { e.preventDefault(); });

  if (lupa && navbar) {
    lupa.addEventListener("click", () => {
      const abierto = navbar.classList.toggle("showInput");
      lupa.classList.replace(abierto ? "bx-search" : "bx-x", abierto ? "bx-x" : "bx-search");
      if (abierto) {
        const input = nav.querySelector(".search-box input");
        if (input) input.focus();
      }
    });
  }

  const abrirMenu = () => { navLinks.style.left = "0"; };
  const cerrarMenu = () => { navLinks.style.left = "-100%"; };

  if (navLinks) {
    if (menuOpenBtn) menuOpenBtn.addEventListener("click", abrirMenu);
    if (menuCloseBtn) menuCloseBtn.addEventListener("click", cerrarMenu);

    // los links a secciones del home (#nosotros, #local...) cierran el menú lateral
    navLinks.querySelectorAll('.links a[href^="#"]:not([href="#"])').forEach(function (link) {
      link.addEventListener("click", function () {
        if (navLinks.style.left === "0px") cerrarMenu();
      });
    });

    // en el menú lateral cada categoría (flecha o nombre) abre solo su propio submenú
    navLinks.querySelectorAll(".links > li.con-submenu").forEach(function (li) {
      const alternar = function (e) {
        e.preventDefault(); // el nombre es href="#": no salta al inicio de la página
        if (!enMenuLateral()) return;
        const abierto = li.classList.toggle("abierto");
        if (nombre) nombre.setAttribute("aria-expanded", abierto ? "true" : "false");
      };
      const flecha = li.querySelector(":scope > .arrow");
      const nombre = li.querySelector(':scope > a[href="#"]');
      if (flecha) flecha.addEventListener("click", alternar);
      if (nombre) nombre.addEventListener("click", alternar);
    });

    // al volver a escritorio el menú lateral queda cerrado
    window.matchMedia("(max-width: 1200px)").addEventListener("change", function (mq) {
      if (!mq.matches) navLinks.style.left = "";
    });
  }
})();
