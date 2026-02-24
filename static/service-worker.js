var CACHE_NAME = "rag-bible-v1";
var CACHE_FILES = [
  "/static/index.html",
  "/static/styles.css",
  "/static/app.js",
  "https://fonts.googleapis.com/css2?family=Crimson+Text:wght@400;600&display=swap",
  "https://unpkg.com/embla-carousel@8.0.0/embla-carousel.umd.js",
  "https://unpkg.com/htmx.org@2.0.4"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(CACHE_FILES);
    })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(
        names
          .filter(function (name) { return name !== CACHE_NAME; })
          .map(function (name) { return caches.delete(name); })
      );
    })
  );
});

self.addEventListener("fetch", function (event) {
  var url = new URL(event.request.url);

  if (event.request.method !== "GET" || url.pathname === "/search") {
    return;
  }

  event.respondWith(
    caches.match(event.request).then(function (cached) {
      return cached || fetch(event.request);
    })
  );
});
