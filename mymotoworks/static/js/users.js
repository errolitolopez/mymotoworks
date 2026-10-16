// The Users page (admin): search, add, rename, reset a password, deactivate or activate.

const SEARCH_DELAY_MS = 300;

const listBox = document.getElementById("user-list");
const emptyState = document.getElementById("empty-state");
const searchInput = document.getElementById("search");
const userForm = document.getElementById("user-form");
const nameInput = document.getElementById("user-name");
const usernameInput = document.getElementById("user-username");
const roleSelect = document.getElementById("user-role");
const saveButton = document.getElementById("save-button");
const userModal = bootstrap.Modal.getOrCreateInstance(document.getElementById("user-modal"));

let editingId = null; // null while adding a new account

// roleLabel("staff") -> "Staff"
const roleLabel = (role) => (role === "admin" ? "Admin" : "Staff");

// smallButton("bi-pencil", "Edit", handler) -> a small outline button with an icon and a label
const smallButton = (icon, label, onClick) => {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `btn btn-outline-secondary btn-sm bi ${icon}`;
  button.textContent = ` ${label}`;
  button.addEventListener("click", () => onClick(button));
  return button;
};

// badge("Admin", "text-bg-dark") -> <span class="badge text-bg-dark">Admin</span>
const badge = (text, style) => {
  const element = document.createElement("span");
  element.className = `badge ${style}`;
  element.textContent = text;
  return element;
};

// sendUpdate(3, {active: false}, button) -> the response data, or null when it failed
const sendUpdate = async (userId, body, button) => {
  const stopLoading = startLoading(button);
  if (!stopLoading) return null;
  try {
    const response = await apiFetch(`/api/users/${userId}`, {
      method: "PUT",
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

const resetPassword = async (user, button) => {
  if (!confirm(`Make a new temporary password for ${user.name}? Their old password stops working.`)) return;
  const data = await sendUpdate(user.id, { reset_password: true }, button);
  if (!data) return;
  showLoginDetails(data.user, data.temp_password);
  loadUsers();
};

const toggleActive = async (user, button) => {
  if (user.active && !confirm(`Deactivate ${user.name}? They will be logged out and cannot log in.`)) return;
  const data = await sendUpdate(user.id, { active: !user.active }, button);
  if (data) loadUsers();
};

// userRow({name: "Maria", username: "maria", role: "staff", active: true, ...}) -> one list row
const userRow = (user) => {
  const row = document.createElement("div");
  row.className = "list-group-item d-flex flex-wrap justify-content-between align-items-center gap-2";

  const info = document.createElement("div");
  const name = document.createElement("div");
  name.className = "fw-semibold";
  name.textContent = user.name;
  const details = document.createElement("div");
  details.className = "small text-body-secondary d-flex flex-wrap align-items-center gap-2";
  const username = document.createElement("span");
  username.textContent = user.username;
  details.append(username, badge(roleLabel(user.role), user.role === "admin" ? "text-bg-dark" : "text-bg-secondary"));
  if (!user.active) details.append(badge("Deactivated", "text-bg-danger"));
  if (user.active && user.must_change_password) details.append(badge("Temporary password", "text-bg-warning"));
  info.append(name, details);

  const actions = document.createElement("div");
  actions.className = "d-flex flex-wrap gap-2";
  actions.append(
    smallButton("bi-pencil", "Edit", () => openForm(user)),
    smallButton("bi-key", "Reset password", (button) => resetPassword(user, button)),
    smallButton(user.active ? "bi-person-x" : "bi-person-check", user.active ? "Deactivate" : "Activate",
      (button) => toggleActive(user, button)),
  );
  row.append(info, actions);
  return row;
};

const loadUsers = async () => {
  try {
    const response = await apiFetch(`/api/users?q=${encodeURIComponent(searchInput.value.trim())}`);
    if (!response) return;
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    hideError("load-error");
    listBox.replaceChildren(...data.users.map(userRow));
    emptyState.classList.toggle("d-none", data.users.length > 0);
  } catch {
    showError("load-error", "Could not load the accounts.");
  }
};

// openForm() adds a new account; openForm(user) renames that account (username and role stay).
const openForm = (user = null) => {
  editingId = user ? user.id : null;
  document.getElementById("user-modal-title").textContent = user ? "Edit account" : "Add account";
  nameInput.value = user ? user.name : "";
  usernameInput.value = user ? user.username : "";
  roleSelect.value = user ? user.role : "staff";
  document.getElementById("username-group").classList.toggle("d-none", Boolean(user));
  document.getElementById("role-group").classList.toggle("d-none", Boolean(user));
  hideError("form-error");
  userModal.show();
};

userForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("form-error");
  const stopLoading = startLoading(saveButton);
  if (!stopLoading) return;
  try {
    const adding = editingId === null;
    const response = await apiFetch(adding ? "/api/users" : `/api/users/${editingId}`, {
      method: adding ? "POST" : "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(adding
        ? { name: nameInput.value, username: usernameInput.value, role: roleSelect.value }
        : { name: nameInput.value }),
    });
    if (!response) return;
    const data = await response.json();
    if (!response.ok) {
      showError("form-error", data.error || "Could not save the account.");
      return;
    }
    userModal.hide();
    if (adding) showLoginDetails(data.user, data.temp_password);
    loadUsers();
  } catch {
    showError("form-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});

document.getElementById("add-button").addEventListener("click", () => openForm());

let searchTimer = null;
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadUsers, SEARCH_DELAY_MS);
});

loadUsers();
