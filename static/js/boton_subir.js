// Botón "volver arriba" (templates/partials/boton_subir.html): aparece después de bajar un poco más de
// media pantalla y el anillo marca cuánto se ha recorrido de la página.
(function () {
  const boton = document.getElementById("boton-subir");
  if (!boton) return;
  const progreso = boton.querySelector(".boton-subir-progreso");
  const sinAnimacion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let pendiente = false;

  function actualizar() {
    pendiente = false;
    const y = window.scrollY || document.documentElement.scrollTop;
    const recorrible = document.documentElement.scrollHeight - window.innerHeight;
    const visible = recorrible > 0 && y > Math.min(400, window.innerHeight * 0.6);
    boton.classList.toggle("visible", visible);
    boton.tabIndex = visible ? 0 : -1;
    if (progreso && recorrible > 0) {
      const pct = Math.min(100, Math.max(0, (y / recorrible) * 100));
      progreso.style.strokeDashoffset = String(100 - pct);
    }
  }

  function alHacerScroll() {
    if (!pendiente) {
      pendiente = true;
      window.requestAnimationFrame(actualizar);
    }
  }

  window.addEventListener("scroll", alHacerScroll, { passive: true });
  window.addEventListener("resize", alHacerScroll);

  boton.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: sinAnimacion.matches ? "auto" : "smooth" });
    boton.blur();
  });

  actualizar();
})();
