/* Agent queue keyboard shortcuts: j/k navigate, / focus search */
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    const rows = function () { return document.querySelectorAll('.ticket-row'); };
    let idx = -1;

    function selectRow(i) {
      const all = rows();
      if (!all.length) return;
      idx = Math.max(0, Math.min(all.length - 1, i));
      all[idx].click();
      all[idx].focus();
    }

    document.addEventListener('keydown', function (e) {
      // Skip if focus is on input/textarea
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
        if (e.key === 'Escape') document.activeElement.blur();
        return;
      }

      switch (e.key) {
        case 'j': selectRow(idx + 1); break;
        case 'k': selectRow(idx - 1); break;
        case '/':
          e.preventDefault();
          const search = document.getElementById('queue-search');
          if (search) search.focus();
          break;
      }
    });
  });
})();
