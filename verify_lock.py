"""Ensure that adding Lean Graph didn't upgrade Mathlib's pinned dependencies."""
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parent / 'tools' / 'mathlib4'
lock = root / 'lake-manifest.json'
baseline = root / '.aljabr-baseline-lock.json'
if sys.argv[1:] == ['save']:
    current = json.loads(lock.read_text(encoding='utf-8'))
    baseline.write_text(json.dumps({p['name']: p.get('rev') for p in current.get('packages',[])}, indent=2), encoding='utf-8')
    print('Saved original Mathlib dependency lock.')
elif sys.argv[1:] == ['check']:
    current = json.loads(lock.read_text(encoding='utf-8'))
    original = json.loads(baseline.read_text(encoding='utf-8'))
    now = {p['name']: p.get('rev') for p in current.get('packages',[])}
    unexpected = {k: (v, now.get(k)) for k,v in original.items() if now.get(k) != v}
    if unexpected:
        print('ERROR: Mathlib dependencies unexpectedly changed:')
        for k,(old,new) in unexpected.items(): print(f'  {k}: {old} -> {new}')
        sys.exit(1)
    print(f'Mathlib lock preserved: {len(original)} original dependencies unchanged.')
else:
    raise SystemExit('Usage: verify_lock.py save|check')
