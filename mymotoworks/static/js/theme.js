// Light / dark theme. Loaded in <head> so the theme is set before the page is drawn (no flash).
// "auto" follows the device; a person's choice is kept in this browser only.

(function () {
  const KEY = "mymotoworks-theme";
  const CHOICES = ["auto", "light", "dark"];
  const LABELS = { auto: "Auto", light: "Light", dark: "Dark" };
  const dark = window.matchMedia("(prefers-color-scheme: dark)");

  // saved() -> "dark" (or "auto" when nothing is saved or storage is blocked)
  const saved = () => {
    try {
      const value = localStorage.getItem(KEY);
      return CHOICES.includes(value) ? value : "auto";
    } catch {
      return "auto";
    }
  };

  // apply("auto") on a dark phone -> sets data-bs-theme="dark"
  const apply = (choice) => {
    const theme = choice === "auto" ? (dark.matches ? "dark" : "light") : choice;
    document.documentElement.setAttribute("data-bs-theme", theme);
  };

  // showButtons("dark") -> every theme button reads "Theme: Dark"
  const showButtons = (choice) => {
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.textContent = `Theme: ${LABELS[choice]}`;
    });
  };

  document.documentElement.classList.add("preload");
  window.addEventListener("load", () => {
    requestAnimationFrame(() => document.documentElement.classList.remove("preload"));
  });

  apply(saved());
  dark.addEventListener("change", () => apply(saved()));

  document.addEventListener("DOMContentLoaded", () => {
    showButtons(saved());
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = CHOICES[(CHOICES.indexOf(saved()) + 1) % CHOICES.length];
        try {
          localStorage.setItem(KEY, next);
        } catch {
          // Private window or blocked storage: the choice only lasts for this page.
        }
        apply(next);
        showButtons(next);
      });
    });
  });
})();
