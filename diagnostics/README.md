# Run diagnostics

Every launcher run writes `latest.json` and `latest.log` here locally (ignored by Git).
The launcher publishes a bounded copy to the GitHub **diagnostics** branch:

- [Latest structured report](https://github.com/foreandr/ALJABR/blob/diagnostics/latest.json)
- [Latest console tail](https://github.com/foreandr/ALJABR/blob/diagnostics/latest.log)

For an LLM debugging a failed update: read both files on that branch, inspect
`mathematics.commands` for the failing command and exit code, and check the
ALJABR / Mathlib / Lean Graph revisions and toolchain. Full rotating logs,
command reports, and the previous generated browser data are under local `logs/`.
Each process retains at most eight 4 MiB log files; older run folders remain local.
These files contain command output and local paths. Never put credentials in
command arguments or upstream remote URLs. `--no-publish` keeps diagnostics local.

Upload requires Git credentials with write access. Public read-only users can
still update mathematics; a report-upload failure does not fail that update.
Uploads are fast-forward only. A competing upload is retained locally on failure.
