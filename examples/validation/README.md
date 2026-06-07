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
- `RYM_2026-03_locators_metadata.csv`: Expected standard comma-separated CSV output generated with the same metadata columns.
- `RYM_2026-03_audition_markers.csv`: Expected Adobe Audition marker import output generated with a 27-second offset. The `.csv` filename extension is intentional for Audition import compatibility, but the file contents are tab-separated marker rows.
- `RYM_2026-03_chapters.vtt`: Expected WebVTT chapter output generated with a 27-second offset.
- `RYM_2026-03_tracks.cue`: Expected CUE sheet output generated with a 27-second offset and `RYM_2026-03.wav` as the referenced audio filename.
- `RYM_2026-03_locators_metadata.md`: Expected Markdown locator report generated with every metadata column and a 27-second offset.
- `RYM_2026-03_markers.mid`: Expected Standard MIDI marker file generated from the locator absolute beat positions.
- `RYM_2026-03_markers_timing.mid`: Expected Standard MIDI marker file with optional tempo and time-signature timing-map meta events enabled.

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

## Interchange Format Output Command

The CSV, Audition marker, WebVTT, CUE, Markdown, and MIDI files were generated from
`RYM_2026-03.als` with:

```bash
python3 ~/git/ableton-live-tools/src/extract_locators.py "RYM_2026-03.als" --add-offset=27 --columns=all -o /tmp/ableton-live-tools-2026-06-02-dummy.tsv --csv=RYM_2026-03_locators_metadata.csv --audition=RYM_2026-03_audition_markers.csv --webvtt=RYM_2026-03_chapters.vtt --cue=RYM_2026-03_tracks.cue --cue-audio=RYM_2026-03.wav --markdown=RYM_2026-03_locators_metadata.md --midi=RYM_2026-03_markers.mid
```

## MIDI Timing Map Output Command

The MIDI timing-map fixture was generated from `RYM_2026-03.als` with:

```bash
python3 ~/git/ableton-live-tools/src/extract_locators.py "RYM_2026-03.als" --add-offset=27 --columns=all -o /tmp/ableton-live-tools-2026-06-07-dummy.tsv --midi=RYM_2026-03_markers_timing.mid --midi-timing-map
```

## Validation Note

For future checks, ignore the first actual track when its title is
`Mysterium - Show Intro`; that entry was added manually.
