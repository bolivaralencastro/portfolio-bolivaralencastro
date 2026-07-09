(function (window, document) {
  "use strict";

  var GTM_CONTAINER_ID = "GTM-T3LNHCNR";
  var dataLayerName = "dataLayer";
  var dataLayer = window[dataLayerName] = window[dataLayerName] || [];
  var loaded = false;
  var idleDelay = 9000;

  dataLayer.push({
    "gtm.start": new Date().getTime(),
    event: "gtm.js"
  });

  function loadGtm() {
    var firstScript;
    var script;

    if (loaded) {
      return;
    }

    loaded = true;
    firstScript = document.getElementsByTagName("script")[0];
    script = document.createElement("script");
    script.async = true;
    script.src = "https://www.googletagmanager.com/gtm.js?id=" + GTM_CONTAINER_ID;
    firstScript.parentNode.insertBefore(script, firstScript);
  }

  function loadAfterPageSettles() {
    window.setTimeout(loadGtm, idleDelay);
  }

  window.addEventListener("pointerdown", loadGtm, { once: true, passive: true });
  window.addEventListener("keydown", loadGtm, { once: true });
  window.addEventListener("scroll", loadGtm, { once: true, passive: true });

  if (document.readyState === "complete") {
    loadAfterPageSettles();
  } else {
    window.addEventListener("load", loadAfterPageSettles, { once: true });
  }
})(window, document);
