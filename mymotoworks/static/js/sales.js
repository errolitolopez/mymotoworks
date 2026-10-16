// The Sales page: the sales of one day, each opening to show its items.

const isAdmin = document.getElementById("sales-main").dataset.admin === "true";
const dayInput = document.getElementById("day-date"); // only the admin has it

const listBox = document.getElementById("sale-list");
const emptyState = document.getElementById("empty-state");

// textLine("2 × AIR FILTER", "₱300.00") -> one line of a sale: what, and the amount on the right
const textLine = (left, right) => {
  const line = document.createElement("div");
  line.className = "d-flex justify-content-between gap-2";
  const leftBox = document.createElement("span");
  leftBox.className = "text-break min-w-0";
  leftBox.textContent = left;
  const rightBox = document.createElement("span");
  rightBox.className = "flex-shrink-0";
  rightBox.textContent = right;
  line.append(leftBox, rightBox);
  return line;
};

// saleCard(sale) -> a collapsible card: "#12 · 10:30 · Maria · ₱450.00", items inside
const saleCard = (sale) => {
  const card = document.createElement("details");
  card.className = "card";
  const summary = document.createElement("summary");
  summary.className = "card-body d-flex justify-content-between align-items-center gap-2";
  const head = document.createElement("span");
  head.className = "text-break min-w-0";
  head.textContent = `#${sale.id} · ${sale.recorded_at} · ${sale.recorded_by}`;
  const total = document.createElement("span");
  total.className = "fw-semibold flex-shrink-0";
  total.textContent = `₱${pesos(sale.total)}`;
  if (sale.voided) {
    head.classList.add("text-decoration-line-through", "text-body-secondary");
    total.classList.add("text-decoration-line-through", "text-body-secondary");
  }
  summary.append(head, total);

  const body = document.createElement("div");
  body.className = "card-body border-top d-flex flex-column gap-1 pt-2";
  sale.lines.forEach((line) => {
    body.append(textLine(`${line.qty} × ${line.name} @ ₱${pesos(line.benta)}`, `₱${pesos(line.line_total)}`));
    // Cost and profit only exist in the data for the admin.
    if (isAdmin) {
      const profit = document.createElement("div");
      profit.className = "small text-body-secondary";
      profit.textContent = `Puhunan ₱${pesos(line.puhunan)} · Tubo ₱${pesos(line.tubo)}`;
      body.append(profit);
    }
  });
  if (sale.voided) {
    const note = document.createElement("div");
    note.className = "small text-danger";
    note.textContent = `Voided: ${sale.void_reason}`;
    body.append(note);
  }
  card.append(summary, body);
  return card;
};

const loadDay = async () => {
  try {
    const query = dayInput && dayInput.value ? `?date=${encodeURIComponent(dayInput.value)}` : "";
    const response = await apiFetch(`/api/sales${query}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    hideError("load-error");
    document.getElementById("summary-count").textContent = String(data.summary.count);
    document.getElementById("summary-total").textContent = `₱${pesos(data.summary.total)}`;
    if (isAdmin) document.getElementById("summary-tubo").textContent = `₱${pesos(data.summary.tubo)}`;
    listBox.replaceChildren(...data.sales.map(saleCard));
    emptyState.classList.toggle("d-none", data.sales.length > 0);
  } catch {
    showError("load-error", "Could not load the sales.");
  }
};

if (dayInput) dayInput.addEventListener("change", loadDay);

loadDay();
