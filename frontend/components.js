/**
 * Shared UI Components — American Dream Election
 * Drew's UI base layout feature (drew/ui-base-layout)
 * Provides consistent navbar, footer, and alert system across all pages.
 */

const API_BASE_URL = "/api";

/* ------------------------------------------------------------------ */
/*  NAVBAR                                                            */
/* ------------------------------------------------------------------ */

/**
 * Renders the shared navbar into a <header id="app-navbar"> element.
 * @param {object} opts
 * @param {string} opts.title       - Page title shown next to logo (default: "American Dream Election")
 * @param {boolean} opts.showBack   - Show a "← Back" link to dashboard (default: false)
 * @param {boolean} opts.showUser   - Show user greeting + logout button (default: true)
 */
export function renderNavbar(opts = {}) {
  const {
    title = "American Dream Election",
    showBack = false,
    showUser = true,
  } = opts;

  const target = document.getElementById("app-navbar");
  if (!target) return;

  const backBtn = showBack
    ? `<a href="./dashboard.html"
         class="bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium px-4 py-2 rounded-lg transition">
         &larr; Back
       </a>`
    : "";

  const userSection = showUser
    ? `<div class="flex items-center gap-2 sm:gap-3">
         <span id="nav-whoami" class="text-sm text-gray-500 hidden sm:block"></span>
         <span id="nav-role-badge" class="hidden sm:inline-flex text-xs font-semibold px-2.5 py-1 rounded-full"></span>
         ${backBtn}
         <a href="./settings.html" title="Settings"
           class="bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium px-2.5 py-2 rounded-lg transition">
           &#9881;
         </a>
         <button id="nav-logout-btn"
           class="bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium px-3 py-2 rounded-lg transition">
           <span class="hidden sm:inline">Logout</span>
           <span class="sm:hidden">&#x2192;</span>
         </button>
       </div>`
    : (showBack ? `<div class="flex items-center gap-2">${backBtn}</div>` : "");

  target.innerHTML = `
    <div class="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <img src="./applogo.png" alt="American Dream Election logo" class="h-10 w-auto" />
        <span class="text-lg font-bold text-gray-800">${title}</span>
      </div>
      ${userSection}
    </div>
  `;

  // Attach logout handler
  const logoutBtn = document.getElementById("nav-logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: "POST",
          credentials: "include",
        });
      } finally {
        localStorage.removeItem("sessionUser");
        sessionStorage.removeItem("sessionUser");
        window.location.href = "./login.html";
      }
    });
  }
}

/**
 * Fetches /api/me, populates the navbar user info, and returns the user object.
 */
export async function loadNavbarUser() {
  try {
    const response = await fetch(`${API_BASE_URL}/me`, { credentials: "include" });
    if (!response.ok) throw new Error("Not authenticated");
    const user = await response.json();

    const whoami = document.getElementById("nav-whoami");
    if (whoami) {
      whoami.textContent = `${user.first_name || ""} ${user.last_name || ""}`.trim();
    }

    // Role badge colors
    const roleBadge = document.getElementById("nav-role-badge");
    if (roleBadge && user.role) {
      const roleColors = {
        admin:    "bg-red-100 text-red-700",
        officer:  "bg-purple-100 text-purple-700",
        employee: "bg-blue-100 text-blue-700",
        member:   "bg-green-100 text-green-700",
      };
      roleBadge.className = `text-xs font-semibold px-2.5 py-1 rounded-full ${roleColors[user.role] || "bg-gray-100 text-gray-600"}`;
      roleBadge.textContent = user.role.charAt(0).toUpperCase() + user.role.slice(1);
      roleBadge.classList.remove("hidden");
    }

    return user;
  } catch (_) {
    window.location.href = "./login.html";
    return null;
  }
}

/* ------------------------------------------------------------------ */
/*  FOOTER                                                            */
/* ------------------------------------------------------------------ */

/**
 * Renders the shared footer into a <footer id="app-footer"> element.
 */
export function renderFooter() {
  const target = document.getElementById("app-footer");
  if (!target) return;

  const year = new Date().getFullYear();

  target.innerHTML = `
    <div class="max-w-6xl mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
      <p class="text-sm text-gray-400">&copy; ${year} American Dream Election System &mdash; ISTE-432 FooFighters</p>
      <div class="flex gap-4 text-sm">
        <a href="#" class="text-gray-400 hover:text-gray-600 transition">Help</a>
        <a href="#" class="text-gray-400 hover:text-gray-600 transition">Privacy</a>
        <a href="#" class="text-gray-400 hover:text-gray-600 transition">Terms</a>
      </div>
    </div>
  `;
}

/* ------------------------------------------------------------------ */
/*  ALERTS / NOTIFICATIONS                                            */
/* ------------------------------------------------------------------ */

/**
 * Shows a temporary alert banner at the top of the page.
 * @param {string} message - The message to display
 * @param {"success"|"error"|"info"|"warning"} type - Alert style
 * @param {number} duration - Auto-dismiss in ms (0 = manual dismiss only)
 */
export function showAlert(message, type = "info", duration = 4000) {
  // Remove any existing alert
  const existing = document.getElementById("app-alert");
  if (existing) existing.remove();

  const colors = {
    success: "bg-green-50 border-green-300 text-green-800",
    error:   "bg-red-50 border-red-300 text-red-800",
    warning: "bg-amber-50 border-amber-300 text-amber-800",
    info:    "bg-blue-50 border-blue-300 text-blue-800",
  };

  const icons = {
    success: "&#10003;",
    error:   "&#10007;",
    warning: "&#9888;",
    info:    "&#8505;",
  };

  const alert = document.createElement("div");
  alert.id = "app-alert";
  alert.className = `fixed top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-5 py-3 rounded-lg border shadow-lg text-sm font-medium transition-all ${colors[type] || colors.info}`;
  alert.style.animation = "alertSlideIn 0.3s ease-out";
  alert.innerHTML = `
    <span class="text-lg leading-none">${icons[type] || icons.info}</span>
    <span>${message}</span>
    <button onclick="this.parentElement.remove()" class="ml-2 opacity-60 hover:opacity-100 text-lg leading-none">&times;</button>
  `;

  document.body.appendChild(alert);

  if (duration > 0) {
    setTimeout(() => {
      if (alert.parentElement) {
        alert.style.animation = "alertSlideOut 0.3s ease-in forwards";
        setTimeout(() => alert.remove(), 300);
      }
    }, duration);
  }
}
