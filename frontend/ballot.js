import { renderNavbar, renderFooter, loadNavbarUser, showAlert } from "./components.js";

const API_BASE_URL = "/api";
const params = new URLSearchParams(window.location.search);
const electionId = params.get("id");
const form = document.getElementById("ballot-form");
const messageEl = document.getElementById("ballot-message");

// Initialize shared components
renderNavbar({ title: "Ballot", showBack: true, showUser: true });
renderFooter();

// Load user (ensures auth check + populates navbar)
loadNavbarUser();

function setMessage(text, isError = true) {
  messageEl.className = `mt-4 text-sm text-center font-medium ${isError ? "text-red-600" : "text-green-600"}`;
  messageEl.textContent = text;
}

function render(data) {
  // Update navbar title with election name
  const titleEl = document.querySelector("#app-navbar span.text-lg");
  if (titleEl) titleEl.textContent = data.election.name;

  const officeHtml = data.offices.map((office) => {
    const type = office.votes_allowed > 1 ? "checkbox" : "radio";
    const name = `office_${office.office_id}`;
    const candidates = office.candidates.map((c) => `
      <label class="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-indigo-50 hover:border-indigo-300 cursor-pointer transition">
        <input type="${type}" name="${name}" value="${c.candidate_id}"
          class="w-4 h-4 text-indigo-600 border-gray-300 focus:ring-indigo-500" />
        ${c.photo_url ? `<img src="${c.photo_url}" alt="${c.name}" class="w-10 h-10 rounded-full object-cover border border-gray-200" onerror="this.style.display='none'" />` : ""}
        <span class="text-gray-700 font-medium">${c.name}${c.title_position ? `<span class="text-xs text-gray-400 font-normal ml-1">${c.title_position}</span>` : ""}</span>
      </label>
    `).join("");
    return `
      <section class="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <h3 class="text-lg font-semibold text-gray-800 mb-1">${office.title}</h3>
        <p class="text-sm text-gray-400 mb-4">Select up to ${office.votes_allowed}</p>
        <div class="space-y-2">${candidates}</div>
      </section>
    `;
  }).join("");

  const initiativeHtml = data.initiatives.map((i) => {
    const options = i.options.map((o) => `
      <label class="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-indigo-50 hover:border-indigo-300 cursor-pointer transition">
        <input type="radio" name="initiative_${i.initiative_id}" value="${o.option_id}"
          class="w-4 h-4 text-indigo-600 border-gray-300 focus:ring-indigo-500" />
        <span class="text-gray-700 font-medium">${o.label}</span>
      </label>
    `).join("");
    return `
      <section class="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <h3 class="text-lg font-semibold text-gray-800 mb-4">${i.title}</h3>
        <div class="space-y-2">${options}</div>
      </section>
    `;
  }).join("");

  form.innerHTML = `
    ${officeHtml}
    ${initiativeHtml}
    <button class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-xl transition mt-2" type="submit">
      Submit Vote
    </button>
  `;
}

async function load() {
  try {
    // Check if user already voted — if so, block access
    const votedRes = await fetch(`${API_BASE_URL}/elections/${electionId}/voted`, { credentials: "include" });
    if (votedRes.ok) {
      const { voted } = await votedRes.json();
      if (voted) {
        form.innerHTML = "";
        setMessage("You have already voted in this election.", false);
        return;
      }
    }

    const response = await fetch(`${API_BASE_URL}/elections/${electionId}`, { credentials: "include" });
    if (!response.ok) throw new Error("Unable to load election.");
    const data = await response.json();
    render(data);
  } catch (error) {
    setMessage(error.message);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const officeVotes = [];
  const initiativeVotes = [];
  const officeGroups = [...new Set([...form.querySelectorAll("input[name^='office_']")].map((i) => i.name))];
  officeGroups.forEach((groupName) => {
    const officeId = Number(groupName.replace("office_", ""));
    const selected = [...form.querySelectorAll(`input[name='${groupName}']:checked`)].map((i) => Number(i.value));
    officeVotes.push({ office_id: officeId, candidate_ids: selected });
  });

  const initiativeGroups = [...new Set([...form.querySelectorAll("input[name^='initiative_']")].map((i) => i.name))];
  initiativeGroups.forEach((groupName) => {
    const selected = form.querySelector(`input[name='${groupName}']:checked`);
    if (!selected) return;
    initiativeVotes.push({
      initiative_id: Number(groupName.replace("initiative_", "")),
      option_id: Number(selected.value)
    });
  });

  try {
    const response = await fetch(`${API_BASE_URL}/elections/${electionId}/vote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ office_votes: officeVotes, initiative_votes: initiativeVotes })
    });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.message || "Vote failed.");
    }
    showAlert("Vote submitted successfully!", "success");
    setTimeout(() => {
      window.location.href = "./dashboard.html";
    }, 1200);
  } catch (error) {
    showAlert(error.message, "error");
  }
});

load();
