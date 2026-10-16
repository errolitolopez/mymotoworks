// Helpers shared by the logged-in pages.

// showError("login-error", "Wrong password.") -> shows the message in that alert box
const showError = (elementId, message) => {
  const box = document.getElementById(elementId);
  box.textContent = message;
  box.classList.remove("d-none");
};

// hideError("login-error") -> hides the alert box
const hideError = (elementId) => {
  document.getElementById(elementId).classList.add("d-none");
};

// fetch() that sends the user to the login page when the session has ended, or to the change
// password page while they still have a temporary password.
// Returns null in those cases, so callers can simply stop: if (!response) return;
const apiFetch = async (url, options) => {
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.location.href = "/login";
    return null;
  }
  if (response.status === 403) {
    const data = await response.clone().json().catch(() => ({}));
    if (data.must_change_password) {
      window.location.href = "/change-password";
      return null;
    }
  }
  return response;
};

// Marks a button as busy while its request runs: disabled, with a spinner in front of the label.
// Returns a function that puts the button back, or null when the button is already busy, so a
// double click sends only one request:
//   const stopLoading = startLoading(button);
//   if (!stopLoading) return;
//   try { ... } finally { stopLoading(); }
const busyButtons = new WeakSet();

const startLoading = (button) => {
  if (busyButtons.has(button)) return null;
  busyButtons.add(button);
  const spinner = document.createElement("span");
  spinner.className = "spinner-border spinner-border-sm me-1";
  spinner.setAttribute("aria-hidden", "true");
  button.prepend(spinner);
  button.disabled = true;
  return () => {
    spinner.remove();
    button.disabled = false;
    busyButtons.delete(button);
  };
};

const logoutButton = document.getElementById("logout-button");
if (logoutButton) {
  logoutButton.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
  });
}

// showLoginDetails({name, username}, "k3m9x2pq7a") -> opens the popup (templates/_login_details_modal.html)
// that shows a new account's or a reset password once.
const showLoginDetails = (user, password) => {
  document.getElementById("details-name").textContent = user.name;
  document.getElementById("details-username").textContent = user.username;
  document.getElementById("details-password").textContent = password;
  bootstrap.Modal.getOrCreateInstance(document.getElementById("login-details-modal")).show();
};

const copyDetailsButton = document.getElementById("copy-details-button");
if (copyDetailsButton) {
  copyDetailsButton.addEventListener("click", async () => {
    const text =
      `mymotoworks login\n` +
      `Username: ${document.getElementById("details-username").textContent}\n` +
      `Password: ${document.getElementById("details-password").textContent}`;
    try {
      await navigator.clipboard.writeText(text);
      copyDetailsButton.textContent = "Copied!";
    } catch {
      copyDetailsButton.textContent = "Can't copy";
    }
    setTimeout(() => (copyDetailsButton.textContent = " Copy"), 1500);
  });
}

// pesos(10350) -> "103.50", pesos(123456700) -> "1,234,567.00"
const pesos = (centavos) =>
  (centavos / 100).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// toCentavos("103.5") -> 10350, toCentavos("") -> 0, toCentavos("abc") -> null (not an amount)
// Typed pesos are read as text, never as a float, so 0.1 + 0.2 style errors cannot creep in.
const toCentavos = (text) => {
  const value = text.trim();
  if (value === "") return 0;
  if (!/^\d+(\.\d{1,2})?$/.test(value)) return null;
  const [whole, fraction = ""] = value.split(".");
  return Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
};

// toCount("12") -> 12, toCount("") -> 0, toCount("1.5") -> null (not a whole number)
const toCount = (text) => {
  const value = text.trim();
  if (value === "") return 0;
  return /^\d+$/.test(value) ? Number(value) : null;
};
