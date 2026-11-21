/* TAT live-update module — re-renders every 30 seconds */
(function () {
  function formatDuration(secs) {
    if (secs <= 0) return 'OVERDUE';
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    if (secs < 1800) return '< 30m left';
    if (h > 0) return h + 'h ' + String(m).padStart(2, '0') + 'm left';
    return m + 'm left';
  }

  function updateMeters() {
    document.querySelectorAll('[data-due-at]').forEach(function (el) {
      const dueAt = new Date(el.dataset.dueAt);
      const paused = el.dataset.paused === 'true';
      const label = el.querySelector('.tat-label');
      const fill = el.querySelector('.tat-fill');

      if (paused) {
        if (label) { label.textContent = 'CLOCK PAUSED / waiting for member'; label.className = 'tat-label'; }
        return;
      }

      const now = new Date();
      const remaining = Math.floor((dueAt - now) / 1000);

      if (label) {
        if (remaining <= 0) {
          const over = Math.abs(remaining);
          const h = Math.floor(over / 3600);
          const m = Math.floor((over % 3600) / 60);
          label.textContent = 'OVERDUE ' + (h ? h + 'h ' : '') + String(m).padStart(2, '0') + 'm';
          label.className = 'tat-label overdue';
        } else {
          label.textContent = formatDuration(remaining);
          label.className = 'tat-label' + (remaining < 1800 ? ' warning' : '');
        }
      }

      if (fill) {
        const total = parseInt(el.dataset.tatMinutes || '240') * 60;
        const elapsed = total - remaining;
        const pct = Math.min(100, Math.max(0, (elapsed / total) * 100));
        fill.style.width = pct + '%';
        fill.className = 'tat-fill' + (remaining <= 0 ? ' overdue' : remaining < 1800 ? ' warning' : '');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    updateMeters();
    setInterval(updateMeters, 30000);
  });
})();
