// Navbar de la tienda (templates/partials/navbar.html): buscador, menú lateral en móvil y submenús.
// Cada elemento se revisa antes de usarlo porque no todas las variantes del navbar los tienen.
(function () {
  const navbar = document.querySelector(".navbar");
  const searchBox = document.querySelector(".search-box .bx-search");
  const navLinks = document.querySelector(".nav-links");
  const menuOpenBtn = document.querySelector(".navbar .bx-menu");
  const menuCloseBtn = document.querySelector(".nav-links .bx-x");

  if (searchBox && navbar) {
    searchBox.addEventListener("click", () => {
      navbar.classList.toggle("showInput");
      if (navbar.classList.contains("showInput")) {
        searchBox.classList.replace("bx-search", "bx-x");
      } else {
        searchBox.classList.replace("bx-x", "bx-search");
      }
    });
  }

  if (menuOpenBtn && navLinks) {
    menuOpenBtn.onclick = function () {
      navLinks.style.left = "0";
    };
  }

  if (menuCloseBtn && navLinks) {
    menuCloseBtn.onclick = function () {
      navLinks.style.left = "-100%";
    };
  }

  // flechas de los submenús en móvil
  const flechas = { ".htmlcss-arrow": "show1", ".more-arrow": "show2", ".js-arrow": "show3" };
  for (const [selector, clase] of Object.entries(flechas)) {
    const flecha = document.querySelector(selector);
    if (flecha && navLinks) {
      flecha.onclick = function () {
        navLinks.classList.toggle(clase);
      };
    }
  }
})();
