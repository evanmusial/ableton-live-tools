#!/usr/bin/env python3

"""
extract_project_manifest.py
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
  - Initial Project Manifest release.
  - Adds project inventory reporting for tracks, clips, samples, devices, and
    high-level Ableton metadata.
  - Adds sample manifest TSV/JSON data with audio file paths, relative paths,
    original file sizes, original CRC values, default sample rates, default
    durations, usage counts, and missing-file status.
  - Adds plugin/effects manifest data for third-party plugins and Ableton native
    devices, including track location, device position, manufacturer, format,
    enabled state, placeholder state, and preset names where detectable.
  - Adds plugin views sorted by author/manufacturer and by plugin/effect name.
  - Writes a Markdown report, JSON payload, and TSV tables in one output
    directory.

What this script does:
  Ableton Live .als files are XML documents, usually gzip-compressed. This tool
  streams each top-level track XML subtree, extracts inventory data from that
  subtree, then clears it before moving to the next track. That keeps memory use
  much lower than building the full uncompressed ALS tree while still allowing
  precise track-local parsing of clips, sample references, and devices.

Default output:
  If --output-dir is omitted, the script writes a directory named
  <input filename>.project-manifest in the current working directory.

  Files written by default:
    project_inventory.md
    project_manifest.json
    tracks.tsv
    clips.tsv
    samples.tsv
    devices.tsv
    plugins_by_author.tsv
    plugins_by_name.tsv

Arguments:
  als_path
      Path to the Ableton .als file.

      Example:
        python3 src/extract_project_manifest.py path/to/song.als

  --output-dir=PATH
  -o PATH
      Directory where the report files should be written.

      Example:
        python3 src/extract_project_manifest.py song.als --output-dir=song_manifest

  --json-format=pretty|compact
      Choose whether JSON is human-readable or compact.
      Default: pretty

  --no-json
      Do not write project_manifest.json.

  --no-markdown
      Do not write project_inventory.md.

  --no-tsv
      Do not write TSV tables.

CLI reporting:
  - Reports are headed "Project Manifest Results".
  - Every written file is listed with the label "output".
  - Elapsed processing time is shown with three decimal places.
  - Successful runs exit with status code 0.
  - Runtime/user-data errors exit with status code 1.
  - Command-line argument errors exit with status code 2.
"""

import argparse
import csv
from dataclasses import dataclass, field
import gzip
import json
import os
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET
import zlib


SCRIPT_NAME = "extract_project_manifest.py"
SCRIPT_VERSION = "2026.06.07"
REPORT_TITLE = "Project Manifest Results"
XML_READ_CHUNK_SIZE = 4 * 1024 * 1024

TRACK_TAGS = {
    "AudioTrack": "audio",
    "MidiTrack": "midi",
    "GroupTrack": "group",
    "ReturnTrack": "return",
    "MasterTrack": "master",
}
CLIP_TAGS = {"AudioClip": "audio", "MidiClip": "midi"}
PLUGIN_DEVICE_FORMATS = {
    "AuPluginDevice": "AU",
    "VstPluginDevice": "VST",
    "Vst3PluginDevice": "VST3",
    "PluginDevice": "Plugin",
    "MxDevice": "Max for Live",
}
PLUGIN_INFO_FORMATS = {
    "AuPluginInfo": "AU",
    "VstPluginInfo": "VST",
    "Vst3PluginInfo": "VST3",
    "PluginInfo": "Plugin",
}

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
FG_GREEN = "\033[38;5;114m"
FG_RED = "\033[38;5;203m"
FG_YELLOW = "\033[38;5;221m"
FG_MUTED = "\033[38;5;244m"
FG_VALUE = "\033[38;5;250m"
FG_TITLE = "\033[38;5;153m"


class ProjectManifestError(Exception):
    """User-facing runtime error with structured report details."""

    def __init__(self, problem, details=None):
        super().__init__(problem)
        self.problem = problem
        self.details = details or []


class ManifestArgumentParser(argparse.ArgumentParser):
    """Argparse subclass that reports argument errors like the other tools."""

    def error(self, message):
        print_report(
            "error",
            [("problem", message)],
            stream=sys.stderr,
            status_color=FG_RED,
        )
        raise SystemExit(2)


@dataclass
class TrackRecord:
    """One top-level Live track as exported in the inventory tables."""

    track_index: int
    track_id: str
    track_type: str
    name: str
    color: str = ""
    clip_count: int = 0
    audio_clip_count: int = 0
    midi_clip_count: int = 0
    frozen_clip_count: int = 0
    disabled_clip_count: int = 0
    device_count: int = 0
    plugin_count: int = 0
    native_device_count: int = 0


@dataclass
class ClipRecord:
    """One arrangement/session clip found inside a top-level track."""

    clip_id: str
    clip_type: str
    track_index: int
    track_id: str
    track_name: str
    track_type: str
    name: str
    start_beat: str = ""
    end_beat: str = ""
    disabled: str = ""
    area: str = ""
    path: str = ""
    relative_path: str = ""
    original_file_size: str = ""
    original_crc: str = ""
    default_sample_rate: str = ""
    default_duration_samples: str = ""


@dataclass
class SampleRecord:
    """Unique sample/audio file reference with aggregated clip usage."""

    key: str
    path: str = ""
    relative_path: str = ""
    original_file_size: str = ""
    original_crc: str = ""
    default_sample_rate: str = ""
    default_duration_samples: str = ""
    usage_count: int = 0
    tracks: set = field(default_factory=set)
    clips: set = field(default_factory=set)
    resolved_path: str = ""
    exists: bool = False


@dataclass
class DeviceRecord:
    """One device, native effect, plugin, or Max for Live device."""

    track_index: int
    track_id: str
    track_name: str
    track_type: str
    device_index: int
    device_id: str
    device_type: str
    name: str
    user_name: str = ""
    manufacturer: str = ""
    format: str = ""
    category: str = ""
    enabled: str = ""
    placeholder: str = ""
    preset_name: str = ""
    chain_path: str = ""


@dataclass
class ProjectManifest:
    """Complete parsed project inventory."""

    source_file: str
    ableton_creator: str = ""
    ableton_major_version: str = ""
    ableton_minor_version: str = ""
    locator_count: int = 0
    tempo_event_count: int = 0
    time_signature_event_count: int = 0
    tracks: list = field(default_factory=list)
    clips: list = field(default_factory=list)
    samples: dict = field(default_factory=dict)
    devices: list = field(default_factory=list)


def stream_supports_color(stream):
    """Return True when ANSI/xterm-256 color should be emitted."""
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
    """Print one stable key/value report row."""
    label_text = colorize(f"{label:<10}", FG_MUTED, stream=stream)
    value_text = colorize(str(value), FG_VALUE, stream=stream)
    print(f"  {label_text} {value_text}", file=stream)


def print_report(status, rows, *, stream=sys.stdout, status_color=FG_GREEN):
    """Print a compact CLI report matching the other tools."""
    title = colorize(REPORT_TITLE, FG_TITLE, stream=stream, bold=True)
    print(title, file=stream)
    print_kv("status", colorize(status, status_color, stream=stream), stream=stream)

    for label, value in rows:
        print_kv(label, value, stream=stream)


def format_elapsed(started_at):
    """Return elapsed wall-clock time with stable CLI precision."""
    return f"{time.perf_counter() - started_at:.3f}s"


def display_path(path):
    """Return an absolute, expanded path for CLI and JSON output."""
    return str(Path(path).expanduser().resolve(strict=False))


def user_path(raw_path):
    """Expand a user-provided path without requiring it to exist."""
    return Path(raw_path).expanduser()


def default_output_dir(als_path):
    """Return the default project manifest output directory."""
    return Path.cwd() / f"{als_path.name}.project-manifest"


def ensure_output_dir(path):
    """Create the report directory if it does not already exist."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while creating the output directory.",
            [("path", display_path(path))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to create the output directory.",
            [("path", display_path(path)), ("detail", exc)],
        ) from exc


def bool_text(raw_value):
    """Normalize Ableton true/false strings for manifest output."""
    if raw_value is None or raw_value == "":
        return ""
    return "true" if str(raw_value).lower() == "true" else "false"


def value_at(element, path, default=""):
    """Return an Ableton element's Value attribute at a simple ElementTree path."""
    found = element.find(path)
    if found is None:
        return default
    return found.attrib.get("Value", default)


def first_value_at(element, paths, default=""):
    """Return the first non-empty Value attribute found at any path."""
    for path in paths:
        value = value_at(element, path, "")
        if value not in ("", None):
            return value
    return default


def direct_child_value(element, tag_name, default=""):
    """Return a direct child Value attribute without walking into grandchildren."""
    child = element.find(f"./{tag_name}")
    if child is None:
        return default
    return child.attrib.get("Value", default)


def safe_text(value):
    """Collapse arbitrary Ableton text into one TSV/Markdown-safe line."""
    if value is None:
        return ""
    return " ".join(str(value).splitlines())


def display_device_type(device_type):
    """Convert a CamelCase device tag into a readable fallback name."""
    if not device_type:
        return ""
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", device_type)
    return spaced.replace("E Q", "EQ").replace("M X", "MX")


def candidate_sample_paths(clip, als_path):
    """Return possible filesystem paths for one audio clip source."""
    candidates = []

    if clip.path:
        candidates.append(Path(clip.path).expanduser())

    if clip.relative_path:
        relative = Path(clip.relative_path)
        candidates.append(relative if relative.is_absolute() else als_path.parent / relative)

    deduped = []
    seen = set()

    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        deduped.append(candidate)
        seen.add(key)

    return deduped


def sample_key_for_clip(clip):
    """Build a stable dedupe key for a sample reference."""
    return "\x1f".join(
        (
            clip.path,
            clip.relative_path,
            clip.original_file_size,
            clip.original_crc,
        )
    )


def clip_area(clip, parent_map):
    """Identify whether a clip came from the main sequencer or freeze data."""
    current = parent_map.get(clip)

    while current is not None:
        if current.tag == "FreezeSequencer":
            return "freeze"
        if current.tag == "MainSequencer":
            return "main"
        current = parent_map.get(current)

    return ""


def chain_path_for_device(device, parent_map):
    """Return a short path showing whether a device lives inside a nested rack."""
    names = []
    current = parent_map.get(device)

    while current is not None:
        if current.tag in ("Devices", "DeviceChain"):
            names.append(current.tag)
        current = parent_map.get(current)

    return " > ".join(reversed(names))


def plugin_info_for_device(device):
    """Return the first plugin-info element under a device, if one exists."""
    plugin_desc = device.find("./PluginDesc")
    if plugin_desc is None:
        return None

    for child in list(plugin_desc):
        return child

    return None


def preset_name_for_device(device):
    """Return a detected preset name without mistaking plugin names for presets."""
    plugin_info = plugin_info_for_device(device)

    if plugin_info is not None:
        for path in (
            "./Preset/AuPreset/Name",
            "./Preset/VstPreset/Name",
            "./Preset/Vst3Preset/Name",
            "./Preset/PluginPreset/Name",
        ):
            value = value_at(plugin_info, path, "")
            if value:
                return value

    return first_value_at(
        device,
        (
            "./LastPresetRef/Value/FilePresetRef/FileRef/Path",
            "./LastPresetRef/Value/AbletonDefaultPresetRef/FileRef/Path",
        ),
    )


def device_record_from_element(device, track, device_index, parent_map):
    """Extract one DeviceRecord from a device XML subtree."""
    plugin_info = plugin_info_for_device(device)
    user_name = direct_child_value(device, "UserName")
    plugin_name = value_at(plugin_info, "./Name") if plugin_info is not None else ""
    manufacturer = (
        value_at(plugin_info, "./Manufacturer") if plugin_info is not None else ""
    )
    plugin_format = ""

    if plugin_info is not None:
        plugin_format = PLUGIN_INFO_FORMATS.get(plugin_info.tag, "")

    if not plugin_format:
        plugin_format = PLUGIN_DEVICE_FORMATS.get(device.tag, "Ableton Native")

    category = (
        "third_party_plugin"
        if plugin_format not in ("Ableton Native", "Max for Live")
        else "ableton_native_device"
    )

    if not manufacturer:
        manufacturer = "Ableton" if category == "ableton_native_device" else "Unknown"

    name = user_name or plugin_name or display_device_type(device.tag)

    return DeviceRecord(
        track_index=track.track_index,
        track_id=track.track_id,
        track_name=track.name,
        track_type=track.track_type,
        device_index=device_index,
        device_id=device.attrib.get("Id", ""),
        device_type=device.tag,
        name=name,
        user_name=user_name,
        manufacturer=manufacturer,
        format=plugin_format,
        category=category,
        enabled=bool_text(value_at(device, "./On/Manual")),
        placeholder=(
            bool_text(value_at(plugin_info, "./IsPlaceholderDevice"))
            if plugin_info is not None
            else ""
        ),
        preset_name=preset_name_for_device(device),
        chain_path=chain_path_for_device(device, parent_map),
    )


def parse_track_element(track_element, track_index, als_path):
    """Extract tracks, clips, samples, and devices from one top-level track."""
    track = TrackRecord(
        track_index=track_index,
        track_id=track_element.attrib.get("Id", ""),
        track_type=TRACK_TAGS.get(track_element.tag, track_element.tag),
        name=first_value_at(track_element, ("./Name/UserName",), track_element.tag),
        color=value_at(track_element, "./Color"),
    )
    parent_map = {child: parent for parent in track_element.iter() for child in parent}
    clips = []
    devices = []
    sample_updates = []

    for clip in track_element.iter():
        if clip.tag not in CLIP_TAGS:
            continue

        clip_type = CLIP_TAGS[clip.tag]
        sample_ref = clip.find("./SampleRef")
        file_ref = sample_ref.find("./FileRef") if sample_ref is not None else None
        record = ClipRecord(
            clip_id=clip.attrib.get("Id", ""),
            clip_type=clip_type,
            track_index=track.track_index,
            track_id=track.track_id,
            track_name=track.name,
            track_type=track.track_type,
            name=clip.attrib.get("Name")
            or value_at(clip, "./Name", "")
            or f"{clip_type.title()} Clip",
            start_beat=clip.attrib.get("Time", ""),
            end_beat=value_at(clip, "./CurrentEnd"),
            disabled=bool_text(value_at(clip, "./Disabled")),
            area=clip_area(clip, parent_map),
            path=value_at(file_ref, "./Path") if file_ref is not None else "",
            relative_path=(
                value_at(file_ref, "./RelativePath") if file_ref is not None else ""
            ),
            original_file_size=(
                value_at(file_ref, "./OriginalFileSize") if file_ref is not None else ""
            ),
            original_crc=(
                value_at(file_ref, "./OriginalCrc") if file_ref is not None else ""
            ),
            default_sample_rate=(
                value_at(sample_ref, "./DefaultSampleRate")
                if sample_ref is not None
                else ""
            ),
            default_duration_samples=(
                value_at(sample_ref, "./DefaultDuration")
                if sample_ref is not None
                else ""
            ),
        )
        clips.append(record)

        if record.disabled == "true":
            track.disabled_clip_count += 1
        if record.area == "freeze":
            track.frozen_clip_count += 1
        if clip_type == "audio":
            track.audio_clip_count += 1
            if record.path or record.relative_path or record.original_crc:
                sample_updates.append(record)
        elif clip_type == "midi":
            track.midi_clip_count += 1

    for devices_element in track_element.iter("Devices"):
        for device in list(devices_element):
            device_index = len(devices) + 1
            devices.append(
                device_record_from_element(
                    device,
                    track,
                    device_index,
                    parent_map,
                )
            )

    track.clip_count = len(clips)
    track.device_count = len(devices)
    track.plugin_count = sum(
        1 for device in devices if device.category == "third_party_plugin"
    )
    track.native_device_count = track.device_count - track.plugin_count

    return track, clips, devices, sample_updates


def update_sample_manifest(samples, clip, als_path):
    """Merge one audio clip source into the unique sample manifest."""
    key = sample_key_for_clip(clip)

    if key not in samples:
        sample = SampleRecord(
            key=key,
            path=clip.path,
            relative_path=clip.relative_path,
            original_file_size=clip.original_file_size,
            original_crc=clip.original_crc,
            default_sample_rate=clip.default_sample_rate,
            default_duration_samples=clip.default_duration_samples,
        )

        for candidate in candidate_sample_paths(clip, als_path):
            sample.resolved_path = str(candidate)
            sample.exists = candidate.exists() and candidate.is_file()

            if sample.exists:
                break

        samples[key] = sample

    sample = samples[key]
    sample.usage_count += 1
    sample.tracks.add(clip.track_name)
    sample.clips.add(clip.name)


def parse_locator_timing_counts(als_path):
    """Use the locator parser for timing counts without duplicating that logic."""
    try:
        import extract_locators

        tempo_events, time_signature_events, _manual_value, locators = (
            extract_locators.parse_als_locator_data(als_path)
        )
        return len(locators), len(tempo_events), len(time_signature_events)
    except Exception:
        return 0, 0, 0


def parse_project_manifest(als_path):
    """Parse a project manifest from an Ableton Live session file."""
    locator_count, tempo_count, time_signature_count = parse_locator_timing_counts(
        als_path
    )
    manifest = ProjectManifest(
        source_file=display_path(als_path),
        locator_count=locator_count,
        tempo_event_count=tempo_count,
        time_signature_event_count=time_signature_count,
    )
    path = []
    track_index = 0
    active_track_depth = None

    try:
        with als_path.open("rb") as als_file:
            first_two_bytes = als_file.read(2)
            als_file.seek(0)

            xml_stream = (
                gzip.GzipFile(fileobj=als_file)
                if first_two_bytes == b"\x1f\x8b"
                else als_file
            )

            with xml_stream:
                parser = ET.iterparse(xml_stream, events=("start", "end"))

                for event, element in parser:
                    if event == "start":
                        path.append(element.tag)

                        if element.tag == "Ableton":
                            manifest.ableton_creator = element.attrib.get("Creator", "")
                            manifest.ableton_major_version = element.attrib.get(
                                "MajorVersion", ""
                            )
                            manifest.ableton_minor_version = element.attrib.get(
                                "MinorVersion", ""
                            )

                        if element.tag in TRACK_TAGS and len(path) >= 3:
                            parent_tag = path[-2]

                            if parent_tag in ("Tracks", "ReturnTracks", "LiveSet"):
                                active_track_depth = len(path)
                        continue

                    if (
                        active_track_depth is not None
                        and len(path) == active_track_depth
                        and element.tag in TRACK_TAGS
                    ):
                        parent_tag = path[-2]
                        is_top_level_track = parent_tag in (
                            "Tracks",
                            "ReturnTracks",
                            "LiveSet",
                        )

                        if is_top_level_track:
                            track_index += 1
                            track, clips, devices, sample_updates = parse_track_element(
                                element,
                                track_index,
                                als_path,
                            )
                            manifest.tracks.append(track)
                            manifest.clips.extend(clips)
                            manifest.devices.extend(devices)

                            for clip in sample_updates:
                                update_sample_manifest(manifest.samples, clip, als_path)

                        active_track_depth = None
                        path.pop()
                        element.clear()
                        continue

                    path.pop()

                    if active_track_depth is None:
                        element.clear()
    except FileNotFoundError as exc:
        raise ProjectManifestError(
            "Ableton session file was not found.",
            [("path", display_path(als_path))],
        ) from exc
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while reading the Ableton session file.",
            [("path", display_path(als_path))],
        ) from exc
    except (gzip.BadGzipFile, EOFError, zlib.error) as exc:
        raise ProjectManifestError(
            "Ableton session file looks gzipped, but it could not be decompressed.",
            [("path", display_path(als_path))],
        ) from exc
    except ET.ParseError as exc:
        raise ProjectManifestError(
            "Ableton session file could not be parsed as XML.",
            [("path", display_path(als_path)), ("detail", exc)],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to read the Ableton session file.",
            [("path", display_path(als_path)), ("detail", exc)],
        ) from exc

    return manifest


def sample_records(manifest):
    """Return sample records in stable path/name order."""
    return sorted(
        manifest.samples.values(),
        key=lambda sample: (
            sample.path.lower(),
            sample.relative_path.lower(),
            sample.original_crc,
        ),
    )


def plugin_records(manifest):
    """Return plugin/effect manifest records, including native Ableton devices."""
    return list(manifest.devices)


def plugins_by_author(manifest):
    """Return devices sorted by manufacturer/author, then name."""
    return sorted(
        plugin_records(manifest),
        key=lambda item: (
            item.manufacturer.lower(),
            item.name.lower(),
            item.track_name.lower(),
            item.device_index,
        ),
    )


def plugins_by_name(manifest):
    """Return devices sorted by effect/plugin name, then manufacturer."""
    return sorted(
        plugin_records(manifest),
        key=lambda item: (
            item.name.lower(),
            item.manufacturer.lower(),
            item.track_name.lower(),
            item.device_index,
        ),
    )


def summary_payload(manifest):
    """Return high-level project counts."""
    sample_list = sample_records(manifest)
    devices = plugin_records(manifest)
    third_party = [item for item in devices if item.category == "third_party_plugin"]
    native = [item for item in devices if item.category != "third_party_plugin"]

    return {
        "track_count": len(manifest.tracks),
        "audio_track_count": sum(1 for item in manifest.tracks if item.track_type == "audio"),
        "midi_track_count": sum(1 for item in manifest.tracks if item.track_type == "midi"),
        "group_track_count": sum(1 for item in manifest.tracks if item.track_type == "group"),
        "return_track_count": sum(1 for item in manifest.tracks if item.track_type == "return"),
        "master_track_count": sum(1 for item in manifest.tracks if item.track_type == "master"),
        "clip_count": len(manifest.clips),
        "audio_clip_count": sum(1 for item in manifest.clips if item.clip_type == "audio"),
        "midi_clip_count": sum(1 for item in manifest.clips if item.clip_type == "midi"),
        "freeze_clip_count": sum(1 for item in manifest.clips if item.area == "freeze"),
        "sample_reference_count": sum(item.usage_count for item in sample_list),
        "unique_sample_count": len(sample_list),
        "missing_sample_count": sum(1 for item in sample_list if not item.exists),
        "existing_sample_count": sum(1 for item in sample_list if item.exists),
        "device_count": len(devices),
        "third_party_plugin_count": len(third_party),
        "ableton_native_device_count": len(native),
        "plugin_author_count": len({item.manufacturer for item in devices if item.manufacturer}),
        "locator_count": manifest.locator_count,
        "tempo_event_count": manifest.tempo_event_count,
        "time_signature_event_count": manifest.time_signature_event_count,
    }


def track_to_dict(track):
    """Convert a track record to a JSON-friendly dict."""
    return {
        "track_index": track.track_index,
        "track_id": track.track_id,
        "track_type": track.track_type,
        "name": track.name,
        "color": track.color,
        "clip_count": track.clip_count,
        "audio_clip_count": track.audio_clip_count,
        "midi_clip_count": track.midi_clip_count,
        "frozen_clip_count": track.frozen_clip_count,
        "disabled_clip_count": track.disabled_clip_count,
        "device_count": track.device_count,
        "plugin_count": track.plugin_count,
        "native_device_count": track.native_device_count,
    }


def clip_to_dict(clip):
    """Convert a clip record to a JSON-friendly dict."""
    return {
        "clip_id": clip.clip_id,
        "clip_type": clip.clip_type,
        "track_index": clip.track_index,
        "track_id": clip.track_id,
        "track_name": clip.track_name,
        "track_type": clip.track_type,
        "name": clip.name,
        "start_beat": clip.start_beat,
        "end_beat": clip.end_beat,
        "disabled": clip.disabled,
        "area": clip.area,
        "path": clip.path,
        "relative_path": clip.relative_path,
        "original_file_size": clip.original_file_size,
        "original_crc": clip.original_crc,
        "default_sample_rate": clip.default_sample_rate,
        "default_duration_samples": clip.default_duration_samples,
    }


def sample_to_dict(sample):
    """Convert a sample record to a JSON-friendly dict."""
    return {
        "path": sample.path,
        "relative_path": sample.relative_path,
        "original_file_size": sample.original_file_size,
        "original_crc": sample.original_crc,
        "default_sample_rate": sample.default_sample_rate,
        "default_duration_samples": sample.default_duration_samples,
        "usage_count": sample.usage_count,
        "tracks": sorted(sample.tracks),
        "clips": sorted(sample.clips),
        "resolved_path": sample.resolved_path,
        "exists": sample.exists,
    }


def device_to_dict(device):
    """Convert a device record to a JSON-friendly dict."""
    return {
        "track_index": device.track_index,
        "track_id": device.track_id,
        "track_name": device.track_name,
        "track_type": device.track_type,
        "device_index": device.device_index,
        "device_id": device.device_id,
        "device_type": device.device_type,
        "name": device.name,
        "user_name": device.user_name,
        "manufacturer": device.manufacturer,
        "format": device.format,
        "category": device.category,
        "enabled": device.enabled,
        "placeholder": device.placeholder,
        "preset_name": device.preset_name,
        "chain_path": device.chain_path,
    }


def manifest_payload(manifest):
    """Return the full JSON payload."""
    return {
        "metadata": {
            "generated_by": SCRIPT_NAME,
            "version": SCRIPT_VERSION,
            "source_file": manifest.source_file,
            "ableton": {
                "creator": manifest.ableton_creator,
                "major_version": manifest.ableton_major_version,
                "minor_version": manifest.ableton_minor_version,
            },
        },
        "summary": summary_payload(manifest),
        "tracks": [track_to_dict(item) for item in manifest.tracks],
        "clips": [clip_to_dict(item) for item in manifest.clips],
        "samples": [sample_to_dict(item) for item in sample_records(manifest)],
        "devices": [device_to_dict(item) for item in manifest.devices],
        "plugins_by_author": [device_to_dict(item) for item in plugins_by_author(manifest)],
        "plugins_by_name": [device_to_dict(item) for item in plugins_by_name(manifest)],
    }


def write_tsv(path, headers, rows):
    """Write one TSV table."""
    try:
        with path.open("w", encoding="utf-8", newline="") as out:
            writer = csv.writer(out, delimiter="\t", lineterminator="\n")
            writer.writerow(headers)
            writer.writerows(rows)
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while writing a TSV output file.",
            [("path", display_path(path))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to write a TSV output file.",
            [("path", display_path(path)), ("detail", exc)],
        ) from exc


def write_tsv_outputs(manifest, output_dir):
    """Write all TSV tables and return their paths."""
    outputs = []

    tracks_path = output_dir / "tracks.tsv"
    write_tsv(
        tracks_path,
        (
            "Track #",
            "Track ID",
            "Type",
            "Name",
            "Color",
            "Clips",
            "Audio Clips",
            "MIDI Clips",
            "Freeze Clips",
            "Disabled Clips",
            "Devices",
            "Third-Party Plugins",
            "Ableton Native Devices",
        ),
        [
            (
                item.track_index,
                item.track_id,
                item.track_type,
                item.name,
                item.color,
                item.clip_count,
                item.audio_clip_count,
                item.midi_clip_count,
                item.frozen_clip_count,
                item.disabled_clip_count,
                item.device_count,
                item.plugin_count,
                item.native_device_count,
            )
            for item in manifest.tracks
        ],
    )
    outputs.append(tracks_path)

    clips_path = output_dir / "clips.tsv"
    write_tsv(
        clips_path,
        (
            "Clip ID",
            "Type",
            "Track #",
            "Track",
            "Track Type",
            "Name",
            "Start Beat",
            "End Beat",
            "Disabled",
            "Area",
            "Path",
            "Relative Path",
            "Original File Size",
            "Original CRC",
            "Default Sample Rate",
            "Default Duration Samples",
        ),
        [
            (
                item.clip_id,
                item.clip_type,
                item.track_index,
                item.track_name,
                item.track_type,
                item.name,
                item.start_beat,
                item.end_beat,
                item.disabled,
                item.area,
                item.path,
                item.relative_path,
                item.original_file_size,
                item.original_crc,
                item.default_sample_rate,
                item.default_duration_samples,
            )
            for item in manifest.clips
        ],
    )
    outputs.append(clips_path)

    samples_path = output_dir / "samples.tsv"
    write_tsv(
        samples_path,
        (
            "Path",
            "Relative Path",
            "Original File Size",
            "Original CRC",
            "Default Sample Rate",
            "Default Duration Samples",
            "Usage Count",
            "Tracks",
            "Clips",
            "Resolved Path",
            "Exists",
        ),
        [
            (
                item.path,
                item.relative_path,
                item.original_file_size,
                item.original_crc,
                item.default_sample_rate,
                item.default_duration_samples,
                item.usage_count,
                "; ".join(sorted(item.tracks)),
                "; ".join(sorted(item.clips)),
                item.resolved_path,
                "true" if item.exists else "false",
            )
            for item in sample_records(manifest)
        ],
    )
    outputs.append(samples_path)

    devices_path = output_dir / "devices.tsv"
    device_headers = (
        "Track #",
        "Track",
        "Track Type",
        "Device #",
        "Device ID",
        "Device Type",
        "Name",
        "User Name",
        "Manufacturer",
        "Format",
        "Category",
        "Enabled",
        "Placeholder",
        "Preset Name",
        "Chain Path",
    )
    device_rows = [
        (
            item.track_index,
            item.track_name,
            item.track_type,
            item.device_index,
            item.device_id,
            item.device_type,
            item.name,
            item.user_name,
            item.manufacturer,
            item.format,
            item.category,
            item.enabled,
            item.placeholder,
            item.preset_name,
            item.chain_path,
        )
        for item in manifest.devices
    ]
    write_tsv(devices_path, device_headers, device_rows)
    outputs.append(devices_path)

    plugins_author_path = output_dir / "plugins_by_author.tsv"
    write_tsv(
        plugins_author_path,
        device_headers,
        [
            (
                item.track_index,
                item.track_name,
                item.track_type,
                item.device_index,
                item.device_id,
                item.device_type,
                item.name,
                item.user_name,
                item.manufacturer,
                item.format,
                item.category,
                item.enabled,
                item.placeholder,
                item.preset_name,
                item.chain_path,
            )
            for item in plugins_by_author(manifest)
        ],
    )
    outputs.append(plugins_author_path)

    plugins_name_path = output_dir / "plugins_by_name.tsv"
    write_tsv(
        plugins_name_path,
        device_headers,
        [
            (
                item.track_index,
                item.track_name,
                item.track_type,
                item.device_index,
                item.device_id,
                item.device_type,
                item.name,
                item.user_name,
                item.manufacturer,
                item.format,
                item.category,
                item.enabled,
                item.placeholder,
                item.preset_name,
                item.chain_path,
            )
            for item in plugins_by_name(manifest)
        ],
    )
    outputs.append(plugins_name_path)

    return outputs


def markdown_table(headers, rows):
    """Return a compact Markdown table."""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]

    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                safe_text(value).replace("\\", "\\\\").replace("|", "\\|")
                for value in row
            )
            + " |"
        )

    return "\n".join(lines)


def write_markdown_report(manifest, path):
    """Write the human-readable project inventory report."""
    summary = summary_payload(manifest)
    top_authors = {}

    for device in manifest.devices:
        top_authors[device.manufacturer] = top_authors.get(device.manufacturer, 0) + 1

    author_rows = sorted(
        top_authors.items(),
        key=lambda item: (-item[1], item[0].lower()),
    )[:12]
    device_rows = [
        (item.manufacturer, item.name, item.format, item.track_name)
        for item in plugins_by_author(manifest)[:20]
    ]
    sample_rows = [
        (
            item.usage_count,
            item.path or item.relative_path or item.original_crc,
            "yes" if item.exists else "no",
        )
        for item in sample_records(manifest)[:20]
    ]

    lines = [
        "# Project Inventory",
        "",
        f"- Source: `{Path(manifest.source_file).name}`",
        f"- Generated by: `{SCRIPT_NAME}`",
        f"- Version: `{SCRIPT_VERSION}`",
        "",
        "## Summary",
        "",
        markdown_table(
            ("Metric", "Value"),
            [(key.replace("_", " ").title(), value) for key, value in summary.items()],
        ),
        "",
        "## Plugin/Effect Authors",
        "",
        markdown_table(("Author", "Devices"), author_rows),
        "",
        "## First Plugin/Effect Rows",
        "",
        markdown_table(("Author", "Name", "Format", "Track"), device_rows),
        "",
        "## First Sample Rows",
        "",
        markdown_table(("Uses", "Sample", "Exists"), sample_rows),
        "",
    ]

    try:
        path.write_text("\n".join(lines), encoding="utf-8")
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while writing the Markdown report.",
            [("path", display_path(path))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to write the Markdown report.",
            [("path", display_path(path)), ("detail", exc)],
        ) from exc


def write_json_report(manifest, path, json_format):
    """Write the full JSON project manifest."""
    payload = manifest_payload(manifest)

    if json_format == "compact":
        dump_options = {"ensure_ascii": False, "separators": (",", ":")}
    else:
        dump_options = {"ensure_ascii": False, "indent": 2}

    try:
        with path.open("w", encoding="utf-8") as out:
            json.dump(payload, out, **dump_options)
            out.write("\n")
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while writing the JSON report.",
            [("path", display_path(path))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to write the JSON report.",
            [("path", display_path(path)), ("detail", exc)],
        ) from exc


def parse_args():
    """Parse and validate command-line arguments."""
    parser = ManifestArgumentParser(
        description="Extract Ableton project inventory, samples, devices, and plugins.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 src/extract_project_manifest.py song.als\n"
            "  python3 src/extract_project_manifest.py song.als --output-dir=song_manifest\n"
            "  python3 src/extract_project_manifest.py song.als --json-format=compact\n"
            "  python3 src/extract_project_manifest.py song.als --no-markdown"
        ),
    )
    parser.add_argument(
        "als_path",
        help="Path to the Ableton .als file. Plain XML and gzip-compressed ALS files are supported.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="PATH",
        help="Directory for Markdown, JSON, and TSV outputs. Default: <input filename>.project-manifest.",
    )
    parser.add_argument(
        "--json-format",
        choices=("pretty", "compact"),
        default="pretty",
        help="JSON formatting style. Default: pretty.",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Do not write project_manifest.json.",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Do not write project_inventory.md.",
    )
    parser.add_argument(
        "--no-tsv",
        action="store_true",
        help="Do not write TSV tables.",
    )
    return parser.parse_args()


def run(args):
    """Run extraction and write requested output files."""
    als_path = user_path(args.als_path)
    output_dir = user_path(args.output_dir) if args.output_dir else default_output_dir(als_path)
    started_at = time.perf_counter()

    ensure_output_dir(output_dir)
    manifest = parse_project_manifest(als_path)
    summary = summary_payload(manifest)
    outputs = []

    if not args.no_markdown:
        markdown_path = output_dir / "project_inventory.md"
        write_markdown_report(manifest, markdown_path)
        outputs.append(markdown_path)

    if not args.no_json:
        json_path = output_dir / "project_manifest.json"
        write_json_report(manifest, json_path, args.json_format)
        outputs.append(json_path)

    if not args.no_tsv:
        outputs.extend(write_tsv_outputs(manifest, output_dir))

    rows = [
        ("input", display_path(als_path)),
        ("tracks", summary["track_count"]),
        ("clips", summary["clip_count"]),
        ("samples", summary["unique_sample_count"]),
        ("devices", summary["device_count"]),
    ]
    rows.extend(("output", display_path(path)) for path in outputs)
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
    except ProjectManifestError as exc:
        print_report(
            "error",
            [("problem", exc.problem), *exc.details],
            stream=sys.stderr,
            status_color=FG_RED,
        )
        return 1

    print_report(
        result["status"],
        result["rows"],
        status_color=result["status_color"],
    )
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
