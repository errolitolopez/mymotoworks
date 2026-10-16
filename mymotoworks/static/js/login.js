// Sends the username and password to /api/login, then opens the home page.

const form = document.getElementById("login-form");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const button = document.getElementById("login-button");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError("login-error");

  const username = usernameInput.value.trim();
  const password = passwordInput.value;
  if (!username || !password) {
    showError("login-error", "Enter your username and password.");
    return;
  }

  const stopLoading = startLoading(button);
  if (!stopLoading) return;
  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await response.json();
    if (response.ok) {
      window.location.href = data.must_change_password ? "/change-password" : "/dashboard";
      return;
    }
    // Only clear the password after a failed login: on success the browser reads it from the
    // field to offer "Save password?".
    passwordInput.value = "";
    passwordInput.focus();
    showError("login-error", data.error || "Login failed.");
  } catch {
    showError("login-error", "Cannot reach the server. Check your connection.");
  } finally {
    stopLoading();
  }
});
