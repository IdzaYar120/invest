const CACHE_NAME = 'invest-pro-cache-v1';
const urlsToCache = [
  '/',
  '/crypto/',
  '/static/analyzer/bootstrap.min.css',
  '/static/analyzer/bootstrap.bundle.min.js',
  '/static/analyzer/apexcharts.js',
  '/static/analyzer/style.css',
  '/static/analyzer/intro.min.js',
  '/static/analyzer/introjs.min.css',
  '/static/analyzer/icons/icon-192x192.png',
  '/static/analyzer/icons/icon-512x512.png',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached response if found
        if (response) {
          return response;
        }
        // Else fetch from network
        return fetch(event.request).catch(() => {
          // Fallback if offline
        });
      })
  );
});
