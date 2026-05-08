const CACHE_NAME = 'invest-pro-cache-v2';
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
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Use Network First for HTML pages so they are always up to date
  if (event.request.mode === 'navigate' || event.request.headers.get('accept').includes('text/html')) {
      event.respondWith(
          fetch(event.request).then(response => {
              return caches.open(CACHE_NAME).then(cache => {
                  cache.put(event.request, response.clone());
                  return response;
              });
          }).catch(() => {
              return caches.match(event.request);
          })
      );
      return;
  }

  // Use Cache First for static assets
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached response if found
        if (response) {
          return response;
        }
        // Else fetch from network
        return fetch(event.request);
      })
  );
});
