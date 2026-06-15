# Semantic ALS Diff

`src/diff_als_semantic.py` compares two Ableton Live `.als` files using extracted project meaning instead of raw XML text.

The script uses only the Python 3 standard library and reuses the existing locator and project manifest parsers.

## Current Version

Version: `2026.06.15`

Author: Evan Musial <evan@evan.engineer>

License: Creative Commons Attribution-ShareAlike 4.0 International

This license requires that reusers give credit to the creator. It allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, even for commercial purposes. If others remix, adapt, or build upon the material, they must license the modified material under identical terms.

## Release Notes

### 2026.06.15

- Added the initial Semantic ALS Diff CLI.
- Compared high-level summary counts between two Ableton Live sessions.
- Added semantic added/removed comparisons for tracks, clips, samples, devices/plugins, locators, tempo events, and time-signature events.
- Added Markdown and JSON reports.
- Added script-friendly exit behavior: `0` when files are semantically the same, `1` when semantic differences are found, and `2` for command-line argument errors.
- Added `--no-fail-on-diff` for report-only workflows.
- Added CLI validation coverage for the identical-file no-change case.
- Tested and validated with Ableton Live 12.4.2 sessions.

## What It Does

Raw `.als` XML diffs can be extremely noisy. A small musical edit can appear beside a large amount of unrelated XML churn, object IDs, ordering details, or implementation-specific Ableton data.

Semantic ALS Diff extracts practical project inventories from each file and compares those extracted meanings.

Current comparison categories:

- Summary counts.
- Tracks.
- Clips.
- Sample/audio references.
- Native devices.
- Third-party plugins/effects.
- Locators.
- Tempo events.
- Time-signature events.

This first version does not yet compare mixer state, routing, sends, track delay, detailed device parameters, or automation envelopes beyond the tempo/time-signature data already used by the timing tools.

## Basic Usage

Run the script from the repository root with a baseline file and a comparison file:

```bash
python3 src/diff_als_semantic.py before.als after.als
```

The command returns exit code `0` when no semantic differences are detected and exit code `1` when differences are detected.

## Markdown Output

Use `--markdown` to write a human-readable report:

```bash
python3 src/diff_als_semantic.py before.als after.als --markdown=diff.md
```

The Markdown report includes summary-count changes and added/removed rows for each semantic section with changes.

## JSON Output

Use `--json` to write automation-friendly diff data:

```bash
python3 src/diff_als_semantic.py before.als after.als --json=diff.json
```

Choose JSON formatting with `--json-format`:

```bash
python3 src/diff_als_semantic.py before.als after.als --json=diff.json --json-format=compact
python3 src/diff_als_semantic.py before.als after.als --json=diff.json --json-format=pretty
```

JSON output includes:

- Metadata.
- Overall status.
- Total change count.
- Summary changes.
- Added/removed rows for each semantic section.

## Report-Only Mode

Use `--no-fail-on-diff` when you want a report but do not want differences to return exit code `1`:

```bash
python3 src/diff_als_semantic.py before.als after.als --no-fail-on-diff --json=diff.json
```

This is useful in scheduled archive reports or dashboards where differences are expected.

## Terminal Output

The script prints a short status report after it runs:

- The before file.
- The after file.
- Total semantic change count.
- Added row count.
- Removed row count.
- One `output` row for each written Markdown or JSON file.
- Elapsed processing time, shown to three decimal places.

Reports are headed `Semantic ALS Diff Results`. Runtime errors exit with status code `1`, and command-line argument errors exit with status code `2`.

## Notes For Maintainers

The semantic diff intentionally compares only fields that are already parsed with confidence by the project tools. Expanding it should generally start by adding richer parser support to `extract_project_manifest.py` or the timing tools, then exposing that new data here.

Good future candidates include mixer settings, routing, sends, track delay, device parameter summaries, automation presence, and more precise changed/renamed/reordered classification instead of added/removed inventory rows only.
