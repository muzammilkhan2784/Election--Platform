import { renderNavbar, renderFooter, loadNavbarUser, showAlert } from "./components.js";

const API = "/api";

renderNavbar({ title: "Admin Panel", showBack: true, showUser: true });
renderFooter();

let allUsers = [];
let allSocieties = [];

// ── Tab switching ──────────────────────────────────────────────────────────────

function switchTab(tab) {
  ["users", "societies", "assignments", "audit", "reports"].forEach((t) => {
    document.getElementById(`panel-${t}`).classList.toggle("hidden", t !== tab);
    const btn = document.getElementById(`tab-${t}`);
    btn.classList.toggle("border-brand-600", t === tab);
    btn.classList.toggle("text-brand-600", t === tab);
    btn.classList.toggle("border-transparent", t !== tab);
    btn.classList.toggle("text-ink-500", t !== tab);
  });
  if (tab === "assignments") loadAssignments();
  if (tab === "audit") loadAuditLogs();
  if (tab === "reports") loadReports();
}
window.switchTab = switchTab;

// ── Fetch helper ───────────────────────────────────────────────────────────────

async function api(url, options = {}) {
  const res = await fetch(API + url, { credentials: "include", ...options });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.message || `Error ${res.status}`);
  return body;
}

// ── Users ──────────────────────────────────────────────────────────────────────

// The roster is tens of thousands of rows, so the server pages it and this
// only ever holds the page on screen.
const USERS_PAGE_SIZE = 25;
const userQuery = { search: "", role: "", offset: 0, total: 0 };
let searchDebounce;

async function loadUsers() {
  const params = new URLSearchParams({
    limit: USERS_PAGE_SIZE,
    offset: userQuery.offset,
  });
  if (userQuery.search) params.set("search", userQuery.search);
  if (userQuery.role) params.set("role", userQuery.role);

  const result = await api(`/users?${params}`);
  allUsers = result.users;
  userQuery.total = result.total;

  const tbody = document.getElementById("users-table-body");

  if (!allUsers.length) {
    tbody.innerHTML = `
      <tr><td colspan="6" class="py-10 text-center text-ink-500 text-[14px]">
        No users match that search.
      </td></tr>`;
    renderUsersPager();
    return;
  }

  tbody.innerHTML = allUsers.map((u) => `
    <tr>
      <td class="text-ink-800 font-medium">${u.first_name || ""} ${u.last_name || ""}</td>
      <td class="text-ink-500">${u.email}</td>
      <td>
        <span class="px-2 py-0.5 rounded-full text-[11.5px] font-semibold border ${roleColor(u.role)}">${u.role}</span>
      </td>
      <td class="text-ink-600 max-w-[220px] truncate" title="${u.society_name || ""}">${u.society_name || "\u2014"}</td>
      <td>
        <span class="px-2 py-0.5 rounded-full text-[11.5px] font-semibold border ${u.status === "active" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-red-50 text-red-600 border-red-200"}">${u.status}</span>
      </td>
      <td>
        ${u.status === "active"
          ? `<button onclick="disableUser(${u.user_id})" class="text-[13px] font-medium text-red-600 hover:underline">Disable</button>`
          : `<button onclick="enableUser(${u.user_id})" class="text-[13px] font-medium text-emerald-700 hover:underline">Enable</button>`
        }
      </td>
    </tr>
  `).join("");

  renderUsersPager();
}

function renderUsersPager() {
  const el = document.getElementById("users-pager");
  if (!el) return;
  const { offset, total } = userQuery;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + USERS_PAGE_SIZE, total);
  const canPrev = offset > 0;
  const canNext = to < total;

  const btn = (label, enabled, action) => `
    <button ${enabled ? `onclick="${action}"` : "disabled"}
      class="px-3 py-1.5 rounded-lg border text-[13px] font-medium transition-colors
        ${enabled
          ? "border-ink-200 text-ink-700 hover:bg-ink-50 hover:border-ink-300"
          : "border-ink-100 text-ink-300 cursor-not-allowed"}">${label}</button>`;

  el.innerHTML = `
    <p class="text-[13px] text-ink-500 tabular">
      ${from.toLocaleString()}\u2013${to.toLocaleString()} of ${total.toLocaleString()}
    </p>
    <div class="flex gap-2">
      ${btn("Previous", canPrev, "usersPage(-1)")}
      ${btn("Next", canNext, "usersPage(1)")}
    </div>`;
}

window.usersPage = (direction) => {
  userQuery.offset = Math.max(0, userQuery.offset + direction * USERS_PAGE_SIZE);
  loadUsers();
};

window.onUsersSearch = (value) => {
  // Debounced so typing does not fire a query per keystroke.
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    userQuery.search = value;
    userQuery.offset = 0;
    loadUsers();
  }, 250);
};

window.onUsersRoleFilter = (value) => {
  userQuery.role = value;
  userQuery.offset = 0;
  loadUsers();
};

function roleColor(role) {
  return {
    admin: "bg-red-50 text-red-700 border-red-200",
    employee: "bg-brand-50 text-brand-700 border-brand-200",
    officer: "bg-purple-50 text-purple-700 border-purple-200",
    member: "bg-emerald-50 text-emerald-700 border-emerald-200",
  }[role] || "bg-ink-100 text-ink-500 border-ink-200";
}

window.disableUser = async (userId) => {
  try {
    await api(`/users/${userId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "disabled" }) });
    showAlert("User disabled.", "success");
    loadUsers();
  } catch (e) { showAlert(e.message, "error"); }
};

window.enableUser = async (userId) => {
  try {
    await api(`/users/${userId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "active" }) });
    showAlert("User enabled.", "success");
    loadUsers();
  } catch (e) { showAlert(e.message, "error"); }
};

window.showCreateUser = () => document.getElementById("create-user-form").classList.remove("hidden");
window.hideCreateUser = () => document.getElementById("create-user-form").classList.add("hidden");

window.createUser = async () => {
  const errEl = document.getElementById("create-user-error");
  errEl.classList.add("hidden");
  const data = {
    first_name: document.getElementById("new-first-name").value.trim(),
    last_name:  document.getElementById("new-last-name").value.trim(),
    email:      document.getElementById("new-email").value.trim(),
    password:   document.getElementById("new-password").value,
    role:       document.getElementById("new-role").value,
    society_id: document.getElementById("new-society").value || null,
  };
  try {
    await api("/users", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    showAlert("User created.", "success");
    hideCreateUser();
    loadUsers();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove("hidden");
  }
};

// ── Societies ──────────────────────────────────────────────────────────────────

async function loadSocieties() {
  allSocieties = await api("/societies");
  const list = document.getElementById("societies-list");
  list.innerHTML = allSocieties.map((s) => `
    <div class="bg-white rounded-xl border border-ink-100 shadow-sm p-5">
      <h3 class="font-semibold text-ink-800">${s.name}</h3>
      <p class="text-sm text-ink-500 mt-1">${s.description || "No description"}</p>
    </div>
  `).join("");

  // Populate society dropdowns
  const opts = allSocieties.map((s) => `<option value="${s.society_id}">${s.name}</option>`).join("");
  document.getElementById("new-society").innerHTML = `<option value="">Select Society (optional)</option>` + opts;
  document.getElementById("assign-society").innerHTML = `<option value="">Select Society</option>` + opts;
}

window.showCreateSociety = () => document.getElementById("create-society-form").classList.remove("hidden");
window.hideCreateSociety = () => document.getElementById("create-society-form").classList.add("hidden");

window.createSociety = async () => {
  const errEl = document.getElementById("create-society-error");
  errEl.classList.add("hidden");
  const data = {
    name:        document.getElementById("new-society-name").value.trim(),
    description: document.getElementById("new-society-desc").value.trim(),
  };
  try {
    await api("/societies", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    showAlert("Society created.", "success");
    hideCreateSociety();
    loadSocieties();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove("hidden");
  }
};

// ── Assignments ────────────────────────────────────────────────────────────────

async function loadAssignments() {
  const assignments = await api("/societies/assignments");
  const tbody = document.getElementById("assignments-table-body");
  tbody.innerHTML = assignments.map((a) => `
    <tr class="hover:bg-ink-50">
      <td class="text-ink-800">${a.employee_name}</td>
      <td class="text-ink-600 max-w-[260px] truncate" title="${a.society_name}">${a.society_name}</td>
      <td>
        <button onclick="unassign(${a.user_id}, ${a.society_id})" class="text-xs text-red-500 hover:underline">Remove</button>
      </td>
    </tr>
  `).join("");

  // Employees come from a dedicated endpoint: the users table is paged now,
  // so filtering the page on screen would miss most of them.
  const employees = await api("/users/employees");
  document.getElementById("assign-employee").innerHTML =
    `<option value="">Select employee</option>` +
    employees.map((u) => `<option value="${u.user_id}">${u.first_name} ${u.last_name}</option>`).join("");
}

window.assignEmployee = async () => {
  const errEl = document.getElementById("assign-error");
  errEl.classList.add("hidden");
  const userId = document.getElementById("assign-employee").value;
  const societyId = document.getElementById("assign-society").value;
  if (!userId || !societyId) {
    errEl.textContent = "Select both an employee and a society.";
    errEl.classList.remove("hidden");
    return;
  }
  try {
    await api(`/users/${userId}/societies`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ society_id: Number(societyId) }) });
    showAlert("Assigned.", "success");
    loadAssignments();
  } catch (e) { showAlert(e.message, "error"); }
};

window.unassign = async (userId, societyId) => {
  try {
    await api(`/users/${userId}/societies/${societyId}`, { method: "DELETE" });
    showAlert("Removed.", "success");
    loadAssignments();
  } catch (e) { showAlert(e.message, "error"); }
};

// ── Audit Logs ─────────────────────────────────────────────────────────────────

async function loadAuditLogs() {
  try {
    const data = await api("/audit");

    const actionLabel = (a) => ({
      election_created:  "Election Created",
      ballot_saved:      "Ballot Saved",
      election_published:"Election Published",
    }[a] || a);

    document.getElementById("audit-ballot-body").innerHTML = data.ballot_events.length
      ? data.ballot_events.map((r) => `
          <tr class="hover:bg-ink-50">
            <td class="text-ink-400 text-xs whitespace-nowrap">${r.edited_at.slice(0, 19).replace("T", " ")}</td>
            <td class="text-ink-700">${r.user_name}<br><span class="text-xs text-ink-400">${r.user_email}</span></td>
            <td class="text-ink-600">${r.election_name}</td>
            <td><span class="px-2 py-0.5 rounded-full text-xs font-medium bg-brand-50 text-brand-700">${actionLabel(r.action)}</span></td>
            <td class="text-ink-400 text-xs">${r.details || "—"}</td>
          </tr>`).join("")
      : `<tr><td colspan="5" class="px-4 py-4 text-ink-400 text-sm">No ballot activity yet.</td></tr>`;

    document.getElementById("audit-votes-body").innerHTML = data.vote_events.length
      ? data.vote_events.map((r) => `
          <tr class="hover:bg-ink-50">
            <td class="text-ink-400 text-xs whitespace-nowrap">${r.submitted_at.slice(0, 19).replace("T", " ")}</td>
            <td class="text-ink-700">${r.user_name}<br><span class="text-xs text-ink-400">${r.user_email}</span></td>
            <td class="text-ink-600">${r.election_name}</td>
          </tr>`).join("")
      : `<tr><td colspan="3" class="px-4 py-4 text-ink-400 text-sm">No votes cast yet.</td></tr>`;
  } catch (e) { showAlert(e.message, "error"); }
}

// ── Reports ────────────────────────────────────────────────────────────────────

async function loadReports() {
  try {
    const data = await api("/reports");

    // System stats cards
    const sys = data.system_stats;
    const cards = [
      { label: "Active Elections",    value: sys.active_elections },
      { label: "Draft Elections",     value: sys.draft_elections },
      { label: "Completed Elections", value: sys.completed_elections },
      { label: "Total Users",         value: sys.total_users },
      { label: "Active Users",        value: sys.active_users },
      { label: "Members",             value: sys.members },
      { label: "Officers",            value: sys.officers },
      { label: "Employees",           value: sys.employees },
    ];
    document.getElementById("system-stats-grid").innerHTML = cards.map((c) => `
      <div class="bg-white rounded-xl border border-ink-100 shadow-sm p-4 text-center">
        <p class="text-2xl font-bold text-brand-600">${c.value}</p>
        <p class="text-xs text-ink-500 mt-1">${c.label}</p>
      </div>`).join("");

    // Society stats table
    document.getElementById("society-stats-body").innerHTML = data.society_stats.length
      ? data.society_stats.map((s) => `
          <tr class="hover:bg-ink-50">
            <td class="font-medium text-ink-800">${s.name}</td>
            <td class="text-ink-600">${s.member_count}</td>
            <td class="text-ink-600">${s.total_elections}</td>
            <td class="text-ink-600">${s.active_elections}</td>
            <td class="text-ink-600">${s.completed_elections}</td>
            <td class="text-ink-600">${s.avg_turnout}</td>
          </tr>`).join("")
      : `<tr><td colspan="6" class="px-4 py-4 text-ink-400 text-sm">No society data yet.</td></tr>`;
  } catch (e) { showAlert(e.message, "error"); }
}

// ── Init ───────────────────────────────────────────────────────────────────────

async function init() {
  const user = await loadNavbarUser();
  if (!user) return;
  if (user.role !== "admin") {
    window.location.href = "./dashboard.html";
    return;
  }
  await Promise.all([loadUsers(), loadSocieties()]);
  const tab = new URLSearchParams(window.location.search).get("tab");
  if (tab === "societies" || tab === "assignments" || tab === "audit" || tab === "reports") switchTab(tab);
}

init();
