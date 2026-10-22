"""Regression tests for structure-oriented Lean dependency exploration."""
import json
from pathlib import Path
import sqlite3
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atlas_index import neighborhood, search


class DependencyNeighborhoodTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.executescript('''
            CREATE TABLE nodes(id TEXT PRIMARY KEY, name TEXT, decl_type TEXT, payload TEXT);
            CREATE TABLE edges(source TEXT, target TEXT, kind TEXT, extras TEXT);
            CREATE INDEX edges_source ON edges(source);
            CREATE INDEX edges_target ON edges(target);
        ''')
        for index in range(160):
            self.node('ModuleGenerated' + str(index).zfill(3), 'inst')
            self.edge('ModuleGenerated' + str(index).zfill(3), 'Module', 'sig')
        self.node('Module', 'class')
        self.node('LieAlgebra', 'class')
        self.node('FiniteDimensional', 'struct')
        self.node('AxiomExample', 'thm')
        self.edge('LieAlgebra', 'Module', 'extends')
        self.edge('FiniteDimensional', 'Module', 'field')
        self.edge('AxiomExample', 'Module', 'proof')
        self.edge('Module', 'AddCommMonoid', 'extends')
        self.node('AddCommMonoid', 'class')

    def node(self, name, decl_type):
        value = {'id': 'lean:' + name, 'name': name, 'decl_type': decl_type}
        self.db.execute('INSERT INTO nodes VALUES (?,?,?,?)',
                        (value['id'], name, decl_type, json.dumps(value)))

    def edge(self, source, target, kind):
        self.db.execute('INSERT INTO edges VALUES (?,?,?,?)',
                        ('lean:' + source, 'lean:' + target, kind, '{}'))

    def test_old_unfiltered_limit_omits_the_useful_structures(self):
        result = neighborhood(self.db, 'lean:Module')
        self.assertEqual(result['in_sample'], 100)
        self.assertNotIn('lean:LieAlgebra', {e['source'] for e in result['edges']})

    def test_structure_view_finds_descendants_after_instance_noise(self):
        result = neighborhood(self.db, 'lean:Module', view='structures')
        names = {node['name'] for node in result['nodes']}
        self.assertTrue({'Module', 'AddCommMonoid', 'LieAlgebra',
                         'FiniteDimensional'} <= names)
        self.assertNotIn('AxiomExample', names)
        self.assertEqual(result['in_count'], 163)
        self.assertEqual(result['in_sample'], 2)

    def test_explicit_structure_extensions(self):
        result = neighborhood(self.db, 'lean:Module',
                              view='structures', relation='extends')
        endpoints = {(e['source'], e['target']) for e in result['edges']}
        self.assertEqual(endpoints, {('lean:LieAlgebra', 'lean:Module'),
                                     ('lean:Module', 'lean:AddCommMonoid')})

    def test_exact_match_precedes_fuzzy_results(self):
        results = search(self.db, 'Module')
        self.assertEqual(results[0]['id'], 'lean:Module')
        self.assertEqual(len(results), 180)

    def test_missing_node_returns_none(self):
        self.assertIsNone(neighborhood(self.db, 'lean:does-not-exist'))


if __name__ == '__main__':
    unittest.main()
