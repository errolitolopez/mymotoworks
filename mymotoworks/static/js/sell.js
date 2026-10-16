// The Sell page: search items, build a cart, save the sale.

const SEARCH_DELAY_MS = 300;
const RESULT_LIMIT = 8;

const searchInput = document.getElementById("item-search");
const resultsBox = document.getElementById("results");
const resultsEmpty = document.getElementById("results-empty");
const resultsHint = document.getElementById("results-hint");
const cartBox = document.getElementById("cart-lines");
const cartEmpty = document.getElementById("cart-empty");
const totalBox = document.getElementById("cart-total");
const saveButton = document.getElementById("save-sale");
const dateInput = document.getElementById("sale-date"); // only the admin has it
const noteInput = document.getElementById("sale-note");

// Each line: {item, qty, price} where price is centavos (the item's own price unless changed).
let cart = [];

// newRef() -> "3f2c..." A new id for each cart. Sent with the sale, so a double tap or a retry
// after a bad connection saves the sale only once. randomUUID needs https, so fall back on
// plain http (the shop Wi-Fi).
const newRef = () =>
  crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
let saleRef = newRef();

// lineTotal({qty: 2, price: 15000}) -> 30000. A box that is empty or not a number counts as 0,
// so the total never shows "NaN" while someone is typing.
const lineTotal = (line) => (Number.isInteger(line.qty) && line.price !== null ? line.qty * line.price : 0);

const cartTotal = () => cart.reduce((sum, line) => sum + lineTotal(line), 0);

// stockWarning({item: {track_stock: true, stock: 2}, qty: 3}) -> "Only 2 in stock. ..." ("" when fine)
const stockWarning = (line) =>
  line.item.track_stock && line.qty > line.item.stock
    ? `Only ${Math.max(line.item.stock, 0)} in stock. You can still sell it.`
    : "";

// cartProblem() -> "" when the cart can be saved, or the reason it cannot
const cartProblem = () => {
  if (cart.length === 0) return "Add an item first.";
  if (cart.some((line) => !Number.isInteger(line.qty) || line.qty < 1)) return "Every quantity must be 1 or more.";
  if (cart.some((line) => line.price === null)) return "Every price must be an amount like 150 or 150.50.";
  return "";
};

const updateTotals = () => {
  totalBox.textContent = `₱${pesos(cartTotal())}`;
  saveButton.disabled = cart.length === 0;
  cartEmpty.classList.toggle("d-none", cart.length > 0);
  cart.forEach((line) => {
    line.totalBox.textContent = `₱${pesos(lineTotal(line))}`;
    line.warningBox.textContent = stockWarning(line);
    line.warningBox.classList.toggle("d-none", stockWarning(line) === "");
  });
};

// stepButton("bi-dash-lg", "Less", handler) -> a square button for the quantity
const stepButton = (icon, label, onClick) => {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `btn btn-outline-secondary bi ${icon}`;
  button.setAttribute("aria-label", label);
  button.addEventListener("click", onClick);
  return button;
};

// cartRow(line) -> the elements of one cart line (name, quantity, price, total, remove)
const cartRow = (line) => {
  const row = document.createElement("div");
  row.className = "border rounded-3 p-2";

  const top = document.createElement("div");
  top.className = "d-flex justify-content-between align-items-start gap-2";
  const name = document.createElement("div");
  name.className = "fw-semibold text-break min-w-0";
  name.textContent = [line.item.name, line.item.model].filter(Boolean).join(" · ");
  const remove = stepButton("bi-x-lg", `Remove ${line.item.name}`, () => {
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
  qtyInput.style.maxWidth = "4.5rem";
  qtyInput.setAttribute("aria-label", `Quantity of ${line.item.name}`);
  qtyInput.value = String(line.qty);
  qtyInput.addEventListener("input", () => {
    const count = toCount(qtyInput.value);
    line.qty = count === null ? NaN : count;
    updateTotals();
  });
  const setQty = (next) => {
    line.qty = Math.max(1, next);
    qtyInput.value = String(line.qty);
    updateTotals();
  };
  const priceGroup = document.createElement("div");
  priceGroup.className = "input-group";
  const peso = document.createElement("span");
  peso.className = "input-group-text";
  peso.textContent = "₱";
  const priceInput = document.createElement("input");
  priceInput.type = "text";
  priceInput.inputMode = "decimal";
  priceInput.className = "form-control";
  priceInput.setAttribute("aria-label", `Price of ${line.item.name}`);
  priceInput.value = pesos(line.price).replaceAll(",", "");
  priceInput.addEventListener("input", () => {
    line.price = priceInput.value.trim() === "" ? null : toCentavos(priceInput.value);
    updateTotals();
  });
  priceGroup.append(peso, priceInput);
  controls.append(
    stepButton("bi-dash-lg", "Less", () => setQty((Number.isInteger(line.qty) ? line.qty : 1) - 1)),
    qtyInput,
    stepButton("bi-plus-lg", "More", () => setQty((Number.isInteger(line.qty) ? line.qty : 0) + 1)),
    priceGroup,
  );

  const bottom = document.createElement("div");
  bottom.className = "d-flex justify-content-between align-items-center mt-2";
  const warning = document.createElement("div");
  warning.className = "small text-warning-emphasis d-none";
  const total = document.createElement("div");
  total.className = "fw-semibold ms-auto";
  bottom.append(warning, total);

  line.warningBox = warning;
  line.totalBox = total;
  row.append(top, controls, bottom);
  return row;
};

const renderCart = () => {
  cartBox.replaceChildren(...cart.map(cartRow));
  updateTotals();
};

// addToCart(item) -> adds one of the item, or one more when it is already there at its own price
const addToCart = (item) => {
  const same = cart.find((line) => line.item.id === item.id && line.price === item.benta);
  if (same) {
    same.qty = Number.isInteger(same.qty) ? same.qty + 1 : 1;
  } else {
    cart.push({ item, qty: 1, price: item.benta });
  }
  hideError("sale-error");
  renderCart();
};

// resultRow(item) -> a tappable row in the search results
const resultRow = (item) => {
  const row = document.createElement("button");
  row.type = "button";
  row.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-start gap-2";
  const info = document.createElement("div");
  info.className = "min-w-0 text-start";
  const name = document.createElement("div");
  name.className = "fw-semibold text-break";
  name.textContent = item.name;
  info.append(name);
  const where = [item.model, item.part_no].filter(Boolean).join(" · ");
  if (where) {
    const detail = document.createElement("div");
    detail.className = "small text-body-secondary";
    detail.textContent = where;
    info.append(detail);
  }
  const numbers = document.createElement("div");
  numbers.className = "text-end flex-shrink-0";
  const price = document.createElement("div");
  price.className = "fw-semibold";
  price.textContent = `₱${pesos(item.benta)}`;
  const stock = document.createElement("div");
  stock.className = "small text-body-secondary";
  stock.textContent = item.track_stock ? `Stock ${item.stock}` : "No stock count";
  numbers.append(price, stock);
  row.append(info, numbers);
  row.addEventListener("click", () => addToCart(item));
  return row;
};

const searchItems = async () => {
  const text = searchInput.value.trim();
  resultsHint.classList.toggle("d-none", text !== "");
  if (text === "") {
    resultsBox.replaceChildren();
    resultsEmpty.classList.add("d-none");
    return;
  }
  try {
    const response = await apiFetch(`/api/items?q=${encodeURIComponent(text)}&per_page=${RESULT_LIMIT}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    hideError("load-error");
    resultsBox.replaceChildren(...data.items.map(resultRow));
    resultsEmpty.classList.toggle("d-none", data.items.length > 0);
  } catch {
    showError("load-error", "Could not load the items.");
  }
};

let searchTimer = null;
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(searchItems, SEARCH_DELAY_MS);
});

saveButton.addEventListener("click", async () => {
  hideError("sale-error");
  const problem = cartProblem();
  if (problem) {
    showError("sale-error", problem);
    return;
  }
  const stopLoading = startLoading(saveButton);
  if (!stopLoading) return;
  try {
    const body = {
      client_ref: saleRef,
      lines: cart.map((line) => ({
        item_id: line.item.id,
        qty: line.qty,
        // Only send a price when it was changed; otherwise the item's own price is used.
        ...(line.price !== line.item.benta ? { benta: line.price } : {}),
      })),
    };
    if (dateInput && dateInput.value) body.sale_date = dateInput.value;
    if (noteInput.value.trim()) body.note = noteInput.value;
    const response = await apiFetch("/api/sales", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("sale-error", data.error || "Could not save the sale.");
      return;
    }
    const message = document.getElementById("sale-message");
    message.textContent = `Sale #${data.sale.id} saved: ₱${pesos(data.sale.total)}.`;
    message.classList.remove("d-none");
    cart = [];
    noteInput.value = "";
    saleRef = newRef(); // the next customer is a new sale
    renderCart();
    searchInput.value = "";
    searchItems();
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch {
    // The reference stays the same, so tapping Save again cannot make a second sale.
    showError("sale-error", "Cannot reach the server. Check your connection and tap Save again.");
  } finally {
    stopLoading();
    updateTotals();
  }
});

updateTotals();
