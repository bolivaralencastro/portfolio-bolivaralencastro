(function (window, document) {
  "use strict";

  var PIXEL_ID = "1537864418068216";
  var loaded = false;
  var idleDelay = 9000;
  var fbq = window.fbq;

  if (!fbq) {
    fbq = function () {
      fbq.callMethod ? fbq.callMethod.apply(fbq, arguments) : fbq.queue.push(arguments);
    };
    window.fbq = fbq;
    window._fbq = window._fbq || fbq;
    fbq.push = fbq;
    fbq.loaded = true;
    fbq.version = "2.0";
    fbq.queue = [];
  }

  fbq("init", PIXEL_ID);
  fbq("track", "PageView");

  function loadPixel() {
    var firstScript;
    var script;

    if (loaded) {
      return;
    }

    loaded = true;
    firstScript = document.getElementsByTagName("script")[0];
    script = document.createElement("script");
    script.async = true;
    script.src = "https://connect.facebook.net/en_US/fbevents.js";
    firstScript.parentNode.insertBefore(script, firstScript);
  }

  function loadAfterPageSettles() {
    window.setTimeout(loadPixel, idleDelay);
  }

  window.addEventListener("pointerdown", loadPixel, { once: true, passive: true });
  window.addEventListener("keydown", loadPixel, { once: true });
  window.addEventListener("scroll", loadPixel, { once: true, passive: true });

  if (document.readyState === "complete") {
    loadAfterPageSettles();
  } else {
    window.addEventListener("load", loadAfterPageSettles, { once: true });
  }
})(window, document);
