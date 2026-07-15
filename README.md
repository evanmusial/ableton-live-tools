Ableton Live Tools is a small Python toolkit for reading Ableton Live `.als`
session files and turning useful arrangement data into practical exports for
DJs, producers, editors, archivists, and automation workflows. It focuses on
things Ableton users often need outside Live itself: locator tracklists,
tempo-aware timeline data, Mixcloud-compatible tracklists, Adobe Audition marker
files, WebVTT chapters, CUE sheets, Markdown reports, MIDI locator markers and
timing maps, Logic Pro/Pro Tools/Cubase/Nuendo marker-map presets, REAPER marker
CSV files, project inventories, sample manifests, plugin/effects manifests,
external-asset manifests, project health checks, semantic ALS diffs, JSON
exports, fixture-backed validation workflows, and bundled project audits.

The scripts are standard-library Python and are designed to be easy to run from
a terminal, CI job, or batch-processing workflow. They are optimized for
high-performance parsing, low memory use, and low-friction command-line use on
large Ableton Live sets.

## Current Release

Version `2026.07.14` is validated for Ableton Live 12.4.3. The compatibility
suite exercises all six CLIs against the canonical project fixture with Live
12.4.3 creator metadata.

## Points Of Interest

- Extract Ableton Live arrangement locators from `.als` files with accurate
  timing across tempo changes, tempo ramps, offsets, and moved/pre-roll starts.
- Export locator data to TSV, CSV, JSON, Mixcloud text, Adobe Audition marker
  files, REAPER marker CSV files, Logic Pro/Pro Tools/Cubase/Nuendo marker-map
  presets, WebVTT chapters, CUE sheets, Markdown reports, and Standard MIDI
  marker files with optional tempo/time-signature timing maps.
- Generate precise Ableton Live timeline data for tempo events, tempo ramps,
  time signatures, detected keys, locators, clip boundaries, song end, and
  optional bar/beat grids.
- Build project inventories with tracks, clips, samples, native devices,
  third-party plugins, plugin/effect authors, and missing-sample status.
- Enumerate file-backed assets—including samples, preset files, Max for Live
  devices, and other media references—with usage, location, and portability
  status in `assets.tsv` and JSON.
- Check project health for missing samples, placeholder plugins, disabled
  material, outside-project sample and preset references, mixed sample rates,
  and other archive/collaboration risks.
- Build one project-audit folder with handoff status, manifest output, health
  reports, optional semantic diff output, and detailed manifest tables.
- Compare two `.als` files semantically so reviews can focus on meaningful
  changes to locators, timing maps, tracks, clips, samples, and devices/plugins.
- Include metadata such as BPM, bar/beat position, time signature, absolute
  seconds, normalized seconds, Ableton locator IDs, and sequential track
  numbers.
- Validate changes against canonical Ableton Live fixture files and benchmark
  performance against another git ref.

## Tools Collection

- [Extract Locators](<docs/Extract Locators.md>): `src/extract_locators.py` extracts Ableton Live arrangement locators from `.als` session files and writes timestamped tracklists. It supports tempo changes, linear tempo ramps, offsets, TSV exports, CSV exports, Mixcloud exports, Adobe Audition marker exports, REAPER marker CSV exports, Logic Pro/Pro Tools/Cubase/Nuendo MIDI marker-map presets, WebVTT chapter exports, CUE sheet exports, Markdown reports, Standard MIDI marker exports with optional tempo/time-signature timing maps, JSON exports, optional key stripping, configurable TSV/CSV heading rows, and optional locator metadata columns.

- [Extract Timeline](<docs/Extract Timeline.md>): `src/extract_timeline.py` extracts a precise Ableton Live arrangement timeline from `.als` session files. It writes an interleaved event stream for tempo, tempo ramps, time signatures, detected keys, locators, clip boundaries, song end, and optional generated bar/beat grid rows, with real wall-clock time and sample indexes when a sample rate is available.

- [Project Health Checker](<docs/Project Health Checker.md>): `src/check_project_health.py` checks an Ableton Live project for archive and collaboration risks, including missing samples, placeholder plugins, outside-project sample and preset references, mixed sample rates, disabled clips/devices, frozen clips, unknown plugin authors, unnamed tracks, and unusually long sample paths. It writes terminal, Markdown, and JSON reports with configurable CI failure thresholds and Ableton creator/version metadata.

- [Project Audit Bundle](<docs/Project Audit Bundle.md>): `src/audit_project.py` builds a bundled project handoff folder with a top-level audit, Project Manifest outputs, Project Health outputs, manifest TSV tables, and optional Semantic ALS Diff outputs. It reuses the parsed project manifest for health and audit summaries so the default bundle avoids extra full-output passes.

- [Project Manifest](<docs/Project Manifest.md>): `src/extract_project_manifest.py` extracts project-level inventory data from `.als` session files. It writes Markdown, JSON, and TSV reports for assets, tracks, clips, samples, native devices, third-party plugins, plugin/effect views sorted by author and name, and missing-file checks.

- [Semantic ALS Diff](<docs/Semantic ALS Diff.md>): `src/diff_als_semantic.py` compares two Ableton Live `.als` files using extracted project meaning rather than raw XML text. It reports summary-count changes plus added/removed tracks, clips, samples, devices/plugins, locators, tempo events, and time-signature events, with Markdown and JSON output.

## Project Notes

- [Backlog](docs/Backlog.md): Tracks delivered tools and future tool ideas.
- [Performance and Output Roadmap](<docs/Performance and Output Roadmap.md>): Tracks profiling results, optimization candidates, validation notes, and candidate export formats for future releases.

## Testing

- [Tests](tests/README.md): Run `python3 -m unittest discover -s tests` from the repository root to validate the CLI tools against the canonical Ableton Live fixture set, including the Ableton Live 12.4.3 compatibility pass.
- [Validation Benchmark](scripts/benchmark_validation.py): Run `python3 scripts/benchmark_validation.py --compare-ref=main` to measure current CLI performance against another git ref.

## License

Please read [LICENSE](LICENSE) for the terms of use.
