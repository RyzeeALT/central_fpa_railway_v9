document.querySelectorAll("form[data-confirm]").forEach(form => {
  form.addEventListener("submit", event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

window.setTimeout(() => {
  document.querySelectorAll(".flash").forEach(el => el.classList.add("flash-hide"));
}, 5000);
