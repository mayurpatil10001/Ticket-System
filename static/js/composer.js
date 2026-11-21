/* Composer: char counter, saved-reply picker, internal note toggle */
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    // Character counter
    document.querySelectorAll('textarea[data-maxlength]').forEach(function (ta) {
      const max = parseInt(ta.dataset.maxlength);
      const counter = document.getElementById(ta.id + '-counter');
      if (!counter) return;

      function update() {
        const len = ta.value.length;
        counter.textContent = len + ' / ' + max;
        counter.className = 'char-counter' + (len >= max ? ' at-limit' : len >= max * 0.9 ? ' near-limit' : '');
      }
      ta.addEventListener('input', update);
      update();
    });

    // Saved reply picker (typing / in composer)
    const composerTA = document.getElementById('composer-body');
    const pickerEl = document.getElementById('saved-reply-picker');
    if (composerTA && pickerEl) {
      composerTA.addEventListener('input', function () {
        if (composerTA.value === '/') {
          pickerEl.style.display = 'block';
        } else {
          pickerEl.style.display = 'none';
        }
      });
      pickerEl.querySelectorAll('[data-reply-body]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          composerTA.value = btn.dataset.replyBody;
          pickerEl.style.display = 'none';
          composerTA.focus();
        });
      });
    }

    // Internal note toggle
    const noteToggle = document.getElementById('internal-note-toggle');
    const composer = document.getElementById('composer-form');
    if (noteToggle && composer) {
      noteToggle.addEventListener('change', function () {
        composer.classList.toggle('composer--internal', noteToggle.checked);
        const flag = document.getElementById('is-internal-note-flag');
        if (flag) flag.value = noteToggle.checked ? '1' : '0';
      });
    }
  });
})();
