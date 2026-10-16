// The Home page: the sales bar chart (admin only), drawn with Chart.js. It shows the months of a
// year; tapping a month shows its days.

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const backButton = document.getElementById("chart-back");
let shownYear = new Date().getFullYear();
let shownMonth = null; // 1-12 while the days of a month are shown, null for the year view
let chart = null;
let lastData = null; // the last answer from the server, so the metric can change without a new request
let lastView = null; // what was drawn last, so a theme change can draw it again

const METRIC_NAMES = { total: "Sales", cost: "Cost", tubo: "Tubo" };

// chosenMetric() -> "total", "cost" or "tubo": what the radio buttons say the chart shows
const chosenMetric = () => document.querySelector("input[name=chart-metric]:checked").value;

// monthTotals([{month: "2026-03", total: 5000}], "total") -> [0, 0, 5000, 0, 0, 0, 0, 0, 0, 0, 0, 0]
// Months without sales are 0, so the chart always has 12 bars.
const monthTotals = (months, metric) => {
  const totals = new Array(12).fill(0);
  months.forEach((entry) => (totals[Number(entry.month.slice(5)) - 1] = entry[metric]));
  return totals;
};

// dayTotals([{date: "2026-09-02", total: 5000}], 2026, 9, "total") -> 30 numbers, [0, 5000, 0, ...]
// Days without sales are 0, so the chart has one bar for every day of the month.
const dayTotals = (days, year, month, metric) => {
  const totals = new Array(new Date(year, month, 0).getDate()).fill(0);
  days.forEach((entry) => (totals[Number(entry.date.slice(8)) - 1] = entry[metric]));
  return totals;
};

// compactPesos(1234500) -> "12.3k", compactPesos(250000) -> "2.5k", compactPesos(9950) -> "100"
// Short enough for the axis and the bar labels on a phone. The tooltip has the full amount.
const compactPesos = (centavos) => {
  const value = centavos / 100;
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return Math.round(value).toString();
};

// cssColor("--bs-primary") -> "#0d6efd". Chart.js draws on a canvas, so it cannot read CSS itself;
// reading the Bootstrap variable keeps the chart in the light or dark theme.
const cssColor = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// A small plugin that writes each bar's value above it (Chart.js has no such thing built in).
const valueLabels = {
  id: "valueLabels",
  afterDatasetsDraw(instance) {
    const { ctx } = instance;
    ctx.save();
    ctx.fillStyle = cssColor("--bs-secondary-color");
    ctx.font = "11px sans-serif";
    ctx.textAlign = "center";
    instance.getDatasetMeta(0).data.forEach((bar, index) => {
      const total = instance.data.datasets[0].data[index];
      if (total > 0) ctx.fillText(compactPesos(total), bar.x, bar.y - 4);
    });
    ctx.restore();
  },
};

// drawChart({labels, totals, titles, onBarClick, showValues}) -> draws one bar per total. Day bars are
// too narrow for value labels, so the days show them in the tooltip (tap or hover) only.
const drawChart = (view) => {
  lastView = view;
  if (chart) chart.destroy();
  const textColor = cssColor("--bs-secondary-color");
  chart = new Chart(document.getElementById("chart"), {
    type: "bar",
    data: {
      labels: view.labels,
      datasets: [{ data: view.totals, backgroundColor: cssColor("--bs-primary"), borderRadius: 4 }],
    },
    options: {
      maintainAspectRatio: false,
      // Room above the tallest bar for its label.
      layout: { padding: { top: 18 } },
      onClick: (event, elements) => {
        if (view.onBarClick && elements.length > 0) view.onBarClick(elements[0].index);
      },
      onHover: (event, elements) => {
        event.native.target.style.cursor = view.onBarClick && elements.length > 0 ? "pointer" : "default";
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { title: (items) => view.titles[items[0].dataIndex], label: (item) => `₱${pesos(item.raw)}` } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: textColor, maxRotation: 0, autoSkip: true } },
        y: { beginAtZero: true, grid: { color: cssColor("--bs-border-color") },
             ticks: { color: textColor, maxTicksLimit: 5, callback: (value) => compactPesos(value) } },
      },
    },
    plugins: view.showValues ? [valueLabels] : [],
  });
};

// showSummary(rows, text) -> the sales, cost and tubo of the period on the three buttons above the chart
const showSummary = (rows, text) => {
  const sums = { total: 0, cost: 0, tubo: 0 };
  rows.forEach((row) => Object.keys(sums).forEach((key) => (sums[key] += row[key])));
  Object.keys(sums).forEach((key) => (document.getElementById(`sum-${key}`).textContent = `₱${pesos(sums[key])}`));
  document.getElementById("chart-sub").textContent = sums.total > 0 ? text : "No sales in this period.";
};

// showYearView(data) -> bars for the 12 months; tapping one opens its days
const showYearView = (data) => {
  const metric = chosenMetric();
  const totals = monthTotals(data.months, metric);
  showSummary(data.months, `${METRIC_NAMES[metric]} in ${data.year}. Tap a bar to see its days.`);
  drawChart({
    labels: MONTH_NAMES,
    totals,
    titles: MONTH_NAMES.map((name) => `${name} ${data.year}`),
    onBarClick: (index) => { shownMonth = index + 1; loadChart(); },
    showValues: true,
  });
};

// showMonthView(data) -> bars for each day of the month
const showMonthView = (data) => {
  const [year, month] = data.month.split("-").map(Number);
  const metric = chosenMetric();
  const totals = dayTotals(data.days, year, month, metric);
  showSummary(data.days, `${METRIC_NAMES[metric]} in ${MONTH_NAMES[month - 1]} ${year}. Tap a bar for its day.`);
  drawChart({
    labels: totals.map((_, index) => String(index + 1)),
    totals,
    titles: totals.map((_, index) => `${MONTH_NAMES[month - 1]} ${index + 1}, ${year}`),
    onBarClick: null,
    showValues: false,
  });
};

// showData() -> draws lastData for the chosen metric
const showData = () => (shownMonth === null ? showYearView(lastData) : showMonthView(lastData));

// loadChart() -> loads what is shown (a year, or one month) and draws it
const loadChart = async () => {
  const monthView = shownMonth !== null;
  document.getElementById("year-label").textContent = monthView ? `${MONTH_NAMES[shownMonth - 1]} ${shownYear}` : shownYear;
  document.getElementById("chart-title").textContent = monthView ? " Sales per day" : " Sales per month";
  backButton.classList.toggle("d-none", !monthView);
  hideError("chart-error");
  try {
    const url = monthView
      ? `/api/reports/sales?month=${shownYear}-${String(shownMonth).padStart(2, "0")}`
      : `/api/reports/months?year=${shownYear}`;
    const response = await apiFetch(url);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    lastData = data;
    showData();
  } catch (error) {
    showError("chart-error", error.message || "Could not load the chart.");
  }
};

// step(-1) -> the previous year (or month, in the month view); step(1) -> the next one
const step = (direction) => {
  if (shownMonth === null) {
    shownYear += direction;
  } else {
    // Month 13 is January of the next year, month 0 is December of the last: Date does the carry.
    const moved = new Date(shownYear, shownMonth - 1 + direction, 1);
    shownYear = moved.getFullYear();
    shownMonth = moved.getMonth() + 1;
  }
  loadChart();
};

document.getElementById("year-prev").addEventListener("click", () => step(-1));
document.getElementById("year-next").addEventListener("click", () => step(1));
document.querySelectorAll("input[name=chart-metric]").forEach((radio) =>
  radio.addEventListener("change", () => { if (lastData) showData(); }));
backButton.addEventListener("click", () => { shownMonth = null; loadChart(); });

// The theme button changes data-bs-theme; draw again so the chart colors follow.
new MutationObserver(() => { if (lastView) drawChart(lastView); })
  .observe(document.documentElement, { attributes: true, attributeFilter: ["data-bs-theme"] });

if (typeof Chart === "undefined") {
  showError("chart-error", "The chart could not load. Check your internet connection.");
} else {
  loadChart();
}
