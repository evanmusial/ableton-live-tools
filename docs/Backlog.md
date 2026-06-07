# Backlog

Ideas for Ableton Live tools and utilities. This document is intentionally lightweight: each entry should be easy to expand into a release plan, issue, or implementation checklist later.

## Status Style

Each item keeps a plain status line instead of strike-through text:

- ✅ `Delivered`: shipped in the listed release.
- `Proposed`: useful idea, not started yet.
- `Exploring`: design or research has started, but the feature has not shipped.

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
- `2026.06.07`: Optional Standard MIDI timing-map export with tempo and time-signature meta events, single-pass reuse of parsed timing data for MIDI output, and locator timing-context performance cleanup.

### Extract Timeline

Status: ✅ `Delivered`

Extract a precise, interleaved Ableton Live arrangement timeline with real wall-clock time, fractional seconds, and optional generated musical grid rows.

Delivered versions:

- `2026.05.21`: Initial timeline extraction with tempo events, tempo ramps, time signatures, detected key/scale entries, locators, clip boundaries, song end, optional bar/beat grids, sample-index calculation, sample-rate/bit-depth metadata, TSV output, JSON output, selectable event types, selectable columns, and `--end-beat`.
- `2026.05.29`: Compatibility, validation, and performance/output roadmap documentation.
- `2026.05.31`: XML parser fast paths, target-aware parsing, direct parent/depth path checks, repeatable CLI validation tests, and repeatable benchmark tooling.
- `2026.06.07`: Timing-context performance cleanup, lazy `details` payload construction, and beat-grid timing reuse.

### Validation And Benchmark Infrastructure

Status: ✅ `Delivered`

Add project-level safety rails so future changes can be checked against known-good Ableton output and measured consistently.

Delivered versions:

- `2026.05.17`: Canonical validation fixtures for `examples/validation/RYM_2026-03.als`.
- `2026.05.31`: Standard-library `unittest` CLI validation suite and `scripts/benchmark_validation.py` benchmark runner with optional git-ref comparison.
- `2026.06.07`: MIDI timing-map fixture and regression checks, plus expanded CLI argument-error coverage.

## Proposed

## Project Health Checker

Status: `Proposed`

Inspect an Ableton Live session and report anything that might make the project hard to open, transfer, archive, render, or collaborate on.

Possible checks:

- Missing audio files.
- Referenced files outside the project folder.
- Mixed sample rates or bit depths.
- Missing, unknown, or unavailable plugins.
- Disabled clips or devices.
- Frozen tracks and freeze-file references.
- External preset references.
- Very long file paths.
- Suspicious routing, sends, or track delay.
- Ableton Live version used to create the set.

Possible outputs:

- Terminal summary.
- Markdown report.
- JSON report for automation or CI.

## Semantic ALS Diff

Status: `Proposed`

Compare two `.als` files and report meaningful musical/project changes instead of raw XML differences.

Possible comparisons:

- Locators added, removed, renamed, or moved.
- Tracks added, removed, renamed, reordered, recolored, or regrouped.
- Clips moved, shortened, lengthened, disabled, renamed, or retimed.
- Tempo, time signature, and key/scale changes.
- Devices, plugins, and effects added, removed, reordered, or changed.
- Mixer changes such as volume, pan, sends, mute state, and track delay.
- Automation added, removed, or changed.
- Sample references changed.

Possible outputs:

- Human-readable Markdown diff.
- Terminal summary.
- JSON diff for Git hooks or release automation.

## Sample & Plugin/Effects Manifest

Status: `Proposed`

Create a bill of materials for everything the Live Set depends on.

Possible fields:

- Audio file paths, relative paths, sizes, sample rates, bit depths, durations, and checksums.
- Which clips use each audio file.
- Missing-file status.
- Built-in Ableton devices.
- Third-party plugins and effects.
- Max for Live devices.
- Preset references where available.
- Track and device-chain location for each dependency.

Possible outputs:

- TSV manifest.
- JSON manifest.
- Markdown archive report.

## Project Inventory

Status: `Proposed`

Produce a broad inventory of the contents of an Ableton Live project, covering all MIDI files, sound files, plugins, effects, devices, tracks, groups, and arrangement/session elements that can be reasonably extracted from the `.als` file.

Possible fields:

- Tracks, groups, returns, and master track.
- Track names, colors, routing, sends, and clip counts.
- MIDI clips and MIDI note counts.
- Audio clips and source media.
- Locators.
- Tempo and time signature map.
- Session and clip scale/key metadata.
- Devices, plugins, effects, racks, and macros.
- Automation envelope counts by track/device/parameter.

Possible outputs:

- Markdown project summary.
- TSV tables for spreadsheet review.
- JSON for scripting and future tools.

## Plugin Manifest

Status: `Proposed`

Extract every plugin/effect used in the session, with views sorted by author and by plugin/effect name.

Possible fields:

- Plugin/effect name.
- Manufacturer/author, where detectable.
- Format or device type, such as Ableton native, AU, VST, VST3, or Max for Live.
- Track name.
- Device-chain position.
- Rack location and macro context.
- Enabled/disabled state.
- Preset reference, where available.
- Duplicate usage count.
- Missing or unavailable status, where detectable.

Possible outputs:

- `plugins_by_author.tsv`
- `plugins_by_name.tsv`
- Markdown plugin report.
- JSON manifest for automation.
