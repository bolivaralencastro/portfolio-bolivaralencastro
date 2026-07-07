(function (window, document) {
  "use strict";

  var SOCIAL_HOSTS = {
    "facebook.com": "facebook",
    "www.facebook.com": "facebook",
    "m.facebook.com": "facebook",
    "github.com": "github",
    "instagram.com": "instagram",
    "www.instagram.com": "instagram",
    "linkedin.com": "linkedin",
    "www.linkedin.com": "linkedin",
    "x.com": "x",
    "twitter.com": "x",
    "youtube.com": "youtube",
    "www.youtube.com": "youtube"
  };
  var READ_THRESHOLDS = [50, 90];
  var firedReadThresholds = {};

  function slugFromPath(pathname) {
    var cleaned = pathname.replace(/^\/+|\/+$/g, "");
    var parts;

    if (!cleaned || cleaned === "index.html") {
      return "home";
    }

    parts = cleaned.split("/");
    return (parts[parts.length - 1] || cleaned).replace(/\.html$/, "") || "home";
  }

  function text(selector) {
    var element = document.querySelector(selector);
    return element ? element.textContent.replace(/\s+/g, " ").trim() : "";
  }

  function attr(selector, name) {
    var element = document.querySelector(selector);
    return element ? (element.getAttribute(name) || "").trim() : "";
  }

  function getPageType(pathname) {
    if (pathname === "/") {
      return "home";
    }
    if (pathname === "/about.html") {
      return "about";
    }
    if (pathname === "/blog.html" || pathname.indexOf("/blog/page/") === 0) {
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
    if (pathname === "/notes/" || pathname === "/notes/index.html" || pathname.indexOf("/notes/page/") === 0) {
      return "notes-index";
    }
    if (pathname.indexOf("/notes/") === 0) {
      return "note-detail";
    }
    if (pathname === "/links.html") {
      return "links";
    }
    return "site-page";
  }

  function getSiteSection(pathname) {
    if (pathname === "/" || pathname === "/about.html" || pathname === "/now.html" || pathname === "/links.html") {
      return "core";
    }
    if (pathname === "/blog.html" || pathname.indexOf("/blog/") === 0) {
      return "blog";
    }
    if (pathname === "/projects.html" || pathname.indexOf("/projects/") === 0) {
      return "projects";
    }
    if (pathname.indexOf("/notes") === 0) {
      return "notes";
    }
    return "site";
  }

  function getContentType(pageType) {
    if (pageType === "blog-post") {
      return "post";
    }
    if (pageType === "project-detail") {
      return "project";
    }
    if (pageType === "note-detail") {
      return "note";
    }
    if (pageType.indexOf("index") !== -1) {
      return "listing";
    }
    return "page";
  }

  function pageContext() {
    var pathname = window.location.pathname || "/";
    var pageType = getPageType(pathname);

    return {
      page_type: pageType,
      site_section: getSiteSection(pathname),
      content_type: getContentType(pageType),
      content_slug: slugFromPath(pathname),
      content_title: text("h1") || document.title,
      content_category: text(".p-category"),
      content_date: attr(".dt-published", "datetime").slice(0, 10),
      page_path: pathname,
      page_location: window.location.href,
      canonical_url: attr('link[rel="canonical"]', "href")
    };
  }

  function pushEvent(name, values) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(Object.assign({ event: name }, pageContext(), values || {}));
  }

  function setClarityContext(context) {
    var attempts = 0;
    var keys = [
      "page_type",
      "site_section",
      "content_type",
      "content_slug",
      "content_category"
    ];

    function trySet() {
      attempts += 1;

      if (typeof window.clarity === "function") {
        keys.forEach(function (key) {
          if (context[key]) {
            window.clarity("set", key, context[key]);
          }
        });
        return;
      }

      if (attempts < 20) {
        window.setTimeout(trySet, 500);
      }
    }

    trySet();
  }

  function linkLabel(link) {
    return (link.getAttribute("aria-label") || link.textContent || link.href || "").replace(/\s+/g, " ").trim();
  }

  function contentTypeFromHref(pathname) {
    if (pathname.indexOf("/projects/") === 0) {
      return "project";
    }
    if (pathname.indexOf("/blog/") === 0) {
      return "post";
    }
    if (pathname.indexOf("/notes/") === 0) {
      return "note";
    }
    return "";
  }

  function trackLinkClick(event) {
    var link = event.target.closest ? event.target.closest("a[href]") : null;
    var url;
    var socialNetwork;
    var targetContentType;

    if (!link) {
      return;
    }

    url = new URL(link.href, window.location.href);
    socialNetwork = SOCIAL_HOSTS[url.hostname];

    if (url.protocol === "mailto:" || url.protocol === "tel:") {
      pushEvent("portfolio_contact_click", {
        link_url: link.href,
        link_text: linkLabel(link),
        contact_type: url.protocol.replace(":", "")
      });
      return;
    }

    if (socialNetwork) {
      pushEvent("portfolio_social_click", {
        link_url: url.href,
        link_text: linkLabel(link),
        link_domain: url.hostname,
        social_network: socialNetwork
      });
      return;
    }

    if (url.hostname !== window.location.hostname) {
      pushEvent("portfolio_outbound_click", {
        link_url: url.href,
        link_text: linkLabel(link),
        link_domain: url.hostname
      });
      return;
    }

    targetContentType = contentTypeFromHref(url.pathname);
    if (targetContentType) {
      pushEvent("portfolio_content_click", {
        link_url: url.href,
        link_text: linkLabel(link),
        target_content_type: targetContentType,
        target_content_slug: slugFromPath(url.pathname)
      });
    }
  }

  function readableHeight() {
    var target = document.querySelector(".e-content") || document.querySelector("article") || document.documentElement;
    var rect = target.getBoundingClientRect();
    return Math.max(target.scrollHeight, rect.height, document.documentElement.scrollHeight - window.innerHeight);
  }

  function trackReadDepth() {
    var context = pageContext();
    var contentTypes = { post: true, project: true, note: true };
    var top;
    var height;
    var percent;

    if (!contentTypes[context.content_type]) {
      return;
    }

    top = window.scrollY || window.pageYOffset || 0;
    height = readableHeight();
    if (height <= 0) {
      return;
    }

    percent = Math.min(100, Math.round((top / height) * 100));
    READ_THRESHOLDS.forEach(function (threshold) {
      if (percent >= threshold && !firedReadThresholds[threshold]) {
        firedReadThresholds[threshold] = true;
        pushEvent("portfolio_read_depth", {
          read_percent: threshold
        });
      }
    });
  }

  function throttle(fn, wait) {
    var timeout = null;
    return function () {
      if (timeout) {
        return;
      }
      timeout = window.setTimeout(function () {
        timeout = null;
        fn();
      }, wait);
    };
  }

  function init() {
    var context = pageContext();

    pushEvent("portfolio_page_context", {});
    setClarityContext(context);
    document.addEventListener("click", trackLinkClick, true);
    window.addEventListener("scroll", throttle(trackReadDepth, 250), { passive: true });
    window.addEventListener("resize", throttle(trackReadDepth, 500), { passive: true });
    trackReadDepth();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})(window, document);
