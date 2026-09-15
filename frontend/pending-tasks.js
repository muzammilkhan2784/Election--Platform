import { renderNavbar, renderFooter, loadNavbarUser, showAlert } from "./components.js";

const API = "/api";

renderNavbar({ title: "Pending Tasks", showBack: true, showUser: true });
renderFooter();

const listEl = document.getElementById("tasks-list");

async function load() {
  const user = await loadNavbarUser();
  if (!user) return;
  if (user.role !== "employee") {
    window.location.href = "./dashboard.html";
    return;
  }

  try {
    const res = await fetch(`${API}/elections/pending`, { credentials: "include" });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.message || `Error ${res.status}`);
    }
    const tasks = await res.json();

    if (!tasks.length) {
      listEl.innerHTML = `<p class="text-gray-400 text-sm">No pending tasks. All draft elections have been handled.</p>`;
      return;
    }

    listEl.innerHTML = tasks.map((t) => `
      <div class="bg-white rounded-xl border border-gray-100 shadow-sm p-5 flex items-center justify-between gap-4">
        <div>
          <h3 class="font-semibold text-gray-800">${t.name}</h3>
          <p class="text-xs text-gray-400 mt-0.5">${t.society_name} &bull; ${t.start_date || "TBD"} &rarr; ${t.end_date || "TBD"}</p>
          <span class="inline-block mt-2 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">Draft</span>
        </div>
        <a href="./ballot-editor.html?id=${t.election_id}"
          class="shrink-0 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition">
          Edit Ballot
        </a>
      </div>
    `).join("");
  } catch (err) {
    showAlert(err.message, "error");
    listEl.innerHTML = `<p class="text-red-500 text-sm">${err.message}</p>`;
  }
}

load();
