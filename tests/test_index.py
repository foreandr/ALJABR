import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.atlas_index import build_index, neighborhood, search


class IndexTests(unittest.TestCase):
    def test_complete_graph_is_retained_and_neighborhoods_are_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = root/'graph.ndjson'
            items = [{'name': 'Module', 'decl_type': 'class', 'edges': [{'target': 'Group', 'kind': 'sig', 'binder': 'implicit'}]},
                     {'name': 'Group', 'decl_type': 'structure', 'edges': []}]
            items += [{'name': f'User{i}', 'decl_type': 'def', 'edges': [{'target': 'Module', 'kind': 'def'}]} for i in range(150)]
            raw.write_text('\n'.join(json.dumps(item) for item in items), encoding='utf8')
            database = root/'atlas.sqlite'
            build_index(raw, database, {'declarations': 152, 'dependencies': 151})
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(len(search(connection, 'module')), 1)
                self.assertEqual(search(connection, '', 'structure')[0]['name'], 'Group')
                result = neighborhood(connection, 'lean:Module')
                self.assertEqual(result['in_count'], 150)
                self.assertEqual(result['out_count'], 1)
                self.assertLessEqual(len(result['edges']), 200)
                self.assertEqual(result['edges'][0]['binder'], 'implicit')
                self.assertIsNone(neighborhood(connection, 'not present'))
                self.assertEqual(search(connection, "'; DROP TABLE nodes;--"), [])

    def test_wrong_counts_do_not_replace_previous_index(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = root/'graph.ndjson'
            raw.write_text('{"name":"Module","edges":[]}')
            database = root/'atlas.sqlite'
            database.write_bytes(b'previous working index')
            with self.assertRaises(ValueError):
                build_index(raw, database, {'declarations': 2, 'dependencies': 0})
            self.assertEqual(database.read_bytes(), b'previous working index')
