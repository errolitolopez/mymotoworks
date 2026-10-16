// The Count stock page (admin): type what is really on the shelf; saving sets the stock to it.

const MAX_FILTER_WORDS = 6;

const filterInput = document.getElementById("item-filter");
const itemListBox = document.getElementById("item-list");
const itemScroll = document.getElementById("item-scroll");
const itemsCount = document.getElementById("items-count");
const itemsStatus = document.getElementById("items-status");
const itemsEmpty = document.getElementById("items-empty");
const summaryBox = document.getElementById("count-summary");
const noteInput = document.getElementById("count-note");
const saveButton = document.getElementById("save-count");

// Only items that count stock. Loaded once; the list is filtered here.
let allItems = [];

// What was typed, by item id: {12: "7", 15: "0"}. Kept here, not in the boxes, because the list is drawn
// again when the filter changes.
const typed = new Map();

// newRef() -> "3f2c..." One reference per count, so a double tap or a retry saves it only once.
const newRef = () =>
  crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
let countRef = newRef();

// counted(item) -> 7 (what was typed), null (nothing typed), or NaN (typed, but not a whole number)
const counted = (item) => {
  const text = (typed.get(item.id) || "").trim();
  if (text === "") return null;
  const value = toCount(text);
  return value === null ? NaN : value;
};

// difference(item) -> -3 (counted 7, stock 10); null when nothing valid was typed
const difference = (item) => {
  const value = counted(item);
  return value === null || Number.isNaN(value) ? null : value - item.stock;
};

// signed(-2) -> "−2", signed(3) -> "+3", signed(0) -> "no change"
const signed = (change) => (change === 0 ? "no change" : change < 0 ? `−${Math.abs(change)}` : `+${change}`);

const updateSummary = () => {
  const entered = allItems.filter((item) => counted(item) !== null);
  const wrong = entered.filter((item) => Number.isNaN(counted(item))).length;
  const changing = entered.filter((item) => difference(item) !== null && difference(item) !== 0).length;
  summaryBox.textContent = entered.length === 0
    ? "Nothing counted yet."
    : `${plural(entered.length, "item")} counted, ${changing} will change.` + (wrong ? ` ${plural(wrong, "box", "boxes")} not a number.` : "");
  saveButton.disabled = entered.length === 0;
};

// showDifference(item, badge, input) -> the small mark under a row: "−3", "+2", "no change" or "Not a number"
const showDifference = (item, badge, input) => {
  const change = difference(item);
  const wrong = Number.isNaN(counted(item));
  input.classList.toggle("is-invalid", wrong);
  badge.textContent = wrong ? "Not a number" : change === null ? "" : signed(change);
  badge.className = `small fw-semibold ${wrong ? "text-danger" : change === null || change === 0 ? "text-body-secondary" : change < 0 ? "text-danger" : "text-success"}`;
};

// filterWords() -> ["air", "nmax"] from the filter box: every word must be in the item's text
const filterWords = () => filterInput.value.toLowerCase().split(/\s+/).filter(Boolean).slice(0, MAX_FILTER_WORDS);

// matches(item, ["air", "nmax"]) -> true for "AIR FILTER SUNTAL · NMAX V1" (any order, any case)
const matches = (item, words) => {
  const text = `${item.name} ${item.model} ${item.part_no}`.toLowerCase();
  return words.every((word) => text.includes(word));
};

// itemRow(item) -> one row: name, model, stock now, and a box for the number counted
const itemRow = (item) => {
  const row = document.createElement("div");
  row.className = "item-row list-group-item d-flex align-items-center gap-2 px-3 py-2";

  const info = document.createElement("div");
  info.className = "min-w-0 flex-grow-1";
  const name = document.createElement("div");
  name.className = "fw-semibold text-break";
  name.textContent = [item.name, item.model].filter(Boolean).join(" · ");
  const detail = document.createElement("div");
  detail.className = "small text-body-secondary text-break";
  detail.textContent = [item.part_no, `Stock now ${item.stock}`].filter(Boolean).join(" · ");
  info.append(name, detail);

  const side = document.createElement("div");
  side.className = "flex-shrink-0 text-end";
  const input = document.createElement("input");
  input.type = "text";
  input.inputMode = "numeric";
  input.className = "form-control text-center";
  input.style.width = "5.5rem";
  input.placeholder = "Counted";
  input.setAttribute("aria-label", `Counted ${item.name}`);
  input.value = typed.get(item.id) || "";
  const badge = document.createElement("div");
  showDifference(item, badge, input);
  input.addEventListener("input", () => {
    typed.set(item.id, input.value);
    showDifference(item, badge, input);
    updateSummary();
  });
  side.append(input, badge);

  row.append(info, side);
  return row;
};

// renderList() -> draws the items that match the filter box, and says how many
const renderList = () => {
  const words = filterWords();
  const shown = allItems.filter((item) => matches(item, words));
  itemListBox.replaceChildren(...shown.map(itemRow));
  itemsEmpty.classList.toggle("d-none", shown.length > 0 || allItems.length === 0);
  itemsCount.textContent = allItems.length === 0 ? ""
    : words.length ? `${shown.length} of ${plural(allItems.length, "item")}` : plural(allItems.length, "item");
  return shown;
};

const loadItems = async () => {
  try {
    const response = await apiFetch("/api/items/all");
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    hideError("load-error");
    allItems = data.items.filter((item) => item.track_stock);
    itemsStatus.textContent = allItems.length === 0 ? "No items that count stock yet." : "";
    itemsStatus.classList.toggle("d-none", allItems.length > 0);
    renderList();
    updateSummary();
  } catch {
    itemsStatus.classList.add("d-none");
    showError("load-error", "Could not load the items. Reload the page to try again.");
  }
};

filterInput.addEventListener("input", () => {
  renderList();
  itemScroll.scrollTop = 0; // a new filter shows its first match, not the middle of the old list
});

saveButton.addEventListener("click", async () => {
  hideError("count-error");
  const entered = allItems.filter((item) => counted(item) !== null);
  if (entered.some((item) => Number.isNaN(counted(item)))) {
    showError("count-error", "Every counted box must be a whole number, like 7 or 0.");
    return;
  }
  const changing = entered.filter((item) => difference(item) !== 0).length;
  if (!confirm(`Set the stock of ${plural(entered.length, "item")} to what you counted? ${changing} will change.`)) return;
  const stopLoading = startLoading(saveButton);
  if (!stopLoading) return;
  try {
    const body = {
      client_ref: countRef,
      lines: entered.map((item) => ({ item_id: item.id, counted: counted(item) })),
    };
    if (noteInput.value.trim()) body.note = noteInput.value;
    const response = await apiFetch("/api/stock-counts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("count-error", data.error || "Could not save the count.");
      return;
    }
    const message = document.getElementById("count-message");
    message.textContent = data.changed === 0
      ? "Nothing changed: every count was the same as the stock."
      : `Saved: ${plural(data.changed, "item")} changed${data.unchanged ? `, ${data.unchanged} already right` : ""}.`;
    message.classList.remove("d-none");
    typed.clear();
    countRef = newRef(); // the next count is a new one
    noteInput.value = "";
    filterInput.value = "";
    await loadItems(); // the stock shown is the new one
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch {
    // The reference stays the same, so tapping Save again cannot count twice.
    showError("count-error", "Cannot reach the server. Check your connection and tap Save again.");
  } finally {
    stopLoading();
    updateSummary();
  }
});

loadItems();
