(function (window, document) {
  "use strict";

  var CLARITY_PROJECT_ID = "t8asclyhhx";
  var clarityScriptLoaded = false;
  var clarityScriptScheduled = false;

  function isConsentValue(value) {
    return value === "granted" || value === "denied";
  }

  function ensureClarityStub() {
    if (typeof window.clarity === "function") {
      return;
    }

    window.clarity = function () {
      (window.clarity.q = window.clarity.q || []).push(arguments);
    };
  }

  function getPageType(pathname) {
    if (pathname === "/") {
      return "home";
    }

    if (pathname === "/about.html") {
      return "about";
    }

    if (pathname === "/blog.html") {
      return "blog-index";
    }

    if (pathname.indexOf("/blog/") === 0) {
      return "blog-post";
    }

    if (pathname === "/projects.html") {
      return "projects-index";
    }

    if (pathname.indexOf("/projects/") === 0) {
      return "project-detail";
    }

    if (pathname === "/now.html") {
      return "now";
    }

    return "site-page";
  }

  function getSiteSection(pathname) {
    if (pathname === "/" || pathname === "/about.html" || pathname === "/now.html") {
      return "core";
    }

    if (pathname === "/blog.html" || pathname.indexOf("/blog/") === 0) {
      return "blog";
    }

    if (pathname === "/projects.html" || pathname.indexOf("/projects/") === 0) {
      return "projects";
    }

    return "site";
  }

  function loadClarityScript() {
    var firstScript;
    var script;

    if (clarityScriptLoaded) {
      return;
    }

    clarityScriptLoaded = true;
    script = document.createElement("script");
    script.async = true;
    script.src = "https://www.clarity.ms/tag/" + CLARITY_PROJECT_ID;
    firstScript = document.getElementsByTagName("script")[0];
    firstScript.parentNode.insertBefore(script, firstScript);
  }

  function scheduleClarityScript() {
    function scheduleAtIdle() {
      if ("requestIdleCallback" in window) {
        window.requestIdleCallback(loadClarityScript, { timeout: 5000 });
        return;
      }

      window.setTimeout(loadClarityScript, 3000);
    }

    if (clarityScriptScheduled) {
      return;
    }

    clarityScriptScheduled = true;

    if (document.readyState === "complete") {
      scheduleAtIdle();
      return;
    }

    window.addEventListener("load", scheduleAtIdle, { once: true });
  }

  ensureClarityStub();
  scheduleClarityScript();

  window.clarity("set", "page_type", getPageType(window.location.pathname || "/"));
  window.clarity("set", "site_section", getSiteSection(window.location.pathname || "/"));

  // Future cookie banners can call this helper with the user's current consent state.
  window.portfolioClarityConsent = function (adStorage, analyticsStorage) {
    if (!isConsentValue(adStorage) || !isConsentValue(analyticsStorage)) {
      return;
    }

    window.clarity("consentv2", {
      ad_Storage: adStorage,
      analytics_Storage: analyticsStorage
    });
  };
})(window, document);
