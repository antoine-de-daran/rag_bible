document.addEventListener("DOMContentLoaded", function () {
  "use strict";

  window.appState = {};

  function initPageHeader(appState) {
    const description = document.querySelector(".description");
    const verseRef = document.querySelector(".verse-ref-header");
    const header = document.querySelector(".page-header");
    const body = document.body;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    document.body.addEventListener("htmx:beforeRequest", function (evt) {
      if (evt.detail.elt.id !== "search-form") return;
      if (appState.isResultsActive) return;

      appState.isResultsActive = true;
      appState.resultsActiveTimestamp = Date.now();

      if (reducedMotion.matches) {
        body.classList.add("results-active");
        return;
      }

      const descHeight = description.offsetHeight;
      const descMarginTop = parseFloat(getComputedStyle(description).marginTop);
      const verseHeight = verseRef.offsetHeight;
      const verseMarginBottom = parseFloat(getComputedStyle(verseRef).marginBottom);
      const headerPaddingTop = parseFloat(getComputedStyle(header).paddingTop);
      const rootFontSize = parseFloat(
        getComputedStyle(document.documentElement).fontSize
      );
      const targetPaddingTop = 0.5 * rootFontSize;
      const paddingDelta = headerPaddingTop - targetPaddingTop;
      const bodyPaddingTop = parseFloat(getComputedStyle(body).paddingTop);
      const spacerBeforeHeight =
        header.getBoundingClientRect().top -
        body.getBoundingClientRect().top -
        bodyPaddingTop;

      body.style.paddingTop = (bodyPaddingTop + spacerBeforeHeight) + "px";
      body.classList.add("animating");

      const descTotal = descHeight + descMarginTop;
      const verseTotal = verseHeight + verseMarginBottom;
      const dockTotal = spacerBeforeHeight + paddingDelta;
      const totalDistance = descTotal + verseTotal + dockTotal;

      if (totalDistance <= 0) {
        body.style.paddingTop = "";
        body.classList.remove("animating");
        body.classList.add("results-active");
        return;
      }

      const startTime = performance.now();

      function frame(now) {
        const progress = Math.min((now - startTime) / ANIMATION_DURATION_MS, 1);
        const collapsed = progress * totalDistance;

        if (descTotal > 0) {
          const descProgress = Math.min(collapsed / descTotal, 1);
          description.style.opacity = String(1 - descProgress);
          description.style.maxHeight =
            (descHeight * (1 - descProgress)) + "px";
          description.style.marginTop =
            (descMarginTop * (1 - descProgress)) + "px";
        }

        const afterDesc = collapsed - descTotal;
        if (afterDesc > 0 && verseTotal > 0) {
          const verseProgress = Math.min(afterDesc / verseTotal, 1);
          verseRef.style.opacity = String(1 - verseProgress);
          verseRef.style.maxHeight =
            (verseHeight * (1 - verseProgress)) + "px";
          verseRef.style.marginBottom =
            (verseMarginBottom * (1 - verseProgress)) + "px";
        }

        const afterTextBlocks = collapsed - descTotal - verseTotal;
        if (afterTextBlocks > 0 && dockTotal > 0) {
          const dockProgress = Math.min(afterTextBlocks / dockTotal, 1);
          body.style.paddingTop =
            (bodyPaddingTop + spacerBeforeHeight * (1 - dockProgress)) + "px";
          header.style.paddingTop =
            (headerPaddingTop - paddingDelta * dockProgress) + "px";
        }

        if (progress >= 1) {
          description.style.cssText = "";
          verseRef.style.cssText = "";
          header.style.cssText = "";
          body.style.paddingTop = "";
          body.classList.add("results-active");
          body.classList.remove("animating");
          return;
        }

        requestAnimationFrame(frame);
      }

      requestAnimationFrame(frame);
    });
  }

  function initSearchBar(appState) {
    const input = document.getElementById("query-input");
    const clearButton = document.querySelector(".clear-button");
    if (!input) return;

    function updateValidation() {
      const hasContent = input.value.trim().length > 0;

      if (clearButton) {
        clearButton.classList.toggle("hidden", !hasContent);
      }
    }

    function handleClear() {
      input.value = "";
      updateValidation();
      input.focus();

      if (appState.embla) {
        appState.embla.destroy();
        appState.embla = null;
      }

      const resultsContainer = document.getElementById("results-container");
      if (!resultsContainer) return;

      const slides = resultsContainer.querySelectorAll(".carousel-slide");
      slides.forEach(function (slide) {
        const card = slide.querySelector(".result-card");
        if (card) {
          card.style.minHeight = card.offsetHeight + "px";
          card.innerHTML = "";
          card.classList.add("result-card--placeholder");
        }
      });

      const prevBtn = resultsContainer.querySelector(".carousel-arrow-prev");
      const nextBtn = resultsContainer.querySelector(".carousel-arrow-next");
      if (prevBtn) prevBtn.setAttribute("aria-disabled", "true");
      if (nextBtn) nextBtn.setAttribute("aria-disabled", "true");

      const dots = resultsContainer.querySelectorAll(".carousel-dot");
      dots.forEach(function (dot) {
        dot.classList.remove("active");
        dot.setAttribute("aria-selected", "false");
      });
    }

    input.addEventListener("input", updateValidation);

    if (clearButton) {
      clearButton.addEventListener("click", handleClear);
    }

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

  const ANIMATION_DURATION_MS = 630;

  function initCarousel(appState) {
    const resultsContainer = document.getElementById("results-container");
    if (!resultsContainer || typeof EmblaCarousel === "undefined") return;

    document.body.addEventListener("htmx:afterSwap", function (evt) {
      if (evt.detail.target.id !== "results-container") return;

      if (appState.revealTimeout) {
        clearTimeout(appState.revealTimeout);
        appState.revealTimeout = null;
      }

      if (appState.embla) {
        appState.embla.destroy();
        appState.embla = null;
      }

      const viewport = resultsContainer.querySelector(".carousel-viewport");
      if (!viewport) return;

      appState.embla = EmblaCarousel(viewport, {
        loop: false,
        align: "center"
      });

      const resultsContent = resultsContainer.querySelector(".results-content");
      if (resultsContent) {
        const elapsed = appState.resultsActiveTimestamp
          ? Date.now() - appState.resultsActiveTimestamp
          : ANIMATION_DURATION_MS;
        const remaining = Math.max(0, ANIMATION_DURATION_MS - elapsed);
        appState.revealTimeout = setTimeout(function () {
          resultsContent.classList.add("visible");
        }, remaining);
      }
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
