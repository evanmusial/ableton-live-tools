# Project Audit Bundle

`src/audit_project.py` builds a bundled Ableton project audit folder for archive, collaboration, handoff, and release-review workflows.

The script uses only the Python 3 standard library and reuses the existing Project Manifest, Project Health Checker, and Semantic ALS Diff internals.

## Current Version

Version: `2026.06.30`

Author: Evan Musial <evan@evan.engineer>

License: Creative Commons Attribution-ShareAlike 4.0 International

This license requires that reusers give credit to the creator. It allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, even for commercial purposes. If others remix, adapt, or build upon the material, they must license the modified material under identical terms.

## Release Notes

### 2026.06.30

- Added the initial `src/audit_project.py` script.
- Added a top-level Project Audit Markdown and JSON report.
- Reused one parsed Project Manifest object for manifest output, health checks, and audit summaries.
- Added default bundle output for Project Manifest, Project Health, top-level audit, and manifest TSV tables.
- Added optional Semantic ALS Diff output with `--before`.
- Added `--fail-on=critical|warning|any|none` for project-health failure thresholds.
- Added `--fail-on-diff` for workflows that want semantic differences to return exit code `1`.
- Added `--no-tsv` for faster, smaller summary bundles.
- Added CLI validation coverage against the canonical `RYM_2026-03.als` fixture.

## What It Does

Project Audit Bundle is the one command to run when you want to know whether a Live Set is ready to archive, transfer, review, or hand to someone else.

It writes one output directory with:

- `project_audit.md`: a compact handoff summary.
- `project_audit.json`: a script-friendly top-level audit payload.
- `project_inventory.md`: the Project Manifest human-readable summary.
- `project_manifest.json`: the full Project Manifest payload.
- `project_health.md`: the Project Health report.
- `project_health.json`: the Project Health payload.
- `tracks.tsv`, `clips.tsv`, `samples.tsv`, `devices.tsv`, `plugins_by_author.tsv`, and `plugins_by_name.tsv`: detailed manifest tables.

When `--before` is provided, it also writes:

- `semantic_diff.md`
- `semantic_diff.json`

## Basic Usage

Run the script from the repository root with an Ableton session path:

```bash
python3 src/audit_project.py song.als
```

By default, the tool writes:

```text
song.als.project-audit
```

The default exit behavior matches Project Health Checker: exit code `1` when critical health findings are present, exit code `0` otherwise.

## Output Directory

Choose the output directory with `--output-dir` or `-o`:

```bash
python3 src/audit_project.py song.als --output-dir=song_audit
python3 src/audit_project.py song.als -o song_audit
```

## Semantic Diff

Use `--before` to compare an older/baseline `.als` file against the audited file:

```bash
python3 src/audit_project.py after.als --before=before.als --output-dir=after_audit
```

This adds `semantic_diff.md` and `semantic_diff.json` to the bundle. Semantic differences are reported in the audit summary, but they do not change the exit code unless `--fail-on-diff` is set.

```bash
python3 src/audit_project.py after.als --before=before.als --fail-on-diff
```

## Failure Thresholds

Use `--fail-on` to choose which project-health findings return exit code `1`:

```bash
python3 src/audit_project.py song.als --fail-on=critical
python3 src/audit_project.py song.als --fail-on=warning
python3 src/audit_project.py song.als --fail-on=any
python3 src/audit_project.py song.als --fail-on=none
```

Threshold meanings:

- `critical`: fail only when critical findings are present. This is the default.
- `warning`: fail when critical or warning findings are present.
- `any`: fail when any critical, warning, or info finding is present.
- `none`: never fail because of findings. Runtime and argument errors can still fail.

## Smaller Bundles

Use `--no-tsv` when you only need the top-level audit, manifest JSON, inventory Markdown, and health reports:

```bash
python3 src/audit_project.py song.als --no-tsv
```

This avoids writing the detailed manifest TSV tables, but it does not change the parsed audit data.

## Performance Notes

The audit command is designed to avoid unnecessary repeat parsing:

- The current `.als` file is parsed once by Project Manifest.
- That parsed manifest object is reused for Project Health and the top-level audit.
- Full locator exports and full timeline exports are not written by default.
- When `--before` is provided, the command does the extra parsing needed for semantic diff signatures.

The dedicated locator and timeline tools remain the right commands when you need every locator row, full timeline event rows, DAW marker maps, cue sheets, or chapter exports.

## Terminal Output

The script prints a short status report after it runs:

- The audited input path.
- The output directory.
- Project counts for tracks, clips, and unique samples.
- Project-health finding counts.
- Semantic diff status, or `not_run`.
- Output file count.
- Elapsed processing time, shown to three decimal places.

Reports are headed `Project Audit Results`. Runtime errors exit with status code `1`, and command-line argument errors exit with status code `2`.
