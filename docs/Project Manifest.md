# Project Manifest

`src/extract_project_manifest.py` extracts a project-level inventory from an Ableton Live `.als` session file. It is designed for archive checks, handoff notes, remix/session cleanup, dependency review, and spreadsheet-friendly audits of samples, clips, tracks, native devices, third-party plugins, and effects.

The script uses only the Python 3 standard library.

## Current Version

Version: `2026.06.07`

Author: Evan Musial <evan@evan.engineer>

License: Creative Commons Attribution-ShareAlike 4.0 International

This license requires that reusers give credit to the creator. It allows reusers to distribute, remix, adapt, and build upon the material in any medium or format, even for commercial purposes. If others remix, adapt, or build upon the material, they must license the modified material under identical terms.

## Release Notes

### 2026.06.07

- Added the initial `src/extract_project_manifest.py` script.
- Added project inventory output for tracks, clips, samples, devices, Ableton metadata, locators, tempo-event counts, and time-signature-event counts.
- Added sample manifest output with audio paths, relative paths, original file sizes, original CRC values, default sample rates, default durations, usage counts, resolved-path checks, and missing-file status.
- Added plugin/effects manifest output for third-party plugins and Ableton native devices.
- Added plugin/effects views sorted by author/manufacturer and by plugin/effect name.
- Added Markdown, JSON, and TSV output in one report directory.
- Added CLI validation coverage against `examples/validation/RYM_2026-03.als`.

## What It Does

Ableton `.als` files are XML documents, usually gzip-compressed. Project Manifest streams each top-level track subtree, extracts inventory data from that track, clears the subtree, and moves on. This keeps memory behavior much better than building the full uncompressed XML tree while still allowing detailed track-local parsing.

The tool writes one report directory. By default, the directory is named:

```text
<input filename>.project-manifest
```

For `song.als`, that becomes:

```text
song.als.project-manifest
```

## Output Files

By default, the report directory contains:

- `project_inventory.md`: a human-readable summary report.
- `project_manifest.json`: the complete structured manifest.
- `tracks.tsv`: one row per top-level track.
- `clips.tsv`: one row per detected audio or MIDI clip.
- `samples.tsv`: one row per unique audio/sample reference.
- `devices.tsv`: one row per native device, effect, Max for Live device, or third-party plugin.
- `plugins_by_author.tsv`: the same device/plugin rows sorted by manufacturer/author.
- `plugins_by_name.tsv`: the same device/plugin rows sorted by plugin/effect name.

## Usage

Run with defaults:

```bash
python3 src/extract_project_manifest.py song.als
```

Choose the output directory:

```bash
python3 src/extract_project_manifest.py song.als --output-dir=song_manifest
python3 src/extract_project_manifest.py song.als -o song_manifest
```

Write compact JSON:

```bash
python3 src/extract_project_manifest.py song.als --json-format=compact
```

Skip JSON, Markdown, or TSV output:

```bash
python3 src/extract_project_manifest.py song.als --no-json
python3 src/extract_project_manifest.py song.als --no-markdown
python3 src/extract_project_manifest.py song.als --no-tsv
```

## Sample Manifest

`samples.tsv` and the JSON `samples` array include:

- Absolute audio path stored in the ALS, when available.
- Relative audio path stored in the ALS, when available.
- Original file size from Ableton's `FileRef` data.
- Original CRC from Ableton's `FileRef` data.
- Default sample rate from Ableton's `SampleRef` data.
- Default duration in samples from Ableton's `SampleRef` data.
- Usage count across clips.
- Track names and clip names that reference the sample.
- Resolved local path candidate.
- Whether the referenced file exists on disk from this checkout/session location.

## Plugin And Effects Manifest

`devices.tsv`, `plugins_by_author.tsv`, `plugins_by_name.tsv`, and the JSON device/plugin arrays include:

- Track number, track ID, track name, and track type.
- Device position inside the track.
- Ableton device XML tag.
- Display name.
- User name, when the device has one.
- Manufacturer/author, where detectable.
- Format, such as `AU`, `VST`, `VST3`, `Max for Live`, or `Ableton Native`.
- Category, currently `third_party_plugin` or `ableton_native_device`.
- Enabled state, where detectable.
- Placeholder/missing-plugin state, where detectable.
- Preset name, where detectable.
- A short device-chain path.

Ableton native effects are included because they matter for project handoff and reconstruction, not only third-party plugins.

## Project Inventory

The Markdown and JSON summary includes:

- Track counts by type.
- Clip counts by type.
- Freeze clip count.
- Unique sample count.
- Existing and missing sample counts.
- Device count.
- Third-party plugin count.
- Ableton native device count.
- Plugin/effect author count.
- Locator count.
- Tempo-event count.
- Time-signature-event count.

## CLI Reporting

Successful runs print a `Project Manifest Results` report with input path, counts, every written output file, and elapsed time.

Successful runs exit with status code `0`. Runtime/user-data errors exit with status code `1`. Command-line argument errors exit with status code `2`.
