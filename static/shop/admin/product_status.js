(function () {
  function syncProductStatusFields() {
    const activeInput = document.getElementById("id_is_active");
    const redirectRow = document.querySelector(".field-redirect_product");
    if (!activeInput || !redirectRow) return;

    const inactive = !activeInput.checked;
    redirectRow.classList.toggle("vi-product-redirect-hidden", !inactive);

    const select = redirectRow.querySelector("select");
    if (select instanceof HTMLSelectElement) {
      select.toggleAttribute("required", inactive);
      if (!inactive) {
        select.value = "";
      }
    }
  }

  document.addEventListener("DOMContentLoaded", syncProductStatusFields);
  document.addEventListener("change", (event) => {
    if (event.target instanceof HTMLInputElement && event.target.id === "id_is_active") {
      syncProductStatusFields();
    }
  });
})();
