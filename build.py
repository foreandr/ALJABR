"""Build browser data atomically, optionally using staged input/output paths."""
import argparse
import json
import os
from pathlib import Path
import tempfile


def build(source, destination):
    lean = json.loads(source.read_text(encoding='utf8')) if source.exists() else {
        'schema': 'aljabr.lean.v1', 'metadata': {'declarations': 0, 'dependencies': 0,
        'not_imported': True}, 'nodes': [], 'edges': []}
    if lean.get('schema') != 'aljabr.lean.v1':
        raise ValueError('Unsupported ALJABR dataset schema')
    content = 'window.ALJABR_DATA=' + json.dumps(lean, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + ';\n'
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=destination.parent, suffix='.js')
    try:
        with os.fdopen(fd, 'w', encoding='utf8') as output:
            output.write(content)
        os.replace(name, destination)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print(f"Built Lean-only ALJABR: {len(lean['nodes']):,} declarations, {len(lean['edges']):,} dependencies")


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=root/'data'/'lean_import.json')
    parser.add_argument('--output', type=Path, default=root/'aljabr-data.js')
    args = parser.parse_args()
    build(args.input, args.output)
