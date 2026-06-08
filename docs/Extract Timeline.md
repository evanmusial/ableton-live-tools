# Extract Timeline

`src/extract_timeline.py` extracts a precise, interleaved Ableton Live arrangement timeline from an `.als` session file. It is designed for cue sheets, technical audits, archive notes, post-production validation, and any workflow that needs to map Ableton beats to real wall-clock time with fractional seconds.

The script uses only the Python 3 standard library.

## Current Version

Version: `2026.06.07`

Author: Evan Musial <evan@evan.engineer>

License: Creative Commons Attribution-ShareAlike 4.0 International

This license requires that reusers give credit to the creator. It allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, even for commercial purposes. If others remix, adapt, or build upon the material, they must license the modified material under identical terms.

## Release Notes

### 2026.06.07

- Precomputed time-signature section-start positions so repeated timeline rows do not recalculate section-start labels.
- Changed timeline timing context from dictionaries to a compact named tuple.
- Built optional `details` dictionaries only when the selected output columns include `details`.
- Reused generated bar-row timing values for matching beat-one rows in beat-grid exports.
- Against `main` on `RYM_2026-03.als`, the locator-only benchmark improved from `0.729s` to `0.712s`, about `2.3%` faster.
- Against `main` on `RYM_2026-03.als`, the beat-grid core benchmark improved from `0.795s` to `0.762s`, about `4.2%` faster.
- Against `main` on `RYM_2026-03.als`, the full TSV + JSON benchmark moved from `0.785s` to `0.797s`, about `1.5%` slower, which is not a material regression on this fixture.
- Confirmed the expanded standard-library CLI validation suite passes with eleven checks.

### 2026.05.31

- Added tag-name fast paths to the XML start and end handlers so unrelated Ableton tags skip deeper parser-state checks.
- Replaced fixed tuple-slice path checks with direct parent/depth checks in the XML parser.
- Added target-aware timeline parsing so lightweight exports can skip clip/sample structures when selected event types and columns do not need them.
- Added the first standard-library `unittest` CLI validation suite under `tests/`.
- Added `scripts/benchmark_validation.py` for repeatable validation benchmarks.
- Added a root README testing pointer for `python3 -m unittest discover -s tests`.
- On the `RYM_2026-03.als` locator-only benchmark, median elapsed time improved from `1.568s` to `0.698s`, about `55.5%` faster.
- On the `RYM_2026-03.als` beat-grid core timeline benchmark, median elapsed time improved from `1.631s` to `0.773s`, about `52.6%` faster.
- On the `RYM_2026-03.als` full TSV + JSON benchmark, median elapsed time improved from `1.645s` to `0.783s`, about `52.4%` faster.
- Confirmed full timeline TSV and core beat-grid timeline TSV output remain byte-identical to `main`.
- Confirmed full timeline JSON output differs from `main` only in the expected script-version metadata field.

### 2026.05.29

- Added [Performance and Output Roadmap.md](<Performance and Output Roadmap.md>) with profiling baselines, optimization candidates, output-format candidates, and validation notes.
- Re-ran the usual validation checks against `examples/validation/RYM_2026-03.als` on Python 3.14.5.
- Confirmed locator timeline rows match Extract Locators metadata at matching precision.
- Confirmed full TSV + JSON timeline export completed successfully with 2331 events.
- Confirmed beat-grid timeline export completed successfully with 10692 events.
- Confirmed CLI success and missing-file error paths return script-friendly exit codes.
- Tested with Ableton Live 12.4.1, released May 28, 2026.

### 2026.05.21

- Added the initial `src/extract_timeline.py` script.
- Added timeline export rows for tempo events, tempo-ramp intervals, time signature changes, detected session and clip key/scale entries, locators, clip starts, clip ends, and song end.
- Added `--grid=bars` and `--grid=beats` for optional generated musical grid rows.
- Added wall-clock timing with fractional seconds using the same tempo-change and linear tempo-ramp math validated by `src/extract_locators.py`.
- Added sample-index calculation when the sample rate can be detected unambiguously or supplied with `--sample-rate`.
- Added sample-rate metadata detection from Ableton `SampleRef` data.
- Added audio-file metadata inspection for WAV, AIFF, AIFC, and FLAC files when referenced source audio is available on disk.
- Added TSV export and optional JSON export with `--json`.
- Added `--json-format=pretty|compact`.
- Added selectable event types with `--event-types`.
- Added selectable export columns with `--columns`.
- Added `--end-beat` for manual timeline/grid length control.
- Added xterm-256 style CLI reports matching the visual conventions of `src/extract_locators.py`.

## What It Does

Ableton `.als` files are XML documents, usually gzip-compressed. Extract Timeline streams that XML and collects arrangement-level timing data without building the entire XML tree in memory.

The exported timeline is one sorted event stream. Every row has the same timing fields, and rows that share the exact same beat/wall time are listed next to each other with duplicated timing values. The output remains one event per row, which makes it friendly to spreadsheets, databases, scripts, and timeline review.

Core event types are:

- `tempo`: a tempo automation point.
- `tempo_ramp`: an interval where one tempo value ramps linearly into the next.
- `time_signature`: a time signature change.
- `key`: a detected session or clip key/scale entry.
- `locator`: an arrangement locator, with the locator label preserved exactly.
- `clip_start`: an arrangement clip start.
- `clip_end`: an arrangement clip end.
- `song_end`: the detected or user-specified end of the exported timeline.
- `bar`: a generated bar marker when `--grid=bars` or `--grid=beats` is used.
- `beat`: a generated beat marker when `--grid=beats` is used.

## Timing Model

Ableton stores arrangement positions in quarter-note beat units. The script converts those beat positions into real elapsed time.

Constant tempo sections use:

```text
seconds = beats * 60 / BPM
```

Linear tempo ramps integrate `60 / BPM` across the ramp interval. That means ramp timing uses logarithmic math instead of a simple average tempo. This is the same timing approach used by Extract Locators.

Time signatures affect `song_position`, bar numbers, and generated grid rows. They do not directly change elapsed seconds.

Sample indexes are calculated after wall-clock seconds are known:

```text
sample_index = round(wall_seconds * sample_rate)
```

Bit depth is exported as metadata when it can be detected from referenced audio files, but bit depth does not affect sample-index math.

## Basic Usage

Run the script from the repository root with an Ableton session path:

```bash
python3 src/extract_timeline.py path/to/song.als
```

If no output file is specified, the script writes `<input filename>.timeline.tsv` in the current directory. For example, running the command with `song.als` creates `song.als.timeline.tsv`.

Use `--output` or `-o` to choose the TSV output path:

```bash
python3 src/extract_timeline.py song.als --output=song.timeline.tsv
python3 src/extract_timeline.py song.als -o song.timeline.tsv
```

## JSON Output

Use `--json` or `-j` to write a JSON file in addition to TSV:

```bash
python3 src/extract_timeline.py song.als --json=song.timeline.json
python3 src/extract_timeline.py song.als -j song.timeline.json
```

Human-readable JSON is the default:

```bash
python3 src/extract_timeline.py song.als --json=song.timeline.json --json-format=pretty
```

Use compact JSON when file size matters:

```bash
python3 src/extract_timeline.py song.als --json=song.timeline.json --json-format=compact
```

JSON includes a `metadata` object with source file details, Ableton version fields from the ALS, detected sample rates, detected bit depths, selected grid mode, selected event types, and detected end time.

## Grid Output

By default, generated grid rows are not included:

```bash
python3 src/extract_timeline.py song.als --grid=none
```

Use `--grid=bars` to add one generated row at each bar start:

```bash
python3 src/extract_timeline.py song.als --grid=bars --output=song.timeline-bars.tsv
```

Use `--grid=beats` to add both bar rows and beat rows:

```bash
python3 src/extract_timeline.py song.als --grid=beats --output=song.timeline-beats.tsv
```

When a bar and beat occur at the same time, both rows are written. The wall time, sample index, beat position, tempo, and time signature fields are duplicated, but the event rows remain separate.

## Event Type Selection

The default is `--event-types=all`, which includes:

```text
tempo,tempo_ramp,time_signature,key,locator,clip_start,clip_end,song_end
```

Generated `bar` and `beat` rows are controlled separately with `--grid`.

Export only the core musical map:

```bash
python3 src/extract_timeline.py song.als --event-types=tempo,time_signature,key,locator
```

Export only locators on the absolute session timeline:

```bash
python3 src/extract_timeline.py song.als --event-types=locator --columns=wall_time,wall_seconds,sample_index,name,event_id,absolute_beats
```

Export clip boundaries:

```bash
python3 src/extract_timeline.py song.als --event-types=clip_start,clip_end --output=clip-boundaries.tsv
```

## Columns

The default column set is `all`:

```text
wall_time
wall_seconds
sample_index
event_type
song_position
absolute_beats
tempo_bpm
time_signature
key
name
value
event_id
source
source_path
sample_rate
bit_depth
duration_seconds
details
```

Use `--columns` to export a smaller set:

```bash
python3 src/extract_timeline.py song.als --columns=wall_time,event_type,name,value
```

Useful compact review export:

```bash
python3 src/extract_timeline.py song.als --columns=wall_time,sample_index,event_type,song_position,name,value
```

Locator-focused export:

```bash
python3 src/extract_timeline.py song.als --event-types=locator --columns=wall_time,wall_seconds,sample_index,name,event_id,absolute_beats
```

Tempo-focused export:

```bash
python3 src/extract_timeline.py song.als --event-types=tempo,tempo_ramp --columns=wall_time,event_type,absolute_beats,tempo_bpm,value,duration_seconds,details
```

## Precision

The default numeric precision is six decimal places:

```bash
python3 src/extract_timeline.py song.als --precision=6
```

Use fewer decimals for human-facing review:

```bash
python3 src/extract_timeline.py song.als --precision=3
```

Use more decimals for technical validation:

```bash
python3 src/extract_timeline.py song.als --precision=9
```

`--precision` affects `wall_time`, `wall_seconds`, `absolute_beats`, `tempo_bpm`, `duration_seconds`, and related JSON numeric fields.

## Sample Rate And Bit Depth

The script detects sample rates from Ableton `SampleRef` metadata. If every detected sample rate agrees, that rate is used for `sample_index`.

If multiple sample rates are found, the script reports `sample rate` as `not detected` for the global calculation unless you choose one explicitly:

```bash
python3 src/extract_timeline.py song.als --sample-rate=48000
```

When referenced audio files are reachable on disk, the script also attempts to read sample rate and bit depth from WAV, AIFF, AIFC, and FLAC file headers.

Bit depth is metadata only. It does not change wall-clock timing or sample-index calculation.

## End Beat

By default, the script detects the end of the timeline from locators, tempo events, time signature events, and arrangement clip ends.

Use `--end-beat` to force a specific endpoint:

```bash
python3 src/extract_timeline.py song.als --grid=beats --end-beat=4096
```

This is especially useful when exporting a grid for a region longer or shorter than the detected arrangement content.

## Heading Options

The TSV heading row is included by default.

Use `--no-heading-row` or `--no-header` to omit it:

```bash
python3 src/extract_timeline.py song.als --no-heading-row --output=song.timeline.tsv
python3 src/extract_timeline.py song.als --no-header --output=song.timeline.tsv
```

## Combined Examples

Write a full TSV plus pretty JSON:

```bash
python3 src/extract_timeline.py song.als --output=song.timeline.tsv --json=song.timeline.json
```

Write a compact JSON timeline for scripting:

```bash
python3 src/extract_timeline.py song.als --json=song.timeline.json --json-format=compact
```

Write a bar grid with three decimal places:

```bash
python3 src/extract_timeline.py song.als --grid=bars --precision=3 --output=song.timeline-bars.tsv
```

Write a beat grid with sample indexes at 48 kHz:

```bash
python3 src/extract_timeline.py song.als --grid=beats --sample-rate=48000 --output=song.timeline-beats.tsv
```

Write a musical map without clip boundaries:

```bash
python3 src/extract_timeline.py song.als --event-types=tempo,tempo_ramp,time_signature,key,locator --output=song.timeline-core.tsv
```

Write a lightweight locator timeline without normalized locator offsets:

```bash
python3 src/extract_timeline.py song.als --event-types=locator --columns=wall_time,wall_seconds,sample_index,name,event_id,absolute_beats --output=song.locator-timeline.tsv
```

Write only tempo and time signature changes:

```bash
python3 src/extract_timeline.py song.als --event-types=tempo,tempo_ramp,time_signature --columns=wall_time,event_type,absolute_beats,value,duration_seconds,details --output=song.tempo-signature.tsv
```

## Terminal Output

The script prints a short status report after it runs. Successful output includes:

- The input session path.
- The number of exported events.
- The selected grid mode.
- The sample rate used for sample-index calculation, if available.
- One `output` row for each written file.
- The elapsed processing time, shown to three decimal places.

Reports are headed `Timeline Extraction Results`. Errors use the same compact reporting format for issues such as missing files, unreadable files, invalid option values, malformed XML, or invalid tempo data.

Successful runs exit with status code `0`. Runtime errors exit with status code `1`, and command-line argument errors exit with status code `2`.

## Validation Notes

The locator rows produced by Extract Timeline were checked against the known-good `examples/validation/RYM_2026-03_locators_metadata.tsv` fixture. The locator IDs, labels, absolute beats, and absolute seconds match the validated Extract Locators output.

Example validation command:

```bash
python3 src/extract_timeline.py examples/validation/RYM_2026-03.als --event-types=locator --columns=wall_seconds,name,event_id,absolute_beats --output=/tmp/RYM_2026-03.timeline-locators.tsv
```

## Notes For Maintainers

The parser streams Ableton XML with Python's Expat parser and collects only the data needed by the timeline exporter:

- Main-track tempo automation envelopes identified by Ableton `PointeeId=8`.
- Main-track time signature automation envelopes identified by Ableton `PointeeId=10`.
- Arrangement locators.
- Arrangement audio and MIDI clip starts/ends.
- Session and clip `ScaleInformation` blocks.
- Audio `SampleRef` metadata.

After parsing, tempo events are normalized, integrated into elapsed seconds, and searched with `bisect` when converting arbitrary beat positions to real time. Generated grid rows use the normalized time signature map so bar and beat rows follow time signature changes.

When updating the script, keep this document current with:

- New command-line options.
- Changed output formats.
- New release notes.
- Validation notes.
- Any compatibility or behavior changes.
