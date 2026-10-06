(function () {
  "use strict";

  var ALLOW = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";

  function load(button) {
    var id = button.getAttribute("data-youtube-id");
    if (!id || !/^[A-Za-z0-9_-]{6,20}$/.test(id)) {
      return;
    }
    var iframe = document.createElement("iframe");
    iframe.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(id) + "?autoplay=1&rel=0";
    iframe.title = button.getAttribute("data-title") || "Vídeo do YouTube";
    iframe.setAttribute("allow", ALLOW);
    iframe.setAttribute("allowfullscreen", "");
    iframe.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
    button.replaceWith(iframe);
    iframe.focus();
  }

  function init() {
    var buttons = document.querySelectorAll("button.yt-facade[data-youtube-id]");
    Array.prototype.forEach.call(buttons, function (button) {
      button.addEventListener("click", function () {
        load(button);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
