import { renderNavbar, renderFooter, loadNavbarUser, showAlert } from "./components.js";

const API = "/api";

renderNavbar({ title: "Voter Participation", showBack: true, showUser: true });
renderFooter();

const listEl = document.getElementById("participation-list");

async function load() {
  const user = await loadNavbarUser();
  if (!user) return;
  if (!["officer", "employee", "admin"].includes(user.role)) {
    window.location.href = "./dashboard.html";
    return;
  }

  try {
    const res = await fetch(`${API}/elections/participation`, { credentials: "include" });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.message || `Error ${res.status}`);
    }
    const elections = await res.json();

    if (!elections.length) {
      listEl.innerHTML = `<p class="text-gray-400 text-sm">No active elections in your society.</p>`;
      return;
    }

    // Fetch member vote status for all elections in parallel
    const memberData = await Promise.all(
      elections.map((e) =>
        fetch(`${API}/elections/${e.election_id}/members`, { credentials: "include" })
          .then((r) => r.ok ? r.json() : [])
          .catch(() => [])
      )
    );

    listEl.innerHTML = elections.map((e, i) => {
      const pct = e.total_eligible > 0
        ? Math.round((e.voted_count / e.total_eligible) * 100)
        : 0;

      const members = memberData[i] || [];
      const voted    = members.filter((m) => m.has_voted);
      const notVoted = members.filter((m) => !m.has_voted);

      const memberRow = (m, didVote) => `
        <li class="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
          <span class="text-sm text-gray-700">${m.member_name}</span>
          <span class="text-xs font-medium px-2 py-0.5 rounded-full ${didVote ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"}">
            ${didVote ? "Voted" : "Not voted"}
          </span>
        </li>`;

      return `
        <div class="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
          <div class="flex items-start justify-between gap-4 mb-4">
            <div>
              <h3 class="font-semibold text-gray-800">${e.name}</h3>
              <p class="text-xs text-gray-400 mt-0.5">${e.start_date || ""} &rarr; ${e.end_date || ""}</p>
            </div>
            <span class="text-2xl font-bold text-indigo-600 whitespace-nowrap">${pct}%</span>
          </div>

          <div class="w-full bg-gray-100 rounded-full h-3 mb-2">
            <div class="bg-indigo-500 h-3 rounded-full transition-all" style="width: ${pct}%"></div>
          </div>
          <p class="text-sm text-gray-500 mb-4">
            <span class="font-medium text-gray-700">${e.voted_count}</span> of
            <span class="font-medium text-gray-700">${e.total_eligible}</span> eligible members have voted
          </p>

          <!-- Member roster -->
          ${members.length ? `
          <ul class="mt-2 divide-y divide-gray-50">
            ${[...voted, ...notVoted].map((m) => memberRow(m, m.has_voted)).join("")}
          </ul>` : ""}
        </div>
      `;
    }).join("");
  } catch (err) {
    showAlert(err.message, "error");
    listEl.innerHTML = `<p class="text-red-500 text-sm">${err.message}</p>`;
  }
}

load();
