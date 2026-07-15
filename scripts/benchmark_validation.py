#!/usr/bin/env python3

"""
Benchmark Ableton Live Tools against the canonical validation ALS file.

The benchmark intentionally uses the public CLI commands instead of importing
internal functions. That makes the numbers match what users experience,
including argument parsing, XML parsing, event building, and file writing.
"""

from __future__ import annotations

import argparse
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_ALS = REPO_ROOT / "examples" / "validation" / "RYM_2026-03.als"
ELAPSED_RE = re.compile(r"^\s*elapsed\s+([0-9.]+)s\s*$", re.MULTILINE)

BENCHMARK_CASES = (
    {
        "name": "Locators metadata TSV + JSON",
        "script": "extract_locators.py",
        "args": (
            "{als}",
            "--add-offset=27",
            "--columns=all",
            "--output={tmp}/locators_metadata.tsv",
            "--json={tmp}/locators_metadata.json",
            "--json-format=pretty",
        ),
    },
    {
        "name": "Timeline locator-only TSV",
        "script": "extract_timeline.py",
        "args": (
            "{als}",
            "--precision=3",
            "--event-types=locator",
            "--columns=wall_seconds,name,event_id,absolute_beats",
            "--output={tmp}/timeline_locators.tsv",
        ),
    },
    {
        "name": "Timeline beat-grid core TSV",
        "script": "extract_timeline.py",
        "args": (
            "{als}",
            "--grid=beats",
            "--event-types=tempo,time_signature,key,locator",
            "--columns=wall_time,event_type,song_position,absolute_beats,name,value,sample_index",
            "--output={tmp}/timeline_grid.tsv",
        ),
    },
    {
        "name": "Timeline full TSV + JSON",
        "script": "extract_timeline.py",
        "args": (
            "{als}",
            "--output={tmp}/timeline.tsv",
            "--json={tmp}/timeline.json",
        ),
    },
    {
        "name": "Project manifest full bundle",
        "script": "extract_project_manifest.py",
        "args": (
            "{als}",
            "--output-dir={tmp}/project_manifest",
            "--json-format=compact",
        ),
    },
    {
        "name": "Project audit bundle",
        "script": "audit_project.py",
        "compare_ref": False,
        "args": (
            "{als}",
            "--fail-on=none",
            "--output-dir={tmp}/project_audit",
            "--json-format=compact",
        ),
    },
)

REF_SCRIPT_DEPENDENCIES = {
    "extract_project_manifest.py": ("extract_locators.py",),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark the Ableton Live Tools validation fixture.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=7,
        help="Number of measured runs per benchmark case. Default: 7.",
    )
    parser.add_argument(
        "--compare-ref",
        metavar="GIT_REF",
        help="Optionally compare the working tree against a git ref, such as main.",
    )
    parser.add_argument(
        "--show-runs",
        action="store_true",
        help="Print individual elapsed times after the summary table.",
    )
    args = parser.parse_args()

    if args.runs < 1:
        parser.error("--runs must be at least 1")

    return args


def run_command(command: list[str]) -> float:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Benchmark command failed with exit code "
            f"{result.returncode}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    match = ELAPSED_RE.search(result.stdout)

    if not match:
        raise RuntimeError(f"Benchmark command did not report elapsed time:\n{result.stdout}")

    return float(match.group(1))


def materialize_ref_scripts(git_ref: str, temp_dir: Path) -> dict[str, Path]:
    scripts = {}

    script_names = sorted(
        {
            case["script"]
            for case in BENCHMARK_CASES
            if case.get("compare_ref", True)
        }
    )

    for script_name in script_names:
        output_path = temp_dir / f"{git_ref.replace('/', '_')}_{script_name}"
        result = subprocess.run(
            ["git", "show", f"{git_ref}:src/{script_name}"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Unable to read src/{script_name} from {git_ref}:\n{result.stderr}"
            )

        output_path.write_text(result.stdout, encoding="utf-8")
        scripts[script_name] = output_path

    dependency_names = sorted(
        {
            dependency
            for script_name in script_names
            for dependency in REF_SCRIPT_DEPENDENCIES.get(script_name, ())
        }
    )

    for dependency_name in dependency_names:
        output_path = temp_dir / dependency_name
        result = subprocess.run(
            ["git", "show", f"{git_ref}:src/{dependency_name}"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Unable to read src/{dependency_name} from {git_ref}:\n{result.stderr}"
            )

        output_path.write_text(result.stdout, encoding="utf-8")

    return scripts


def working_tree_scripts() -> dict[str, Path]:
    return {
        case["script"]: REPO_ROOT / "src" / case["script"]
        for case in BENCHMARK_CASES
    }


def build_command(
    python_executable: str,
    script_path: Path,
    case_args: tuple[str, ...],
    output_dir: Path,
) -> list[str]:
    formatted_args = [
        arg.format(als=VALIDATION_ALS, tmp=output_dir)
        for arg in case_args
    ]
    return [python_executable, "-B", str(script_path), *formatted_args]


def run_suite(
    scripts: dict[str, Path],
    runs: int,
    python_executable: str,
    temp_root: Path,
    label: str,
) -> dict[str, list[float]]:
    results = {}

    for case in BENCHMARK_CASES:
        if case["script"] not in scripts:
            continue

        elapsed_values = []

        for run_index in range(runs):
            output_dir = temp_root / label / case["name"].replace(" ", "_") / str(run_index)
            output_dir.mkdir(parents=True, exist_ok=True)
            command = build_command(
                python_executable,
                scripts[case["script"]],
                case["args"],
                output_dir,
            )
            elapsed_values.append(run_command(command))

        results[case["name"]] = elapsed_values

    return results


def change_percent(baseline: float, current: float) -> str:
    if baseline <= 0:
        return ""

    change = ((baseline - current) / baseline) * 100
    return f"{change:.1f}% faster" if change >= 0 else f"{abs(change):.1f}% slower"


def print_summary(current_results, baseline_results=None) -> None:
    if baseline_results:
        print("| Case | Baseline Median | Current Median | Change |")
        print("| --- | ---: | ---: | ---: |")

        for case in BENCHMARK_CASES:
            name = case["name"]
            current = statistics.median(current_results[name])
            if name in baseline_results:
                baseline = statistics.median(baseline_results[name])
                print(
                    f"| {name} | `{baseline:.3f}s` | `{current:.3f}s` | "
                    f"`{change_percent(baseline, current)}` |"
                )
            else:
                print(f"| {name} | n/a | `{current:.3f}s` | `current only` |")
    else:
        print("| Case | Median |")
        print("| --- | ---: |")

        for case in BENCHMARK_CASES:
            name = case["name"]
            current = statistics.median(current_results[name])
            print(f"| {name} | `{current:.3f}s` |")


def print_runs(label: str, results: dict[str, list[float]]) -> None:
    print(f"\n{label} runs:")

    for case in BENCHMARK_CASES:
        name = case["name"]
        if name not in results:
            continue
        values = ", ".join(f"{value:.3f}s" for value in results[name])
        print(f"- {name}: {values}")


def main() -> int:
    args = parse_args()
    python_executable = sys.executable or "python3"

    with tempfile.TemporaryDirectory(prefix="ableton-live-tools-benchmark-") as temp:
        temp_root = Path(temp)
        baseline_results = None

        if args.compare_ref:
            baseline_scripts = materialize_ref_scripts(args.compare_ref, temp_root)
            baseline_results = run_suite(
                baseline_scripts,
                args.runs,
                python_executable,
                temp_root,
                "baseline",
            )

        current_results = run_suite(
            working_tree_scripts(),
            args.runs,
            python_executable,
            temp_root,
            "current",
        )

    print_summary(current_results, baseline_results)

    if args.show_runs:
        if baseline_results:
            print_runs("Baseline", baseline_results)
        print_runs("Current", current_results)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
