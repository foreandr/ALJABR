# ALJABR

Mathlib mathematics imported from Lean Graph, with a searchable offline browser.
The bundled browser starts with zero declarations until a real import succeeds.

## Start here on Windows

Double-click **PULL_AND_RUN.bat** in this folder. It:

1. Fetches `foreandr/ALJABR` and fast-forwards `main` to the newest code.
2. Installs Lean through the official elan installer if Lake is missing.
3. Fetches compatible Mathlib and Lean Graph sources, obtains the Mathlib cache,
   checks the dependency lock, builds the extractor, and exports real mathematics.
4. Imports and builds the browser data in a staging directory before replacing
   the previous dataset. A failed import/build leaves previous good data intact.
5. Saves detailed local logs and uploads a compact report to the GitHub
   **diagnostics** branch, on success or failure.

Then double-click **2_OPEN_ALJABR.bat** to open the browser. Opening needs no
mathematics update and does not run the pull-and-build process.

Git and Python 3.9+ must be installed and on PATH. No Python packages or virtual
environment are needed. The initial Lean/Mathlib download and build can take a
long time and many gigabytes; subsequent runs reuse the local tools and cache.
The launcher waits for builds rather than declaring a slow build failed.

## What gets updated

ALJABR always fetches the newest `main` code. Lean Graph fetches its newest `main`
code. Mathlib stays on the compatible **v4.29.0** release, matching Lean Graph's
Lean toolchain. Each click re-extracts that mathematics; it does not claim to
follow Mathlib's incompatible latest development branch. A mismatched toolchain
or a changed dependency revision stops with an explicit error.

The upstream command is `lake exe graph --mode unified --to Mathlib output.ndjson`.
Sources: [Lean Graph](https://github.com/aurasoph/lean-graph) and
[Mathlib](https://github.com/leanprover-community/mathlib4), both Apache 2.0.

## Local work and recovery

The launcher uses a process lock to prevent two ALJABR updaters running together.
Git synchronization uses bounded network retries and fast-forward updates. It
never force-pulls, hard-resets, auto-stashes source edits, or force-pushes.
Commit/stash your source edits and push/reconcile local commits before running.
Untracked files are retained; Git stops if they would be overwritten by a pull.

The generated `aljabr-data.js` is backed up under the current `logs/` run before
pulling, then restored so a code update does not erase your current mathematics.
Generated files under `tools/`, `data/`, and `logs/` are ignored. Do not commit the
large mathematics or raw build logs. The legacy **1_UPDATE_MATHEMATICS.bat**
updates mathematics without pulling ALJABR. You can still drag a real Lean Graph
NDJSON export onto it to import without a Lean build.

Before updating an existing Mathlib checkout, the launcher backs up its local
Lake configuration/manifest changes to the current run's log folder, then
restores those generated configuration files. Other Mathlib source edits and
all Lean Graph edits cause it to stop. An interrupted clone can leave an
incomplete tools folder; rename that folder and retry to preserve it for review.

## Logs for debugging

Read [diagnostics/README.md](diagnostics/README.md). The GitHub diagnostics branch
contains `latest.json` (command arguments, durations, exit codes, versions and
revisions) and `latest.log` (last 80 output lines). The mathematics worker's
commands are nested under `mathematics.commands` in the report.

Full timestamped output streams live under `logs/<UTC timestamp>-<process>/`.
Each process rotates eight 4 MiB log parts; previous run folders remain available
locally. `summary.json` and `mathematics.json` retain structured command history.
If upload fails, reports remain under local `diagnostics/` and the full log
explains the upload error. An upload failure does not erase or invalidate a
successful mathematics update. Public users need write credentials only to
publish reports. Logs include local paths and upstream build output.

Useful options (run in this folder):

```text
PULL_AND_RUN.bat --check
PULL_AND_RUN.bat --no-publish
PULL_AND_RUN.bat --update-only
PULL_AND_RUN.bat --import-file "C:\path\to\real-export.ndjson"
```

`--check` only checks Python and Git and writes local diagnostics. It does not
pull, build, import mathematics, or upload. Set `ALJABR_NO_PAUSE=1` for unattended
runs. Exit code 0 means the requested operation succeeded; 1 means attention is
needed. Python bootstrap errors are recorded in `logs/bootstrap.log`.

## Validation

`py -3 -m unittest discover -s tests -v` exercises real local Git fast-forward
updates, protection of local edits/generated data, imports, failure preservation,
publication rollback, process locking and command failure reports. It uses
small temporary test fixtures, never the production mathematics dataset.
A full Lean/Mathlib build is a separate, substantial end-to-end operation.
