/**
 * Shared UI components — navbar, footer, and alerts.
 *
 * Every page renders these, so they are the fastest way to keep the interface
 * consistent: change the chrome here and it changes everywhere.
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
         class="inline-flex items-center gap-1.5 border border-ink-200 bg-white hover:bg-ink-50 hover:border-ink-300 text-ink-700 text-sm font-medium px-3.5 py-2 rounded-lg transition-colors">
         <span aria-hidden="true">&larr;</span> Back
       </a>`
    : "";

  const userSection = showUser
    ? `<div class="flex items-center gap-2 sm:gap-2.5">
         <div class="hidden sm:flex items-center gap-2 mr-1">
           <span id="nav-whoami" class="text-sm font-medium text-ink-700"></span>
           <span id="nav-role-badge" class="hidden text-[11px] font-semibold tracking-wide px-2 py-0.5 rounded-full border"></span>
         </div>
         ${backBtn}
         <a href="./settings.html" title="Settings" aria-label="Settings"
           class="inline-flex items-center justify-center w-9 h-9 border border-ink-200 bg-white hover:bg-ink-50 hover:border-ink-300 text-ink-600 rounded-lg transition-colors">
           <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
         </a>
         <button id="nav-logout-btn"
           class="inline-flex items-center gap-1.5 border border-ink-200 bg-white hover:bg-ink-50 hover:border-ink-300 text-ink-700 text-sm font-medium px-3.5 py-2 rounded-lg transition-colors">
           <span class="hidden sm:inline">Logout</span>
           <span class="sm:hidden" aria-hidden="true">&#x2192;</span>
         </button>
       </div>`
    : (showBack ? `<div class="flex items-center gap-2">${backBtn}</div>` : "");

  target.innerHTML = `
    <div class="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
      <a href="./dashboard.html" class="flex items-center gap-3 min-w-0 group">
        <img src="./logo.jpeg" alt="" class="h-9 w-auto rounded" />
        <span id="nav-title" class="text-[15px] font-semibold text-ink-900 truncate group-hover:text-brand-700 transition-colors">${title}</span>
      </a>
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
        admin:    "bg-red-50 text-red-700 border-red-200",
        officer:  "bg-purple-50 text-purple-700 border-purple-200",
        employee: "bg-brand-50 text-brand-700 border-brand-200",
        member:   "bg-emerald-50 text-emerald-700 border-emerald-200",
      };
      roleBadge.className = `text-[11px] font-semibold tracking-wide px-2 py-0.5 rounded-full border ${roleColors[user.role] || "bg-ink-100 text-ink-600 border-ink-200"}`;
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
    <div class="max-w-6xl mx-auto px-4 sm:px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-3">
      <p class="text-[13px] text-ink-400">&copy; ${year} American Dream Election System</p>
      <p class="text-[13px] text-ink-400">Secure voting for professional societies</p>
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
    success: "bg-white border-emerald-200 text-emerald-800",
    error:   "bg-white border-red-200 text-red-800",
    warning: "bg-white border-amber-200 text-amber-800",
    info:    "bg-white border-brand-200 text-brand-800",
  };

  const icons = {
    success: "&#10003;",
    error:   "&#10007;",
    warning: "&#9888;",
    info:    "&#8505;",
  };

  const alert = document.createElement("div");
  alert.id = "app-alert";
  alert.className = `fixed top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border shadow-pop text-sm font-medium max-w-[92vw] ${colors[type] || colors.info}`;
  alert.setAttribute("role", type === "error" ? "alert" : "status");
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
