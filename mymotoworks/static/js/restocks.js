// The Restock history page (admin): every restock, newest first, each opening to show its items.

const listBox = document.getElementById("restock-list");
const emptyState = document.getElementById("empty-state");
const pager = document.getElementById("pager");
const pageLabel = document.getElementById("page-label");
const prevButton = document.getElementById("prev-button");
const nextButton = document.getElementById("next-button");

let page = 1;

// textLine("10 × AIR FILTER @ ₱110.00", "₱1,100.00") -> one line: what, and the amount on the right
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

// costChange(line) -> "cost ₱103.50 → ₱110.00", or "cost unchanged ₱103.50"
const costChange = (line) =>
  line.old_puhunan === line.puhunan
    ? `cost unchanged ₱${pesos(line.puhunan)}`
    : `cost ₱${pesos(line.old_puhunan)} → ₱${pesos(line.puhunan)}`;

// restockCard(restock) -> a collapsible card: "#4 · Oct 16 · 10:30", total, items inside
const restockCard = (restock) => {
  const card = document.createElement("details");
  card.className = "card";
  const summary = document.createElement("summary");
  summary.className = "card-body d-flex justify-content-between align-items-center gap-2";
  const head = document.createElement("span");
  head.className = "text-break min-w-0";
  head.textContent = `#${restock.id} · ${formatDay(restock.restock_date)} · ${restock.recorded_at}`;
  const total = document.createElement("span");
  total.className = "fw-semibold flex-shrink-0";
  total.textContent = `₱${pesos(restock.total)}`;
  if (restock.voided) {
    head.classList.add("text-decoration-line-through", "text-body-secondary");
    total.classList.add("text-decoration-line-through", "text-body-secondary");
  }
  const left = document.createElement("span");
  left.className = "min-w-0";
  left.append(head);
  const marks = document.createElement("div");
  marks.className = "d-flex flex-wrap gap-1 align-items-center small text-body-secondary";
  if (restock.voided) {
    const badge = document.createElement("span");
    badge.className = "badge text-bg-secondary";
    badge.textContent = "Voided";
    marks.append(badge);
  }
  const summaryText = document.createElement("span");
  summaryText.className = "text-break";
  summaryText.textContent = [plural(restock.lines.length, "item"), restock.note].filter(Boolean).join(" · ");
  marks.append(summaryText);
  left.append(marks);
  summary.append(left, total);

  const body = document.createElement("div");
  body.className = "card-body border-top d-flex flex-column gap-1 pt-2";
  restock.lines.forEach((line) => {
    body.append(textLine(`${line.qty} × ${line.name} @ ₱${pesos(line.puhunan)}`, `₱${pesos(line.line_total)}`));
    const change = document.createElement("div");
    change.className = "small text-body-secondary";
    change.textContent = costChange(line);
    body.append(change);
  });
  const by = document.createElement("div");
  by.className = "small text-body-secondary";
  by.textContent = `Recorded by ${restock.recorded_by}`;
  body.append(by);
  if (restock.voided) {
    const note = document.createElement("div");
    note.className = "small text-danger";
    note.textContent = `Voided: ${restock.void_reason}`;
    body.append(note);
  }
  if (!restock.voided) {
    const voidButton = document.createElement("button");
    voidButton.type = "button";
    voidButton.className = "btn btn-outline-danger bi bi-slash-circle align-self-start mt-2";
    voidButton.textContent = " Void restock";
    voidButton.addEventListener("click", () => openVoid(restock));
    body.append(voidButton);
  }
  card.append(summary, body);
  return card;
};

let voidingId = null;

// openVoid(restock) -> opens the reason form for that restock
const openVoid = (restock) => {
  voidingId = restock.id;
  document.getElementById("void-summary").textContent =
    `Restock #${restock.id}, ₱${pesos(restock.total)}, ${formatDay(restock.restock_date)}.`;
  document.getElementById("void-reason").value = "";
  hideError("void-error");
  bootstrap.Modal.getOrCreateInstance(document.getElementById("void-modal")).show();
};

const voidForm = document.getElementById("void-form");
const confirmButton = document.getElementById("void-button");
voidForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("void-error");
  const reason = document.getElementById("void-reason").value.trim();
  if (!reason) {
    showError("void-error", "Write why the restock is voided.");
    return;
  }
  const stopLoading = startLoading(confirmButton);
  if (!stopLoading) return;
  try {
    const response = await apiFetch(`/api/restocks/${voidingId}/void`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("void-error", data.error || "Could not void the restock.");
      return;
    }
    bootstrap.Modal.getOrCreateInstance(document.getElementById("void-modal")).hide();
    loadPage();
  } catch {
    showError("void-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

const loadPage = async () => {
  try {
    const response = await apiFetch(`/api/restocks?page=${page}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    hideError("load-error");
    page = data.page;
    listBox.replaceChildren(...data.restocks.map(restockCard));
    emptyState.classList.toggle("d-none", data.total > 0);
    pager.classList.toggle("d-none", data.pages < 2);
    pageLabel.textContent = `Page ${data.page} of ${data.pages} · ${plural(data.total, "restock")}`;
    prevButton.disabled = data.page <= 1;
    nextButton.disabled = data.page >= data.pages;
  } catch {
    showError("load-error", "Could not load the restocks.");
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
