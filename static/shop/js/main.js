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
  if (modal.dataset.initialized === "true") return;
  modal.dataset.initialized = "true";

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

  const setOpenState = (isOpen) => {
    modal.hidden = !isOpen;
    modal.classList.toggle("hidden", !isOpen);
    modal.classList.toggle("flex", isOpen);
    modal.setAttribute("aria-hidden", String(!isOpen));
    document.body.classList.toggle("overflow-hidden", isOpen);
  };

  const open = () => {
    const qty = readCurrentQty();
    if (qtyHidden) qtyHidden.value = String(qty);
    if (qtyLabel) qtyLabel.textContent = String(qty);
    setOpenState(true);
    if (nameInput) {
      window.requestAnimationFrame(() => nameInput.focus());
    }
  };

  const close = () => {
    setOpenState(false);
  };

  setOpenState(false);

  openers.forEach((btn) => btn.addEventListener("click", open));
  closers.forEach((btn) => btn.addEventListener("click", close));

  modal.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (dialog && dialog.contains(target)) return;
    close();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) close();
  });
}

function getCsrfToken() {
  const cookie = document.cookie
    .split(";")
    .map((v) => v.trim())
    .find((v) => v.startsWith("csrftoken="));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
}

async function postForm(url, payload) {
  const body = new URLSearchParams(payload);
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      "X-CSRFToken": getCsrfToken(),
    },
    body: body.toString(),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    throw new Error(data.error || "Произошла ошибка. Попробуйте еще раз.");
  }
  return data;
}

function initAuthModal() {
  const modal = document.querySelector("[data-auth-modal]");
  const openButtons = document.querySelectorAll("[data-auth-open]");
  if (!modal || openButtons.length === 0) return;
  if (modal.dataset.initialized === "true") return;
  modal.dataset.initialized = "true";

  const dialog = modal.querySelector("[data-auth-dialog]");
  const closeButtons = modal.querySelectorAll("[data-auth-close]");
  const backButtons = modal.querySelectorAll("[data-auth-back]");
  const errorBox = modal.querySelector("[data-auth-error]");
  const emailInput = modal.querySelector("[data-auth-email-input]");
  const passwordInput = modal.querySelector("[data-auth-password-input]");
  const password1Input = modal.querySelector("[data-auth-password1-input]");
  const password2Input = modal.querySelector("[data-auth-password2-input]");
  const emailLabels = modal.querySelectorAll("[data-auth-email-label]");
  const emailStep = modal.querySelector('[data-auth-step="email"]');
  const loginStep = modal.querySelector('[data-auth-step="login"]');
  const registerStep = modal.querySelector('[data-auth-step="register"]');
  const confirmStep = modal.querySelector('[data-auth-step="confirm"]');
  const currentPath = window.location.pathname || "/";

  let currentEmail = "";

  const allSteps = [emailStep, loginStep, registerStep, confirmStep];

  const setOpenState = (isOpen) => {
    modal.hidden = !isOpen;
    modal.classList.toggle("hidden", !isOpen);
    modal.classList.toggle("flex", isOpen);
    modal.setAttribute("aria-hidden", String(!isOpen));
    document.body.classList.toggle("overflow-hidden", isOpen);
  };

  const setError = (message) => {
    if (!errorBox) return;
    if (!message) {
      errorBox.textContent = "";
      errorBox.classList.add("hidden");
      return;
    }
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
  };

  const showStep = (name) => {
    allSteps.forEach((step) => step?.classList.add("hidden"));
    const target = modal.querySelector(`[data-auth-step="${name}"]`);
    target?.classList.remove("hidden");
    emailLabels.forEach((node) => {
      node.textContent = currentEmail;
    });
    setError("");
  };

  const open = () => {
    showStep("email");
    setOpenState(true);
    emailInput?.focus();
  };

  const close = () => {
    setOpenState(false);
    setError("");
    if (emailStep instanceof HTMLFormElement) emailStep.reset();
    if (loginStep instanceof HTMLFormElement) loginStep.reset();
    if (registerStep instanceof HTMLFormElement) registerStep.reset();
    currentEmail = "";
  };

  setOpenState(false);

  openButtons.forEach((btn) => btn.addEventListener("click", open));
  closeButtons.forEach((btn) => btn.addEventListener("click", close));
  backButtons.forEach((btn) =>
    btn.addEventListener("click", () => {
      showStep("email");
      emailInput?.focus();
    }),
  );

  modal.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (dialog && dialog.contains(target)) return;
    close();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) close();
  });

  emailStep?.addEventListener("submit", async (event) => {
    event.preventDefault();
    currentEmail = (emailInput?.value || "").trim().toLowerCase();
    if (!currentEmail) {
      setError("Введите email.");
      return;
    }
    try {
      const data = await postForm("/auth/email-check/", { email: currentEmail });
      showStep(data.exists ? "login" : "register");
      if (data.exists) {
        passwordInput?.focus();
      } else {
        password1Input?.focus();
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "Не удалось проверить email.");
    }
  });

  loginStep?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const password = passwordInput?.value || "";
    try {
      await postForm("/auth/login/", {
        email: currentEmail,
        password,
        next: currentPath,
      });
      window.location.reload();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Ошибка входа.");
    }
  });

  registerStep?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const password1 = password1Input?.value || "";
    const password2 = password2Input?.value || "";
    try {
      await postForm("/auth/register/", {
        email: currentEmail,
        password1,
        password2,
      });
      showStep("confirm");
    } catch (error) {
      setError(error instanceof Error ? error.message : "Ошибка регистрации.");
    }
  });
}

/** Административные центры субъектов РФ, для быстрого выбора и подсказок поиска */
const REGIONAL_CENTERS_RU = [
  "Абакан",
  "Анадырь",
  "Архангельск",
  "Астрахань",
  "Барнаул",
  "Белгород",
  "Благовещенск",
  "Брянск",
  "Великий Новгород",
  "Владивосток",
  "Владикавказ",
  "Владимир",
  "Волгоград",
  "Вологда",
  "Воронеж",
  "Горно-Алтайск",
  "Грозный",
  "Екатеринбург",
  "Иваново",
  "Ижевск",
  "Иркутск",
  "Йошкар-Ола",
  "Казань",
  "Калининград",
  "Калуга",
  "Кемерово",
  "Киров",
  "Кострома",
  "Краснодар",
  "Красноярск",
  "Курган",
  "Курск",
  "Кызыл",
  "Липецк",
  "Магас",
  "Майкоп",
  "Махачкала",
  "Москва",
  "Мурманск",
  "Нальчик",
  "Нарьян-Мар",
  "Нижний Новгород",
  "Новосибирск",
  "Омск",
  "Орёл",
  "Оренбург",
  "Пенза",
  "Пермь",
  "Петрозаводск",
  "Петропавловск-Камчатский",
  "Псков",
  "Ростов-на-Дону",
  "Рязань",
  "Салехард",
  "Самара",
  "Санкт-Петербург",
  "Саранск",
  "Саратов",
  "Севастополь",
  "Симферополь",
  "Смоленск",
  "Ставрополь",
  "Сыктывкар",
  "Тамбов",
  "Тверь",
  "Томск",
  "Тула",
  "Тюмень",
  "Улан-Удэ",
  "Ульяновск",
  "Уфа",
  "Хабаровск",
  "Ханты-Мансийск",
  "Чебоксары",
  "Челябинск",
  "Черкесск",
  "Чита",
  "Элиста",
  "Южно-Сахалинск",
  "Якутск",
  "Ярославль",
].sort((a, b) => a.localeCompare(b, "ru"));

/** Порядок крупных городов как на референсе, остальные — ниже по алфавиту */
const CITY_MODAL_PRIORITY = [
  "Москва",
  "Санкт-Петербург",
  "Нижний Новгород",
  "Екатеринбург",
  "Челябинск",
  "Краснодар",
  "Пермь",
  "Воронеж",
  "Самара",
  "Казань",
  "Волгоград",
  "Новосибирск",
  "Ростов-на-Дону",
  "Саратов",
];

function citiesForModalList() {
  const prioritySet = new Set(CITY_MODAL_PRIORITY);
  const rest = REGIONAL_CENTERS_RU.filter((c) => !prioritySet.has(c));
  return [...CITY_MODAL_PRIORITY.filter((c) => REGIONAL_CENTERS_RU.includes(c)), ...rest];
}

const CITY_STORAGE_KEY = "shop_selected_city";
const DEFAULT_CITY_LABEL = "Москва";

function initCityPicker() {
  const modal = document.querySelector("[data-city-modal]");
  const label = document.querySelector("[data-city-label]");
  const openBtn = document.querySelector("[data-city-open]");
  if (!modal || !label || !openBtn) return;
  if (modal.dataset.initialized === "true") return;
  modal.dataset.initialized = "true";

  const dialog = modal.querySelector("[data-city-dialog]");
  const searchInput = modal.querySelector("[data-city-search]");
  const resultsEl = modal.querySelector("[data-city-results]");
  const mainListEl = modal.querySelector("[data-city-main-list]");
  const closeBtn = modal.querySelector("[data-city-close]");

  const readStoredCity = () => {
    try {
      const v = localStorage.getItem(CITY_STORAGE_KEY);
      return v && v.trim() ? v.trim() : DEFAULT_CITY_LABEL;
    } catch {
      return DEFAULT_CITY_LABEL;
    }
  };

  const setOpenState = (isOpen) => {
    modal.hidden = !isOpen;
    modal.classList.toggle("hidden", !isOpen);
    modal.classList.toggle("flex", isOpen);
    modal.setAttribute("aria-hidden", String(!isOpen));
    document.body.classList.toggle("overflow-hidden", isOpen);
  };

  const setMainListHidden = (hidden) => {
    if (!mainListEl) return;
    mainListEl.classList.toggle("hidden", hidden);
    mainListEl.setAttribute("aria-hidden", hidden ? "true" : "false");
  };

  const hideResults = () => {
    if (!resultsEl) return;
    resultsEl.innerHTML = "";
    resultsEl.classList.add("hidden");
    setMainListHidden(false);
  };

  const cityRowClass =
    "block w-full rounded-lg px-3 py-2.5 text-left text-sm text-slate-900 hover:bg-slate-100";

  const renderResults = (query) => {
    if (!resultsEl) return;
    const q = query.trim().toLowerCase();
    resultsEl.innerHTML = "";
    if (!q) {
      hideResults();
      return;
    }
    setMainListHidden(true);
    const matches = REGIONAL_CENTERS_RU.filter((c) =>
      c.toLowerCase().includes(q),
    );
    if (!matches.length) {
      resultsEl.classList.remove("hidden");
      const empty = document.createElement("p");
      empty.className = "px-3 py-2 text-sm text-slate-500";
      empty.textContent = "Ничего не найдено";
      resultsEl.appendChild(empty);
      return;
    }
    resultsEl.classList.remove("hidden");
    const slice = matches.slice(0, 60);
    slice.forEach((city) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = cityRowClass;
      btn.textContent = city;
      btn.addEventListener("click", () => selectCity(city));
      resultsEl.appendChild(btn);
    });
  };

  const selectCity = (name) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      localStorage.setItem(CITY_STORAGE_KEY, trimmed);
    } catch {
      /* ignore quota / private mode */
    }
    label.textContent = trimmed;
    setOpenState(false);
    if (searchInput) searchInput.value = "";
    hideResults();
  };

  label.textContent = readStoredCity();

  if (mainListEl) {
    citiesForModalList().forEach((city) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = cityRowClass;
      btn.textContent = city;
      btn.addEventListener("click", () => selectCity(city));
      mainListEl.appendChild(btn);
    });
  }

  openBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    if (searchInput) searchInput.value = "";
    hideResults();
    setOpenState(true);
    window.requestAnimationFrame(() => searchInput?.focus());
  });

  closeBtn?.addEventListener("click", () => setOpenState(false));

  modal.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (dialog && dialog.contains(target)) return;
    setOpenState(false);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) setOpenState(false);
  });

  searchInput?.addEventListener("input", () => {
    renderResults(searchInput.value);
  });

  setOpenState(false);
}

document.addEventListener("DOMContentLoaded", applyDynamicBits);
document.addEventListener("DOMContentLoaded", initCatalogMenu);
document.addEventListener("DOMContentLoaded", initCartQtyForms);
document.addEventListener("DOMContentLoaded", initQuickOrder);
document.addEventListener("DOMContentLoaded", initAuthModal);
document.addEventListener("DOMContentLoaded", initCityPicker);
