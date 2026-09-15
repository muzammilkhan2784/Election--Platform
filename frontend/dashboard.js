import { renderNavbar, renderFooter, loadNavbarUser, showAlert } from "./components.js";

const API_BASE_URL = "/api";

const electionsListEl = document.getElementById("elections-list");
const rolePanelEl = document.getElementById("role-panel");

// Initialize shared components
renderNavbar({ title: "American Dream Election", showUser: true });
renderFooter();

async function fetchJson(url, options = {}) {
  const response = await fetch(url, { credentials: "include", ...options });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }
  return response.json();
}

/* ------------------------------------------------------------------ */
/*  Role-specific dashboard panels                                    */
/* ------------------------------------------------------------------ */

function renderRolePanel(user) {
  if (!user || !user.role) return;

  rolePanelEl.classList.remove("hidden");

  const panels = {
    admin: `
      <div class="bg-white rounded-2xl border border-ink-200 shadow-card p-6">
        <div class="flex items-center gap-3 mb-4">
          <span class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-red-50 text-red-600 border border-red-200 text-lg font-bold">A</span>
          <div>
            <h3 class="font-semibold text-ink-900">Admin Panel</h3>
            <p class="text-sm text-ink-500">System administration tools</p>
          </div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <a href="./admin.html?tab=users" class="flex flex-col items-center gap-2 px-3 py-4 rounded-xl border border-ink-200 hover:bg-brand-50 hover:border-brand-200 transition-colors text-center">
            <svg class="w-5 h-5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            <span class="text-sm font-medium text-ink-700">Manage Users</span>
          </a>
          <a href="./admin.html?tab=societies" class="flex flex-col items-center gap-2 px-3 py-4 rounded-xl border border-ink-200 hover:bg-brand-50 hover:border-brand-200 transition-colors text-center">
            <svg class="w-5 h-5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21h18"/><path d="M5 21V8l7-5 7 5v13"/><path d="M9 21v-5h6v5"/><path d="M9 12h.01"/><path d="M15 12h.01"/></svg>
            <span class="text-sm font-medium text-ink-700">Societies</span>
          </a>
          <a href="./admin.html?tab=audit" class="flex flex-col items-center gap-2 px-3 py-4 rounded-xl border border-ink-200 hover:bg-brand-50 hover:border-brand-200 transition-colors text-center">
            <svg class="w-5 h-5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>
            <span class="text-sm font-medium text-ink-700">Audit Logs</span>
          </a>
          <a href="./admin.html?tab=reports" class="flex flex-col items-center gap-2 px-3 py-4 rounded-xl border border-ink-200 hover:bg-brand-50 hover:border-brand-200 transition-colors text-center">
            <svg class="w-5 h-5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/></svg>
            <span class="text-sm font-medium text-ink-700">Reports</span>
          </a>
        </div>
      </div>`,

    officer: `
      <div class="bg-white rounded-2xl border border-ink-200 shadow-card p-6">
        <div class="flex items-center gap-3 mb-4">
          <span class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-purple-50 text-purple-600 border border-purple-200 text-lg font-bold">O</span>
          <div>
            <h3 class="font-semibold text-ink-900">Officer Tools</h3>
            <p class="text-sm text-ink-500">Election oversight &amp; participation</p>
          </div>
        </div>
        <div class="grid grid-cols-1 gap-3">
          <a href="./participation.html" class="flex flex-col items-center gap-2 px-3 py-4 rounded-xl border border-ink-200 hover:bg-purple-50 hover:border-purple-200 transition-colors text-center">
            <svg class="w-5 h-5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/></svg>
            <span class="text-sm font-medium text-ink-700">Voter Participation</span>
          </a>
        </div>
      </div>`,

    employee: `
      <div class="bg-white rounded-2xl border border-ink-200 shadow-card p-6">
        <div class="flex items-center gap-3 mb-4">
          <span class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-brand-50 text-brand-600 border border-brand-200 text-lg font-bold">E</span>
          <div>
            <h3 class="font-semibold text-ink-900">Employee Dashboard</h3>
            <p class="text-sm text-ink-500">Your assigned societies &amp; tasks</p>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <a href="./participation.html" class="flex flex-col items-center gap-2 px-3 py-4 rounded-xl border border-ink-200 hover:bg-brand-50 hover:border-brand-200 transition-colors text-center">
            <svg class="w-5 h-5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/></svg>
            <span class="text-sm font-medium text-ink-700">Participation</span>
          </a>
          <a href="./pending-tasks.html" class="flex flex-col items-center gap-2 px-3 py-4 rounded-xl border border-ink-200 hover:bg-brand-50 hover:border-brand-200 transition-colors text-center">
            <svg class="w-5 h-5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M9 14l2 2 4-4"/></svg>
            <span class="text-sm font-medium text-ink-700">Pending Tasks</span>
          </a>
        </div>
      </div>`,

    member: `
      <div class="bg-white rounded-2xl border border-ink-200 shadow-card p-6">
        <div class="flex items-center gap-3 mb-4">
          <span class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-200 text-lg font-bold">M</span>
          <div>
            <h3 class="font-semibold text-ink-900">Welcome Back!</h3>
            <p class="text-sm text-ink-500">Your voting hub</p>
          </div>
        </div>
        <p class="text-ink-600 text-sm">Browse the elections below to cast your vote or check results. Your participation matters!</p>
      </div>`,
  };

  rolePanelEl.innerHTML = panels[user.role] || "";
}

/* ------------------------------------------------------------------ */
/*  Election cards                                                    */
/* ------------------------------------------------------------------ */

function electionCard(e, role) {
  // Badge styling lives in styles.css so election state looks the same on
  // every screen that shows it.
  const badgeClass = {
    active: "badge badge-active",
    draft: "badge badge-draft",
    completed: "badge badge-completed",
  }[e.status] || "badge badge-completed";

  const buttons = [];
  const primary = (href, label) =>
    `<a class="flex-1 text-center bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold py-2.5 rounded-lg transition-colors" href="${href}">${label}</a>`;
  const secondary = (href, label) =>
    `<a class="flex-1 text-center border border-ink-200 hover:bg-ink-50 hover:border-ink-300 text-ink-700 text-sm font-medium py-2.5 rounded-lg transition-colors" href="${href}">${label}</a>`;

  if (role === "employee" || role === "admin") {
    if (e.status === "draft") {
      buttons.push(primary(`./ballot-editor.html?id=${e.election_id}`, "Edit ballot"));
    }
    if (e.status === "active" || e.status === "completed") {
      buttons.push(secondary(`./results.html?id=${e.election_id}`, "View results"));
    }
  } else if (role === "officer") {
    if (e.status === "active") {
      buttons.push(primary(`./ballot.html?id=${e.election_id}`, "Vote"));
    }
    if (e.status === "completed") {
      buttons.push(secondary(`./results.html?id=${e.election_id}`, "View results"));
    }
  } else if (e.status === "active") {
    buttons.push(primary(`./ballot.html?id=${e.election_id}`, "Vote"));
  }

  const buttonsHtml = buttons.length
    ? `<div class="flex gap-2 mt-auto pt-1">${buttons.join("")}</div>`
    : `<p class="mt-auto pt-1 text-[13px] text-ink-400">No actions available</p>`;

  const dates = [e.start_date, e.end_date].filter(Boolean).join(" \u2013 ");

  return `
    <article class="card card-interactive gap-3">
      <div class="card-top">
        <h3>${e.name}</h3>
        <span class="${badgeClass}">${e.status}</span>
      </div>
      <div>
        <p class="text-[13.5px] text-ink-600 font-medium">${e.society_name}</p>
        <p class="text-[12.5px] text-ink-400 mt-0.5 tabular">${dates}</p>
      </div>
      ${buttonsHtml}
    </article>
  `;
}

/* ------------------------------------------------------------------ */
/*  Main load                                                         */
/* ------------------------------------------------------------------ */

async function load() {
  try {
    // Load user data into navbar + role panel
    const user = await loadNavbarUser();
    if (!user) return; // redirected to login

    renderRolePanel(user);

    // Show "Create Election" button for employees and admins
    if (user.role === "employee" || user.role === "admin") {
      const createBtn = document.getElementById("create-election-btn");
      if (createBtn) createBtn.classList.remove("hidden");
    }

    const elections = await fetchJson(`${API_BASE_URL}/elections`);
    if (!elections.length) {
      electionsListEl.innerHTML = `<p class="text-ink-400 col-span-3">No elections available.</p>`;
      return;
    }
    electionsListEl.innerHTML = elections.map(e => electionCard(e, user.role)).join("");
  } catch (err) {
    showAlert("Failed to load dashboard. Please try again.", "error");
    console.error(err);
  }
}

load();
