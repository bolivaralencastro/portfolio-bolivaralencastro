(() => {
  const root = document.documentElement;
  const header = document.querySelector("header");
  const nav = header?.querySelector('nav[aria-label="Navegação principal"]');

  if (!header || !nav || typeof HTMLDialogElement === "undefined") {
    return;
  }

  const navList = nav.querySelector("ul");

  if (!navList) {
    return;
  }

  root.classList.add("has-mobile-nav");

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "mobile-menu-toggle";
  toggle.setAttribute("aria-controls", "mobile-nav-overlay");
  toggle.setAttribute("aria-expanded", "false");
  toggle.setAttribute("aria-label", "Abrir menu principal");
  toggle.textContent = "Menu";
  nav.prepend(toggle);

  const dialog = document.createElement("dialog");
  dialog.className = "mobile-nav-overlay";
  dialog.id = "mobile-nav-overlay";
  dialog.setAttribute("aria-label", "Navegação principal");

  const shell = document.createElement("div");
  shell.className = "mobile-nav-dialog";

  const closeRow = document.createElement("div");
  closeRow.className = "mobile-nav-close-row";

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "mobile-nav-close";
  closeButton.textContent = "Fechar";
  closeRow.append(closeButton);

  const panel = document.createElement("nav");
  panel.className = "mobile-nav-panel";
  panel.setAttribute("aria-label", "Menu mobile");
  panel.append(navList.cloneNode(true));

  shell.append(closeRow, panel);
  dialog.append(shell);
  document.body.append(dialog);

  let lastActive = null;

  function openMenu() {
    lastActive = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    toggle.setAttribute("aria-expanded", "true");
    root.classList.add("mobile-nav-open");
    dialog.showModal();
    closeButton.focus();
  }

  function closeMenu() {
    if (dialog.open) {
      dialog.close();
    }
    toggle.setAttribute("aria-expanded", "false");
    root.classList.remove("mobile-nav-open");
    lastActive?.focus();
  }

  toggle.addEventListener("click", () => {
    if (dialog.open) {
      closeMenu();
      return;
    }
    openMenu();
  });

  closeButton.addEventListener("click", closeMenu);

  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeMenu();
  });

  panel.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeMenu);
  });

  const mobileMedia = window.matchMedia("(max-width: 700px)");
  const syncViewport = (event) => {
    if (!event.matches) {
      closeMenu();
    }
  };

  if (typeof mobileMedia.addEventListener === "function") {
    mobileMedia.addEventListener("change", syncViewport);
  } else if (typeof mobileMedia.addListener === "function") {
    mobileMedia.addListener(syncViewport);
  }
})();
