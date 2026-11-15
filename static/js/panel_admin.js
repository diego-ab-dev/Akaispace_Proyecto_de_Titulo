// Navbar lateral del panel de administración
document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.getElementById("header-toggle");
  const nav = document.getElementById("nav-bar");
  const bodypd = document.getElementById("body-pd");
  const headerpd = document.getElementById("header");

  if (toggle && nav && bodypd && headerpd) {
    function alternarMenu(abrir) {
      nav.classList.toggle("show", abrir);
      toggle.classList.toggle("bx-x", abrir);
      bodypd.classList.toggle("body-pd", abrir);
      headerpd.classList.toggle("body-pd", abrir);
    }
    toggle.addEventListener("click", (evento) => {
      evento.stopPropagation();
      alternarMenu(!nav.classList.contains("show"));
    });

    // en celular el menú va encima del contenido: se cierra al tocar fuera de él o al elegir una sección
    const esCelular = window.matchMedia("(max-width: 767px)");
    document.addEventListener("click", (evento) => {
      const fuera = !nav.contains(evento.target) && !toggle.contains(evento.target);
      if (esCelular.matches && nav.classList.contains("show") && fuera) {
        // el toque solo cierra el menú: no activa lo que había debajo del fondo oscuro
        evento.preventDefault();
        evento.stopPropagation();
        alternarMenu(false);
      }
    }, true);
    nav.querySelectorAll(".nav_link, .nav_logo").forEach((enlace) => {
      enlace.addEventListener("click", () => {
        if (esCelular.matches) alternarMenu(false);
      });
    });
  }

  const linkColor = document.querySelectorAll(".nav_link");
  function colorLink() {
    linkColor.forEach((l) => l.classList.remove("active"));
    this.classList.add("active");
  }
  linkColor.forEach((l) => l.addEventListener("click", colorLink));
});
