# Extract Locators

`src/extract_locators.py` extracts Ableton Live arrangement locators from an `.als` session file and writes timestamped tracklists. It is designed for preparing time and label exports for show notes, livestream descriptions, Mixcloud uploads, and other post-production notes.

The script uses only the Python 3 standard library.

## Current Version

Version: `2026.05`

Author: Evan Musial <evan@evan.engineer>

License: Creative Commons Attribution-ShareAlike 4.0 International

This license requires that reusers give credit to the creator. It allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, even for commercial purposes. If others remix, adapt, or build upon the material, they must license the modified material under identical terms.

## Release Notes

### 2026.05

- Added support for pre-roll offsets, including session data that extends before `1.1.1` or projects where `1.1.1` has been moved.
- Added support for tempo changes and linear tempo ramps so locator timestamps are calculated against the actual session timeline.
- Added TSV output with configurable heading labels.
- Added `--no-heading-row` and `--no-header` to omit TSV headings entirely.
- Added optional Mixcloud-compatible output.
- Added optional stripping of leading musical key labels from locator names.
- Added support for both plain XML `.als` files and gzip-compressed `.als` files.
- Optimized ALS parsing by streaming only the locator and tempo data needed by the tool instead of building the full Ableton XML tree in memory.

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
- The output file path.
- The Mixcloud file path, when requested.
- The elapsed processing time.

Errors use the same compact reporting format for issues such as missing files, unreadable files, invalid option combinations, malformed XML, or invalid tempo data.

## Notes For Maintainers

The current parser streams Ableton XML with Python's Expat parser and collects only the data needed for locator extraction:

- Tempo automation envelopes identified by Ableton `PointeeId=8`.
- Arrangement `Locator` elements.

After parsing, tempo events are sorted, integrated into elapsed seconds, and searched with `bisect` when converting locator beat positions to real time. This keeps the script fast on large `.als` files while preserving the standard-library-only design.

When updating the script, keep this document current with:

- New command-line options.
- Changed output formats.
- New release notes.
- Any compatibility or behavior changes.
