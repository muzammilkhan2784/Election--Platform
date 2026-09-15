const API = "/api";
const params = new URLSearchParams(window.location.search);
let electionId = params.get("id") ? Number(params.get("id")) : null;
let electionStatus = "draft";
let readOnly = false;

const pageTitle        = document.getElementById("page-title");
const nameInput        = document.getElementById("election-name");
const societySelect    = document.getElementById("society-select");
const societyWrapper   = document.getElementById("society-wrapper");
const startInput       = document.getElementById("start-date");
const endInput         = document.getElementById("end-date");
const descInput        = document.getElementById("description");
const createBtn        = document.getElementById("create-election-btn");
const createBtnWrapper = document.getElementById("create-election-btn-wrapper");
const ballotSection    = document.getElementById("ballot-section");
const statusBanner     = document.getElementById("election-status-banner");
const officesList      = document.getElementById("offices-list");
const initiativesList  = document.getElementById("initiatives-list");
const addOfficeBtn     = document.getElementById("add-office-btn");
const addInitiativeBtn = document.getElementById("add-initiative-btn");
const saveBtn          = document.getElementById("save-btn");
const publishBtn       = document.getElementById("publish-btn");
const msgEl            = document.getElementById("action-message");

// ── Utilities ─────────────────────────────────────────────────────────────────

async function api(method, path, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.message || `Error ${res.status}`);
  return json;
}

function setMessage(text, isError = false) {
  msgEl.textContent = text;
  msgEl.className = `text-sm font-medium text-center min-h-[20px] ${isError ? "text-red-600" : "text-green-600"}`;
}

function makeSectionEl(html) {
  const div = document.createElement("div");
  div.innerHTML = html.trim();
  return div.firstElementChild;
}

// ── Office builder ────────────────────────────────────────────────────────────

function officeHtml(office = null, idx) {
  const title        = office?.title ?? "";
  const votesAllowed = office?.votes_allowed ?? 1;
  const writeIn      = office?.allow_write_in ?? false;
  const candidates   = office?.candidates ?? [];

  const candidatesHtml = candidates.map((c, ci) => candidateRowHtml(c, ci)).join("");

  return `
  <div class="office-block border border-gray-200 rounded-xl p-4 space-y-3 bg-gray-50" data-office="${idx}">
    <div class="flex items-center justify-between gap-2">
      <input type="text" placeholder="Office title (e.g. President)" value="${title}"
        class="office-title flex-1 px-3 py-2 border border-gray-300 rounded-lg text-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      <button class="remove-office text-red-400 hover:text-red-600 text-sm font-medium transition">Remove</button>
    </div>
    <div class="flex gap-4 flex-wrap items-center">
      <label class="text-sm text-gray-600 flex items-center gap-2">
        Votes allowed:
        <input type="number" min="1" value="${votesAllowed}"
          class="votes-allowed w-16 px-2 py-1 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      </label>
      <label class="text-sm text-gray-600 flex items-center gap-2 cursor-pointer">
        <input type="checkbox" class="write-in-toggle" ${writeIn ? "checked" : ""} />
        Allow write-in
      </label>
    </div>
    <div class="candidates-list space-y-2">${candidatesHtml}</div>
    <button class="add-candidate text-sm text-indigo-600 hover:text-indigo-800 font-medium transition">+ Add Candidate</button>
  </div>`;
}

function candidateRowHtml(candidate = null, idx) {
  const name  = candidate?.name ?? "";
  const title = candidate?.title_position ?? "";
  const bio   = candidate?.biography ?? "";
  const photo = candidate?.photo_url ?? "";
  return `
  <div class="candidate-row flex gap-2 items-start" data-candidate="${idx}">
    <div class="flex-1 grid grid-cols-1 sm:grid-cols-4 gap-2">
      <input type="text" placeholder="Candidate name" value="${name}"
        class="cand-name px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      <input type="text" placeholder="Title/Position" value="${title}"
        class="cand-title px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      <input type="text" placeholder="Biography (optional)" value="${bio}"
        class="cand-bio px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      <input type="url" placeholder="Photo URL (optional)" value="${photo}"
        class="cand-photo px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
    </div>
    <button class="remove-candidate text-red-300 hover:text-red-500 text-lg leading-none mt-2 transition">×</button>
  </div>`;
}

function addOffice(office = null) {
  const idx = officesList.children.length;
  const el  = makeSectionEl(officeHtml(office, idx));

  el.querySelector(".remove-office").addEventListener("click", () => el.remove());

  el.querySelector(".add-candidate").addEventListener("click", () => {
    const list = el.querySelector(".candidates-list");
    const row  = makeSectionEl(candidateRowHtml(null, list.children.length));
    row.querySelector(".remove-candidate").addEventListener("click", () => row.remove());
    list.appendChild(row);
  });

  el.querySelectorAll(".remove-candidate").forEach(btn => {
    btn.addEventListener("click", () => btn.closest(".candidate-row").remove());
  });

  officesList.appendChild(el);
}

// ── Initiative builder ────────────────────────────────────────────────────────

function initiativeHtml(initiative = null, idx) {
  const title   = initiative?.title ?? "";
  const desc    = initiative?.description ?? "";
  const options = initiative?.options ?? [];
  const optsHtml = options.map((o, oi) => optionRowHtml(o, oi)).join("");

  return `
  <div class="initiative-block border border-gray-200 rounded-xl p-4 space-y-3 bg-gray-50" data-initiative="${idx}">
    <div class="flex items-center justify-between gap-2">
      <input type="text" placeholder="Initiative title (e.g. Bylaw Amendment 1)" value="${title}"
        class="initiative-title flex-1 px-3 py-2 border border-gray-300 rounded-lg text-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      <button class="remove-initiative text-red-400 hover:text-red-600 text-sm font-medium transition">Remove</button>
    </div>
    <textarea placeholder="Description (optional)" class="initiative-desc w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" rows="2">${desc}</textarea>
    <div class="options-list space-y-2">${optsHtml}</div>
    <button class="add-option text-sm text-indigo-600 hover:text-indigo-800 font-medium transition">+ Add Option</button>
  </div>`;
}

function optionRowHtml(option = null, idx) {
  const label = option?.label ?? "";
  return `
  <div class="option-row flex gap-2 items-center" data-option="${idx}">
    <input type="text" placeholder="Option (e.g. Yes / No / Abstain)" value="${label}"
      class="option-label flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
    <button class="remove-option text-red-300 hover:text-red-500 text-lg leading-none transition">×</button>
  </div>`;
}

function addInitiative(initiative = null) {
  const idx = initiativesList.children.length;
  const el  = makeSectionEl(initiativeHtml(initiative, idx));

  el.querySelector(".remove-initiative").addEventListener("click", () => el.remove());

  el.querySelector(".add-option").addEventListener("click", () => {
    const list = el.querySelector(".options-list");
    const row  = makeSectionEl(optionRowHtml(null, list.children.length));
    row.querySelector(".remove-option").addEventListener("click", () => row.remove());
    list.appendChild(row);
  });

  el.querySelectorAll(".remove-option").forEach(btn => {
    btn.addEventListener("click", () => btn.closest(".option-row").remove());
  });

  initiativesList.appendChild(el);
}

// ── Read form state ───────────────────────────────────────────────────────────

function readBallot() {
  const offices = [...officesList.querySelectorAll(".office-block")].map(block => ({
    title:         block.querySelector(".office-title").value.trim(),
    votes_allowed: Number(block.querySelector(".votes-allowed").value),
    allow_write_in: block.querySelector(".write-in-toggle").checked,
    candidates: [...block.querySelectorAll(".candidate-row")].map(row => ({
      name:           row.querySelector(".cand-name").value.trim(),
      title_position: row.querySelector(".cand-title").value.trim(),
      biography:      row.querySelector(".cand-bio").value.trim(),
      photo_url:      row.querySelector(".cand-photo").value.trim(),
    })).filter(c => c.name),
  }));

  const initiatives = [...initiativesList.querySelectorAll(".initiative-block")].map(block => ({
    title:       block.querySelector(".initiative-title").value.trim(),
    description: block.querySelector(".initiative-desc").value.trim(),
    options: [...block.querySelectorAll(".option-row")].map(row => ({
      label: row.querySelector(".option-label").value.trim(),
    })).filter(o => o.label),
  }));

  return { offices, initiatives };
}

// ── Show / hide ballot section ────────────────────────────────────────────────

function showBallotSection(election) {
  electionStatus = election.status;
  readOnly = election.status !== "draft";

  ballotSection.classList.remove("hidden");
  pageTitle.textContent = election.name || "Ballot Editor";

  // Lock the election details fields once created
  nameInput.disabled = true;
  societySelect.disabled = true;
  startInput.disabled = true;
  endInput.disabled = true;
  descInput.disabled = true;
  createBtnWrapper.classList.add("hidden");

  if (readOnly) {
    statusBanner.textContent = `This election is ${electionStatus}. The ballot can no longer be edited.`;
    statusBanner.classList.remove("hidden");
    addOfficeBtn.classList.add("hidden");
    addInitiativeBtn.classList.add("hidden");
    saveBtn.classList.add("hidden");
    publishBtn.classList.add("hidden");
  }
}

function populateBallot(data) {
  officesList.innerHTML = "";
  initiativesList.innerHTML = "";
  data.offices.forEach(o => addOffice(o));
  data.initiatives.forEach(i => addInitiative(i));
}

// ── Load societies dropdown ───────────────────────────────────────────────────

async function loadSocieties() {
  try {
    const societies = await api("GET", "/societies");
    societySelect.innerHTML = `<option value="">Select a society...</option>` +
      societies.map(s => `<option value="${s.society_id}">${s.name}</option>`).join("");
  } catch {
    societySelect.innerHTML = `<option value="">Failed to load societies</option>`;
  }
}

// ── Create election ───────────────────────────────────────────────────────────

createBtn.addEventListener("click", async () => {
  const name       = nameInput.value.trim();
  const society_id = Number(societySelect.value);
  const start_date = startInput.value;
  const end_date   = endInput.value;

  if (!name || !society_id || !start_date || !end_date) {
    setMessage("Please fill in all required fields.", true);
    return;
  }

  try {
    createBtn.disabled = true;
    const election = await api("POST", "/elections", {
      name, society_id, start_date, end_date,
      description: descInput.value.trim(),
    });
    electionId = election.election_id;
    history.replaceState(null, "", `?id=${electionId}`);
    showBallotSection(election);
    setMessage("Election created. Now build the ballot below.");
  } catch (err) {
    setMessage(err.message, true);
  } finally {
    createBtn.disabled = false;
  }
});

// ── Save ballot ───────────────────────────────────────────────────────────────

saveBtn.addEventListener("click", async () => {
  if (!electionId) return;
  try {
    saveBtn.disabled = true;
    const ballot = readBallot();
    await api("PUT", `/elections/${electionId}/ballot`, ballot);
    setMessage("Ballot saved successfully.");
  } catch (err) {
    setMessage(err.message, true);
  } finally {
    saveBtn.disabled = false;
  }
});

// ── Publish election ──────────────────────────────────────────────────────────

publishBtn.addEventListener("click", async () => {
  if (!electionId) return;
  if (!confirm("Publish this election? Members will be able to vote immediately and the ballot cannot be edited.")) return;

  try {
    publishBtn.disabled = true;
    // Save first, then publish
    await api("PUT", `/elections/${electionId}/ballot`, readBallot());
    await api("POST", `/elections/${electionId}/publish`, {});
    setMessage("Election published! Members can now vote.");
    publishBtn.classList.add("hidden");
    saveBtn.classList.add("hidden");
    addOfficeBtn.classList.add("hidden");
    addInitiativeBtn.classList.add("hidden");
    statusBanner.textContent = "This election is now active.";
    statusBanner.classList.remove("hidden");
  } catch (err) {
    setMessage(err.message, true);
  } finally {
    publishBtn.disabled = false;
  }
});

// ── Add buttons ───────────────────────────────────────────────────────────────

addOfficeBtn.addEventListener("click", () => addOffice());
addInitiativeBtn.addEventListener("click", () => addInitiative());

// ── Init ──────────────────────────────────────────────────────────────────────

async function init() {
  // Redirect if not logged in or wrong role
  try {
    const me = await api("GET", "/me");
    if (!["employee", "admin"].includes(me.role)) {
      window.location.href = "./dashboard.html";
      return;
    }
  } catch {
    window.location.href = "./login.html";
    return;
  }

  await loadSocieties();

  if (electionId) {
    // Editing existing election — load it
    try {
      const data = await api("GET", `/elections/${electionId}`);
      const e = data.election;
      nameInput.value  = e.name ?? "";
      startInput.value = e.start_date ?? "";
      endInput.value   = e.end_date ?? "";
      descInput.value  = e.description ?? "";
      societySelect.value = "";  // already locked, society shown by name

      showBallotSection(e);
      populateBallot(data);
    } catch (err) {
      setMessage(err.message, true);
    }
  }
}

init();
