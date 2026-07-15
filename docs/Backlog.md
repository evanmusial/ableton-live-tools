# Backlog

Ideas for Ableton Live tools and utilities. This document is intentionally lightweight: each entry should be easy to expand into a release plan, issue, or implementation checklist later.

## Status Style

Each item keeps a plain status line instead of strike-through text:

- ✅ `Delivered`: shipped in the listed release.
- `Proposed`: useful idea, not started yet.
- `Exploring`: design or research has started, but the feature has not shipped.

## Current Development

Version `2026.06.30` is in progress on the `2026.06.30` branch. Items added
for this development cycle should stay under `Proposed` or `Exploring` until
they are implemented, validated, documented, and ready to move into the
delivered sections below.

## ✅ Delivered

### Extract Locators

Status: ✅ `Delivered`

Extract Ableton Live arrangement locators from `.als` files and export timestamped tracklists.

Delivered versions:

- `2026.05`: Initial locator extraction with TSV output, configurable headings, Mixcloud output, optional key-prefix stripping, positive/negative offsets, gzip-aware ALS reading, tempo changes, and linear tempo-ramp timing.
- `2026.05.16`: Streaming parser optimization, `src/` placement, long-form documentation, and validation against known-good examples.
- `2026.05.17`: Optional locator metadata columns and JSON export.
- `2026.05.29`: Compatibility, validation, and performance/output roadmap documentation.
- `2026.05.31`: XML parser fast paths, direct parent/depth path checks, repeatable CLI validation tests, and repeatable benchmark tooling.
- `2026.06.02`: Standard CSV export, Adobe Audition marker export with `.csv` filenames containing tab-separated marker rows for Audition import compatibility, WebVTT chapter export, CUE sheet export, Markdown report export, and Standard MIDI locator marker export.
- `2026.06.15`: REAPER marker CSV export, Logic Pro/Pro Tools/Cubase/Nuendo MIDI marker-map presets, optional Standard MIDI timing-map export with tempo and time-signature meta events, single-pass reuse of parsed timing data for MIDI output, and locator timing-context performance cleanup.

### Extract Timeline

Status: ✅ `Delivered`

Extract a precise, interleaved Ableton Live arrangement timeline with real wall-clock time, fractional seconds, and optional generated musical grid rows.

Delivered versions:

- `2026.05.21`: Initial timeline extraction with tempo events, tempo ramps, time signatures, detected key/scale entries, locators, clip boundaries, song end, optional bar/beat grids, sample-index calculation, sample-rate/bit-depth metadata, TSV output, JSON output, selectable event types, selectable columns, and `--end-beat`.
- `2026.05.29`: Compatibility, validation, and performance/output roadmap documentation.
- `2026.05.31`: XML parser fast paths, target-aware parsing, direct parent/depth path checks, repeatable CLI validation tests, and repeatable benchmark tooling.
- `2026.06.15`: Timing-context performance cleanup, lazy `details` payload construction, and beat-grid timing reuse.

### Validation And Benchmark Infrastructure

Status: ✅ `Delivered`

Add project-level safety rails so future changes can be checked against known-good Ableton output and measured consistently.

Delivered versions:

- `2026.05.17`: Canonical validation fixtures for `examples/validation/RYM_2026-03.als`.
- `2026.05.31`: Standard-library `unittest` CLI validation suite and `scripts/benchmark_validation.py` benchmark runner with optional git-ref comparison.
- `2026.06.15`: MIDI timing-map fixture and regression checks, DAW MIDI marker-map preset checks, Project Manifest semantic checks, Project Health Checker checks, Semantic ALS Diff no-change checks, plus expanded CLI argument-error coverage.

### Sample & Plugin/Effects Manifest

Status: ✅ `Delivered`

Create a bill of materials for the Live Set's audio references, native devices, third-party plugins, and effects.

Delivered versions:

- `2026.06.15`: Initial `src/extract_project_manifest.py` release with `samples.tsv`, `devices.tsv`, Markdown, JSON, sample usage counts, original file size/CRC fields, default sample rate/duration fields, resolved-path checks, missing-sample status, device/plugin locations, manufacturers, formats, enabled states, placeholder states, and preset names where detectable.

### Project Inventory

Status: ✅ `Delivered`

Produce a broad inventory of Ableton project contents.

Delivered versions:

- `2026.06.15`: Initial project inventory report with track counts, clip counts, freeze clip counts, sample counts, missing/existing sample counts, device counts, third-party plugin counts, Ableton native device counts, locator counts, tempo-event counts, time-signature-event counts, `tracks.tsv`, `clips.tsv`, `project_inventory.md`, and full `project_manifest.json`.

### Plugin Manifest

Status: ✅ `Delivered`

Extract plugins/effects used in the session, with views sorted by author and by plugin/effect name.

Delivered versions:

- `2026.06.15`: Initial plugin/effects manifest through `src/extract_project_manifest.py`, including `plugins_by_author.tsv`, `plugins_by_name.tsv`, JSON plugin views, manufacturer/author fields, format fields, track location, device position, enabled state, placeholder state, and preset names where detectable.

### Project Health Checker

Status: ✅ `Delivered`

Inspect an Ableton Live session and report anything that might make the project hard to open, transfer, archive, render, or collaborate on.

Delivered versions:

- `2026.06.15`: Initial `src/check_project_health.py` release with terminal, Markdown, and JSON reports; configurable `--fail-on=critical|warning|any|none`; critical findings for missing samples and placeholder plugins; warnings for outside-project sample references, mixed sample rates, disabled clips/devices, unknown plugin authors, unnamed tracks, and long sample paths; and info reporting for freeze clips.

Delivered checks:

- Missing audio files.
- Referenced files outside the project folder.
- Mixed sample rates.
- Placeholder plugins.
- Unknown plugin authors.
- Disabled clips or devices.
- Freeze clips.
- Very long file paths.

Delivered outputs:

- Terminal summary.
- Markdown report.
- JSON report for automation or CI.

Future expansion ideas:

- Bit-depth checks when reliable bit-depth extraction is available.
- External preset references.
- Suspicious routing, sends, or track delay.
- Ableton Live creator/version reporting in the health report.
- Full frozen-track and freeze-file reference analysis.

### Semantic ALS Diff

Status: ✅ `Delivered`

Compare two `.als` files and report meaningful musical/project changes instead of raw XML differences.

Delivered versions:

- `2026.06.15`: Initial `src/diff_als_semantic.py` release with terminal, Markdown, and JSON reports; script-friendly same/different exit behavior; `--no-fail-on-diff`; summary-count changes; and added/removed comparisons for tracks, clips, samples, devices/plugins, locators, tempo events, and time-signature events.

Delivered comparisons:

- Locators added or removed by semantic position/name signature.
- Tracks added or removed by semantic inventory signature.
- Clips added or removed by track, clip, timing, disabled state, and sample signature.
- Tempo and time-signature events added or removed.
- Devices, plugins, and effects added or removed.
- Sample references changed.

Delivered outputs:

- Human-readable Markdown diff.
- Terminal summary.
- JSON diff for Git hooks or release automation.

Future expansion ideas:

- Rename/move/reorder classification instead of added/removed inventory rows only.
- Key/scale changes.
- Mixer changes such as volume, pan, sends, mute state, and track delay.
- Automation added, removed, or changed.

## Proposed

### Project Audit Bundle

Status: `Exploring`

Build a single handoff/audit command that writes a complete review folder for one Ableton Live Set, with optional semantic diff output when a baseline set is provided.

Current `2026.06.30` scope:

- Top-level `project_audit.md` and `project_audit.json` reports.
- Project Manifest Markdown, JSON, and optional TSV tables.
- Project Health Markdown and JSON reports.
- Optional Semantic ALS Diff Markdown and JSON reports with `--before`.
- Health-based failure thresholds through `--fail-on=critical|warning|any|none`.
- Optional diff-based failure through `--fail-on-diff`.
- Performance-preserving implementation that reuses the parsed Project Manifest object for health checks and top-level audit summaries instead of shelling out to individual CLIs.

Move this item into the delivered section once the `2026.06.30` release branch is validated, merged, tagged, and published.
