/**
 * PC Control — Browser Action Recorder
 * Injected via CDP Page.addScriptToEvaluateOnNewDocument.
 * Persists actions in sessionStorage to survive page navigations.
 */
(function () {
  if (window.__pcRecorderActive) return;
  window.__pcRecorderActive = true;

  const STORAGE_KEY = "__pcRecordedActions";

  // Load previous actions from sessionStorage (survives navigation)
  let actions;
  try {
    actions = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    actions = [];
  }
  window.__pcRecordedActions = actions;

  const startTime = Date.now();

  function getSelector(el) {
    if (!el || el === document.body || el === document.documentElement) return "body";
    if (el.dataset && el.dataset.testid) return `[data-testid="${el.dataset.testid}"]`;
    if (el.id && el.id.length < 50 && !/^\d|^:/.test(el.id)) return `#${CSS.escape(el.id)}`;
    const ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel) return `[aria-label="${ariaLabel}"]`;
    if (el.name && ["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName)) {
      return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
    }
    if (["BUTTON", "A"].includes(el.tagName) || el.getAttribute("role") === "button") {
      const text = el.innerText?.trim();
      if (text && text.length < 80 && !text.includes("\n")) return `text=${text}`;
    }
    if (el.placeholder) return `[placeholder="${el.placeholder}"]`;
    return buildCssPath(el);
  }

  function buildCssPath(el) {
    const parts = [];
    let current = el;
    while (current && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      if (current.className && typeof current.className === "string") {
        const classes = current.className.trim().split(/\s+/)
          .filter((c) => c.length < 30 && !/^[0-9]/.test(c)).slice(0, 2);
        if (classes.length) selector += "." + classes.map(CSS.escape).join(".");
      }
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter((s) => s.tagName === current.tagName);
        if (siblings.length > 1) selector += `:nth-child(${siblings.indexOf(current) + 1})`;
      }
      parts.unshift(selector);
      current = current.parentElement;
      if (parts.length >= 3) break;
    }
    return parts.join(" > ");
  }

  function persist() {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(window.__pcRecordedActions));
    } catch { /* storage full — unlikely for action data */ }
  }

  function record(action) {
    action.timestamp = Date.now() - startTime;
    action.url = window.location.href;
    window.__pcRecordedActions.push(action);
    persist();
  }

  // ── Click
  document.addEventListener("click", (e) => {
    const el = e.target;
    record({
      type: "click", selector: getSelector(el), tagName: el.tagName,
      text: el.innerText?.trim().slice(0, 100) || "", x: e.clientX, y: e.clientY,
    });
  }, true);

  // ── Input (debounced per element)
  document.addEventListener("input", (e) => {
    const el = e.target;
    if (!["INPUT", "TEXTAREA"].includes(el.tagName)) return;
    const sel = getSelector(el);
    const last = window.__pcRecordedActions[window.__pcRecordedActions.length - 1];
    if (last && last.type === "fill" && last.selector === sel) {
      last.value = el.type === "password" ? "***" : el.value;
      last.timestamp = Date.now() - startTime;
      persist();
      return;
    }
    record({
      type: "fill", selector: sel,
      value: el.type === "password" ? "***" : el.value,
      inputType: el.type || "text",
    });
  }, true);

  // ── Select / Checkbox / Radio
  document.addEventListener("change", (e) => {
    const el = e.target;
    if (el.tagName === "SELECT") {
      record({ type: "select", selector: getSelector(el), value: el.value,
        text: el.options[el.selectedIndex]?.text || "" });
    } else if (el.type === "checkbox" || el.type === "radio") {
      record({ type: el.checked ? "check" : "uncheck", selector: getSelector(el) });
    }
  }, true);

  // ── Key presses (Enter, Tab, Escape)
  document.addEventListener("keydown", (e) => {
    if (["Enter", "Tab", "Escape"].includes(e.key)) {
      record({ type: "key", key: e.key, selector: getSelector(e.target) });
    }
  }, true);

  // ── Navigation detection
  let lastUrl = window.location.href;
  const checkNav = () => {
    if (window.location.href !== lastUrl) {
      record({ type: "navigation", from: lastUrl, to: window.location.href });
      lastUrl = window.location.href;
    }
  };
  window.addEventListener("popstate", checkNav);
  window.addEventListener("hashchange", checkNav);
  // Periodic check for SPA navigations
  setInterval(checkNav, 500);

  console.log("[PC Control] Recorder active — actions persist via sessionStorage");
})();
