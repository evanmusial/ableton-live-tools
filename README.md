# ableton-live-tools
Python scripts for dealing with Ableton Live and its session files.

Please make sure to read the LICENSE file for information about the terms of use of the code.

## Locator Extraction Script

`extract_locators.py` extracts Ableton Live arrangement locators from an `.als` session file and writes timestamped tracklists. It is intended for preparing simple time/label exports for show notes, livestream descriptions, Mixcloud uploads, or other post-production notes.

Version 2026.05 supports:

- Plain XML `.als` files and gzip-compressed `.als` files.
- Tempo changes and linear tempo ramps, so locator timestamps follow the actual session timeline.
- Positive or negative offsets after locator normalization, useful when there is pre-roll or when bar `1.1.1` has moved.
- TSV output with configurable heading labels, or no heading row at all.
- Optional Mixcloud-compatible output.
- Optional stripping of leading musical keys from locator names.

The script uses only the Python 3 standard library.

### Basic Usage

Run the script with an Ableton session path:

```bash
python3 extract_locators.py path/to/song.als
```

If no output file is specified, the script writes `<input filename>.txt` in the current directory. For example, running the command from your Desktop with `song.als` creates `song.als.txt`.

The default TSV output has two columns:

```text
Time    Locator Name
00:00   First Track
01:28   Second Track
```

### Output Files

Use `--output` or `-o` to choose the TSV output path:

```bash
python3 extract_locators.py song.als --output=locators.tsv
python3 extract_locators.py song.als -o locators.tsv
```

Use `--mixcloud` or `-m` to also write a Mixcloud-compatible tracklist:

```bash
python3 extract_locators.py song.als --mixcloud=mixcloud.txt
python3 extract_locators.py song.als -m mixcloud.txt
```

Mixcloud output uses one timestamp and label per line:

```text
00:00 First Track
01:28 Second Track
```

### Timing Options

Use `--add-offset=SECONDS` to shift every locator after normalization. Fractional and negative values are accepted:

```bash
python3 extract_locators.py song.als --add-offset=27
python3 extract_locators.py song.als --add-offset=27.5
python3 extract_locators.py song.als --add-offset=-3.25
```

Use `--precision=DECIMALS` to include decimal seconds in TSV timestamps:

```bash
python3 extract_locators.py song.als --precision=2 --output=locators.tsv
```

With `--precision=0`, timestamps are written as `MM:SS`. With decimal precision, timestamps are written as `MM:SS.sss`.

### Heading Options

The default TSV heading row is:

```text
Time    Locator Name
```

Use `--time-header` and `--label-header` to customize those labels:

```bash
python3 extract_locators.py song.als --time-header=TIME --label-header=LABEL --output=ensemble.tsv
```

Use `--no-heading-row` or `--no-header` to omit the heading row entirely:

```bash
python3 extract_locators.py song.als --no-heading-row --output=locators.tsv
```

### Locator Name Cleanup

Use `--strip-keys` to remove a leading musical key in parentheses from locator names:

```bash
python3 extract_locators.py song.als --strip-keys --output=locators.tsv
```

Examples of stripped prefixes include `(G#)`, `(Gb)`, `(A#m)`, `(F Minor)`, and key names typed with true sharp or flat symbols.

### Combined Example

This command applies a 27-second offset, strips leading key labels, writes a TSV without a heading row, and also writes a Mixcloud file:

```bash
python3 extract_locators.py song.als --add-offset=27 --strip-keys --no-heading-row --output=locators.tsv --mixcloud=mixcloud.txt
```
