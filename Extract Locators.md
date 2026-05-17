# Extract Locators

`src/extract_locators.py` extracts Ableton Live arrangement locators from an `.als` session file and writes timestamped tracklists. It is designed for preparing time and label exports for show notes, livestream descriptions, Mixcloud uploads, and other post-production notes.

The script uses only the Python 3 standard library.

## Current Version

Version: `2026.05.17`

Author: Evan Musial <evan@evan.engineer>

License: Creative Commons Attribution-ShareAlike 4.0 International

This license requires that reusers give credit to the creator. It allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, even for commercial purposes. If others remix, adapt, or build upon the material, they must license the modified material under identical terms.

## Release Notes

### 2026.05.17

- Added optional TSV and JSON export columns for tempo, song position, time signature, absolute seconds, normalized seconds, absolute beats, bar number, time signature section start, Ableton locator ID, and track number.
- Added `--columns`, `--all-columns`, and individual `--include-*` options for choosing locator metadata fields.
- Added `--track-number-offset`, allowing positive track-number offsets and `-1` when the first exported track should be numbered `0`.
- Added JSON export with `--json` / `-j`.
- Added `--json-format=pretty|compact` for human-readable or compact JSON files.
- Added metadata validation exemplars generated from `examples/validation/RYM_2026-03.als`.
- Updated CLI reports to use the `Locator Extraction Results` heading, list every written file as an `output` row, and show elapsed time with three decimal places.
- Documented success and error exit codes for scripting and CI usage.
- Added [docs/locator-export-roadmap.md](docs/locator-export-roadmap.md) as a checklist for future locator export ideas.

### 2026.05.16

- Moved the Python script from the repository root to `src/extract_locators.py`.
- Added this guide-meets-release-notes document at `Extract Locators.md`.
- Simplified `README.md` so it gives a high-level project overview and links here for full Extract Locators documentation.
- Optimized ALS parsing by streaming only the locator and tempo data needed by the tool instead of building the full Ableton XML tree in memory.
- Replaced linear tempo segment lookup with `bisect` over precomputed tempo beat positions.
- Batched TSV and Mixcloud file writes with `writelines`.
- On the `RYM_2026-03.als` test session, elapsed runtime improved from `1.035s` to `0.769s`, about `26%` less elapsed time.
- On the `RYM_2026-03.als` test session, peak memory use improved from about `699 MiB` to about `26.8 MiB`, about `96%` less peak memory.
- Verified the optimized output is byte-identical to the previous implementation for the same command-line options.
- Tested and validated from Python 3.9 through Python 3.14.5.

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

The default TSV and JSON columns are:

```text
time,label
```

Use `--columns` to choose a comma-separated set of columns:

```bash
python3 src/extract_locators.py song.als --columns=time,label,tempo,time_signature --output=locators.tsv
python3 src/extract_locators.py song.als --columns=all --output=locators.tsv
```

You can also append columns to the default `time,label` export with individual flags:

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

JSON uses the same selected columns as TSV. Use `--columns=all` to include every field:

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

Apply a 27-second offset, strip leading key labels, write a TSV without a heading row, and also write a Mixcloud file:

```bash
python3 src/extract_locators.py song.als --add-offset=27 --strip-keys --no-heading-row --output=locators.tsv --mixcloud=mixcloud.txt
```

Write decimal timestamps and custom TSV column labels:

```bash
python3 src/extract_locators.py song.als --precision=2 --time-header=TIME --label-header=LABEL --output=ensemble.tsv
```

## Terminal Output

The script prints a short status report after it runs. Successful output includes:

- The input session path.
- The number of locators processed.
- One `output` row for each written file, including TSV, Mixcloud, and JSON outputs.
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
