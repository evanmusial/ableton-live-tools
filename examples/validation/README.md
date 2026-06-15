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
- `RYM_2026-03_reaper_markers.csv`: Expected REAPER Region/Marker Manager CSV marker output generated with a 27-second offset.
- `RYM_2026-03_locators_metadata.md`: Expected Markdown locator report generated with every metadata column and a 27-second offset.
- `RYM_2026-03_markers.mid`: Expected Standard MIDI marker file generated from the locator absolute beat positions.
- `RYM_2026-03_markers_timing.mid`: Expected Standard MIDI marker file with optional tempo and time-signature timing-map meta events enabled.

DAW MIDI marker-map presets for Logic Pro, Pro Tools, Cubase, and Nuendo are validated by CLI tests that regenerate the files in a temporary directory and check for valid Standard MIDI chunks, DAW-specific track names, and expected locator marker payloads. They are not currently checked in as separate fixture files because they reuse the same marker/timing-map writer as `RYM_2026-03_markers_timing.mid` with a DAW-specific track name.

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

The CSV, Audition marker, WebVTT, CUE, REAPER marker, Markdown, and MIDI files were generated from
`RYM_2026-03.als` with:

```bash
python3 ~/git/ableton-live-tools/src/extract_locators.py "RYM_2026-03.als" --add-offset=27 --columns=all -o /tmp/ableton-live-tools-2026-06-07-dummy.tsv --csv=RYM_2026-03_locators_metadata.csv --audition=RYM_2026-03_audition_markers.csv --webvtt=RYM_2026-03_chapters.vtt --cue=RYM_2026-03_tracks.cue --cue-audio=RYM_2026-03.wav --reaper=RYM_2026-03_reaper_markers.csv --markdown=RYM_2026-03_locators_metadata.md --midi=RYM_2026-03_markers.mid
```

## MIDI Timing Map Output Command

The MIDI timing-map fixture was generated from `RYM_2026-03.als` with:

```bash
python3 ~/git/ableton-live-tools/src/extract_locators.py "RYM_2026-03.als" --add-offset=27 --columns=all -o /tmp/ableton-live-tools-2026-06-07-dummy.tsv --midi=RYM_2026-03_markers_timing.mid --midi-timing-map
```

## Project Manifest Validation

`src/extract_project_manifest.py` is validated semantically against `RYM_2026-03.als` rather than by checking in the full generated report directory.

Current expected counts from this fixture:

- Tracks: `160`
- Audio tracks: `92`
- Group tracks: `68`
- Clips: `742`
- Audio clips: `742`
- Unique sample references: `162`
- Devices/effects/plugins: `161`
- Third-party plugins: `55`
- Ableton native devices: `106`
- Locators: `66`
- Tempo events: `23`
- Time signature events: `1`

## Project Health Validation

`src/check_project_health.py` is validated semantically against `RYM_2026-03.als`. The fixture intentionally does not include the referenced audio files in the repository, so the expected health status includes missing-sample findings.

Current expected health checks from this fixture:

- Unique sample references: `162`
- Missing sample references: `162`
- Overall status with `--fail-on=none`: `critical`

## Semantic Diff Validation

`src/diff_als_semantic.py` is validated against the identical-file case:

```bash
python3 ~/git/ableton-live-tools/src/diff_als_semantic.py "RYM_2026-03.als" "RYM_2026-03.als"
```

Expected result:

- Status: `same`
- Change count: `0`

## Validation Note

For future checks, ignore the first actual track when its title is
`Mysterium - Show Intro`; that entry was added manually.
