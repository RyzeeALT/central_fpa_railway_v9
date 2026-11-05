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
const themeToggle = document.querySelector(".theme-toggle");
const desktopMedia = window.matchMedia("(min-width: 901px)");

function updateSidebarAria() {
  if (!menuToggle || !sidebar) return;
  const expanded = desktopMedia.matches
    ? !document.body.classList.contains("sidebar-collapsed")
    : document.body.classList.contains("sidebar-open");
  menuToggle.setAttribute("aria-expanded", expanded ? "true" : "false");
}

function setMobileSidebar(open) {
  if (!sidebar) return;
  document.body.classList.toggle("sidebar-open", open);
  if (sidebarOverlay) sidebarOverlay.setAttribute("aria-hidden", open ? "false" : "true");
  updateSidebarAria();
}

function toggleSidebar() {
  if (!sidebar) return;
  if (desktopMedia.matches) {
    const collapsed = !document.body.classList.contains("sidebar-collapsed");
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    try { localStorage.setItem("fpa-sidebar-collapsed", collapsed ? "1" : "0"); } catch (_) {}
    updateSidebarAria();
  } else {
    setMobileSidebar(!document.body.classList.contains("sidebar-open"));
  }
}

if (sidebar && desktopMedia.matches) {
  try {
    document.body.classList.toggle("sidebar-collapsed", localStorage.getItem("fpa-sidebar-collapsed") === "1");
  } catch (_) {}
}

if (menuToggle) menuToggle.addEventListener("click", toggleSidebar);
if (sidebarOverlay) sidebarOverlay.addEventListener("click", () => setMobileSidebar(false));
if (sidebar) sidebar.querySelectorAll("a").forEach(link => link.addEventListener("click", () => {
  if (!desktopMedia.matches) setMobileSidebar(false);
}));

desktopMedia.addEventListener?.("change", () => {
  document.body.classList.remove("sidebar-open");
  if (desktopMedia.matches) {
    try {
      document.body.classList.toggle("sidebar-collapsed", localStorage.getItem("fpa-sidebar-collapsed") === "1");
    } catch (_) {}
  } else {
    document.body.classList.remove("sidebar-collapsed");
  }
  updateSidebarAria();
});

function applyTheme(theme, persist = true) {
  const normalized = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = normalized;
  if (themeToggle) {
    const isDark = normalized === "dark";
    themeToggle.setAttribute("aria-pressed", isDark ? "true" : "false");
    themeToggle.setAttribute("aria-label", isDark ? "Ativar modo claro" : "Ativar modo escuro");
    themeToggle.title = isDark ? "Modo claro" : "Modo escuro";
  }
  if (persist) {
    try { localStorage.setItem("fpa-theme", normalized); } catch (_) {}
  }
}

let initialTheme = document.documentElement.dataset.theme;
if (initialTheme !== "dark" && initialTheme !== "light") {
  try { initialTheme = localStorage.getItem("fpa-theme"); } catch (_) {}
}
applyTheme(initialTheme === "dark" ? "dark" : "light", false);
if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  });
}

updateSidebarAria();


// Cards públicos: toda a superfície funciona como ação principal.
document.querySelectorAll('[data-card-href]').forEach(card => {
  const href = card.dataset.cardHref;
  if (!href) return;

  const openCard = () => {
    const popup = window.open(href, '_blank');
    if (popup) popup.opener = null;
  };

  card.addEventListener('click', event => {
    if (event.target.closest('a, button, input, select, textarea, label')) return;
    openCard();
  });

  card.addEventListener('keydown', event => {
    if (event.target !== card) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openCard();
    }
  });
});

// Fecha o drawer mobile com Escape.
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && document.body.classList.contains("sidebar-open")) {
    setMobileSidebar(false);
    menuToggle?.focus();
  }
});
