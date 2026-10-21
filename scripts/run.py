"""Standard-library-only ALJABR synchronization, mathematics update and diagnostics."""
import argparse
import collections
import contextlib
import datetime as dt
import json
import logging
import logging.handlers
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/foreandr/ALJABR.git'
MATHLIB_TAG = 'v4.29.0'


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


class Run:
    def __init__(self, root):
        self.root = Path(root)
        self.started = time.monotonic()
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.folder = self.root / 'logs' / (stamp + '-' + str(os.getpid()))
        self.folder.mkdir(parents=True)
        self.tail = collections.deque(maxlen=80)
        self.report = {'schema': 1, 'started_utc': stamp, 'status': 'running',
                       'python': sys.version, 'platform': sys.platform, 'commands': []}
        self.log = logging.getLogger(str(self.folder))
        self.log.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
            self.folder / 'run.log', maxBytes=4*1024*1024, backupCount=7, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        self.log.addHandler(handler)
        self.log.addHandler(logging.StreamHandler(sys.stdout))

    def say(self, text):
        self.log.info(text)
        self.tail.append(str(text)[-2000:])

    def command(self, args, cwd=None, retry=False, timeout=None):
        args = list(map(str, args))
        for attempt in range(1, (3 if retry else 1) + 1):
            self.say('COMMAND: ' + subprocess.list2cmdline(args))
            record = {'argv': args, 'cwd': os.path.relpath(cwd or self.root, self.root),
                      'attempt': attempt}
            self.report['commands'].append(record)
            start = time.monotonic()
            # Network commands use bounded retries/timeouts. Builds stream until completion.
            output = []
            env = dict(os.environ, GIT_TERMINAL_PROMPT='0', PYTHONUNBUFFERED='1',
                       GCM_INTERACTIVE='Never')
            with subprocess.Popen(args, cwd=cwd or self.root, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, encoding='utf-8',
                                  errors='replace', env=env) as process:
                import threading
                timed_out = []
                def expire():
                    timed_out.append(True)
                    process.kill()
                timer = threading.Timer(timeout, expire) if timeout else None
                if timer:
                    timer.start()
                try:
                    for line in process.stdout:
                        line = line.rstrip('\r\n')
                        self.say(line)
                        output.append(line)
                        if len(output) > 4000:
                            del output[:2000]
                    code = process.wait()
                finally:
                    if timer:
                        timer.cancel()
                record.update(exit_code=code, seconds=round(time.monotonic()-start, 2),
                              timed_out=bool(timed_out))
            if code == 0 and not timed_out:
                return '\n'.join(output)
            if not retry or attempt == 3:
                raise RuntimeError('Command failed (exit %s): %s' % (code, subprocess.list2cmdline(args)))
            self.say('Retrying network operation in %s seconds...' % (attempt*2))
            time.sleep(attempt*2)

    def git(self, *args, cwd=None, retry=False):
        return self.command(['git', *args], cwd=cwd, retry=retry, timeout=180 if retry else 60)


@contextlib.contextmanager
def exclusive(root):
    # OS lock releases even after a crash; a stale file never blocks the next run.
    path = Path(root) / '.aljabr-run.lock'
    with path.open('a+b') as handle:
        handle.seek(0)
        if path.stat().st_size == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError('Another ALJABR updater is running. Wait for it to finish.') from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def sync(run):
    if run.git('rev-parse', '--show-toplevel').replace('\\', '/').casefold() != run.root.as_posix().casefold():
        raise RuntimeError('Run this launcher inside the ALJABR Git checkout.')
    if run.git('branch', '--show-current') != 'main':
        raise RuntimeError('Switch to main before running the updater.')
    remote = run.git('remote', 'get-url', 'origin')
    if remote not in (REPO, REPO[:-4], 'git@github.com:foreandr/ALJABR.git'):
        raise RuntimeError('origin must point to foreandr/ALJABR; refusing to pull an unexpected repository.')
    run.git('diff', '--cached', '--quiet')
    changed = run.git('diff', '--name-only').splitlines()
    allowed = {'aljabr-data.js'}
    if set(changed) - allowed:
        raise RuntimeError('Local source edits found. Commit or stash them before retrying: ' + ', '.join(changed))
    run.git('fetch', 'origin', 'main', retry=True)
    ahead = run.git('rev-list', '--count', 'origin/main..HEAD')
    if ahead != '0':
        raise RuntimeError('Local commits have not been pushed. Push/reconcile them before retrying; no reset performed.')
    # Generated browser data is backed up before Git updates its tracked placeholder.
    data = run.root / 'aljabr-data.js'
    backup = run.folder / 'aljabr-data.previous.js'
    if changed:
        shutil.copy2(data, backup)
        run.git('restore', '--', 'aljabr-data.js')
    try:
        run.git('merge', '--ff-only', 'origin/main')
    finally:
        if backup.exists():
            shutil.copy2(backup, data)
    run.report['aljabr_commit'] = run.git('rev-parse', 'HEAD')


def update_math(run, source=None):
    root = run.root
    data = root / 'data'
    data.mkdir(exist_ok=True)
    if source is None:
        if not shutil.which('lake'):
            run.command(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                         '-File', root / 'install_lean.ps1'])
            os.environ['PATH'] = str(Path.home()/'.elan'/'bin') + os.pathsep + os.environ['PATH']
        math = root / 'tools' / 'mathlib4'
        graph = root / 'tools' / 'lean-graph'
        math.parent.mkdir(exist_ok=True)
        for target, url, branch in [(math, 'https://github.com/leanprover-community/mathlib4.git', MATHLIB_TAG),
                                    (graph, 'https://github.com/aurasoph/lean-graph.git', 'main')]:
            if not target.exists():
                run.git('clone', '--depth', '1', '--branch', branch, url, str(target), retry=True)
            else:
                if not (target / '.git').exists():
                    raise RuntimeError('Incomplete clone: rename %s and retry.' % target)
                if run.git('remote', 'get-url', 'origin', cwd=target) != url:
                    raise RuntimeError('Unexpected upstream remote: ' + str(target))
                if target == math:
                    # Only our generated Lake edits may be reset. Other edits are preserved.
                    changed = run.git('diff', '--name-only', cwd=target).splitlines()
                    if set(changed) - {'lakefile.lean', 'lakefile.toml', 'lake-manifest.json'}:
                        raise RuntimeError('Local Mathlib source edits found; preserve them before updating.')
                    run.git('diff', '--cached', '--quiet', cwd=target)
                    for name in changed:
                        shutil.copy2(target/name, run.folder/('mathlib-' + name))
                        run.git('restore', '--', name, cwd=target)
                    run.git('fetch', '--depth', '1', 'origin', 'tag', branch, cwd=target, retry=True)
                    run.git('checkout', '--detach', 'tags/' + branch, cwd=target)
                else:
                    if run.git('status', '--porcelain', cwd=target):
                        raise RuntimeError('Local Lean Graph edits found; commit or stash them before updating.')
                    run.git('pull', '--ff-only', cwd=target, retry=True)
        expected = 'leanprover/lean4:' + MATHLIB_TAG
        for target in (math, graph):
            toolchain = (target/'lean-toolchain').read_text().strip()
            if toolchain != expected:
                raise RuntimeError('Toolchain mismatch in %s: %s; expected %s. Update compatibility pin deliberately.' % (target.name, toolchain, expected))
            run.report[target.name + '_commit'] = run.git('rev-parse', 'HEAD', cwd=target)
        run.report['toolchain'] = expected
        run.command(['lake', '--version'], cwd=math)
        run.command([sys.executable, root/'verify_lock.py', 'save'])
        run.command(['lake', 'exe', 'cache', 'get'], cwd=math)
        run.command([sys.executable, root/'setup_lean.py'])
        run.command(['lake', 'update', 'leanGraph', '--keep-toolchain'], cwd=math)
        run.command([sys.executable, root/'verify_lock.py', 'check'])
        run.command(['lake', 'build', 'graph'], cwd=math)
    # Stage all outputs away from the last good dataset, including supplied imports.
    with tempfile.TemporaryDirectory(prefix='.aljabr-', dir=data) as temporary:
        stage = Path(temporary)
        export = stage/'mathlib_unified.ndjson'
        if source is None:
            run.command(['lake', 'exe', 'graph', '--mode', 'unified', '--to', 'Mathlib', export], cwd=math)
        else:
            shutil.copyfile(source, export)
        if not export.exists() or export.stat().st_size == 0:
            raise RuntimeError('Extractor produced no mathematics; previous dataset preserved.')
        run.command([sys.executable, root/'import_lean.py', export, '--output', stage/'lean_import.json'])
        run.command([sys.executable, root/'build.py', '--input', stage/'lean_import.json', '--output', stage/'aljabr-data.js'])
        # Publication rolls back every replaced file if any replacement fails.
        publications = [(export, data/export.name), (stage/'lean_import.json', data/'lean_import.json'),
                        (stage/'aljabr-data.js', root/'aljabr-data.js')]
        done = []
        try:
            for new, destination in publications:
                old = stage/(destination.name + '.previous')
                if destination.exists():
                    shutil.copy2(destination, old)
                os.replace(new, destination)
                done.append((destination, old))
        except BaseException:
            for destination, old in reversed(done):
                if old.exists():
                    os.replace(old, destination)
                else:
                    destination.unlink(missing_ok=True)
            raise
    run.say('SUCCESS: mathematics refreshed. Open 2_OPEN_ALJABR.bat when ready.')


def publish(run):
    # Separate branch keeps reports available to repo readers without dirtying main.
    with tempfile.TemporaryDirectory(prefix='aljabr-diagnostics-') as temporary:
        temp = Path(temporary)
        run.git('init', str(temp))
        run.git('remote', 'add', 'origin', REPO, cwd=temp)
        refs = run.git('ls-remote', '--heads', 'origin', 'diagnostics', cwd=temp, retry=True)
        if refs:
            run.git('fetch', '--depth', '1', 'origin', 'diagnostics', cwd=temp, retry=True)
            run.git('checkout', '-B', 'diagnostics', 'FETCH_HEAD', cwd=temp)
        else:
            run.git('checkout', '--orphan', 'diagnostics', cwd=temp)
        for name in ('latest.json', 'latest.log'):
            shutil.copy2(run.root/'diagnostics'/name, temp/name)
        run.git('add', '--', 'latest.json', 'latest.log', cwd=temp)
        run.git('-c', 'user.name=ALJABR diagnostics', '-c', 'user.email=aljabr-diagnostics@users.noreply.github.com',
                'commit', '-m', 'Latest ALJABR run diagnostics', cwd=temp)
        run.git('push', 'origin', 'HEAD:diagnostics', cwd=temp, retry=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update-only', action='store_true', help='Skip ALJABR pull; still update mathematics')
    parser.add_argument('--import-file', type=Path, help='Import a real existing NDJSON export instead of building Lean')
    parser.add_argument('--no-publish', action='store_true', help='Keep diagnostics local')
    parser.add_argument('--check', action='store_true', help='Check Git/Python only; no pull, mathematics or upload')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--worker-report', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        run = Run(ROOT)
        run.report['mode'] = 'check' if args.check else ('import' if args.import_file else 'mathematics')
        try:
            update_math(run, args.import_file)
            run.report['status'] = 'success'
        except BaseException as error:
            run.report.update(status='failed', error=str(error))
            raise
        finally:
            atomic_json(args.worker_report or run.folder/'summary.json', run.report)
        return 0
    with exclusive(ROOT):
        run = Run(ROOT)
        run.report['mode'] = 'check' if args.check else ('import' if args.import_file else 'mathematics')
        code = 1
        try:
            run.say('ALJABR update started. Full local logs: ' + str(run.folder))
            run.command(['git', '--version'])
            run.report['aljabr_commit'] = run.git('rev-parse', 'HEAD')
            if args.check:
                run.git('status', '--short')
            else:
                if not args.update_only:
                    sync(run)
                else:
                    run.report['aljabr_commit'] = run.git('rev-parse', 'HEAD')
                # Reload the updater after pull so this click uses newly downloaded code.
                worker_report = run.folder/'mathematics.json'
                command = [sys.executable, '-u', ROOT/'scripts'/'run.py', '--worker', '--worker-report', worker_report]
                if args.import_file:
                    command += ['--import-file', args.import_file.resolve()]
                try:
                    run.command(command)
                finally:
                    if worker_report.exists():
                        run.report['mathematics'] = json.loads(worker_report.read_text(encoding='utf-8'))
            run.report['status'] = 'success'
            code = 0
        except (Exception, KeyboardInterrupt) as error:
            run.report.update(status='failed', error=str(error))
            run.say(traceback.format_exc())
        finally:
            run.report['seconds'] = round(time.monotonic()-run.started, 2)
            atomic_json(run.folder/'summary.json', run.report)
            diag = ROOT/'diagnostics'
            atomic_json(diag/'latest.json', run.report)
            (diag/'latest.log').write_text('\n'.join(run.tail) + '\n', encoding='utf-8')
            if not args.no_publish and not args.check:
                try:
                    publish(run)
                except Exception as error:
                    run.say('Diagnostics upload failed; retained locally: ' + str(error))
            run.say('Finished with exit code %s. Latest report: diagnostics/latest.json' % code)
        return code


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    try:
        sys.exit(main())
    except Exception as error:
        print('ALJABR ERROR:', error, file=sys.stderr)
        sys.exit(1)
