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
