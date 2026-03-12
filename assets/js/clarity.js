(function (window, document) {
  "use strict";

  var CLARITY_PROJECT_ID = "t8asclyhhx";

  function isConsentValue(value) {
    return value === "granted" || value === "denied";
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

  (function (c, l, a, r, i, t, y) {
    c[a] =
      c[a] ||
      function () {
        (c[a].q = c[a].q || []).push(arguments);
      };
    t = l.createElement(r);
    t.async = 1;
    t.src = "https://www.clarity.ms/tag/" + i;
    y = l.getElementsByTagName(r)[0];
    y.parentNode.insertBefore(t, y);
  })(window, document, "clarity", "script", CLARITY_PROJECT_ID);

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
