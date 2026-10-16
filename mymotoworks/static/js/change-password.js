// Saves a new password, then opens the home page.

const MIN_PASSWORD_LENGTH = 6;

const form = document.getElementById("password-form");
const currentInput = document.getElementById("current-password");
const newInput = document.getElementById("new-password");
const confirmInput = document.getElementById("confirm-password");
const button = document.getElementById("password-button");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("password-error");

  if (!currentInput.value) {
    showError("password-error", "Enter your current password.");
    return;
  }
  if (newInput.value.length < MIN_PASSWORD_LENGTH) {
    showError("password-error", `New password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
    return;
  }
  if (newInput.value !== confirmInput.value) {
    showError("password-error", "The two new passwords don't match.");
    return;
  }

  const stopLoading = startLoading(button);
  if (!stopLoading) return;
  try {
    const response = await apiFetch("/api/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentInput.value, new_password: newInput.value }),
    });
    if (!response) return;
    if (response.ok) {
      window.location.href = "/dashboard";
      return;
    }
    const data = await response.json();
    showError("password-error", data.error || "Could not save the password.");
  } catch {
    showError("password-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});
