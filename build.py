"""Build browser data atomically, optionally using staged input/output paths."""
import argparse
import json
import os
from pathlib import Path
import tempfile


def build(source, destination):
    if source.exists():
        with source.open(encoding='utf8') as stream:
            prefix = stream.read(65536)
        # Our importer emits metadata before the large arrays. Copy its already
        # validated JSON in chunks rather than loading a multi-GB graph in RAM.
        if prefix.startswith('{"schema":"aljabr.lean.v1","metadata":') and ',"nodes":[' in prefix:
            metadata = json.loads(prefix.split(',"nodes":[', 1)[0] + '}')['metadata']
            if source.stat().st_size > 128*1024*1024:
                from scripts.atlas_index import build_index
                raw = source.parent/'mathlib_unified.ndjson'
                if not raw.exists():
                    raise ValueError('The full NDJSON export is required to index this large dataset')
                build_index(raw, destination.with_suffix('.sqlite'), metadata)
                stub = {'schema': 'aljabr.lean.v1', 'api': True, 'metadata': metadata, 'nodes': [], 'edges': []}
                temporary = destination.with_suffix('.js.tmp')
                temporary.write_text('window.ALJABR_DATA=' + json.dumps(stub) + ';\n', encoding='utf8')
                os.replace(temporary, destination)
                print(f"Built indexed ALJABR: {metadata['declarations']:,} declarations, {metadata['dependencies']:,} dependencies")
                return
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(dir=destination.parent, suffix='.js')
            try:
                with os.fdopen(fd, 'w', encoding='utf8') as output, source.open(encoding='utf8') as stream:
                    output.write('window.ALJABR_DATA=')
                    carry = ''
                    while chunk := stream.read(1024*1024):
                        chunk = carry + chunk
                        carry = '<' if chunk.endswith('<') else ''
                        if carry:
                            chunk = chunk[:-1]
                        output.write(chunk.replace('</', '<\\/'))
                    output.write(carry + ';\n')
                os.replace(name, destination)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
            print(f"Built Lean-only ALJABR: {metadata['declarations']:,} declarations, {metadata['dependencies']:,} dependencies")
            return
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
