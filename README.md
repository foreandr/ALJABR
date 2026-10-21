# ALJABR — Mathlib-only prototype

This revision **does not include** the hand-built ALJABR graph. Every mathematical node and edge displayed comes from Lean Graph's Mathlib extraction. The initial coverage is correctly ZERO until a real import succeeds. No synthetic data or bundled fake examples.

## Two buttons

1. **`1_UPDATE_MATHEMATICS.bat`** — download/update Mathlib and Lean Graph, extract a fresh NDJSON graph, import it, rebuild the UI data. Requires **Git and Python 3**. If Lean 4 (elan/Lake) is absent, the launcher downloads and installs it automatically for your Windows user. No virtual environment is created. This is a substantial download/build (several GB). It does not create a Python venv or install pip packages. If Lean Graph and the latest Mathlib are incompatible, this step may require adjusting versions. The Windows integration has not yet been verified end to end.
2. **`2_OPEN_ALJABR.bat`** — open the HTML UI. Works without Python if the prebuilt JS file is present.

Alternative: drag an **existing Lean Graph unified `.ndjson` export** onto `1_UPDATE_MATHEMATICS.bat`. This skips Git/Lean compilation and only requires Python 3. Exports are created by the author's `lake exe graph --mode unified --to Mathlib output.ndjson` command.

## Coverage

Top bar shows **actual declaration count**, **dependency count**, **structure/class count**, and import status. These measure the imported collection, not a percentage of all mathematical ideas. Existing ALJABR curated structures/construction routes are intentionally absent.

## Data

- `import_lean.py`: NDJSON to `data/lean_import.json` (preserves source names and typed edges).
- `build.py`: produces offline-loadable `aljabr-data.js`.
- `aljabr.html`: searchable UI for the imported graph.
- `setup_lean.py`: attaches the extractor to a Mathlib checkout.

Data is written atomically after successful conversion. Failed extraction leaves the last successful JSON/JS unchanged. Original ALJABR is not reconstructed unless Lean Graph contains corresponding formal declarations; visual semantics such as hand-crafted alternative construction routes do not automatically reappear.

Sources: https://github.com/aurasoph/lean-graph ; https://github.com/leanprover-community/mathlib4 . Both upstream projects use Apache 2.0 licensing.

## Automatic Lean setup

Launcher 1 calls `install_lean.ps1` only when Lake is missing. It downloads the official elan installer over HTTPS from `https://elan.lean-lang.org/elan-init.ps1`, installs it into the normal user directory, and adds `%USERPROFILE%\.elan\bin` to the current launcher PATH immediately (no terminal restart). A compatible Lean toolchain is then selected via the Mathlib repository’s pinned `lean-toolchain` file. Requires an Internet connection.

## v5 installer fix
The automatic Lean installer now invokes the downloaded PowerShell script directly in the same process, ensuring its Boolean NoPrompt parameter is passed as a Boolean rather than the string from `powershell.exe -File`. No venv required.

## v6 compatibility fix
Your v5 log showed LeanGraph/MainGraph.lean failing to compile against Mathlib's Lean v4.36.0-rc1. The upstream Lean Graph repository currently specifies `leanprover/lean4:v4.29.0`. v6 pins Mathlib4 to its `v4.29.0` tag, allowing Lake to install and use the matching Lean version automatically. The installer no longer follows Mathlib `master` blindly.

If you still have v5's `tools` directory, you can copy it into this release to reuse the Lean Graph checkout; the updater switches Mathlib to v4.29.0 and downloads only the cache for that version. Do not copy the old `data/mathlib_unified.ndjson` as if it were a completed extract.

**Note:** This patch is based on upstream version metadata and your log; the full Windows extraction has not yet been run successfully in this environment.

## v7 lockfile fix
Version 6 used plain `lake update`, which upgraded Mathlib's dependencies from the historical v4.29.0 manifest and then switched the compiler to v4.36.0-rc1. Version 7 runs a targeted `lake update leanGraph --keep-toolchain` and checks every original Mathlib dependency revision afterward. It will stop with a clear message rather than compile mismatched versions if Lake updates anything unexpectedly.

**For v6 users:** Copy your `tools` folder into this v7 folder. The launcher restores Mathlib's versioned Lake configuration/manifest with `git checkout` and obtains precompiled artifacts for the pinned version. Do not manually run plain `lake update` in the Mathlib directory.
