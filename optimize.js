// optimize.js - 前端性能与加载稳定性一键优化脚本

(function () {
  // 1. 自动注册 Service Worker 离线缓存
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js')
        .then(reg => console.log('🚀 WorkBuddy 缓存加速引擎激活成功！'))
        .catch(err => console.error('❌ Cache 引擎注册失败:', err));
    });
  }

  // 2. 自动化原生图片懒加载 (Lazy Loading)
  // 在 DOM 准备好后，自动为没有设置 loading 的图片加上 lazy 属性，减轻服务器瞬间并发压力
  document.addEventListener('DOMContentLoaded', () => {
    const images = document.querySelectorAll('img');
    images.forEach(img => {
      if (!img.hasAttribute('loading')) {
        img.setAttribute('loading', 'lazy');
      }
    });
    console.log(`📦 已自动对全页 ${images.length} 张图片配置延迟加载策略。`);
  });

  // 3. 监控加载失败的第三方资源（如国外不稳定的 CDN 链接）进行容错提示
  window.addEventListener('error', function (e) {
    const target = e.target;
    if (target.tagName === 'LINK' || target.tagName === 'SCRIPT') {
      const url = target.src || target.href;
      console.warn(`⚠️ 检测到关键资源加载失败，正在尝试重新触发或记录: ${url}`);
      // 这里可以扩展针对特定 CDN 崩溃时的备用链接替换逻辑
    }
  }, true);

})();
