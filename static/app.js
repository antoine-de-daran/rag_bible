document.addEventListener("DOMContentLoaded", function () {
  "use strict";

  window.appState = {};

  function initPageHeader(appState) {
    document.body.addEventListener("htmx:beforeRequest", function (evt) {
      if (evt.detail.elt.id === "search-form") {
        document.body.classList.add("results-active");
        appState.isResultsActive = true;
      }
    });
  }

  function initSearchBar(appState) {
    const MIN_WORDS = 5;

    const input = document.getElementById("query-input");
    const searchButton = document.querySelector(".search-button");
    const clearButton = document.querySelector(".clear-button");
    const wordCountHint = document.getElementById("word-count-hint");
    if (!input) return;

    function wordCount(text) {
      const cleaned = text.replace(/<[^>]*>/g, "").trim();
      return cleaned ? cleaned.split(/\s+/).length : 0;
    }

    function updateValidation() {
      const count = wordCount(input.value);
      const hasContent = input.value.length > 0;

      if (count > 0 && count < MIN_WORDS) {
        wordCountHint.textContent = count + "/" + MIN_WORDS + " mots";
        wordCountHint.classList.remove("hidden");
      } else {
        wordCountHint.textContent = "";
        wordCountHint.classList.add("hidden");
      }

      if (clearButton) {
        clearButton.classList.toggle("hidden", !hasContent);
      }

      if (searchButton) {
        searchButton.setAttribute("aria-disabled", count < MIN_WORDS ? "true" : "false");
      }
    }

    function handleClear() {
      input.value = "";
      updateValidation();
      input.focus();
    }

    input.addEventListener("input", updateValidation);

    if (clearButton) {
      clearButton.addEventListener("click", handleClear);
    }

    document.body.addEventListener("htmx:configRequest", function (evt) {
      const params = evt.detail.parameters;
      if (params.query !== undefined && wordCount(params.query) < MIN_WORDS) {
        evt.preventDefault();
      }
    });

    updateValidation();

    const api = {
      focus: function () { input.focus(); },
      getValue: function () { return input.value; },
      setValue: function (value) {
        input.value = value;
        updateValidation();
      }
    };
    appState.searchBar = api;
    return api;
  }

  function initStatusMessages(appState) {
    const resultsContainer = document.getElementById("results-container");
    if (!resultsContainer) return;

    const originalHTML = resultsContainer.innerHTML;

    document.body.addEventListener("htmx:afterSwap", function (evt) {
      if (evt.detail.target.id !== "results-container") return;

      const retryButton = resultsContainer.querySelector(".retry-button");
      if (retryButton) {
        retryButton.addEventListener("click", function () {
          resultsContainer.innerHTML = originalHTML;
          if (appState.searchBar) appState.searchBar.focus();
        });
        retryButton.focus();
      }
    });
  }

  function initCarousel(appState) {
    const resultsContainer = document.getElementById("results-container");
    if (!resultsContainer || typeof EmblaCarousel === "undefined") return;

    document.body.addEventListener("htmx:afterSwap", function (evt) {
      if (evt.detail.target.id !== "results-container") return;

      if (appState.embla) {
        appState.embla.destroy();
        appState.embla = null;
      }

      const viewport = resultsContainer.querySelector(".carousel-viewport");
      if (!viewport) return;

      appState.embla = EmblaCarousel(viewport, {
        loop: false,
        align: "center",
        containScroll: "trimSnaps"
      });
    });
  }

  function initCarouselNavigation(appState) {
    const resultsContainer = document.getElementById("results-container");
    if (!resultsContainer) return;

    document.body.addEventListener("htmx:afterSwap", function (evt) {
      if (evt.detail.target.id !== "results-container") return;
      if (!appState.embla) return;

      const embla = appState.embla;
      const prevButton = resultsContainer.querySelector(".carousel-arrow-prev");
      const nextButton = resultsContainer.querySelector(".carousel-arrow-next");
      const dotsContainer = resultsContainer.querySelector(".carousel-dots");
      const viewport = resultsContainer.querySelector(".carousel-viewport");

      if (!prevButton || !nextButton || !dotsContainer) return;

      const dots = [];
      const slideCount = embla.scrollSnapList().length;

      for (let i = 0; i < slideCount; i++) {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "carousel-dot" + (i === 0 ? " active" : "");
        dot.setAttribute("role", "tab");
        dot.setAttribute("aria-label", "Aller au resultat " + (i + 1) + " de " + slideCount);
        dot.dataset.index = i;
        dotsContainer.appendChild(dot);
        dots.push(dot);
      }

      function updateNavigation() {
        const selected = embla.selectedScrollSnap();
        prevButton.setAttribute("aria-disabled", selected === 0 ? "true" : "false");
        nextButton.setAttribute("aria-disabled", selected === slideCount - 1 ? "true" : "false");
        dots.forEach(function (dot, idx) {
          dot.classList.toggle("active", idx === selected);
          dot.setAttribute("aria-selected", idx === selected ? "true" : "false");
        });
      }

      prevButton.addEventListener("click", function () {
        embla.scrollPrev();
      });

      nextButton.addEventListener("click", function () {
        embla.scrollNext();
      });

      dotsContainer.addEventListener("click", function (evt) {
        var dot = evt.target.closest(".carousel-dot");
        if (dot && dot.dataset.index !== undefined) {
          embla.scrollTo(parseInt(dot.dataset.index, 10));
        }
      });

      if (viewport) {
        viewport.addEventListener("keydown", function (evt) {
          if (evt.key === "ArrowLeft") {
            evt.preventDefault();
            embla.scrollPrev();
          } else if (evt.key === "ArrowRight") {
            evt.preventDefault();
            embla.scrollNext();
          }
        });
      }

      embla.on("select", updateNavigation);
      updateNavigation();
    });
  }

  function initHistorySidebar(appState) {
    const toggle = document.querySelector(".sidebar-toggle");
    const sidebar = document.getElementById("history-sidebar");
    const backdrop = document.querySelector(".sidebar-backdrop");
    const openIcon = document.querySelector(".sidebar-toggle-open");
    const closeIcon = document.querySelector(".sidebar-toggle-close");
    if (!toggle || !sidebar) return;

    function isMobile() {
      return window.innerWidth < 768;
    }

    function openSidebar() {
      document.body.classList.add("sidebar-open");
      toggle.setAttribute("aria-expanded", "true");
      toggle.setAttribute("aria-label", "Fermer l'historique");
      if (openIcon) openIcon.classList.add("hidden");
      if (closeIcon) closeIcon.classList.remove("hidden");
      if (backdrop && isMobile()) backdrop.classList.remove("hidden");
      appState.sidebarOpen = true;
    }

    function closeSidebar() {
      document.body.classList.remove("sidebar-open");
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "Ouvrir l'historique");
      if (openIcon) openIcon.classList.remove("hidden");
      if (closeIcon) closeIcon.classList.add("hidden");
      if (backdrop) backdrop.classList.add("hidden");
      appState.sidebarOpen = false;
      toggle.focus();
    }

    toggle.addEventListener("click", function () {
      if (appState.sidebarOpen) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    if (backdrop) {
      backdrop.addEventListener("click", closeSidebar);
    }

    document.addEventListener("keydown", function (evt) {
      if (evt.key === "Escape" && appState.sidebarOpen && isMobile()) {
        closeSidebar();
      }
    });

    const STORAGE_KEY = "bible_search_history";
    const MAX_ENTRIES = 20;
    const historyList = sidebar.querySelector(".history-list");

    function loadHistory() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
      } catch (e) {
        return [];
      }
    }

    function saveHistory(entries) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    }

    function addEntry(query) {
      const entries = loadHistory();
      const exists = entries.some(function (e) { return e.query === query; });
      if (exists) return;
      entries.unshift({
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
        query: query,
        timestamp: Date.now()
      });
      if (entries.length > MAX_ENTRIES) entries.length = MAX_ENTRIES;
      saveHistory(entries);
      renderHistory();
    }

    function removeEntry(id) {
      const entries = loadHistory().filter(function (e) { return e.id !== id; });
      saveHistory(entries);
      renderHistory();
    }

    function renderHistory() {
      if (!historyList) return;
      historyList.innerHTML = "";
      const entries = loadHistory();
      entries.forEach(function (entry) {
        const div = document.createElement("div");
        div.className = "history-entry";

        const queryBtn = document.createElement("button");
        queryBtn.type = "button";
        queryBtn.className = "history-query";
        queryBtn.textContent = entry.query;
        queryBtn.title = entry.query;

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "history-delete";
        deleteBtn.setAttribute("aria-label", "Supprimer : " + entry.query);
        deleteBtn.textContent = "\u00d7";

        queryBtn.addEventListener("click", function () {
          if (appState.searchBar) {
            appState.searchBar.setValue(entry.query);
            htmx.trigger(document.getElementById("search-form"), "submit");
          }
          if (isMobile()) closeSidebar();
        });

        deleteBtn.addEventListener("click", function () {
          removeEntry(entry.id);
        });

        div.appendChild(queryBtn);
        div.appendChild(deleteBtn);
        historyList.appendChild(div);
      });
    }

    document.body.addEventListener("htmx:afterSwap", function (evt) {
      if (evt.detail.target.id !== "results-container") return;
      const resultsContainer = document.getElementById("results-container");
      if (resultsContainer && resultsContainer.querySelector(".carousel-viewport")) {
        const query = appState.searchBar ? appState.searchBar.getValue() : "";
        if (query) addEntry(query);
      }
    });

    renderHistory();
    appState.sidebar = { open: openSidebar, close: closeSidebar };
  }

  function initOfflineDetection() {
    const banner = document.querySelector(".offline-banner");
    if (!banner) return;

    function update() {
      if (navigator.onLine) {
        banner.classList.add("hidden");
      } else {
        banner.classList.remove("hidden");
      }
    }

    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    update();
  }

  initPageHeader(window.appState);
  initSearchBar(window.appState);
  initStatusMessages(window.appState);
  initCarousel(window.appState);
  initCarouselNavigation(window.appState);
  initHistorySidebar(window.appState);
  initOfflineDetection();

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/service-worker.js");
  }
});
