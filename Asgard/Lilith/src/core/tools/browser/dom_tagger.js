function getInteractiveState() {
  let idCounter = 1;
  const actions_tree = [];
  const VIEWPORT_MARGIN = 400;

  const isVisible = (elem) => {
    const style = window.getComputedStyle(elem);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return false;

    const rect = elem.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return false;

    if (rect.bottom < 0 || rect.top > window.innerHeight + VIEWPORT_MARGIN) return false;

    return true;
  };

  const selectors =
    'a, button, input, textarea, select, [role="button"], [role="link"], [tabindex]:not([tabindex="-1"])';
  const elements = document.querySelectorAll(selectors);

  elements.forEach((el) => {
    if (!isVisible(el)) return;

    el.setAttribute("lilith-id", idCounter.toString());

    let text =
      el.innerText ||
      el.value ||
      el.placeholder ||
      el.getAttribute("aria-label") ||
      el.alt ||
      "";
    text = (text || "").trim().substring(0, 80);

    actions_tree.push({
      id: idCounter,
      role: el.tagName.toLowerCase(),
      type: el.type || undefined,
      text: text !== "" ? text : "[Icono/Vacío]",
    });

    idCounter++;
  });

  const scrollY = window.scrollY || window.pageYOffset || 0;
  const bottom =
    window.innerHeight + scrollY >= document.body.offsetHeight - 50;

  return {
    meta: {
      viewport_position:
        scrollY === 0 ? "top" : bottom ? "bottom" : "middle",
      can_scroll_down:
        window.innerHeight + scrollY < document.body.offsetHeight - 50,
      can_scroll_up: scrollY > 0,
    },
    actions_tree: actions_tree,
  };
}

return getInteractiveState();
