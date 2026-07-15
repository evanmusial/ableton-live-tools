#!/usr/bin/env python3

"""
check_project_health.py
Version: 2026.07.14

Author: Evan Musial <evan@evan.engineer>
License: Creative Commons Attribution-ShareAlike 4.0 International

License meaning:
  - This license requires that reusers give credit to the creator.
  - It allows reusers to distribute, remix, adapt, and build upon the material
    in any medium or format, even for commercial purposes.
  - If others remix, adapt, or build upon the material, they must license the
    modified material under identical terms.

Version 2026.07.14 notes:
  - Confirms compatibility with Ableton Live 12.4.3 through the full CLI
    compatibility suite.
  - Reports missing and outside-project preset file references from the unified
    asset inventory without treating serialized plugin state as unavailable.
  - Adds Ableton Live creator and version metadata to JSON, Markdown, and
    terminal health output.

Version 2026.06.15 notes:
  - Initial Project Health Checker release.
  - Reuses the streaming project manifest parser so health checks can run on
    large Ableton Live sets without loading the full uncompressed ALS XML tree.
  - Reports critical missing-sample and placeholder-plugin findings.
  - Reports warning/info findings for outside-project sample references, mixed
    sample rates, disabled clips/devices, frozen clips, unknown plugin authors,
    unnamed tracks, and unusually long sample paths.
  - Adds Markdown and JSON output for archival, collaboration, and CI workflows.
  - Tested and validated with Ableton Live 12.4.2 sessions.

What this script does:
  Project Health Checker reads an Ableton Live .als file and reports conditions
  that can make a project harder to open, archive, transfer, render, or hand to
  someone else. It is not a creative-quality checker and it does not decide
  whether a musical choice is good or bad. It simply highlights project-health
  risks that are commonly worth reviewing before a session leaves your machine.

Default behavior:
  - Prints a compact terminal report headed "Project Health Results".
  - Exits 0 when no critical findings are present.
  - Exits 1 when critical findings are present.
  - Exits 2 for command-line argument errors.

Arguments:
  als_path
      Path to the Ableton .als file.

      Example:
        python3 src/check_project_health.py song.als

  --markdown=PATH
      Write a human-readable Markdown health report.

      Example:
        python3 src/check_project_health.py song.als --markdown=health.md

  --json=PATH
      Write a JSON health report for automation and CI systems.

      Example:
        python3 src/check_project_health.py song.als --json=health.json

  --json-format=pretty|compact
      Choose whether JSON is human-readable or compact.
      Default: pretty

  --fail-on=critical|warning|any|none
      Choose which finding severities should return exit code 1.
      Default: critical

      Examples:
        python3 src/check_project_health.py song.als --fail-on=warning
        python3 src/check_project_health.py song.als --fail-on=none --json=health.json
"""

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys
import time

from extract_project_manifest import (
    ProjectManifestError,
    asset_records,
    display_path,
    parse_project_manifest,
    plugin_records,
    safe_text,
    sample_records,
    summary_payload,
    user_path,
)


SCRIPT_NAME = "check_project_health.py"
SCRIPT_VERSION = "2026.07.14"
REPORT_TITLE = "Project Health Results"
LONG_PATH_WARNING_LENGTH = 240

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
FG_GREEN = "\033[38;5;114m"
FG_RED = "\033[38;5;203m"
FG_YELLOW = "\033[38;5;221m"
FG_MUTED = "\033[38;5;244m"
FG_VALUE = "\033[38;5;250m"
FG_TITLE = "\033[38;5;153m"


@dataclass
class HealthFinding:
    """One health finding with enough detail for terminal, Markdown, and JSON."""

    severity: str
    category: str
    message: str
    count: int = 0
    items: list = field(default_factory=list)


class HealthArgumentParser(argparse.ArgumentParser):
    """Argparse subclass that reports argument errors in the tool's style."""

    def error(self, message):
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


def path_is_inside(candidate, root):
    """Return True when candidate is inside root, with Python 3.9 support."""
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def sample_label(sample):
    """Return the most useful display label for a sample reference."""
    return (
        sample.path
        or sample.relative_path
        or sample.original_crc
        or sample.original_file_size
        or "(unnamed sample reference)"
    )


def asset_label(asset):
    """Return a concise label for a file-backed asset reference."""
    label = asset.path or asset.relative_path or asset.original_crc or "(unnamed asset)"
    context = ", ".join(sorted(asset.devices)) or ", ".join(sorted(asset.tracks))
    return f"{label} [{context}]" if context else label


def sample_candidate_path(sample, als_path):
    """Return the best filesystem path candidate for a sample reference."""
    if sample.resolved_path:
        return Path(sample.resolved_path).expanduser()
    if sample.path:
        return Path(sample.path).expanduser()
    if sample.relative_path:
        relative = Path(sample.relative_path)
        return relative if relative.is_absolute() else als_path.parent / relative
    return None


def severity_counts(findings):
    """Count findings by severity while preserving explicit zeroes."""
    counts = {"critical": 0, "warning": 0, "info": 0}

    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1

    return counts


def health_status(findings):
    """Return the overall health status from finding severities."""
    counts = severity_counts(findings)

    if counts["critical"]:
        return "critical"
    if counts["warning"]:
        return "warning"
    return "healthy"


def status_color(status):
    """Return the report color for a health status."""
    if status == "critical":
        return FG_RED
    if status == "warning":
        return FG_YELLOW
    return FG_GREEN


def exit_code_for(findings, fail_on):
    """Return script-friendly exit status for the requested failure threshold."""
    counts = severity_counts(findings)

    if fail_on == "none":
        return 0
    if fail_on == "critical":
        return 1 if counts["critical"] else 0
    if fail_on == "warning":
        return 1 if counts["critical"] or counts["warning"] else 0
    return 1 if findings else 0


def finding_to_dict(finding):
    """Convert one finding to JSON-friendly data."""
    return {
        "severity": finding.severity,
        "category": finding.category,
        "message": finding.message,
        "count": finding.count,
        "items": list(finding.items),
    }


def build_health_findings(manifest, als_path):
    """Inspect a parsed manifest and return ordered health findings."""
    findings = []
    samples = sample_records(manifest)
    assets = asset_records(manifest)
    devices = plugin_records(manifest)
    summary = summary_payload(manifest)
    project_root = als_path.parent.resolve(strict=False)

    missing_samples = [sample for sample in samples if not sample.exists]
    if missing_samples:
        findings.append(
            HealthFinding(
                "critical",
                "missing_samples",
                "Sample references are missing or could not be resolved.",
                count=len(missing_samples),
                items=[sample_label(sample) for sample in missing_samples[:50]],
            )
        )

    placeholder_plugins = [device for device in devices if device.placeholder == "true"]
    if placeholder_plugins:
        findings.append(
            HealthFinding(
                "critical",
                "placeholder_plugins",
                "Plugin devices are placeholders and may be unavailable.",
                count=len(placeholder_plugins),
                items=[
                    f"{device.track_name}: {device.manufacturer} {device.name}".strip()
                    for device in placeholder_plugins[:50]
                ],
            )
        )

    outside_project_samples = []
    long_path_samples = []

    for sample in samples:
        candidate = sample_candidate_path(sample, als_path)
        label = sample_label(sample)

        if candidate is not None:
            normalized = candidate.resolve(strict=False)
            if not path_is_inside(normalized, project_root):
                outside_project_samples.append(label)

            if len(str(normalized)) > LONG_PATH_WARNING_LENGTH:
                long_path_samples.append(str(normalized))
        elif len(label) > LONG_PATH_WARNING_LENGTH:
            long_path_samples.append(label)

    if outside_project_samples:
        findings.append(
            HealthFinding(
                "warning",
                "outside_project_samples",
                "Sample references appear to point outside the ALS file's folder.",
                count=len(outside_project_samples),
                items=outside_project_samples[:50],
            )
        )

    if long_path_samples:
        findings.append(
            HealthFinding(
                "warning",
                "long_sample_paths",
                f"Sample paths exceed {LONG_PATH_WARNING_LENGTH} characters.",
                count=len(long_path_samples),
                items=long_path_samples[:50],
            )
        )

    preset_assets = [asset for asset in assets if asset.asset_type == "preset"]
    missing_presets = [asset for asset in preset_assets if not asset.exists]
    if missing_presets:
        findings.append(
            HealthFinding(
                "warning",
                "missing_preset_references",
                (
                    "Referenced preset files were not found locally. Device state may "
                    "still be embedded in the ALS, but the named preset files could not "
                    "be verified."
                ),
                count=len(missing_presets),
                items=[asset_label(asset) for asset in missing_presets[:50]],
            )
        )

    external_presets = [asset for asset in preset_assets if not asset.inside_project]
    if external_presets:
        findings.append(
            HealthFinding(
                "warning",
                "external_preset_references",
                "Preset file references point outside the ALS file's folder.",
                count=len(external_presets),
                items=[asset_label(asset) for asset in external_presets[:50]],
            )
        )

    sample_rates = sorted(
        {
            sample.default_sample_rate
            for sample in samples
            if sample.default_sample_rate not in ("", None)
        }
    )
    if len(sample_rates) > 1:
        findings.append(
            HealthFinding(
                "warning",
                "mixed_sample_rates",
                "Referenced samples report multiple default sample rates.",
                count=len(sample_rates),
                items=sample_rates,
            )
        )

    disabled_clips = [clip for clip in manifest.clips if clip.disabled == "true"]
    if disabled_clips:
        findings.append(
            HealthFinding(
                "warning",
                "disabled_clips",
                "Disabled clips are present.",
                count=len(disabled_clips),
                items=[
                    f"{clip.track_name}: {clip.name or clip.clip_id}"
                    for clip in disabled_clips[:50]
                ],
            )
        )

    disabled_devices = [device for device in devices if device.enabled == "false"]
    if disabled_devices:
        findings.append(
            HealthFinding(
                "warning",
                "disabled_devices",
                "Disabled devices/plugins are present.",
                count=len(disabled_devices),
                items=[
                    f"{device.track_name}: {device.manufacturer} {device.name}".strip()
                    for device in disabled_devices[:50]
                ],
            )
        )

    unknown_plugins = [
        device
        for device in devices
        if device.category == "third_party_plugin" and device.manufacturer == "Unknown"
    ]
    if unknown_plugins:
        findings.append(
            HealthFinding(
                "warning",
                "unknown_plugin_authors",
                "Third-party plugins with unknown manufacturers are present.",
                count=len(unknown_plugins),
                items=[f"{device.track_name}: {device.name}" for device in unknown_plugins[:50]],
            )
        )

    unnamed_tracks = [track for track in manifest.tracks if not track.name]
    if unnamed_tracks:
        findings.append(
            HealthFinding(
                "warning",
                "unnamed_tracks",
                "Tracks without names are present.",
                count=len(unnamed_tracks),
                items=[f"track {track.track_index} ({track.track_type})" for track in unnamed_tracks[:50]],
            )
        )

    if summary["freeze_clip_count"]:
        findings.append(
            HealthFinding(
                "info",
                "frozen_clips",
                "Freeze clips are present; include freeze/sample media when archiving.",
                count=summary["freeze_clip_count"],
                items=[],
            )
        )

    if not samples:
        findings.append(
            HealthFinding(
                "info",
                "no_sample_references",
                "No sample/audio file references were detected.",
                count=0,
                items=[],
            )
        )

    return findings


def health_payload(manifest, findings, als_path, fail_on):
    """Return a JSON-friendly health report payload."""
    status = health_status(findings)

    return {
        "metadata": {
            "generated_by": SCRIPT_NAME,
            "version": SCRIPT_VERSION,
            "source_file": display_path(als_path),
            "fail_on": fail_on,
            "ableton": {
                "creator": manifest.ableton_creator,
                "major_version": manifest.ableton_major_version,
                "minor_version": manifest.ableton_minor_version,
            },
        },
        "status": status,
        "exit_code": exit_code_for(findings, fail_on),
        "summary": summary_payload(manifest),
        "finding_counts": severity_counts(findings),
        "findings": [finding_to_dict(finding) for finding in findings],
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


def write_markdown_report(manifest, findings, path, als_path, fail_on):
    """Write a human-readable Project Health report."""
    payload = health_payload(manifest, findings, als_path, fail_on)
    lines = [
        "# Project Health",
        "",
        f"- Source: `{Path(als_path).name}`",
        f"- Generated by: `{SCRIPT_NAME}`",
        f"- Version: `{SCRIPT_VERSION}`",
        f"- Ableton creator: `{payload['metadata']['ableton']['creator'] or 'unknown'}`",
        f"- Ableton major version: `{payload['metadata']['ableton']['major_version'] or 'unknown'}`",
        f"- Ableton minor version: `{payload['metadata']['ableton']['minor_version'] or 'unknown'}`",
        f"- Status: `{payload['status']}`",
        f"- Exit code with current threshold: `{payload['exit_code']}`",
        "",
        "## Finding Counts",
        "",
        markdown_table(
            ("Severity", "Findings"),
            sorted(payload["finding_counts"].items()),
        ),
        "",
        "## Project Summary",
        "",
        markdown_table(
            ("Metric", "Value"),
            [(key.replace("_", " ").title(), value) for key, value in payload["summary"].items()],
        ),
        "",
        "## Findings",
        "",
    ]

    if not findings:
        lines.extend(["No project-health findings were detected.", ""])
    else:
        for finding in findings:
            lines.extend(
                [
                    f"### {finding.severity.title()}: {finding.category}",
                    "",
                    finding.message,
                    "",
                    f"- Count: `{finding.count}`",
                ]
            )
            if finding.items:
                lines.append("- First affected items:")
                lines.extend(f"  - `{safe_text(item)}`" for item in finding.items)
            lines.append("")

    ensure_parent_directory(path)

    try:
        path.write_text("\n".join(lines), encoding="utf-8")
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while writing the Markdown health report.",
            [("path", display_path(path))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to write the Markdown health report.",
            [("path", display_path(path)), ("detail", exc)],
        ) from exc


def write_json_report(manifest, findings, path, als_path, fail_on, json_format):
    """Write a JSON Project Health report."""
    payload = health_payload(manifest, findings, als_path, fail_on)
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
            "Permission denied while writing the JSON health report.",
            [("path", display_path(path))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to write the JSON health report.",
            [("path", display_path(path)), ("detail", exc)],
        ) from exc


def parse_args():
    """Parse and validate command-line arguments."""
    parser = HealthArgumentParser(
        description="Check Ableton project health from an .als session file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 src/check_project_health.py song.als\n"
            "  python3 src/check_project_health.py song.als --markdown=health.md\n"
            "  python3 src/check_project_health.py song.als --json=health.json\n"
            "  python3 src/check_project_health.py song.als --fail-on=warning\n"
            "  python3 src/check_project_health.py song.als --fail-on=none --json=health.json"
        ),
    )
    parser.add_argument(
        "als_path",
        help="Path to the Ableton .als file. Plain XML and gzip-compressed ALS files are supported.",
    )
    parser.add_argument(
        "--markdown",
        metavar="PATH",
        help="Write a Markdown project-health report to PATH.",
    )
    parser.add_argument(
        "-j",
        "--json",
        metavar="PATH",
        help="Write a JSON project-health report to PATH.",
    )
    parser.add_argument(
        "--json-format",
        choices=("pretty", "compact"),
        default="pretty",
        help="JSON formatting style. Default: pretty.",
    )
    parser.add_argument(
        "--fail-on",
        choices=("critical", "warning", "any", "none"),
        default="critical",
        help="Finding severity threshold that returns exit code 1. Default: critical.",
    )
    return parser.parse_args()


def run(args):
    """Run health checks and write requested output files."""
    als_path = user_path(args.als_path)
    markdown_path = user_path(args.markdown) if args.markdown else None
    json_path = user_path(args.json) if args.json else None
    started_at = time.perf_counter()

    manifest = parse_project_manifest(als_path)
    findings = build_health_findings(manifest, als_path)
    status = health_status(findings)
    counts = severity_counts(findings)
    outputs = []

    if markdown_path:
        write_markdown_report(manifest, findings, markdown_path, als_path, args.fail_on)
        outputs.append(markdown_path)

    if json_path:
        write_json_report(
            manifest,
            findings,
            json_path,
            als_path,
            args.fail_on,
            args.json_format,
        )
        outputs.append(json_path)

    rows = [
        ("input", display_path(als_path)),
        ("ableton", manifest.ableton_creator or "unknown"),
        ("critical", counts["critical"]),
        ("warnings", counts["warning"]),
        ("info", counts["info"]),
    ]
    rows.extend(("output", display_path(path)) for path in outputs)
    rows.append(("elapsed", format_elapsed(started_at)))

    return {
        "status": status,
        "status_color": status_color(status),
        "rows": rows,
        "exit_code": exit_code_for(findings, args.fail_on),
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
