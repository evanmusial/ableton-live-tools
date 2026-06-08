#!/usr/bin/env python3

"""
extract_timeline.py
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
  - Precomputes time-signature section positions so repeated timeline rows do
    not recalculate section-start labels.
  - Uses a compact timing context object instead of per-row timing dictionaries.
  - Builds optional details dictionaries only when the selected output columns
    include details.
  - Reuses a generated bar row's timing values for the matching beat-one row in
    beat-grid exports.
  - Against main on RYM_2026-03.als, final median benchmark results showed no
    material regression: locator-only improved by about 2.3%, beat-grid core
    improved by about 4.2%, and full TSV + JSON moved about 1.5% slower.

Version 2026.05.31 notes:
  - Added tag-name fast paths to the XML start and end handlers so unrelated
    Ableton tags skip deeper parser-state checks.
  - Replaced fixed tuple-slice path checks with direct parent/depth checks.
  - Added target-aware parsing so lightweight exports can skip clip/sample
    structures when selected event types and columns do not need them.
  - Added standard-library unittest CLI validation under tests/.
  - Added scripts/benchmark_validation.py for repeatable validation benchmarks.
  - On the RYM_2026-03.als locator-only benchmark, median elapsed time improved
    from 1.568s to 0.698s, about 55.5% faster.
  - On the RYM_2026-03.als beat-grid core benchmark, median elapsed time
    improved from 1.631s to 0.773s, about 52.6% faster.
  - On the RYM_2026-03.als full TSV + JSON benchmark, median elapsed time
    improved from 1.645s to 0.783s, about 52.4% faster.
  - Confirmed full timeline TSV and core beat-grid TSV output remain
    byte-identical to main. Full timeline JSON differs only in expected
    script-version metadata.

Version 2026.05.29 notes:
  - Added docs/Performance and Output Roadmap.md with profiling baselines,
    optimization candidates, output-format candidates, and validation notes.
  - Re-ran the usual validation checks against examples/validation/RYM_2026-03.als
    on Python 3.14.5.
  - Confirmed locator timeline rows match Extract Locators metadata at matching
    precision.
  - Confirmed full TSV/JSON timeline export and beat-grid timeline export
    complete successfully.
  - Confirmed CLI success and missing-file error paths return script-friendly
    exit codes.
  - Tested with Ableton Live 12.4.1, released May 28, 2026.

Version 2026.05.21 notes:
  - Initial Extract Timeline release.
  - Exports an interleaved, beat-sorted Ableton Live arrangement timeline with
    tempo events, tempo-ramp intervals, time signatures, detected key/scale
    events, locators, clip starts, clip ends, and a detected song-end row.
  - Adds optional bar and beat grid rows with --grid=bars or --grid=beats.
  - Calculates real wall-clock time with fractional seconds while respecting
    tempo changes and linear tempo ramps.
  - Calculates sample indexes when a project/sample rate can be detected or
    supplied by the user.
  - Detects sample-rate metadata from Ableton sample references and, when the
    referenced audio files are available, detects sample rate and bit depth from
    WAV, AIFF, AIFC, and FLAC headers.
  - Writes TSV and optional compact or human-readable JSON.

What this script does:
  Ableton Live .als files are XML documents, usually gzip-compressed. This tool
  streams that XML and builds a single chronological event list for the
  arrangement. The list is intended for technical review, cue sheets, archive
  notes, post-production validation, and any workflow that needs a precise map
  from Ableton beats to real elapsed time.

Timing model:
  - Ableton stores arrangement positions in quarter-note beat units.
  - Constant tempo segments convert with beats * 60 / BPM.
  - Linear tempo ramps integrate 60 / BPM over the ramp interval. That is why
    the ramp math uses a logarithm instead of a simple average tempo.
  - Time signatures affect musical position labels and grid generation, but
    they do not affect elapsed seconds directly.
  - Sample indexes are derived after elapsed seconds are known:
        sample_index = round(wall_seconds * sample_rate)
    Bit depth is useful metadata, but it does not change the sample-index math.

Default output columns:
  wall_time
  wall_seconds
  sample_index
  event_type
  song_position
  absolute_beats
  tempo_bpm
  time_signature
  key
  name
  value
  event_id
  source
  source_path
  sample_rate
  bit_depth
  duration_seconds
  details

Arguments:
  als_path
      Path to the Ableton .als file.

      Example:
        python3 src/extract_timeline.py path/to/song.als

  --output=PATH
  -o PATH
      Output TSV path.
      Default: <input filename>.timeline.tsv in the current directory.

      Examples:
        python3 src/extract_timeline.py song.als --output=song.timeline.tsv
        python3 src/extract_timeline.py song.als -o song.timeline.tsv

  --json=PATH
  -j PATH
      Also write a JSON timeline export.

      Examples:
        python3 src/extract_timeline.py song.als --json=song.timeline.json
        python3 src/extract_timeline.py song.als -j song.timeline.json

  --json-format=pretty|compact
      Choose whether JSON is human-readable or compact.
      Default: pretty

      Examples:
        python3 src/extract_timeline.py song.als --json=song.timeline.json --json-format=pretty
        python3 src/extract_timeline.py song.als --json=song.timeline.json --json-format=compact

  --grid=none|bars|beats
      Add musical grid rows to the exported timeline.
      Default: none

      none:
        Do not emit grid rows.

      bars:
        Emit one bar row at every bar start.

      beats:
        Emit bar rows and beat rows. Bar starts and beat-one rows share the same
        timing fields but remain separate rows, so the output stays one event
        per row while grouping simultaneous events together.

      Examples:
        python3 src/extract_timeline.py song.als --grid=bars
        python3 src/extract_timeline.py song.als --grid=beats

  --precision=DECIMALS
      Decimal places for wall_time, wall_seconds, beats, tempo, and durations.
      Default: 6

      Examples:
        python3 src/extract_timeline.py song.als --precision=3
        python3 src/extract_timeline.py song.als --precision=9

  --sample-rate=HZ
      Use HZ for sample-index calculations. When omitted, the tool uses an
      automatically detected sample rate only if the detected rate is
      unambiguous.

      Example:
        python3 src/extract_timeline.py song.als --sample-rate=48000

  --end-beat=BEAT
      Override the beat where grid generation and the song-end row stop.
      By default, the end beat is detected from locators, tempo events, time
      signature events, and arrangement clip ends.

      Example:
        python3 src/extract_timeline.py song.als --grid=beats --end-beat=4096

  --event-types=LIST
      Select comma-separated event types.
      Default: all

      Available event types:
        tempo
        tempo_ramp
        time_signature
        key
        locator
        clip_start
        clip_end
        song_end

      Examples:
        python3 src/extract_timeline.py song.als --event-types=tempo,time_signature,locator
        python3 src/extract_timeline.py song.als --event-types=all

  --columns=LIST
      Select comma-separated TSV/JSON columns.
      Default: all

      Example:
        python3 src/extract_timeline.py song.als --columns=wall_time,event_type,name,value

  --no-heading-row
  --no-header
      Omit the TSV heading row entirely.

      Example:
        python3 src/extract_timeline.py song.als --no-heading-row

Combined examples:
  python3 src/extract_timeline.py song.als --grid=beats --json=song.timeline.json
  python3 src/extract_timeline.py song.als --event-types=tempo,time_signature,key,locator --output=core.tsv
  python3 src/extract_timeline.py song.als --grid=bars --precision=3 --sample-rate=48000

CLI reporting:
  - Reports are headed "Timeline Extraction Results".
  - Every written file is listed with the label "output".
  - Elapsed processing time is shown with three decimal places.
  - Successful runs exit with status code 0.
  - Runtime/user-data errors exit with status code 1.
  - Command-line argument errors exit with status code 2.
"""

import argparse
import bisect
import csv
from dataclasses import dataclass, field
import gzip
import json
import math
import os
from pathlib import Path
import struct
import sys
import time
from typing import NamedTuple, Optional
import xml.parsers.expat as expat
import zlib


SCRIPT_NAME = "extract_timeline.py"
SCRIPT_VERSION = "2026.06.07"
REPORT_TITLE = "Timeline Extraction Results"

DEFAULT_BPM = 120.0
DEFAULT_PRECISION = 6
DEFAULT_TIME_SIGNATURE_VALUE = 201
TEMPO_AUTOMATION_POINTEE_ID = "8"
TIME_SIGNATURE_AUTOMATION_POINTEE_ID = "10"
TIME_SIGNATURE_DENOMINATORS = (1, 2, 4, 8, 16)

# The XML parser sees every ALS element. These are the only start tags that can
# affect timeline output, so the handler can return quickly for the many Ableton
# tags that do not influence tempo, signatures, keys, locators, clips, or media
# metadata. The full path is still tracked for all tags because interesting
# children rely on their parent context.
TIMELINE_XML_INTERESTING_TAGS = frozenset(
    (
        "Ableton",
        "AutomationEnvelope",
        "PointeeId",
        "FloatEvent",
        "EnumEvent",
        "Manual",
        "Root",
        "Name",
        "InKey",
        "Locator",
        "Time",
        "AudioClip",
        "MidiClip",
        "CurrentStart",
        "CurrentEnd",
        "IsInKey",
        "SampleRef",
        "FileRef",
        "DefaultSampleRate",
        "DefaultDuration",
        "Path",
        "RelativePath",
    )
)
TIMELINE_XML_INTERESTING_END_TAGS = frozenset(
    (
        "AutomationEnvelope",
        "Locator",
        "AudioClip",
        "MidiClip",
        "SampleRef",
        "FileRef",
    )
)

# Ableton stores scale roots as chromatic semitone indexes. The enharmonic
# spellings below follow a simple sharp-based display so output is stable across
# systems and shells.
ROOT_NOTE_NAMES = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)

# Live's scale-name integer is not documented as part of a public ALS file
# format. The first two IDs are common and useful enough to decode; unknown IDs
# are still exported as raw scale IDs instead of being guessed.
KNOWN_SCALE_NAMES = {
    0: "Major",
    1: "Minor",
}

ALL_EVENT_TYPES = (
    "tempo",
    "tempo_ramp",
    "time_signature",
    "key",
    "locator",
    "clip_start",
    "clip_end",
    "song_end",
)

DEFAULT_EVENT_TYPES = ALL_EVENT_TYPES

EVENT_SORT_ORDER = {
    "time_signature": 10,
    "tempo": 20,
    "tempo_ramp": 21,
    "key": 30,
    "bar": 40,
    "beat": 41,
    "locator": 50,
    "clip_start": 60,
    "clip_end": 61,
    "song_end": 90,
}

ALL_COLUMNS = (
    "wall_time",
    "wall_seconds",
    "sample_index",
    "event_type",
    "song_position",
    "absolute_beats",
    "tempo_bpm",
    "time_signature",
    "key",
    "name",
    "value",
    "event_id",
    "source",
    "source_path",
    "sample_rate",
    "bit_depth",
    "duration_seconds",
    "details",
)

DEFAULT_COLUMNS = ALL_COLUMNS

COLUMN_HEADERS = {
    "wall_time": "Wall Time",
    "wall_seconds": "Wall Seconds",
    "sample_index": "Sample Index",
    "event_type": "Event Type",
    "song_position": "Song Position",
    "absolute_beats": "Absolute Beats",
    "tempo_bpm": "Tempo (BPM)",
    "time_signature": "Time Signature",
    "key": "Key",
    "name": "Name",
    "value": "Value",
    "event_id": "Event ID",
    "source": "Source",
    "source_path": "Source Path",
    "sample_rate": "Sample Rate",
    "bit_depth": "Bit Depth",
    "duration_seconds": "Duration Seconds",
    "details": "Details",
}

COLUMN_ALIASES = {
    "time": "wall_time",
    "timestamp": "wall_time",
    "seconds": "wall_seconds",
    "wall": "wall_time",
    "wall_clock": "wall_time",
    "sample": "sample_index",
    "samples": "sample_index",
    "type": "event_type",
    "event": "event_type",
    "position": "song_position",
    "bar_beat": "song_position",
    "bar.beat": "song_position",
    "bar.beat.sixteenth": "song_position",
    "beat": "absolute_beats",
    "beats": "absolute_beats",
    "bpm": "tempo_bpm",
    "tempo": "tempo_bpm",
    "time_sig": "time_signature",
    "timesig": "time_signature",
    "signature": "time_signature",
    "id": "event_id",
    "path": "source_path",
    "sr": "sample_rate",
    "rate": "sample_rate",
    "bits": "bit_depth",
    "duration": "duration_seconds",
}

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


class TimelineToolError(Exception):
    """A user-facing problem that should be reported without a traceback."""

    def __init__(self, problem, details=None):
        super().__init__(problem)
        self.problem = problem
        self.details = details or []


class TimelineArgumentParser(argparse.ArgumentParser):
    """
    ArgumentParser with the same compact reporting style used by runtime errors.

    This keeps parse failures visually aligned with XML, filesystem, and
    validation failures, which matters for people wiring the command into CI or
    batch scripts.
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
class TempoEvent:
    """A tempo value that becomes active at an Ableton beat position."""

    beat: float
    bpm: float


@dataclass(frozen=True)
class TimeSignatureEvent:
    """A time signature that becomes active at an Ableton beat position."""

    beat: float
    numerator: int
    denominator: int


@dataclass(frozen=True)
class LocatorSource:
    """Arrangement locator data exactly as it appears in the Live set."""

    locator_id: str
    beat: float
    name: str


@dataclass(frozen=True)
class ScaleInfo:
    """A root/scale pair from Live's ScaleInformation XML block."""

    root: Optional[int] = None
    name: Optional[int] = None
    in_key: Optional[bool] = None


@dataclass
class ClipSource:
    """Arrangement clip timing and media metadata gathered during XML parsing."""

    clip_id: str
    clip_type: str
    start_beat: Optional[float] = None
    end_beat: Optional[float] = None
    name: str = "Unnamed Clip"
    scale: ScaleInfo = field(default_factory=ScaleInfo)
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    default_duration_samples: Optional[int] = None
    path: str = ""
    relative_path: str = ""
    existing_audio_path: str = ""


@dataclass(frozen=True)
class TimelineRawData:
    """Raw arrangement information extracted from the Ableton XML stream."""

    tempo_events: tuple[TempoEvent, ...]
    time_signature_events: tuple[TimeSignatureEvent, ...]
    manual_time_signature_value: Optional[int]
    locators: tuple[LocatorSource, ...]
    clips: tuple[ClipSource, ...]
    session_scale: ScaleInfo
    creator: str
    major_version: str
    minor_version: str


@dataclass(frozen=True)
class TimelineParseOptions:
    """
    Control which optional XML regions are collected during timeline parsing.

    Tempo, time-signature, locator, and top-level Ableton metadata are always
    gathered because they are cheap and central to the timing model. Clip and
    media regions are much larger, so callers can skip them when the selected
    export shape does not need that data.
    """

    collect_session_scale: bool = True
    collect_clips: bool = True
    collect_clip_media: bool = True
    inspect_audio_files: bool = True


@dataclass(frozen=True)
class TimelineMetadata:
    """Metadata shared by every exported timeline event."""

    sample_rate: Optional[int]
    sample_rate_source: str
    detected_sample_rates: tuple[int, ...]
    detected_bit_depths: tuple[int, ...]
    bit_depth_source: str
    end_beat: float
    end_seconds: float
    grid: str
    event_types: tuple[str, ...]
    ableton_creator: str
    ableton_major_version: str
    ableton_minor_version: str


class TimeSignatureContext(NamedTuple):
    """Computed musical-position values for one Ableton beat."""

    event: TimeSignatureEvent
    bar_number: int
    displayed_beat: int
    sixteenth: int
    song_position: str
    time_signature: str
    time_signature_section_start: str


@dataclass
class TimelineEvent:
    """
    One exported timeline row.

    The first group of fields is the shared timing spine. The second group is
    intentionally generic so many event types can live in the same TSV without
    adding sparse one-off columns for every possible Ableton concept.
    """

    event_type: str
    beat: float
    seconds: float
    sample_index: Optional[int]
    song_position: str
    bar_number: int
    displayed_beat: int
    sixteenth: int
    tempo_bpm: float
    time_signature: str
    key: str = ""
    name: str = ""
    value: str = ""
    event_id: str = ""
    source: str = ""
    source_path: str = ""
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    duration_seconds: Optional[float] = None
    details: Optional[dict] = None
    sequence: int = 0


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


def print_kv(label, value, *, stream=sys.stdout):
    """Print one indented key/value line with a stable label width."""
    label_text = colorize(f"{label:<10}", FG_MUTED, stream=stream)
    value_text = colorize(str(value), FG_VALUE, stream=stream)
    print(f"  {label_text} {value_text}", file=stream)


def print_report(status, rows, *, stream=sys.stdout, status_color=FG_GREEN):
    """Print a compact, aligned status report."""
    print(colorize(REPORT_TITLE, FG_BLUE, stream=stream, bold=True), file=stream)
    print_kv("status", colorize(status, status_color, stream=stream), stream=stream)

    for label, value in rows:
        print_kv(label, value, stream=stream)


def display_path(path):
    """Return an absolute path string suitable for terminal reporting."""
    return str(Path(path).expanduser().resolve(strict=False))


def user_path(raw_path):
    """Expand a command-line path relative to the current working directory."""
    path = Path(raw_path).expanduser()

    if path.is_absolute():
        return path

    return Path.cwd() / path


def default_output_path(als_path):
    """Build the default TSV path from the input session filename."""
    return Path.cwd() / f"{als_path.name}.timeline.tsv"


def format_elapsed(started_at):
    """Return elapsed processing time with stable CLI precision."""
    return f"{time.perf_counter() - started_at:.3f}s"


def require_positive_bpm(bpm, context):
    """Reject impossible tempo values before they reach logarithmic math."""
    if bpm <= 0:
        raise TimelineToolError(
            "Ableton file contains a tempo value that is zero or negative.",
            [(context, bpm)],
        )


def float_value(raw_value, default, context):
    """Read a float-valued XML attribute string with a helpful error."""
    if raw_value is None:
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise TimelineToolError(
            "Ableton file contains a numeric value this tool could not read.",
            [(context, raw_value)],
        ) from exc


def int_value(raw_value, default, context):
    """Read an integer-like XML attribute string with a helpful error."""
    if raw_value is None:
        return default

    try:
        return int(float(raw_value))
    except ValueError as exc:
        raise TimelineToolError(
            "Ableton file contains an integer value this tool could not read.",
            [(context, raw_value)],
        ) from exc


def bool_value(raw_value, default=False):
    """Read Ableton's lowercase true/false XML attributes."""
    if raw_value is None:
        return default

    return raw_value.strip().lower() == "true"


def decode_time_signature_value(encoded_value):
    """
    Decode Ableton's packed main time-signature parameter value.

    Live stores the main time signature as a single enum value. The observed
    range is 0..494, which maps to 99 possible numerators across five supported
    denominators. For example, value 201 decodes to 4/4.
    """
    denominator_index, numerator_index = divmod(encoded_value, 99)

    if denominator_index >= len(TIME_SIGNATURE_DENOMINATORS):
        raise TimelineToolError(
            "Ableton file contains a time signature value this tool could not decode.",
            [("time signature value", encoded_value)],
        )

    return numerator_index + 1, TIME_SIGNATURE_DENOMINATORS[denominator_index]


def format_decimal(value, precision=DEFAULT_PRECISION):
    """Format a number compactly while preserving the requested precision."""
    if value is None:
        return ""

    rounded = round(value, precision)

    if abs(rounded) < 10 ** (-precision):
        rounded = 0.0

    text = f"{rounded:.{precision}f}"
    return text.rstrip("0").rstrip(".")


def format_wall_time(total_seconds, precision=DEFAULT_PRECISION):
    """Format elapsed seconds as HH:MM:SS.ssssss with configurable precision."""
    total_seconds = max(0.0, total_seconds)
    rounded_seconds = round(total_seconds, precision)
    hours = int(rounded_seconds // 3600)
    minutes = int((rounded_seconds - hours * 3600) // 60)
    seconds = rounded_seconds - hours * 3600 - minutes * 60

    # Rounding can produce 60.000000 seconds or minutes. Normalize the display
    # so downstream tools never see impossible clock fields.
    if seconds >= 60.0:
        minutes += 1
        seconds -= 60.0

    if minutes >= 60:
        hours += 1
        minutes -= 60

    if precision == 0:
        return f"{hours:02}:{minutes:02}:{int(seconds):02}"

    seconds_width = 3 + precision
    return f"{hours:02}:{minutes:02}:{seconds:0{seconds_width}.{precision}f}"


def scale_label(scale_info):
    """Return a readable key/scale label while preserving unknown raw IDs."""
    if scale_info.root is None and scale_info.name is None:
        return ""

    if scale_info.root is None:
        root = "unknown root"
    else:
        root = ROOT_NOTE_NAMES[scale_info.root % len(ROOT_NOTE_NAMES)]

    if scale_info.name is None:
        scale = "unknown scale"
    else:
        scale = KNOWN_SCALE_NAMES.get(scale_info.name, f"scale_id={scale_info.name}")

    if scale_info.in_key is False:
        return f"{root} {scale} (scale mode off)"

    return f"{root} {scale}"


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


def parse_als_timeline_data(als_path, parse_options=None):
    """
    Extract timeline-relevant raw data from an Ableton .als file.

    Ableton .als files are commonly gzip-compressed XML, but some may be plain
    XML. The magic bytes are more reliable than the file extension, so detection
    is based on the first two bytes rather than on the filename.
    """
    if parse_options is None:
        parse_options = TimelineParseOptions()

    try:
        with als_path.open("rb") as als_file:
            first_two_bytes = als_file.read(2)
            als_file.seek(0)

            if first_two_bytes == b"\x1f\x8b":
                with gzip.GzipFile(fileobj=als_file) as gzipped_file:
                    raw_data = parse_als_xml_stream(
                        gzipped_file,
                        parse_options=parse_options,
                    )
            else:
                raw_data = parse_als_xml_stream(
                    als_file,
                    parse_options=parse_options,
                )

        if parse_options.inspect_audio_files:
            return enrich_clip_media(raw_data, als_path)

        return raw_data
    except FileNotFoundError as exc:
        raise TimelineToolError(
            "Ableton session file was not found.",
            [("path", display_path(als_path))],
        ) from exc
    except PermissionError as exc:
        raise TimelineToolError(
            "Permission denied while reading the Ableton session file.",
            [("path", display_path(als_path))],
        ) from exc
    except (gzip.BadGzipFile, EOFError, zlib.error) as exc:
        raise TimelineToolError(
            "Ableton session file looks gzipped, but it could not be decompressed.",
            [("path", display_path(als_path))],
        ) from exc
    except expat.ExpatError as exc:
        raise TimelineToolError(
            "Ableton session file could not be parsed as XML.",
            [
                ("path", display_path(als_path)),
                ("line", exc.lineno),
                ("column", exc.offset),
                ("detail", exc),
            ],
        ) from exc
    except OSError as exc:
        raise TimelineToolError(
            "Unable to read the Ableton session file.",
            [("path", display_path(als_path)), ("detail", exc)],
        ) from exc


def parse_als_xml_stream(xml_stream, chunk_size=1024 * 1024, parse_options=None):
    """
    Stream-parse Ableton XML and collect only timeline-relevant data.

    Large Live sets can decompress into hundreds of megabytes of XML. Expat
    lets the script watch for a small number of important paths and discard the
    rest as it flows past.
    """
    if parse_options is None:
        parse_options = TimelineParseOptions()

    path = []
    tempo_events = []
    time_signature_events = []
    manual_time_signature_value = None
    locators = []
    clips = []
    session_scale_values = {"root": None, "name": None, "in_key": None}
    ableton_attrs = {"creator": "", "major_version": "", "minor_version": ""}
    state = {
        "inside_automation_candidate": False,
        "automation_pointee_id": None,
        "automation_float_events": None,
        "automation_enum_events": None,
        "inside_locator": False,
        "locator_id": None,
        "locator_name": None,
        "locator_beat": None,
        "current_clip": None,
        "current_clip_type": None,
        "inside_sample_ref": False,
        "sample_ref_depth": 0,
        "inside_sample_file_ref": False,
        "sample_file_ref_depth": 0,
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

    def at_session_scale_child(tag_name):
        return (
            len(path) >= 4
            and path[-4] == "Ableton"
            and path[-3] == "LiveSet"
            and path[-2] == "ScaleInformation"
            and path[-1] == tag_name
        )

    def at_session_in_key():
        return (
            len(path) >= 3
            and path[-3] == "Ableton"
            and path[-2] == "LiveSet"
            and path[-1] == "InKey"
        )

    def start_element(name, attrs):
        nonlocal manual_time_signature_value

        path.append(name)

        if name not in TIMELINE_XML_INTERESTING_TAGS:
            return

        if name == "Ableton":
            ableton_attrs["creator"] = attrs.get("Creator", "")
            ableton_attrs["major_version"] = attrs.get("MajorVersion", "")
            ableton_attrs["minor_version"] = attrs.get("MinorVersion", "")
            return

        if name == "AutomationEnvelope":
            state["inside_automation_candidate"] = True
            state["automation_pointee_id"] = None
            state["automation_float_events"] = []
            state["automation_enum_events"] = []
            return

        if state["inside_automation_candidate"]:
            if name == "PointeeId" and parent_is("EnvelopeTarget"):
                state["automation_pointee_id"] = attrs.get("Value")
                return

            if name == "FloatEvent" and parent_chain_is("Events", "Automation"):
                state["automation_float_events"].append(
                    (attrs.get("Time"), attrs.get("Value"))
                )
                return

            if name == "EnumEvent" and parent_chain_is("Events", "Automation"):
                state["automation_enum_events"].append(
                    (attrs.get("Time"), attrs.get("Value"))
                )
                return

        if name == "Manual" and at_main_time_signature_manual():
            manual_time_signature_value = int_value(
                attrs.get("Value"),
                DEFAULT_TIME_SIGNATURE_VALUE,
                "manual time signature value",
            )
            return

        if (
            parse_options.collect_session_scale
            and name == "Root"
            and at_session_scale_child("Root")
        ):
            session_scale_values["root"] = int_value(
                attrs.get("Value"),
                None,
                "session scale root",
            )
            return

        if (
            parse_options.collect_session_scale
            and name == "Name"
            and at_session_scale_child("Name")
        ):
            session_scale_values["name"] = int_value(
                attrs.get("Value"),
                None,
                "session scale name",
            )
            return

        if (
            parse_options.collect_session_scale
            and name == "InKey"
            and at_session_in_key()
        ):
            session_scale_values["in_key"] = bool_value(attrs.get("Value"))
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
            return

        if parse_options.collect_clips and name in ("AudioClip", "MidiClip"):
            clip_type = "audio" if name == "AudioClip" else "midi"
            state["current_clip"] = ClipSource(
                clip_id=attrs.get("Id", ""),
                clip_type=clip_type,
                start_beat=float_value(attrs.get("Time"), None, "clip start beat"),
            )
            state["current_clip_type"] = name
            return

        current_clip = state["current_clip"]

        if parse_options.collect_clips and current_clip is not None:
            is_direct_clip_child = (
                state["current_clip_type"] is not None
                and parent_is(state["current_clip_type"])
            )

            if is_direct_clip_child and name == "CurrentStart":
                current_clip.start_beat = float_value(
                    attrs.get("Value"),
                    current_clip.start_beat,
                    "clip current start beat",
                )
                return

            if is_direct_clip_child and name == "CurrentEnd":
                current_clip.end_beat = float_value(
                    attrs.get("Value"),
                    current_clip.end_beat,
                    "clip current end beat",
                )
                return

            if is_direct_clip_child and name == "Name":
                current_clip.name = attrs.get("Value") or current_clip.name
                return

            if parent_is("ScaleInformation") and name == "Root":
                current_clip.scale = ScaleInfo(
                    root=int_value(attrs.get("Value"), None, "clip scale root"),
                    name=current_clip.scale.name,
                    in_key=current_clip.scale.in_key,
                )
                return

            if parent_is("ScaleInformation") and name == "Name":
                current_clip.scale = ScaleInfo(
                    root=current_clip.scale.root,
                    name=int_value(attrs.get("Value"), None, "clip scale name"),
                    in_key=current_clip.scale.in_key,
                )
                return

            if is_direct_clip_child and name == "IsInKey":
                current_clip.scale = ScaleInfo(
                    root=current_clip.scale.root,
                    name=current_clip.scale.name,
                    in_key=bool_value(attrs.get("Value")),
                )
                return

            if not parse_options.collect_clip_media:
                return

            if name == "SampleRef":
                state["inside_sample_ref"] = True
                state["sample_ref_depth"] = len(path)
                return

            if state["inside_sample_ref"] and name == "FileRef":
                state["inside_sample_file_ref"] = True
                state["sample_file_ref_depth"] = len(path)
                return

            if state["inside_sample_ref"] and name == "DefaultSampleRate":
                current_clip.sample_rate = int_value(
                    attrs.get("Value"),
                    None,
                    "sample default sample rate",
                )
                return

            if state["inside_sample_ref"] and name == "DefaultDuration":
                current_clip.default_duration_samples = int_value(
                    attrs.get("Value"),
                    None,
                    "sample default duration",
                )
                return

            if state["inside_sample_file_ref"] and name == "Path":
                current_clip.path = attrs.get("Value") or current_clip.path
                return

            if state["inside_sample_file_ref"] and name == "RelativePath":
                current_clip.relative_path = (
                    attrs.get("Value") or current_clip.relative_path
                )
                return

    def end_element(name):
        if name not in TIMELINE_XML_INTERESTING_END_TAGS:
            path.pop()
            return

        if name == "AutomationEnvelope":
            if state["automation_pointee_id"] == TEMPO_AUTOMATION_POINTEE_ID:
                for beat_value, bpm_value in state["automation_float_events"]:
                    beat = float_value(beat_value, 0.0, "tempo event beat")
                    bpm = float_value(bpm_value, DEFAULT_BPM, "tempo event bpm")
                    require_positive_bpm(bpm, "tempo event bpm")
                    tempo_events.append(TempoEvent(beat, bpm))
            elif state["automation_pointee_id"] == TIME_SIGNATURE_AUTOMATION_POINTEE_ID:
                for beat_value, signature_value in state["automation_enum_events"]:
                    beat = float_value(beat_value, 0.0, "time signature event beat")
                    encoded_signature = int_value(
                        signature_value,
                        DEFAULT_TIME_SIGNATURE_VALUE,
                        "time signature event value",
                    )
                    numerator, denominator = decode_time_signature_value(
                        encoded_signature
                    )
                    time_signature_events.append(
                        TimeSignatureEvent(beat, numerator, denominator)
                    )

            state["inside_automation_candidate"] = False
            state["automation_pointee_id"] = None
            state["automation_float_events"] = None
            state["automation_enum_events"] = None

        elif name == "Locator":
            locators.append(
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

        elif name in ("AudioClip", "MidiClip"):
            if state["current_clip"] is not None:
                clips.append(state["current_clip"])
            state["current_clip"] = None
            state["current_clip_type"] = None
            state["inside_sample_ref"] = False
            state["sample_ref_depth"] = 0
            state["inside_sample_file_ref"] = False
            state["sample_file_ref_depth"] = 0

        if state["inside_sample_file_ref"] and len(path) == state["sample_file_ref_depth"]:
            state["inside_sample_file_ref"] = False
            state["sample_file_ref_depth"] = 0

        if state["inside_sample_ref"] and len(path) == state["sample_ref_depth"]:
            state["inside_sample_ref"] = False
            state["sample_ref_depth"] = 0

        path.pop()

    parser = expat.ParserCreate()
    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element

    for chunk in iter(lambda: xml_stream.read(chunk_size), b""):
        parser.Parse(chunk, False)

    parser.Parse(b"", True)

    return TimelineRawData(
        tempo_events=tuple(tempo_events),
        time_signature_events=tuple(time_signature_events),
        manual_time_signature_value=manual_time_signature_value,
        locators=tuple(locators),
        clips=tuple(clips),
        session_scale=ScaleInfo(
            root=session_scale_values["root"],
            name=session_scale_values["name"],
            in_key=session_scale_values["in_key"],
        ),
        creator=ableton_attrs["creator"],
        major_version=ableton_attrs["major_version"],
        minor_version=ableton_attrs["minor_version"],
    )


def candidate_audio_paths(clip, als_path):
    """Return possible filesystem paths for a clip's referenced audio file."""
    candidates = []

    if clip.path:
        candidates.append(Path(clip.path).expanduser())

    if clip.relative_path:
        relative = Path(clip.relative_path)

        if relative.is_absolute():
            candidates.append(relative)
        else:
            candidates.append(als_path.parent / relative)

    deduped = []
    seen = set()

    for candidate in candidates:
        key = str(candidate)

        if key not in seen:
            deduped.append(candidate)
            seen.add(key)

    return deduped


def enrich_clip_media(raw_data, als_path):
    """
    Add audio-header metadata to clips when referenced files are available.

    ALS files usually include DefaultSampleRate inside SampleRef, which is
    enough for global sample-index calculations when every referenced sample
    agrees. Bit depth is not reliably stored in the ALS, so the script attempts
    to read it from the source audio file when that file is reachable.
    """
    enriched_clips = []

    for clip in raw_data.clips:
        enriched = ClipSource(
            clip_id=clip.clip_id,
            clip_type=clip.clip_type,
            start_beat=clip.start_beat,
            end_beat=clip.end_beat,
            name=clip.name,
            scale=clip.scale,
            sample_rate=clip.sample_rate,
            bit_depth=clip.bit_depth,
            default_duration_samples=clip.default_duration_samples,
            path=clip.path,
            relative_path=clip.relative_path,
        )

        for candidate in candidate_audio_paths(clip, als_path):
            if not candidate.exists() or not candidate.is_file():
                continue

            metadata = read_audio_file_metadata(candidate)
            enriched.existing_audio_path = str(candidate)

            if metadata.get("sample_rate") is not None:
                enriched.sample_rate = metadata["sample_rate"]

            if metadata.get("bit_depth") is not None:
                enriched.bit_depth = metadata["bit_depth"]

            break

        enriched_clips.append(enriched)

    return TimelineRawData(
        tempo_events=raw_data.tempo_events,
        time_signature_events=raw_data.time_signature_events,
        manual_time_signature_value=raw_data.manual_time_signature_value,
        locators=raw_data.locators,
        clips=tuple(enriched_clips),
        session_scale=raw_data.session_scale,
        creator=raw_data.creator,
        major_version=raw_data.major_version,
        minor_version=raw_data.minor_version,
    )


def read_audio_file_metadata(path):
    """Dispatch to a small set of standard audio-header readers."""
    try:
        with path.open("rb") as audio_file:
            first_four = audio_file.read(4)
            audio_file.seek(0)

            if first_four == b"RIFF":
                return read_wav_metadata(audio_file)

            if first_four == b"FORM":
                return read_aiff_metadata(audio_file)

            if first_four == b"fLaC":
                return read_flac_metadata(audio_file)
    except OSError:
        return {}

    return {}


def read_wav_metadata(audio_file):
    """Read sample rate and bit depth from a RIFF/WAVE fmt chunk."""
    header = audio_file.read(12)

    if len(header) != 12 or header[8:12] != b"WAVE":
        return {}

    while True:
        chunk_header = audio_file.read(8)

        if len(chunk_header) < 8:
            return {}

        chunk_id, chunk_size = struct.unpack("<4sI", chunk_header)
        chunk_data = audio_file.read(chunk_size)

        if chunk_id == b"fmt " and len(chunk_data) >= 16:
            (
                _audio_format,
                _channels,
                sample_rate,
                _byte_rate,
                _block_align,
                bits_per_sample,
            ) = struct.unpack("<HHIIHH", chunk_data[:16])
            return {
                "sample_rate": int(sample_rate),
                "bit_depth": int(bits_per_sample),
            }

        if chunk_size % 2:
            audio_file.seek(1, os.SEEK_CUR)


def extended_80_to_float(raw):
    """Convert AIFF's 80-bit extended sample-rate number to a Python float."""
    if len(raw) != 10:
        return None

    sign = -1 if raw[0] & 0x80 else 1
    exponent = ((raw[0] & 0x7F) << 8) | raw[1]
    mantissa = int.from_bytes(raw[2:], "big")

    if exponent == 0 and mantissa == 0:
        return 0.0

    return sign * mantissa * (2 ** (exponent - 16383 - 63))


def read_aiff_metadata(audio_file):
    """Read sample rate and bit depth from an AIFF/AIFC COMM chunk."""
    header = audio_file.read(12)

    if len(header) != 12 or header[8:12] not in (b"AIFF", b"AIFC"):
        return {}

    while True:
        chunk_header = audio_file.read(8)

        if len(chunk_header) < 8:
            return {}

        chunk_id, chunk_size = struct.unpack(">4sI", chunk_header)
        chunk_data = audio_file.read(chunk_size)

        if chunk_id == b"COMM" and len(chunk_data) >= 18:
            _channels, _frames, bit_depth = struct.unpack(">hIh", chunk_data[:8])
            sample_rate = extended_80_to_float(chunk_data[8:18])
            return {
                "sample_rate": int(round(sample_rate)) if sample_rate else None,
                "bit_depth": int(bit_depth),
            }

        if chunk_size % 2:
            audio_file.seek(1, os.SEEK_CUR)


def read_flac_metadata(audio_file):
    """Read sample rate and bit depth from a FLAC STREAMINFO block."""
    if audio_file.read(4) != b"fLaC":
        return {}

    while True:
        header = audio_file.read(4)

        if len(header) < 4:
            return {}

        block_type = header[0] & 0x7F
        is_last = bool(header[0] & 0x80)
        block_size = int.from_bytes(header[1:4], "big")
        block_data = audio_file.read(block_size)

        if block_type == 0 and len(block_data) >= 18:
            packed = int.from_bytes(block_data[10:18], "big")
            sample_rate = (packed >> 44) & 0xFFFFF
            bit_depth = ((packed >> 36) & 0x1F) + 1
            return {
                "sample_rate": int(sample_rate),
                "bit_depth": int(bit_depth),
            }

        if is_last:
            return {}


def normalized_tempo_events(tempo_events):
    """Return sorted tempo events with a definite active tempo at beat zero."""
    if not tempo_events:
        return (TempoEvent(0.0, DEFAULT_BPM),)

    sorted_events = sorted(tempo_events, key=lambda item: item.beat)
    active_at_zero = TempoEvent(0.0, DEFAULT_BPM)
    future_events = []

    for event in sorted_events:
        if event.beat <= 0:
            active_at_zero = TempoEvent(0.0, event.bpm)
        else:
            future_events.append(event)

    normalized = [active_at_zero]

    for event in future_events:
        if normalized[-1].beat == event.beat:
            normalized[-1] = event
        else:
            normalized.append(event)

    return tuple(normalized)


def normalized_time_signature_events(time_signature_events, manual_value):
    """Return sorted time signature events with a definite event at beat zero."""
    if manual_value is None:
        manual_value = DEFAULT_TIME_SIGNATURE_VALUE

    manual_numerator, manual_denominator = decode_time_signature_value(manual_value)
    sorted_events = sorted(time_signature_events, key=lambda item: item.beat)
    active_at_zero = TimeSignatureEvent(0.0, manual_numerator, manual_denominator)
    future_events = []

    for event in sorted_events:
        if event.beat <= 0:
            active_at_zero = TimeSignatureEvent(
                0.0,
                event.numerator,
                event.denominator,
            )
        else:
            future_events.append(event)

    normalized = [active_at_zero]

    for event in future_events:
        if normalized[-1].beat == event.beat:
            normalized[-1] = event
        else:
            normalized.append(event)

    return tuple(normalized)


def build_beat_to_seconds_converter(tempo_events):
    """
    Create a converter that maps Ableton beat positions to elapsed seconds.

    The converter integrates over every tempo segment once, caches the elapsed
    seconds at each tempo event, then uses those cached anchors to convert
    arbitrary timeline beats efficiently.
    """
    beat_positions = [event.beat for event in tempo_events]
    seconds_at_beat = [0.0]
    total_seconds = 0.0

    for index in range(1, len(tempo_events)):
        previous = tempo_events[index - 1]
        current = tempo_events[index]
        total_seconds += seconds_for_segment(
            previous.beat,
            previous.bpm,
            current.beat,
            current.bpm,
        )
        seconds_at_beat.append(total_seconds)

    def beat_to_seconds(beat):
        first = tempo_events[0]

        if beat <= first.beat:
            require_positive_bpm(first.bpm, "first tempo event bpm")
            return (beat - first.beat) * (60.0 / first.bpm)

        next_event_index = bisect.bisect_left(beat_positions, beat)

        if (
            next_event_index < len(beat_positions)
            and beat == beat_positions[next_event_index]
        ):
            return seconds_at_beat[next_event_index]

        if next_event_index == len(tempo_events):
            last = tempo_events[-1]
            require_positive_bpm(last.bpm, "last tempo event bpm")
            return seconds_at_beat[-1] + (beat - last.beat) * (60.0 / last.bpm)

        start = tempo_events[next_event_index - 1]
        end = tempo_events[next_event_index]
        segment_beats = beat - start.beat

        if abs(end.bpm - start.bpm) < 1e-9:
            return seconds_at_beat[next_event_index - 1] + segment_beats * (
                60.0 / start.bpm
            )

        slope = (end.bpm - start.bpm) / (end.beat - start.beat)
        bpm_at_beat = start.bpm + slope * segment_beats
        require_positive_bpm(bpm_at_beat, "interpolated tempo bpm")

        return seconds_at_beat[next_event_index - 1] + (60.0 / slope) * math.log(
            bpm_at_beat / start.bpm
        )

    return beat_to_seconds


def build_tempo_at_beat_lookup(tempo_events):
    """Create a lookup that returns active/interpolated tempo at a beat."""
    beat_positions = [event.beat for event in tempo_events]

    def tempo_at_beat(beat):
        first = tempo_events[0]

        if beat <= first.beat:
            return first.bpm

        next_event_index = bisect.bisect_right(beat_positions, beat)

        if next_event_index == len(tempo_events):
            return tempo_events[-1].bpm

        start = tempo_events[next_event_index - 1]
        end = tempo_events[next_event_index]

        if abs(end.beat - start.beat) < 1e-9:
            return end.bpm

        beat_offset = beat - start.beat
        slope = (end.bpm - start.bpm) / (end.beat - start.beat)
        return start.bpm + slope * beat_offset

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

    Ableton beat zero displays as bar 1, beat 1, sixteenth 1. Time-signature
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
        event_index, bar_number, displayed_beat, sixteenth = position_parts_at_beat(
            beat
        )
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


def detected_end_beat(raw_data, tempo_events, time_signature_events):
    """
    Choose a sensible end beat from arrangement evidence.

    Clip ends usually provide the most complete arrangement length. Locators and
    automation events are included so sparse or clip-free sets still produce a
    timeline that reaches their last meaningful marker.
    """
    candidates = [0.0]
    candidates.extend(event.beat for event in tempo_events)
    candidates.extend(event.beat for event in time_signature_events)
    candidates.extend(locator.beat for locator in raw_data.locators)

    for clip in raw_data.clips:
        if clip.end_beat is not None:
            candidates.append(clip.end_beat)
        elif clip.start_beat is not None:
            candidates.append(clip.start_beat)

    return max(candidates)


def choose_sample_rate(raw_data, user_sample_rate=None):
    """
    Select the rate used for sample-index calculations.

    A single detected sample rate is safe to use globally. Mixed sample rates
    require a user override because one canonical sample grid cannot represent
    multiple source-media rates without an explicit project/export target.
    """
    detected_rates = sorted(
        {
            clip.sample_rate
            for clip in raw_data.clips
            if clip.sample_rate is not None and clip.sample_rate > 0
        }
    )

    if user_sample_rate is not None:
        return user_sample_rate, "user", tuple(detected_rates)

    if len(detected_rates) == 1:
        return detected_rates[0], "detected", tuple(detected_rates)

    if len(detected_rates) > 1:
        return None, "mixed", tuple(detected_rates)

    return None, "not_detected", tuple()


def detected_bit_depths(raw_data):
    """Return unique bit depths found by audio-header inspection."""
    return tuple(
        sorted(
            {
                clip.bit_depth
                for clip in raw_data.clips
                if clip.bit_depth is not None and clip.bit_depth > 0
            }
        )
    )


def bit_depth_source(bit_depth_values):
    """Describe how bit-depth metadata was discovered."""
    if not bit_depth_values:
        return "not_detected"

    if len(bit_depth_values) == 1:
        return "audio_file"

    return "mixed_audio_files"


def sample_index_at_seconds(seconds, sample_rate):
    """Return the nearest integer sample index for a wall-clock position."""
    if sample_rate is None:
        return None

    return int(round(max(0.0, seconds) * sample_rate))


def build_base_event(
    event_type,
    beat,
    beat_to_seconds,
    tempo_at_beat,
    time_signature_context_at_beat,
    sample_rate,
    sequence=0,
):
    """Create a TimelineEvent with all shared timing/context fields filled."""
    seconds = beat_to_seconds(beat)
    timing_context = time_signature_context_at_beat(beat)

    return TimelineEvent(
        event_type=event_type,
        beat=beat,
        seconds=seconds,
        sample_index=sample_index_at_seconds(seconds, sample_rate),
        song_position=timing_context.song_position,
        bar_number=timing_context.bar_number,
        displayed_beat=timing_context.displayed_beat,
        sixteenth=timing_context.sixteenth,
        tempo_bpm=tempo_at_beat(beat),
        time_signature=timing_context.time_signature,
        sequence=sequence,
    )


def build_event_with_shared_timing(event_type, template_event):
    """
    Create an event at the exact same beat/time as an existing event.

    Generated grid exports intentionally contain both a bar row and a beat-one
    row at the same musical position. Reusing the bar row's computed timing
    avoids a second tempo/signature lookup for that same beat.
    """
    return TimelineEvent(
        event_type=event_type,
        beat=template_event.beat,
        seconds=template_event.seconds,
        sample_index=template_event.sample_index,
        song_position=template_event.song_position,
        bar_number=template_event.bar_number,
        displayed_beat=template_event.displayed_beat,
        sixteenth=template_event.sixteenth,
        tempo_bpm=template_event.tempo_bpm,
        time_signature=template_event.time_signature,
    )


def append_event(events, event):
    """Append an event while assigning a stable sequence number."""
    event.sequence = len(events)
    events.append(event)


def build_tempo_events(events, tempo_events, context):
    """Add tempo-point and tempo-ramp interval events to the timeline."""
    selected_event_types = context["event_types"]
    include_details = context["include_details"]

    if "tempo" in selected_event_types:
        for tempo_event in tempo_events:
            event = build_base_event("tempo", tempo_event.beat, **context["base"])
            event.name = "Tempo"
            event.value = format_decimal(tempo_event.bpm, context["precision"])
            event.source = "main_track_automation"
            if include_details:
                event.details = {"bpm": tempo_event.bpm}
            append_event(events, event)

    if "tempo_ramp" not in selected_event_types:
        return

    for index in range(1, len(tempo_events)):
        start = tempo_events[index - 1]
        end = tempo_events[index]

        if abs(start.bpm - end.bpm) < 1e-9:
            continue

        start_seconds = context["base"]["beat_to_seconds"](start.beat)
        end_seconds = context["base"]["beat_to_seconds"](end.beat)
        event = build_base_event("tempo_ramp", start.beat, **context["base"])
        event.name = "Tempo Ramp"
        event.value = (
            f"{format_decimal(start.bpm, context['precision'])} -> "
            f"{format_decimal(end.bpm, context['precision'])} BPM"
        )
        event.source = "main_track_automation"
        event.duration_seconds = max(0.0, end_seconds - start_seconds)
        if include_details:
            event.details = {
                "start_bpm": start.bpm,
                "end_bpm": end.bpm,
                "end_beat": end.beat,
                "end_wall_seconds": end_seconds,
                "end_wall_time": format_wall_time(end_seconds, context["precision"]),
            }
        append_event(events, event)


def build_time_signature_events(events, time_signature_events, context):
    """Add time-signature change events to the timeline."""
    if "time_signature" not in context["event_types"]:
        return

    include_details = context["include_details"]

    for signature_event in time_signature_events:
        event = build_base_event(
            "time_signature",
            signature_event.beat,
            **context["base"],
        )
        event.name = "Time Signature"
        event.value = f"{signature_event.numerator}/{signature_event.denominator}"
        event.source = "main_track_automation"
        if include_details:
            event.details = {
                "numerator": signature_event.numerator,
                "denominator": signature_event.denominator,
            }
        append_event(events, event)


def build_key_events(events, raw_data, context):
    """Add session and clip key/scale events when ScaleInformation is present."""
    if "key" not in context["event_types"]:
        return

    include_details = context["include_details"]
    session_key = scale_label(raw_data.session_scale)

    if session_key:
        event = build_base_event("key", 0.0, **context["base"])
        event.name = "Session Key"
        event.value = session_key
        event.key = session_key
        event.source = "session_scale"
        if include_details:
            event.details = {
                "root": raw_data.session_scale.root,
                "scale_id": raw_data.session_scale.name,
                "in_key": raw_data.session_scale.in_key,
            }
        append_event(events, event)

    for clip in raw_data.clips:
        if clip.start_beat is None:
            continue

        key = scale_label(clip.scale)

        if not key:
            continue

        event = build_base_event("key", clip.start_beat, **context["base"])
        event.name = clip.name
        event.value = key
        event.key = key
        event.event_id = clip.clip_id
        event.source = f"{clip.clip_type}_clip_scale"
        event.source_path = clip.path or clip.relative_path
        event.sample_rate = clip.sample_rate
        event.bit_depth = clip.bit_depth
        if include_details:
            event.details = {
                "root": clip.scale.root,
                "scale_id": clip.scale.name,
                "in_key": clip.scale.in_key,
            }
        append_event(events, event)


def build_locator_events(events, locators, context):
    """Add arrangement locator events without modifying locator labels."""
    if "locator" not in context["event_types"]:
        return

    include_details = context["include_details"]

    for locator in locators:
        event = build_base_event("locator", locator.beat, **context["base"])
        event.name = locator.name
        event.value = locator.name
        event.event_id = locator.locator_id
        event.source = "arrangement_locator"
        if include_details:
            event.details = {"locator_id": locator.locator_id}
        append_event(events, event)


def build_clip_events(events, clips, context):
    """Add clip start and end boundary events."""
    wants_start = "clip_start" in context["event_types"]
    wants_end = "clip_end" in context["event_types"]

    if not wants_start and not wants_end:
        return

    for clip in clips:
        if wants_start and clip.start_beat is not None:
            event = build_base_event("clip_start", clip.start_beat, **context["base"])
            populate_clip_event(event, clip, context["include_details"])
            append_event(events, event)

        if wants_end and clip.end_beat is not None:
            event = build_base_event("clip_end", clip.end_beat, **context["base"])
            populate_clip_event(event, clip, context["include_details"])

            if clip.start_beat is not None:
                start_seconds = context["base"]["beat_to_seconds"](clip.start_beat)
                event.duration_seconds = max(0.0, event.seconds - start_seconds)
                if context["include_details"]:
                    event.details["start_beat"] = clip.start_beat
                    event.details["duration_seconds"] = event.duration_seconds

            append_event(events, event)


def populate_clip_event(event, clip, include_details):
    """Fill clip-specific fields shared by clip_start and clip_end rows."""
    event.name = clip.name
    event.value = clip.clip_type
    event.event_id = clip.clip_id
    event.source = f"{clip.clip_type}_clip"
    event.source_path = clip.path or clip.relative_path
    event.sample_rate = clip.sample_rate
    event.bit_depth = clip.bit_depth
    if include_details:
        event.details = {
            "clip_id": clip.clip_id,
            "clip_type": clip.clip_type,
            "sample_rate": clip.sample_rate,
            "bit_depth": clip.bit_depth,
            "default_duration_samples": clip.default_duration_samples,
            "relative_path": clip.relative_path,
            "existing_audio_path": clip.existing_audio_path,
        }


def build_grid_events(events, time_signature_events, context, end_beat):
    """Add optional bar and beat grid events through the end of the song."""
    grid_mode = context["grid"]

    if grid_mode == "none":
        return

    for index, signature_event in enumerate(time_signature_events):
        section_end = (
            time_signature_events[index + 1].beat
            if index + 1 < len(time_signature_events)
            else end_beat
        )
        section_end = min(section_end, end_beat)

        if section_end < signature_event.beat:
            continue

        bar_length = beats_per_bar(signature_event)
        displayed_beat_size = beat_unit_size(signature_event)
        bar_beat = signature_event.beat

        while bar_beat <= section_end + 1e-9:
            bar_event = build_base_event("bar", bar_beat, **context["base"])
            bar_event.name = f"Bar {bar_event.bar_number}"
            bar_event.value = bar_event.song_position
            bar_event.source = "generated_grid"
            append_event(events, bar_event)

            if grid_mode == "beats":
                beat_index = 0

                while beat_index < signature_event.numerator:
                    beat_position = bar_beat + beat_index * displayed_beat_size

                    if beat_position <= section_end + 1e-9:
                        if beat_index == 0:
                            beat_event = build_event_with_shared_timing(
                                "beat",
                                bar_event,
                            )
                        else:
                            beat_event = build_base_event(
                                "beat",
                                beat_position,
                                **context["base"],
                            )
                        beat_event.name = (
                            f"Bar {beat_event.bar_number} Beat "
                            f"{beat_event.displayed_beat}"
                        )
                        beat_event.value = beat_event.song_position
                        beat_event.source = "generated_grid"
                        append_event(events, beat_event)

                    beat_index += 1

            bar_beat += bar_length


def build_song_end_event(events, context, end_beat):
    """Add one explicit event marking the detected or user-specified end."""
    if "song_end" not in context["event_types"]:
        return

    event = build_base_event("song_end", end_beat, **context["base"])
    event.name = "Song End"
    event.value = event.song_position
    event.source = "detected_end"
    if context["include_details"]:
        event.details = {"end_beat": end_beat}
    append_event(events, event)


def build_parse_options(
    event_types,
    columns,
    grid,
    end_beat_override,
    sample_rate_override,
):
    """
    Return the narrowest XML parse options that preserve requested output.

    Clip and media regions are the expensive optional parts of the ALS stream.
    We still collect them when they directly produce events, when clip scale
    data may produce key events, when clip timing is needed for the exported
    end/grid boundary, or when sample references are needed for sample indexes.
    """
    selected_event_types = set(event_types)
    selected_columns = set(columns)

    needs_clip_events = bool(
        {"clip_start", "clip_end"}.intersection(selected_event_types)
    )
    needs_clip_keys = "key" in selected_event_types
    needs_clip_end_for_timeline_length = (
        end_beat_override is None
        and (grid != "none" or "song_end" in selected_event_types)
    )
    needs_detected_sample_rate = (
        sample_rate_override is None
        and bool({"sample_index", "sample_rate", "bit_depth"}.intersection(selected_columns))
    )
    needs_clip_media_columns = bool(
        {"source_path", "sample_rate", "bit_depth", "details"}.intersection(
            selected_columns
        )
        and (needs_clip_events or needs_clip_keys)
    )

    collect_clips = (
        needs_clip_events
        or needs_clip_keys
        or needs_clip_end_for_timeline_length
        or needs_detected_sample_rate
    )
    collect_clip_media = collect_clips and (
        needs_detected_sample_rate or needs_clip_media_columns
    )
    inspect_audio_files = collect_clip_media and (
        "bit_depth" in selected_columns or "details" in selected_columns
    )

    return TimelineParseOptions(
        collect_session_scale="key" in selected_event_types,
        collect_clips=collect_clips,
        collect_clip_media=collect_clip_media,
        inspect_audio_files=inspect_audio_files,
    )


def sorted_events(events):
    """Sort by wall time, then beat, then event-kind order, then parse order."""
    return sorted(
        events,
        key=lambda event: (
            event.seconds,
            event.beat,
            EVENT_SORT_ORDER.get(event.event_type, 500),
            event.sequence,
        ),
    )


def extract_timeline(
    als_path,
    grid="none",
    event_types=DEFAULT_EVENT_TYPES,
    columns=DEFAULT_COLUMNS,
    end_beat_override=None,
    sample_rate_override=None,
    precision=DEFAULT_PRECISION,
):
    """Parse the Ableton file and build exported timeline events plus metadata."""
    parse_options = build_parse_options(
        event_types,
        columns,
        grid,
        end_beat_override,
        sample_rate_override,
    )
    raw_data = parse_als_timeline_data(als_path, parse_options=parse_options)
    tempo_events = normalized_tempo_events(raw_data.tempo_events)
    time_signature_events = normalized_time_signature_events(
        raw_data.time_signature_events,
        raw_data.manual_time_signature_value,
    )
    beat_to_seconds = build_beat_to_seconds_converter(tempo_events)
    tempo_at_beat = build_tempo_at_beat_lookup(tempo_events)
    time_signature_context_at_beat = build_time_signature_context(
        time_signature_events
    )
    sample_rate, sample_rate_source, detected_rates = choose_sample_rate(
        raw_data,
        sample_rate_override,
    )
    bit_depth_values = detected_bit_depths(raw_data)
    end_beat = (
        end_beat_override
        if end_beat_override is not None
        else detected_end_beat(raw_data, tempo_events, time_signature_events)
    )
    end_seconds = beat_to_seconds(end_beat)
    context = {
        "grid": grid,
        "event_types": tuple(event_types),
        "include_details": "details" in columns,
        "precision": precision,
        "base": {
            "beat_to_seconds": beat_to_seconds,
            "tempo_at_beat": tempo_at_beat,
            "time_signature_context_at_beat": time_signature_context_at_beat,
            "sample_rate": sample_rate,
        },
    }
    events = []

    build_time_signature_events(events, time_signature_events, context)
    build_tempo_events(events, tempo_events, context)
    build_key_events(events, raw_data, context)
    build_locator_events(events, raw_data.locators, context)
    build_clip_events(events, raw_data.clips, context)
    build_grid_events(events, time_signature_events, context, end_beat)
    build_song_end_event(events, context, end_beat)

    metadata = TimelineMetadata(
        sample_rate=sample_rate,
        sample_rate_source=sample_rate_source,
        detected_sample_rates=detected_rates,
        detected_bit_depths=bit_depth_values,
        bit_depth_source=bit_depth_source(bit_depth_values),
        end_beat=end_beat,
        end_seconds=end_seconds,
        grid=grid,
        event_types=tuple(event_types),
        ableton_creator=raw_data.creator,
        ableton_major_version=raw_data.major_version,
        ableton_minor_version=raw_data.minor_version,
    )

    return sorted_events(events), metadata


def ensure_parent_directory(path):
    """Fail early with a clear message when the output directory is missing."""
    parent = path.parent

    if parent and not parent.exists():
        raise TimelineToolError(
            "Output directory does not exist.",
            [("path", display_path(parent))],
        )


def tsv_value(event, column, precision):
    """Format one selected event column for TSV output."""
    if column == "wall_time":
        return format_wall_time(event.seconds, precision)

    if column == "wall_seconds":
        return format_decimal(event.seconds, precision)

    if column == "sample_index":
        return "" if event.sample_index is None else str(event.sample_index)

    if column == "event_type":
        return event.event_type

    if column == "song_position":
        return event.song_position

    if column == "absolute_beats":
        return format_decimal(event.beat, precision)

    if column == "tempo_bpm":
        return format_decimal(event.tempo_bpm, precision)

    if column == "time_signature":
        return event.time_signature

    if column == "key":
        return event.key

    if column == "name":
        return event.name

    if column == "value":
        return event.value

    if column == "event_id":
        return event.event_id

    if column == "source":
        return event.source

    if column == "source_path":
        return event.source_path

    if column == "sample_rate":
        return "" if event.sample_rate is None else str(event.sample_rate)

    if column == "bit_depth":
        return "" if event.bit_depth is None else str(event.bit_depth)

    if column == "duration_seconds":
        return format_decimal(event.duration_seconds, precision)

    if column == "details":
        return json.dumps(event.details or {}, ensure_ascii=False, sort_keys=True)

    raise TimelineToolError("Unknown export column requested.", [("column", column)])


def json_value(event, column, precision):
    """Return one selected event column as a JSON-friendly value."""
    if column == "wall_time":
        return format_wall_time(event.seconds, precision)

    if column == "wall_seconds":
        return round(event.seconds, precision)

    if column == "sample_index":
        return event.sample_index

    if column == "event_type":
        return event.event_type

    if column == "song_position":
        return event.song_position

    if column == "absolute_beats":
        return round(event.beat, precision)

    if column == "tempo_bpm":
        return round(event.tempo_bpm, precision)

    if column == "time_signature":
        return event.time_signature

    if column == "key":
        return event.key

    if column == "name":
        return event.name

    if column == "value":
        return event.value

    if column == "event_id":
        return int(event.event_id) if event.event_id.isdigit() else event.event_id

    if column == "source":
        return event.source

    if column == "source_path":
        return event.source_path

    if column == "sample_rate":
        return event.sample_rate

    if column == "bit_depth":
        return event.bit_depth

    if column == "duration_seconds":
        if event.duration_seconds is None:
            return None
        return round(event.duration_seconds, precision)

    if column == "details":
        return event.details or {}

    raise TimelineToolError("Unknown export column requested.", [("column", column)])


def write_tsv(events, output_path, columns, precision, include_heading_row=True):
    """Write timeline events to a tab-separated file."""
    ensure_parent_directory(output_path)

    try:
        with output_path.open("w", encoding="utf-8", newline="") as out:
            writer = csv.writer(out, delimiter="\t", lineterminator="\n")

            if include_heading_row:
                writer.writerow([COLUMN_HEADERS[column] for column in columns])

            for event in events:
                writer.writerow(
                    [tsv_value(event, column, precision) for column in columns]
                )
    except PermissionError as exc:
        raise TimelineToolError(
            "Permission denied while writing the TSV output file.",
            [("path", display_path(output_path))],
        ) from exc
    except OSError as exc:
        raise TimelineToolError(
            "Unable to write the TSV output file.",
            [("path", display_path(output_path)), ("detail", exc)],
        ) from exc


def metadata_payload(metadata, als_path, precision):
    """Return JSON-friendly run metadata."""
    return {
        "generated_by": SCRIPT_NAME,
        "version": SCRIPT_VERSION,
        "source_file": display_path(als_path),
        "ableton": {
            "creator": metadata.ableton_creator,
            "major_version": metadata.ableton_major_version,
            "minor_version": metadata.ableton_minor_version,
        },
        "sample_rate": metadata.sample_rate,
        "sample_rate_source": metadata.sample_rate_source,
        "detected_sample_rates": list(metadata.detected_sample_rates),
        "detected_bit_depths": list(metadata.detected_bit_depths),
        "bit_depth_source": metadata.bit_depth_source,
        "end_beat": round(metadata.end_beat, precision),
        "end_wall_seconds": round(metadata.end_seconds, precision),
        "end_wall_time": format_wall_time(metadata.end_seconds, precision),
        "grid": metadata.grid,
        "event_types": list(metadata.event_types),
    }


def build_json_payload(events, metadata, als_path, columns, precision):
    """Build the structured JSON timeline export payload."""
    return {
        "metadata": metadata_payload(metadata, als_path, precision),
        "columns": list(columns),
        "events": [
            {column: json_value(event, column, precision) for column in columns}
            for event in events
        ],
    }


def write_json_export(
    events,
    metadata,
    json_path,
    als_path,
    columns,
    precision,
    json_format="pretty",
):
    """Write timeline events to JSON in compact or human-readable form."""
    ensure_parent_directory(json_path)
    payload = build_json_payload(events, metadata, als_path, columns, precision)

    if json_format == "compact":
        dump_options = {"ensure_ascii": False, "separators": (",", ":")}
    else:
        dump_options = {"ensure_ascii": False, "indent": 2}

    try:
        with json_path.open("w", encoding="utf-8") as out:
            json.dump(payload, out, **dump_options)
            out.write("\n")
    except PermissionError as exc:
        raise TimelineToolError(
            "Permission denied while writing the JSON output file.",
            [("path", display_path(json_path))],
        ) from exc
    except OSError as exc:
        raise TimelineToolError(
            "Unable to write the JSON output file.",
            [("path", display_path(json_path)), ("detail", exc)],
        ) from exc


def normalize_column_name(raw_column_name):
    """Normalize one user-supplied export column name or alias."""
    normalized = raw_column_name.strip().lower().replace("-", "_")
    normalized = COLUMN_ALIASES.get(normalized, normalized)

    if normalized not in ALL_COLUMNS:
        valid_names = ", ".join(ALL_COLUMNS)
        raise TimelineToolError(
            "Unknown export column requested.",
            [("column", raw_column_name), ("valid", valid_names)],
        )

    return normalized


def normalize_event_type(raw_event_type):
    """Normalize one user-supplied event type."""
    normalized = raw_event_type.strip().lower().replace("-", "_")

    if normalized not in ALL_EVENT_TYPES:
        valid_names = ", ".join(ALL_EVENT_TYPES)
        raise TimelineToolError(
            "Unknown event type requested.",
            [("event_type", raw_event_type), ("valid", valid_names)],
        )

    return normalized


def dedupe(items):
    """Return items in order, keeping only the first instance of each."""
    seen = set()
    deduped = []

    for item in items:
        if item not in seen:
            deduped.append(item)
            seen.add(item)

    return tuple(deduped)


def parse_column_list(raw_columns):
    """Parse a comma-separated column list from the command line."""
    if raw_columns is None:
        return DEFAULT_COLUMNS

    columns = []

    for raw_column in raw_columns.split(","):
        token = raw_column.strip()

        if not token:
            continue

        normalized = token.lower().replace("-", "_")

        if normalized in ("all", "default"):
            columns.extend(DEFAULT_COLUMNS)
        else:
            columns.append(normalize_column_name(token))

    if not columns:
        raise TimelineToolError(
            "No export columns were selected.",
            [("columns", raw_columns)],
        )

    return dedupe(columns)


def parse_event_type_list(raw_event_types):
    """Parse a comma-separated event-type list from the command line."""
    if raw_event_types is None:
        return DEFAULT_EVENT_TYPES

    event_types = []

    for raw_event_type in raw_event_types.split(","):
        token = raw_event_type.strip()

        if not token:
            continue

        normalized = token.lower().replace("-", "_")

        if normalized in ("all", "default"):
            event_types.extend(DEFAULT_EVENT_TYPES)
        else:
            event_types.append(normalize_event_type(token))

    if not event_types:
        raise TimelineToolError(
            "No event types were selected.",
            [("event_types", raw_event_types)],
        )

    return dedupe(event_types)


def parse_args():
    """Parse command-line arguments and validate simple numeric options."""
    parser = TimelineArgumentParser(
        description="Extract a precise Ableton arrangement timeline to TSV/JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 src/extract_timeline.py song.als\n"
            "  python3 src/extract_timeline.py song.als --output=song.timeline.tsv\n"
            "  python3 src/extract_timeline.py song.als --json=song.timeline.json\n"
            "  python3 src/extract_timeline.py song.als --grid=bars\n"
            "  python3 src/extract_timeline.py song.als --grid=beats\n"
            "  python3 src/extract_timeline.py song.als --event-types=tempo,time_signature,key,locator\n"
            "  python3 src/extract_timeline.py song.als --columns=wall_time,event_type,name,value"
        ),
    )

    parser.add_argument(
        "als_path",
        help="Path to the Ableton .als file. Plain XML and gzip-compressed ALS files are supported.",
    )

    parser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="Output TSV path. Default: <input filename>.timeline.tsv in the current directory.",
    )

    parser.add_argument(
        "-j",
        "--json",
        metavar="PATH",
        help="Also write a JSON timeline export to PATH.",
    )

    parser.add_argument(
        "--json-format",
        choices=("pretty", "compact"),
        default="pretty",
        help="JSON formatting style. Default: pretty.",
    )

    parser.add_argument(
        "--grid",
        choices=("none", "bars", "beats"),
        default="none",
        help="Add generated musical grid rows. Default: none.",
    )

    parser.add_argument(
        "--precision",
        type=int,
        default=DEFAULT_PRECISION,
        help=f"Decimal places for wall time and numeric fields. Default: {DEFAULT_PRECISION}.",
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        metavar="HZ",
        help="Override the sample rate used for sample-index calculations.",
    )

    parser.add_argument(
        "--end-beat",
        type=float,
        metavar="BEAT",
        help="Override the beat where grid generation and song-end reporting stop.",
    )

    parser.add_argument(
        "--event-types",
        metavar="LIST",
        help="Comma-separated event types. Default: all.",
    )

    parser.add_argument(
        "--columns",
        metavar="LIST",
        help="Comma-separated TSV/JSON columns. Default: all.",
    )

    parser.add_argument(
        "--no-heading-row",
        "--no-header",
        action="store_true",
        help="Omit the TSV heading row entirely.",
    )

    args = parser.parse_args()

    if args.precision < 0:
        parser.error("--precision must be 0 or greater")

    if args.sample_rate is not None and args.sample_rate <= 0:
        parser.error("--sample-rate must be greater than 0")

    if args.end_beat is not None and args.end_beat < 0:
        parser.error("--end-beat must be 0 or greater")

    return args


def run(args):
    """Run the extraction workflow and return the values needed for reporting."""
    als_path = user_path(args.als_path)
    output_path = user_path(args.output) if args.output else default_output_path(als_path)
    json_path = user_path(args.json) if args.json else None
    columns = parse_column_list(args.columns)
    event_types = parse_event_type_list(args.event_types)
    started_at = time.perf_counter()

    events, metadata = extract_timeline(
        als_path,
        grid=args.grid,
        event_types=event_types,
        columns=columns,
        end_beat_override=args.end_beat,
        sample_rate_override=args.sample_rate,
        precision=args.precision,
    )

    write_tsv(
        events,
        output_path=output_path,
        columns=columns,
        precision=args.precision,
        include_heading_row=not args.no_heading_row,
    )

    rows = [
        ("input", display_path(als_path)),
        ("events", len(events)),
        ("grid", args.grid),
        ("sample rate", metadata.sample_rate or "not detected"),
        ("output", display_path(output_path)),
    ]

    if json_path:
        write_json_export(
            events,
            metadata,
            json_path=json_path,
            als_path=als_path,
            columns=columns,
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
    except TimelineToolError as exc:
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
