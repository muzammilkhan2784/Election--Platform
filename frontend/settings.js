import { renderNavbar, renderFooter, loadNavbarUser, showAlert } from "./components.js";

const API = "/api";

renderNavbar({ title: "Settings", showBack: true, showUser: true });
renderFooter();

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

function setMsg(elId, text, isError) {
  const el = document.getElementById(elId);
  el.textContent = text;
  el.className = `text-sm ${isError ? "text-red-600" : "text-green-600"}`;
  el.classList.remove("hidden");
}

async function init() {
  const user = await loadNavbarUser();
  if (!user) return;

  document.getElementById("profile-email").value = user.email || "";
  document.getElementById("profile-first").value = user.first_name || "";
  document.getElementById("profile-last").value  = user.last_name  || "";

  // Save profile
  document.getElementById("save-profile-btn").addEventListener("click", async () => {
    const first_name = document.getElementById("profile-first").value.trim();
    const last_name  = document.getElementById("profile-last").value.trim();
    if (!first_name || !last_name) {
      setMsg("profile-msg", "First and last name are required.", true);
      return;
    }
    try {
      await api("PUT", "/me", { first_name, last_name });
      showAlert("Profile updated.", "success");
      setMsg("profile-msg", "Saved!", false);
    } catch (e) {
      setMsg("profile-msg", e.message, true);
    }
  });

  // Change password
  document.getElementById("save-password-btn").addEventListener("click", async () => {
    const current_password = document.getElementById("pw-current").value;
    const new_password     = document.getElementById("pw-new").value;
    const confirm          = document.getElementById("pw-confirm").value;

    if (!current_password || !new_password || !confirm) {
      setMsg("password-msg", "All password fields are required.", true);
      return;
    }
    if (new_password !== confirm) {
      setMsg("password-msg", "New passwords do not match.", true);
      return;
    }
    try {
      await api("PUT", "/me/password", { current_password, new_password });
      showAlert("Password updated.", "success");
      setMsg("password-msg", "Password changed!", false);
      document.getElementById("pw-current").value = "";
      document.getElementById("pw-new").value = "";
      document.getElementById("pw-confirm").value = "";
    } catch (e) {
      setMsg("password-msg", e.message, true);
    }
  });
}

init();
