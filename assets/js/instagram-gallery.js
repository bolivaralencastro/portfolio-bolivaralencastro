(function () {
  var images = Array.prototype.slice.call(
    document.querySelectorAll(
      ".project-opening-image img, .hero-image img, .grid-item img"
    )
  );
  var dialog = document.querySelector(".lightbox");
  var pageMeta = document.querySelector(".meta");

  if (!images.length || !dialog || typeof dialog.showModal !== "function") {
    return;
  }

  var stageImage = dialog.querySelector(".lightbox-stage img");
  var meta = dialog.querySelector(".lightbox-meta");
  var caption = dialog.querySelector(".lightbox-caption");
  var closeButton = dialog.querySelector(".lightbox-close");
  var prevButton = dialog.querySelector(".lightbox-prev");
  var nextButton = dialog.querySelector(".lightbox-next");
  var activeIndex = 0;
  var uiTimer = null;

  if (pageMeta) {
    meta.textContent = pageMeta.textContent.trim();
  }

  function showUi() {
    dialog.classList.add("is-ui-visible");
    window.clearTimeout(uiTimer);
    uiTimer = window.setTimeout(function () {
      if (dialog.open) {
        dialog.classList.remove("is-ui-visible");
      }
    }, 1400);
  }

  function getLightboxCopy(image) {
    var section = image.closest(".project-section");
    var text = image.getAttribute("alt") || "";

    if (section) {
      var postCaption = section.querySelector(".post-caption");
      if (postCaption) {
        text = postCaption.textContent.trim();
      }
    }

    return text;
  }

  function render(index) {
    activeIndex = index;
    var image = images[activeIndex];
    var copy = getLightboxCopy(image);

    stageImage.src = image.currentSrc || image.src;
    stageImage.alt = image.alt;
    caption.textContent = copy;
    prevButton.disabled = images.length < 2;
    nextButton.disabled = images.length < 2;
    syncStageImageBounds();
  }

  function syncStageImageBounds() {
    var stageRect = dialog.querySelector(".lightbox-stage").getBoundingClientRect();
    stageImage.style.maxWidth = Math.max(0, Math.floor(stageRect.width)) + "px";
    stageImage.style.maxHeight = Math.max(0, Math.floor(stageRect.height)) + "px";
  }

  function openLightbox(index) {
    dialog.showModal();
    render(index);
    showUi();
    closeButton.focus();
  }

  function closeLightbox() {
    dialog.close();
    window.clearTimeout(uiTimer);
    var source = images[activeIndex];
    if (source) {
      source.focus();
    }
  }

  images.forEach(function (image, index) {
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
    }
    showUi();
  });

  dialog.addEventListener("mousemove", function () {
    showUi();
  });

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

  window.addEventListener("resize", function () {
    if (dialog.open) {
      syncStageImageBounds();
    }
  });
})();
