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
  // The Excel file is for the month on screen.
  document.getElementById("download-sales").href = `/reports/sales.xlsx?month=${month}`;
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

// card("Capital", "₱81,050.00") -> a small card for the stock tab
const card = (label, value) => {
  const column = document.createElement("div");
  column.className = "col-6";
  const box = document.createElement("div");
  box.className = "card";
  const body = document.createElement("div");
  body.className = "card-body py-2";
  const small = document.createElement("div");
  small.className = "small text-body-secondary";
  small.textContent = label;
  const big = document.createElement("div");
  big.className = "fs-6 fw-semibold";
  big.textContent = value;
  body.append(small, big);
  box.append(body);
  column.append(box);
  return column;
};

// stockRow(item, small) -> a row: the item's name and model, its stock, and a small figure on the right
const stockRow = (item, small) =>
  row([item.name, item.model].filter(Boolean).join(" · "),
    `Stock ${item.stock}${item.reorder_level ? ` · re-order at ${item.reorder_level}` : ""}`,
    `₱${pesos(item.capital)}`, small);

// listOrEmpty(rows, "Nothing here.") -> the rows, or one quiet row when there are none
const listOrEmpty = (rows, text) => (rows.length === 0 ? [emptyRow(text)] : rows);

const loadStock = async () => {
  try {
    const response = await apiFetch("/api/reports/stock");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    hideError("load-error");
    const totals = data.totals;
    document.getElementById("stock-cards").replaceChildren(
      card("Capital in stock", `₱${pesos(totals.capital)}`),
      card("If all sold (revenue)", `₱${pesos(totals.revenue)}`),
      card("Tubo if all sold", `₱${pesos(totals.tubo)}`),
      card("Items / pieces", `${totals.items} / ${totals.pieces}`),
      card("Low stock", String(totals.low_stock)),
      card("Out of stock", String(totals.out_of_stock)),
    );
    document.getElementById("stock-note").textContent =
      "Only items that count stock and are for sale. Capital is the cost of the stock on the shelf (puhunan × stock).";
    document.getElementById("low-count").textContent = `(${totals.low_stock})`;
    document.getElementById("zero-count").textContent = `(${totals.below_zero})`;
    document.getElementById("low-list").replaceChildren(...listOrEmpty(
      data.low_stock.map((item) => stockRow(item, "low")), "Nothing is low."));
    document.getElementById("zero-list").replaceChildren(...listOrEmpty(
      data.below_zero.map((item) => stockRow(item, "below zero")), "Nothing is below zero."));
    document.getElementById("capital-list").replaceChildren(...listOrEmpty(
      data.top_capital.map((item, index) => stockRow(item, `#${index + 1}`)), "No stock yet."));
  } catch {
    showError("load-error", "Could not load the stock report.");
  }
};

loadSales("");
