#!/usr/bin/env python3
"""Import Lean Graph unified NDJSON into ALJABR's versioned JSON dataset.
Standard library only. Usage: python import_lean.py path/to/output.ndjson
"""
import argparse, json, pathlib, datetime, collections, tempfile, os
ROOT = pathlib.Path(__file__).resolve().parent
KINDS = {'extends','field','sig','proof','def','docref'}
def read_ndjson(path):
    with path.open('r',encoding='utf8') as inp:
        for line_no,line in enumerate(inp,1):
            if not line.strip(): continue
            try: item=json.loads(line)
            except json.JSONDecodeError as e: raise ValueError(f'{path}:{line_no}: {e}') from e
            if not isinstance(item,dict) or not isinstance(item.get('name'),str):
                raise ValueError(f'{path}:{line_no}: expected declaration with name')
            yield item

def import_graph(source, output, limit=None):
    nodes=[]; edges=[]; counts=collections.Counter(); decl=collections.Counter(); dropped=0
    for i,item in enumerate(read_ndjson(source)):
        if limit is not None and i>=limit: break
        name=item['name']; dtype=str(item.get('decl_type','unknown')); decl[dtype]+=1
        nodes.append({'id':'lean:'+name,'name':name,'kind':'lean_declaration','decl_type':dtype,
                      'module':item.get('module',''),'docstring':item.get('docstring',''),
                      'in_degree':item.get('in_degree',0),'is_instance':bool(item.get('is_instance',False)),
                      'source':'lean-graph'})
        for e in item.get('edges',[]):
            if not isinstance(e,dict) or not isinstance(e.get('target'),str): dropped+=1; continue
            kind=e.get('kind','')
            if kind not in KINDS: dropped+=1; continue
            edge={'source':'lean:'+name,'target':'lean:'+e['target'],'kind':kind}
            for key in ('position','binder','role','via_proj'):
                if key in e: edge[key]=e[key]
            edges.append(edge);counts[kind]+=1
    ids={n['id'] for n in nodes}
    # Retain edges to external declaration references; consumers can identify unresolved endpoints.
    output.parent.mkdir(parents=True,exist_ok=True)
    payload={'schema':'aljabr.lean.v1','metadata':{'imported_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'input_file':source.name,'declarations':len(nodes),'dependencies':len(edges),
             'unresolved_targets':sum(e['target'] not in ids for e in edges),'rejected_edges':dropped,
             'by_decl_type':dict(decl),'by_edge_type':dict(counts)}, 'nodes':nodes,'edges':edges}
    fd,tmp=tempfile.mkstemp(dir=output.parent,prefix='.lean-',suffix='.json')
    try:
        with os.fdopen(fd,'w',encoding='utf8') as f: json.dump(payload,f,ensure_ascii=False,separators=(',',':'))
        os.replace(tmp,output)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    print(f"Imported {len(nodes):,} declarations and {len(edges):,} edges. Unresolved targets: {payload['metadata']['unresolved_targets']:,}")
    print(f'JSON: {output}')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=pathlib.Path,help='Lean Graph unified NDJSON export')
    p.add_argument('--output',type=pathlib.Path,default=ROOT/'data'/'lean_import.json')
    p.add_argument('--limit',type=int,help='Import first N declarations for testing')
    a=p.parse_args();import_graph(a.source,a.output,a.limit)
