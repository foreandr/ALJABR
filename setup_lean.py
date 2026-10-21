"""Attach a local LeanGraph dependency to the freshly checked out Mathlib project.
Does not modify the upstream repository on disk beyond a local lakefile append.
"""
from pathlib import Path
root=Path(__file__).resolve().parent
math=root/'tools'/'mathlib4'
graph=root/'tools'/'lean-graph'
# The author's documented command uses a lakefile.lean, but newer Mathlib uses
# lakefile.toml. TOML supports local dependency requires in [[require]] tables.
toml=math/'lakefile.toml'
lean=math/'lakefile.lean'
if toml.exists():
    s=toml.read_text(encoding='utf8')
    # Correct Lake TOML syntax for local path dependencies.
    block='\n[[require]]\nname = "leanGraph"\npath = "../lean-graph"\n'
    if 'name = "leanGraph"' not in s:
        toml.write_text(s.rstrip()+'\n'+block,encoding='utf8')
elif lean.exists():
    s=lean.read_text(encoding='utf8')
    if 'require leanGraph from' not in s:
        lean.write_text(s.rstrip()+'\nrequire leanGraph from "../lean-graph"\n',encoding='utf8')
else:
    raise SystemExit('No Mathlib Lake configuration found')
print('Attached local lean-graph dependency.')
