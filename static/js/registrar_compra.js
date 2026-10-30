// Panel > Compras > Registrar compra (HU-10): buscar productos por nombre o código de barras y armar la compra.
// El servidor vuelve a validar todo al registrar.
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("form-compra");
  const buscador = document.getElementById("buscar-producto");
  const resultados = document.getElementById("resultados-busqueda");
  const aviso = document.getElementById("aviso-busqueda");
  const cuerpo = document.getElementById("items-compra");
  const vacio = document.getElementById("compra-vacia");
  const total = document.getElementById("total-compra");
  const boton = document.getElementById("btn-registrar");
  const urlBuscar = form.dataset.urlBuscar;

  const items = new Map(); // id del producto -> { cantidad, costo, subtotal }
  const pesos = (monto) => "$" + monto.toLocaleString("es-CL");
  const entero = (input) => parseInt(input.value, 10) || 0;

  function actualizar() {
    let suma = 0;
    let valida = items.size > 0;
    items.forEach((item) => {
      const subtotal = entero(item.cantidad) * entero(item.costo);
      item.subtotal.textContent = pesos(subtotal);
      suma += subtotal;
      [item.cantidad, item.costo].forEach((input) => {
        const malo = entero(input) < 1;
        input.classList.toggle("is-invalid", malo);
        if (malo) valida = false;
      });
    });
    vacio.hidden = items.size > 0;
    total.textContent = pesos(suma);
    boton.disabled = !valida || !form.proveedor.value.trim();
  }

  function campoNumero(nombre, valor, etiqueta) {
    const input = document.createElement("input");
    input.type = "number";
    input.name = nombre;
    input.min = 1;
    input.step = 1;
    input.inputMode = "numeric";
    input.value = valor;
    input.className = "form-control form-control-sm venta-item__cantidad";
    input.setAttribute("aria-label", etiqueta);
    input.addEventListener("input", actualizar);
    return input;
  }

  function crearFila(producto, cantidad, costo) {
    const fila = document.createElement("tr");

    const celdaProducto = document.createElement("td");
    const info = document.createElement("div");
    info.className = "venta-item__producto";
    const img = document.createElement("img");
    img.className = "venta-miniatura";
    img.alt = "";
    if (producto.imagen) img.src = producto.imagen;
    const textos = document.createElement("div");
    textos.textContent = producto.nombre;
    const detalle = document.createElement("small");
    detalle.textContent = [producto.codigo, `Stock actual: ${producto.stock}`].filter(Boolean).join(" · ");
    textos.appendChild(detalle);
    const oculto = document.createElement("input");
    oculto.type = "hidden";
    oculto.name = "producto";
    oculto.value = producto.id;
    info.append(img, textos, oculto);
    celdaProducto.appendChild(info);

    const inputCantidad = campoNumero("cantidad", cantidad, `Cantidad de ${producto.nombre}`);
    const inputCosto = campoNumero("costo_unitario", costo, `Costo unitario de ${producto.nombre}`);
    inputCosto.classList.replace("venta-item__cantidad", "compra-item__costo");
    const celdaCantidad = document.createElement("td");
    celdaCantidad.appendChild(inputCantidad);
    const celdaCosto = document.createElement("td");
    celdaCosto.appendChild(inputCosto);

    const subtotal = document.createElement("td");

    const celdaQuitar = document.createElement("td");
    const quitar = document.createElement("button");
    quitar.type = "button";
    quitar.className = "venta-item__quitar";
    quitar.title = "Quitar";
    quitar.setAttribute("aria-label", `Quitar ${producto.nombre}`);
    quitar.innerHTML = "<i class='bx bx-trash'></i>";
    quitar.addEventListener("click", () => {
      items.delete(producto.id);
      fila.remove();
      actualizar();
      buscador.focus();
    });
    celdaQuitar.appendChild(quitar);

    fila.append(celdaProducto, celdaCantidad, celdaCosto, subtotal, celdaQuitar);
    cuerpo.appendChild(fila);
    items.set(producto.id, { cantidad: inputCantidad, costo: inputCosto, subtotal });
  }

  function agregar(producto) {
    const existente = items.get(producto.id);
    if (existente) {
      existente.cantidad.value = entero(existente.cantidad) + 1;
    } else {
      crearFila(producto, 1, producto.costo || "");
      if (!producto.costo) items.get(producto.id).costo.focus();
    }
    aviso.textContent = "";
    actualizar();
  }

  function cerrarResultados() {
    resultados.hidden = true;
    resultados.replaceChildren();
  }

  function mostrarResultados(productos, texto) {
    resultados.replaceChildren();
    if (!productos.length) {
      cerrarResultados();
      aviso.textContent = `No hay productos que coincidan con "${texto}".`;
      return;
    }
    aviso.textContent = "";
    productos.forEach((producto) => {
      const opcion = document.createElement("li");
      const botonProducto = document.createElement("button");
      botonProducto.type = "button";
      botonProducto.className = "venta-resultado";
      const img = document.createElement("img");
      img.className = "venta-miniatura";
      img.alt = "";
      if (producto.imagen) img.src = producto.imagen;
      const textos = document.createElement("span");
      textos.textContent = producto.nombre;
      const detalle = document.createElement("small");
      detalle.textContent = [producto.categoria, producto.codigo].filter(Boolean).join(" · ");
      textos.appendChild(detalle);
      const costo = document.createElement("span");
      costo.textContent = producto.costo ? `Costo ${pesos(producto.costo)}` : "Sin costo";
      const stock = document.createElement("small");
      stock.textContent = `Stock: ${producto.stock}`;
      costo.appendChild(stock);
      botonProducto.append(img, textos, costo);
      botonProducto.addEventListener("click", () => {
        agregar(producto);
        buscador.value = "";
        cerrarResultados();
      });
      opcion.appendChild(botonProducto);
      resultados.appendChild(opcion);
    });
    resultados.hidden = false;
  }

  let ultimaBusqueda = 0;
  async function buscar(texto) {
    const numero = ++ultimaBusqueda;
    try {
      const respuesta = await fetch(`${urlBuscar}?q=${encodeURIComponent(texto)}`);
      const datos = await respuesta.json();
      return numero === ultimaBusqueda ? datos.productos : null; // descarta respuestas de búsquedas anteriores
    } catch (error) {
      aviso.textContent = "No se pudo buscar. Recarga la página e inténtalo de nuevo.";
      return null;
    }
  }

  let temporizador = null;
  buscador.addEventListener("input", () => {
    clearTimeout(temporizador);
    const texto = buscador.value.trim();
    if (texto.length < 2) {
      cerrarResultados();
      return;
    }
    temporizador = setTimeout(async () => {
      const productos = await buscar(texto);
      if (productos) mostrarResultados(productos, texto);
    }, 250);
  });

  // El lector de código de barras escribe el código y presiona Enter: si hay un solo producto, se agrega.
  buscador.addEventListener("keydown", async (evento) => {
    if (evento.key === "Escape") cerrarResultados();
    if (evento.key !== "Enter") return;
    evento.preventDefault();
    clearTimeout(temporizador);
    const texto = buscador.value.trim();
    if (!texto) return;
    const productos = await buscar(texto);
    if (!productos) return;
    if (productos.length === 1) {
      agregar(productos[0]);
      buscador.value = "";
      cerrarResultados();
    } else {
      mostrarResultados(productos, texto);
    }
  });

  document.addEventListener("click", (evento) => {
    if (!evento.target.closest(".venta-buscador")) cerrarResultados();
  });

  form.proveedor.addEventListener("input", actualizar);
  form.addEventListener("submit", (evento) => {
    if (boton.disabled) {
      evento.preventDefault();
      return;
    }
    boton.disabled = true; // evita registrar dos veces con doble clic
  });

  // si el servidor rechazó la compra, se vuelven a mostrar los productos que se habían agregado
  JSON.parse(document.getElementById("items-ingresados").textContent).forEach((producto) => {
    if (!items.has(producto.id)) crearFila(producto, producto.cantidad, producto.costo);
  });
  actualizar();
});
