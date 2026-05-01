function applyDynamicBits() {
  const yearNodes = document.querySelectorAll("[data-current-year]");
  const year = new Date().getFullYear();
  yearNodes.forEach((node) => {
    node.textContent = String(year);
  });
}

function initQuickOrderModal() {
  const modal = document.querySelector("[data-quick-order-modal]");
  const openButtons = document.querySelectorAll("[data-quick-order-open]");
  const dialog = modal?.querySelector("[data-quick-order-dialog]");
  const closeButtons = modal?.querySelectorAll("[data-quick-order-close]") ?? [];

  if (!modal || openButtons.length === 0) return;
  if (modal.dataset.initialized === "true") return;
  modal.dataset.initialized = "true";

  const setOpenState = (isOpen) => {
    modal.hidden = !isOpen;
    modal.classList.toggle("hidden", !isOpen);
    modal.classList.toggle("flex", isOpen);
    modal.setAttribute("aria-hidden", String(!isOpen));
    document.body.classList.toggle("overflow-hidden", isOpen);
  };

  setOpenState(false);

  openButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setOpenState(true);
    });
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setOpenState(false);
    });
  });

  modal.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (dialog && dialog.contains(target)) return;
    setOpenState(false);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.getAttribute("aria-hidden") === "false") {
      setOpenState(false);
    }
  });
}

function initPage() {
  applyDynamicBits();
  initQuickOrderModal();
}

document.addEventListener("DOMContentLoaded", initPage);
document.addEventListener("components:loaded", initPage);
