/* Imported Lean graph in the October 14 canvas and inspector. No synthetic routes. */
(async () => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = n => Number(n || 0).toLocaleString();
  const api = async path => { const r = await fetch('/api/' + path); if (!r.ok) throw Error(`Request failed (${r.status})`); return r.json(); };
  const colors = {class:'#6cb4ff',struct:'#6cb4ff',axiom:'#7be0b4',thm:'#7be0b4'};
  const color = n => colors[n.decl_type] || '#f0a15b';
  let current, nodes = new Map(), edges = [], positions = new Map(), selected, generation = 0;
  const relations = ['all','extends','field','sig','def','proof','docref'];
  const labels = {all:'All dependencies',extends:'Structure extension',field:'Structure field',sig:'Signature',def:'Definition',proof:'Proof',docref:'Documentation'};
  const isStructure = n => ['class','struct','structure'].includes(n.decl_type);
  let view = 'all', autoView = true;
  let relation = 0;
  const accepts = e => relation === 0 || e.kind === relations[relation];
  const locationId = () => { const raw = new URLSearchParams(location.search).get('lean') || decodeURIComponent(location.hash.slice(1)) || 'Module'; const aliases = {vspace:'Module',module:'Module',ring:'Ring',field:'Field'}; const name = aliases[raw] || raw; return name.startsWith('lean:') ? name : 'lean:' + name; };
  let depth = 1, focused = false, camera = {x:0,y:0,k:1}, drag, searchTimer, searchVersion = 0;
  const cache = new Map();
  const fetchNode = async (id, scope='all', kind='all') => {
    const key = JSON.stringify([id,scope,kind]);
    if (!cache.has(key)) {
      const result = await api('node?id=' + encodeURIComponent(id) + '&view=' + encodeURIComponent(scope) + '&relation=' + encodeURIComponent(kind));
      if (!result) throw Error('Declaration not found: ' + id);
      cache.set(key,result);
      if (cache.size > 150) cache.delete(cache.keys().next().value);
    }
    return cache.get(key);
  };
  const apply = () => $('wd').setAttribute('transform', `translate(${camera.x} ${camera.y}) scale(${camera.k})`);
  function fit() {
    const points = [...positions.values()]; if (!points.length) return;
    const minX = Math.min(...points.map(p=>p.x))-210, maxX = Math.max(...points.map(p=>p.x))+210;
    const minY = Math.min(...points.map(p=>p.y))-60, maxY = Math.max(...points.map(p=>p.y))+60;
    const w=$('cv').clientWidth, h=$('cv').clientHeight;
    camera.k=Math.min(1,(w-60)/(maxX-minX),(h-160)/(maxY-minY));
    camera.x=w/2-(minX+maxX)*camera.k/2; camera.y=90+(h-100)/2-(minY+maxY)*camera.k/2; apply();
  }
  const chip = n => `<button class="chip" data-id="${esc(n.id)}" style="--c:${color(n)}">${esc(n.name)}</button>`;
  function panel() {
    const n=current.node, lookup=new Map(current.nodes.map(n=>[n.id,n]));
    const dependencies=[...new Set(current.edges.filter(e=>e.source===selected).map(e=>e.target))];
    const dependents=[...new Set(current.edges.filter(e=>e.target===selected).map(e=>e.source))];
    const chips=ids=>ids.map(id=>lookup.has(id)?chip(lookup.get(id)):'').join('');
    const note=view==='structures'
      ? 'Only direct Lean references to CLASS and STRUCT declarations are shown. A dependency is not necessarily a mathematical construction.'
      : 'These are source-level Lean dependencies, not inferred construction routes.';
    $('ins').innerHTML=`<div class="k" style="color:${color(n)}">${esc(n.decl_type.toUpperCase())} · LEAN</div><h2>${esc(n.name)}</h2><p>${esc(n.docstring || n.module)}</p>
      <div class="sc">Left · Prerequisites · ${fmt(current.out_count)} total edges</div>
      ${chips(dependencies)}
      <div class="sc">Right · Used by · ${fmt(current.in_count)} total edges</div>
      ${chips(dependents)}
      <div class="l">${esc(note)} The graph is a sampled neighborhood (maximum 100 edges per side, 70 displayed declarations); totals include edges not on screen.</div>
      <div class="sc">Mathlib source</div><p>${esc(n.module)}</p>
      <div class="sc">Mathematical constructions</div><p>The original curated construction graph has distinct relationships for structures, maps, and axioms.</p>
      <a class="chip" href="constructions.html">Open construction atlas ↗</a>`;
  }
  function draw() {
    $('rg').innerHTML=''; $('sg').innerHTML='';
    $('ed').innerHTML=edges.filter(e=>positions.has(e.source)&&positions.has(e.target)).map(e=>{
      // Dependency points toward the declaration that requires it, as in the baseline.
      const a=positions.get(e.target),b=positions.get(e.source),dir=b.x>=a.x?1:-1;
      const ec=e.kind==='extends'?'#fbbf24':e.kind==='field'?'#22d3ee':'#8393b3';
      const ax=a.x+dir*180,bx=b.x-dir*180,m=(ax+bx)/2;
      return `<path d="M${ax},${a.y} C${m},${a.y} ${m},${b.y} ${bx},${b.y}" fill="none" stroke="${ec}" stroke-width="1.5" opacity=".65"><title>${esc(e.kind)}: ${esc(e.source)} depends on ${esc(e.target)}</title></path><polygon points="${bx},${b.y} ${bx-dir*8},${b.y-4} ${bx-dir*8},${b.y+4}" fill="${ec}"/>`;
    }).join('');
    $('nd').innerHTML=[...nodes.values()].map(n=>{
      const p=positions.get(n.id),c=n.id===selected?'#fbbf24':color(n);
      const name=n.name.length>40?n.name.slice(0,37)+'…':n.name;
      const shape=['class','struct'].includes(n.decl_type)?'<rect class="sh" x="-180" y="-30" width="360" height="60" rx="10"':n.decl_type==='axiom'||n.decl_type==='thm'?'<path class="sh" d="M-168 -30H168L180 -18V18L168 30H-168L-180 18V-18Z"':'<rect class="sh" x="-180" y="-30" width="360" height="60" rx="25"';
      return `<g class="n" tabindex="0" role="button" aria-label="${esc(n.name)}" data-id="${esc(n.id)}" transform="translate(${p.x} ${p.y})"><title>${esc(n.name)}</title>${shape} fill="#101d35" stroke="${c}" stroke-width="${n.id===selected?2.5:1.5}"/><text y="-5" text-anchor="middle" fill="#e6ecf8" font-size="14" font-weight="600">${esc(name)}</text><text y="15" text-anchor="middle" fill="${c}" font-size="9" letter-spacing=".8">${esc(n.decl_type.toUpperCase())}</text></g>`;
    }).join('');
  }
  async function select(id,push=true) {
    const token=++generation;
    $('mt').textContent='Loading dependencies…';
    try {
      // The default for mathematical classes/structures is to prioritize
      // other class/structure declarations, not arbitrary generated instances.
      const metadata=await fetchNode(id);
      if(token!==generation)return;
      if(autoView)view=isStructure(metadata.node)?'structures':'all';
      const kind=relations[relation], scope=view;
      const root=await fetchNode(id,scope,kind);
      if(token!==generation)return;
      const nextNodes=new Map([[id,root.node]]), nextEdges=new Map(), cols=new Map([[id,0]]);
      const queue=[{id,level:0}], seen=new Set();
      let calls=0;
      while(queue.length && calls<20 && nextNodes.size<70) {
        const q=queue.shift();
        if(seen.has(q.id)||q.level>=depth)continue;
        seen.add(q.id);
        const data=await fetchNode(q.id,scope,kind);
        calls++;
        if(token!==generation)return;
        const lookup=new Map(data.nodes.map(n=>[n.id,n]));
        const outgoing=data.edges.filter(e=>e.source===q.id && accepts(e));
        const incoming=focused?[]:data.edges.filter(e=>e.target===q.id && accepts(e));
        for(const [list,direction] of [[outgoing,-1],[incoming,1]]) {
          const neighbors=new Set();
          for(const edge of list) {
            const other=direction<0?edge.target:edge.source;
            if(!lookup.has(other))continue;
            if(!neighbors.has(other)&&neighbors.size>=12)continue;
            neighbors.add(other);
            if(!nextNodes.has(other)) {
              if(nextNodes.size>=70)continue;
              nextNodes.set(other,lookup.get(other));
              cols.set(other,cols.get(q.id)+direction);
              queue.push({id:other,level:q.level+1});
            }
            nextEdges.set(JSON.stringify([edge.source,edge.target,edge.kind]),edge);
          }
        }
      }
      if(token!==generation)return;
      selected=id;current=root;nodes=nextNodes;edges=[...nextEdges.values()];positions=new Map();
      const groups=new Map();
      for(const [key,col] of cols){if(!groups.has(col))groups.set(col,[]);groups.get(col).push(key);}
      for(const [col,ids] of groups)ids.forEach((key,i)=>positions.set(key,{x:col*490,y:(i-(ids.length-1)/2)*100}));
      if(push)history.pushState({lean:id},'', '/aljabr.html#'+encodeURIComponent(id));
      $('viewmode').textContent=view==='structures'?'Structures ✓':'All declarations';
      $('viewmode').setAttribute('aria-pressed',String(view==='structures'));
      $('methodCount').textContent=fmt(nodes.size)+' nodes';
      $('mt').textContent=labels[kind]+(view==='structures'?' · structures':'');
      draw();panel();fit();
      if(view==='structures'&&nodes.size===1)
        $('ins').insertAdjacentHTML('beforeend','<p class="l">No direct structure declarations found for these filters. Try All declarations or another dependency relation.</p>');
    }catch(error){
      if(token!==generation)return;
      console.error('ALJABR graph load',error);
      $('mt').textContent='Could not load graph';
      $('ins').innerHTML=`<h2>Unable to load</h2><p>${esc(error.message)}</p><a href="aljabr.html">Try again</a>`;
    }
  }
  $('dp').value=depth;$('dv').textContent=depth;$('dp').oninput=e=>{depth=+e.target.value;$('dv').textContent=depth;select(selected,false);};
  $('focus').textContent='All branches';$('focus').setAttribute('aria-pressed','false');$('focus').title='Toggle dependencies only';
  $('focus').onclick=()=>{focused=!focused;$('focus').textContent=focused?'Focused ✓':'All branches';$('focus').setAttribute('aria-pressed',String(focused));select(selected,false);};
  $('viewmode').onclick=()=>{autoView=false;view=view==='structures'?'all':'structures';select(selected,false);};
  const setRelation = index => { relation = (index + relations.length) % relations.length; $('methodMenu').classList.remove('open'); $('methodsList').setAttribute('aria-expanded','false'); select(selected,false); };
  $('mp').onclick=()=>setRelation(relation-1);$('mn').onclick=()=>setRelation(relation+1);
  $('methodsList').onclick=()=>{ const open=$('methodMenu').classList.toggle('open');$('methodsList').setAttribute('aria-expanded',String(open));$('methodMenu').innerHTML=relations.map((name,i)=>`<button class="method-option ${i===relation?'active':''}" data-relation="${i}">${labels[name]}</button>`).join(''); };
  $('methodMenu').onclick=e=>{const b=e.target.closest('[data-relation]');if(b)setRelation(+b.dataset.relation);};
  $('bk').onclick=()=>history.back();$('fw').onclick=()=>history.forward();
  addEventListener('popstate',()=>select(locationId(),false));
  $('rn').onclick=()=>{const choices=[...nodes.keys()].filter(id=>id!==selected);if(choices.length)select(choices[Math.floor(Math.random()*choices.length)]);};
  $('ins').onclick=e=>{const b=e.target.closest('[data-id]');if(b)select(b.dataset.id);};
  $('tg').onclick=()=>$('ins').classList.toggle('o');
  $('sv').onkeydown=e=>{const n=e.target.closest('[data-id]');if(n&&['Enter',' '].includes(e.key)){e.preventDefault();select(n.dataset.id);}};
  $('cv').onpointerdown=e=>{if(e.target.closest('#bar,#vp,#methodMenu'))return;const n=e.target.closest('[data-id]');drag={x:e.clientX,y:e.clientY,cx:camera.x,cy:camera.y,id:n?.dataset.id,moved:false};$('cv').setPointerCapture(e.pointerId);};
  $('cv').onpointermove=e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.hypot(dx,dy)>5)drag.moved=true;camera.x=drag.cx+dx;camera.y=drag.cy+dy;apply();};
  $('cv').onpointerup=()=>{if(drag?.id&&!drag.moved)select(drag.id);drag=null;};$('cv').onpointercancel=()=>drag=null;
  $('cv').addEventListener('wheel',e=>{if(e.target.closest('#bar,#vp,#methodMenu'))return;e.preventDefault();const r=$('cv').getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top,k=Math.min(3,Math.max(.03,camera.k*Math.exp(-e.deltaY*.0015)));camera.x=x-(x-camera.x)*k/camera.k;camera.y=y-(y-camera.y)*k/camera.k;camera.k=k;apply();},{passive:false});
  $('q').oninput=()=>{const token=++searchVersion;clearTimeout(searchTimer);searchTimer=setTimeout(async()=>{try{const rows=await api('search?q='+encodeURIComponent($('q').value));if(token===searchVersion)$('nl').innerHTML=rows.map(n=>`<option value="${esc(n.name)}">${esc(n.decl_type)}</option>`).join('');}catch(e){console.error('ALJABR search',e);}},220);};
  $('q').onchange=async()=>{try{const typed=$('q').value.trim(),value=/^vector[ -]?space$/i.test(typed)?'Module':typed,rows=await api('search?q='+encodeURIComponent(value)),n=rows.find(n=>n.name.toLowerCase()===value.toLowerCase())||rows[0];if(n){select(n.id);$('q').value='';}else{$('q').setCustomValidity('No matching declaration');$('q').reportValidity();}}catch(e){console.error(e);}};
  $('q').addEventListener('input',()=>$('q').setCustomValidity(''));
  $('vb').onclick=()=>$('vp').classList.toggle('o');
  addEventListener('resize',fit);addEventListener('keydown',e=>{if(e.key==='/'&&e.target.tagName!=='INPUT'){e.preventDefault();$('q').focus();}if(e.key==='Escape')$('vp').classList.remove('o');});
  try {const health=await api('health');$('vb').textContent='⊢ '+fmt(health.metadata.declarations);$('vp').textContent=fmt(health.metadata.declarations)+' declarations · '+fmt(health.metadata.dependencies)+' dependency edges. Complete data stored locally; canvas loads bounded neighborhoods.';}catch(e){console.error(e);}
  await select(locationId(),false);
})();
