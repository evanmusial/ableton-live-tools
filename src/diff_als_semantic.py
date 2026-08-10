#!/usr/bin/env python3

"""
Compare two Ableton sessions by project meaning instead of raw XML text.

The diff builds stable signatures for the inventory categories the parsers
understand deliberately, including tracks, clips, samples, devices, locators,
tempo events, and time signatures. Incidental serialization changes are ignored.

See ``docs/Semantic ALS Diff.md`` for CLI and comparison documentation.

Author: Evan Musial <evan@evan.engineer>
License: Creative Commons Attribution-ShareAlike 4.0 International
"""

import argparse
from collections import Counter
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys
import time

from extract_locators import LocatorToolError, extract_locator_data
from extract_project_manifest import (
    ProjectManifestError,
    display_path,
    parse_project_manifest,
    plugin_records,
    safe_text,
    sample_records,
    summary_payload,
    user_path,
)


SCRIPT_NAME = "diff_als_semantic.py"
SCRIPT_VERSION = "2026.06.15"
REPORT_TITLE = "Semantic ALS Diff Results"
MAX_REPORT_ITEMS = 80

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
FG_GREEN = "\033[38;5;114m"
FG_RED = "\033[38;5;203m"
FG_YELLOW = "\033[38;5;221m"
FG_MUTED = "\033[38;5;244m"
FG_VALUE = "\033[38;5;250m"
FG_TITLE = "\033[38;5;153m"


@dataclass
class DiffSection:
    """Added and removed semantic inventory rows for one comparison category."""

    name: str
    added: list = field(default_factory=list)
    removed: list = field(default_factory=list)

    @property
    def change_count(self):
        """Return total changes in this section."""
        return len(self.added) + len(self.removed)


class DiffArgumentParser(argparse.ArgumentParser):
    """Argparse subclass that reports argument errors in the tool's style."""

    def error(self, message):
        """Report a usage error in the standard CLI format and exit with 2."""
        print_report(
            "error",
            [("problem", message)],
            stream=sys.stderr,
            status_color=FG_RED,
        )
        raise SystemExit(2)


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
    """Print one aligned key/value row."""
    label_text = colorize(f"{label:<10}", FG_MUTED, stream=stream)
    value_text = colorize(str(value), FG_VALUE, stream=stream)
    print(f"  {label_text} {value_text}", file=stream)


def print_report(status, rows, *, stream=sys.stdout, status_color=FG_GREEN):
    """Print a compact status report matching the rest of the tools."""
    title = colorize(REPORT_TITLE, FG_TITLE, stream=stream, bold=True)
    print(title, file=stream)
    print_kv("status", colorize(status, status_color, stream=stream), stream=stream)

    for label, value in rows:
        print_kv(label, value, stream=stream)


def format_elapsed(started_at):
    """Return elapsed wall-clock time with stable CLI precision."""
    return f"{time.perf_counter() - started_at:.3f}s"


def ensure_parent_directory(path):
    """Create a file output's parent directory when needed."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while creating the output directory.",
            [("path", display_path(path.parent))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to create the output directory.",
            [("path", display_path(path.parent)), ("detail", exc)],
        ) from exc


def rounded(value):
    """Format numeric values tightly enough for stable semantic signatures."""
    try:
        return f"{float(value):.6f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return safe_text(value)


def track_entries(manifest):
    """Return semantic signatures for top-level tracks."""
    return [
        "|".join(
            (
                str(track.track_index),
                track.track_type,
                safe_text(track.name),
                f"clips={track.clip_count}",
                f"devices={track.device_count}",
                f"plugins={track.plugin_count}",
                f"native={track.native_device_count}",
                f"color={track.color}",
            )
        )
        for track in manifest.tracks
    ]


def clip_entries(manifest):
    """Return semantic signatures for clips."""
    return [
        "|".join(
            (
                f"track={clip.track_index}:{safe_text(clip.track_name)}",
                clip.clip_type,
                safe_text(clip.name),
                f"start={rounded(clip.start_beat)}",
                f"end={rounded(clip.end_beat)}",
                f"disabled={clip.disabled}",
                f"area={clip.area}",
                f"sample={safe_text(clip.path or clip.relative_path or clip.original_crc)}",
            )
        )
        for clip in manifest.clips
    ]


def sample_entries(manifest):
    """Return semantic signatures for unique sample/audio references."""
    return [
        "|".join(
            (
                safe_text(sample.path),
                safe_text(sample.relative_path),
                f"size={sample.original_file_size}",
                f"crc={sample.original_crc}",
                f"rate={sample.default_sample_rate}",
                f"samples={sample.default_duration_samples}",
                f"uses={sample.usage_count}",
            )
        )
        for sample in sample_records(manifest)
    ]


def device_entries(manifest):
    """Return semantic signatures for native devices and third-party plugins."""
    return [
        "|".join(
            (
                f"track={device.track_index}:{safe_text(device.track_name)}",
                f"device={device.device_index}",
                device.category,
                device.format,
                safe_text(device.manufacturer),
                safe_text(device.name),
                f"enabled={device.enabled}",
                f"placeholder={device.placeholder}",
                f"preset={safe_text(device.preset_name)}",
            )
        )
        for device in plugin_records(manifest)
    ]


def locator_entries(locator_extraction):
    """Return semantic signatures for arrangement locators."""
    return [
        "|".join(
            (
                f"beat={rounded(row.absolute_beats)}",
                f"seconds={rounded(row.absolute_seconds)}",
                safe_text(row.name),
            )
        )
        for row in sorted(locator_extraction.rows, key=lambda item: item.absolute_beats)
    ]


def tempo_entries(locator_extraction):
    """Return semantic signatures for tempo map events."""
    return [
        f"beat={rounded(beat)}|bpm={rounded(bpm)}"
        for beat, bpm in locator_extraction.tempo_events
    ]


def time_signature_entries(locator_extraction):
    """Return semantic signatures for time-signature map events."""
    return [
        f"beat={rounded(event.beat)}|signature={event.numerator}/{event.denominator}"
        for event in locator_extraction.time_signature_events
    ]


def semantic_snapshot(als_path):
    """Parse one ALS file and return the semantic inventories we compare."""
    manifest = parse_project_manifest(als_path)
    locator_extraction = extract_locator_data(als_path)

    return {
        "summary": summary_payload(manifest),
        "tracks": track_entries(manifest),
        "clips": clip_entries(manifest),
        "samples": sample_entries(manifest),
        "devices_and_plugins": device_entries(manifest),
        "locators": locator_entries(locator_extraction),
        "tempo_events": tempo_entries(locator_extraction),
        "time_signature_events": time_signature_entries(locator_extraction),
    }


def multiset_delta(before_items, after_items):
    """Return sorted added/removed items while preserving duplicate signatures."""
    before = Counter(before_items)
    after = Counter(after_items)

    added = sorted((after - before).elements())
    removed = sorted((before - after).elements())

    return added, removed


def build_semantic_diff(before_snapshot, after_snapshot):
    """Return summary changes and section deltas between two snapshots."""
    summary_changes = []

    for key in sorted(set(before_snapshot["summary"]) | set(after_snapshot["summary"])):
        before_value = before_snapshot["summary"].get(key)
        after_value = after_snapshot["summary"].get(key)

        if before_value != after_value:
            summary_changes.append(
                {
                    "metric": key,
                    "before": before_value,
                    "after": after_value,
                }
            )

    sections = []
    for name in (
        "tracks",
        "clips",
        "samples",
        "devices_and_plugins",
        "locators",
        "tempo_events",
        "time_signature_events",
    ):
        added, removed = multiset_delta(before_snapshot[name], after_snapshot[name])
        sections.append(DiffSection(name=name, added=added, removed=removed))

    return summary_changes, sections


def section_to_dict(section):
    """Convert one diff section to JSON-friendly data."""
    return {
        "name": section.name,
        "added_count": len(section.added),
        "removed_count": len(section.removed),
        "added": section.added,
        "removed": section.removed,
    }


def diff_payload(before_path, after_path, summary_changes, sections):
    """Return the full JSON-friendly semantic diff payload."""
    change_count = len(summary_changes) + sum(section.change_count for section in sections)

    return {
        "metadata": {
            "generated_by": SCRIPT_NAME,
            "version": SCRIPT_VERSION,
            "before_file": display_path(before_path),
            "after_file": display_path(after_path),
        },
        "status": "different" if change_count else "same",
        "change_count": change_count,
        "summary_changes": summary_changes,
        "sections": [section_to_dict(section) for section in sections],
    }


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


def write_markdown_report(before_path, after_path, summary_changes, sections, path):
    """Write a human-readable Markdown semantic diff report."""
    payload = diff_payload(before_path, after_path, summary_changes, sections)
    lines = [
        "# Semantic ALS Diff",
        "",
        f"- Before: `{Path(before_path).name}`",
        f"- After: `{Path(after_path).name}`",
        f"- Generated by: `{SCRIPT_NAME}`",
        f"- Version: `{SCRIPT_VERSION}`",
        f"- Status: `{payload['status']}`",
        f"- Change count: `{payload['change_count']}`",
        "",
        "## Summary Changes",
        "",
    ]

    if summary_changes:
        lines.append(
            markdown_table(
                ("Metric", "Before", "After"),
                [
                    (
                        change["metric"].replace("_", " ").title(),
                        change["before"],
                        change["after"],
                    )
                    for change in summary_changes
                ],
            )
        )
    else:
        lines.append("No summary count changes were detected.")

    lines.extend(["", "## Semantic Sections", ""])

    for section in sections:
        if not section.change_count:
            continue

        lines.extend(
            [
                f"### {section.name.replace('_', ' ').title()}",
                "",
                f"- Added: `{len(section.added)}`",
                f"- Removed: `{len(section.removed)}`",
                "",
            ]
        )

        if section.added:
            lines.append("#### Added")
            lines.append("")
            lines.extend(f"- `{safe_text(item)}`" for item in section.added[:MAX_REPORT_ITEMS])
            lines.append("")

        if section.removed:
            lines.append("#### Removed")
            lines.append("")
            lines.extend(f"- `{safe_text(item)}`" for item in section.removed[:MAX_REPORT_ITEMS])
            lines.append("")

    if not any(section.change_count for section in sections):
        lines.append("No semantic inventory changes were detected.")
        lines.append("")

    ensure_parent_directory(path)

    try:
        path.write_text("\n".join(lines), encoding="utf-8")
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while writing the Markdown semantic diff report.",
            [("path", display_path(path))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to write the Markdown semantic diff report.",
            [("path", display_path(path)), ("detail", exc)],
        ) from exc


def write_json_report(before_path, after_path, summary_changes, sections, path, json_format):
    """Write a JSON semantic diff report."""
    payload = diff_payload(before_path, after_path, summary_changes, sections)
    dump_options = (
        {"ensure_ascii": False, "separators": (",", ":")}
        if json_format == "compact"
        else {"ensure_ascii": False, "indent": 2}
    )

    ensure_parent_directory(path)

    try:
        with path.open("w", encoding="utf-8") as out:
            json.dump(payload, out, **dump_options)
            out.write("\n")
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while writing the JSON semantic diff report.",
            [("path", display_path(path))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to write the JSON semantic diff report.",
            [("path", display_path(path)), ("detail", exc)],
        ) from exc


def parse_args():
    """Parse and validate command-line arguments."""
    parser = DiffArgumentParser(
        description="Compare two Ableton .als files by extracted project meaning.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 src/diff_als_semantic.py before.als after.als\n"
            "  python3 src/diff_als_semantic.py before.als after.als --markdown=diff.md\n"
            "  python3 src/diff_als_semantic.py before.als after.als --json=diff.json\n"
            "  python3 src/diff_als_semantic.py before.als after.als --no-fail-on-diff"
        ),
    )
    parser.add_argument(
        "before_als",
        help="Older/baseline Ableton .als file. Plain XML and gzip-compressed ALS files are supported.",
    )
    parser.add_argument(
        "after_als",
        help="Newer/comparison Ableton .als file. Plain XML and gzip-compressed ALS files are supported.",
    )
    parser.add_argument(
        "--markdown",
        metavar="PATH",
        help="Write a Markdown semantic diff report to PATH.",
    )
    parser.add_argument(
        "-j",
        "--json",
        metavar="PATH",
        help="Write a JSON semantic diff report to PATH.",
    )
    parser.add_argument(
        "--json-format",
        choices=("pretty", "compact"),
        default="pretty",
        help="JSON formatting style. Default: pretty.",
    )
    parser.add_argument(
        "--no-fail-on-diff",
        action="store_true",
        help="Return exit code 0 even when semantic differences are detected.",
    )
    return parser.parse_args()


def run(args):
    """Run the semantic diff and write requested output files."""
    before_path = user_path(args.before_als)
    after_path = user_path(args.after_als)
    markdown_path = user_path(args.markdown) if args.markdown else None
    json_path = user_path(args.json) if args.json else None
    started_at = time.perf_counter()

    before_snapshot = semantic_snapshot(before_path)
    after_snapshot = semantic_snapshot(after_path)
    summary_changes, sections = build_semantic_diff(before_snapshot, after_snapshot)
    payload = diff_payload(before_path, after_path, summary_changes, sections)
    outputs = []

    if markdown_path:
        write_markdown_report(before_path, after_path, summary_changes, sections, markdown_path)
        outputs.append(markdown_path)

    if json_path:
        write_json_report(
            before_path,
            after_path,
            summary_changes,
            sections,
            json_path,
            args.json_format,
        )
        outputs.append(json_path)

    added = sum(len(section.added) for section in sections)
    removed = sum(len(section.removed) for section in sections)
    rows = [
        ("before", display_path(before_path)),
        ("after", display_path(after_path)),
        ("changes", payload["change_count"]),
        ("added", added),
        ("removed", removed),
    ]
    rows.extend(("output", display_path(path)) for path in outputs)
    rows.append(("elapsed", format_elapsed(started_at)))

    exit_code = 0 if args.no_fail_on_diff or payload["status"] == "same" else 1

    return {
        "status": payload["status"],
        "status_color": FG_YELLOW if payload["status"] == "different" else FG_GREEN,
        "rows": rows,
        "exit_code": exit_code,
    }


def main():
    """CLI entry point."""
    args = parse_args()

    try:
        result = run(args)
    except (ProjectManifestError, LocatorToolError) as exc:
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
