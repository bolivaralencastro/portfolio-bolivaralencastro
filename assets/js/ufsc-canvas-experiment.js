(function () {
  "use strict";

  var canvas = document.getElementById("ufsc-canvas");
  var track = document.getElementById("ufsc-scene-track");
  var status = document.getElementById("ufsc-render-status");
  var countNode = document.getElementById("ufsc-frame-count");
  var titleNode = document.getElementById("ufsc-frame-title");
  var noteNode = document.getElementById("ufsc-frame-note");
  var linkNode = document.getElementById("ufsc-frame-link");
  var jumpNodes = Array.prototype.slice.call(document.querySelectorAll("[data-ufsc-jump]"));

  if (!canvas || !track || !status || !countNode || !titleNode || !noteNode || !linkNode) {
    return;
  }

  var ctx = canvas.getContext("2d");

  if (!ctx) {
    status.textContent = "Canvas indisponivel neste navegador.";
    return;
  }

  var cover = new window.Image();
  var cards = Array.prototype.slice.call(document.querySelectorAll(".ufsc-source-card")).map(function (card, index) {
    return {
      index: index,
      node: card,
      image: card.querySelector("img"),
      title: card.getAttribute("data-title") || "",
      note: card.getAttribute("data-note") || "",
      link: card.getAttribute("data-link") || "#",
      width: 320,
      height: 420
    };
  });

  if (!cards.length) {
    status.textContent = "Nenhum frame configurado para a cena.";
    return;
  }

  cover.src = canvas.getAttribute("data-cover-src") || "";

  var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var supportsHtmlInCanvas = typeof ctx.drawElementImage === "function";
  var dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 1.25));
  var currentProgress = 0;
  var targetProgress = 0;
  var currentIndex = 0;
  var currentPointer = { x: 0, y: 0 };
  var targetPointer = { x: 0, y: 0 };
  var rafId = 0;
  var backgroundCanvas = document.createElement("canvas");
  var backgroundCtx = backgroundCanvas.getContext("2d");
  var lastCanvasWidth = 0;
  var lastCanvasHeight = 0;

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function lerp(start, end, amount) {
    return start + (end - start) * amount;
  }

  function buildRoundedRectPath(context, x, y, width, height, radius) {
    var r = Math.min(radius, width / 2, height / 2);

    context.beginPath();
    context.moveTo(x + r, y);
    context.lineTo(x + width - r, y);
    context.quadraticCurveTo(x + width, y, x + width, y + r);
    context.lineTo(x + width, y + height - r);
    context.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    context.lineTo(x + r, y + height);
    context.quadraticCurveTo(x, y + height, x, y + height - r);
    context.lineTo(x, y + r);
    context.quadraticCurveTo(x, y, x + r, y);
    context.closePath();
  }

  function measureCards() {
    cards.forEach(function (frame) {
      frame.width = frame.node.offsetWidth || 320;
      frame.height = frame.node.offsetHeight || Math.round(frame.width * 1.28);
    });
  }

  function resizeCanvas() {
    var rect = canvas.getBoundingClientRect();
    var nextWidth = Math.max(1, Math.round(rect.width * dpr));
    var nextHeight = Math.max(1, Math.round(rect.height * dpr));

    if (canvas.width !== nextWidth || canvas.height !== nextHeight) {
      canvas.width = nextWidth;
      canvas.height = nextHeight;
    }

    if (lastCanvasWidth !== rect.width || lastCanvasHeight !== rect.height) {
      lastCanvasWidth = rect.width;
      lastCanvasHeight = rect.height;
      rebuildBackground();
    }
  }

  function rebuildBackground() {
    var width = Math.max(1, Math.round(lastCanvasWidth));
    var height = Math.max(1, Math.round(lastCanvasHeight));
    var vignette;
    var dotSpacing = 22;
    var dotRadius = 1.1;
    var x;
    var y;

    if (!backgroundCtx || !width || !height) {
      return;
    }

    backgroundCanvas.width = width;
    backgroundCanvas.height = height;
    backgroundCtx.clearRect(0, 0, width, height);
    backgroundCtx.fillStyle = "#f8f7f2";
    backgroundCtx.fillRect(0, 0, width, height);

    backgroundCtx.save();
    backgroundCtx.fillStyle = "rgba(38, 38, 38, 0.12)";

    for (y = 11; y <= height; y += dotSpacing) {
      for (x = 11; x <= width; x += dotSpacing) {
        backgroundCtx.beginPath();
        backgroundCtx.arc(x, y, dotRadius, 0, Math.PI * 2);
        backgroundCtx.fill();
      }
    }

    backgroundCtx.restore();

    vignette = backgroundCtx.createRadialGradient(
      width * 0.5,
      height * 0.48,
      Math.max(40, width * 0.08),
      width * 0.5,
      height * 0.5,
      Math.max(width, height) * 0.72
    );
    vignette.addColorStop(0, "rgba(255, 255, 255, 0)");
    vignette.addColorStop(0.6, "rgba(255, 255, 255, 0)");
    vignette.addColorStop(1, "rgba(38, 38, 38, 0.08)");
    backgroundCtx.fillStyle = vignette;
    backgroundCtx.fillRect(0, 0, width, height);
  }

  function getScrollProgress() {
    var total = Math.max(track.offsetHeight - window.innerHeight, 1);
    var traveled = clamp(-track.getBoundingClientRect().top, 0, total);
    return traveled / total;
  }

  function updateFrameInfo(index) {
    var frame = cards[index];

    if (!frame) {
      return;
    }

    currentIndex = index;
    countNode.textContent = String(index + 1).padStart(2, "0") + " / " + String(cards.length).padStart(2, "0");
    titleNode.textContent = frame.title;
    noteNode.textContent = frame.note;
    linkNode.href = frame.link;

    jumpNodes.forEach(function (node, nodeIndex) {
      node.setAttribute("aria-current", nodeIndex === index ? "true" : "false");
    });
  }

  function wrapCanvasText(text, x, y, maxWidth, lineHeight) {
    var words = text.split(" ");
    var line = "";
    var lineIndex = 0;
    var maxLines = 3;

    words.forEach(function (word) {
      var testLine = line ? line + " " + word : word;
      var width = ctx.measureText(testLine).width;

      if (width > maxWidth && line && lineIndex < maxLines - 1) {
        ctx.fillText(line, x, y + lineIndex * lineHeight);
        line = word;
        lineIndex += 1;
        return;
      }

      line = testLine;
    });

    if (line) {
      ctx.fillText(line, x, y + lineIndex * lineHeight);
    }
  }

  function drawImageCover(image, x, y, width, height) {
    var sourceWidth = image.naturalWidth || image.width;
    var sourceHeight = image.naturalHeight || image.height;
    var sourceRatio;
    var targetRatio;
    var drawWidth;
    var drawHeight;
    var sourceX = 0;
    var sourceY = 0;

    if (!sourceWidth || !sourceHeight) {
      ctx.fillRect(x, y, width, height);
      return;
    }

    sourceRatio = sourceWidth / sourceHeight;
    targetRatio = width / height;

    if (sourceRatio > targetRatio) {
      drawHeight = sourceHeight;
      drawWidth = drawHeight * targetRatio;
      sourceX = (sourceWidth - drawWidth) * 0.5;
    } else {
      drawWidth = sourceWidth;
      drawHeight = drawWidth / targetRatio;
      sourceY = (sourceHeight - drawHeight) * 0.5;
    }

    ctx.drawImage(image, sourceX, sourceY, drawWidth, drawHeight, x, y, width, height);
  }

  function drawFallbackCard(frame, x, y, width, height, focus, visibility) {
    var radius = Math.max(14, width * 0.04);

    ctx.save();
    ctx.globalAlpha = visibility;
    buildRoundedRectPath(ctx, x, y, width, height, radius);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.clip();

    if (frame.image && frame.image.complete) {
      drawImageCover(frame.image, x, y, width, height);
    } else {
      ctx.fillStyle = "rgba(255, 255, 255, 0.16)";
      ctx.fillRect(x, y, width, height);
    }
    ctx.restore();

    ctx.save();
    ctx.globalAlpha = 0.08 + focus * 0.08;
    ctx.strokeStyle = "rgba(38, 38, 38, 0.18)";
    ctx.lineWidth = 1;
    buildRoundedRectPath(ctx, x, y, width, height, radius);
    ctx.stroke();
    ctx.restore();
  }

  function shouldUseHtmlInCanvas(distance) {
    return supportsHtmlInCanvas && distance < 0.24;
  }

  function renderScene() {
    var rect = canvas.getBoundingClientRect();
    var width = rect.width;
    var height = rect.height;
    var frameSpan = Math.max(cards.length - 1, 1);
    var phase;
    var nearestIndex;
    var progressDelta;
    var pointerDeltaX;
    var pointerDeltaY;

    resizeCanvas();

    currentProgress = lerp(currentProgress, targetProgress, prefersReducedMotion.matches ? 1 : 0.18);
    currentPointer.x = lerp(currentPointer.x, targetPointer.x, prefersReducedMotion.matches ? 1 : 0.22);
    currentPointer.y = lerp(currentPointer.y, targetPointer.y, prefersReducedMotion.matches ? 1 : 0.22);

    progressDelta = Math.abs(targetProgress - currentProgress);
    pointerDeltaX = Math.abs(targetPointer.x - currentPointer.x);
    pointerDeltaY = Math.abs(targetPointer.y - currentPointer.y);

    if (progressDelta < 0.001) {
      currentProgress = targetProgress;
    }

    if (pointerDeltaX < 0.002) {
      currentPointer.x = targetPointer.x;
    }

    if (pointerDeltaY < 0.002) {
      currentPointer.y = targetPointer.y;
    }

    phase = currentProgress * frameSpan;
    nearestIndex = clamp(Math.round(phase), 0, cards.length - 1);

    if (nearestIndex !== currentIndex) {
      updateFrameInfo(nearestIndex);
    }

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(backgroundCanvas, 0, 0, width, height);

    cards.forEach(function (frame, index) {
      var delta = index - phase;
      var distance = Math.abs(delta);
      var visibility = clamp(1 - distance / 1.5, 0, 1);
      var focus = clamp(1 - distance / 0.82, 0, 1);
      var baseSize = Math.min(width * 0.78, height * 0.78);
      var scale = 0.92 + focus * 0.22;
      var cardWidth = baseSize;
      var cardHeight = baseSize;
      var xOffset = delta * Math.min(cardWidth * 0.52, width * 0.11);
      var yOffset = distance * 8;
      var drawX = width * 0.5 + xOffset + currentPointer.x * (6 + focus * 4) - cardWidth * 0.5;
      var drawY = height * 0.5 + yOffset + currentPointer.y * (6 + focus * 4) - cardHeight * 0.5;
      var rotation = delta * -0.01 + currentPointer.x * 0.004;

      if (distance > 0.92 || visibility <= 0.04) {
        return;
      }

      ctx.save();
      ctx.translate(drawX + cardWidth * 0.5, drawY + cardHeight * 0.5);
      ctx.rotate(rotation);
      ctx.scale(scale, scale);
      ctx.translate(-(drawX + cardWidth * 0.5), -(drawY + cardHeight * 0.5));

      ctx.save();
      ctx.globalAlpha = 0.06 + focus * 0.08;
      ctx.fillStyle = "rgba(38, 38, 38, 0.18)";
      buildRoundedRectPath(ctx, drawX + 6, drawY + 10, cardWidth, cardHeight, 20);
      ctx.fill();
      ctx.restore();

      if (shouldUseHtmlInCanvas(distance)) {
        ctx.globalAlpha = visibility;
        ctx.drawElementImage(frame.node, drawX, drawY);
      } else {
        drawFallbackCard(frame, drawX, drawY, cardWidth, cardHeight, focus, visibility);
      }

      ctx.restore();
    });

    return progressDelta > 0.001 || pointerDeltaX > 0.002 || pointerDeltaY > 0.002;
  }

  function requestRender() {
    if (rafId) {
      return;
    }

    rafId = window.requestAnimationFrame(function () {
      rafId = 0;

      if (renderScene()) {
        requestRender();
      }
    });
  }

  function scrollToFrame(index) {
    var total = Math.max(track.offsetHeight - window.innerHeight, 1);
    var targetTop = track.offsetTop + (total * clamp(index, 0, cards.length - 1)) / Math.max(cards.length - 1, 1);

    window.scrollTo({
      top: targetTop,
      behavior: prefersReducedMotion.matches ? "auto" : "smooth"
    });
  }

  function handleScroll() {
    targetProgress = getScrollProgress();
    requestRender();
  }

  jumpNodes.forEach(function (node) {
    node.addEventListener("click", function () {
      scrollToFrame(Number(node.getAttribute("data-ufsc-jump")));
    });
  });

  cards.forEach(function (frame) {
    if (!frame.image) {
      return;
    }

    frame.image.addEventListener("load", function () {
      measureCards();
      requestRender();
    });
  });

  cover.addEventListener("load", function () {
    rebuildBackground();
    requestRender();
  });

  window.addEventListener("scroll", handleScroll, { passive: true });

  window.addEventListener("mousemove", function (event) {
    targetPointer.x = ((event.clientX / window.innerWidth) - 0.5) * 2;
    targetPointer.y = ((event.clientY / window.innerHeight) - 0.5) * 2;
    requestRender();
  });

  window.addEventListener("mouseleave", function () {
    targetPointer.x = 0;
    targetPointer.y = 0;
    requestRender();
  });

  window.addEventListener("keydown", function (event) {
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      scrollToFrame(currentIndex + 1);
    }

    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      scrollToFrame(currentIndex - 1);
    }
  });

  window.addEventListener("resize", function () {
    dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 1.25));
    measureCards();
    resizeCanvas();
    targetProgress = getScrollProgress();
    requestRender();
  });

  if (typeof prefersReducedMotion.addEventListener === "function") {
    prefersReducedMotion.addEventListener("change", function () {
      requestRender();
    });
  }

  measureCards();
  resizeCanvas();
  targetProgress = getScrollProgress();
  currentProgress = targetProgress;
  updateFrameInfo(0);
  status.textContent = supportsHtmlInCanvas
    ? "Cena otimizada. HTML in Canvas entra no card central quando a API experimental estiver ativa."
    : "Cena otimizada em Canvas 2D. HTML in Canvas entra quando a API experimental estiver disponivel.";
  requestRender();
})();
