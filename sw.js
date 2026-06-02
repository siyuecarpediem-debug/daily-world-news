// sw.js - 负责本地离线缓存
const CACHE_NAME = 'workbuddy-site-cache-v1';

// 你可以把网页中雷打不动、最核心的样式和图片写在这里
const urlsToCache = [
  '/',
  './index.html'
];

// 安装阶段：缓存核心资源
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('[Service Worker] 正在预缓存核心资源');
      return cache.addAll(urlsToCache);
    })
  );
});

// 激活阶段：清理旧缓存
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('[Service Worker] 清理过期缓存:', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// 拦截请求：网络优先，网络失败时降级到缓存，并自动对新资源进行动态缓存
self.addEventListener('fetch', event => {
  // 只拦截普通的 http/https 请求，忽略 chrome 扩展等
  if (!event.request.url.startsWith('http')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // 如果请求成功，复制一份扔进缓存，下次网络不好就靠它了
        if (response && response.status === 200 && response.type === 'basic') {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        // 当网络断开或超时崩溃时，从缓存中捞出资源救场
        console.log('[Service Worker] 网络请求失败，正在调取本地缓存:', event.request.url);
        return caches.match(event.request);
      })
  );
});
