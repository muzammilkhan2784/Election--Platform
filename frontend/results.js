import { renderNavbar, renderFooter, loadNavbarUser, showAlert } from "./components.js";

const API_BASE_URL = "/api";
const params = new URLSearchParams(window.location.search);
const electionId = params.get("id");

const officeResults = document.getElementById("office-results");
const initiativeResults = document.getElementById("initiative-results");

// Initialize shared components
renderNavbar({ title: "Election Results", showBack: true, showUser: true });
renderFooter();

// Load user (ensures auth check + populates navbar)
loadNavbarUser();

function groupBy(rows, key) {
  return rows.reduce((acc, row) => {
    const groupKey = row[key];
    if (!acc[groupKey]) acc[groupKey] = [];
    acc[groupKey].push(row);
    return acc;
  }, {});
}

async function loadResults() {
  const response = await fetch(`${API_BASE_URL}/elections/${electionId}/results`, {
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error("Could not load results.");
  }
  const data = await response.json();

  officeResults.innerHTML = data.offices.map((office) => `
    <article class="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
      <h3 class="font-semibold text-gray-800 text-base mb-4">${office.office_title}</h3>
      <div class="space-y-2">
        ${office.candidates.map((c) => `
          <div class="flex justify-between items-center py-2 border-b border-gray-50 last:border-0">
            <span class="text-gray-600">${c.candidate_name}</span>
            <span class="font-bold text-indigo-600">${c.vote_count} votes</span>
          </div>
        `).join("")}
      </div>
    </article>
  `).join("");

  initiativeResults.innerHTML = data.initiatives.map((initiative) => `
    <article class="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
      <h3 class="font-semibold text-gray-800 text-base mb-4">${initiative.initiative_title}</h3>
      <div class="space-y-2">
        ${initiative.options.map((o) => `
          <div class="flex justify-between items-center py-2 border-b border-gray-50 last:border-0">
            <span class="text-gray-600">${o.option_label}</span>
            <span class="font-bold text-indigo-600">${o.vote_count} votes</span>
          </div>
        `).join("")}
      </div>
    </article>
  `).join("");
}

loadResults().catch((error) => {
  showAlert(error.message, "error");
  officeResults.innerHTML = `<p class="text-red-500 text-sm">${error.message}</p>`;
});
