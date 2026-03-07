(() => {
  const FALLBACK_TEXT = "Imagem indisponivel";

  function buildFallbackNode() {
    const wrap = document.createElement("span");
    wrap.className = "media-fallback-content";

    const icon = document.createElement("span");
    icon.className = "media-fallback-icon";
    icon.setAttribute("aria-hidden", "true");

    const label = document.createElement("span");
    label.className = "media-fallback-label";
    label.textContent = FALLBACK_TEXT;

    wrap.append(icon, label);
    return wrap;
  }

  function ensureFrame(img) {
    const existing = img.closest(".post-row-cover, .project-cover, .media-fallback-frame");
    if (existing) {
      existing.classList.add("media-fallback-frame");
      return existing;
    }

    const frame = document.createElement("span");
    frame.className = "media-fallback-frame media-fallback-inline";

    const width = img.getAttribute("width");
    const height = img.getAttribute("height");
    if (width && height && Number(width) > 0 && Number(height) > 0) {
      frame.style.aspectRatio = `${width} / ${height}`;
    }

    img.parentNode.insertBefore(frame, img);
    frame.appendChild(img);
    return frame;
  }

  function applyFallback(img) {
    if (img.dataset.fallbackApplied === "1") return;
    img.dataset.fallbackApplied = "1";

    const frame = ensureFrame(img);
    frame.classList.add("is-broken");

    if (!frame.querySelector(".media-fallback-content")) {
      frame.appendChild(buildFallbackNode());
    }

    img.style.display = "none";
    img.setAttribute("aria-hidden", "true");
  }

  function bindImage(img) {
    if (!(img instanceof HTMLImageElement)) return;
    if (img.dataset.fallbackBound === "1") return;
    img.dataset.fallbackBound = "1";

    img.addEventListener("error", () => applyFallback(img), { once: true });

    if (img.complete && img.naturalWidth === 0) {
      applyFallback(img);
    }
  }

  function init() {
    document.querySelectorAll("img").forEach(bindImage);

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof Element)) return;

          if (node.tagName === "IMG") {
            bindImage(node);
            return;
          }

          node.querySelectorAll?.("img").forEach(bindImage);
        });
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
