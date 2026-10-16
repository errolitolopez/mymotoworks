// The Reports page (admin): the sales of a month, and (feature B) the stock value.

const tabSales = document.getElementById("tab-sales");
const tabStock = document.getElementById("tab-stock");
const panelSales = document.getElementById("panel-sales");
const panelStock = document.getElementById("panel-stock");

const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
  "October", "November", "December"];

// The month on screen, as "2026-10". Starts empty: the server answers with this month.
let month = "";
let thisMonth = "";

// monthLabel("2026-10") -> "October 2026"
const monthLabel = (text) => `${MONTH_NAMES[Number(text.slice(5)) - 1]} ${text.slice(0, 4)}`;

// shiftMonth("2026-01", -1) -> "2025-12"
const shiftMonth = (text, step) => {
  const index = Number(text.slice(0, 4)) * 12 + (Number(text.slice(5)) - 1) + step;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`;
};

// row("Oct 16", "5 sales · 12 pieces", "₱1,200.00", "tubo ₱300.00") -> one list row: what, details, amount, small amount
const row = (title, details, amount, small) => {
  const element = document.createElement("div");
  element.className = "list-group-item d-flex justify-content-between align-items-start gap-2";
  const left = document.createElement("div");
  left.className = "min-w-0";
  const name = document.createElement("div");
  name.className = "fw-semibold text-break";
  name.textContent = title;
  const info = document.createElement("div");
  info.className = "small text-body-secondary text-break";
  info.textContent = details;
  left.append(name, info);
  const right = document.createElement("div");
  right.className = "text-end flex-shrink-0";
  const main = document.createElement("div");
  main.className = "fw-semibold";
  main.textContent = amount;
  const sub = document.createElement("div");
  sub.className = "small text-body-secondary";
  sub.textContent = small;
  right.append(main, sub);
  element.append(left, right);
  return element;
};

// emptyRow("Nothing sold yet.") -> a quiet row for a list with nothing in it
const emptyRow = (text) => {
  const element = document.createElement("div");
  element.className = "list-group-item text-body-secondary";
  element.textContent = text;
  return element;
};

const showSales = (data) => {
  month = data.month;
  document.getElementById("month-label").textContent = monthLabel(month);
  document.getElementById("next-month").disabled = thisMonth !== "" && month >= thisMonth;
  const totals = data.totals;
  document.getElementById("sum-total").textContent = `₱${pesos(totals.total)}`;
  document.getElementById("sum-tubo").textContent = `₱${pesos(totals.tubo)}`;
  document.getElementById("sum-cost").textContent = `₱${pesos(totals.cost)}`;
  document.getElementById("sum-restocked").textContent = `₱${pesos(data.restocked)}`;
  document.getElementById("sum-count").textContent =
    `${plural(totals.sales, "sale")}, ${plural(totals.pieces, "piece")} sold in ${plural(data.days.length, "day")}.`;
  document.getElementById("day-list").replaceChildren(...data.days.map((day) =>
    row(formatDay(day.date), `${plural(day.sales, "sale")} · ${plural(day.pieces, "piece")}`,
      `₱${pesos(day.total)}`, `tubo ₱${pesos(day.tubo)}`)));
  document.getElementById("day-empty").classList.toggle("d-none", data.days.length > 0);
  document.getElementById("best-list").replaceChildren(...(data.best_sellers.length === 0
    ? [emptyRow("Nothing sold this month.")]
    : data.best_sellers.map((item, index) =>
      row(`${index + 1}. ${item.name}`, plural(item.pieces, "piece"), `₱${pesos(item.total)}`, `tubo ₱${pesos(item.tubo)}`))));
};

const showYear = (data) => {
  document.getElementById("year-title").textContent = `The year ${data.year}, month by month`;
  document.getElementById("year-list").replaceChildren(...(data.months.length === 0
    ? [emptyRow("No sales this year.")]
    : data.months.map((entry) =>
      row(monthLabel(entry.month), `${plural(entry.sales, "sale")}`, `₱${pesos(entry.total)}`, `tubo ₱${pesos(entry.tubo)}`))));
};

// loadSales("2026-09") -> loads that month (empty = this month) and the year it belongs to
const loadSales = async (wanted) => {
  try {
    const response = await apiFetch(`/api/reports/sales?month=${encodeURIComponent(wanted)}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    if (thisMonth === "") thisMonth = data.month; // the first answer is this month
    hideError("load-error");
    showSales(data);
    const yearResponse = await apiFetch(`/api/reports/months?year=${data.month.slice(0, 4)}`);
    if (!yearResponse) return;
    const yearData = await yearResponse.json();
    if (yearResponse.ok) showYear(yearData);
  } catch {
    showError("load-error", "Could not load the report.");
  }
};

document.getElementById("prev-month").addEventListener("click", () => loadSales(shiftMonth(month, -1)));
document.getElementById("next-month").addEventListener("click", () => loadSales(shiftMonth(month, 1)));
document.getElementById("this-month").addEventListener("click", () => loadSales(thisMonth));

// showTab("stock") -> shows the stock report instead of the sales report
const showTab = (name) => {
  const stock = name === "stock";
  panelSales.classList.toggle("d-none", stock);
  panelStock.classList.toggle("d-none", !stock);
  tabSales.classList.toggle("active", !stock);
  tabStock.classList.toggle("active", stock);
  tabSales.setAttribute("aria-selected", String(!stock));
  tabStock.setAttribute("aria-selected", String(stock));
  if (stock && typeof loadStock === "function") loadStock();
};
tabSales.addEventListener("click", () => showTab("sales"));
tabStock.addEventListener("click", () => showTab("stock"));

loadSales("");
