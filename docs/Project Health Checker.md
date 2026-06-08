# Project Health Checker

`src/check_project_health.py` inspects an Ableton Live `.als` session and reports conditions that can make a project harder to open, transfer, archive, render, or collaborate on.

The script uses only the Python 3 standard library and reuses the streaming parser from `src/extract_project_manifest.py`.

## Current Version

Version: `2026.06.07`

Author: Evan Musial <evan@evan.engineer>

License: Creative Commons Attribution-ShareAlike 4.0 International

This license requires that reusers give credit to the creator. It allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, even for commercial purposes. If others remix, adapt, or build upon the material, they must license the modified material under identical terms.

## Release Notes

### 2026.06.07

- Added the initial Project Health Checker CLI.
- Reused the streaming Project Manifest parser to keep memory use low on large Ableton Live sets.
- Added critical findings for missing sample references and placeholder plugins.
- Added warnings for outside-project sample references, mixed sample rates, disabled clips/devices, unknown third-party plugin authors, unnamed tracks, and unusually long sample paths.
- Added an informational finding for freeze clips so users remember to include freeze/sample media when archiving.
- Added terminal, Markdown, and JSON report output.
- Added `--fail-on=critical|warning|any|none` for CI and scripted workflows.
- Added CLI validation coverage against the canonical `RYM_2026-03.als` fixture.

## What It Does

Project Health Checker is a practical preflight report. It does not judge creative choices. It points out conditions that are easy to miss when preparing a Live Set for backup, transfer, collaboration, or release handoff.

Current checks include:

- Missing sample/audio references.
- Placeholder plugins.
- Sample references that appear to live outside the ALS file's folder.
- Mixed default sample rates in referenced samples.
- Disabled clips.
- Disabled devices/plugins.
- Unknown third-party plugin manufacturers.
- Tracks without names.
- Very long sample paths.
- Freeze clips.

## Basic Usage

Run the script from the repository root with an Ableton session path:

```bash
python3 src/check_project_health.py song.als
```

By default, the tool prints a terminal report and returns exit code `1` if critical findings are present.

## Markdown Output

Use `--markdown` to write a human-readable report:

```bash
python3 src/check_project_health.py song.als --markdown=health.md
```

The Markdown report includes finding counts, project summary counts, and the first affected items for each finding category.

## JSON Output

Use `--json` to write automation-friendly report data:

```bash
python3 src/check_project_health.py song.als --json=health.json
```

Choose JSON formatting with `--json-format`:

```bash
python3 src/check_project_health.py song.als --json=health.json --json-format=compact
python3 src/check_project_health.py song.als --json=health.json --json-format=pretty
```

JSON output includes:

- Metadata.
- Overall status.
- Exit code for the current failure threshold.
- Project summary counts.
- Finding counts by severity.
- Full finding records.

## Failure Thresholds

Use `--fail-on` to choose what should make the CLI return exit code `1`:

```bash
python3 src/check_project_health.py song.als --fail-on=critical
python3 src/check_project_health.py song.als --fail-on=warning
python3 src/check_project_health.py song.als --fail-on=any
python3 src/check_project_health.py song.als --fail-on=none
```

Threshold meanings:

- `critical`: fail only when critical findings are present. This is the default.
- `warning`: fail when critical or warning findings are present.
- `any`: fail when any critical, warning, or info finding is present.
- `none`: never fail because of findings. Runtime and argument errors can still fail.

`--fail-on=none` is useful when generating reports from known-incomplete fixture sessions or when collecting data without gating a job.

## Terminal Output

The script prints a short status report after it runs:

- The input session path.
- Critical finding count.
- Warning finding count.
- Info finding count.
- One `output` row for each written Markdown or JSON file.
- Elapsed processing time, shown to three decimal places.

Reports are headed `Project Health Results`. Runtime errors exit with status code `1`, and command-line argument errors exit with status code `2`.

## Notes For Maintainers

The health checker intentionally depends on the Project Manifest parser. That keeps sample, clip, track, device, and plugin extraction centralized instead of creating a parallel parser with subtly different behavior.

Future health checks should be added only after the underlying field is parsed deliberately. Good candidates include mixer/routing checks, sends, track delay, external preset references, and more complete plugin availability hints.
