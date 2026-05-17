# Validation Fixtures

These files are canonical examples for future testing and validation of
`src/extract_locators.py`.

## Files

- `RYM_2026-03.als`: Ableton Live session used as the validation input.
- `RYM_2026-03_locators.tsv`: Expected TSV output generated with the standard options, with no high precision and no custom heading names.
- `RYM_2026-03_mixcloud.txt`: Expected Mixcloud output generated with the standard options.
- `RYM_2026-03_locators_highres.tsv`: Expected TSV output generated with high precision, custom headings, and a 27-second offset.
- `RYM_2026-03_mixcloud_highres.txt`: Expected Mixcloud output generated with high precision, custom headings, and a 27-second offset.
- `RYM_2026-03_locators_metadata.tsv`: Expected TSV output generated with every metadata column, including tempo, song position, time signature, absolute seconds, normalized seconds, absolute beats, bar number, time signature section start, locator ID, and track number.
- `RYM_2026-03_locators_metadata.json`: Expected pretty JSON output generated with the same metadata columns.

## High-Resolution Output Command

The `_highres` files were generated with:

```bash
python3 ~/git/ableton-live-tools/src/extract_locators.py "RYM_2026-03.als" --precision=3 -o RYM_2026-03_locators_highres.tsv -m RYM_2026-03_mixcloud_highres.txt --time-header=Time --label-header=Title --add-offset=27
```

## Metadata Output Command

The `_metadata` files were generated from `RYM_2026-03.als` with:

```bash
python3 ~/git/ableton-live-tools/src/extract_locators.py "RYM_2026-03.als" --add-offset=27 --columns=all -o RYM_2026-03_locators_metadata.tsv -j RYM_2026-03_locators_metadata.json --json-format=pretty
```

## Validation Note

For future checks, ignore the first actual track when its title is
`Mysterium - Show Intro`; that entry was added manually.
