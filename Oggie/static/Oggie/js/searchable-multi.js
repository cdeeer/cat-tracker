/**
 * Turn any <select multiple class="searchable-multi"> into a filterable
 * checkbox list. Preserves keyboard accessibility and vanilla form submission.
 */
(function () {
  function enhance(select) {
    if (select.dataset.enhanced === '1') return;
    select.dataset.enhanced = '1';

    const wrapper = document.createElement('div');
    wrapper.className = 'searchable-multi-wrapper';

    const search = document.createElement('input');
    search.type = 'search';
    search.placeholder = 'Type to filter…';
    search.className = 'searchable-multi-search';
    search.setAttribute('aria-label', 'Filter options');

    const list = document.createElement('div');
    list.className = 'searchable-multi-list';
    list.setAttribute('role', 'listbox');

    const summary = document.createElement('div');
    summary.className = 'searchable-multi-summary';

    const rows = [];
    Array.from(select.options).forEach(function (opt) {
      const label = document.createElement('label');
      label.className = 'searchable-multi-row';
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.value = opt.value;
      cb.checked = opt.selected;
      cb.addEventListener('change', function () {
        opt.selected = cb.checked;
        updateSummary();
      });
      label.appendChild(cb);
      const span = document.createElement('span');
      span.textContent = opt.textContent;
      label.appendChild(span);
      list.appendChild(label);
      rows.push({ row: label, text: opt.textContent.toLowerCase() });
    });

    search.addEventListener('input', function () {
      const q = search.value.trim().toLowerCase();
      rows.forEach(function (r) {
        r.row.style.display = q && r.text.indexOf(q) === -1 ? 'none' : '';
      });
    });

    function updateSummary() {
      const n = Array.from(select.options).filter(o => o.selected).length;
      summary.textContent = n === 0
        ? 'None selected'
        : n + ' selected';
    }
    updateSummary();

    wrapper.appendChild(search);
    wrapper.appendChild(list);
    wrapper.appendChild(summary);
    select.style.display = 'none';
    select.parentNode.insertBefore(wrapper, select.nextSibling);
  }

  function init() {
    document.querySelectorAll('select.searchable-multi').forEach(enhance);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
