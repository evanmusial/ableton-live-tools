#!/usr/bin/env python3

"""
audit_project.py
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
  - Includes the unified assets.tsv and JSON asset inventory in audit bundles.
  - Carries missing/external preset findings and Ableton creator/version metadata
    into the reused Project Health outputs.

Version 2026.06.30 notes:
  - Adds a project audit bundle for archive, collaboration, and handoff review.
  - Reuses the parsed Project Manifest object for health checks and audit
    summaries, so the default audit does not rerun the manifest parser for each
    report.
  - Writes a top-level Markdown and JSON audit, Project Manifest outputs,
    Project Health outputs, and optional Semantic ALS Diff outputs when a
    baseline file is provided.

What this script does:
  Ableton Live Tools already has focused tools for project inventory, health
  checks, and semantic diffs. Project Audit Bundle stitches those checks into
  one repeatable handoff folder without shelling out to the individual CLIs.

Default output:
  If --output-dir is omitted, the script writes a directory named
  <input filename>.project-audit in the current working directory.

  Files written by default:
    project_audit.md
    project_audit.json
    project_inventory.md
    project_manifest.json
    project_health.md
    project_health.json
    assets.tsv
    tracks.tsv
    clips.tsv
    samples.tsv
    devices.tsv
    plugins_by_author.tsv
    plugins_by_name.tsv

  If --before is provided, the bundle also includes:
    semantic_diff.md
    semantic_diff.json

Performance note:
  The audit parses the current project manifest once and reuses that result for
  the manifest, health, and top-level audit files. Full locator/timeline exports
  remain separate commands so this bundle does not add hidden full-output passes.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time

from check_project_health import (
    build_health_findings,
    exit_code_for,
    health_payload,
    severity_counts,
    write_json_report as write_health_json_report,
    write_markdown_report as write_health_markdown_report,
)
from diff_als_semantic import (
    build_semantic_diff,
    clip_entries,
    device_entries,
    diff_payload,
    locator_entries,
    sample_entries,
    semantic_snapshot,
    tempo_entries,
    time_signature_entries,
    track_entries,
    write_json_report as write_diff_json_report,
    write_markdown_report as write_diff_markdown_report,
)
from extract_locators import LocatorToolError, extract_locator_data
from extract_project_manifest import (
    ProjectManifestError,
    display_path,
    ensure_output_dir,
    parse_project_manifest,
    safe_text,
    summary_payload,
    user_path,
    write_json_report as write_manifest_json_report,
    write_markdown_report as write_manifest_markdown_report,
    write_tsv_outputs,
)


SCRIPT_NAME = "audit_project.py"
SCRIPT_VERSION = "2026.07.14"
REPORT_TITLE = "Project Audit Results"
MAX_REPORT_FINDINGS = 8

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
FG_GREEN = "\033[38;5;114m"
FG_RED = "\033[38;5;203m"
FG_YELLOW = "\033[38;5;221m"
FG_MUTED = "\033[38;5;244m"
FG_VALUE = "\033[38;5;250m"
FG_TITLE = "\033[38;5;153m"


class AuditArgumentParser(argparse.ArgumentParser):
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


def default_output_dir(als_path):
    """Return the default project audit output directory."""
    return Path.cwd() / f"{als_path.name}.project-audit"


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


def dump_options(json_format):
    """Return json.dump keyword arguments for the requested formatting style."""
    if json_format == "compact":
        return {"ensure_ascii": False, "separators": (",", ":")}
    return {"ensure_ascii": False, "indent": 2}


def diff_snapshot_from_manifest(manifest, als_path):
    """
    Build a semantic-diff snapshot while reusing the already parsed manifest.

    Locator signatures still require the locator parser, but this avoids parsing
    the current project's manifest a second time when an audit includes --before.
    """
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


def audit_status(health_report, semantic_diff):
    """Return the top-level audit status."""
    if health_report["status"] == "critical":
        return "critical"
    if semantic_diff is not None and semantic_diff["status"] == "different":
        return "review"
    if health_report["status"] == "warning":
        return "warning"
    return "healthy"


def status_color(status):
    """Return the report color for an audit status."""
    if status == "critical":
        return FG_RED
    if status in ("warning", "review"):
        return FG_YELLOW
    return FG_GREEN


def diff_summary(semantic_diff):
    """Return compact semantic-diff counts for the audit payload."""
    if semantic_diff is None:
        return None

    added = sum(section["added_count"] for section in semantic_diff["sections"])
    removed = sum(section["removed_count"] for section in semantic_diff["sections"])

    return {
        "status": semantic_diff["status"],
        "change_count": semantic_diff["change_count"],
        "summary_change_count": len(semantic_diff["summary_changes"]),
        "added_count": added,
        "removed_count": removed,
    }


def handoff_summary(health_report, semantic_diff):
    """Return a small, script-friendly handoff summary."""
    return {
        "health_status": health_report["status"],
        "semantic_diff_status": semantic_diff["status"] if semantic_diff else "not_run",
        "has_missing_samples": any(
            finding["category"] == "missing_samples"
            for finding in health_report["findings"]
        ),
        "has_placeholder_plugins": any(
            finding["category"] == "placeholder_plugins"
            for finding in health_report["findings"]
        ),
        "has_outside_project_samples": any(
            finding["category"] == "outside_project_samples"
            for finding in health_report["findings"]
        ),
        "has_disabled_material": any(
            finding["category"] in ("disabled_clips", "disabled_devices")
            for finding in health_report["findings"]
        ),
    }


def audit_payload(
    manifest,
    health_report,
    semantic_diff,
    outputs,
    als_path,
    before_path,
    fail_on,
    fail_on_diff,
    exit_code,
):
    """Return the JSON-friendly top-level audit payload."""
    status = audit_status(health_report, semantic_diff)

    return {
        "metadata": {
            "generated_by": SCRIPT_NAME,
            "version": SCRIPT_VERSION,
            "source_file": display_path(als_path),
            "before_file": display_path(before_path) if before_path else None,
            "fail_on": fail_on,
            "fail_on_diff": fail_on_diff,
            "ableton": {
                "creator": manifest.ableton_creator,
                "major_version": manifest.ableton_major_version,
                "minor_version": manifest.ableton_minor_version,
            },
            "performance": {
                "manifest_reused_for_health": True,
                "full_locator_exports_written": False,
                "full_timeline_exports_written": False,
                "semantic_diff_requested": semantic_diff is not None,
            },
        },
        "status": status,
        "exit_code": exit_code,
        "handoff": handoff_summary(health_report, semantic_diff),
        "summary": summary_payload(manifest),
        "health": {
            "status": health_report["status"],
            "finding_counts": health_report["finding_counts"],
            "findings": health_report["findings"],
        },
        "semantic_diff": diff_summary(semantic_diff),
        "outputs": {
            key: display_path(path)
            for key, path in sorted(outputs.items())
        },
    }


def top_findings(health_report):
    """Return the most useful finding rows for the Markdown audit."""
    return [
        (
            finding["severity"],
            finding["category"],
            finding["count"],
            finding["message"],
        )
        for finding in health_report["findings"][:MAX_REPORT_FINDINGS]
    ]


def write_audit_markdown(payload, path):
    """Write the top-level human-readable Project Audit report."""
    summary = payload["summary"]
    health = payload["health"]
    semantic_diff = payload["semantic_diff"]
    handoff = payload["handoff"]

    lines = [
        "# Project Audit",
        "",
        f"- Source: `{Path(payload['metadata']['source_file']).name}`",
        f"- Generated by: `{SCRIPT_NAME}`",
        f"- Version: `{SCRIPT_VERSION}`",
        f"- Ableton creator: `{payload['metadata']['ableton']['creator'] or 'unknown'}`",
        f"- Status: `{payload['status']}`",
        f"- Exit code with current thresholds: `{payload['exit_code']}`",
        "",
        "## Handoff Summary",
        "",
        markdown_table(
            ("Check", "Value"),
            [
                ("Health status", handoff["health_status"]),
                ("Semantic diff status", handoff["semantic_diff_status"]),
                ("Missing samples", "yes" if handoff["has_missing_samples"] else "no"),
                (
                    "Placeholder plugins",
                    "yes" if handoff["has_placeholder_plugins"] else "no",
                ),
                (
                    "Outside-project samples",
                    "yes" if handoff["has_outside_project_samples"] else "no",
                ),
                (
                    "Disabled material",
                    "yes" if handoff["has_disabled_material"] else "no",
                ),
            ],
        ),
        "",
        "## Project Summary",
        "",
        markdown_table(
            ("Metric", "Value"),
            [
                ("Tracks", summary["track_count"]),
                ("Clips", summary["clip_count"]),
                ("Unique samples", summary["unique_sample_count"]),
                ("Missing samples", summary["missing_sample_count"]),
                ("Devices", summary["device_count"]),
                ("Third-party plugins", summary["third_party_plugin_count"]),
                ("Locators", summary["locator_count"]),
                ("Tempo events", summary["tempo_event_count"]),
                ("Time-signature events", summary["time_signature_event_count"]),
            ],
        ),
        "",
        "## Health Findings",
        "",
        markdown_table(
            ("Severity", "Findings"),
            sorted(health["finding_counts"].items()),
        ),
        "",
    ]

    finding_rows = top_findings(health)
    if finding_rows:
        lines.extend(
            [
                markdown_table(
                    ("Severity", "Category", "Count", "Message"),
                    finding_rows,
                ),
                "",
            ]
        )
    else:
        lines.extend(["No project-health findings were detected.", ""])

    lines.extend(["## Semantic Diff", ""])

    if semantic_diff is None:
        lines.extend(["No baseline was provided, so semantic diff was not run.", ""])
    else:
        lines.extend(
            [
                markdown_table(
                    ("Metric", "Value"),
                    [
                        ("Status", semantic_diff["status"]),
                        ("Change count", semantic_diff["change_count"]),
                        ("Summary changes", semantic_diff["summary_change_count"]),
                        ("Added rows", semantic_diff["added_count"]),
                        ("Removed rows", semantic_diff["removed_count"]),
                    ],
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Generated Files",
            "",
            markdown_table(
                ("Output", "Path"),
                [
                    (key.replace("_", " ").title(), value)
                    for key, value in sorted(payload["outputs"].items())
                ],
            ),
            "",
        ]
    )

    try:
        path.write_text("\n".join(lines), encoding="utf-8")
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while writing the Markdown audit report.",
            [("path", display_path(path))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to write the Markdown audit report.",
            [("path", display_path(path)), ("detail", exc)],
        ) from exc


def write_audit_json(payload, path, json_format):
    """Write the top-level JSON Project Audit report."""
    try:
        with path.open("w", encoding="utf-8") as out:
            json.dump(payload, out, **dump_options(json_format))
            out.write("\n")
    except PermissionError as exc:
        raise ProjectManifestError(
            "Permission denied while writing the JSON audit report.",
            [("path", display_path(path))],
        ) from exc
    except OSError as exc:
        raise ProjectManifestError(
            "Unable to write the JSON audit report.",
            [("path", display_path(path)), ("detail", exc)],
        ) from exc


def parse_args():
    """Parse and validate command-line arguments."""
    parser = AuditArgumentParser(
        description="Build a bundled Ableton project audit report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 src/audit_project.py song.als\n"
            "  python3 src/audit_project.py song.als --output-dir=song_audit\n"
            "  python3 src/audit_project.py after.als --before=before.als\n"
            "  python3 src/audit_project.py song.als --fail-on=warning --no-tsv"
        ),
    )
    parser.add_argument(
        "als_path",
        help="Path to the Ableton .als file. Plain XML and gzip-compressed ALS files are supported.",
    )
    parser.add_argument(
        "--before",
        metavar="PATH",
        help="Optional older/baseline .als file for semantic diff output.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="PATH",
        help="Directory for audit outputs. Default: <input filename>.project-audit.",
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
        help="Project-health severity threshold that returns exit code 1. Default: critical.",
    )
    parser.add_argument(
        "--fail-on-diff",
        action="store_true",
        help="Return exit code 1 when --before detects semantic differences.",
    )
    parser.add_argument(
        "--no-tsv",
        action="store_true",
        help="Do not write the detailed manifest TSV tables.",
    )
    return parser.parse_args()


def write_bundle_outputs(
    manifest,
    findings,
    health_report,
    semantic_diff_data,
    diff_sections,
    diff_summary_changes,
    output_dir,
    als_path,
    before_path,
    args,
    exit_code,
):
    """Write all requested bundle files and return output path labels."""
    outputs = {}

    inventory_markdown = output_dir / "project_inventory.md"
    write_manifest_markdown_report(manifest, inventory_markdown)
    outputs["project_inventory_markdown"] = inventory_markdown

    manifest_json = output_dir / "project_manifest.json"
    write_manifest_json_report(manifest, manifest_json, args.json_format)
    outputs["project_manifest_json"] = manifest_json

    if not args.no_tsv:
        for path in write_tsv_outputs(manifest, output_dir):
            outputs[path.stem] = path

    health_markdown = output_dir / "project_health.md"
    write_health_markdown_report(
        manifest,
        findings,
        health_markdown,
        als_path,
        args.fail_on,
    )
    outputs["project_health_markdown"] = health_markdown

    health_json = output_dir / "project_health.json"
    write_health_json_report(
        manifest,
        findings,
        health_json,
        als_path,
        args.fail_on,
        args.json_format,
    )
    outputs["project_health_json"] = health_json

    if semantic_diff_data is not None:
        diff_markdown = output_dir / "semantic_diff.md"
        write_diff_markdown_report(
            before_path,
            als_path,
            diff_summary_changes,
            diff_sections,
            diff_markdown,
        )
        outputs["semantic_diff_markdown"] = diff_markdown

        diff_json = output_dir / "semantic_diff.json"
        write_diff_json_report(
            before_path,
            als_path,
            diff_summary_changes,
            diff_sections,
            diff_json,
            args.json_format,
        )
        outputs["semantic_diff_json"] = diff_json

    audit_markdown = output_dir / "project_audit.md"
    audit_json = output_dir / "project_audit.json"
    outputs["project_audit_markdown"] = audit_markdown
    outputs["project_audit_json"] = audit_json

    payload = audit_payload(
        manifest,
        health_report,
        semantic_diff_data,
        outputs,
        als_path,
        before_path,
        args.fail_on,
        args.fail_on_diff,
        exit_code,
    )
    write_audit_markdown(payload, audit_markdown)
    write_audit_json(payload, audit_json, args.json_format)

    return outputs, payload


def run(args):
    """Run the audit and write the bundle."""
    als_path = user_path(args.als_path)
    before_path = user_path(args.before) if args.before else None
    output_dir = user_path(args.output_dir) if args.output_dir else default_output_dir(als_path)
    started_at = time.perf_counter()

    ensure_output_dir(output_dir)

    manifest = parse_project_manifest(als_path)
    findings = build_health_findings(manifest, als_path)
    health_report = health_payload(manifest, findings, als_path, args.fail_on)
    semantic_diff_data = None
    diff_summary_changes = []
    diff_sections = []

    if before_path:
        before_snapshot = semantic_snapshot(before_path)
        after_snapshot = diff_snapshot_from_manifest(manifest, als_path)
        diff_summary_changes, diff_sections = build_semantic_diff(
            before_snapshot,
            after_snapshot,
        )
        semantic_diff_data = diff_payload(
            before_path,
            als_path,
            diff_summary_changes,
            diff_sections,
        )

    exit_code = exit_code_for(findings, args.fail_on)
    if (
        args.fail_on_diff
        and semantic_diff_data is not None
        and semantic_diff_data["status"] == "different"
    ):
        exit_code = 1

    outputs, payload = write_bundle_outputs(
        manifest,
        findings,
        health_report,
        semantic_diff_data,
        diff_sections,
        diff_summary_changes,
        output_dir,
        als_path,
        before_path,
        args,
        exit_code,
    )

    counts = severity_counts(findings)
    summary = summary_payload(manifest)
    rows = [
        ("input", display_path(als_path)),
        ("output", display_path(output_dir)),
        ("tracks", summary["track_count"]),
        ("clips", summary["clip_count"]),
        ("assets", summary["unique_asset_count"]),
        ("samples", summary["unique_sample_count"]),
        ("critical", counts["critical"]),
        ("warnings", counts["warning"]),
        ("diff", semantic_diff_data["status"] if semantic_diff_data else "not_run"),
        ("files", len(outputs)),
        ("elapsed", format_elapsed(started_at)),
    ]

    return {
        "status": payload["status"],
        "status_color": status_color(payload["status"]),
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
