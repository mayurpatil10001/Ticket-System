/* Toast notification system */
(function () {
  function createContainer() {
    let el = document.getElementById('toast-container');
    if (!el) {
      el = document.createElement('div');
      el.id = 'toast-container';
      el.setAttribute('role', 'status');
      el.setAttribute('aria-live', 'polite');
      document.body.appendChild(el);
    }
    return el;
  }

  window.showToast = function (message, type) {
    const container = createContainer();
    const toast = document.createElement('div');
    toast.className = 'toast' + (type === 'error' ? ' error' : '');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity .3s';
      setTimeout(function () { toast.remove(); }, 350);
    }, 4000);
  };

  // Auto-show toasts from data attribute
  document.addEventListener('DOMContentLoaded', function () {
    const el = document.getElementById('auto-toast');
    if (el) {
      showToast(el.dataset.message, el.dataset.type || 'info');
    }
  });
})();
