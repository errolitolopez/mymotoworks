// The Sales page: the sales of one day, each opening to show its items. The admin approves, rejects,
// voids and replaces from here.

const isAdmin = document.getElementById("sales-main").dataset.admin === "true";
const dayInput = document.getElementById("day-date"); // only the admin has it
const approveAllButton = document.getElementById("approve-all"); // only the admin has it

const listBox = document.getElementById("sale-list");
const emptyState = document.getElementById("empty-state");
const pendingBox = document.getElementById("pending-box");

// The Home page links here with the day to look at: /sales?date=2026-10-16
const linkedDay = new URLSearchParams(window.location.search).get("date");
if (dayInput && linkedDay && /^\d{4}-\d{2}-\d{2}$/.test(linkedDay) && linkedDay <= dayInput.max) {
  dayInput.value = linkedDay;
}

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

// badge("Pending", "text-bg-warning") -> <span class="badge text-bg-warning">Pending</span>
const badge = (text, style) => {
  const element = document.createElement("span");
  element.className = `badge ${style}`;
  element.textContent = text;
  return element;
};

// actionButton("bi-check-lg", "Approve", "btn-success", handler) -> a button with an icon and a label
const actionButton = (icon, label, style, onClick) => {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `btn ${style} bi ${icon}`;
  button.textContent = ` ${label}`;
  button.addEventListener("click", () => onClick(button));
  return button;
};

// postAction("/api/sales/12/approve", {}, button) -> the answer, or null when it failed (the error is shown)
const postAction = async (url, body, button) => {
  const stopLoading = startLoading(button);
  if (!stopLoading) return null;
  try {
    const response = await apiFetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response) return null;
    const data = await response.json();
    if (!response.ok) {
      showError("load-error", data.error || "Could not save the change.");
      return null;
    }
    hideError("load-error");
    return data;
  } catch {
    showError("load-error", "Cannot reach the server. Check your connection.");
    return null;
  } finally {
    stopLoading();
  }
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
  // The note (for example the customer's name) shows under the sale number, so it can be found at a glance.
  const left = document.createElement("span");
  left.className = "min-w-0";
  left.append(head);
  const marks = document.createElement("div");
  marks.className = "d-flex flex-wrap gap-1 align-items-center";
  if (sale.status === "pending") marks.append(badge("Pending", "text-bg-warning"));
  if (sale.status === "rejected") marks.append(badge("Rejected", "text-bg-secondary"));
  if (sale.status === "voided") marks.append(badge("Voided", "text-bg-secondary"));
  if (sale.note) {
    const note = document.createElement("span");
    note.className = "small text-body-secondary text-break";
    note.textContent = sale.note;
    marks.append(note);
  }
  if (marks.children.length) left.append(marks);
  summary.append(left, total);

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
  if (sale.status === "pending") {
    const wait = document.createElement("div");
    wait.className = "small text-body-secondary";
    wait.textContent = "Waiting for the admin to approve it. The stock is not touched yet.";
    body.append(wait);
  }
  if (sale.voided) {
    const note = document.createElement("div");
    note.className = "small text-danger";
    note.textContent = `${sale.status === "rejected" ? "Rejected" : "Voided"}: ${sale.void_reason}`;
    body.append(note);
  }
  // Links between a sale and the one that corrected it. Both records stay.
  [[sale.replaces, "Replaces sale"], [sale.replaced_by, "Replaced by sale"]].forEach(([id, label]) => {
    if (!id) return;
    const link = document.createElement("div");
    link.className = "small text-body-secondary";
    link.textContent = `${label} #${id}`;
    body.append(link);
  });

  const actions = document.createElement("div");
  actions.className = "d-flex flex-wrap gap-2 mt-2";
  // Copy starts a new cart from this sale; the sale itself is not changed.
  const copyLink = document.createElement("a");
  copyLink.className = "btn btn-outline-secondary bi bi-files";
  copyLink.href = `/sell?copy=${sale.id}`;
  copyLink.textContent = " Copy";
  actions.append(copyLink);
  if (isAdmin && sale.status === "pending") {
    actions.append(
      actionButton("bi-check-lg", "Approve", "btn-success", async (button) => {
        if (await postAction(`/api/sales/${sale.id}/approve`, {}, button)) loadDay();
      }),
      actionButton("bi-x-circle", "Reject", "btn-outline-danger", () => openVoid(sale)),
    );
  }
  if (isAdmin && sale.status === "approved") {
    actions.append(actionButton("bi-slash-circle", "Void sale", "btn-outline-danger", () => openVoid(sale)));
  }
  body.append(actions);
  card.append(summary, body);
  return card;
};

let voidingId = null;

// openVoid(sale) -> opens the reason form. A pending sale is "rejected" (no stock was taken); an
// approved one is "voided" (its stock comes back).
const openVoid = (sale) => {
  const pending = sale.status === "pending";
  voidingId = sale.id;
  document.getElementById("void-modal-title").textContent = pending ? "Reject sale" : "Void sale";
  document.getElementById("void-label").textContent = pending ? "Why is it rejected?" : "Why is it voided?";
  document.getElementById("void-help").textContent = pending
    ? "It was never approved, so the stock is not touched. The sale stays in the list, crossed out."
    : "The stock goes back and the sale leaves the totals. The sale stays in the list, crossed out.";
  document.getElementById("void-button").textContent = pending ? " Reject sale" : " Void sale";
  document.getElementById("void-summary").textContent =
    `Sale #${sale.id}, ₱${pesos(sale.total)}, ${sale.recorded_at}.`;
  document.getElementById("void-reason").value = "";
  hideError("void-error");
  bootstrap.Modal.getOrCreateInstance(document.getElementById("void-modal")).show();
};

if (isAdmin) {
  const voidForm = document.getElementById("void-form");
  const confirmButton = document.getElementById("void-button");
  voidForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideError("void-error");
    const reason = document.getElementById("void-reason").value.trim();
    if (!reason) {
      showError("void-error", "Write the reason.");
      return;
    }
    const stopLoading = startLoading(confirmButton);
    if (!stopLoading) return;
    try {
      const response = await apiFetch(`/api/sales/${voidingId}/void`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      if (!response) return;
      const data = await response.json();
      if (!response.ok) {
        showError("void-error", data.error || "Could not save the change.");
        return;
      }
      bootstrap.Modal.getOrCreateInstance(document.getElementById("void-modal")).hide();
      loadDay();
    } catch {
      showError("void-error", "Cannot reach the server. Check your connection.");
    } finally {
      stopLoading();
    }
  });
}

// showPending(summary.pending) -> the yellow box about sales that wait for approval (hidden when none)
const showPending = (pending) => {
  pendingBox.classList.toggle("d-none", pending.count === 0);
  document.getElementById("pending-text").textContent =
    `Pending: ${plural(pending.count, "sale")}, ₱${pesos(pending.total)}. ` +
    "They are not in the totals above, and the stock is not touched until the admin approves them.";
  if (approveAllButton) approveAllButton.dataset.count = String(pending.count);
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
    showPending(data.summary.pending);
    listBox.replaceChildren(...data.sales.map(saleCard));
    emptyState.classList.toggle("d-none", data.sales.length > 0);
  } catch {
    showError("load-error", "Could not load the sales.");
  }
};

if (approveAllButton) {
  approveAllButton.addEventListener("click", async () => {
    const count = Number(approveAllButton.dataset.count);
    if (!confirm(`Approve ${plural(count, "sale")}? Their stock is taken now.`)) return;
    const body = dayInput && dayInput.value ? { date: dayInput.value } : {};
    if (await postAction("/api/sales/approve-all", body, approveAllButton)) loadDay();
  });
}

if (dayInput) dayInput.addEventListener("change", loadDay);

loadDay();
