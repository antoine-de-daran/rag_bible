document.addEventListener("DOMContentLoaded", function () {
  "use strict";

  window.appState = {};

  var MOBILE_MQ = window.matchMedia("(max-width: 767px)");

  function initPageHeader(appState) {
    var description = document.querySelector(".description");
    var verseRef = document.querySelector(".verse-ref-header");
    var header = document.querySelector(".page-header");
    var body = document.body;
    var reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

    document.body.addEventListener("htmx:beforeRequest", function (evt) {
      if (evt.detail.elt.id !== "search-form") return;
      if (appState.isResultsActive) return;

      appState.isResultsActive = true;
      appState.resultsActiveTimestamp = Date.now();

      if (reducedMotion.matches) {
        body.classList.add("results-active");
        return;
      }

      var descHeight = description.offsetHeight;
      var descMarginTop = parseFloat(
        getComputedStyle(description).marginTop
      );
      var verseHeight = verseRef.offsetHeight;
      var verseMarginBottom = parseFloat(
        getComputedStyle(verseRef).marginBottom
      );
      var headerPaddingTop = parseFloat(
        getComputedStyle(header).paddingTop
      );
      var rootFontSize = parseFloat(
        getComputedStyle(document.documentElement).fontSize
      );
      var targetPaddingTop = 0.5 * rootFontSize;
      var paddingDelta = headerPaddingTop - targetPaddingTop;
      var bodyPaddingTop = parseFloat(
        getComputedStyle(body).paddingTop
      );
      var spacerBeforeHeight =
        header.getBoundingClientRect().top -
        body.getBoundingClientRect().top -
        bodyPaddingTop;

      body.style.paddingTop =
        (bodyPaddingTop + spacerBeforeHeight) + "px";
      body.classList.add("animating");
      header.style.willChange = "padding";

      var descTotal = descHeight + descMarginTop;
      var verseTotal = verseHeight + verseMarginBottom;
      var dockTotal = spacerBeforeHeight + paddingDelta;
      var totalDistance = descTotal + verseTotal + dockTotal;

      if (totalDistance <= 0) {
        body.style.paddingTop = "";
        body.classList.remove("animating");
        body.classList.add("results-active");
        header.style.willChange = "";
        return;
      }

      var startTime = performance.now();

      function frame(now) {
        var progress = Math.min(
          (now - startTime) / ANIMATION_DURATION_MS, 1
        );
        var collapsed = progress * totalDistance;

        if (descTotal > 0) {
          var descProgress = Math.min(collapsed / descTotal, 1);
          description.style.opacity = String(1 - descProgress);
          description.style.maxHeight =
            (descHeight * (1 - descProgress)) + "px";
          description.style.marginTop =
            (descMarginTop * (1 - descProgress)) + "px";
        }

        var afterDesc = collapsed - descTotal;
        if (afterDesc > 0 && verseTotal > 0) {
          var verseProgress = Math.min(afterDesc / verseTotal, 1);
          verseRef.style.opacity = String(1 - verseProgress);
          verseRef.style.maxHeight =
            (verseHeight * (1 - verseProgress)) + "px";
          verseRef.style.marginBottom =
            (verseMarginBottom * (1 - verseProgress)) + "px";
        }

        var afterTextBlocks = collapsed - descTotal - verseTotal;
        if (afterTextBlocks > 0 && dockTotal > 0) {
          var dockProgress = Math.min(
            afterTextBlocks / dockTotal, 1
          );
          body.style.paddingTop =
            (bodyPaddingTop +
              spacerBeforeHeight * (1 - dockProgress)) + "px";
          header.style.paddingTop =
            (headerPaddingTop -
              paddingDelta * dockProgress) + "px";
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
    var input = document.getElementById("query-input");
    var clearButton = document.querySelector(".clear-button");
    if (!input) return;

    function updateValidation() {
      var hasContent = input.value.trim().length > 0;

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

      var resultsContainer =
        document.getElementById("results-container");
      if (!resultsContainer) return;

      var slides =
        resultsContainer.querySelectorAll(".carousel-slide");
      slides.forEach(function (slide) {
        var card = slide.querySelector(".result-card");
        if (card) {
          card.style.minHeight = card.offsetHeight + "px";
          card.innerHTML = "";
          card.classList.add("result-card--placeholder");
        }
      });

      var prevBtn = resultsContainer.querySelector(
        ".carousel-arrow-prev"
      );
      var nextBtn = resultsContainer.querySelector(
        ".carousel-arrow-next"
      );
      if (prevBtn) prevBtn.setAttribute("aria-disabled", "true");
      if (nextBtn) nextBtn.setAttribute("aria-disabled", "true");

      var dots =
        resultsContainer.querySelectorAll(".carousel-dot");
      dots.forEach(function (dot) {
        dot.classList.remove("active");
        dot.setAttribute("aria-pressed", "false");
      });
    }

    input.addEventListener("input", updateValidation);

    if (clearButton) {
      clearButton.addEventListener("click", handleClear);
    }

    updateValidation();

    var api = {
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

  function initLoadingStates() {
    var input = document.getElementById("query-input");

    document.body.addEventListener("htmx:beforeRequest", function (evt) {
      if (evt.detail.elt.id !== "search-form") return;
      if (input) input.setAttribute("aria-busy", "true");
    });

    document.body.addEventListener("htmx:afterRequest", function (evt) {
      if (evt.detail.elt.id !== "search-form") return;
      if (input) input.removeAttribute("aria-busy");
    });
  }

  function initStatusMessages(appState) {
    var resultsContainer =
      document.getElementById("results-container");
    if (!resultsContainer) return;

    var originalHTML = resultsContainer.innerHTML;

    document.body.addEventListener("htmx:afterSwap", function (evt) {
      if (evt.detail.target.id !== "results-container") return;

      var retryButton =
        resultsContainer.querySelector(".retry-button");
      if (retryButton) {
        retryButton.addEventListener("click", function () {
          resultsContainer.innerHTML = originalHTML;
          if (appState.searchBar) appState.searchBar.focus();
        });
        retryButton.focus();
      }
    });
  }

  var ANIMATION_DURATION_MS = 630;

  function initCarousel(appState) {
    var resultsContainer =
      document.getElementById("results-container");
    if (!resultsContainer || typeof EmblaCarousel === "undefined") {
      return;
    }

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

      var viewport =
        resultsContainer.querySelector(".carousel-viewport");
      if (!viewport) return;

      appState.embla = EmblaCarousel(viewport, {
        loop: false,
        align: "center",
        startIndex: 1
      });

      var slides = viewport.querySelectorAll(
        ".carousel-slide:not(.carousel-slide--spacer)"
      );
      var maxHeight = 0;
      slides.forEach(function (slide) {
        var h = slide.scrollHeight;
        if (h > maxHeight) maxHeight = h;
      });
      if (maxHeight > 0) {
        viewport.style.minHeight = maxHeight + "px";
      }

      var resultsContent =
        resultsContainer.querySelector(".results-content");
      if (resultsContent) {
        var elapsed = appState.resultsActiveTimestamp
          ? Date.now() - appState.resultsActiveTimestamp
          : ANIMATION_DURATION_MS;
        var remaining = Math.max(
          0, ANIMATION_DURATION_MS - elapsed
        );
        appState.revealTimeout = setTimeout(function () {
          resultsContent.classList.add("visible");
        }, remaining);
      }
    });
  }

  function initCarouselNavigation(appState) {
    var resultsContainer =
      document.getElementById("results-container");
    if (!resultsContainer) return;

    document.body.addEventListener("htmx:afterSwap", function (evt) {
      if (evt.detail.target.id !== "results-container") return;
      if (!appState.embla) return;

      var embla = appState.embla;
      var prevButton = resultsContainer.querySelector(
        ".carousel-arrow-prev"
      );
      var nextButton = resultsContainer.querySelector(
        ".carousel-arrow-next"
      );
      var dotsContainer =
        resultsContainer.querySelector(".carousel-dots");
      var viewport =
        resultsContainer.querySelector(".carousel-viewport");
      var liveRegion =
        resultsContainer.querySelector(".carousel-live");

      if (!prevButton || !nextButton || !dotsContainer) return;

      var totalSlides = embla.scrollSnapList().length;
      var realCount = totalSlides - 2;
      var dots = [];

      for (var i = 0; i < realCount; i++) {
        var dot = document.createElement("button");
        dot.type = "button";
        dot.className =
          "carousel-dot" + (i === 0 ? " active" : "");
        dot.setAttribute("role", "button");
        dot.setAttribute(
          "aria-label",
          "Aller au resultat " + (i + 1) +
            " de " + realCount
        );
        dot.setAttribute(
          "aria-pressed", i === 0 ? "true" : "false"
        );
        dot.dataset.index = i + 1;
        dotsContainer.appendChild(dot);
        dots.push(dot);
      }

      function announceSlide(realIndex) {
        if (!liveRegion) return;
        liveRegion.textContent =
          "Resultat " + (realIndex + 1) +
            " de " + realCount;
      }

      function updateNavigation() {
        var snap = embla.selectedScrollSnap();
        if (snap < 1 || snap > realCount) return;
        var realIndex = snap - 1;
        prevButton.setAttribute(
          "aria-disabled",
          snap <= 1 ? "true" : "false"
        );
        nextButton.setAttribute(
          "aria-disabled",
          snap >= realCount ? "true" : "false"
        );
        dots.forEach(function (dot, idx) {
          dot.classList.toggle("active", idx === realIndex);
          dot.setAttribute(
            "aria-pressed",
            idx === realIndex ? "true" : "false"
          );
        });
        announceSlide(realIndex);
      }

      function clampToReal() {
        var snap = embla.selectedScrollSnap();
        if (snap < 1) {
          embla.scrollTo(1, true);
          return;
        }
        if (snap > realCount) {
          embla.scrollTo(realCount, true);
          return;
        }
        updateNavigation();
      }

      prevButton.addEventListener("click", function () {
        if (embla.selectedScrollSnap() > 1) {
          embla.scrollPrev();
        }
      });

      nextButton.addEventListener("click", function () {
        if (embla.selectedScrollSnap() < realCount) {
          embla.scrollNext();
        }
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
            if (embla.selectedScrollSnap() > 1) {
              embla.scrollPrev();
            }
          } else if (evt.key === "ArrowRight") {
            evt.preventDefault();
            if (embla.selectedScrollSnap() < realCount) {
              embla.scrollNext();
            }
          }
        });
      }

      embla.on("select", clampToReal);
      clampToReal();
    });
  }

  function initHistorySidebar(appState) {
    var toggle = document.querySelector(".sidebar-toggle");
    var sidebar = document.getElementById("history-sidebar");
    var backdrop = document.querySelector(".sidebar-backdrop");
    var openIcon = document.querySelector(".sidebar-toggle-open");
    var closeIcon =
      document.querySelector(".sidebar-toggle-close");
    if (!toggle || !sidebar) return;

    var focusableSelector =
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    var swipeStartX = null;
    var SWIPE_THRESHOLD = 60;

    function openSidebar() {
      document.body.classList.add("sidebar-open");
      toggle.setAttribute("aria-expanded", "true");
      toggle.setAttribute("aria-label", "Fermer l'historique");
      if (openIcon) openIcon.classList.add("hidden");
      if (closeIcon) closeIcon.classList.remove("hidden");
      if (backdrop && MOBILE_MQ.matches) {
        backdrop.classList.remove("hidden");
      }
      appState.sidebarOpen = true;

      if (MOBILE_MQ.matches) {
        var firstFocusable =
          sidebar.querySelector(focusableSelector);
        if (firstFocusable) firstFocusable.focus();
      }
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
      if (
        evt.key === "Escape" &&
        appState.sidebarOpen &&
        MOBILE_MQ.matches
      ) {
        closeSidebar();
      }

      if (
        evt.key === "Tab" &&
        appState.sidebarOpen &&
        MOBILE_MQ.matches
      ) {
        var focusable =
          sidebar.querySelectorAll(focusableSelector);
        if (focusable.length === 0) return;
        var first = focusable[0];
        var last = focusable[focusable.length - 1];

        if (evt.shiftKey) {
          if (
            document.activeElement === first ||
            document.activeElement === toggle
          ) {
            evt.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            evt.preventDefault();
            toggle.focus();
          }
        }
      }
    });

    sidebar.addEventListener("touchstart", function (evt) {
      if (!MOBILE_MQ.matches || !appState.sidebarOpen) return;
      swipeStartX = evt.touches[0].clientX;
    }, { passive: true });

    sidebar.addEventListener("touchmove", function (evt) {
      if (swipeStartX === null) return;
      var deltaX = evt.touches[0].clientX - swipeStartX;
      if (deltaX < -10) {
        sidebar.style.transform =
          "translateX(" + Math.max(deltaX, -280) + "px)";
      }
    }, { passive: true });

    sidebar.addEventListener("touchend", function (evt) {
      if (swipeStartX === null) return;
      var endX = evt.changedTouches[0].clientX;
      var deltaX = endX - swipeStartX;
      swipeStartX = null;
      sidebar.style.transform = "";

      if (deltaX < -SWIPE_THRESHOLD) {
        closeSidebar();
      }
    }, { passive: true });

    var STORAGE_KEY = "bible_search_history";
    var MAX_ENTRIES = 20;
    var historyList = sidebar.querySelector(".history-list");

    function loadHistory() {
      try {
        var raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
      } catch (e) {
        return [];
      }
    }

    function saveHistory(entries) {
      localStorage.setItem(
        STORAGE_KEY, JSON.stringify(entries)
      );
    }

    function addEntry(query) {
      var entries = loadHistory();
      var exists = entries.some(function (e) {
        return e.query === query;
      });
      if (exists) return;
      entries.unshift({
        id: Date.now().toString(36) +
          Math.random().toString(36).slice(2, 7),
        query: query,
        timestamp: Date.now()
      });
      if (entries.length > MAX_ENTRIES) {
        entries.length = MAX_ENTRIES;
      }
      saveHistory(entries);
      renderHistory();
    }

    function removeEntry(id) {
      var entries = loadHistory().filter(function (e) {
        return e.id !== id;
      });
      saveHistory(entries);
      renderHistory();
    }

    function renderHistory() {
      if (!historyList) return;
      historyList.innerHTML = "";
      var entries = loadHistory();
      entries.forEach(function (entry) {
        var div = document.createElement("div");
        div.className = "history-entry";

        var queryBtn = document.createElement("button");
        queryBtn.type = "button";
        queryBtn.className = "history-query";
        queryBtn.textContent = entry.query;
        queryBtn.title = entry.query;

        var deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "history-delete";
        deleteBtn.setAttribute(
          "aria-label", "Supprimer : " + entry.query
        );
        deleteBtn.textContent = "\u00d7";

        queryBtn.addEventListener("click", function () {
          if (appState.searchBar) {
            appState.searchBar.setValue(entry.query);
            htmx.trigger(
              document.getElementById("search-form"),
              "submit"
            );
          }
          if (MOBILE_MQ.matches) closeSidebar();
        });

        deleteBtn.addEventListener("click", function () {
          removeEntry(entry.id);
        });

        div.appendChild(queryBtn);
        div.appendChild(deleteBtn);
        historyList.appendChild(div);
      });
    }

    document.body.addEventListener(
      "htmx:afterSwap", function (evt) {
        if (evt.detail.target.id !== "results-container") return;
        var resultsContainer =
          document.getElementById("results-container");
        if (
          resultsContainer &&
          resultsContainer.querySelector(".carousel-viewport")
        ) {
          var query = appState.searchBar
            ? appState.searchBar.getValue()
            : "";
          if (query) addEntry(query);
        }
      }
    );

    renderHistory();
    appState.sidebar = { open: openSidebar, close: closeSidebar };
  }

  function initOfflineDetection() {
    var banner = document.querySelector(".offline-banner");
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
  initLoadingStates();
  initStatusMessages(window.appState);
  initCarousel(window.appState);
  initCarouselNavigation(window.appState);
  initHistorySidebar(window.appState);
  initOfflineDetection();

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/service-worker.js");
  }
});
