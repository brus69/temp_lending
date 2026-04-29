async function loadComponent(node) {
  const name = node.getAttribute("data-component");
  if (!name) return;

  try {
    const response = await fetch(`../components/${name}.html`);
    if (!response.ok) return;
    node.innerHTML = await response.text();
  } catch (error) {
    console.error(`Component load failed: ${name}`, error);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const componentNodes = [...document.querySelectorAll("[data-component]")];
  await Promise.all(componentNodes.map((node) => loadComponent(node)));
  document.dispatchEvent(new CustomEvent("components:loaded"));
});
