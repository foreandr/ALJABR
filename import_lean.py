#!/usr/bin/env python3
"""Import Lean Graph NDJSON without holding millions of dependency edges in RAM."""
import argparse
import collections
import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent
KINDS = {'extends', 'field', 'sig', 'proof', 'def', 'docref'}


def read_ndjson(path, limit=None):
    with path.open(encoding='utf-8') as stream:
        count = 0
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            if limit is not None and count >= limit:
                break
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f'{path}:{number}: {error}') from error
            if not isinstance(item, dict) or not isinstance(item.get('name'), str):
                raise ValueError(f'{path}:{number}: expected declaration with name')
            count += 1
            yield item


def import_graph(source, output, limit=None):
    # Keep only declaration names in memory; spool nodes/edges to disk.
    ids = {'lean:' + item['name'] for item in read_ndjson(source, limit)}
    if not ids:
        raise ValueError('Export contains no declarations; previous mathematics preserved')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.import-', dir=output.parent) as temporary:
        stage = Path(temporary)
        counts = collections.Counter()
        decl = collections.Counter()
        dropped = unresolved = node_count = edge_count = 0
        with (stage/'nodes').open('w', encoding='utf-8') as nodes, (stage/'edges').open('w', encoding='utf-8') as edges:
            for item in read_ndjson(source, limit):
                name = item['name']
                dtype = str(item.get('decl_type', 'unknown'))
                decl[dtype] += 1
                node = {'id': 'lean:' + name, 'name': name, 'kind': 'lean_declaration',
                        'decl_type': dtype, 'module': item.get('module', ''),
                        'docstring': item.get('docstring', ''), 'in_degree': item.get('in_degree', 0),
                        'is_instance': bool(item.get('is_instance', False)), 'source': 'lean-graph'}
                if node_count:
                    nodes.write(',')
                nodes.write(json.dumps(node, ensure_ascii=False, separators=(',', ':')))
                node_count += 1
                for edge in item.get('edges', []):
                    if not isinstance(edge, dict) or not isinstance(edge.get('target'), str) or edge.get('kind') not in KINDS:
                        dropped += 1
                        continue
                    kind = edge['kind']
                    result = {'source': 'lean:' + name, 'target': 'lean:' + edge['target'], 'kind': kind}
                    for key in ('position', 'binder', 'role', 'via_proj'):
                        if key in edge:
                            result[key] = edge[key]
                    if edge_count:
                        edges.write(',')
                    edges.write(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
                    edge_count += 1
                    counts[kind] += 1
                    unresolved += result['target'] not in ids
                if node_count % 20000 == 0:
                    print(f'Imported {node_count:,} declarations / {edge_count:,} dependencies...', flush=True)
        metadata = {'imported_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'input_file': source.name, 'declarations': node_count, 'dependencies': edge_count,
                    'unresolved_targets': unresolved, 'rejected_edges': dropped,
                    'by_decl_type': dict(decl), 'by_edge_type': dict(counts)}
        destination = stage/'complete.json'
        with destination.open('w', encoding='utf-8') as target:
            target.write('{"schema":"aljabr.lean.v1","metadata":')
            json.dump(metadata, target, ensure_ascii=False, separators=(',', ':'))
            target.write(',"nodes":[')
            with (stage/'nodes').open(encoding='utf-8') as stream:
                shutil.copyfileobj(stream, target, 1024*1024)
            target.write('],"edges":[')
            with (stage/'edges').open(encoding='utf-8') as stream:
                shutil.copyfileobj(stream, target, 1024*1024)
            target.write(']}')
        os.replace(destination, output)
    print(f'Imported {node_count:,} declarations and {edge_count:,} edges. Unresolved targets: {unresolved:,}')
    print(f'JSON: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'data'/'lean_import.json')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    import_graph(args.source, args.output, args.limit)
