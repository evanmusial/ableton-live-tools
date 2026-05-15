#!/usr/bin/env python3

"""
extract_locators.py
Version: 2026.05

Author: Evan Musial <evan@evan.engineer>
License: Creative Commons Attribution-ShareAlike 4.0 International

License meaning:
  - This license requires that reusers give credit to the creator.
  - It allows reusers to distribute, remix, adapt, and build upon the material
    in any medium or format, even for commercial purposes.
  - If others remix, adapt, or build upon the material, they must license the
    modified material under identical terms.

Version 2026.05 notes:
  - Fixed: Placeholder for fixes in this release.
  - New: Placeholder for new behavior in this release.

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
  - Writes tab-separated output with columns:
      Time    Locator Name

Arguments:
  als_path
      Path to the Ableton .als file.

      Example:
        python3 extract_locators.py path/to/song.als

  --add-offset=SECONDS
      Add SECONDS to every locator after normalization.
      Fractional and negative values are accepted.

      Examples:
        python3 extract_locators.py song.als --add-offset=27
        python3 extract_locators.py song.als --add-offset=27.5
        python3 extract_locators.py song.als --add-offset=-3.25

  --precision=DECIMALS
      Number of decimal places to show in the seconds portion of each timestamp.
      Default: 0

      Examples:
        python3 extract_locators.py song.als --precision=0
        python3 extract_locators.py song.als --precision=1
        python3 extract_locators.py song.als --precision=3

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
        python3 extract_locators.py song.als --strip-keys

  --output=PATH
  -o PATH
      Output TSV path.
      Default: <input filename>.txt in the current directory.

      Examples:
        python3 extract_locators.py song.als --output=locators.tsv
        python3 extract_locators.py song.als --output=adjusted_locators.tsv
        python3 extract_locators.py song.als -o locators.tsv

  --mixcloud=PATH
  -m PATH
      Also write a Mixcloud-compatible timestamped tracklist.

      Format:
        MM:SS Locator Name

      Examples:
        python3 extract_locators.py song.als --mixcloud=mixcloud.txt
        python3 extract_locators.py song.als -m mixcloud.txt

Combined examples:
  python3 extract_locators.py song.als --add-offset=27.5 --precision=2 --output=adjusted_locators.tsv
  python3 extract_locators.py song.als --add-offset=27 --mixcloud=mixcloud.txt
  python3 extract_locators.py song.als --add-offset=27 --strip-keys --output=locators.tsv --mixcloud=mixcloud.txt
"""

import argparse
import gzip
import math
import os
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET
import zlib


SCRIPT_NAME = "extract_locators.py"
DEFAULT_BPM = 120.0
TEMPO_AUTOMATION_POINTEE_ID = "8"

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
    print(colorize(SCRIPT_NAME, FG_BLUE, stream=stream, bold=True), file=stream)
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


def float_attribute(element, attribute_name, default, context):
    """
    Read a float-valued XML attribute with a helpful error if it is malformed.

    Ableton stores beats, tempo values, and locator positions as XML attributes.
    A missing attribute uses the caller's default; a present but non-numeric
    attribute is treated as a corrupt/unexpected session file.
    """
    if element is None:
        return default

    raw_value = element.get(attribute_name)

    if raw_value is None:
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise LocatorToolError(
            "Ableton file contains a numeric value this tool could not read.",
            [(context, raw_value)],
        ) from exc


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


def read_als_xml_bytes(als_path):
    """
    Read an Ableton .als file as XML bytes.

    Ableton .als files are commonly gzip-compressed XML, but some may be plain
    XML. The magic bytes are more reliable than the file extension, so detection
    is based on the first two bytes rather than on the name of the file.
    """
    try:
        with als_path.open("rb") as als_file:
            first_two_bytes = als_file.read(2)
            als_file.seek(0)

            if first_two_bytes == b"\x1f\x8b":
                with gzip.GzipFile(fileobj=als_file) as gzipped_file:
                    return gzipped_file.read()

            return als_file.read()
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
    except OSError as exc:
        raise LocatorToolError(
            "Unable to read the Ableton session file.",
            [("path", display_path(als_path)), ("detail", exc)],
        ) from exc


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


def tempo_events_from_xml(root):
    """
    Extract tempo automation events from Ableton XML.

    In Ableton's XML, tempo automation is identified by PointeeId=8. Each event
    stores the beat position in Time and the tempo in Value.
    """
    tempo_changes = []

    for envelope in root.findall(".//AutomationEnvelope"):
        pointee_id = envelope.find(".//EnvelopeTarget/PointeeId")

        if pointee_id is None or pointee_id.get("Value") != TEMPO_AUTOMATION_POINTEE_ID:
            continue

        for event in envelope.findall(".//Automation/Events/FloatEvent"):
            beat = float_attribute(event, "Time", 0.0, "tempo event beat")
            bpm = float_attribute(event, "Value", DEFAULT_BPM, "tempo event bpm")

            require_positive_bpm(bpm, "tempo event bpm")

            if beat >= 0:
                tempo_changes.append((beat, bpm))

    if not tempo_changes:
        return [(0.0, DEFAULT_BPM)]

    return sorted(tempo_changes, key=lambda item: item[0])


def build_beat_to_seconds_converter(tempo_changes):
    """
    Create a converter that maps Ableton beat positions to elapsed seconds.

    The converter integrates over every tempo segment once, caches the elapsed
    seconds at each tempo event, then uses those cached anchors to convert
    arbitrary locator beats efficiently.
    """
    seconds_at_beat = {tempo_changes[0][0]: 0.0}
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
        seconds_at_beat[current_beat] = total_seconds

    def beat_to_seconds(beat):
        first_beat, first_bpm = tempo_changes[0]

        if beat <= first_beat:
            require_positive_bpm(first_bpm, "first tempo event bpm")
            return (beat - first_beat) * (60.0 / first_bpm)

        for index in range(1, len(tempo_changes)):
            segment_start_beat, segment_start_bpm = tempo_changes[index - 1]
            segment_end_beat, segment_end_bpm = tempo_changes[index]

            if beat > segment_end_beat:
                continue

            segment_beats = beat - segment_start_beat

            if abs(segment_end_bpm - segment_start_bpm) < 1e-9:
                return seconds_at_beat[segment_start_beat] + segment_beats * (
                    60.0 / segment_start_bpm
                )

            slope = (segment_end_bpm - segment_start_bpm) / (
                segment_end_beat - segment_start_beat
            )
            bpm_at_beat = segment_start_bpm + slope * segment_beats

            require_positive_bpm(bpm_at_beat, "interpolated tempo bpm")

            return seconds_at_beat[segment_start_beat] + (60.0 / slope) * math.log(
                bpm_at_beat / segment_start_bpm
            )

        last_beat, last_bpm = tempo_changes[-1]
        require_positive_bpm(last_bpm, "last tempo event bpm")
        return seconds_at_beat[last_beat] + (beat - last_beat) * (60.0 / last_bpm)

    return beat_to_seconds


def extract_locators_with_ramps(als_path, add_offset=0.0, strip_keys=False):
    """
    Extract locators from an ALS file and return them as (seconds, name) tuples.

    Returned seconds are normalized so the earliest locator is zero, then
    shifted by the user-requested add_offset.
    """
    xml_data = read_als_xml_bytes(als_path)

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        raise LocatorToolError(
            "Ableton session file could not be parsed as XML.",
            [("path", display_path(als_path)), ("detail", exc)],
        ) from exc

    tempo_changes = tempo_events_from_xml(root)
    beat_to_seconds = build_beat_to_seconds_converter(tempo_changes)

    locators = []
    earliest_seconds = float("inf")

    for locator in root.iter("Locator"):
        name_element = locator.find(".//Name")
        time_element = locator.find(".//Time")

        name = (
            name_element.get("Value")
            if name_element is not None and name_element.get("Value") is not None
            else "Unnamed Locator"
        )

        if strip_keys:
            name = strip_key_prefix(name)

        beat = float_attribute(time_element, "Value", 0.0, "locator beat")
        seconds = beat_to_seconds(beat)

        earliest_seconds = min(earliest_seconds, seconds)
        locators.append((seconds, name))

    if not locators:
        return []

    normalized_locators = [
        (seconds - earliest_seconds + add_offset, name) for seconds, name in locators
    ]
    normalized_locators.sort(key=lambda item: item[0])

    return normalized_locators


def ensure_parent_directory(path):
    """Fail early with a clear message when the output directory is missing."""
    parent = path.parent

    if parent and not parent.exists():
        raise LocatorToolError(
            "Output directory does not exist.",
            [("path", display_path(parent))],
        )


def write_tsv(locators, output_tsv, precision=0):
    """Write locators to a tab-separated file."""
    ensure_parent_directory(output_tsv)

    try:
        with output_tsv.open("w", encoding="utf-8") as out:
            out.write("Time\tLocator Name\n")

            for seconds, name in locators:
                timestamp = format_timestamp(seconds, precision=precision)
                out.write(f"{timestamp}\t{name}\n")
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


def write_mixcloud_tracklist(locators, mixcloud_path):
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
            for seconds, name in locators:
                timestamp = format_timestamp(seconds, precision=0)
                out.write(f"{timestamp} {name}\n")
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


def parse_args():
    """Parse command-line arguments and validate simple numeric options."""
    parser = LocatorArgumentParser(
        description="Extract Ableton locators to TSV with tempo-ramp-aware timing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 extract_locators.py song.als\n"
            "  python3 extract_locators.py song.als --output=locators.tsv\n"
            "  python3 extract_locators.py song.als --mixcloud=mixcloud.txt\n"
            "  python3 extract_locators.py song.als --add-offset=27 --strip-keys --output=locators.tsv --mixcloud=mixcloud.txt"
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
        "-m",
        "--mixcloud",
        metavar="PATH",
        help="Also write a Mixcloud-compatible tracklist to PATH.",
    )

    args = parser.parse_args()

    if args.precision < 0:
        parser.error("--precision must be 0 or greater")

    return args


def run(args):
    """Run the extraction workflow and return the values needed for reporting."""
    als_path = user_path(args.als_path)
    output_path = user_path(args.output) if args.output else default_output_path(als_path)
    mixcloud_path = user_path(args.mixcloud) if args.mixcloud else None

    started_at = time.perf_counter()

    locators = extract_locators_with_ramps(
        als_path,
        add_offset=args.add_offset,
        strip_keys=args.strip_keys,
    )

    if not locators:
        return {
            "status": "no locators",
            "status_color": FG_YELLOW,
            "rows": [
                ("input", display_path(als_path)),
                ("locators", 0),
                ("elapsed", f"{time.perf_counter() - started_at:.2f}s"),
            ],
            "exit_code": 0,
        }

    write_tsv(locators, output_tsv=output_path, precision=args.precision)

    rows = [
        ("input", display_path(als_path)),
        ("locators", len(locators)),
        ("output", display_path(output_path)),
    ]

    if mixcloud_path:
        write_mixcloud_tracklist(locators, mixcloud_path=mixcloud_path)
        rows.append(("mixcloud", display_path(mixcloud_path)))

    rows.append(("elapsed", f"{time.perf_counter() - started_at:.2f}s"))

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
