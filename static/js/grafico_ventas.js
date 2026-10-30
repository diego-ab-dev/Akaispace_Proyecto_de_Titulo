// Panel > Dashboard y Reportes (HU-10): gráfico de ventas por canal (columnas apiladas, Chart.js).
// Uso: <canvas data-grafico-ventas="id-del-json"></canvas>, donde el json_script trae
// {etiquetas: [...], series: [{clave, nombre, datos: [...]}], totales: [...]}.
(function () {
  const COLORES = { web: "#2a78d6", tienda: "#eb6834", whatsapp: "#1baf7a" };
  const TINTA = "#4f5866";
  const TENUE = "#7a828c";
  const GRILLA = "#eef1f4";
  const EJE = "#d5dbe1";

  const pesos = (monto) => "$" + Math.round(monto).toLocaleString("es-CL");

  function compacto(monto) {
    if (monto >= 1000000) return "$" + (monto / 1000000).toLocaleString("es-CL", { maximumFractionDigits: 1 }) + " M";
    if (monto >= 1000) return "$" + (monto / 1000).toLocaleString("es-CL", { maximumFractionDigits: 0 }) + " mil";
    return pesos(monto);
  }

  // Solo el segmento de arriba de cada columna lleva las esquinas redondeadas; la base queda recta.
  function esElDeArriba(contexto) {
    const datasets = contexto.chart.data.datasets;
    for (let i = contexto.datasetIndex + 1; i < datasets.length; i++) {
      if (contexto.chart.isDatasetVisible(i) && datasets[i].data[contexto.dataIndex] > 0) return false;
    }
    return true;
  }

  function crear(canvas) {
    const datos = JSON.parse(document.getElementById(canvas.dataset.graficoVentas).textContent);
    const muchas = datos.etiquetas.length > 16;

    new Chart(canvas, {
      type: "bar",
      data: {
        labels: datos.etiquetas,
        datasets: datos.series.map((serie) => ({
          label: serie.nombre,
          data: serie.datos,
          backgroundColor: COLORES[serie.clave],
          hoverBackgroundColor: COLORES[serie.clave],
          // 2px del color de la superficie separan los segmentos apilados
          borderColor: "#ffffff",
          borderWidth: { top: 2, right: 0, bottom: 0, left: 0 },
          borderSkipped: false,
          borderRadius: (contexto) => (esElDeArriba(contexto) ? { topLeft: 4, topRight: 4 } : 0),
          maxBarThickness: 24,
          categoryPercentage: 0.7,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 250 },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false }, // la leyenda va en HTML, sobre el gráfico
          tooltip: {
            backgroundColor: "#1c253b",
            padding: 10,
            cornerRadius: 6,
            boxWidth: 10,
            boxHeight: 10,
            boxPadding: 4,
            titleFont: { weight: "700" },
            footerFont: { weight: "700" },
            filter: (item) => item.raw > 0,
            callbacks: {
              label: (item) => ` ${item.dataset.label}: ${pesos(item.raw)}`,
              footer: (items) => (items.length ? `Total: ${pesos(datos.totales[items[0].dataIndex])}` : ""),
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            grid: { display: false },
            border: { color: EJE },
            ticks: { color: TENUE, maxRotation: 0, autoSkip: true, maxTicksLimit: muchas ? 10 : 16 },
          },
          y: {
            stacked: true,
            beginAtZero: true,
            grid: { color: GRILLA },
            border: { display: false },
            ticks: { color: TENUE, maxTicksLimit: 6, callback: (valor) => compacto(valor) },
          },
        },
      },
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (typeof Chart === "undefined") return;
    Chart.defaults.font.family = "'Nunito', system-ui, -apple-system, 'Segoe UI', sans-serif";
    Chart.defaults.color = TINTA;
    document.querySelectorAll("canvas[data-grafico-ventas]").forEach(crear);
  });
})();
