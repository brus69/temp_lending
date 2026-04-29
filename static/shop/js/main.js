function applyDynamicBits() {
  const yearNodes = document.querySelectorAll("[data-current-year]");
  const year = new Date().getFullYear();
  yearNodes.forEach((node) => {
    node.textContent = String(year);
  });
}

function initCatalogMenu() {
  const toggle = document.querySelector("[data-catalog-toggle]");
  const menu = document.querySelector("[data-catalog-menu]");
  if (!toggle || !menu) return;

  const closeMenu = () => menu.classList.add("hidden");
  const openMenu = () => menu.classList.remove("hidden");
  const isOpen = () => !menu.classList.contains("hidden");

  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    if (isOpen()) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  document.addEventListener("click", (event) => {
    if (!isOpen()) return;
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (menu.contains(target) || toggle.contains(target)) return;
    closeMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
}

document.addEventListener("DOMContentLoaded", applyDynamicBits);
document.addEventListener("DOMContentLoaded", initCatalogMenu);
