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

function initCartQtyForms() {
  document.querySelectorAll("[data-cart-qty-form]").forEach((form) => {
    const input = form.querySelector("[data-qty-input]");
    const dec = form.querySelector("[data-qty-dec]");
    const inc = form.querySelector("[data-qty-inc]");
    if (!input || !dec || !inc) return;

    const clamp = () => {
      let n = parseInt(input.value, 10);
      if (Number.isNaN(n) || n < 1) n = 1;
      input.value = String(n);
    };

    dec.addEventListener("click", () => {
      const n = parseInt(input.value, 10) || 1;
      input.value = String(Math.max(1, n - 1));
    });
    inc.addEventListener("click", () => {
      const n = parseInt(input.value, 10) || 1;
      input.value = String(n + 1);
    });
    input.addEventListener("change", clamp);
    input.addEventListener("blur", clamp);
    form.addEventListener("submit", clamp);
  });
}

function initQuickOrder() {
  const modal = document.querySelector("[data-quick-order-modal]");
  if (!modal) return;

  const dialog = modal.querySelector("[data-quick-order-dialog]");
  const qtyHidden = modal.querySelector("[data-quick-order-qty]");
  const qtyLabel = modal.querySelector("[data-quick-order-qty-label]");
  const nameInput = modal.querySelector("[data-quick-order-name]");
  const openers = document.querySelectorAll("[data-quick-order-open]");
  const closers = modal.querySelectorAll("[data-quick-order-close]");

  const readCurrentQty = () => {
    const cartQty = document.querySelector("[data-cart-qty-form] [data-qty-input]");
    const raw = cartQty ? parseInt(cartQty.value, 10) : 1;
    return Number.isNaN(raw) || raw < 1 ? 1 : raw;
  };

  const open = () => {
    const qty = readCurrentQty();
    if (qtyHidden) qtyHidden.value = String(qty);
    if (qtyLabel) qtyLabel.textContent = String(qty);
    modal.hidden = false;
    document.body.classList.add("overflow-hidden");
    if (nameInput) {
      window.requestAnimationFrame(() => nameInput.focus());
    }
  };

  const close = () => {
    modal.hidden = true;
    document.body.classList.remove("overflow-hidden");
  };

  openers.forEach((btn) => btn.addEventListener("click", open));
  closers.forEach((btn) => btn.addEventListener("click", close));

  modal.addEventListener("click", (event) => {
    if (dialog && dialog.contains(event.target)) return;
    close();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) close();
  });
}

document.addEventListener("DOMContentLoaded", applyDynamicBits);
document.addEventListener("DOMContentLoaded", initCatalogMenu);
document.addEventListener("DOMContentLoaded", initCartQtyForms);
document.addEventListener("DOMContentLoaded", initQuickOrder);
