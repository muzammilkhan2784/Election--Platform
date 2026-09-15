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
      <div class="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <div class="flex items-center gap-3 mb-4">
          <span class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-red-100 text-red-600 text-lg font-bold">A</span>
          <div>
            <h3 class="font-semibold text-gray-800">Admin Panel</h3>
            <p class="text-sm text-gray-500">System administration tools</p>
          </div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <a href="./admin.html?tab=users" class="flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-200 hover:bg-indigo-50 hover:border-indigo-200 transition text-center">
            <span class="text-2xl">&#128101;</span>
            <span class="text-sm font-medium text-gray-700">Manage Users</span>
          </a>
          <a href="./admin.html?tab=societies" class="flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-200 hover:bg-indigo-50 hover:border-indigo-200 transition text-center">
            <span class="text-2xl">&#127963;</span>
            <span class="text-sm font-medium text-gray-700">Societies</span>
          </a>
          <a href="./admin.html?tab=audit" class="flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-200 hover:bg-indigo-50 hover:border-indigo-200 transition text-center">
            <span class="text-2xl">&#128202;</span>
            <span class="text-sm font-medium text-gray-700">Audit Logs</span>
          </a>
          <a href="./admin.html?tab=reports" class="flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-200 hover:bg-indigo-50 hover:border-indigo-200 transition text-center">
            <span class="text-2xl">&#128200;</span>
            <span class="text-sm font-medium text-gray-700">Reports</span>
          </a>
        </div>
      </div>`,

    officer: `
      <div class="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <div class="flex items-center gap-3 mb-4">
          <span class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-purple-100 text-purple-600 text-lg font-bold">O</span>
          <div>
            <h3 class="font-semibold text-gray-800">Officer Tools</h3>
            <p class="text-sm text-gray-500">Election oversight &amp; participation</p>
          </div>
        </div>
        <div class="grid grid-cols-1 gap-3">
          <a href="./participation.html" class="flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-200 hover:bg-purple-50 hover:border-purple-200 transition text-center">
            <span class="text-2xl">&#128200;</span>
            <span class="text-sm font-medium text-gray-700">Voter Participation</span>
          </a>
        </div>
      </div>`,

    employee: `
      <div class="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <div class="flex items-center gap-3 mb-4">
          <span class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-blue-100 text-blue-600 text-lg font-bold">E</span>
          <div>
            <h3 class="font-semibold text-gray-800">Employee Dashboard</h3>
            <p class="text-sm text-gray-500">Your assigned societies &amp; tasks</p>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <a href="./participation.html" class="flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition text-center">
            <span class="text-2xl">&#128200;</span>
            <span class="text-sm font-medium text-gray-700">Participation</span>
          </a>
          <a href="./pending-tasks.html" class="flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition text-center">
            <span class="text-2xl">&#128203;</span>
            <span class="text-sm font-medium text-gray-700">Pending Tasks</span>
          </a>
        </div>
      </div>`,

    member: `
      <div class="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <div class="flex items-center gap-3 mb-4">
          <span class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-green-100 text-green-600 text-lg font-bold">M</span>
          <div>
            <h3 class="font-semibold text-gray-800">Welcome Back!</h3>
            <p class="text-sm text-gray-500">Your voting hub</p>
          </div>
        </div>
        <p class="text-gray-600 text-sm">Browse the elections below to cast your vote or check results. Your participation matters!</p>
      </div>`,
  };

  rolePanelEl.innerHTML = panels[user.role] || "";
}

/* ------------------------------------------------------------------ */
/*  Election cards                                                    */
/* ------------------------------------------------------------------ */

function electionCard(e, role) {
  const statusColors = {
    active:    "bg-green-100 text-green-700",
    draft:     "bg-amber-100 text-amber-700",
    completed: "bg-gray-100 text-gray-500",
  };
  const badge = statusColors[e.status] || "bg-gray-100 text-gray-500";

  // Build action buttons based on role + election status
  const buttons = [];

  if (role === "employee" || role === "admin") {
    // Employees/admins can edit the ballot while draft
    if (e.status === "draft") {
      buttons.push(`<a class="flex-1 text-center bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2 rounded-lg transition"
         href="./ballot-editor.html?id=${e.election_id}">Edit Ballot</a>`);
    }
    // Results visible once active or completed
    if (e.status === "active" || e.status === "completed") {
      buttons.push(`<a class="flex-1 text-center border border-gray-200 hover:bg-gray-50 text-gray-600 text-sm font-medium py-2 rounded-lg transition"
         href="./results.html?id=${e.election_id}">View Results</a>`);
    }
  } else if (role === "officer") {
    // Officers can vote on active elections
    if (e.status === "active") {
      buttons.push(`<a class="flex-1 text-center bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2 rounded-lg transition"
         href="./ballot.html?id=${e.election_id}">Vote</a>`);
    }
    // Officers can only see results of completed elections
    if (e.status === "completed") {
      buttons.push(`<a class="flex-1 text-center border border-gray-200 hover:bg-gray-50 text-gray-600 text-sm font-medium py-2 rounded-lg transition"
         href="./results.html?id=${e.election_id}">View Results</a>`);
    }
  } else {
    // Members can only vote on active elections
    if (e.status === "active") {
      buttons.push(`<a class="flex-1 text-center bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2 rounded-lg transition"
         href="./ballot.html?id=${e.election_id}">Vote</a>`);
    }
  }

  const buttonsHtml = buttons.length
    ? `<div class="flex gap-2 mt-auto pt-2">${buttons.join("")}</div>`
    : "";

  return `
    <article class="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition p-5 flex flex-col gap-3">
      <div class="flex items-start justify-between gap-2">
        <h3 class="font-semibold text-gray-800 text-base leading-snug">${e.name}</h3>
        <span class="text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${badge}">${e.status}</span>
      </div>
      <div>
        <p class="text-sm text-gray-500">${e.society_name}</p>
        <p class="text-xs text-gray-400 mt-0.5">${e.start_date || ""} &rarr; ${e.end_date || ""}</p>
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
      electionsListEl.innerHTML = `<p class="text-gray-400 col-span-3">No elections available.</p>`;
      return;
    }
    electionsListEl.innerHTML = elections.map(e => electionCard(e, user.role)).join("");
  } catch (err) {
    showAlert("Failed to load dashboard. Please try again.", "error");
    console.error(err);
  }
}

load();
