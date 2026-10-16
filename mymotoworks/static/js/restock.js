// The Restock page (admin): pick the items that arrived, set how many and what each cost, save.

const MAX_FILTER_WORDS = 6;
const MAX_QTY = 100000;

const filterInput = document.getElementById("item-filter");
const lowOnly = document.getElementById("low-only");
const itemListBox = document.getElementById("item-list");
const itemScroll = document.getElementById("item-scroll");
const itemsCount = document.getElementById("items-count");
const itemsStatus = document.getElementById("items-status");
const itemsEmpty = document.getElementById("items-empty");
const tabItems = document.getElementById("tab-items");
const tabCart = document.getElementById("tab-cart");
const panelItems = document.getElementById("panel-items");
const panelCart = document.getElementById("panel-cart");
const cartBox = document.getElementById("cart-lines");
const cartEmpty = document.getElementById("cart-empty");
const totalBox = document.getElementById("cart-total");
const saveButton = document.getElementById("save-restock");
const noteInput = document.getElementById("restock-note");
const dateInput = document.getElementById("restock-date");
const today = document.getElementById("restock-main").dataset.today;

// Only items that count stock can be restocked. Loaded once; the list is filtered here.
let allItems = [];

// Each line: {item, qty, cost}. cost is centavos for one piece (the item's current cost unless changed),
// or null while the box holds something that is not an amount.
let cart = [];

// newRef() -> "3f2c..." A new id for each restock, so a double tap or a retry saves it only once.
// randomUUID needs https, so fall back on plain http (the shop Wi-Fi).
const newRef = () =>
  crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
let restockRef = newRef();

// lineTotal({qty: 10, cost: 11000}) -> 110000. An empty or bad box counts as 0, so the total never shows "NaN".
const lineTotal = (line) => (Number.isInteger(line.qty) && line.cost !== null ? line.qty * line.cost : 0);

const cartTotal = () => cart.reduce((sum, line) => sum + lineTotal(line), 0);

// cartCount() -> 15 (all the pieces; a quantity that is not a number counts as 0)
const cartCount = () => cart.reduce((sum, line) => sum + (Number.isInteger(line.qty) ? line.qty : 0), 0);

// inCart(item) -> 10 (how many of this item are in the restock)
const inCart = (item) => cart.filter((line) => line.item.id === item.id)
  .reduce((sum, line) => sum + (Number.isInteger(line.qty) ? line.qty : 0), 0);

// cartProblem() -> "" when the restock can be saved, or the reason it cannot
const cartProblem = () => {
  if (cart.length === 0) return "Add an item first.";
  if (cart.some((line) => !Number.isInteger(line.qty) || line.qty < 1 || line.qty > MAX_QTY)) {
    return `Every quantity must be from 1 to ${MAX_QTY}.`;
  }
  if (cart.some((line) => line.cost === null)) return "Every cost must be an amount like 120 or 120.50.";
  return "";
};

const updateTotals = () => {
  totalBox.textContent = `₱${pesos(cartTotal())}`;
  tabCart.textContent = cart.length === 0 ? "Restock" : `Restock (${cartCount()}) ₱${pesos(cartTotal())}`;
  saveButton.disabled = cart.length === 0;
  cartEmpty.classList.toggle("d-none", cart.length > 0);
  cart.forEach((line) => {
    line.totalBox.textContent = `₱${pesos(lineTotal(line))}`;
  });
};

// stepperButton("bi-plus-lg", "Add one X", "btn-primary", handler) -> a − or + button
const stepperButton = (icon, label, style, onClick) => {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `btn ${style} bi ${icon}`;
  button.setAttribute("aria-label", label);
  button.addEventListener("click", onClick);
  return button;
};

// addToCart(item) -> adds one of the item, or one more when it is already in the restock
const addToCart = (item) => {
  const same = cart.find((line) => line.item.id === item.id);
  if (same) {
    same.qty = Number.isInteger(same.qty) ? Math.min(same.qty + 1, MAX_QTY) : 1;
  } else {
    cart.push({ item, qty: 1, cost: item.puhunan });
  }
  hideError("restock-error");
  renderCart();
};

// removeOne(item) -> takes one off the item's quantity (the line goes when it reaches 0)
const removeOne = (item) => {
  const line = cart.find((other) => other.item.id === item.id);
  if (!line) return;
  if (Number.isInteger(line.qty) && line.qty > 1) {
    line.qty -= 1;
  } else {
    cart = cart.filter((other) => other !== line);
  }
  renderCart();
};

// cartRow(line) -> one line of the restock: name, quantity, cost of one piece, line total, remove
const cartRow = (line) => {
  const row = document.createElement("div");
  row.className = "border rounded-3 p-2";

  const top = document.createElement("div");
  top.className = "d-flex justify-content-between align-items-start gap-2";
  const name = document.createElement("div");
  name.className = "fw-semibold text-break min-w-0";
  name.textContent = [line.item.name, line.item.model].filter(Boolean).join(" · ");
  const remove = stepperButton("bi-x-lg", `Remove ${line.item.name}`, "btn-outline-secondary", () => {
    cart = cart.filter((other) => other !== line);
    renderCart();
  });
  remove.classList.add("flex-shrink-0");
  top.append(name, remove);

  const controls = document.createElement("div");
  controls.className = "d-flex align-items-center gap-2 mt-2";
  const qtyInput = document.createElement("input");
  qtyInput.type = "text";
  qtyInput.inputMode = "numeric";
  qtyInput.className = "form-control text-center";
  qtyInput.style.maxWidth = "5rem";
  qtyInput.setAttribute("aria-label", `Quantity of ${line.item.name}`);
  qtyInput.value = String(line.qty);
  qtyInput.addEventListener("input", () => {
    const count = toCount(qtyInput.value);
    line.qty = count === null ? NaN : count;
    updateTotals();
  });
  const setQty = (next) => {
    line.qty = Math.min(Math.max(1, next), MAX_QTY);
    qtyInput.value = String(line.qty);
    updateTotals();
  };
  const costGroup = document.createElement("div");
  costGroup.className = "input-group";
  const peso = document.createElement("span");
  peso.className = "input-group-text";
  peso.textContent = "₱";
  const costInput = document.createElement("input");
  costInput.type = "text";
  costInput.inputMode = "decimal";
  costInput.className = "form-control";
  costInput.setAttribute("aria-label", `Cost of one ${line.item.name}`);
  costInput.value = pesos(line.cost).replaceAll(",", "");
  costInput.addEventListener("input", () => {
    line.cost = costInput.value.trim() === "" ? null : toCentavos(costInput.value);
    updateTotals();
  });
  costGroup.append(peso, costInput);
  controls.append(
    stepperButton("bi-dash-lg", "Less", "btn-outline-secondary", () => setQty((Number.isInteger(line.qty) ? line.qty : 1) - 1)),
    qtyInput,
    stepperButton("bi-plus-lg", "More", "btn-outline-secondary", () => setQty((Number.isInteger(line.qty) ? line.qty : 0) + 1)),
    costGroup,
  );

  const bottom = document.createElement("div");
  bottom.className = "d-flex justify-content-between align-items-center mt-2 small";
  const hint = document.createElement("span");
  hint.className = "text-body-secondary";
  hint.textContent = `Cost of one now ₱${pesos(line.item.puhunan)}. Stock ${line.item.stock}.`;
  const total = document.createElement("span");
  total.className = "fw-semibold fs-6";
  bottom.append(hint, total);

  line.totalBox = total;
  row.append(top, controls, bottom);
  return row;
};

const renderCart = () => {
  cartBox.replaceChildren(...cart.map(cartRow));
  updateTotals();
  renderList(); // the items in the restock show their quantity
};

// showTab("cart") -> on a phone, shows the restock instead of the item list ("items" does the reverse).
// From 768px both are always visible (d-md-block).
const showTab = (name) => {
  const cartTab = name === "cart";
  panelItems.classList.toggle("d-none", cartTab);
  panelCart.classList.toggle("d-none", !cartTab);
  tabItems.classList.toggle("active", !cartTab);
  tabCart.classList.toggle("active", cartTab);
  tabItems.setAttribute("aria-selected", String(!cartTab));
  tabCart.setAttribute("aria-selected", String(cartTab));
};
tabItems.addEventListener("click", () => showTab("items"));
tabCart.addEventListener("click", () => showTab("cart"));

// filterWords() -> ["air", "nmax"] from the filter box: every word must be in the item's text
const filterWords = () => filterInput.value.toLowerCase().split(/\s+/).filter(Boolean).slice(0, MAX_FILTER_WORDS);

// matches(item, ["air", "nmax"]) -> true for "AIR FILTER SUNTAL · NMAX V1" (any order, any case)
const matches = (item, words) => {
  const text = `${item.name} ${item.model} ${item.part_no}`.toLowerCase();
  return words.every((word) => text.includes(word));
};

// itemRow(item) -> one row of the list: name, model, part no., cost, stock, and a − 2 + stepper
const itemRow = (item) => {
  const row = document.createElement("div");
  row.className = "item-row list-group-item d-flex align-items-center gap-2 px-3 py-2";

  const info = document.createElement("div");
  info.className = "min-w-0 flex-grow-1";
  const name = document.createElement("div");
  name.className = "fw-semibold text-break";
  name.textContent = [item.name, item.model].filter(Boolean).join(" · ");
  info.append(name);
  const detail = document.createElement("div");
  detail.className = "small text-body-secondary text-break";
  detail.textContent = [item.part_no, `Cost ₱${pesos(item.puhunan)}`].filter(Boolean).join(" · ");
  const stock = document.createElement("span");
  stock.className = item.low_stock ? "text-danger" : "";
  stock.textContent = ` · Stock ${item.stock}${item.low_stock ? " (low)" : ""}`;
  detail.append(stock);
  info.append(detail);

  const count = inCart(item);
  const stepper = document.createElement("div");
  stepper.className = "d-flex align-items-center flex-shrink-0 gap-1";
  const less = stepperButton("bi-dash-lg", `Remove one ${item.name}`, "btn-outline-secondary", () => removeOne(item));
  less.disabled = count === 0;
  const qty = document.createElement("span");
  qty.className = `item-qty fw-semibold text-center ${count > 0 ? "text-primary" : "text-body-secondary"}`;
  qty.style.minWidth = "1.75rem";
  qty.textContent = String(count);
  const more = stepperButton("bi-plus-lg", `Add one ${item.name}`, "btn-primary", () => addToCart(item));
  stepper.append(less, qty, more);

  row.append(info, stepper);
  return row;
};

// renderList() -> draws the items that match the filter box (and the low-stock switch), and says how many
const renderList = () => {
  const words = filterWords();
  const shown = allItems.filter((item) => matches(item, words) && (!lowOnly.checked || item.low_stock));
  itemListBox.replaceChildren(...shown.map(itemRow));
  itemsEmpty.classList.toggle("d-none", shown.length > 0 || allItems.length === 0);
  const filtering = words.length > 0 || lowOnly.checked;
  itemsCount.textContent = allItems.length === 0 ? ""
    : filtering ? `${shown.length} of ${plural(allItems.length, "item")}` : plural(allItems.length, "item");
  return shown;
};

const loadItems = async () => {
  try {
    const response = await apiFetch("/api/items/all");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    hideError("load-error");
    // Only items that count stock can be restocked. The server refuses the others too.
    allItems = data.items.filter((item) => item.track_stock);
    itemsStatus.textContent = allItems.length === 0 ? "No items that count stock yet." : "";
    itemsStatus.classList.toggle("d-none", allItems.length > 0);
    renderList();
  } catch {
    itemsStatus.classList.add("d-none");
    showError("load-error", "Could not load the items. Reload the page to try again.");
  }
};

filterInput.addEventListener("input", () => {
  renderList();
  itemScroll.scrollTop = 0; // a new filter shows its first match, not the middle of the old list
});
lowOnly.addEventListener("change", () => {
  renderList();
  itemScroll.scrollTop = 0;
});
// Enter adds the item when only one is left: quick for a typed code.
filterInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  const shown = renderList();
  if (shown.length === 1) {
    addToCart(shown[0]);
    filterInput.select();
  }
});

saveButton.addEventListener("click", async () => {
  hideError("restock-error");
  const problem = cartProblem();
  if (problem) {
    showError("restock-error", problem);
    return;
  }
  const stopLoading = startLoading(saveButton);
  if (!stopLoading) return;
  try {
    const body = {
      client_ref: restockRef,
      lines: cart.map((line) => ({ item_id: line.item.id, qty: line.qty, puhunan: line.cost })),
    };
    if (dateInput.value) body.restock_date = dateInput.value;
    if (noteInput.value.trim()) body.note = noteInput.value;
    const response = await apiFetch("/api/restocks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("restock-error", data.error || "Could not save the restock.");
      return;
    }
    const message = document.getElementById("restock-message");
    message.textContent = `Restock #${data.restock.id} saved: ${plural(data.restock.lines.length, "item")}, ₱${pesos(data.restock.total)}. The stock and the costs are updated.`;
    message.classList.remove("d-none");
    cart = [];
    restockRef = newRef(); // the next restock is a new one
    noteInput.value = "";
    dateInput.value = today;
    filterInput.value = "";
    lowOnly.checked = false;
    await loadItems(); // the stock and costs shown are the new ones
    renderCart();
    showTab("items");
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch {
    // The reference stays the same, so tapping Save again cannot make a second restock.
    showError("restock-error", "Cannot reach the server. Check your connection and tap Save again.");
  } finally {
    stopLoading();
    updateTotals();
  }
});

updateTotals();
loadItems();
