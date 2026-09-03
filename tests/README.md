# Tests

This directory contains the first repeatable test harness for Ableton Live Tools.

The tests use Python's built-in `unittest` module. The end-to-end layer runs the
command-line tools against `examples/validation/RYM_2026-03.als`, checking
argument parsing, file writing, exit codes, and output compatibility with the
canonical fixture files. A focused unit layer covers helper branches that are
too narrow or defensive to exercise cleanly through full CLI fixture runs.

Run the tests from the repository root:

```bash
python3 -m unittest discover -s tests
```

Run coverage with `coverage.py` and subprocess capture from the repository root:

```bash
COVERAGE_PROCESS_START=.coveragerc \
PYTHONPATH=tests/coverage_site:$PYTHONPATH \
PYTHONDONTWRITEBYTECODE=1 \
python3 -m unittest discover -s tests
python3 -m coverage combine
python3 -m coverage report
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
- `check_project_health.py` Markdown and JSON report output plus expected missing-sample findings and failure-threshold behavior.
- `diff_als_semantic.py` Markdown and JSON output for an identical-file no-change comparison plus a locator-name change comparison.
- `audit_project.py` bundled audit output, manifest/health reuse metadata, optional same-file semantic diff output, and expected fixture counts.
- Unified asset enumeration, preset-reference health findings, and streamed Live 12 Main/PreHear asset coverage.
- Ableton Live 12.4.3 and 12.4.5 compatibility across all six CLIs using the canonical project fixture with rewritten creator metadata.
- Missing input files returning error exit code `1`.
- Command-line argument errors returning exit code `2`.

The locator JSON test normalizes `version` and `source_file`, because those
fields intentionally change across releases and local checkout paths.

`test_documentation_quality.py` also checks that every production and
maintenance-script module, class, and function has a concise docstring with a
complete summary sentence. Individual end-to-end tests rely on descriptive test
names unless a fixture or normalization needs additional explanation.

The test set has two layers:

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
