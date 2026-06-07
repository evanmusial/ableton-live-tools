# Performance and Output Roadmap

This document records performance findings and export-format candidates for future Ableton Live Tools releases. It is meant to keep profiling notes close to the code without treating unimplemented ideas as shipped behavior.

## 2026.05.29 Profiling Baseline

Benchmarks were run on `examples/validation/RYM_2026-03.als` with Python 3.14.5.

| Tool | Command Shape | Rows / Events | Reported Elapsed Time |
| --- | --- | ---: | ---: |
| `src/extract_locators.py` | TSV + Mixcloud + JSON, all locator columns | 66 locators | `0.873s` |
| `src/extract_timeline.py` | Default timeline TSV + JSON | 2331 events | `1.707s` |
| `src/extract_timeline.py` | Beat grid with tempo, time signature, key, and locator events | 10692 events | `1.695s` |

The main finding is that XML parsing dominates runtime. Output writing is comparatively small, even when both TSV and JSON are enabled.

## Highest-Value Optimization Candidates

- [x] Add target-aware parsing to `src/extract_timeline.py`, so clip, media, audio-header, and sample metadata are collected only when the selected event types or columns require them.
- [x] Add a tag-name fast path in XML start-element handlers, so most unrelated XML elements can return before expensive path matching.
- [x] Add a tag-name fast path in XML end-element handlers, so most unrelated closing tags skip deeper parser-state checks.
- [x] Replace fixed tuple-slice path checks with direct parent/depth checks for hot XML paths.
- [x] Defer media-path and audio-header work until an output column or metadata block actually needs source file details.
- [x] Avoid building or serializing event `details` payloads unless the selected columns include `details`.
- Keep streaming XML parsing as the default model, because it preserves the large memory savings already achieved in `2026.05.16`.

## 2026.05.31 Measured Improvements

Benchmarks were run on `examples/validation/RYM_2026-03.als` with Python 3.14.5. Each row uses the median of seven runs and the elapsed time reported by the CLI.

| Tool / Export Shape | Baseline Median | Optimized Median | Change |
| --- | ---: | ---: | ---: |
| `extract_locators.py` metadata TSV + JSON | `0.844s` | `0.691s` | `18.1%` faster |
| `extract_timeline.py` locator-only TSV | `1.568s` | `0.698s` | `55.5%` faster |
| `extract_timeline.py` beat grid with tempo, time signature, key, locator, and sample index | `1.631s` | `0.773s` | `52.6%` faster |
| `extract_timeline.py` full TSV + JSON | `1.645s` | `0.783s` | `52.4%` faster |

Implemented changes:

- Added tag-name fast paths to both XML parsers.
- Added tag-name fast paths to both XML end handlers.
- Added target-aware timeline parsing so lightweight exports can skip clip/sample structures.
- Replaced fixed tuple-slice path checks with direct parent/depth checks.
- Added an end-to-end `unittest` CLI validation suite under `tests/`.
- Added `scripts/benchmark_validation.py` so validation benchmarks can be repeated consistently and compared against a git ref.

Validation:

- `python3 -m py_compile src/extract_locators.py src/extract_timeline.py tests/test_cli_validation.py`
- `python3 -m unittest discover -s tests`
- `python3 scripts/benchmark_validation.py --compare-ref=main`
- `git diff --check`
- Full timeline TSV output compared byte-for-byte against `main`.
- Full timeline JSON output differs from `main` only in the expected script-version metadata field.
- Core beat-grid timeline TSV output compared byte-for-byte against `main`.

## Delivered Output Formats

- Adobe Audition marker import (`.csv`): delivered in `2026.06.02` for `extract_locators.py`. The filename extension follows Audition's import workflow, while the file contents are intentionally tab-separated marker rows.
- CSV (`.csv`): delivered in `2026.06.02` for `extract_locators.py` as a normal comma-separated mirror of the selected TSV/JSON locator columns.
- WebVTT (`.vtt`): delivered in `2026.06.02` for `extract_locators.py` as locator-based chapter cues.
- CUE sheet (`.cue`): delivered in `2026.06.02` for `extract_locators.py` as locator-based track indexes with optional rendered-audio filename selection.
- Markdown (`.md`): delivered in `2026.06.02` for `extract_locators.py` as a human-readable locator report that mirrors selected export columns.
- Standard MIDI marker file (`.mid`): delivered in `2026.06.02` for `extract_locators.py` as locator marker meta events at absolute Ableton beat positions.
- Optional MIDI timing map (`.mid`): delivered in `2026.06.07` for `extract_locators.py` with tempo and time-signature meta events alongside locator marker meta events.

## Output Format Candidates

- MIDI key-signature map (`.mid`): add key-signature meta events when a reliable global key/signature source can be extracted from the ALS.
- REAPER marker CSV: export locators and timing markers for moving cue data into REAPER.

## 2026.06.07 Performance Check

Benchmarks were run on `examples/validation/RYM_2026-03.als` with Python 3.14.5. Each row uses the median of seven runs and the elapsed time reported by the CLI.

| Tool / Export Shape | Baseline Median | Optimized Median | Change |
| --- | ---: | ---: | ---: |
| `extract_locators.py` metadata TSV + JSON | `0.694s` | `0.691s` | `0.4%` faster |
| `extract_timeline.py` locator-only TSV | `0.706s` | `0.703s` | `0.4%` faster |
| `extract_timeline.py` beat grid with tempo, time signature, key, locator, and sample index | `0.774s` | `0.762s` | `1.6%` faster |
| `extract_timeline.py` full TSV + JSON | `0.803s` | `0.781s` | `2.7%` faster |

These changes are cleanup-oriented and low-risk rather than a major parser breakthrough. The final validation comparison showed modest improvements across all measured benchmark cases.

Implemented changes:

- Precomputed time-signature section-start positions in both locator and timeline timing contexts.
- Replaced per-row timing dictionaries with compact named tuple timing contexts.
- Deferred timeline `details` dictionaries unless the selected columns include `details`.
- Reused the generated bar row's timing values for the matching beat-one row in beat-grid timeline exports.
- Raised the locator parser's streaming XML read chunk size from `1 MiB` to `4 MiB`.
- Added optional MIDI timing-map output with tempo and time-signature meta events for `extract_locators.py`.
- Reused the locator extractor's parsed tempo and time-signature maps for MIDI timing output instead of reparsing the ALS file.

Validation:

- `python3 -m py_compile src/extract_locators.py src/extract_timeline.py tests/test_cli_validation.py`
- `python3 -m unittest discover -s tests`
- `python3 scripts/benchmark_validation.py --compare-ref=main`
- `git diff --check`
- Standard marker-only MIDI output remained byte-identical to the existing validation fixture.
- New MIDI timing-map output compared byte-for-byte against `examples/validation/RYM_2026-03_markers_timing.mid`.

## 2026.06.02 Validation Notes

The usual validation flow was run after adding CSV, Adobe Audition marker, WebVTT, CUE sheet, Markdown, and MIDI marker exports:

- `python3 -m py_compile src/extract_locators.py tests/test_cli_validation.py`
- `python3 -m unittest discover -s tests`
- `python3 scripts/benchmark_validation.py --compare-ref=main`
- `git diff --check`
- Standard CSV, Adobe Audition marker, WebVTT, CUE, Markdown, and MIDI fixtures compared byte-for-byte against generated output.
- Existing high-resolution TSV/Mixcloud, metadata TSV/JSON, timeline locator cross-check, missing-file error, and argument-error checks passed.

Benchmark comparison against `main` showed no material performance movement:

| Case | Baseline Median | Current Median | Change |
| --- | ---: | ---: | ---: |
| Locators metadata TSV + JSON | `0.705s` | `0.702s` | `0.4%` faster |
| Timeline locator-only TSV | `0.706s` | `0.718s` | `1.7%` slower |
| Timeline beat-grid core TSV | `0.769s` | `0.795s` | `3.4%` slower |
| Timeline full TSV + JSON | `0.797s` | `0.823s` | `3.3%` slower |

The expanded all-format locator export, with TSV, JSON, Mixcloud, standard CSV,
Adobe Audition markers, WebVTT, CUE, Markdown, and MIDI all enabled, had a
median elapsed time of `0.707s` across seven runs on the validation fixture.
No benchmark showed a significant speed improvement or deterioration.

## 2026.05.29 Validation Notes

The usual validation flow was run after the documentation and compatibility updates:

- `python3 -m py_compile src/extract_locators.py src/extract_timeline.py`
- `git diff --check`
- High-resolution locator TSV and Mixcloud fixture comparison.
- Locator metadata TSV and pretty JSON fixture comparison.
- Extract Timeline locator cross-check against Extract Locators metadata at matching precision.
- Full Extract Timeline TSV + JSON run.
- Beat-grid Extract Timeline run.
- Success and missing-file exit-code checks for both scripts.

Known fixture note: the standard locator TSV and Mixcloud fixtures include the manually added `Mysterium - Show Intro` row. After ignoring that row, the generated timings match the fixture shape. One standard-fixture label has manual capitalization (`Lift Me Up`) while the ALS locator text, high-resolution fixture, and metadata fixture preserve `LIft Me Up`.
