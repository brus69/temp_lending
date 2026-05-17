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

  const open = (event) => {
    const trigger = event?.currentTarget;
    if (trigger instanceof HTMLElement && trigger.dataset.postLoginHash) {
      try {
        sessionStorage.setItem(
          "shopPostLoginHash",
          trigger.dataset.postLoginHash.startsWith("#")
            ? trigger.dataset.postLoginHash
            : `#${trigger.dataset.postLoginHash}`,
        );
      } catch {
        /* ignore */
      }
    }
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

  openButtons.forEach((btn) => btn.addEventListener("click", (event) => open(event)));
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
      let targetUrl = `${window.location.pathname}${window.location.search}`;
      try {
        const hash = sessionStorage.getItem("shopPostLoginHash");
        if (hash) {
          sessionStorage.removeItem("shopPostLoginHash");
          targetUrl += hash;
        }
      } catch {
        /* ignore */
      }
      window.location.href = targetUrl;
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

/** Оценка отзыва: 5 звёзд, клик задаёт значение в скрытом поле #id_rating */
function initReviewRatingStars() {
  const root = document.querySelector("[data-review-stars]");
  const hidden = document.getElementById("id_rating");
  if (!root || !(hidden instanceof HTMLInputElement)) return;
  if (root.dataset.starsInit === "true") return;
  root.dataset.starsInit = "true";

  const buttons = Array.from(root.querySelectorAll("[data-review-star]"));
  if (buttons.length !== 5) return;

  let current = (() => {
    const v = parseInt(hidden.value, 10);
    return Number.isFinite(v) && v >= 1 && v <= 5 ? v : 0;
  })();

  const paint = () => {
    buttons.forEach((btn, i) => {
      const v = i + 1;
      const on = current > 0 && v <= current;
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.setAttribute("aria-label", `Оценка ${v} из 5`);
      btn.classList.toggle("border-amber-400", on);
      btn.classList.toggle("bg-amber-50", on);
      btn.classList.toggle("text-amber-500", on);
      btn.classList.toggle("border-slate-200", !on);
      btn.classList.toggle("bg-white", !on);
      btn.classList.toggle("text-white", !on);
      btn.classList.toggle("drop-shadow-[0_0_1px_rgb(100,116,139)]", !on);
    });
    hidden.value = current > 0 ? String(current) : "";
  };

  buttons.forEach((btn, i) => {
    const v = i + 1;
    btn.addEventListener("click", () => {
      current = v;
      paint();
    });
  });

  paint();
}

function initProductGallery() {
  document.querySelectorAll("[data-product-gallery]").forEach((root) => {
    const wrap = root.closest("[data-product-gallery-wrap]") || root;
    const main = root.querySelector("[data-gallery-main]");
    const thumbs = Array.from(root.querySelectorAll("[data-gallery-thumb]"));
    const openBtn = root.querySelector("[data-gallery-open]");
    const modal = wrap.querySelector("[data-gallery-modal]");
    const modalDialog = wrap.querySelector("[data-gallery-modal-dialog]");
    const modalImage = wrap.querySelector("[data-gallery-modal-image]");
    const closeBtn = wrap.querySelector("[data-gallery-close]");
    if (!main || thumbs.length === 0) return;

    const setModalOpen = (isOpen) => {
      if (!modal) return;
      if (isOpen) {
        modal.hidden = false;
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("overflow-hidden");
      } else {
        modal.classList.remove("flex");
        modal.classList.add("hidden");
        modal.hidden = true;
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("overflow-hidden");
      }
    };

    const setActive = (btn) => {
      thumbs.forEach((t) => {
        t.classList.remove("border-red-600", "ring-2", "ring-red-600");
      });
      btn.classList.add("border-red-600", "ring-2", "ring-red-600");
    };

    thumbs.forEach((btn) => {
      btn.addEventListener("click", () => {
        const url = btn.getAttribute("data-gallery-thumb");
        if (url) {
          main.setAttribute("src", url);
          if (modalImage) modalImage.setAttribute("src", url);
        }
        setActive(btn);
      });
    });

    openBtn?.addEventListener("click", () => {
      if (modalImage) modalImage.setAttribute("src", main.getAttribute("src") || "");
      setModalOpen(true);
    });

    closeBtn?.addEventListener("click", () => {
      setModalOpen(false);
    });

    modal?.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (modalDialog && modalDialog.contains(target)) return;
      setModalOpen(false);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") setModalOpen(false);
    });

    setActive(thumbs[0]);
    if (modalImage) modalImage.setAttribute("src", main.getAttribute("src") || "");
  });
}

function initSubCategoryFilters() {
  const form = document.querySelector("[data-subcategory-filters]");
  if (!form) return;

  const countUrl = form.dataset.countUrl;
  let popover = form.querySelector("[data-filter-popover]");
  const countNode = popover?.querySelector("[data-filter-popover-count]");
  const submitBtn = form.querySelector("[data-filter-submit-btn]");
  const popoverSubmitBtn = popover?.querySelector("[data-filter-popover-submit]");
  const resetAllLink = form.querySelector("[data-filter-reset-all]");
  const priceResetBtn = form.querySelector("[data-filter-price-reset]");
  if (!countUrl || !popover || !countNode) return;

  const setSubmitLabels = (label) => {
    if (typeof label !== "string") return;
    if (submitBtn instanceof HTMLButtonElement) submitBtn.textContent = label;
    if (popoverSubmitBtn instanceof HTMLButtonElement) popoverSubmitBtn.textContent = label;
  };

  if (!form.id) form.id = "subcategory-filters-form";
  document.body.appendChild(popover);
  if (popoverSubmitBtn instanceof HTMLButtonElement) {
    popoverSubmitBtn.setAttribute("form", form.id);
  }

  let debounceTimer = null;
  let activeController = null;
  let anchorEl = null;

  const hasActivePriceFilter = () => {
    const priceMin = form.querySelector('[name="price_min"]');
    const priceMax = form.querySelector('[name="price_max"]');
    return (
      (priceMin instanceof HTMLInputElement && priceMin.value.trim() !== "") ||
      (priceMax instanceof HTMLInputElement && priceMax.value.trim() !== "")
    );
  };

  const hasActiveFilters = () => {
    const hasCheckbox = form.querySelector("[data-filter-checkbox]:checked");
    return Boolean(hasCheckbox || hasActivePriceFilter());
  };

  const updatePriceResetVisibility = () => {
    if (!(priceResetBtn instanceof HTMLElement)) return;
    priceResetBtn.classList.toggle("hidden", !hasActivePriceFilter());
  };

  const shouldShowResetAll = () => hasActiveFilters() || Boolean(window.location.search);

  const updateResetAllVisibility = () => {
    if (!(resetAllLink instanceof HTMLElement)) return;
    resetAllLink.classList.toggle("hidden", !shouldShowResetAll());
  };

  const clearFormFilters = () => {
    form.querySelectorAll("[data-filter-checkbox]").forEach((checkbox) => {
      if (checkbox instanceof HTMLInputElement) checkbox.checked = false;
    });
    form.querySelectorAll('[name="price_min"], [name="price_max"]').forEach((input) => {
      if (input instanceof HTMLInputElement) input.value = "";
    });
    resetPriceRange?.();
    updatePriceResetVisibility();
    anchorEl = null;
  };

  const navigateWithoutPriceFilter = () => {
    const action = form.getAttribute("action") || window.location.pathname;
    const params = new URLSearchParams();
    new FormData(form).forEach((value, key) => {
      if (value === "" || key === "price_min" || key === "price_max" || key === "page") return;
      params.append(key, value);
    });
    const query = params.toString();
    window.location.href = query ? `${action}?${query}` : action;
  };

  const clearPriceFilter = () => {
    form.querySelectorAll('[name="price_min"], [name="price_max"]').forEach((input) => {
      if (input instanceof HTMLInputElement) input.value = "";
    });
    resetPriceRange?.();
    navigateWithoutPriceFilter();
  };

  let resetPriceRange = null;
  const priceRangeRoot = form.querySelector("[data-price-range]");
  const priceMinInput = form.querySelector('[name="price_min"]');
  const priceMaxInput = form.querySelector('[name="price_max"]');
  if (
    priceRangeRoot instanceof HTMLElement &&
    priceMinInput instanceof HTMLInputElement &&
    priceMaxInput instanceof HTMLInputElement
  ) {
    const rangeMin = priceRangeRoot.querySelector("[data-price-range-min]");
    const rangeMax = priceRangeRoot.querySelector("[data-price-range-max]");
    const rangeFill = priceRangeRoot.querySelector("[data-price-range-fill]");
    const minBound = Number.parseInt(priceRangeRoot.dataset.min || "0", 10);
    const maxBound = Number.parseInt(priceRangeRoot.dataset.max || "0", 10);

    if (
      rangeMin instanceof HTMLInputElement &&
      rangeMax instanceof HTMLInputElement &&
      rangeFill instanceof HTMLElement &&
      Number.isFinite(minBound) &&
      Number.isFinite(maxBound) &&
      maxBound > minBound
    ) {
      const updateRangeFill = () => {
        const minVal = Number.parseInt(rangeMin.value, 10);
        const maxVal = Number.parseInt(rangeMax.value, 10);
        const span = maxBound - minBound;
        const left = ((minVal - minBound) / span) * 100;
        const width = ((maxVal - minVal) / span) * 100;
        rangeFill.style.left = `${left}%`;
        rangeFill.style.width = `${width}%`;
      };

      const syncPriceInputsFromRange = () => {
        const minVal = Number.parseInt(rangeMin.value, 10);
        const maxVal = Number.parseInt(rangeMax.value, 10);
        priceMinInput.value = minVal > minBound ? String(minVal) : "";
        priceMaxInput.value = maxVal < maxBound ? String(maxVal) : "";
        updateRangeFill();
        updatePriceResetVisibility();
      };

      const syncRangeFromPriceInputs = () => {
        const minRaw = priceMinInput.value.trim();
        const maxRaw = priceMaxInput.value.trim();
        const minVal = minRaw
          ? Math.min(maxBound, Math.max(minBound, Number.parseInt(minRaw, 10) || minBound))
          : minBound;
        const maxVal = maxRaw
          ? Math.min(maxBound, Math.max(minBound, Number.parseInt(maxRaw, 10) || maxBound))
          : maxBound;
        rangeMin.value = String(Math.min(minVal, maxVal));
        rangeMax.value = String(Math.max(minVal, maxVal));
        updateRangeFill();
        updatePriceResetVisibility();
      };

      const onRangeInput = (event) => {
        let minVal = Number.parseInt(rangeMin.value, 10);
        let maxVal = Number.parseInt(rangeMax.value, 10);
        if (minVal > maxVal) {
          if (event.target === rangeMin) {
            maxVal = minVal;
            rangeMax.value = String(maxVal);
          } else {
            minVal = maxVal;
            rangeMin.value = String(minVal);
          }
        }
        syncPriceInputsFromRange();
        anchorEl = form.querySelector("[data-filter-anchor]");
        scheduleUpdate();
      };

      resetPriceRange = () => {
        rangeMin.value = String(minBound);
        rangeMax.value = String(maxBound);
        updateRangeFill();
      };

      rangeMin.addEventListener("input", onRangeInput);
      rangeMax.addEventListener("input", onRangeInput);
      priceMinInput.addEventListener("change", syncRangeFromPriceInputs);
      priceMaxInput.addEventListener("change", syncRangeFromPriceInputs);

      syncRangeFromPriceInputs();
    }
  }

  const resolveAnchor = () => {
    if (anchorEl && anchorEl.isConnected) return anchorEl;
    const checked = form.querySelector("[data-filter-checkbox]:checked");
    if (checked instanceof HTMLInputElement) {
      return checked.closest("[data-filter-option]");
    }
    const priceAnchor = form.querySelector("[data-filter-anchor]");
    if (priceAnchor instanceof HTMLElement && hasActiveFilters()) return priceAnchor;
    return null;
  };

  const positionPopover = () => {
    const anchor = resolveAnchor();
    if (!anchor) return;

    const rect = anchor.getBoundingClientRect();
    const popoverWidth = popover.offsetWidth || 200;
    const gap = 14;
    let left = rect.right + gap;
    let top = rect.top + rect.height / 2;

    if (left + popoverWidth > window.innerWidth - 8) {
      left = rect.left - popoverWidth - gap;
    }
    top = Math.max(12, Math.min(top, window.innerHeight - 12));

    popover.style.left = `${left}px`;
    popover.style.top = `${top}px`;
    popover.style.transform = "translateY(-50%)";
  };

  const showPopover = () => {
    if (!hasActiveFilters()) {
      hidePopover();
      return;
    }
    positionPopover();
    popover.classList.remove("hidden");
    popover.classList.add("is-visible");
    popover.setAttribute("aria-hidden", "false");
  };

  const hidePopover = () => {
    popover.classList.add("hidden");
    popover.classList.remove("is-visible");
    popover.setAttribute("aria-hidden", "true");
  };

  const buildParams = () => {
    const params = new URLSearchParams();
    new FormData(form).forEach((value, key) => {
      if (value !== "") params.append(key, value);
    });
    return params;
  };

  const updateCount = () => {
    if (activeController) activeController.abort();
    activeController = new AbortController();

    const params = hasActiveFilters() ? buildParams() : new URLSearchParams();
    const query = params.toString();

    fetch(query ? `${countUrl}?${query}` : countUrl, {
      headers: { Accept: "application/json" },
      signal: activeController.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error("count failed");
        return response.json();
      })
      .then((data) => {
        if (typeof data.count === "number") countNode.textContent = String(data.count);
        setSubmitLabels(data.label);
        updateResetAllVisibility();
        updatePriceResetVisibility();
        if (hasActiveFilters()) showPopover();
        else hidePopover();
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
      });
  };

  const scheduleUpdate = () => {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(updateCount, 200);
  };

  form.addEventListener("change", (event) => {
    const target = event.target;
    if (target instanceof HTMLInputElement && target.matches("[data-filter-checkbox]")) {
      anchorEl = target.checked ? target.closest("[data-filter-option]") : null;
    }
    if (target instanceof HTMLInputElement && target.type === "number") {
      anchorEl = form.querySelector("[data-filter-anchor]");
      updatePriceResetVisibility();
    }
    scheduleUpdate();
  });

  form.querySelectorAll('input[type="number"]').forEach((input) => {
    input.addEventListener("input", () => {
      anchorEl = form.querySelector("[data-filter-anchor]");
      updatePriceResetVisibility();
      scheduleUpdate();
    });
  });

  if (priceResetBtn instanceof HTMLButtonElement) {
    priceResetBtn.addEventListener("click", (event) => {
      event.preventDefault();
      clearPriceFilter();
    });
  }

  window.addEventListener("resize", () => {
    if (popover.classList.contains("is-visible")) positionPopover();
  });

  window.addEventListener(
    "scroll",
    () => {
      if (popover.classList.contains("is-visible")) positionPopover();
    },
    true,
  );

  document.addEventListener("click", (event) => {
    if (!popover.classList.contains("is-visible")) return;
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (popover.contains(target) || form.contains(target)) return;
    hidePopover();
  });

  if (resetAllLink instanceof HTMLAnchorElement) {
    resetAllLink.addEventListener("click", (event) => {
      event.preventDefault();
      const resetUrl = form.dataset.resetUrl || resetAllLink.href;
      if (window.location.search) {
        window.location.href = resetUrl;
        return;
      }
      clearFormFilters();
      updateCount();
    });
  }

  updateResetAllVisibility();
  updatePriceResetVisibility();
}

document.addEventListener("DOMContentLoaded", applyDynamicBits);
document.addEventListener("DOMContentLoaded", initCatalogMenu);
document.addEventListener("DOMContentLoaded", initSubCategoryFilters);
document.addEventListener("DOMContentLoaded", initCartQtyForms);
document.addEventListener("DOMContentLoaded", initQuickOrder);
document.addEventListener("DOMContentLoaded", initAuthModal);
document.addEventListener("DOMContentLoaded", initCityPicker);
document.addEventListener("DOMContentLoaded", initReviewRatingStars);
document.addEventListener("DOMContentLoaded", initProductGallery);
