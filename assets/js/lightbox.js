(function () {
  "use strict";

  var path = window.location.pathname || "";
  var isDetailPage = path.indexOf("/blog/") === 0 || path.indexOf("/projects/") === 0;

  if (!isDetailPage) {
    return;
  }

  if (document.querySelector(".lightbox")) {
    return;
  }

  var images = Array.prototype.slice.call(
    document.querySelectorAll("main img")
  ).filter(function (image) {
    if (image.closest(".author-card, .related-list, .project-item, .post-item, .video-link-card, footer, header, nav")) {
      return false;
    }

    if (image.classList.contains("author-card-photo")) {
      return false;
    }

    if ((image.getAttribute("src") || "").indexOf("/assets/images/author/") !== -1) {
      return false;
    }

    return true;
  });

  if (!images.length) {
    return;
  }

  var dialog = document.createElement("dialog");
  dialog.className = "site-lightbox";
  dialog.setAttribute("aria-label", "Visualizacao ampliada de imagem");
  dialog.innerHTML = [
    '<div class="site-lightbox-inner">',
    '  <div class="site-lightbox-topbar site-lightbox-ui">',
    '    <p class="site-lightbox-meta"></p>',
    '    <button type="button" class="site-lightbox-close" aria-label="Fechar visualizacao">×</button>',
    "  </div>",
    '  <div class="site-lightbox-stage">',
    '    <img src="" alt="Visualizacao ampliada da imagem selecionada">',
    "  </div>",
    '  <div class="site-lightbox-bottombar site-lightbox-ui">',
    '    <div class="site-lightbox-copy">',
    '      <p class="site-lightbox-caption"></p>',
    "    </div>",
    '    <div class="site-lightbox-controls">',
    '      <button type="button" class="site-lightbox-nav site-lightbox-prev" aria-label="Imagem anterior">←</button>',
    '      <button type="button" class="site-lightbox-nav site-lightbox-next" aria-label="Proxima imagem">→</button>',
    "    </div>",
    "  </div>",
    "</div>"
  ].join("");
  document.body.appendChild(dialog);

  var pageMeta = document.querySelector(".meta, .post-meta, .p-category");
  var stage = dialog.querySelector(".site-lightbox-stage");
  var stageImage = stage.querySelector("img");
  var meta = dialog.querySelector(".site-lightbox-meta");
  var caption = dialog.querySelector(".site-lightbox-caption");
  var closeButton = dialog.querySelector(".site-lightbox-close");
  var prevButton = dialog.querySelector(".site-lightbox-prev");
  var nextButton = dialog.querySelector(".site-lightbox-next");
  var activeIndex = 0;
  var uiTimer = null;
  var triggers = [];
  var touchUiMedia = window.matchMedia("(hover: none), (pointer: coarse), (max-width: 700px)");
  var desktopFullscreenMedia = window.matchMedia("(hover: hover) and (pointer: fine) and (min-width: 701px)");

  meta.textContent = pageMeta ? pageMeta.textContent.trim() : "Imagem ampliada";

  function syncUiMode() {
    dialog.classList.toggle("is-touch-ui", touchUiMedia.matches);
    if (touchUiMedia.matches && dialog.open) {
      dialog.classList.add("is-ui-visible");
      window.clearTimeout(uiTimer);
    }
  }

  function showUi() {
    dialog.classList.add("is-ui-visible");
    window.clearTimeout(uiTimer);
    if (touchUiMedia.matches) {
      return;
    }
    uiTimer = window.setTimeout(function () {
      if (dialog.open) {
        dialog.classList.remove("is-ui-visible");
      }
    }, 1400);
  }

  function getCaption(image) {
    var figcaption = image.closest("figure");
    if (figcaption) {
      var captionNode = figcaption.querySelector("figcaption");
      if (captionNode) {
        return captionNode.textContent.trim();
      }
    }

    var source = image.closest(".project-section, .section-block, article, section");
    if (source) {
      var postCaption = source.querySelector(".post-caption, .p-summary");
      if (postCaption) {
        return postCaption.textContent.trim();
      }
    }

    return image.getAttribute("alt") || "";
  }

  function syncStageImageBounds() {
    var stageStyle = window.getComputedStyle(stage);
    var horizontalPadding = parseFloat(stageStyle.paddingLeft || "0") + parseFloat(stageStyle.paddingRight || "0");
    var verticalPadding = parseFloat(stageStyle.paddingTop || "0") + parseFloat(stageStyle.paddingBottom || "0");
    stageImage.style.maxWidth = Math.max(0, Math.floor(stage.clientWidth - horizontalPadding)) + "px";
    stageImage.style.maxHeight = Math.max(0, Math.floor(stage.clientHeight - verticalPadding)) + "px";
  }

  function requestDesktopFullscreen() {
    if (!desktopFullscreenMedia.matches || typeof dialog.requestFullscreen !== "function" || document.fullscreenElement) {
      return;
    }

    dialog.requestFullscreen().catch(function (error) {
      console.info("Lightbox fullscreen unavailable:", error && error.name ? error.name : error);
    });
  }

  function exitDesktopFullscreen() {
    if (!document.fullscreenElement || (document.fullscreenElement !== dialog && !dialog.contains(document.fullscreenElement))) {
      return;
    }

    document.exitFullscreen().catch(function (error) {
      console.info("Lightbox fullscreen exit unavailable:", error && error.name ? error.name : error);
    });
  }

  function render(index) {
    activeIndex = index;
    var image = images[activeIndex];
    stageImage.src = image.currentSrc || image.src;
    stageImage.alt = image.alt;
    caption.textContent = getCaption(image);
    prevButton.disabled = images.length < 2;
    nextButton.disabled = images.length < 2;
    syncStageImageBounds();
  }

  function openLightbox(index) {
    dialog.showModal();
    render(index);
    showUi();
    requestDesktopFullscreen();
    closeButton.focus();
  }

  function closeLightbox() {
    dialog.close();
    exitDesktopFullscreen();
    window.clearTimeout(uiTimer);
    if (triggers[activeIndex]) {
      triggers[activeIndex].focus();
    }
  }

  images.forEach(function (image, index) {
    var trigger = image.closest("a[href]");
    var isWrappedImageLink = !!(trigger && trigger.querySelector("img") === image);

    image.style.cursor = "zoom-in";
    triggers[index] = isWrappedImageLink ? trigger : image;

    if (isWrappedImageLink) {
      trigger.setAttribute("aria-label", "Ampliar imagem");
      trigger.style.cursor = "zoom-in";
      trigger.addEventListener("click", function (event) {
        event.preventDefault();
        openLightbox(index);
      });
      trigger.addEventListener("keydown", function (event) {
        if (event.key === " ") {
          event.preventDefault();
          openLightbox(index);
        }
      });
      return;
    }

    image.tabIndex = 0;
    image.setAttribute("role", "button");
    image.setAttribute("aria-label", "Ampliar imagem");

    image.addEventListener("click", function () {
      openLightbox(index);
    });

    image.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openLightbox(index);
      }
    });
  });

  closeButton.addEventListener("click", closeLightbox);

  prevButton.addEventListener("click", function () {
    render((activeIndex - 1 + images.length) % images.length);
    showUi();
  });

  nextButton.addEventListener("click", function () {
    render((activeIndex + 1) % images.length);
    showUi();
  });

  dialog.addEventListener("click", function (event) {
    if (event.target === dialog) {
      closeLightbox();
      return;
    }
    showUi();
  });

  dialog.addEventListener("mousemove", showUi);
  dialog.addEventListener("touchstart", showUi, { passive: true });

  dialog.addEventListener("keydown", function (event) {
    showUi();

    if (event.key === "ArrowLeft") {
      event.preventDefault();
      render((activeIndex - 1 + images.length) % images.length);
    }

    if (event.key === "ArrowRight") {
      event.preventDefault();
      render((activeIndex + 1) % images.length);
    }
  });

  dialog.addEventListener("close", function () {
    dialog.classList.remove("is-ui-visible");
    stageImage.src = "";
    stageImage.style.maxWidth = "";
    stageImage.style.maxHeight = "";
  });

  syncUiMode();

  if (typeof touchUiMedia.addEventListener === "function") {
    touchUiMedia.addEventListener("change", syncUiMode);
  } else if (typeof touchUiMedia.addListener === "function") {
    touchUiMedia.addListener(syncUiMode);
  }

  window.addEventListener("resize", function () {
    syncUiMode();
    if (dialog.open) {
      syncStageImageBounds();
    }
  });
})();
