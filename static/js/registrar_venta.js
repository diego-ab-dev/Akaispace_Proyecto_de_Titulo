// Panel > Registrar venta (HU-12): buscar productos por nombre o código de barras y armar la venta.
// El servidor vuelve a validar todo (stock, cantidades, medio de pago) al confirmar.
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("form-venta");
  const buscador = document.getElementById("buscar-producto");
  const resultados = document.getElementById("resultados-busqueda");
  const aviso = document.getElementById("aviso-busqueda");
  const cuerpo = document.getElementById("items-venta");
  const vacio = document.getElementById("venta-vacia");
  const botonConfirmar = document.getElementById("btn-confirmar");
  const botonRegistrar = document.getElementById("btn-registrar");
  const faltaMedioPago = document.getElementById("falta-medio-pago");
  const bloqueEfectivo = document.getElementById("bloque-efectivo");
  const recibido = document.getElementById("monto-recibido");
  const vuelto = document.getElementById("vuelto");
  const modal = new bootstrap.Modal(document.getElementById("confirmarVentaModal"));
  const urlBuscar = form.dataset.urlBuscar;

  const items = new Map(); // id del producto -> { producto, input, subtotal, alerta }
  let confirmada = false;

  const pesos = (monto) => "$" + monto.toLocaleString("es-CL");
  const cantidadDe = (item) => parseInt(item.input.value, 10) || 0;
  const elegido = (nombre) => form.querySelector(`input[name="${nombre}"]:checked`);

  function total() {
    let suma = 0;
    items.forEach((item) => { suma += item.producto.precio * cantidadDe(item); });
    return suma;
  }

  function avisar(mensaje) {
    aviso.textContent = mensaje;
  }

  function actualizar() {
    let valida = items.size > 0;
    items.forEach((item) => {
      const cantidad = cantidadDe(item);
      let mensaje = "";
      if (cantidad < 1) mensaje = "Mínimo 1";
      else if (cantidad > item.producto.stock) mensaje = `Solo hay ${item.producto.stock}`;
      item.alerta.textContent = mensaje;
      item.input.classList.toggle("is-invalid", Boolean(mensaje));
      item.subtotal.textContent = pesos(item.producto.precio * cantidad);
      if (mensaje) valida = false;
    });
    vacio.hidden = items.size > 0;
    document.querySelectorAll("[data-total]").forEach((el) => { el.textContent = pesos(total()); });
    botonConfirmar.disabled = !valida;
    calcularVuelto();
  }

  function calcularVuelto() {
    const efectivo = elegido("metodo_pago")?.value === "efectivo";
    bloqueEfectivo.hidden = !efectivo;
    const monto = parseInt(recibido.value, 10);
    if (!efectivo || Number.isNaN(monto)) {
      vuelto.textContent = "Solo para calcular el vuelto; no se guarda.";
    } else if (monto >= total()) {
      vuelto.textContent = `Vuelto: ${pesos(monto - total())}`;
    } else {
      vuelto.textContent = `Faltan ${pesos(total() - monto)}`;
    }
  }

  function miniatura(producto) {
    const img = document.createElement("img");
    img.className = "venta-miniatura";
    img.alt = "";
    if (producto.imagen) img.src = producto.imagen;
    return img;
  }

  function crearFila(producto, cantidad) {
    const fila = document.createElement("tr");

    const celdaProducto = document.createElement("td");
    const info = document.createElement("div");
    info.className = "venta-item__producto";
    const textos = document.createElement("div");
    textos.textContent = producto.nombre;
    const detalle = document.createElement("small");
    detalle.textContent = [producto.codigo, `Stock: ${producto.stock}`].filter(Boolean).join(" · ");
    textos.appendChild(detalle);
    const oculto = document.createElement("input");
    oculto.type = "hidden";
    oculto.name = "producto";
    oculto.value = producto.id;
    info.append(miniatura(producto), textos, oculto);
    celdaProducto.appendChild(info);

    const celdaPrecio = document.createElement("td");
    celdaPrecio.textContent = pesos(producto.precio);

    const celdaCantidad = document.createElement("td");
    const input = document.createElement("input");
    input.type = "number";
    input.name = "cantidad";
    input.min = 1;
    input.max = producto.stock;
    input.step = 1;
    input.value = cantidad;
    input.className = "form-control form-control-sm venta-item__cantidad";
    input.setAttribute("aria-label", `Cantidad de ${producto.nombre}`);
    input.addEventListener("input", actualizar);
    const alerta = document.createElement("span");
    alerta.className = "venta-item__alerta";
    celdaCantidad.append(input, alerta);

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

    fila.append(celdaProducto, celdaPrecio, celdaCantidad, subtotal, celdaQuitar);
    cuerpo.appendChild(fila);
    items.set(producto.id, { producto, input, subtotal, alerta });
  }

  function agregar(producto) {
    if (producto.stock < 1) {
      avisar(`${producto.nombre} no tiene stock.`);
      return;
    }
    const existente = items.get(producto.id);
    if (existente) {
      existente.producto.stock = producto.stock;
      const cantidad = cantidadDe(existente) + 1;
      if (cantidad > producto.stock) {
        avisar(`Solo hay ${producto.stock} unidad(es) de ${producto.nombre}.`);
        return;
      }
      existente.input.value = cantidad;
    } else {
      crearFila(producto, 1);
    }
    avisar("");
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
      avisar(`No hay productos que coincidan con "${texto}".`);
      return;
    }
    avisar("");
    productos.forEach((producto) => {
      const opcion = document.createElement("li");
      const boton = document.createElement("button");
      boton.type = "button";
      boton.className = "venta-resultado";
      boton.disabled = producto.stock < 1;

      const textos = document.createElement("span");
      textos.textContent = producto.nombre;
      const detalle = document.createElement("small");
      detalle.textContent = [producto.categoria, producto.codigo].filter(Boolean).join(" · ");
      textos.appendChild(detalle);

      const precio = document.createElement("span");
      precio.textContent = pesos(producto.precio);
      const stock = document.createElement("small");
      stock.textContent = producto.stock < 1 ? "Sin stock" : `Stock: ${producto.stock}`;
      precio.appendChild(stock);

      boton.append(miniatura(producto), textos, precio);
      boton.addEventListener("click", () => {
        agregar(producto);
        buscador.value = "";
        cerrarResultados();
        buscador.focus();
      });
      opcion.appendChild(boton);
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
      avisar("No se pudo buscar. Recarga la página e inténtalo de nuevo.");
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

  form.querySelectorAll('input[name="metodo_pago"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      faltaMedioPago.hidden = true;
      calcularVuelto();
    });
  });
  recibido.addEventListener("input", calcularVuelto);

  // Antes de registrar se muestra un resumen; Enter en una cantidad tampoco envía sin confirmar.
  form.addEventListener("submit", (evento) => {
    if (confirmada) return;
    evento.preventDefault();
    if (botonConfirmar.disabled) return;
    const pago = elegido("metodo_pago");
    if (!pago) {
      faltaMedioPago.hidden = false;
      return;
    }
    let unidades = 0;
    items.forEach((item) => { unidades += cantidadDe(item); });
    document.getElementById("resumen-canal").textContent = elegido("canal").parentElement.textContent.trim();
    document.getElementById("resumen-pago").textContent = pago.parentElement.textContent.trim();
    document.getElementById("resumen-unidades").textContent = unidades;
    modal.show();
  });

  botonRegistrar.addEventListener("click", () => {
    confirmada = true;
    botonRegistrar.disabled = true;
    form.submit();
  });

  // si el servidor rechazó la venta, se vuelven a mostrar los productos que se habían agregado
  JSON.parse(document.getElementById("items-ingresados").textContent).forEach((producto) => {
    if (!items.has(producto.id)) crearFila(producto, producto.cantidad);
  });
  actualizar();
});
