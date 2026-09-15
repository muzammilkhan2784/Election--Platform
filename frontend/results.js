import { renderNavbar, renderFooter, loadNavbarUser, showAlert } from "./components.js";

const API_BASE_URL = "/api";
const params = new URLSearchParams(window.location.search);
const electionId = params.get("id");

const officeResults = document.getElementById("office-results");
const initiativeResults = document.getElementById("initiative-results");

renderNavbar({ title: "Election Results", showBack: true, showUser: true });
renderFooter();
loadNavbarUser();

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));

/**
 * One result row: name, a proportional bar, and the tally.
 *
 * The bar is scaled against the leader rather than the total, because an
 * office with several candidates would otherwise render every bar as a short
 * stub and the comparison — which is the whole point — would be lost.
 */
function resultRow(label, votes, total, leaderVotes, isLeader) {
  const share = total > 0 ? (votes / total) * 100 : 0;
  const width = leaderVotes > 0 ? (votes / leaderVotes) * 100 : 0;
  return `
    <li class="py-3">
      <div class="flex items-baseline justify-between gap-4 mb-1.5">
        <span class="text-[14.5px] ${isLeader ? "font-semibold text-ink-900" : "text-ink-700"} truncate">
          ${escapeHtml(label)}
          ${isLeader && votes > 0 ? '<span class="badge badge-active ml-1.5 align-middle">leading</span>' : ""}
        </span>
        <span class="shrink-0 text-[13px] tabular text-ink-500">
          <span class="font-semibold ${isLeader ? "text-brand-700" : "text-ink-700"}">${votes.toLocaleString()}</span>
          <span class="text-ink-400"> &middot; ${share.toFixed(1)}%</span>
        </span>
      </div>
      <div class="h-2 rounded-full bg-ink-100 overflow-hidden" role="img"
           aria-label="${share.toFixed(1)} percent of votes cast">
        <div class="h-full rounded-full ${isLeader ? "bg-brand-600" : "bg-brand-300"}"
             style="width: ${width.toFixed(2)}%"></div>
      </div>
    </li>
  `;
}

function resultCard(title, rows, labelKey) {
  const total = rows.reduce((sum, r) => sum + Number(r.vote_count), 0);
  const leaderVotes = rows.reduce((max, r) => Math.max(max, Number(r.vote_count)), 0);
  // A tie has no single leader, so highlight nobody rather than the first row.
  const leaders = rows.filter((r) => Number(r.vote_count) === leaderVotes).length;

  const sorted = [...rows].sort((a, b) => Number(b.vote_count) - Number(a.vote_count));

  return `
    <article class="bg-white rounded-2xl border border-ink-200 shadow-card p-6">
      <div class="flex items-baseline justify-between gap-4 mb-4">
        <h3 class="text-[16.5px] font-semibold text-ink-900">${escapeHtml(title)}</h3>
        <span class="text-[13px] text-ink-400 tabular shrink-0">${total.toLocaleString()} votes</span>
      </div>
      <ul class="divide-y divide-ink-100 -my-3">
        ${sorted.map((r) => resultRow(
          r[labelKey],
          Number(r.vote_count),
          total,
          leaderVotes,
          leaders === 1 && Number(r.vote_count) === leaderVotes,
        )).join("")}
      </ul>
    </article>
  `;
}

const emptyState = (message) => `
  <div class="bg-white rounded-2xl border border-dashed border-ink-200 p-10 text-center">
    <p class="text-[14.5px] text-ink-500">${message}</p>
  </div>
`;

async function loadResults() {
  const response = await fetch(`${API_BASE_URL}/elections/${electionId}/results`, {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Could not load results.");
  const data = await response.json();

  const heading = document.getElementById("results-heading");
  if (heading && data.election_name) heading.textContent = data.election_name;

  officeResults.innerHTML = data.offices.length
    ? data.offices.map((o) => resultCard(o.office_title, o.candidates, "candidate_name")).join("")
    : emptyState("This ballot had no offices.");

  initiativeResults.innerHTML = data.initiatives.length
    ? data.initiatives.map((i) => resultCard(i.initiative_title, i.options, "option_label")).join("")
    : emptyState("This ballot had no initiatives.");
}

loadResults().catch((error) => {
  showAlert(error.message, "error");
  officeResults.innerHTML = emptyState(escapeHtml(error.message));
});
