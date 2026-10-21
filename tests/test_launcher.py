"""Exercise updates against disposable files and real local Git repositories."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runner', PROJECT/'scripts'/'run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aljabr-test-')
        self.root = Path(self.temp.name)/'project with spaces'
        self.root.mkdir()
        for name in ('import_lean.py', 'build.py'):
            shutil.copy2(PROJECT/name, self.root/name)

    def tearDown(self):
        for logger in list(runner.logging.Logger.manager.loggerDict.values()):
            if isinstance(logger, runner.logging.Logger):
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)
        self.temp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.check_output(['git', *args], cwd=cwd or self.root,
                                       stderr=subprocess.STDOUT, text=True).strip()

    def seed(self):
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Launcher tests')
        self.git('config', 'user.email', 'tests@example.invalid')
        (self.root/'aljabr-data.js').write_text('original placeholder')
        (self.root/'code.txt').write_text('original source')
        (self.root/'.gitignore').write_text('logs/\n')
        self.git('add', '.')
        self.git('commit', '-m', 'seed')
        remote = Path(self.temp.name)/'remote.git'
        self.git('clone', '--bare', str(self.root), str(remote))
        self.git('remote', 'add', 'origin', str(remote))
        return str(remote)

    def fixture(self, content):
        source = Path(self.temp.name)/'input.ndjson'
        source.write_text(content, encoding='utf-8')
        return source

    def test_real_import_publishes_all_outputs(self):
        source = self.fixture(json.dumps({'name': 'Test.declaration', 'edges': []}))
        runner.update_math(runner.Run(self.root), source)
        payload = json.loads((self.root/'data'/'lean_import.json').read_text())
        self.assertEqual(payload['metadata']['declarations'], 1)
        self.assertIn('Test.declaration', (self.root/'aljabr-data.js').read_text())

    def test_bad_and_empty_import_preserve_last_good_files(self):
        (self.root/'data').mkdir()
        for name in ('lean_import.json', 'mathlib_unified.ndjson'):
            (self.root/'data'/name).write_text('last good data')
        (self.root/'aljabr-data.js').write_text('last good browser')
        for content in ('bad json', '\n'):
            with self.assertRaises(RuntimeError):
                runner.update_math(runner.Run(self.root), self.fixture(content))
            self.assertEqual((self.root/'data'/'lean_import.json').read_text(), 'last good data')
            self.assertEqual((self.root/'data'/'mathlib_unified.ndjson').read_text(), 'last good data')
            self.assertEqual((self.root/'aljabr-data.js').read_text(), 'last good browser')

    def test_partial_publication_rolls_back(self):
        (self.root/'data').mkdir()
        (self.root/'data'/'mathlib_unified.ndjson').write_text('previous export')
        (self.root/'aljabr-data.js').write_text('previous browser')
        replace = os.replace
        def fail_browser(source, destination):
            if Path(destination) == self.root/'aljabr-data.js':
                raise PermissionError('browser file locked')
            return replace(source, destination)
        with patch.object(runner.os, 'replace', side_effect=fail_browser):
            with self.assertRaises(PermissionError):
                runner.update_math(runner.Run(self.root), self.fixture('{"name":"Test.declaration"}'))
        self.assertEqual((self.root/'data'/'mathlib_unified.ndjson').read_text(), 'previous export')
        self.assertFalse((self.root/'data'/'lean_import.json').exists())
        self.assertEqual((self.root/'aljabr-data.js').read_text(), 'previous browser')

    def test_pull_new_code_preserves_generated_browser_data(self):
        remote = self.seed()
        other = Path(self.temp.name)/'other'
        self.git('clone', remote, str(other))
        (other/'code.txt').write_text('new upstream code')
        self.git('add', '.', cwd=other)
        self.git('-c', 'user.name=Tests', '-c', 'user.email=tests@example.invalid', 'commit', '-m', 'new', cwd=other)
        self.git('push', cwd=other)
        (self.root/'aljabr-data.js').write_text('local real mathematics')
        with patch.object(runner, 'REPO', remote):
            runner.sync(runner.Run(self.root))
        self.assertEqual((self.root/'code.txt').read_text(), 'new upstream code')
        self.assertEqual((self.root/'aljabr-data.js').read_text(), 'local real mathematics')

    def test_dirty_source_stops_without_discarding_edits(self):
        remote = self.seed()
        (self.root/'code.txt').write_text('my edits')
        with patch.object(runner, 'REPO', remote), self.assertRaisesRegex(RuntimeError, 'Local source edits'):
            runner.sync(runner.Run(self.root))
        self.assertEqual((self.root/'code.txt').read_text(), 'my edits')

    def test_second_updater_cannot_acquire_lock(self):
        with runner.exclusive(self.root):
            with self.assertRaisesRegex(RuntimeError, 'Another ALJABR'):
                with runner.exclusive(self.root):
                    self.fail('Second updater acquired the lock')

    def test_failed_command_records_exit_code(self):
        run = runner.Run(self.root)
        with self.assertRaises(RuntimeError):
            run.command([runner.sys.executable, '-c', 'raise SystemExit(7)'])
        self.assertEqual(run.report['commands'][-1]['exit_code'], 7)

    def graph_assets(self):
        self.seed()
        assets = self.root/'docs'/'data'
        assets.mkdir(parents=True)
        (self.root/'.gitattributes').write_text('docs/data/*.db filter=lfs diff=lfs merge=lfs -text\n')
        pointer = 'version https://git-lfs.github.com/spec/v1\noid sha256:' + 'a'*64 + '\nsize 987654321\n'
        database = assets/'type-deps.db'
        database.write_text(pointer)
        self.git('add', '.gitattributes', 'docs/data/type-deps.db')
        self.git('commit', '-m', 'optional LFS explorer data')
        return database, pointer

    def test_missing_optional_lfs_database_recovers_without_smudge(self):
        database, pointer = self.graph_assets()
        database.unlink()
        # Simulate a broken/unavailable LFS filter. Recovery must bypass it.
        self.git('config', 'filter.lfs.process', 'nonexistent-aljabr-lfs-command')
        self.git('config', 'filter.lfs.required', 'true')
        runner.repair_missing_graph_assets(runner.Run(self.root), self.root)
        self.assertEqual(database.read_text(), pointer)
        self.git('config', '--unset', 'filter.lfs.process')
        self.git('config', '--unset', 'filter.lfs.required')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_optional_asset_recovery_preserves_real_edits_and_source_deletions(self):
        database, pointer = self.graph_assets()
        database.write_text('my local database edits')
        (self.root/'code.txt').unlink()
        runner.repair_missing_graph_assets(runner.Run(self.root), self.root)
        self.assertEqual(database.read_text(), 'my local database edits')
        self.assertFalse((self.root/'code.txt').exists())

    def test_optional_asset_recovery_preserves_staged_deletion(self):
        database, pointer = self.graph_assets()
        self.git('rm', 'docs/data/type-deps.db')
        runner.repair_missing_graph_assets(runner.Run(self.root), self.root)
        self.assertFalse(database.exists())
        self.assertIn('D  docs/data/type-deps.db', self.git('status', '--porcelain'))

    def test_diagnostics_upload_creates_and_advances_separate_branch(self):
        remote = self.seed()
        (self.root/'diagnostics').mkdir()
        report = self.root/'diagnostics'/'latest.json'
        report.write_text('{"status":"test-one"}')
        (self.root/'diagnostics'/'latest.log').write_text('test console tail')
        with patch.object(runner, 'REPO', remote):
            runner.publish(runner.Run(self.root))
            report.write_text('{"status":"test-two"}')
            runner.publish(runner.Run(self.root))
        self.assertEqual(self.git('branch', '--show-current'), 'main')
        self.assertEqual(self.git('--git-dir', remote, 'show', 'diagnostics:latest.json'), '{"status":"test-two"}')


if __name__ == '__main__':
    unittest.main()
