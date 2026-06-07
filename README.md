Ableton Live Tools is a small Python toolkit for reading Ableton Live `.als`
session files and turning useful arrangement data into practical exports for
DJs, producers, editors, archivists, and automation workflows. It focuses on
things Ableton users often need outside Live itself: locator tracklists,
tempo-aware timeline data, Mixcloud-compatible tracklists, Adobe Audition marker
files, WebVTT chapters, CUE sheets, Markdown reports, MIDI locator markers and
timing maps, JSON exports, and fixture-backed validation workflows.

The scripts are standard-library Python and are designed to be easy to run from
a terminal, CI job, or batch-processing workflow. They are optimized for
high-performance parsing, low memory use, and low-friction command-line use on
large Ableton Live sets.

## Points Of Interest

- Extract Ableton Live arrangement locators from `.als` files with accurate
  timing across tempo changes, tempo ramps, offsets, and moved/pre-roll starts.
- Export locator data to TSV, CSV, JSON, Mixcloud text, Adobe Audition marker
  files, WebVTT chapters, CUE sheets, Markdown reports, and Standard MIDI marker
  files with optional tempo/time-signature timing maps.
- Generate precise Ableton Live timeline data for tempo events, tempo ramps,
  time signatures, detected keys, locators, clip boundaries, song end, and
  optional bar/beat grids.
- Include metadata such as BPM, bar/beat position, time signature, absolute
  seconds, normalized seconds, Ableton locator IDs, and sequential track
  numbers.
- Validate changes against canonical Ableton Live fixture files and benchmark
  performance against another git ref.

## Tools Collection

- [Extract Locators](<docs/Extract Locators.md>): `src/extract_locators.py` extracts Ableton Live arrangement locators from `.als` session files and writes timestamped tracklists. It supports tempo changes, linear tempo ramps, offsets, TSV exports, CSV exports, Mixcloud exports, Adobe Audition marker exports, WebVTT chapter exports, CUE sheet exports, Markdown reports, Standard MIDI marker exports with optional tempo/time-signature timing maps, JSON exports, optional key stripping, configurable TSV/CSV heading rows, and optional locator metadata columns.

- [Extract Timeline](<docs/Extract Timeline.md>): `src/extract_timeline.py` extracts a precise Ableton Live arrangement timeline from `.als` session files. It writes an interleaved event stream for tempo, tempo ramps, time signatures, detected keys, locators, clip boundaries, song end, and optional generated bar/beat grid rows, with real wall-clock time and sample indexes when a sample rate is available.

## Project Notes

- [Performance and Output Roadmap](<docs/Performance and Output Roadmap.md>): Tracks profiling results, optimization candidates, validation notes, and candidate export formats for future releases.

## Testing

- [Tests](tests/README.md): Run `python3 -m unittest discover -s tests` from the repository root to validate the CLI tools against the canonical Ableton Live fixture set.
- [Validation Benchmark](scripts/benchmark_validation.py): Run `python3 scripts/benchmark_validation.py --compare-ref=main` to measure current CLI performance against another git ref.

## License

Please read [LICENSE](LICENSE) for the terms of use.
