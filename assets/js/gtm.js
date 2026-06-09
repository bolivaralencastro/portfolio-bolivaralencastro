(function (window, document) {
  "use strict";

  var GTM_CONTAINER_ID = "GTM-T3LNHCNR";
  var dataLayerName = "dataLayer";
  var firstScript = document.getElementsByTagName("script")[0];
  var script = document.createElement("script");
  var dataLayer = window[dataLayerName] = window[dataLayerName] || [];

  dataLayer.push({
    "gtm.start": new Date().getTime(),
    event: "gtm.js"
  });

  script.async = true;
  script.src = "https://www.googletagmanager.com/gtm.js?id=" + GTM_CONTAINER_ID;
  firstScript.parentNode.insertBefore(script, firstScript);
})(window, document);
