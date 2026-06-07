#!/usr/bin/env python3

"""
extract_locators.py
Version: 2026.06.07

Author: Evan Musial <evan@evan.engineer>
License: Creative Commons Attribution-ShareAlike 4.0 International

License meaning:
  - This license requires that reusers give credit to the creator.
  - It allows reusers to distribute, remix, adapt, and build upon the material
    in any medium or format, even for commercial purposes.
  - If others remix, adapt, or build upon the material, they must license the
    modified material under identical terms.

Version 2026.06.07 notes:
  - Added optional MIDI timing-map output with --midi-timing-map.
  - When enabled, the Standard MIDI export includes tempo and time-signature
    meta events alongside locator marker meta events.
  - Kept the default --midi behavior as a marker-only file for compatibility.
  - Reuses the already parsed tempo and time-signature maps for MIDI timing
    output instead of reading the ALS file a second time.
  - Precomputes time-signature section positions and uses a compact timing
    context object for a small locator-export performance improvement.
  - Raises the streaming XML read chunk size from 1 MiB to 4 MiB to reduce
    parser I/O overhead while keeping memory use low.
  - Added a validation fixture and CLI regression test for MIDI timing-map
    output.

Version 2026.06.02 notes:
  - Added Adobe Audition marker export with --audition / -a.
  - Added standard comma-separated CSV export with --csv.
  - Added WebVTT chapter export with --webvtt.
  - Added CUE sheet export with --cue and optional --cue-audio.
  - Added Markdown locator report export with --markdown.
  - Added Standard MIDI locator marker export with --midi.
  - Writes Audition marker import files with Name, Start, Duration,
    Time Format, Type, and Description columns.
  - Uses tab-separated marker rows, matching Audition's practical marker
    import/export format even when the file is saved with a .csv extension.
  - Exports Ableton locators as zero-duration Audition Cue markers.
  - Added validation fixtures for CSV, WebVTT, CUE, Markdown, MIDI, and
    Audition marker output.

Version 2026.05.31 notes:
  - Added tag-name fast paths to the XML start and end handlers so unrelated
    Ableton tags skip deeper parser-state checks.
  - Replaced fixed tuple-slice path checks with direct parent/depth checks.
  - Added standard-library unittest CLI validation under tests/.
  - Added scripts/benchmark_validation.py for repeatable validation benchmarks.
  - On the RYM_2026-03.als metadata TSV + JSON benchmark, median elapsed time
    improved from 0.844s to 0.691s, about 18.1% faster.
  - Confirmed fixture-compatible high-resolution TSV/Mixcloud and metadata
    TSV/JSON output.

Version 2026.05.29 notes:
  - Added docs/Performance and Output Roadmap.md with profiling baselines,
    optimization candidates, output-format candidates, and validation notes.
  - Re-ran the usual validation checks against examples/validation/RYM_2026-03.als
    on Python 3.14.5.
  - Confirmed high-resolution TSV/Mixcloud and metadata TSV/JSON outputs still
    match the validation fixtures exactly.
  - Confirmed CLI success and missing-file error paths return script-friendly
    exit codes.
  - Tested with Ableton Live 12.4.1, released May 28, 2026.

Version 2026.05.17 notes:
  - Added optional TSV/JSON columns for tempo, song position, time signature,
    absolute seconds, normalized seconds, absolute beats, bar number, time
    signature section start, locator ID, and track number.
  - Added JSON export with compact and human-readable formatting options.
  - Added metadata validation exemplars under examples/validation.
  - Updated CLI reporting with the "Locator Extraction Results" title,
    repeated "output" rows for written files, three-decimal elapsed time, and
    predictable exit codes for success and error handling.
  - Tested and validated from Python 3.9 through Python 3.14.5.
  - Tested with Ableton Live 12.4 (2026-04-24_d85a94ab5e) on macOS.
  - Tested operating-system and CPU combinations:
      - macOS Tahoe 26.5 (Apple Silicon: M3 Max)
      - macOS Sequoia 15.7.7 (Intel Core i9-9980HK)
      - Ubuntu 22.04.5 LTS (Intel Xeon E5-1620)
      - Ubuntu 24.04 LTS (Dual Intel Xeon E5-2680 v3)
  - Added a future export-field checklist in docs/locator-export-roadmap.md.

Version 2026.05.16 notes:
  - Optimized ALS parsing to run about 26% faster on the RYM_2026-03.als test session.
  - Reduced peak memory use by about 96% on the RYM_2026-03.als test session.
  - Moved the script into src/ and moved the long-form guide into Extract Locators.md.
  - Tested and validated from Python 3.9 through Python 3.14.5.
  - Tested with Ableton Live 12.4 (2026-04-24_d85a94ab5e) on macOS.
  - Tested operating-system and CPU combinations:
      - macOS Tahoe 26.5 (Apple Silicon: M3 Max)
      - macOS Sequoia 15.7.7 (Intel Core i9-9980HK)
      - Ubuntu 22.04.5 LTS (Intel Xeon E5-1620)
      - Ubuntu 24.04 LTS (Dual Intel Xeon E5-2680 v3)

Version 2026.05 notes:
  - Support for pre-roll offset (data extending before 1.1.1 or if 1.1.1 has been moved)
  - Support for tempo changes and ramps: the locator's time will be calculated correctly.

Extract Ableton Live locator markers from an .als file and write them to a TSV.

Timing note:
  - Locator times are calculated against Ableton tempo changes and linear tempo
    ramps, so exported timestamps follow the actual session timeline.
  - User offsets are applied after locator normalization, which keeps offset
    behavior predictable even when a set begins somewhere after bar 1.

Features:
  - Handles both plain XML .als files and gzip-compressed .als files.
  - Reads tempo automation, including linear tempo ramps.
  - Normalizes locator times so the earliest locator starts at 00:00 by default.
  - Can add a positive or negative time offset to every locator.
  - Can output timestamps with configurable decimal precision.
  - Can strip leading musical keys from locator names.
  - Can write a Mixcloud-compatible timestamped tracklist.
  - Can write a standard comma-separated CSV file for spreadsheet workflows.
  - Can write an Adobe Audition marker import file.
  - Can write WebVTT chapter cues.
  - Can write CUE sheets for locator-based track indexes.
  - Can write Markdown locator reports.
  - Can write Standard MIDI files with locator marker meta events.
  - Can optionally add tempo and time-signature MIDI meta events to Standard
    MIDI exports.
  - Can write compact or human-readable JSON.
  - Can customize or omit the TSV heading row.
  - Can add optional locator-position metadata columns.
  - Reports success and error status with stable CLI exit codes.
  - Writes tab-separated output with default columns:
      Time    Locator Name

Arguments:
  als_path
      Path to the Ableton .als file.

      Example:
        python3 src/extract_locators.py path/to/song.als

  --add-offset=SECONDS
      Add SECONDS to every locator after normalization.
      Fractional and negative values are accepted.

      Examples:
        python3 src/extract_locators.py song.als --add-offset=27
        python3 src/extract_locators.py song.als --add-offset=27.5
        python3 src/extract_locators.py song.als --add-offset=-3.25

  --precision=DECIMALS
      Number of decimal places to show in the seconds portion of each timestamp.
      Default: 0

      Examples:
        python3 src/extract_locators.py song.als --precision=0
        python3 src/extract_locators.py song.als --precision=1
        python3 src/extract_locators.py song.als --precision=3

      Example output with --precision=0:
        01:28

      Example output with --precision=2:
        01:28.42

  --strip-keys
      Remove a leading musical key in parentheses from each locator name.

      Examples:
        (G#) Blue Man & Blaze U & LUPEX - All Night Long
        becomes:
        Blue Man & Blaze U & LUPEX - All Night Long

        (G♯) Blue Man & Blaze U & LUPEX - All Night Long
        becomes:
        Blue Man & Blaze U & LUPEX - All Night Long

        (A) Jack Trades & Kadiri - Can You Be
        becomes:
        Jack Trades & Kadiri - Can You Be

      Example:
        python3 src/extract_locators.py song.als --strip-keys

  --output=PATH
  -o PATH
      Output TSV path.
      Default: <input filename>.txt in the current directory.

      Examples:
        python3 src/extract_locators.py song.als --output=locators.tsv
        python3 src/extract_locators.py song.als --output=adjusted_locators.tsv
        python3 src/extract_locators.py song.als -o locators.tsv

  --time-header=LABEL
      Use LABEL as the first TSV column heading.
      Default: Time

      Example:
        python3 src/extract_locators.py song.als --time-header=Start

  --label-header=LABEL
      Use LABEL as the second TSV column heading.
      Default: Locator Name

      Example:
        python3 src/extract_locators.py song.als --label-header=Title

  --no-heading-row
  --no-header
      Omit the TSV heading row entirely.

      Example:
        python3 src/extract_locators.py song.als --no-heading-row

  --columns=LIST
      Select comma-separated TSV/JSON columns.
      Default: time,label
      Use all to include every available column.

      Available columns:
        time
        label
        tempo
        song_position
        time_signature
        absolute_seconds
        normalized_seconds
        absolute_beats
        bar_number
        time_signature_section_start
        locator_id
        track_number

      Examples:
        python3 src/extract_locators.py song.als --columns=time,label,tempo
        python3 src/extract_locators.py song.als --columns=all

  --all-columns
      Include every available TSV/JSON column.

      Example:
        python3 src/extract_locators.py song.als --all-columns

  --include-tempo
      Add the current tempo in BPM.

  --include-song-position
      Add the current bar.beat.sixteenth position.

  --include-time-signature
      Add the current time signature.

  --include-absolute-seconds
      Add elapsed seconds from the beginning of the session.

  --include-normalized-seconds
      Add seconds after earliest-locator normalization and before user offset.

  --include-absolute-beats
      Add the raw Ableton beat position.

  --include-bar-number
      Add the current bar number.

  --include-time-signature-section-start
      Add the song position where the current time signature began.

  --include-locator-id
      Add the Ableton locator ID.

  --include-track-number
      Add a sequential track number after sorting locators by time.

      Example:
        python3 src/extract_locators.py song.als --include-tempo --include-song-position --include-time-signature

  --track-number-offset=NUMBER
      Offset exported track numbers. Use 4 to start at 5, or -1 to start at 0.

      Example:
        python3 src/extract_locators.py song.als --include-track-number --track-number-offset=4

  --mixcloud=PATH
  -m PATH
      Also write a Mixcloud-compatible timestamped tracklist.

      Format:
        MM:SS Locator Name

      Examples:
        python3 src/extract_locators.py song.als --mixcloud=mixcloud.txt
        python3 src/extract_locators.py song.als -m mixcloud.txt

  --csv=PATH
      Also write a standard comma-separated CSV file.

      CSV uses the same selected columns, precision, heading labels, and
      heading-row behavior as TSV. This is a normal comma CSV, unlike the
      Adobe Audition marker export, which intentionally uses tab-separated
      marker rows inside a .csv-named file.

      Example:
        python3 src/extract_locators.py song.als --csv=locators.csv

  --audition=PATH
  -a PATH
      Also write an Adobe Audition marker import file.

      Audition marker files are commonly saved with a .csv extension, but the
      marker table itself is tab-separated text. That CSV filename / TSV
      contents mismatch is intentional for Audition compatibility.

      Columns:
        Name    Start    Duration    Time Format    Type    Description

      Ableton locators are exported as zero-duration Cue markers.

      Examples:
        python3 src/extract_locators.py song.als --audition=audition_markers.csv
        python3 src/extract_locators.py song.als -a audition_markers.csv

  --webvtt=PATH
      Also write WebVTT chapter cues.

      Each cue starts at a locator and ends at the next locator. The final cue
      ends one second after the final locator because Extract Locators does not
      know the rendered media duration.

      Example:
        python3 src/extract_locators.py song.als --webvtt=chapters.vtt

  --cue=PATH
      Also write a CUE sheet using each locator as TRACK INDEX 01.

      Example:
        python3 src/extract_locators.py song.als --cue=tracks.cue

  --cue-audio=PATH
      Set the audio filename used by the CUE sheet FILE line.
      Default: <input session stem>.wav

      Example:
        python3 src/extract_locators.py song.als --cue=tracks.cue --cue-audio=render.wav

  --markdown=PATH
      Also write a Markdown locator report.

      Markdown uses the same selected columns as TSV, CSV, and JSON, and always
      includes a table heading row.

      Example:
        python3 src/extract_locators.py song.als --columns=all --markdown=locators.md

  --midi=PATH
      Also write a Standard MIDI file containing locator marker meta events.

      MIDI marker placement uses the locator's absolute Ableton beat position,
      not the normalized/output timestamp. The --add-offset option is meant for
      timestamped text formats and does not shift MIDI beat positions.

      Example:
        python3 src/extract_locators.py song.als --midi=markers.mid

  --midi-timing-map
      Add tempo and time-signature meta events to the Standard MIDI export.
      Requires --midi. Locator markers remain in the same file.

      Standard MIDI represents tempo with discrete tempo meta events. Ableton
      linear tempo ramps are therefore exported as their tempo automation
      points rather than as continuous ramp curves.

      Example:
        python3 src/extract_locators.py song.als --midi=markers.mid --midi-timing-map

  --json=PATH
  -j PATH
      Also write a JSON locator export.

      Examples:
        python3 src/extract_locators.py song.als --json=locators.json
        python3 src/extract_locators.py song.als -j locators.json

  --json-format=pretty|compact
      Choose whether JSON is human-readable or compact.
      Default: pretty

Combined examples:
  python3 src/extract_locators.py song.als --add-offset=27.5 --precision=2 --output=adjusted_locators.tsv
  python3 src/extract_locators.py song.als --time-header=TIME --label-header=LABEL --output=ensemble.tsv
  python3 src/extract_locators.py song.als --no-heading-row --output=locators.tsv
  python3 src/extract_locators.py song.als --add-offset=27 --mixcloud=mixcloud.txt
  python3 src/extract_locators.py song.als --columns=all --csv=locators.csv
  python3 src/extract_locators.py song.als --add-offset=27 --audition=audition_markers.csv
  python3 src/extract_locators.py song.als --webvtt=chapters.vtt
  python3 src/extract_locators.py song.als --cue=tracks.cue --cue-audio=render.wav
  python3 src/extract_locators.py song.als --columns=all --markdown=locators.md
  python3 src/extract_locators.py song.als --midi=markers.mid
  python3 src/extract_locators.py song.als --midi=markers.mid --midi-timing-map
  python3 src/extract_locators.py song.als --include-tempo --include-song-position --include-time-signature --output=locators.tsv
  python3 src/extract_locators.py song.als --columns=all --json=locators.json
  python3 src/extract_locators.py song.als --add-offset=27 --strip-keys --output=locators.tsv --mixcloud=mixcloud.txt --csv=locators.csv --audition=audition_markers.csv --webvtt=chapters.vtt --cue=tracks.cue --markdown=locators.md --midi=markers.mid

CLI reporting:
  - Reports are headed "Locator Extraction Results".
  - Every written file is listed with the label "output".
  - Elapsed processing time is shown with three decimal places.
  - Successful runs exit with status code 0.
  - Runtime/user-data errors exit with status code 1.
  - Command-line argument errors exit with status code 2.
"""

import argparse
import bisect
import csv
from dataclasses import dataclass
import gzip
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from typing import NamedTuple
import xml.parsers.expat as expat
import zlib


SCRIPT_NAME = "extract_locators.py"
SCRIPT_VERSION = "2026.06.07"
REPORT_TITLE = "Locator Extraction Results"
DEFAULT_BPM = 120.0
LOCATOR_XML_READ_CHUNK_SIZE = 4 * 1024 * 1024
TEMPO_AUTOMATION_POINTEE_ID = "8"
TIME_SIGNATURE_AUTOMATION_POINTEE_ID = "10"
DEFAULT_TIME_SIGNATURE_VALUE = 201
TIME_SIGNATURE_DENOMINATORS = (1, 2, 4, 8, 16)

# The XML start handler is called for every element in the uncompressed ALS
# document. Most tags are irrelevant to locator extraction, so this small allow
# list lets the handler skip deeper path checks unless the current tag can
# actually affect exported timing or labels.
LOCATOR_XML_INTERESTING_TAGS = frozenset(
    (
        "AutomationEnvelope",
        "PointeeId",
        "FloatEvent",
        "EnumEvent",
        "Manual",
        "Locator",
        "Name",
        "Time",
    )
)
LOCATOR_XML_INTERESTING_END_TAGS = frozenset(("AutomationEnvelope", "Locator"))

DEFAULT_TIME_HEADER = "Time"
DEFAULT_LABEL_HEADER = "Locator Name"
DEFAULT_TSV_COLUMNS = ("time", "label")
OPTIONAL_TSV_COLUMNS = (
    "tempo",
    "song_position",
    "time_signature",
    "absolute_seconds",
    "normalized_seconds",
    "absolute_beats",
    "bar_number",
    "time_signature_section_start",
    "locator_id",
    "track_number",
)
ALL_TSV_COLUMNS = (*DEFAULT_TSV_COLUMNS, *OPTIONAL_TSV_COLUMNS)
DEFAULT_METADATA_DECIMAL_PLACES = 3
AUDITION_MARKER_HEADERS = (
    "Name",
    "Start",
    "Duration",
    "Time Format",
    "Type",
    "Description",
)
AUDITION_ZERO_DURATION = "0:00.000"
AUDITION_TIME_FORMAT = "decimal"
AUDITION_MARKER_TYPE = "Cue"
WEBVTT_FINAL_CUE_SECONDS = 1.0
CUE_FRAMES_PER_SECOND = 75
CUE_DEFAULT_AUDIO_SUFFIX = ".wav"
MIDI_TICKS_PER_QUARTER_NOTE = 480
MIDI_FORMAT_SINGLE_TRACK = 0
MIDI_TRACK_COUNT = 1
MIDI_MARKER_META_TYPE = 0x06
MIDI_TEMPO_META_TYPE = 0x51
MIDI_TIME_SIGNATURE_META_TYPE = 0x58
MIDI_TRACK_NAME_META_TYPE = 0x03
MIDI_END_OF_TRACK_META_TYPE = 0x2F
MIDI_DEFAULT_CLOCKS_PER_METRONOME_CLICK = 24
MIDI_DEFAULT_32ND_NOTES_PER_QUARTER_NOTE = 8

COLUMN_HEADERS = {
    "time": DEFAULT_TIME_HEADER,
    "label": DEFAULT_LABEL_HEADER,
    "tempo": "Tempo (BPM)",
    "song_position": "Song Position",
    "time_signature": "Time Signature",
    "absolute_seconds": "Absolute Seconds",
    "normalized_seconds": "Normalized Seconds",
    "absolute_beats": "Absolute Beats",
    "bar_number": "Bar Number",
    "time_signature_section_start": "Time Signature Section Start",
    "locator_id": "Locator ID",
    "track_number": "Track Number",
}

COLUMN_ALIASES = {
    "name": "label",
    "locator_name": "label",
    "timestamp": "time",
    "bpm": "tempo",
    "tempo_bpm": "tempo",
    "measure_beat": "song_position",
    "measure_bar_beat": "song_position",
    "measure.bar.beat": "song_position",
    "bar_beat": "song_position",
    "bar.beat": "song_position",
    "bar.beat.sixteenth": "song_position",
    "position": "song_position",
    "time_sig": "time_signature",
    "timesig": "time_signature",
    "signature": "time_signature",
    "beats": "absolute_beats",
    "locator_beat": "absolute_beats",
    "locator_beats": "absolute_beats",
    "bar": "bar_number",
    "time_signature_start": "time_signature_section_start",
    "signature_start": "time_signature_section_start",
    "section_start": "time_signature_section_start",
    "id": "locator_id",
    "track": "track_number",
    "track_no": "track_number",
}

# Ableton locator names often begin with a DJ-friendly musical key token such
# as "(G#)" or "(Amin)". The expression only strips a key when it appears at
# the very start of the locator name, and it accepts ASCII and true musical
# sharp/flat characters.
KEY_PREFIX_RE = re.compile(
    r"""
    ^\s*
    \(
        \s*
        [A-Ga-g]
        (?:\#|♯|b|♭)?
        (?:
            m
            |maj
            |major
            |min
            |minor
        )?
        \s*
    \)
    \s*
    """,
    re.VERBOSE,
)

# xterm-256 foreground colors. Output remains plain text when stdout/stderr is
# not an interactive terminal, when NO_COLOR is set, or when TERM=dumb.
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
FG_BLUE = "\033[38;5;75m"
FG_GREEN = "\033[38;5;114m"
FG_RED = "\033[38;5;203m"
FG_YELLOW = "\033[38;5;179m"
FG_MUTED = "\033[38;5;245m"
FG_VALUE = "\033[38;5;231m"


class LocatorToolError(Exception):
    """A user-facing problem that should be reported without a traceback."""

    def __init__(self, problem, details=None):
        super().__init__(problem)
        self.problem = problem
        self.details = details or []


class LocatorArgumentParser(argparse.ArgumentParser):
    """
    ArgumentParser with the same compact reporting style used by runtime errors.

    argparse normally writes "error: ..." after the usage block. Keeping parse
    failures in the same visual language as file and XML failures makes the
    command-line experience calmer and easier to scan.
    """

    def error(self, message):
        self.print_usage(sys.stderr)
        print_report(
            "error",
            [("problem", message)],
            stream=sys.stderr,
            status_color=FG_RED,
        )
        raise SystemExit(2)


@dataclass(frozen=True)
class LocatorSource:
    """Raw locator data as it appears in the Ableton session file."""

    locator_id: str
    beat: float
    name: str


@dataclass(frozen=True)
class TimeSignatureEvent:
    """A time signature that becomes active at a specific Ableton beat."""

    beat: float
    numerator: int
    denominator: int


class TimeSignatureContext(NamedTuple):
    """Computed musical-position values for one Ableton beat."""

    event: TimeSignatureEvent
    bar_number: int
    displayed_beat: int
    sixteenth: int
    song_position: str
    time_signature: str
    time_signature_section_start: str


@dataclass(frozen=True)
class LocatorExportRow:
    """All computed values that can be written for a single exported locator."""

    output_seconds: float
    name: str
    locator_id: str
    absolute_beats: float
    absolute_seconds: float
    normalized_seconds: float
    tempo_bpm: float
    song_position: str
    time_signature: str
    bar_number: int
    time_signature_section_start: str
    track_number: int


@dataclass(frozen=True)
class LocatorExtractionResult:
    """Locator rows plus the timing map needed by richer export formats."""

    rows: list[LocatorExportRow]
    tempo_events: tuple[tuple[float, float], ...]
    time_signature_events: tuple[TimeSignatureEvent, ...]


def stream_supports_color(stream):
    """Return True when ANSI/xterm-256 color should be emitted to this stream."""
    return (
        hasattr(stream, "isatty")
        and stream.isatty()
        and os.environ.get("NO_COLOR") is None
        and os.environ.get("TERM") != "dumb"
    )


def colorize(text, color, *, stream=sys.stdout, bold=False):
    """Wrap text in ANSI styling when the target stream supports it."""
    if not stream_supports_color(stream):
        return text

    prefix = ANSI_BOLD if bold else ""
    return f"{prefix}{color}{text}{ANSI_RESET}"


def print_report(status, rows, *, stream=sys.stdout, status_color=FG_GREEN):
    """
    Print a compact, aligned status report.

    The same shape is used for success, warning, and error output so users can
    quickly find the status, the affected paths, and the useful counts.
    """
    print(colorize(REPORT_TITLE, FG_BLUE, stream=stream, bold=True), file=stream)
    print_kv("status", colorize(status, status_color, stream=stream), stream=stream)

    for label, value in rows:
        print_kv(label, value, stream=stream)


def print_kv(label, value, *, stream=sys.stdout):
    """Print one indented key/value line with a stable label width."""
    label_text = colorize(f"{label:<10}", FG_MUTED, stream=stream)
    value_text = colorize(str(value), FG_VALUE, stream=stream)
    print(f"  {label_text} {value_text}", file=stream)


def display_path(path):
    """Return an absolute path string suitable for terminal reporting."""
    return str(Path(path).expanduser().resolve(strict=False))


def user_path(raw_path):
    """
    Expand a command-line path relative to the current working directory.

    This keeps all reads and writes predictable even when the command is called
    with a relative path from another directory.
    """
    path = Path(raw_path).expanduser()

    if path.is_absolute():
        return path

    return Path.cwd() / path


def default_output_path(als_path):
    """
    Build the default TSV path from the input session filename.

    If the input is /sets/night_ride.als, the default output becomes
    ./night_ride.als.txt in the current working directory, matching the naming
    requested for this tool.
    """
    return Path.cwd() / f"{als_path.name}.txt"


def format_elapsed(started_at):
    """Return elapsed processing time with stable CLI precision."""
    return f"{time.perf_counter() - started_at:.3f}s"


def strip_key_prefix(locator_name):
    """
    Remove a leading musical key in parentheses from a locator name.

    Examples:
      (B) Artist - Track
      (D#) Artist - Track
      (D♯) Artist - Track
      (Gb) Artist - Track
      (G♭) Artist - Track
      (A#m) Artist - Track
      (F Minor) Artist - Track
      (C Major) Artist - Track
    """
    return KEY_PREFIX_RE.sub("", locator_name, count=1)


def require_positive_bpm(bpm, context):
    """Reject impossible tempo values before they reach logarithmic math."""
    if bpm <= 0:
        raise LocatorToolError(
            "Ableton file contains a tempo value that is zero or negative.",
            [(context, bpm)],
        )


def float_value(raw_value, default, context):
    """
    Read a float-valued XML attribute string with a helpful error if malformed.

    Ableton stores beats, tempo values, and locator positions as XML attributes.
    A missing attribute uses the caller's default; a present but non-numeric
    attribute is treated as a corrupt/unexpected session file.
    """
    if raw_value is None:
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise LocatorToolError(
            "Ableton file contains a numeric value this tool could not read.",
            [(context, raw_value)],
        ) from exc


def int_value(raw_value, default, context):
    """
    Read an integer-like XML attribute string with a helpful error if malformed.

    Ableton stores enum automation values as XML attributes. Values are expected
    to be whole numbers, but reading through float first makes the parser a bit
    more tolerant of files that serialize enum values as "201.0".
    """
    if raw_value is None:
        return default

    try:
        return int(float(raw_value))
    except ValueError as exc:
        raise LocatorToolError(
            "Ableton file contains an integer value this tool could not read.",
            [(context, raw_value)],
        ) from exc


def decode_time_signature_value(encoded_value):
    """
    Decode Ableton's packed main time-signature parameter value.

    Live stores the main time signature as a single enum value. The observed
    range is 0..494, which maps to 99 possible numerators across five supported
    denominators. For example, value 201 decodes to 4/4.
    """
    denominator_index, numerator_index = divmod(encoded_value, 99)

    if denominator_index >= len(TIME_SIGNATURE_DENOMINATORS):
        raise LocatorToolError(
            "Ableton file contains a time signature value this tool could not decode.",
            [("time signature value", encoded_value)],
        )

    return numerator_index + 1, TIME_SIGNATURE_DENOMINATORS[denominator_index]


def format_decimal(value, decimal_places=DEFAULT_METADATA_DECIMAL_PLACES):
    """Format a metadata number compactly while preserving useful precision."""
    rounded = round(value, decimal_places)

    if abs(rounded) < 10 ** (-decimal_places):
        rounded = 0.0

    text = f"{rounded:.{decimal_places}f}"
    return text.rstrip("0").rstrip(".")


def seconds_for_segment(b1, bpm1, b2, bpm2):
    """
    Calculate elapsed seconds between two beat positions.

    Constant tempo can use the direct beats * seconds-per-beat formula. A linear
    ramp integrates 60 / bpm over the beat interval, which produces the
    logarithmic expression below.
    """
    require_positive_bpm(bpm1, "starting bpm")
    require_positive_bpm(bpm2, "ending bpm")

    if b2 <= b1:
        return 0.0

    if abs(bpm2 - bpm1) < 1e-9:
        return (b2 - b1) * (60.0 / bpm1)

    slope = (bpm2 - bpm1) / (b2 - b1)
    return (60.0 / slope) * math.log(bpm2 / bpm1)


def parse_als_locator_data(als_path):
    """
    Extract tempo events and locator beats from an Ableton .als file.

    Ableton .als files are commonly gzip-compressed XML, but some may be plain
    XML. The magic bytes are more reliable than the file extension, so detection
    is based on the first two bytes rather than on the name of the file. XML is
    parsed as a stream so the script does not need to build a full in-memory
    tree for large session files.
    """
    try:
        with als_path.open("rb") as als_file:
            first_two_bytes = als_file.read(2)
            als_file.seek(0)

            if first_two_bytes == b"\x1f\x8b":
                with gzip.GzipFile(fileobj=als_file) as gzipped_file:
                    return parse_als_xml_stream(gzipped_file)

            return parse_als_xml_stream(als_file)
    except FileNotFoundError as exc:
        raise LocatorToolError(
            "Ableton session file was not found.",
            [("path", display_path(als_path))],
        ) from exc
    except PermissionError as exc:
        raise LocatorToolError(
            "Permission denied while reading the Ableton session file.",
            [("path", display_path(als_path))],
        ) from exc
    except (gzip.BadGzipFile, EOFError, zlib.error) as exc:
        raise LocatorToolError(
            "Ableton session file looks gzipped, but it could not be decompressed.",
            [("path", display_path(als_path))],
        ) from exc
    except expat.ExpatError as exc:
        raise LocatorToolError(
            "Ableton session file could not be parsed as XML.",
            [
                ("path", display_path(als_path)),
                ("line", exc.lineno),
                ("column", exc.offset),
                ("detail", exc),
            ],
        ) from exc
    except OSError as exc:
        raise LocatorToolError(
            "Unable to read the Ableton session file.",
            [("path", display_path(als_path)), ("detail", exc)],
        ) from exc


def parse_als_xml_stream(xml_stream, chunk_size=LOCATOR_XML_READ_CHUNK_SIZE):
    """
    Stream-parse Ableton XML and return raw timing data needed by this tool.

    The full Ableton XML can be tens or hundreds of megabytes after gzip
    decompression. Expat lets us collect only tempo automation and arrangement
    locators while discarding everything else as it flows past.
    """
    path = []
    tempo_changes = []
    time_signature_changes = []
    time_signature_manual_value = None
    locator_sources = []
    state = {
        "inside_tempo_candidate": False,
        "tempo_candidate_pointee_id": None,
        "tempo_candidate_float_events": None,
        "tempo_candidate_enum_events": None,
        "inside_locator": False,
        "locator_id": None,
        "locator_name": None,
        "locator_beat": None,
    }

    def parent_is(tag_name):
        return len(path) >= 2 and path[-2] == tag_name

    def parent_chain_is(parent_name, grandparent_name):
        return (
            len(path) >= 3
            and path[-2] == parent_name
            and path[-3] == grandparent_name
        )

    def at_main_time_signature_manual():
        return (
            len(path) >= 5
            and path[-5] == "MainTrack"
            and path[-4] == "DeviceChain"
            and path[-3] == "Mixer"
            and path[-2] == "TimeSignature"
            and path[-1] == "Manual"
        )

    def start_element(name, attrs):
        nonlocal time_signature_manual_value

        path.append(name)

        if name not in LOCATOR_XML_INTERESTING_TAGS:
            return

        if name == "AutomationEnvelope":
            state["inside_tempo_candidate"] = True
            state["tempo_candidate_pointee_id"] = None
            state["tempo_candidate_float_events"] = []
            state["tempo_candidate_enum_events"] = []
            return

        if state["inside_tempo_candidate"]:
            if name == "PointeeId" and parent_is("EnvelopeTarget"):
                state["tempo_candidate_pointee_id"] = attrs.get("Value")
                return

            if name == "FloatEvent" and parent_chain_is("Events", "Automation"):
                state["tempo_candidate_float_events"].append(
                    (
                        attrs.get("Time"),
                        attrs.get("Value"),
                    )
                )
                return

            if name == "EnumEvent" and parent_chain_is("Events", "Automation"):
                state["tempo_candidate_enum_events"].append(
                    (
                        attrs.get("Time"),
                        attrs.get("Value"),
                    )
                )
                return

        if name == "Manual" and at_main_time_signature_manual():
            time_signature_manual_value = int_value(
                attrs.get("Value"),
                DEFAULT_TIME_SIGNATURE_VALUE,
                "manual time signature value",
            )
            return

        if name == "Locator":
            state["inside_locator"] = True
            state["locator_id"] = attrs.get("Id", "")
            state["locator_name"] = None
            state["locator_beat"] = None
            return

        if state["inside_locator"] and name == "Name" and state["locator_name"] is None:
            state["locator_name"] = attrs.get("Value")
            return

        if state["inside_locator"] and name == "Time" and state["locator_beat"] is None:
            state["locator_beat"] = float_value(
                attrs.get("Value"),
                0.0,
                "locator beat",
            )

    def end_element(name):
        if name not in LOCATOR_XML_INTERESTING_END_TAGS:
            path.pop()
            return

        if name == "AutomationEnvelope":
            if state["tempo_candidate_pointee_id"] == TEMPO_AUTOMATION_POINTEE_ID:
                for beat_value, bpm_value in state["tempo_candidate_float_events"]:
                    beat = float_value(beat_value, 0.0, "tempo event beat")
                    bpm = float_value(bpm_value, DEFAULT_BPM, "tempo event bpm")

                    require_positive_bpm(bpm, "tempo event bpm")

                    tempo_changes.append((beat, bpm))
            elif (
                state["tempo_candidate_pointee_id"]
                == TIME_SIGNATURE_AUTOMATION_POINTEE_ID
            ):
                for beat_value, signature_value in state["tempo_candidate_enum_events"]:
                    beat = float_value(beat_value, 0.0, "time signature event beat")
                    encoded_signature = int_value(
                        signature_value,
                        DEFAULT_TIME_SIGNATURE_VALUE,
                        "time signature event value",
                    )
                    numerator, denominator = decode_time_signature_value(
                        encoded_signature
                    )
                    time_signature_changes.append(
                        TimeSignatureEvent(beat, numerator, denominator)
                    )

            state["inside_tempo_candidate"] = False
            state["tempo_candidate_pointee_id"] = None
            state["tempo_candidate_float_events"] = None
            state["tempo_candidate_enum_events"] = None

        elif name == "Locator":
            locator_sources.append(
                LocatorSource(
                    state["locator_id"] or "",
                    state["locator_beat"] if state["locator_beat"] is not None else 0.0,
                    state["locator_name"] or "Unnamed Locator",
                )
            )
            state["inside_locator"] = False
            state["locator_id"] = None
            state["locator_name"] = None
            state["locator_beat"] = None

        path.pop()

    parser = expat.ParserCreate()
    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element

    for chunk in iter(lambda: xml_stream.read(chunk_size), b""):
        parser.Parse(chunk, False)

    parser.Parse(b"", True)

    return tempo_changes, time_signature_changes, time_signature_manual_value, locator_sources


def format_timestamp(total_seconds, precision=0):
    """
    Format seconds as MM:SS or MM:SS.sss depending on precision.

    precision=0 intentionally rounds up to the next whole second, preserving the
    behavior of the original script. Negative values are clamped to zero because
    timestamps before 00:00 are not useful in TSV or Mixcloud output.
    """
    total_seconds = max(0.0, total_seconds)

    if precision == 0:
        total_whole_seconds = math.ceil(total_seconds)

        minutes = total_whole_seconds // 60
        seconds = total_whole_seconds % 60

        return f"{minutes:02}:{seconds:02}"

    rounded_seconds = round(total_seconds, precision)

    minutes = int(rounded_seconds // 60)
    seconds = rounded_seconds - (minutes * 60)

    # Rounding can theoretically produce 60.000 seconds, so normalize it before
    # formatting rather than letting a timestamp such as 01:60.00 leak out.
    if seconds >= 60.0:
        minutes += 1
        seconds -= 60.0

    seconds_width = 3 + precision

    return f"{minutes:02}:{seconds:0{seconds_width}.{precision}f}"


def format_audition_time(total_seconds):
    """
    Format seconds for Adobe Audition marker import files.

    Audition's marker table examples use minute-oriented decimal timestamps such
    as 0:00.000 and 1:30.000. Internally, this formatter works in integer
    milliseconds so rounding cannot leak values such as 1:59.1000 or 1:60.000
    into the marker file.
    """
    total_milliseconds = max(0, int(round(total_seconds * 1000)))
    minutes, remaining_milliseconds = divmod(total_milliseconds, 60_000)
    seconds, milliseconds = divmod(remaining_milliseconds, 1000)

    return f"{minutes}:{seconds:02}.{milliseconds:03}"


def format_webvtt_time(total_seconds):
    """
    Format seconds as a WebVTT timestamp.

    WebVTT cue timings use hours, minutes, seconds, and milliseconds:
      HH:MM:SS.mmm
    """
    total_milliseconds = max(0, int(round(total_seconds * 1000)))
    hours, remaining_milliseconds = divmod(total_milliseconds, 3_600_000)
    minutes, remaining_milliseconds = divmod(remaining_milliseconds, 60_000)
    seconds, milliseconds = divmod(remaining_milliseconds, 1000)

    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"


def format_cue_time(total_seconds):
    """
    Format seconds as a CUE sheet index timestamp.

    CUE sheets use CD frames rather than milliseconds. There are 75 frames per
    second, so 01:02:03 means one minute, two seconds, and three frames.
    """
    total_frames = max(0, int(round(total_seconds * CUE_FRAMES_PER_SECOND)))
    minutes, remaining_frames = divmod(total_frames, 60 * CUE_FRAMES_PER_SECOND)
    seconds, frames = divmod(remaining_frames, CUE_FRAMES_PER_SECOND)

    return f"{minutes:02}:{seconds:02}:{frames:02}"


def single_line_text(raw_text):
    """Collapse user-facing labels into one safe line for cue-style formats."""
    return " ".join(str(raw_text).splitlines())


def webvtt_cue_text(raw_text):
    """
    Return text that is safe to place in a WebVTT cue body.

    The arrow token separates cue timing from cue text in WebVTT, so replace it
    if a locator label happens to contain that exact sequence.
    """
    return single_line_text(raw_text).replace("-->", "->")


def cue_quoted_text(raw_text):
    """
    Quote text for simple CUE sheet fields.

    Double quotes inside locator labels are replaced with apostrophes. That is
    intentionally conservative because CUE parsers vary in how they treat
    escaped quotes inside TITLE and FILE fields.
    """
    safe_text = single_line_text(raw_text).replace('"', "'")
    return f'"{safe_text}"'


def markdown_table_cell(raw_value):
    """Escape one value for a simple GitHub-flavored Markdown table cell."""
    text = single_line_text(raw_value)
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    return text


def midi_variable_length_quantity(value):
    """
    Encode an integer as a MIDI variable-length quantity.

    Standard MIDI delta times and meta-event lengths use this compact base-128
    representation. Values here are small, but the full encoding keeps the
    writer correct for long sessions.
    """
    value = max(0, int(value))
    bytes_out = [value & 0x7F]
    value >>= 7

    while value:
        bytes_out.insert(0, (value & 0x7F) | 0x80)
        value >>= 7

    return bytes(bytes_out)


def midi_meta_event(delta_ticks, meta_type, payload=b""):
    """Build one Standard MIDI meta event with a variable-length delta time."""
    payload = bytes(payload)

    return b"".join(
        (
            midi_variable_length_quantity(delta_ticks),
            b"\xFF",
            bytes((meta_type,)),
            midi_variable_length_quantity(len(payload)),
            payload,
        )
    )


def midi_text_payload(raw_text):
    """Encode one MIDI marker/track-name text payload."""
    return single_line_text(raw_text).encode("utf-8")


def midi_tick_for_beat(beat):
    """Convert an Ableton beat position to a Standard MIDI tick position."""
    return max(0, int(round(beat * MIDI_TICKS_PER_QUARTER_NOTE)))


def midi_tempo_payload(bpm):
    """Encode BPM as a MIDI set-tempo payload."""
    require_positive_bpm(bpm, "midi tempo bpm")
    microseconds_per_quarter = int(round(60_000_000 / bpm))
    clamped_value = min(max(1, microseconds_per_quarter), 0xFFFFFF)
    return clamped_value.to_bytes(3, byteorder="big")


def midi_time_signature_payload(time_signature_event):
    """Encode an Ableton time signature as a MIDI time-signature payload."""
    try:
        denominator_power = TIME_SIGNATURE_DENOMINATORS.index(
            time_signature_event.denominator
        )
    except ValueError as exc:
        raise LocatorToolError(
            "Ableton file contains a time-signature denominator MIDI cannot encode.",
            [("denominator", time_signature_event.denominator)],
        ) from exc

    numerator = max(1, min(255, int(time_signature_event.numerator)))
    return bytes(
        (
            numerator,
            denominator_power,
            MIDI_DEFAULT_CLOCKS_PER_METRONOME_CLICK,
            MIDI_DEFAULT_32ND_NOTES_PER_QUARTER_NOTE,
        )
    )


def normalized_tempo_events(tempo_changes):
    """Return sorted tempo events with a definite active tempo at beat zero."""
    if not tempo_changes:
        return [(0.0, DEFAULT_BPM)]

    sorted_changes = sorted(tempo_changes, key=lambda item: item[0])
    active_at_zero = (0.0, DEFAULT_BPM)
    future_changes = []

    for beat, bpm in sorted_changes:
        if beat <= 0:
            active_at_zero = (0.0, bpm)
        else:
            future_changes.append((beat, bpm))

    normalized_events = [active_at_zero]

    for beat, bpm in future_changes:
        if normalized_events[-1][0] == beat:
            normalized_events[-1] = (beat, bpm)
        else:
            normalized_events.append((beat, bpm))

    return normalized_events


def normalized_time_signature_events(time_signature_changes, manual_value):
    """
    Return sorted time signature events with a definite event at beat zero.

    Ableton represents the initial time signature either as the main manual
    value, an automation enum event far before the arrangement, or both. For
    position calculations, any pre-zero value is treated as the active signature
    at beat zero.
    """
    if manual_value is None:
        manual_value = DEFAULT_TIME_SIGNATURE_VALUE

    manual_numerator, manual_denominator = decode_time_signature_value(manual_value)
    sorted_changes = sorted(time_signature_changes, key=lambda item: item.beat)
    active_at_zero = TimeSignatureEvent(0.0, manual_numerator, manual_denominator)
    future_changes = []

    for event in sorted_changes:
        if event.beat <= 0:
            active_at_zero = TimeSignatureEvent(0.0, event.numerator, event.denominator)
        else:
            future_changes.append(event)

    normalized_events = [active_at_zero]

    for event in future_changes:
        if normalized_events[-1].beat == event.beat:
            normalized_events[-1] = event
        else:
            normalized_events.append(event)

    return normalized_events


def build_beat_to_seconds_converter(tempo_changes):
    """
    Create a converter that maps Ableton beat positions to elapsed seconds.

    The converter integrates over every tempo segment once, caches the elapsed
    seconds at each tempo event, then uses those cached anchors to convert
    arbitrary locator beats efficiently.
    """
    beat_positions = [beat for beat, _bpm in tempo_changes]
    seconds_at_beat = [0.0]
    total_seconds = 0.0

    for index in range(1, len(tempo_changes)):
        previous_beat, previous_bpm = tempo_changes[index - 1]
        current_beat, current_bpm = tempo_changes[index]

        total_seconds += seconds_for_segment(
            previous_beat,
            previous_bpm,
            current_beat,
            current_bpm,
        )
        seconds_at_beat.append(total_seconds)

    def beat_to_seconds(beat):
        first_beat, first_bpm = tempo_changes[0]

        if beat <= first_beat:
            require_positive_bpm(first_bpm, "first tempo event bpm")
            return (beat - first_beat) * (60.0 / first_bpm)

        next_event_index = bisect.bisect_left(beat_positions, beat)

        if (
            next_event_index < len(beat_positions)
            and beat == beat_positions[next_event_index]
        ):
            return seconds_at_beat[next_event_index]

        if next_event_index == len(tempo_changes):
            last_beat, last_bpm = tempo_changes[-1]
            require_positive_bpm(last_bpm, "last tempo event bpm")
            return seconds_at_beat[-1] + (beat - last_beat) * (60.0 / last_bpm)

        segment_start_index = next_event_index - 1
        segment_start_beat, segment_start_bpm = tempo_changes[segment_start_index]
        segment_end_beat, segment_end_bpm = tempo_changes[next_event_index]
        segment_beats = beat - segment_start_beat

        if abs(segment_end_bpm - segment_start_bpm) < 1e-9:
            return seconds_at_beat[segment_start_index] + segment_beats * (
                60.0 / segment_start_bpm
            )

        slope = (segment_end_bpm - segment_start_bpm) / (
            segment_end_beat - segment_start_beat
        )
        bpm_at_beat = segment_start_bpm + slope * segment_beats

        require_positive_bpm(bpm_at_beat, "interpolated tempo bpm")

        return seconds_at_beat[segment_start_index] + (60.0 / slope) * math.log(
            bpm_at_beat / segment_start_bpm
        )

    return beat_to_seconds


def build_tempo_at_beat_lookup(tempo_changes):
    """
    Create a lookup that returns the active/interpolated tempo at a beat.

    Tempo automation in Live is linear between float events. This mirrors the
    same ramp behavior used by the seconds converter, but returns BPM instead
    of elapsed time.
    """
    beat_positions = [beat for beat, _bpm in tempo_changes]

    def tempo_at_beat(beat):
        first_beat, first_bpm = tempo_changes[0]

        if beat <= first_beat:
            return first_bpm

        next_event_index = bisect.bisect_right(beat_positions, beat)

        if next_event_index == len(tempo_changes):
            return tempo_changes[-1][1]

        segment_start_index = next_event_index - 1
        segment_start_beat, segment_start_bpm = tempo_changes[segment_start_index]
        segment_end_beat, segment_end_bpm = tempo_changes[next_event_index]

        if abs(segment_end_beat - segment_start_beat) < 1e-9:
            return segment_end_bpm

        beat_offset = beat - segment_start_beat
        slope = (segment_end_bpm - segment_start_bpm) / (
            segment_end_beat - segment_start_beat
        )

        return segment_start_bpm + slope * beat_offset

    return tempo_at_beat


def beats_per_bar(time_signature_event):
    """Return the number of Ableton quarter-note beats in one bar."""
    return time_signature_event.numerator * (4.0 / time_signature_event.denominator)


def beat_unit_size(time_signature_event):
    """Return the size of one displayed beat in Ableton quarter-note beats."""
    return 4.0 / time_signature_event.denominator


def build_time_signature_context(time_signature_events):
    """
    Create lookups for musical position and active time signature.

    Ableton beat zero displays as bar 1, beat 1, sixteenth 1. Time signature
    events start new sections; each section tracks the bar number that was
    current when the section began.
    """
    event_beats = [event.beat for event in time_signature_events]
    section_start_bars = [1]

    for index in range(1, len(time_signature_events)):
        previous_event = time_signature_events[index - 1]
        previous_start_bar = section_start_bars[index - 1]
        beats_since_previous = time_signature_events[index].beat - previous_event.beat
        bars_since_previous = math.floor(
            max(0.0, beats_since_previous) / beats_per_bar(previous_event) + 1e-9
        )
        section_start_bars.append(previous_start_bar + bars_since_previous)

    def event_index_at_beat(beat):
        return max(0, bisect.bisect_right(event_beats, beat) - 1)

    def position_parts_at_beat(beat):
        event_index = event_index_at_beat(beat)
        event = time_signature_events[event_index]
        section_offset = max(0.0, beat - event.beat)
        bar_length = beats_per_bar(event)
        displayed_beat_size = beat_unit_size(event)
        bars_into_section = math.floor(section_offset / bar_length + 1e-9)
        bar_number = section_start_bars[event_index] + bars_into_section
        beat_offset_in_bar = section_offset - (bars_into_section * bar_length)
        displayed_beat = math.floor(
            beat_offset_in_bar / displayed_beat_size + 1e-9
        ) + 1
        beat_remainder = beat_offset_in_bar - (
            (displayed_beat - 1) * displayed_beat_size
        )
        sixteenth = math.floor(beat_remainder / 0.25 + 1e-9) + 1

        return event_index, bar_number, displayed_beat, sixteenth

    def format_position_parts(bar_number, displayed_beat, sixteenth):
        return f"{bar_number}.{displayed_beat}.{sixteenth}"

    section_start_positions = []

    for event in time_signature_events:
        _event_index, bar_number, displayed_beat, sixteenth = position_parts_at_beat(
            event.beat
        )
        section_start_positions.append(
            format_position_parts(bar_number, displayed_beat, sixteenth)
        )

    def context_at_beat(beat):
        event_index, bar_number, displayed_beat, sixteenth = position_parts_at_beat(beat)
        event = time_signature_events[event_index]

        return TimeSignatureContext(
            event=event,
            bar_number=bar_number,
            displayed_beat=displayed_beat,
            sixteenth=sixteenth,
            song_position=format_position_parts(bar_number, displayed_beat, sixteenth),
            time_signature=f"{event.numerator}/{event.denominator}",
            time_signature_section_start=section_start_positions[event_index],
        )

    return context_at_beat


def extract_locator_data(
    als_path,
    add_offset=0.0,
    strip_keys=False,
    track_number_offset=0,
):
    """
    Extract locators, export fields, and the session timing map.

    The output timestamp remains the familiar normalized time plus any user
    offset. Metadata columns keep their own meanings: absolute values refer to
    the session timeline, and normalized_seconds excludes the user offset. The
    normalized tempo and time-signature events travel with the rows so optional
    export formats can reuse the already parsed ALS timing data instead of
    reading the session file a second time.
    """
    (
        raw_tempo_changes,
        raw_time_signature_changes,
        manual_time_signature_value,
        locator_sources,
    ) = parse_als_locator_data(als_path)
    tempo_changes = normalized_tempo_events(raw_tempo_changes)
    time_signature_events = normalized_time_signature_events(
        raw_time_signature_changes,
        manual_time_signature_value,
    )
    beat_to_seconds = build_beat_to_seconds_converter(tempo_changes)
    tempo_at_beat = build_tempo_at_beat_lookup(tempo_changes)
    time_signature_context_at_beat = build_time_signature_context(
        time_signature_events
    )

    prepared_locators = []
    earliest_seconds = float("inf")

    for locator_source in locator_sources:
        name = locator_source.name

        if strip_keys:
            name = strip_key_prefix(name)

        absolute_seconds = beat_to_seconds(locator_source.beat)
        timing_context = time_signature_context_at_beat(locator_source.beat)

        earliest_seconds = min(earliest_seconds, absolute_seconds)
        prepared_locators.append(
            {
                "source": locator_source,
                "name": name,
                "absolute_seconds": absolute_seconds,
                "tempo_bpm": tempo_at_beat(locator_source.beat),
                "timing_context": timing_context,
            }
        )

    if not prepared_locators:
        return LocatorExtractionResult(
            rows=[],
            tempo_events=tuple(tempo_changes),
            time_signature_events=tuple(time_signature_events),
        )

    rows = []

    for prepared_locator in prepared_locators:
        source = prepared_locator["source"]
        normalized_seconds = prepared_locator["absolute_seconds"] - earliest_seconds
        output_seconds = normalized_seconds + add_offset
        timing_context = prepared_locator["timing_context"]

        rows.append(
            LocatorExportRow(
                output_seconds=output_seconds,
                name=prepared_locator["name"],
                locator_id=source.locator_id,
                absolute_beats=source.beat,
                absolute_seconds=prepared_locator["absolute_seconds"],
                normalized_seconds=normalized_seconds,
                tempo_bpm=prepared_locator["tempo_bpm"],
                song_position=timing_context.song_position,
                time_signature=timing_context.time_signature,
                bar_number=timing_context.bar_number,
                time_signature_section_start=(
                    timing_context.time_signature_section_start
                ),
                track_number=0,
            )
        )

    rows.sort(key=lambda item: item.output_seconds)

    numbered_rows = [
        LocatorExportRow(
            output_seconds=row.output_seconds,
            name=row.name,
            locator_id=row.locator_id,
            absolute_beats=row.absolute_beats,
            absolute_seconds=row.absolute_seconds,
            normalized_seconds=row.normalized_seconds,
            tempo_bpm=row.tempo_bpm,
            song_position=row.song_position,
            time_signature=row.time_signature,
            bar_number=row.bar_number,
            time_signature_section_start=row.time_signature_section_start,
            track_number=index + track_number_offset,
        )
        for index, row in enumerate(rows, start=1)
    ]

    return LocatorExtractionResult(
        rows=numbered_rows,
        tempo_events=tuple(tempo_changes),
        time_signature_events=tuple(time_signature_events),
    )


def extract_locator_rows(
    als_path,
    add_offset=0.0,
    strip_keys=False,
    track_number_offset=0,
):
    """
    Extract locators and compute every supported export field.

    This compatibility wrapper preserves the existing list return value for
    callers that do not need the parsed tempo or time-signature maps.
    """
    return extract_locator_data(
        als_path,
        add_offset=add_offset,
        strip_keys=strip_keys,
        track_number_offset=track_number_offset,
    ).rows


def extract_locators_with_ramps(als_path, add_offset=0.0, strip_keys=False):
    """
    Extract locators from an ALS file and return them as (seconds, name) tuples.

    This compatibility wrapper preserves the original internal return shape for
    callers that only need timestamp and label values.
    """
    return [
        (row.output_seconds, row.name)
        for row in extract_locator_rows(
            als_path,
            add_offset=add_offset,
            strip_keys=strip_keys,
        )
    ]


def ensure_parent_directory(path):
    """Fail early with a clear message when the output directory is missing."""
    parent = path.parent

    if parent and not parent.exists():
        raise LocatorToolError(
            "Output directory does not exist.",
            [("path", display_path(parent))],
        )


def column_header(column_name, time_header, label_header):
    """Return the TSV heading label for a selected export column."""
    if column_name == "time":
        return time_header

    if column_name == "label":
        return label_header

    return COLUMN_HEADERS[column_name]


def tsv_value(row, column_name, precision=0):
    """Format one selected column for TSV output."""
    if column_name == "time":
        return format_timestamp(row.output_seconds, precision=precision)

    if column_name == "label":
        return row.name

    if column_name == "tempo":
        return format_decimal(row.tempo_bpm)

    if column_name == "song_position":
        return row.song_position

    if column_name == "time_signature":
        return row.time_signature

    if column_name == "absolute_seconds":
        return format_decimal(row.absolute_seconds)

    if column_name == "normalized_seconds":
        return format_decimal(row.normalized_seconds)

    if column_name == "absolute_beats":
        return format_decimal(row.absolute_beats)

    if column_name == "bar_number":
        return str(row.bar_number)

    if column_name == "time_signature_section_start":
        return row.time_signature_section_start

    if column_name == "locator_id":
        return row.locator_id

    if column_name == "track_number":
        return str(row.track_number)

    raise LocatorToolError(
        "Unknown export column requested.",
        [("column", column_name)],
    )


def json_value(row, column_name, precision=0):
    """Return one selected column as a JSON-friendly value."""
    if column_name == "time":
        return format_timestamp(row.output_seconds, precision=precision)

    if column_name == "label":
        return row.name

    if column_name == "tempo":
        return round(row.tempo_bpm, DEFAULT_METADATA_DECIMAL_PLACES)

    if column_name == "song_position":
        return row.song_position

    if column_name == "time_signature":
        return row.time_signature

    if column_name == "absolute_seconds":
        return round(row.absolute_seconds, DEFAULT_METADATA_DECIMAL_PLACES)

    if column_name == "normalized_seconds":
        return round(row.normalized_seconds, DEFAULT_METADATA_DECIMAL_PLACES)

    if column_name == "absolute_beats":
        return round(row.absolute_beats, DEFAULT_METADATA_DECIMAL_PLACES)

    if column_name == "bar_number":
        return row.bar_number

    if column_name == "time_signature_section_start":
        return row.time_signature_section_start

    if column_name == "locator_id":
        return int(row.locator_id) if row.locator_id.isdigit() else row.locator_id

    if column_name == "track_number":
        return row.track_number

    raise LocatorToolError(
        "Unknown export column requested.",
        [("column", column_name)],
    )


def write_tsv(
    rows,
    output_tsv,
    precision=0,
    columns=DEFAULT_TSV_COLUMNS,
    time_header=DEFAULT_TIME_HEADER,
    label_header=DEFAULT_LABEL_HEADER,
    include_heading_row=True,
):
    """Write locators to a tab-separated file."""
    ensure_parent_directory(output_tsv)

    try:
        with output_tsv.open("w", encoding="utf-8") as out:
            lines = []

            if include_heading_row:
                headings = [
                    column_header(column, time_header, label_header)
                    for column in columns
                ]
                lines.append("\t".join(headings) + "\n")

            for row in rows:
                values = [
                    tsv_value(row, column, precision=precision)
                    for column in columns
                ]
                lines.append("\t".join(values) + "\n")

            out.writelines(lines)
    except PermissionError as exc:
        raise LocatorToolError(
            "Permission denied while writing the TSV output file.",
            [("path", display_path(output_tsv))],
        ) from exc
    except OSError as exc:
        raise LocatorToolError(
            "Unable to write the TSV output file.",
            [("path", display_path(output_tsv)), ("detail", exc)],
        ) from exc


def write_csv_export(
    rows,
    output_csv,
    precision=0,
    columns=DEFAULT_TSV_COLUMNS,
    time_header=DEFAULT_TIME_HEADER,
    label_header=DEFAULT_LABEL_HEADER,
    include_heading_row=True,
):
    """
    Write locators to a normal comma-separated CSV file.

    This intentionally mirrors TSV column selection and heading behavior. It is
    separate from Adobe Audition marker export, whose .csv filename convention
    still contains tab-separated marker rows.
    """
    ensure_parent_directory(output_csv)

    try:
        with output_csv.open("w", encoding="utf-8", newline="") as out:
            writer = csv.writer(out, lineterminator="\n")

            if include_heading_row:
                writer.writerow(
                    [
                        column_header(column, time_header, label_header)
                        for column in columns
                    ]
                )

            for row in rows:
                writer.writerow(
                    [
                        tsv_value(row, column, precision=precision)
                        for column in columns
                    ]
                )
    except PermissionError as exc:
        raise LocatorToolError(
            "Permission denied while writing the CSV output file.",
            [("path", display_path(output_csv))],
        ) from exc
    except OSError as exc:
        raise LocatorToolError(
            "Unable to write the CSV output file.",
            [("path", display_path(output_csv)), ("detail", exc)],
        ) from exc


def write_mixcloud_tracklist(rows, mixcloud_path):
    """
    Write a Mixcloud-compatible tracklist.

    Mixcloud marker paste format is intentionally simple:
      MM:SS Track Name

    Mixcloud does not need decimal seconds, so this always uses whole-second
    timestamps no matter which TSV precision the caller selected.
    """
    ensure_parent_directory(mixcloud_path)

    try:
        with mixcloud_path.open("w", encoding="utf-8") as out:
            lines = []

            for row in rows:
                timestamp = format_timestamp(row.output_seconds, precision=0)
                lines.append(f"{timestamp} {row.name}\n")

            out.writelines(lines)
    except PermissionError as exc:
        raise LocatorToolError(
            "Permission denied while writing the Mixcloud output file.",
            [("path", display_path(mixcloud_path))],
        ) from exc
    except OSError as exc:
        raise LocatorToolError(
            "Unable to write the Mixcloud output file.",
            [("path", display_path(mixcloud_path)), ("detail", exc)],
        ) from exc


def write_audition_markers(rows, audition_path):
    """
    Write an Adobe Audition marker import file.

    Audition exposes this as a marker CSV workflow, but the practical import
    format is a tab-separated marker table. Each Ableton locator maps cleanly to
    a point marker, so exported rows use zero duration and the Cue marker type.
    """
    ensure_parent_directory(audition_path)

    try:
        with audition_path.open("w", encoding="utf-8", newline="") as out:
            writer = csv.writer(
                out,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writerow(AUDITION_MARKER_HEADERS)

            for row in rows:
                writer.writerow(
                    (
                        row.name,
                        format_audition_time(row.output_seconds),
                        AUDITION_ZERO_DURATION,
                        AUDITION_TIME_FORMAT,
                        AUDITION_MARKER_TYPE,
                        "",
                    )
                )
    except PermissionError as exc:
        raise LocatorToolError(
            "Permission denied while writing the Adobe Audition marker file.",
            [("path", display_path(audition_path))],
        ) from exc
    except OSError as exc:
        raise LocatorToolError(
            "Unable to write the Adobe Audition marker file.",
            [("path", display_path(audition_path)), ("detail", exc)],
        ) from exc


def write_webvtt_chapters(rows, webvtt_path):
    """
    Write locators as WebVTT chapter cues.

    WebVTT cues require an end time. Locator rows only provide point markers, so
    every cue ends at the next locator. The final cue receives a small one
    second duration because this script does not know the rendered media end.
    """
    ensure_parent_directory(webvtt_path)

    try:
        with webvtt_path.open("w", encoding="utf-8") as out:
            lines = ["WEBVTT\n", "\n"]

            for index, row in enumerate(rows):
                start_seconds = max(0.0, row.output_seconds)

                next_row_starts_later = (
                    index + 1 < len(rows)
                    and rows[index + 1].output_seconds > start_seconds
                )

                if next_row_starts_later:
                    end_seconds = rows[index + 1].output_seconds
                else:
                    end_seconds = start_seconds + WEBVTT_FINAL_CUE_SECONDS

                cue_text = webvtt_cue_text(row.name) or f"Locator {index + 1}"
                lines.extend(
                    [
                        (
                            f"{format_webvtt_time(start_seconds)} --> "
                            f"{format_webvtt_time(end_seconds)}\n"
                        ),
                        f"{cue_text}\n",
                        "\n",
                    ]
                )

            out.writelines(lines)
    except PermissionError as exc:
        raise LocatorToolError(
            "Permission denied while writing the WebVTT output file.",
            [("path", display_path(webvtt_path))],
        ) from exc
    except OSError as exc:
        raise LocatorToolError(
            "Unable to write the WebVTT output file.",
            [("path", display_path(webvtt_path)), ("detail", exc)],
        ) from exc


def write_cue_sheet(rows, cue_path, als_path, cue_audio=None):
    """
    Write a CUE sheet from locator rows.

    The FILE line points at a rendered audio filename. If the caller does not
    provide one, use the input ALS stem with a .wav suffix as a practical
    placeholder that can be edited after rendering.
    """
    ensure_parent_directory(cue_path)

    cue_audio_name = cue_audio or (
        f"{Path(als_path).stem}{CUE_DEFAULT_AUDIO_SUFFIX}"
    )
    cue_title = Path(als_path).stem

    try:
        with cue_path.open("w", encoding="utf-8") as out:
            lines = [
                f"TITLE {cue_quoted_text(cue_title)}\n",
                f"FILE {cue_quoted_text(cue_audio_name)} WAVE\n",
            ]

            for index, row in enumerate(rows, start=1):
                track_title = row.name or f"Track {index:02d}"
                lines.extend(
                    [
                        f"  TRACK {index:02d} AUDIO\n",
                        f"    TITLE {cue_quoted_text(track_title)}\n",
                        f"    INDEX 01 {format_cue_time(row.output_seconds)}\n",
                    ]
                )

            out.writelines(lines)
    except PermissionError as exc:
        raise LocatorToolError(
            "Permission denied while writing the CUE sheet.",
            [("path", display_path(cue_path))],
        ) from exc
    except OSError as exc:
        raise LocatorToolError(
            "Unable to write the CUE sheet.",
            [("path", display_path(cue_path)), ("detail", exc)],
        ) from exc


def write_markdown_report(
    rows,
    markdown_path,
    columns,
    als_path,
    precision=0,
    time_header=DEFAULT_TIME_HEADER,
    label_header=DEFAULT_LABEL_HEADER,
):
    """
    Write a human-readable Markdown locator report.

    Markdown is meant for release notes, documentation, review comments, and
    quick sharing. Unlike raw TSV/CSV, it always includes table headings.
    """
    ensure_parent_directory(markdown_path)

    headings = [
        column_header(column, time_header, label_header)
        for column in columns
    ]
    separator = ["---" for _column in columns]

    try:
        with markdown_path.open("w", encoding="utf-8") as out:
            lines = [
                "# Locator Export\n",
                "\n",
                f"- Source: `{Path(als_path).name}`\n",
                f"- Locators: `{len(rows)}`\n",
                f"- Generated by: `{SCRIPT_NAME}`\n",
                "\n",
                (
                    "| "
                    + " | ".join(markdown_table_cell(item) for item in headings)
                    + " |\n"
                ),
                "| " + " | ".join(separator) + " |\n",
            ]

            for row in rows:
                values = [
                    tsv_value(row, column, precision=precision)
                    for column in columns
                ]
                lines.append(
                    "| "
                    + " | ".join(markdown_table_cell(value) for value in values)
                    + " |\n"
                )

            out.writelines(lines)
    except PermissionError as exc:
        raise LocatorToolError(
            "Permission denied while writing the Markdown output file.",
            [("path", display_path(markdown_path))],
        ) from exc
    except OSError as exc:
        raise LocatorToolError(
            "Unable to write the Markdown output file.",
            [("path", display_path(markdown_path)), ("detail", exc)],
        ) from exc


def write_midi_markers(
    rows,
    midi_path,
    tempo_events=(),
    time_signature_events=(),
    include_timing_map=False,
):
    """
    Write locator names as Standard MIDI marker meta events.

    MIDI files are beat/tick-based, so markers use each locator's absolute
    Ableton beat position. Text timestamp offsets do not apply here. When the
    optional timing map is enabled, tempo and time-signature meta events are
    written at their absolute Ableton beat positions in the same single track.
    """
    ensure_parent_directory(midi_path)

    try:
        track_events = bytearray()
        track_name = (
            "Ableton Live Locator Timing Map"
            if include_timing_map
            else "Ableton Live Locators"
        )
        track_events.extend(
            midi_meta_event(
                0,
                MIDI_TRACK_NAME_META_TYPE,
                midi_text_payload(track_name),
            )
        )

        scheduled_events = []

        if include_timing_map:
            for beat, bpm in tempo_events:
                scheduled_events.append(
                    (
                        midi_tick_for_beat(beat),
                        10,
                        MIDI_TEMPO_META_TYPE,
                        midi_tempo_payload(bpm),
                    )
                )

            for signature_event in time_signature_events:
                scheduled_events.append(
                    (
                        midi_tick_for_beat(signature_event.beat),
                        20,
                        MIDI_TIME_SIGNATURE_META_TYPE,
                        midi_time_signature_payload(signature_event),
                    )
                )

        sorted_rows = sorted(rows, key=lambda item: item.absolute_beats)

        for index, row in enumerate(sorted_rows, start=1):
            marker_name = row.name or f"Locator {index}"
            scheduled_events.append(
                (
                    midi_tick_for_beat(row.absolute_beats),
                    30,
                    MIDI_MARKER_META_TYPE,
                    midi_text_payload(marker_name),
                )
            )

        scheduled_events.sort(key=lambda item: (item[0], item[1]))
        previous_tick = 0

        for tick, _priority, meta_type, payload in scheduled_events:
            delta_ticks = max(0, tick - previous_tick)
            previous_tick = tick
            track_events.extend(
                midi_meta_event(
                    delta_ticks,
                    meta_type,
                    payload,
                )
            )

        track_events.extend(
            midi_meta_event(0, MIDI_END_OF_TRACK_META_TYPE)
        )

        header_chunk = b"".join(
            (
                b"MThd",
                (6).to_bytes(4, byteorder="big"),
                MIDI_FORMAT_SINGLE_TRACK.to_bytes(2, byteorder="big"),
                MIDI_TRACK_COUNT.to_bytes(2, byteorder="big"),
                MIDI_TICKS_PER_QUARTER_NOTE.to_bytes(2, byteorder="big"),
            )
        )
        track_chunk = b"".join(
            (
                b"MTrk",
                len(track_events).to_bytes(4, byteorder="big"),
                bytes(track_events),
            )
        )

        with midi_path.open("wb") as out:
            out.write(header_chunk)
            out.write(track_chunk)
    except PermissionError as exc:
        raise LocatorToolError(
            "Permission denied while writing the MIDI output file.",
            [("path", display_path(midi_path))],
        ) from exc
    except OSError as exc:
        raise LocatorToolError(
            "Unable to write the MIDI output file.",
            [("path", display_path(midi_path)), ("detail", exc)],
        ) from exc


def build_json_payload(rows, columns, als_path, precision=0):
    """Build the structured JSON export payload."""
    return {
        "generated_by": SCRIPT_NAME,
        "version": SCRIPT_VERSION,
        "source_file": display_path(als_path),
        "columns": list(columns),
        "locators": [
            {
                column: json_value(row, column, precision=precision)
                for column in columns
            }
            for row in rows
        ],
    }


def write_json_export(
    rows,
    json_path,
    columns,
    als_path,
    precision=0,
    json_format="pretty",
):
    """Write locator rows to JSON in compact or human-readable form."""
    ensure_parent_directory(json_path)
    payload = build_json_payload(
        rows,
        columns,
        als_path,
        precision=precision,
    )

    if json_format == "compact":
        dump_options = {
            "ensure_ascii": False,
            "separators": (",", ":"),
        }
    else:
        dump_options = {
            "ensure_ascii": False,
            "indent": 2,
        }

    try:
        with json_path.open("w", encoding="utf-8") as out:
            json.dump(payload, out, **dump_options)
            out.write("\n")
    except PermissionError as exc:
        raise LocatorToolError(
            "Permission denied while writing the JSON output file.",
            [("path", display_path(json_path))],
        ) from exc
    except OSError as exc:
        raise LocatorToolError(
            "Unable to write the JSON output file.",
            [("path", display_path(json_path)), ("detail", exc)],
        ) from exc


def normalize_column_name(raw_column_name):
    """Normalize one user-supplied export column name or alias."""
    normalized = raw_column_name.strip().lower().replace("-", "_")
    normalized = COLUMN_ALIASES.get(normalized, normalized)

    if normalized not in ALL_TSV_COLUMNS:
        valid_names = ", ".join(ALL_TSV_COLUMNS)
        raise LocatorToolError(
            "Unknown export column requested.",
            [
                ("column", raw_column_name),
                ("valid", valid_names),
            ],
        )

    return normalized


def dedupe_columns(columns):
    """Return columns in order, keeping only the first instance of each."""
    seen = set()
    deduped = []

    for column in columns:
        if column not in seen:
            deduped.append(column)
            seen.add(column)

    return tuple(deduped)


def parse_column_list(raw_columns):
    """
    Parse a comma-separated column list from the command line.

    The special values "default" and "all" expand to the built-in two-column
    tracklist and the complete export field list, respectively.
    """
    if raw_columns is None:
        return DEFAULT_TSV_COLUMNS

    columns = []

    for raw_column in raw_columns.split(","):
        token = raw_column.strip()

        if not token:
            continue

        normalized = token.lower().replace("-", "_")

        if normalized == "default":
            columns.extend(DEFAULT_TSV_COLUMNS)
        elif normalized == "all":
            columns.extend(ALL_TSV_COLUMNS)
        else:
            columns.append(normalize_column_name(token))

    if not columns:
        raise LocatorToolError(
            "No export columns were selected.",
            [("columns", raw_columns)],
        )

    return dedupe_columns(columns)


def selected_columns_from_args(args):
    """Resolve the final export-column set from exact and convenience options."""
    columns = list(parse_column_list(args.columns))

    if args.all_columns:
        columns = list(ALL_TSV_COLUMNS)

    include_flag_columns = [
        column
        for column in OPTIONAL_TSV_COLUMNS
        if getattr(args, f"include_{column}")
    ]

    return dedupe_columns([*columns, *include_flag_columns])


def parse_args():
    """Parse command-line arguments and validate simple numeric options."""
    parser = LocatorArgumentParser(
        description="Extract Ableton locators to TSV with tempo-ramp-aware timing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 src/extract_locators.py song.als\n"
            "  python3 src/extract_locators.py song.als --output=locators.tsv\n"
            "  python3 src/extract_locators.py song.als --time-header=TIME --label-header=LABEL\n"
            "  python3 src/extract_locators.py song.als --no-heading-row\n"
            "  python3 src/extract_locators.py song.als --mixcloud=mixcloud.txt\n"
            "  python3 src/extract_locators.py song.als --csv=locators.csv\n"
            "  python3 src/extract_locators.py song.als --audition=audition_markers.csv\n"
            "  python3 src/extract_locators.py song.als --webvtt=chapters.vtt\n"
            "  python3 src/extract_locators.py song.als --cue=tracks.cue --cue-audio=render.wav\n"
            "  python3 src/extract_locators.py song.als --columns=all --markdown=locators.md\n"
            "  python3 src/extract_locators.py song.als --midi=markers.mid\n"
            "  python3 src/extract_locators.py song.als --midi=markers.mid --midi-timing-map\n"
            "  python3 src/extract_locators.py song.als --columns=all --json=locators.json\n"
            "  python3 src/extract_locators.py song.als --json=locators.json --json-format=compact\n"
            "  python3 src/extract_locators.py song.als --add-offset=27 --strip-keys --output=locators.tsv --mixcloud=mixcloud.txt --csv=locators.csv --audition=audition_markers.csv --webvtt=chapters.vtt --cue=tracks.cue --markdown=locators.md --midi=markers.mid"
        ),
    )

    parser.add_argument(
        "als_path",
        help="Path to the Ableton .als file. Plain XML and gzip-compressed ALS files are supported.",
    )

    parser.add_argument(
        "--add-offset",
        type=float,
        default=0.0,
        help="Add this many seconds to each locator position. Fractional values are accepted.",
    )

    parser.add_argument(
        "--precision",
        type=int,
        default=0,
        help="Decimal places to show in the TSV seconds field. Default: 0.",
    )

    parser.add_argument(
        "--strip-keys",
        action="store_true",
        help="Remove leading musical keys in parentheses from locator names, such as (B), (D#), (D♯), (Gb), or (G♭).",
    )

    parser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="Output TSV path. Default: <input filename>.txt in the current directory.",
    )

    parser.add_argument(
        "--time-header",
        metavar="LABEL",
        help=f"First TSV column heading. Default: {DEFAULT_TIME_HEADER}.",
    )

    parser.add_argument(
        "--label-header",
        metavar="LABEL",
        help=f"Second TSV column heading. Default: {DEFAULT_LABEL_HEADER}.",
    )

    parser.add_argument(
        "--no-heading-row",
        "--no-header",
        action="store_true",
        help="Omit the TSV heading row entirely.",
    )

    parser.add_argument(
        "--columns",
        metavar="LIST",
        help=(
            "Comma-separated TSV/JSON columns. Default: time,label. "
            "Use all to include every column."
        ),
    )

    parser.add_argument(
        "--all-columns",
        action="store_true",
        help="Include every available TSV/JSON column.",
    )

    parser.add_argument(
        "--include-tempo",
        action="store_true",
        help="Add the current tempo in BPM to TSV/JSON output.",
    )

    parser.add_argument(
        "--include-song-position",
        action="store_true",
        help="Add the current bar.beat.sixteenth position to TSV/JSON output.",
    )

    parser.add_argument(
        "--include-time-signature",
        action="store_true",
        help="Add the current time signature to TSV/JSON output.",
    )

    parser.add_argument(
        "--include-absolute-seconds",
        action="store_true",
        help="Add elapsed seconds from the beginning of the session.",
    )

    parser.add_argument(
        "--include-normalized-seconds",
        action="store_true",
        help="Add normalized seconds before user offset is applied.",
    )

    parser.add_argument(
        "--include-absolute-beats",
        action="store_true",
        help="Add the raw Ableton beat position.",
    )

    parser.add_argument(
        "--include-bar-number",
        action="store_true",
        help="Add the current bar number.",
    )

    parser.add_argument(
        "--include-time-signature-section-start",
        action="store_true",
        help="Add the song position where the current time signature began.",
    )

    parser.add_argument(
        "--include-locator-id",
        action="store_true",
        help="Add the Ableton locator ID.",
    )

    parser.add_argument(
        "--include-track-number",
        action="store_true",
        help="Add a sequential track number after sorting locators by time.",
    )

    parser.add_argument(
        "--track-number-offset",
        type=int,
        default=0,
        help="Offset track numbers. Use 4 to start at 5, or -1 to start at 0.",
    )

    parser.add_argument(
        "-m",
        "--mixcloud",
        metavar="PATH",
        help="Also write a Mixcloud-compatible tracklist to PATH.",
    )

    parser.add_argument(
        "--csv",
        metavar="PATH",
        help="Also write a normal comma-separated CSV export to PATH.",
    )

    parser.add_argument(
        "-a",
        "--audition",
        metavar="PATH",
        help=(
            "Also write an Adobe Audition marker import file to PATH. "
            "Use a .csv filename; the contents are tab-separated marker rows."
        ),
    )

    parser.add_argument(
        "--webvtt",
        metavar="PATH",
        help="Also write WebVTT chapter cues to PATH.",
    )

    parser.add_argument(
        "--cue",
        metavar="PATH",
        help="Also write a CUE sheet to PATH.",
    )

    parser.add_argument(
        "--cue-audio",
        metavar="PATH",
        help="Audio filename to use in the CUE sheet FILE line. Requires --cue.",
    )

    parser.add_argument(
        "--markdown",
        metavar="PATH",
        help="Also write a Markdown locator report to PATH.",
    )

    parser.add_argument(
        "--midi",
        metavar="PATH",
        help="Also write a Standard MIDI file with locator marker events to PATH.",
    )

    parser.add_argument(
        "--midi-timing-map",
        action="store_true",
        help="Add tempo and time-signature meta events to the Standard MIDI export. Requires --midi.",
    )

    parser.add_argument(
        "-j",
        "--json",
        metavar="PATH",
        help="Also write a JSON locator export to PATH.",
    )

    parser.add_argument(
        "--json-format",
        choices=("pretty", "compact"),
        default="pretty",
        help="JSON formatting style. Default: pretty.",
    )

    args = parser.parse_args()

    if args.precision < 0:
        parser.error("--precision must be 0 or greater")

    if args.track_number_offset < -1:
        parser.error("--track-number-offset only accepts -1 or greater")

    if args.no_heading_row and (
        args.time_header is not None or args.label_header is not None
    ):
        parser.error(
            "--no-heading-row cannot be combined with --time-header or --label-header"
        )

    if args.cue_audio is not None and args.cue is None:
        parser.error("--cue-audio requires --cue")

    if args.midi_timing_map and args.midi is None:
        parser.error("--midi-timing-map requires --midi")

    return args


def run(args):
    """Run the extraction workflow and return the values needed for reporting."""
    als_path = user_path(args.als_path)
    output_path = user_path(args.output) if args.output else default_output_path(als_path)
    mixcloud_path = user_path(args.mixcloud) if args.mixcloud else None
    csv_path = user_path(args.csv) if args.csv else None
    audition_path = user_path(args.audition) if args.audition else None
    webvtt_path = user_path(args.webvtt) if args.webvtt else None
    cue_path = user_path(args.cue) if args.cue else None
    cue_audio = str(Path(args.cue_audio).expanduser()) if args.cue_audio else None
    markdown_path = user_path(args.markdown) if args.markdown else None
    midi_path = user_path(args.midi) if args.midi else None
    json_path = user_path(args.json) if args.json else None
    columns = selected_columns_from_args(args)

    started_at = time.perf_counter()

    extraction = extract_locator_data(
        als_path,
        add_offset=args.add_offset,
        strip_keys=args.strip_keys,
        track_number_offset=args.track_number_offset,
    )
    locator_rows = extraction.rows

    if not locator_rows:
        return {
            "status": "no locators",
            "status_color": FG_YELLOW,
            "rows": [
                ("input", display_path(als_path)),
                ("locators", 0),
                ("elapsed", format_elapsed(started_at)),
            ],
            "exit_code": 0,
        }

    time_header = (
        args.time_header
        if args.time_header is not None
        else DEFAULT_TIME_HEADER
    )
    label_header = (
        args.label_header
        if args.label_header is not None
        else DEFAULT_LABEL_HEADER
    )
    include_heading_row = not args.no_heading_row

    write_tsv(
        locator_rows,
        output_tsv=output_path,
        precision=args.precision,
        columns=columns,
        time_header=time_header,
        label_header=label_header,
        include_heading_row=include_heading_row,
    )

    rows = [
        ("input", display_path(als_path)),
        ("locators", len(locator_rows)),
        ("output", display_path(output_path)),
    ]

    if csv_path:
        write_csv_export(
            locator_rows,
            output_csv=csv_path,
            precision=args.precision,
            columns=columns,
            time_header=time_header,
            label_header=label_header,
            include_heading_row=include_heading_row,
        )
        rows.append(("output", display_path(csv_path)))

    if mixcloud_path:
        write_mixcloud_tracklist(locator_rows, mixcloud_path=mixcloud_path)
        rows.append(("output", display_path(mixcloud_path)))

    if audition_path:
        write_audition_markers(locator_rows, audition_path=audition_path)
        rows.append(("output", display_path(audition_path)))

    if webvtt_path:
        write_webvtt_chapters(locator_rows, webvtt_path=webvtt_path)
        rows.append(("output", display_path(webvtt_path)))

    if cue_path:
        write_cue_sheet(
            locator_rows,
            cue_path=cue_path,
            als_path=als_path,
            cue_audio=cue_audio,
        )
        rows.append(("output", display_path(cue_path)))

    if markdown_path:
        write_markdown_report(
            locator_rows,
            markdown_path=markdown_path,
            columns=columns,
            als_path=als_path,
            precision=args.precision,
            time_header=time_header,
            label_header=label_header,
        )
        rows.append(("output", display_path(markdown_path)))

    if midi_path:
        write_midi_markers(
            locator_rows,
            midi_path=midi_path,
            tempo_events=extraction.tempo_events,
            time_signature_events=extraction.time_signature_events,
            include_timing_map=args.midi_timing_map,
        )
        rows.append(("output", display_path(midi_path)))

    if json_path:
        write_json_export(
            locator_rows,
            json_path=json_path,
            columns=columns,
            als_path=als_path,
            precision=args.precision,
            json_format=args.json_format,
        )
        rows.append(("output", display_path(json_path)))

    rows.append(("elapsed", format_elapsed(started_at)))

    return {
        "status": "complete",
        "status_color": FG_GREEN,
        "rows": rows,
        "exit_code": 0,
    }


def main():
    """CLI entry point."""
    args = parse_args()

    try:
        result = run(args)
    except LocatorToolError as exc:
        print_report(
            "error",
            [("problem", exc.problem), *exc.details],
            stream=sys.stderr,
            status_color=FG_RED,
        )
        raise SystemExit(1) from exc

    print_report(
        result["status"],
        result["rows"],
        status_color=result["status_color"],
    )
    raise SystemExit(result["exit_code"])


if __name__ == "__main__":
    main()
