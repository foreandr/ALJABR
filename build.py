import json,pathlib
P=pathlib.Path(__file__).resolve().parent
f=P/'data'/'lean_import.json'
lean=json.loads(f.read_text(encoding='utf8')) if f.exists() else {'schema':'aljabr.lean.v1','metadata':{'declarations':0,'dependencies':0,'not_imported':True},'nodes':[],'edges':[]}
assert lean.get('schema')=='aljabr.lean.v1'
(P/'aljabr-data.js').write_text('window.ALJABR_DATA='+json.dumps(lean,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n',encoding='utf8')
print(f"Built Lean-only ALJABR: {len(lean['nodes']):,} declarations, {len(lean['edges']):,} dependencies")
