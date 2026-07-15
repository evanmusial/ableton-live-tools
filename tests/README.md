# Tests

This directory contains the first repeatable test harness for Ableton Live Tools.

The tests use Python's built-in `unittest` module and run the command-line tools
against `examples/validation/RYM_2026-03.als`. That makes them end-to-end tests:
they check argument parsing, file writing, exit codes, and output compatibility
with the canonical fixture files.

Run the tests from the repository root:

```bash
python3 -m unittest discover -s tests
```

The first test layer focuses on stable user-visible behavior:

- `extract_locators.py` high-resolution TSV and Mixcloud output.
- `extract_locators.py` metadata TSV and JSON output.
- `extract_locators.py` standard CSV, WebVTT chapter, CUE sheet, and REAPER marker CSV output.
- `extract_locators.py` Markdown report, Standard MIDI marker output, and optional MIDI timing-map output.
- `extract_locators.py` Logic Pro, Pro Tools, Cubase, and Nuendo Standard MIDI marker-map preset output.
- `extract_locators.py` Adobe Audition marker output, including its `.csv` filename with tab-separated contents.
- `extract_timeline.py` locator rows compared against locator metadata.
- `extract_project_manifest.py` Markdown, JSON, and TSV output presence plus semantic inventory counts.
- `check_project_health.py` Markdown and JSON report output plus expected missing-sample findings.
- `diff_als_semantic.py` Markdown and JSON output for an identical-file no-change comparison.
- `audit_project.py` bundled audit output, manifest/health reuse metadata, optional same-file semantic diff output, and expected fixture counts.
- Unified asset enumeration, preset-reference health findings, and streamed Live 12 Main/PreHear asset coverage.
- Ableton Live 12.4.3 compatibility across all six CLIs using the canonical project fixture with 12.4.3 creator metadata.
- Missing input files returning error exit code `1`.
- Command-line argument errors returning exit code `2`.

The locator JSON test normalizes `version` and `source_file`, because those
fields intentionally change across releases and local checkout paths.

As the tools grow, a healthy test set will probably have two layers:

- End-to-end CLI tests like these, which protect real user workflows.
- Smaller unit tests for pure timing/math helpers, which run faster and make
  edge cases easier to reason about.

## Benchmarks

Performance checks live beside the test approach, but they are intentionally
separate from pass/fail tests because timing varies across machines.

Run the validation benchmark for the current working tree:

```bash
python3 scripts/benchmark_validation.py
```

Compare the working tree against a git ref:

```bash
python3 scripts/benchmark_validation.py --compare-ref=main
```
