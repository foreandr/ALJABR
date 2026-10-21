"""Disk-backed browser index for complete Lean Graph exports."""
import json
import os
from pathlib import Path
import sqlite3


def build_index(source, destination, metadata):
    temporary = destination.with_suffix('.sqlite.building')
    connection = sqlite3.connect(temporary)
    try:
        connection.executescript('''
            PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
            PRAGMA cache_size=-65536; PRAGMA temp_store=FILE;
            DROP TABLE IF EXISTS nodes; DROP TABLE IF EXISTS edges; DROP TABLE IF EXISTS metadata;
            CREATE TABLE nodes(id TEXT PRIMARY KEY, name TEXT, decl_type TEXT, payload TEXT);
            CREATE TABLE edges(source TEXT, target TEXT, kind TEXT, extras TEXT);
            CREATE TABLE metadata(payload TEXT);
        ''')
        count = edge_count = 0
        kinds = {'extends', 'field', 'sig', 'proof', 'def', 'docref'}
        with source.open(encoding='utf8') as stream:
            for line in stream:
                if not line.strip():
                    continue
                item = json.loads(line)
                name = item['name']
                ident = 'lean:' + name
                node = {'id': ident, 'name': name, 'kind': 'lean_declaration',
                        'decl_type': item.get('decl_type', 'unknown'), 'module': item.get('module', ''),
                        'docstring': item.get('docstring', ''), 'in_degree': item.get('in_degree', 0),
                        'is_instance': bool(item.get('is_instance', False)), 'source': 'lean-graph'}
                connection.execute('INSERT INTO nodes VALUES(?,?,?,?)',
                                   (ident, name, node['decl_type'], json.dumps(node, ensure_ascii=False)))
                batch = []
                for edge in item.get('edges', []):
                    if not isinstance(edge, dict) or not isinstance(edge.get('target'), str) or edge.get('kind') not in kinds:
                        continue
                    extras = {key: edge[key] for key in ('position', 'binder', 'role', 'via_proj') if key in edge}
                    batch.append((ident, 'lean:' + edge['target'], edge['kind'], json.dumps(extras, separators=(',', ':'))))
                connection.executemany('INSERT INTO edges VALUES(?,?,?,?)', batch)
                edge_count += len(batch)
                count += 1
                if count % 20000 == 0:
                    connection.commit()
                    print(f'Indexed {count:,} declarations / {edge_count:,} dependencies...', flush=True)
        if count != metadata['declarations'] or edge_count != metadata['dependencies']:
            raise ValueError('Browser index counts do not match the imported mathematics')
        print('Creating dependency lookup indexes (all mathematics retained)...', flush=True)
        connection.executescript('CREATE INDEX edges_source ON edges(source); CREATE INDEX edges_target ON edges(target);')
        connection.execute('INSERT INTO metadata VALUES(?)', (json.dumps(metadata),))
        connection.commit()
    finally:
        connection.close()
    os.replace(temporary, destination)


def search(connection, query='', kind=''):
    conditions, args = [], []
    if query:
        conditions.append('instr(lower(name), lower(?)) > 0')
        args.append(query)
    if kind:
        conditions.append('decl_type=?')
        args.append(kind)
    where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
    return [json.loads(row[0]) for row in connection.execute('SELECT payload FROM nodes' + where + ' LIMIT 180', args)]


def neighborhood(connection, ident):
    row = connection.execute('SELECT payload FROM nodes WHERE id=?', (ident,)).fetchone()
    if row is None:
        return None
    outgoing = connection.execute('SELECT source,target,kind,extras FROM edges WHERE source=? LIMIT 100', (ident,)).fetchall()
    incoming = connection.execute('SELECT source,target,kind,extras FROM edges WHERE target=? LIMIT 100', (ident,)).fetchall()
    edges = [dict(source=s, target=t, kind=k, **json.loads(extra)) for s, t, k, extra in outgoing + incoming]
    ids = {ident} | {edge['source'] for edge in edges} | {edge['target'] for edge in edges}
    nodes = []
    for key in ids:
        found = connection.execute('SELECT payload FROM nodes WHERE id=?', (key,)).fetchone()
        if found:
            nodes.append(json.loads(found[0]))
    return {'node': json.loads(row[0]), 'nodes': nodes, 'edges': edges,
            'out_count': connection.execute('SELECT count(*) FROM edges WHERE source=?', (ident,)).fetchone()[0],
            'in_count': connection.execute('SELECT count(*) FROM edges WHERE target=?', (ident,)).fetchone()[0]}
