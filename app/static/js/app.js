document.querySelectorAll("form[data-confirm]").forEach(form => {
  form.addEventListener("submit", event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

window.setTimeout(() => {
  document.querySelectorAll(".flash").forEach(el => el.classList.add("flash-hide"));
}, 5000);


const sidebar = document.getElementById("portalSidebar");
const menuToggle = document.querySelector(".menu-toggle");
const sidebarOverlay = document.querySelector(".sidebar-overlay");

function setSidebar(open) {
  if (!sidebar) return;
  document.body.classList.toggle("sidebar-open", open);
  if (menuToggle) menuToggle.setAttribute("aria-expanded", open ? "true" : "false");
}

if (menuToggle) menuToggle.addEventListener("click", () => setSidebar(!document.body.classList.contains("sidebar-open")));
if (sidebarOverlay) sidebarOverlay.addEventListener("click", () => setSidebar(false));
if (sidebar) sidebar.querySelectorAll("a").forEach(link => link.addEventListener("click", () => setSidebar(false)));
