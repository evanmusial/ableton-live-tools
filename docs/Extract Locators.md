# Extract Locators

`src/extract_locators.py` extracts Ableton Live arrangement locators from an `.als` session file and writes timestamped tracklists. It is designed for preparing time and label exports for show notes, livestream descriptions, Mixcloud uploads, Adobe Audition marker imports, REAPER marker imports, DAW MIDI marker maps, WebVTT chapters, CUE sheets, Markdown reports, MIDI marker/timing files, and other post-production notes.

The script uses only the Python 3 standard library.

## Current Version

Version: `2026.06.07`

Author: Evan Musial <evan@evan.engineer>

License: Creative Commons Attribution-ShareAlike 4.0 International

This license requires that reusers give credit to the creator. It allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, even for commercial purposes. If others remix, adapt, or build upon the material, they must license the modified material under identical terms.

## Release Notes

### 2026.06.07

- Added optional MIDI timing-map output with `--midi-timing-map`.
- When enabled, the Standard MIDI export now includes tempo and time-signature meta events alongside locator marker meta events.
- Added REAPER marker CSV export with `--reaper`.
- Added Logic Pro, Pro Tools, Cubase, and Nuendo MIDI marker-map presets with `--logic-midi`, `--pro-tools-midi`, `--cubase-midi`, and `--nuendo-midi`.
- DAW marker-map presets write Standard MIDI files that include locator markers plus tempo and time-signature meta events by default.
- Kept the default `--midi` behavior as a marker-only file for compatibility with the `2026.06.02` fixture and existing user workflows.
- Reused the already parsed tempo and time-signature maps for MIDI timing output instead of reading the ALS file a second time.
- Precomputed time-signature section-start positions and changed locator timing context from dictionaries to a compact named tuple.
- Raised the locator parser's streaming XML read chunk size from `1 MiB` to `4 MiB` to reduce parser I/O overhead while preserving streaming behavior.
- Added a validation fixture for `RYM_2026-03_markers_timing.mid`.
- Added a validation fixture for `RYM_2026-03_reaper_markers.csv`.
- Added CLI regression tests for REAPER marker output, MIDI timing-map output, DAW MIDI marker-map presets, and the `--midi-timing-map` / `--midi` argument dependency.
- Against `main` on `RYM_2026-03.als`, the locator metadata TSV + JSON benchmark stayed flat at a `0.687s` median, confirming no speed regression after the expanded export options.

### 2026.06.02

- Added Adobe Audition marker export with `--audition` / `-a`.
- Added standard comma-separated CSV export with `--csv`.
- Added WebVTT chapter export with `--webvtt`.
- Added CUE sheet export with `--cue` and optional `--cue-audio`.
- Added Markdown locator report export with `--markdown`.
- Added Standard MIDI locator marker export with `--midi`.
- Exported Ableton locators as zero-duration Audition `Cue` markers.
- Added fixed Audition marker columns: `Name`, `Start`, `Duration`, `Time Format`, `Type`, and `Description`.
- Documented Audition's practical CSV/TSV quirk: use a `.csv` filename for import, but the marker-file contents are intentionally tab-separated text.
- Documented that MIDI marker placement uses absolute Ableton beat positions rather than normalized text timestamps.
- Added validation fixtures for standard CSV, Audition markers, WebVTT chapters, CUE sheets, Markdown reports, and MIDI marker files generated from the canonical Ableton Live session.
- Added CLI validation tests that regenerate the new export formats and compare them byte-for-byte against the fixtures.
- Confirmed the expanded validation suite passes with eight standard-library `unittest` checks.
- Confirmed benchmark results against `main` show no significant speed deterioration; the expanded all-format locator export ran at a `0.707s` median on the validation fixture.

### 2026.05.31

- Added tag-name fast paths to the XML start and end handlers so unrelated Ableton tags skip deeper parser-state checks.
- Replaced fixed tuple-slice path checks with direct parent/depth checks in the XML parser.
- Added the first standard-library `unittest` CLI validation suite under `tests/`.
- Added `scripts/benchmark_validation.py` for repeatable validation benchmarks.
- Added a root README testing pointer for `python3 -m unittest discover -s tests`.
- On the `RYM_2026-03.als` metadata TSV + JSON benchmark, median elapsed time improved from `0.844s` to `0.691s`, about `18.1%` faster.
- Confirmed high-resolution TSV/Mixcloud and metadata TSV/JSON outputs still match the validation fixtures, allowing only expected JSON metadata normalization for script version and local source path.

### 2026.05.29

- Added [Performance and Output Roadmap.md](<Performance and Output Roadmap.md>) with profiling baselines, optimization candidates, output-format candidates, and validation notes.
- Re-ran the usual validation checks against `examples/validation/RYM_2026-03.als` on Python 3.14.5.
- Confirmed high-resolution TSV and Mixcloud output still match the validation fixtures exactly.
- Confirmed metadata TSV and pretty JSON output still match the validation fixtures exactly.
- Confirmed CLI success and missing-file error paths return script-friendly exit codes.
- Tested with Ableton Live 12.4.1, released May 28, 2026.

### 2026.05.17

- Added optional TSV and JSON export columns for tempo, song position, time signature, absolute seconds, normalized seconds, absolute beats, bar number, time signature section start, Ableton locator ID, and track number.
- Added `--columns`, `--all-columns`, and individual `--include-*` options for choosing locator metadata fields.
- Added `--track-number-offset`, allowing positive track-number offsets and `-1` when the first exported track should be numbered `0`.
- Added JSON export with `--json` / `-j`.
- Added `--json-format=pretty|compact` for human-readable or compact JSON files.
- Added metadata validation exemplars generated from `examples/validation/RYM_2026-03.als`.
- Updated CLI reports to use the `Locator Extraction Results` heading, list every written file as an `output` row, and show elapsed time with three decimal places.
- Documented success and error exit codes for scripting and CI usage.
- Tested and validated from Python 3.9 through Python 3.14.5.
- Tested with Ableton Live 12.4 (`2026-04-24_d85a94ab5e`) on macOS.
- Tested operating-system and CPU combinations:
  - macOS Tahoe 26.5 (Apple Silicon: M3 Max)
  - macOS Sequoia 15.7.7 (Intel Core i9-9980HK)
  - Ubuntu 22.04.5 LTS (Intel Xeon E5-1620)
  - Ubuntu 24.04 LTS (Dual Intel Xeon E5-2680 v3)
- Added [locator-export-roadmap.md](locator-export-roadmap.md) as a checklist for future locator export ideas.

### 2026.05.16

- Moved the Python script from the repository root to `src/extract_locators.py`.
- Added this guide-meets-release-notes document at `docs/Extract Locators.md`.
- Simplified `README.md` so it gives a high-level project overview and links here for full Extract Locators documentation.
- Optimized ALS parsing by streaming only the locator and tempo data needed by the tool instead of building the full Ableton XML tree in memory.
- Replaced linear tempo segment lookup with `bisect` over precomputed tempo beat positions.
- Batched TSV and Mixcloud file writes with `writelines`.
- On the `RYM_2026-03.als` test session, elapsed runtime improved from `1.035s` to `0.769s`, about `26%` less elapsed time.
- On the `RYM_2026-03.als` test session, peak memory use improved from about `699 MiB` to about `26.8 MiB`, about `96%` less peak memory.
- Verified the optimized output is byte-identical to the previous implementation for the same command-line options.
- Tested and validated from Python 3.9 through Python 3.14.5.
- Tested with Ableton Live 12.4 (`2026-04-24_d85a94ab5e`) on macOS.
- Tested operating-system and CPU combinations:
  - macOS Tahoe 26.5 (Apple Silicon: M3 Max)
  - macOS Sequoia 15.7.7 (Intel Core i9-9980HK)
  - Ubuntu 22.04.5 LTS (Intel Xeon E5-1620)
  - Ubuntu 24.04 LTS (Dual Intel Xeon E5-2680 v3)

### 2026.05

- Added support for pre-roll offsets, including session data that extends before `1.1.1` or projects where `1.1.1` has been moved.
- Added support for tempo changes and linear tempo ramps so locator timestamps are calculated against the actual session timeline.
- Added TSV output with configurable heading labels.
- Added `--no-heading-row` and `--no-header` to omit TSV headings entirely.
- Added optional Mixcloud-compatible output.
- Added optional stripping of leading musical key labels from locator names.
- Added support for both plain XML `.als` files and gzip-compressed `.als` files.

## What It Does

Ableton `.als` files are XML documents, often gzip-compressed. Extract Locators reads the session, finds arrangement locators, calculates their real elapsed time, and exports timestamped labels.

Timing is calculated with awareness of:

- Tempo automation events.
- Linear tempo ramps.
- Locator normalization, so the earliest extracted locator starts at `00:00` before any user offset is applied.
- User-specified positive or negative offsets.

## Basic Usage

Run the script from the repository root with an Ableton session path:

```bash
python3 src/extract_locators.py path/to/song.als
```

If no output file is specified, the script writes `<input filename>.txt` in the current directory. For example, running the command with `song.als` creates `song.als.txt`.

## TSV Output

The default TSV output has two columns:

```text
Time    Locator Name
00:00   First Track
01:28   Second Track
```

Use `--output` or `-o` to choose the TSV output path:

```bash
python3 src/extract_locators.py song.als --output=locators.tsv
python3 src/extract_locators.py song.als -o locators.tsv
```

## CSV Output

Use `--csv` to also write a normal comma-separated CSV file:

```bash
python3 src/extract_locators.py song.als --csv=locators.csv
```

CSV output mirrors TSV column selection, precision, custom heading labels, and `--no-heading-row` behavior:

```bash
python3 src/extract_locators.py song.als --columns=all --csv=locators_metadata.csv
python3 src/extract_locators.py song.als --time-header=Start --label-header=Title --csv=locators.csv
python3 src/extract_locators.py song.als --no-heading-row --csv=locators.csv
```

This is ordinary comma-separated CSV for spreadsheets and scripting. It is separate from Adobe Audition marker export, which commonly uses a `.csv` filename but intentionally contains tab-separated marker rows.

## Mixcloud Output

Use `--mixcloud` or `-m` to also write a Mixcloud-compatible timestamped tracklist:

```bash
python3 src/extract_locators.py song.als --mixcloud=mixcloud.txt
python3 src/extract_locators.py song.als -m mixcloud.txt
```

Mixcloud output uses one timestamp and label per line:

```text
00:00 First Track
01:28 Second Track
```

## Adobe Audition Marker Output

Use `--audition` or `-a` to also write an Adobe Audition marker import file:

```bash
python3 src/extract_locators.py song.als --audition=audition_markers.csv
python3 src/extract_locators.py song.als -a audition_markers.csv
```

The recommended filename extension is `.csv`, because that is what Audition's marker-import workflow commonly expects. The contents are intentionally tab-separated marker rows, not comma-separated CSV. This CSV filename / TSV contents mismatch is an Audition compatibility quirk, not a typo.

Audition marker output uses these columns:

```text
Name    Start    Duration    Time Format    Type    Description
```

Ableton locators are exported as zero-duration `Cue` markers:

```text
Name    Start       Duration   Time Format   Type   Description
Intro   0:00.000    0:00.000   decimal       Cue
Break   1:30.000    0:00.000   decimal       Cue
```

Audition marker output uses millisecond precision regardless of the TSV `--precision` setting, because Audition marker imports expect decimal marker times.

## WebVTT Chapter Output

Use `--webvtt` to write locator rows as WebVTT chapter cues:

```bash
python3 src/extract_locators.py song.als --webvtt=chapters.vtt
```

WebVTT output starts each cue at a locator and ends it at the next locator:

```text
WEBVTT

00:00:27.000 --> 00:01:40.125
First Track
```

The final cue ends one second after the final locator because Extract Locators does not know the rendered media duration. If a hosting platform requires the final cue to run to the exact media end, adjust that final end time after rendering.

## CUE Sheet Output

Use `--cue` to write locator rows as CUE sheet track indexes:

```bash
python3 src/extract_locators.py song.als --cue=tracks.cue
```

CUE output uses the standard `MM:SS:FF` index format, where `FF` is a 75-frames-per-second CD frame count:

```text
TITLE "song"
FILE "song.wav" WAVE
  TRACK 01 AUDIO
    TITLE "First Track"
    INDEX 01 00:27:00
```

By default, the CUE sheet `FILE` line uses the input session stem with a `.wav` suffix. Use `--cue-audio` when the rendered audio filename is known:

```bash
python3 src/extract_locators.py song.als --cue=tracks.cue --cue-audio=render.wav
```

## Markdown Output

Use `--markdown` to write a human-readable locator report:

```bash
python3 src/extract_locators.py song.als --columns=all --markdown=locators.md
```

Markdown output uses the same selected columns as TSV, CSV, and JSON. It always includes a table heading row, because the file is meant to be readable in documentation, GitHub pull requests, release notes, and review comments.

Example:

```markdown
# Locator Export

- Source: `song.als`
- Locators: `2`
- Generated by: `extract_locators.py`

| Time | Locator Name |
| --- | --- |
| 00:00 | First Track |
| 01:28 | Second Track |
```

## REAPER Marker CSV Output

Use `--reaper` to write locator rows as REAPER Region/Marker Manager CSV markers:

```bash
python3 src/extract_locators.py song.als --reaper=markers.csv
```

The output uses the CSV columns REAPER exports for markers and regions:

```text
#,Name,Start,End,Length
M1,First Track,0:00.000,,
M2,Second Track,1:28.000,,
```

Locator rows are point markers, not regions, so the `End` and `Length` columns are intentionally blank. REAPER marker timestamps are normalized and offset like TSV, Mixcloud, CSV, Audition marker, WebVTT, CUE, and Markdown output.

## MIDI Marker Output

Use `--midi` to write a Standard MIDI file containing locator marker meta events:

```bash
python3 src/extract_locators.py song.als --midi=markers.mid
```

MIDI output stores each locator as a MIDI marker meta event in a single-track Standard MIDI file. Marker placement uses the locator's absolute Ableton beat position converted to MIDI ticks, not the normalized/output text timestamp. That means `--add-offset` shifts text-oriented exports such as TSV, Mixcloud, CSV, REAPER marker CSV, WebVTT, CUE, and Markdown, but it does not shift MIDI beat positions.

Use `--midi-timing-map` with `--midi` to add tempo and time-signature meta events to the same Standard MIDI file:

```bash
python3 src/extract_locators.py song.als --midi=markers.mid --midi-timing-map
```

The default `--midi` output remains marker-only. The timing-map option is explicit because some workflows only want locator markers and do not want an imported tempo/signature map to affect a DAW session.

Standard MIDI represents tempo with discrete tempo meta events. Ableton linear tempo ramps are exported as their tempo automation points rather than as mathematically continuous ramp curves, because Standard MIDI has no native continuous-ramp meta event.

## DAW MIDI Marker-Map Presets

Use the DAW-named MIDI options when you want a clearly labeled marker-map source file for another DAW:

```bash
python3 src/extract_locators.py song.als --logic-midi=logic_markers.mid
python3 src/extract_locators.py song.als --pro-tools-midi=pro_tools_markers.mid
python3 src/extract_locators.py song.als --cubase-midi=cubase_markers.mid
python3 src/extract_locators.py song.als --nuendo-midi=nuendo_markers.mid
```

These are Standard MIDI files, not proprietary Logic, Pro Tools, Cubase, or Nuendo project files. They use the same marker meta events as `--midi`, and they include tempo and time-signature meta events automatically so markers can follow Ableton's musical timeline in DAWs that read MIDI marker maps.

DAW import behavior varies. Some DAWs import MIDI markers only when the existing marker or memory-location list is empty, and importing a MIDI timing map may affect the receiving session's tempo or meter data. Review the DAW's import options before applying these files to an existing production session.

## Timing Options

Use `--add-offset=SECONDS` to shift every locator after normalization. Fractional and negative values are accepted:

```bash
python3 src/extract_locators.py song.als --add-offset=27
python3 src/extract_locators.py song.als --add-offset=27.5
python3 src/extract_locators.py song.als --add-offset=-3.25
```

Use `--precision=DECIMALS` to include decimal seconds in TSV timestamps:

```bash
python3 src/extract_locators.py song.als --precision=2 --output=locators.tsv
```

With `--precision=0`, timestamps are written as `MM:SS`. With decimal precision, timestamps are written as `MM:SS.sss`.

Mixcloud output always uses whole-second timestamps.

## Metadata Columns

The default TSV, CSV, Markdown, and JSON columns are:

```text
time,label
```

Use `--columns` to choose a comma-separated set of columns:

```bash
python3 src/extract_locators.py song.als --columns=time,label,tempo,time_signature --output=locators.tsv
python3 src/extract_locators.py song.als --columns=all --output=locators.tsv
```

You can also append columns to the default `time,label` TSV, CSV, Markdown, and JSON export with individual flags:

```bash
python3 src/extract_locators.py song.als --include-tempo --include-song-position --include-time-signature --output=locators.tsv
```

Available columns are:

- `time`: the exported timestamp after normalization and user offset.
- `label`: the locator name.
- `tempo`: the current tempo in BPM at the locator.
- `song_position`: the current `bar.beat.sixteenth` position.
- `time_signature`: the current time signature.
- `absolute_seconds`: elapsed seconds from the beginning of the session.
- `normalized_seconds`: seconds after earliest-locator normalization and before user offset.
- `absolute_beats`: the raw Ableton beat position.
- `bar_number`: the current bar number.
- `time_signature_section_start`: the song position where the current time signature began.
- `locator_id`: the Ableton locator ID.
- `track_number`: sequential track number after sorting locators by time.

Use `--track-number-offset` when exporting `track_number`:

```bash
python3 src/extract_locators.py song.als --include-track-number --track-number-offset=4 --output=locators.tsv
```

With `--track-number-offset=4`, the first exported locator is numbered `5`. The only accepted negative offset is `-1`, which numbers the first exported locator `0`.

## JSON Output

Use `--json` or `-j` to write a JSON file in addition to the TSV output:

```bash
python3 src/extract_locators.py song.als --json=locators.json
python3 src/extract_locators.py song.als -j locators.json
```

JSON uses the same selected columns as TSV, standard CSV, and Markdown. Use `--columns=all` to include every field:

```bash
python3 src/extract_locators.py song.als --columns=all --json=locators.json
```

Human-readable JSON is the default:

```bash
python3 src/extract_locators.py song.als --json=locators.json --json-format=pretty
```

Use compact JSON when file size matters:

```bash
python3 src/extract_locators.py song.als --json=locators.json --json-format=compact
```

## Heading Options

The default TSV heading row is:

```text
Time    Locator Name
```

Use `--time-header` and `--label-header` to customize those labels:

```bash
python3 src/extract_locators.py song.als --time-header=TIME --label-header=LABEL --output=ensemble.tsv
```

Use `--no-heading-row` or `--no-header` to omit the heading row entirely:

```bash
python3 src/extract_locators.py song.als --no-heading-row --output=locators.tsv
python3 src/extract_locators.py song.als --no-header --output=locators.tsv
```

`--no-heading-row` cannot be combined with `--time-header` or `--label-header`.

## Locator Name Cleanup

Use `--strip-keys` to remove a leading musical key in parentheses from locator names:

```bash
python3 src/extract_locators.py song.als --strip-keys --output=locators.tsv
```

Examples of stripped prefixes include:

- `(G#)`
- `(Gb)`
- `(A#m)`
- `(F Minor)`
- `(C Major)`

Sharp and flat symbols are also supported when they appear in the locator name.

## Combined Examples

Apply a 27-second offset, strip leading key labels, write a TSV without a heading row, and also write Mixcloud, CSV, Audition marker, WebVTT, CUE, Markdown, REAPER marker, and MIDI files:

```bash
python3 src/extract_locators.py song.als --add-offset=27 --strip-keys --no-heading-row --output=locators.tsv --mixcloud=mixcloud.txt --csv=locators.csv --audition=audition_markers.csv --webvtt=chapters.vtt --cue=tracks.cue --markdown=locators.md --reaper=markers.csv --midi=markers.mid
```

Write DAW-named Standard MIDI marker maps for import testing:

```bash
python3 src/extract_locators.py song.als --logic-midi=logic_markers.mid --pro-tools-midi=pro_tools_markers.mid --cubase-midi=cubase_markers.mid --nuendo-midi=nuendo_markers.mid
```

Write decimal timestamps and custom TSV column labels:

```bash
python3 src/extract_locators.py song.als --precision=2 --time-header=TIME --label-header=LABEL --output=ensemble.tsv
```

## Terminal Output

The script prints a short status report after it runs. Successful output includes:

- The input session path.
- The number of locators processed.
- One `output` row for each written file, including TSV, CSV, Mixcloud, Audition marker, REAPER marker CSV, DAW MIDI marker-map preset, WebVTT, CUE, Markdown, MIDI, and JSON outputs.
- The elapsed processing time, shown to three decimal places.

Reports are headed `Locator Extraction Results`. Errors use the same compact reporting format for issues such as missing files, unreadable files, invalid option combinations, malformed XML, or invalid tempo data.

Successful runs exit with status code `0`. Runtime errors exit with status code `1`, and command-line argument errors exit with status code `2`.

## Notes For Maintainers

The current parser streams Ableton XML with Python's Expat parser and collects only the data needed for locator extraction:

- Tempo automation envelopes identified by Ableton `PointeeId=8`.
- Time signature automation envelopes identified by Ableton `PointeeId=10`.
- Arrangement `Locator` elements.

After parsing, tempo events are sorted, integrated into elapsed seconds, and searched with `bisect` when converting locator beat positions to real time. This keeps the script fast on large `.als` files while preserving the standard-library-only design.

When updating the script, keep this document current with:

- New command-line options.
- Changed output formats.
- New release notes.
- Any compatibility or behavior changes.
