/* Preserve the baseline construction atlas; connect search and inspector to Lean. */
(() => {
  const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const mappings = {ring:'Ring',cring:'CommRing',field:'Field',module:'Module',vspace:'Module',group:'Group',monoid:'Monoid',semigroup:'Semigroup',set:'Set'};
  const originalPanel = panel;
  panel = function () {
    originalPanel();
    const name = mappings[sel] || N[sel].name.replaceAll(' ', '');
    const link = document.createElement('a');
    link.className = 'chip';
    link.textContent = 'Explore Lean dependencies ↗';
    link.href = '/aljabr.html?lean=' + encodeURIComponent('lean:' + name);
    ins.insertAdjacentHTML('beforeend', '<div class="sc">Imported mathematics</div><div class="l">This view shows the original curated construction routes.</div>');
    ins.append(link);
  };
  panel();
  let timer, version = 0, matches = [];
  const curatedOptions = $('nl').innerHTML;
  $('q').oninput = () => {
    const request = ++version, value = $('q').value.trim();
    clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        const response = await fetch('/api/search?q=' + encodeURIComponent(value));
        if (!response.ok) throw Error('Search failed');
        const rows = await response.json();
        if (request !== version) return;
        matches = rows;
        $('nl').innerHTML = curatedOptions + rows.map(n => `<option value="${escape(n.name)}">Lean · ${escape(n.decl_type)}</option>`).join('');
      } catch (error) { console.error('ALJABR search', error); }
    }, 220);
  };
  const originalSearch = $('q').onchange;
  $('q').onchange = async e => {
    const value = e.target.value.trim();
    if (L.some(n => n.name.toLowerCase() === value.toLowerCase())) return originalSearch(e);
    try {
      const response = await fetch('/api/search?q=' + encodeURIComponent(value));
      if (!response.ok) throw Error('Search failed');
      matches = await response.json();
      const match = matches.find(n => n.name.toLowerCase() === value.toLowerCase()) || matches[0];
      if (match) location.href = '/aljabr.html?lean=' + encodeURIComponent(match.id);
      else { e.target.setCustomValidity('No matching declaration'); e.target.reportValidity(); }
    } catch (error) { console.error(error); e.target.setCustomValidity(error.message); e.target.reportValidity(); }
  };
  $('q').addEventListener('input', e => e.target.setCustomValidity(''));
})();
