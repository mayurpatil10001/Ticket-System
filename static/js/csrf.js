/* Inject CSRF token into all HTMX requests */
document.addEventListener('DOMContentLoaded', function () {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta && window.htmx) {
    htmx.config.defaultHeaders = htmx.config.defaultHeaders || {};
    htmx.config.defaultHeaders['X-CSRF-Token'] = meta.getAttribute('content');
  }
  // Also for HTMX config hook
  document.body.addEventListener('htmx:configRequest', function (e) {
    if (meta) {
      e.detail.headers['X-CSRF-Token'] = meta.getAttribute('content');
    }
  });
});
