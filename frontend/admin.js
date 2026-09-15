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
    btn.classList.toggle("border-indigo-600", t === tab);
    btn.classList.toggle("text-indigo-600", t === tab);
    btn.classList.toggle("border-transparent", t !== tab);
    btn.classList.toggle("text-gray-500", t !== tab);
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

async function loadUsers() {
  allUsers = await api("/users");
  const tbody = document.getElementById("users-table-body");
  tbody.innerHTML = allUsers.map((u) => `
    <tr class="hover:bg-gray-50">
      <td class="px-4 py-3 text-gray-800">${u.first_name || ""} ${u.last_name || ""}</td>
      <td class="px-4 py-3 text-gray-500">${u.email}</td>
      <td class="px-4 py-3">
        <span class="px-2 py-0.5 rounded-full text-xs font-medium ${roleColor(u.role)}">${u.role}</span>
      </td>
      <td class="px-4 py-3 text-gray-500">${u.society_name || "—"}</td>
      <td class="px-4 py-3">
        <span class="px-2 py-0.5 rounded-full text-xs font-medium ${u.status === "active" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}">${u.status}</span>
      </td>
      <td class="px-4 py-3">
        ${u.status === "active"
          ? `<button onclick="disableUser(${u.user_id})" class="text-xs text-red-500 hover:underline">Disable</button>`
          : `<button onclick="enableUser(${u.user_id})" class="text-xs text-green-600 hover:underline">Enable</button>`
        }
      </td>
    </tr>
  `).join("");
}

function roleColor(role) {
  return { admin: "bg-red-100 text-red-700", employee: "bg-blue-100 text-blue-700",
           officer: "bg-purple-100 text-purple-700", member: "bg-green-100 text-green-700" }[role] || "bg-gray-100 text-gray-500";
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
    <div class="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <h3 class="font-semibold text-gray-800">${s.name}</h3>
      <p class="text-sm text-gray-500 mt-1">${s.description || "No description"}</p>
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
    <tr class="hover:bg-gray-50">
      <td class="px-4 py-3 text-gray-800">${a.employee_name}</td>
      <td class="px-4 py-3 text-gray-500">${a.society_name}</td>
      <td class="px-4 py-3">
        <button onclick="unassign(${a.user_id}, ${a.society_id})" class="text-xs text-red-500 hover:underline">Remove</button>
      </td>
    </tr>
  `).join("");

  // Populate employee dropdown with only employees
  const employees = allUsers.filter((u) => u.role === "employee");
  document.getElementById("assign-employee").innerHTML =
    `<option value="">Select Employee</option>` +
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
          <tr class="hover:bg-gray-50">
            <td class="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">${r.edited_at.slice(0, 19).replace("T", " ")}</td>
            <td class="px-4 py-3 text-gray-700">${r.user_name}<br><span class="text-xs text-gray-400">${r.user_email}</span></td>
            <td class="px-4 py-3 text-gray-600">${r.election_name}</td>
            <td class="px-4 py-3"><span class="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700">${actionLabel(r.action)}</span></td>
            <td class="px-4 py-3 text-gray-400 text-xs">${r.details || "—"}</td>
          </tr>`).join("")
      : `<tr><td colspan="5" class="px-4 py-4 text-gray-400 text-sm">No ballot activity yet.</td></tr>`;

    document.getElementById("audit-votes-body").innerHTML = data.vote_events.length
      ? data.vote_events.map((r) => `
          <tr class="hover:bg-gray-50">
            <td class="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">${r.submitted_at.slice(0, 19).replace("T", " ")}</td>
            <td class="px-4 py-3 text-gray-700">${r.user_name}<br><span class="text-xs text-gray-400">${r.user_email}</span></td>
            <td class="px-4 py-3 text-gray-600">${r.election_name}</td>
          </tr>`).join("")
      : `<tr><td colspan="3" class="px-4 py-4 text-gray-400 text-sm">No votes cast yet.</td></tr>`;
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
      <div class="bg-white rounded-xl border border-gray-100 shadow-sm p-4 text-center">
        <p class="text-2xl font-bold text-indigo-600">${c.value}</p>
        <p class="text-xs text-gray-500 mt-1">${c.label}</p>
      </div>`).join("");

    // Society stats table
    document.getElementById("society-stats-body").innerHTML = data.society_stats.length
      ? data.society_stats.map((s) => `
          <tr class="hover:bg-gray-50">
            <td class="px-4 py-3 font-medium text-gray-800">${s.name}</td>
            <td class="px-4 py-3 text-gray-600">${s.member_count}</td>
            <td class="px-4 py-3 text-gray-600">${s.total_elections}</td>
            <td class="px-4 py-3 text-gray-600">${s.active_elections}</td>
            <td class="px-4 py-3 text-gray-600">${s.completed_elections}</td>
            <td class="px-4 py-3 text-gray-600">${s.avg_turnout}</td>
          </tr>`).join("")
      : `<tr><td colspan="6" class="px-4 py-4 text-gray-400 text-sm">No society data yet.</td></tr>`;
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
