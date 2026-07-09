(function () {
  "use strict";

  var controls = document.querySelector("[data-project-filters]");
  var projects = Array.prototype.slice.call(document.querySelectorAll("[data-project-category]"));

  if (!controls || projects.length === 0) {
    return;
  }

  var buttons = Array.prototype.slice.call(controls.querySelectorAll("[data-project-filter]"));
  var validFilters = { todos: true, design: true, fotografia: true };

  function readFilterFromUrl() {
    var params = new URLSearchParams(window.location.search);
    var value = params.get("categoria") || "todos";
    return validFilters[value] ? value : "todos";
  }

  function writeFilterToUrl(filter) {
    var url = new URL(window.location.href);
    if (filter === "todos") {
      url.searchParams.delete("categoria");
    } else {
      url.searchParams.set("categoria", filter);
    }
    window.history.replaceState({}, "", url);
  }

  function applyFilter(filter, updateUrl) {
    projects.forEach(function (project) {
      var category = project.getAttribute("data-project-category");
      project.hidden = filter !== "todos" && category !== filter;
    });

    buttons.forEach(function (button) {
      var isActive = button.getAttribute("data-project-filter") === filter;
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });

    if (updateUrl) {
      writeFilterToUrl(filter);
    }
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      var filter = button.getAttribute("data-project-filter") || "todos";
      applyFilter(validFilters[filter] ? filter : "todos", true);
    });
  });

  applyFilter(readFilterFromUrl(), false);
})();
