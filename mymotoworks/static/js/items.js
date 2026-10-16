// The Items page: everyone can search and look, the admin adds and changes items.

const isAdmin = document.getElementById("items-main").dataset.admin === "true";

const listBox = document.getElementById("item-list");
const emptyState = document.getElementById("empty-state");

// badge("Low stock", "text-bg-warning") -> <span class="badge text-bg-warning">Low stock</span>
const badge = (text, style) => {
  const element = document.createElement("span");
  element.className = `badge ${style}`;
  element.textContent = text;
  return element;
};

// textLine("MIOi125 M3 · YA040A") -> a small gray line of text
const textLine = (text) => {
  const line = document.createElement("div");
  line.className = "small text-body-secondary";
  line.textContent = text;
  return line;
};

// itemRow({name, model, part_no, benta, stock, ...}) -> one list row
const itemRow = (item) => {
  const row = document.createElement("div");
  row.className = "list-group-item d-flex flex-wrap justify-content-between align-items-center gap-2";

  const info = document.createElement("div");
  const name = document.createElement("div");
  name.className = "fw-semibold";
  name.textContent = item.name;
  info.append(name);
  const where = [item.model, item.part_no].filter(Boolean).join(" · ");
  if (where) info.append(textLine(where));
  // Cost and profit only exist in the data for the admin.
  if (isAdmin) info.append(textLine(`Puhunan ₱${pesos(item.puhunan)} · Tubo ₱${pesos(item.tubo)}`));

  const numbers = document.createElement("div");
  numbers.className = "text-end";
  const price = document.createElement("div");
  price.className = "fw-semibold";
  price.textContent = `₱${pesos(item.benta)}`;
  const stock = document.createElement("div");
  stock.className = "small d-flex justify-content-end align-items-center gap-2";
  if (item.track_stock) {
    const count = document.createElement("span");
    count.textContent = `Stock ${item.stock}`;
    stock.append(count);
    if (item.low_stock) stock.append(badge("Low stock", "text-bg-warning"));
  } else {
    stock.append(badge("No stock count", "text-bg-secondary"));
  }
  numbers.append(price, stock);

  row.append(info, numbers);
  return row;
};

const SEARCH_DELAY_MS = 300;

const searchInput = document.getElementById("search");
const lowOnly = document.getElementById("low-only");
const pager = document.getElementById("pager");
const pageLabel = document.getElementById("page-label");
const prevButton = document.getElementById("prev-button");
const nextButton = document.getElementById("next-button");

let page = 1;
let pages = 1;

// itemsUrl() -> "/api/items?q=air+nmax&low=1&page=2" (from the search box, the switch and the page)
const itemsUrl = () => {
  const params = new URLSearchParams({ page });
  if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
  if (lowOnly.checked) params.set("low", "1");
  return `/api/items?${params}`;
};

const loadItems = async () => {
  try {
    const response = await apiFetch(itemsUrl());
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    hideError("load-error");
    page = data.page;
    pages = data.pages;
    listBox.replaceChildren(...data.items.map(itemRow));
    emptyState.classList.toggle("d-none", data.items.length > 0);
    pager.classList.toggle("d-none", pages < 2);
    pageLabel.textContent = `Page ${page} of ${pages} · ${plural(data.total, "item")}`;
    prevButton.disabled = page <= 1;
    nextButton.disabled = page >= pages;
  } catch {
    showError("load-error", "Could not load the items.");
  }
};

// Searching or switching the filter starts again from page 1.
const reloadFromStart = () => {
  page = 1;
  loadItems();
};

let searchTimer = null;
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(reloadFromStart, SEARCH_DELAY_MS);
});
lowOnly.addEventListener("change", reloadFromStart);
prevButton.addEventListener("click", () => {
  page -= 1;
  loadItems();
});
nextButton.addEventListener("click", () => {
  page += 1;
  loadItems();
});

if (isAdmin) {
  const itemForm = document.getElementById("item-form");
  const nameInput = document.getElementById("item-name");
  const modelInput = document.getElementById("item-model");
  const partNoInput = document.getElementById("item-part-no");
  const puhunanInput = document.getElementById("item-puhunan");
  const bentaInput = document.getElementById("item-benta");
  const trackInput = document.getElementById("item-track-stock");
  const stockInput = document.getElementById("item-stock");
  const reorderInput = document.getElementById("item-reorder");
  const saveButton = document.getElementById("save-button");
  const itemModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("item-modal"));

  // The stock boxes only make sense for items whose stock is counted.
  const showStockFields = () => {
    document.getElementById("stock-group").classList.toggle("d-none", !trackInput.checked);
  };
  trackInput.addEventListener("change", showStockFields);

  const openForm = () => {
    document.getElementById("item-modal-title").textContent = "Add item";
    [nameInput, modelInput, partNoInput, puhunanInput, bentaInput, stockInput, reorderInput]
      .forEach((input) => (input.value = ""));
    trackInput.checked = true;
    showStockFields();
    hideError("form-error");
    itemModal.show();
  };

  // Turns what was typed into the JSON the API wants, or returns {error} for the first bad box.
  const readForm = () => {
    const puhunan = toCentavos(puhunanInput.value);
    const benta = toCentavos(bentaInput.value);
    const stock = toCount(stockInput.value);
    const reorder = toCount(reorderInput.value);
    if (!nameInput.value.trim()) return { error: "Item name is required." };
    if (puhunan === null) return { error: "Puhunan must be an amount like 103.50." };
    if (benta === null || bentaInput.value.trim() === "") return { error: "Benta must be an amount like 150 or 150.50." };
    if (stock === null) return { error: "Stock must be a whole number." };
    if (reorder === null) return { error: "Re-order must be a whole number." };
    return {
      body: {
        name: nameInput.value, model: modelInput.value, part_no: partNoInput.value,
        puhunan, benta, stock, reorder_level: reorder, track_stock: trackInput.checked,
      },
    };
  };

  itemForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideError("form-error");
    const form = readForm();
    if (form.error) {
      showError("form-error", form.error);
      return;
    }
    const stopLoading = startLoading(saveButton);
    if (!stopLoading) return;
    try {
      const response = await apiFetch("/api/items", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form.body),
      });
      if (!response) return;
      const data = await response.json();
      if (!response.ok) {
        showError("form-error", data.error || "Could not save the item.");
        return;
      }
      itemModal.hide();
      loadItems();
    } catch {
      showError("form-error", "Cannot reach the server. Check your connection.");
    } finally {
      stopLoading();
    }
  });

  document.getElementById("add-button").addEventListener("click", openForm);
}

loadItems();
