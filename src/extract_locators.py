#!/usr/bin/env python3

"""
extract_locators.py
Version: 2026.05.17

Author: Evan Musial <evan@evan.engineer>
License: Creative Commons Attribution-ShareAlike 4.0 International

License meaning:
  - This license requires that reusers give credit to the creator.
  - It allows reusers to distribute, remix, adapt, and build upon the material
    in any medium or format, even for commercial purposes.
  - If others remix, adapt, or build upon the material, they must license the
    modified material under identical terms.

Version 2026.05.17 notes:
  - Added optional TSV/JSON columns for tempo, song position, time signature,
    absolute seconds, normalized seconds, absolute beats, bar number, time
    signature section start, locator ID, and track number.
  - Added JSON export with compact and human-readable formatting options.
  - Added metadata validation exemplars under examples/validation.
  - Updated CLI reporting with the "Locator Extraction Results" title,
    repeated "output" rows for written files, three-decimal elapsed time, and
    predictable exit codes for success and error handling.
  - Added a future export-field checklist in docs/locator-export-roadmap.md.

Version 2026.05.16 notes:
  - Optimized ALS parsing to run about 26% faster on the RYM_2026-03.als test session.
  - Reduced peak memory use by about 96% on the RYM_2026-03.als test session.
  - Moved the script into src/ and moved the long-form guide into Extract Locators.md.
  - Tested and validated from Python 3.9 through Python 3.14.5.

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
  python3 src/extract_locators.py song.als --include-tempo --include-song-position --include-time-signature --output=locators.tsv
  python3 src/extract_locators.py song.als --columns=all --json=locators.json
  python3 src/extract_locators.py song.als --add-offset=27 --strip-keys --output=locators.tsv --mixcloud=mixcloud.txt

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
from dataclasses import dataclass
import gzip
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import xml.parsers.expat as expat
import zlib


SCRIPT_NAME = "extract_locators.py"
SCRIPT_VERSION = "2026.05.17"
REPORT_TITLE = "Locator Extraction Results"
DEFAULT_BPM = 120.0
TEMPO_AUTOMATION_POINTEE_ID = "8"
TIME_SIGNATURE_AUTOMATION_POINTEE_ID = "10"
DEFAULT_TIME_SIGNATURE_VALUE = 201
TIME_SIGNATURE_DENOMINATORS = (1, 2, 4, 8, 16)
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


def parse_als_xml_stream(xml_stream, chunk_size=1024 * 1024):
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

    def path_ends_with(*tag_names):
        return (
            len(path) >= len(tag_names)
            and tuple(path[-len(tag_names) :]) == tag_names
        )

    def start_element(name, attrs):
        nonlocal time_signature_manual_value

        path.append(name)

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

        if path_ends_with(
            "MainTrack",
            "DeviceChain",
            "Mixer",
            "TimeSignature",
            "Manual",
        ):
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

    def format_song_position(beat):
        _event_index, bar_number, displayed_beat, sixteenth = position_parts_at_beat(
            beat
        )
        return f"{bar_number}.{displayed_beat}.{sixteenth}"

    def context_at_beat(beat):
        event_index, bar_number, _displayed_beat, _sixteenth = position_parts_at_beat(
            beat
        )
        event = time_signature_events[event_index]
        section_start = format_song_position(event.beat)

        return {
            "event": event,
            "bar_number": bar_number,
            "song_position": format_song_position(beat),
            "time_signature": f"{event.numerator}/{event.denominator}",
            "time_signature_section_start": section_start,
        }

    return context_at_beat


def extract_locator_rows(
    als_path,
    add_offset=0.0,
    strip_keys=False,
    track_number_offset=0,
):
    """
    Extract locators and compute every supported export field.

    The output timestamp remains the familiar normalized time plus any user
    offset. Metadata columns keep their own meanings: absolute values refer to
    the session timeline, and normalized_seconds excludes the user offset.
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
        return []

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
                song_position=timing_context["song_position"],
                time_signature=timing_context["time_signature"],
                bar_number=timing_context["bar_number"],
                time_signature_section_start=timing_context[
                    "time_signature_section_start"
                ],
                track_number=0,
            )
        )

    rows.sort(key=lambda item: item.output_seconds)

    return [
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
            "  python3 src/extract_locators.py song.als --columns=all --json=locators.json\n"
            "  python3 src/extract_locators.py song.als --json=locators.json --json-format=compact\n"
            "  python3 src/extract_locators.py song.als --add-offset=27 --strip-keys --output=locators.tsv --mixcloud=mixcloud.txt"
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
        parser.error("--no-heading-row cannot be combined with --time-header or --label-header")

    return args


def run(args):
    """Run the extraction workflow and return the values needed for reporting."""
    als_path = user_path(args.als_path)
    output_path = user_path(args.output) if args.output else default_output_path(als_path)
    mixcloud_path = user_path(args.mixcloud) if args.mixcloud else None
    json_path = user_path(args.json) if args.json else None
    columns = selected_columns_from_args(args)

    started_at = time.perf_counter()

    locator_rows = extract_locator_rows(
        als_path,
        add_offset=args.add_offset,
        strip_keys=args.strip_keys,
        track_number_offset=args.track_number_offset,
    )

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

    write_tsv(
        locator_rows,
        output_tsv=output_path,
        precision=args.precision,
        columns=columns,
        time_header=(
            args.time_header
            if args.time_header is not None
            else DEFAULT_TIME_HEADER
        ),
        label_header=(
            args.label_header
            if args.label_header is not None
            else DEFAULT_LABEL_HEADER
        ),
        include_heading_row=not args.no_heading_row,
    )

    rows = [
        ("input", display_path(als_path)),
        ("locators", len(locator_rows)),
        ("output", display_path(output_path)),
    ]

    if mixcloud_path:
        write_mixcloud_tracklist(locator_rows, mixcloud_path=mixcloud_path)
        rows.append(("output", display_path(mixcloud_path)))

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
