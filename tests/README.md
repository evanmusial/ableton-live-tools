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
- `extract_locators.py` standard CSV, WebVTT chapter, and CUE sheet output.
- `extract_locators.py` Markdown report, Standard MIDI marker output, and optional MIDI timing-map output.
- `extract_locators.py` Adobe Audition marker output, including its `.csv` filename with tab-separated contents.
- `extract_timeline.py` locator rows compared against locator metadata.
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
