/* Complete atlas: load search results and one neighborhood at a time. */
(async () => {
  'use strict';
  const data = window.ALJABR_DATA;
  if (!data?.api) return;
  const $ = id => document.getElementById(id), fmt = n => Number(n || 0).toLocaleString();
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const meta = data.metadata;
  $('sn').textContent = fmt(meta.declarations);
  $('se').textContent = fmt(meta.dependencies);
  $('ss').textContent = fmt((meta.by_decl_type.structure || 0) + (meta.by_decl_type.struct || 0) + (meta.by_decl_type.class || 0));
  $('sourceStatus').textContent = 'Real Lean Graph import';
  if (location.protocol === 'file:') {
    $('message').textContent = 'Open 2_OPEN_ALJABR.bat to explore the full mathematics atlas.';
    return;
  }
  const request = async path => {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Atlas request failed: ${response.status}`);
    return response.json();
  };
  let selected = null, history = [], current = null, results = [], sequence = 0;
  const renderList = () => {
    $('count').textContent = `First ${results.length} matching declarations (max 180 shown)`;
    $('list').innerHTML = results.map(n => `<div class="item ${selected === n.id ? 'sel' : ''}" data-id="${esc(n.id)}">${esc(n.name)}<small>${esc(n.decl_type)} · ${esc(n.module)}</small></div>`).join('');
  };
  async function search() {
    const token = ++sequence;
    const found = await request('/api/search?' + new URLSearchParams({q: $('query').value.trim(), type: $('type').value}));
    if (token !== sequence) return;
    results = found;
    renderList();
  }
  async function show(id, save = true) {
    $('message').textContent = 'Loading declaration…';
    const result = await request('/api/node?' + new URLSearchParams({id}));
    if (!result) { $('message').textContent = 'Declaration not found in this export.'; return; }
    if (save && selected) history.push(selected);
    selected = id;
    current = result;
    renderList();
    const n = result.node;
    const outgoing = result.edges.filter(e => e.source === id).slice(0, 100);
    const incoming = result.edges.filter(e => e.target === id).slice(0, 100);
    const links = (edges, key) => edges.map(e => `<div class="dep" data-go="${esc(e[key])}">${esc(e[key].replace(/^lean:/, ''))} <span class="sub">${esc(e.kind)}</span></div>`).join('');
    $('details').innerHTML = `<strong>${esc(n.name)}</strong><p class="muted">${esc(n.docstring || 'No documentation provided by exporter.')}</p><div class="tag">${esc(n.decl_type)}</div><div class="tag">${esc(n.module)}</div><h3>Dependencies (${fmt(result.out_count)})</h3>${links(outgoing, 'target')}<h3>Used by (${fmt(result.in_count)})</h3>${links(incoming, 'source')}`;
    location.hash = encodeURIComponent(n.name);
    $('message').textContent = '';
    draw();
  }
  function draw() {
    const svg = $('graph'); svg.replaceChildren();
    if (!current) return;
    const lookup = new Map(current.nodes.map(n => [n.id, n]));
    const filter = $('edges').value;
    const available = current.edges.filter(e => !filter || e.kind === filter);
    const outgoing = available.filter(e => e.source === selected).slice(0, 22);
    const incoming = available.filter(e => e.target === selected).slice(0, 22);
    const edges = [...outgoing, ...incoming];
    const ids = [...new Set(edges.flatMap(e => [e.source, e.target]))].filter(id => id !== selected && lookup.has(id)).slice(0, 40);
    const points = new Map([[selected, [475, 300]]]);
    ids.forEach((id, i) => { const a = 2 * Math.PI * i / Math.max(ids.length, 1) - Math.PI / 2; points.set(id, [475 + Math.cos(a) * Math.min(325, Math.max(190, ids.length*8)), 300 + Math.sin(a) * Math.min(230, Math.max(150, ids.length*6))]); });
    function element(type, attrs, parent = svg) {
      const node = document.createElementNS('http://www.w3.org/2000/svg', type);
      for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
      parent.appendChild(node); return node;
    }
    for (const edge of edges) {
      if (!points.has(edge.source) || !points.has(edge.target)) continue;
      const a = points.get(edge.source), b = points.get(edge.target);
      element('line', {x1:a[0], y1:a[1], x2:b[0], y2:b[1], class:'edge ' + edge.kind});
    }
    for (const [id, [x, y]] of points) {
      const name = lookup.get(id).name;
      const group = element('g', {class:id === selected ? 'core' : '', 'data-id':id});
      element('rect', {x:x-94, y:y-20, width:188, height:40, rx:5}, group);
      element('text', {x, y:y+4, 'text-anchor':'middle'}, group).textContent = name.length > 27 ? name.slice(0,25) + '…' : name;
      group.addEventListener('click', () => show(id).catch(fail));
    }
  }
  function fail(error) { $('message').textContent = error.message + '. Reopen 2_OPEN_ALJABR.bat if needed.'; }
  let timer;
  $('query').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => search().catch(fail), 250); });
  $('type').addEventListener('change', () => search().catch(fail));
  $('edges').addEventListener('change', draw);
  $('reset').onclick = draw;
  $('back').onclick = () => { if (history.length) show(history.pop(), false).catch(fail); };
  $('list').onclick = e => { const item = e.target.closest('[data-id]'); if (item) show(item.dataset.id).catch(fail); };
  $('details').onclick = e => { const item = e.target.closest('[data-go]'); if (item) show(item.dataset.go).catch(fail); };
  try {
    await search();
    if (location.hash) await show('lean:' + decodeURIComponent(location.hash.slice(1)), false);
    else {
      const candidates = await request('/api/search?q=Module&type=class');
      const first = candidates.find(n => n.name === 'Module') || results[0];
      if (first) await show(first.id, false);
    }
  } catch (error) { fail(error); }
})();
