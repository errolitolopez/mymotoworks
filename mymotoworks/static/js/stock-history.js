// The Stock changes page (admin): every adjustment and recount, newest first, for all items or one.

const listBox = document.getElementById("adjustment-list");
const emptyState = document.getElementById("empty-state");
const pager = document.getElementById("pager");
const pageLabel = document.getElementById("page-label");
const prevButton = document.getElementById("prev-button");
const nextButton = document.getElementById("next-button");

// The Items page links here with one item to look at: /stock-history?item=12
const itemId = new URLSearchParams(window.location.search).get("item");
const itemFilter = itemId && /^\d+$/.test(itemId) ? `&item=${itemId}` : "";

let page = 1;

// signed(-2) -> "−2", signed(3) -> "+3"
const signed = (change) => (change < 0 ? `−${Math.abs(change)}` : `+${change}`);

// historyRow(change) -> "AIR FILTER · −2 · Stock 5 → 3", why, note, who and when
const historyRow = (change) => {
  const row = document.createElement("div");
  row.className = "list-group-item";

  const top = document.createElement("div");
  top.className = "d-flex justify-content-between align-items-start gap-2";
  const name = document.createElement("div");
  name.className = "fw-semibold text-break min-w-0";
  name.textContent = change.name;
  const amount = document.createElement("span");
  amount.className = `badge flex-shrink-0 ${change.change < 0 ? "text-bg-danger" : "text-bg-success"}`;
  amount.textContent = signed(change.change);
  top.append(name, amount);

  const stock = document.createElement("div");
  stock.className = "small";
  stock.textContent = `Stock ${change.stock_before} → ${change.stock_after}`;

  const why = document.createElement("div");
  why.className = "small text-body-secondary text-break";
  const kind = change.kind === "recount" ? "Recount" : change.reason_label;
  why.textContent = [kind, change.note].filter(Boolean).join(" · ");

  const who = document.createElement("div");
  who.className = "small text-body-secondary";
  who.textContent = `${change.recorded_by} · ${change.recorded_at}`;

  row.append(top, stock, why, who);
  return row;
};

const loadPage = async () => {
  try {
    const response = await apiFetch(`/api/stock-adjustments?page=${page}${itemFilter}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    hideError("load-error");
    page = data.page;
    if (data.item) {
      document.getElementById("item-banner-text").textContent = `Only ${data.item.name}. Stock now: ${data.item.stock}.`;
      document.getElementById("item-banner").classList.remove("d-none");
    }
    listBox.replaceChildren(...data.adjustments.map(historyRow));
    emptyState.classList.toggle("d-none", data.total > 0);
    pager.classList.toggle("d-none", data.pages < 2);
    pageLabel.textContent = `Page ${data.page} of ${data.pages} · ${plural(data.total, "change")}`;
    prevButton.disabled = data.page <= 1;
    nextButton.disabled = data.page >= data.pages;
  } catch {
    showError("load-error", "Could not load the stock changes.");
  }
};

prevButton.addEventListener("click", () => {
  page -= 1;
  loadPage();
});
nextButton.addEventListener("click", () => {
  page += 1;
  loadPage();
});

loadPage();
