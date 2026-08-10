# Code Commenting Style

Comments in Ableton Live Tools should shorten the time needed to understand or
safely change the code. They are not a second narration of the implementation.

## Baseline

- Every Python module in `src/` and `scripts/` has a module docstring describing
  its purpose and any important operating constraints.
- Every class and function in `src/` and `scripts/`, including nested parser
  callbacks and returned lookup functions, has a concise docstring.
- Test modules, test classes, and shared test helpers are documented. Individual
  tests normally rely on descriptive names; add a comment only when the fixture,
  normalization, or expected behavior is not evident from the test body.

The documentation-quality test enforces the production and maintenance-script
baseline. It intentionally does not require ceremonial docstrings on every test
method.

## Function and class docstrings

- Start with a direct summary such as `Return`, `Build`, `Write`, `Parse`, or
  another verb that describes the contract.
- End the summary sentence with punctuation.
- Use a one-line docstring when the name, arguments, and return value make the
  contract clear.
- Add a short explanatory paragraph when a function has a non-obvious invariant,
  ordering guarantee, performance strategy, file-format rule, or state machine.
- Explain parameters and return values only when their meaning is not clear from
  names and nearby types. Do not restate the signature mechanically.

## Inline comments

Use inline comments to explain why the implementation has a surprising shape:

- undocumented or version-sensitive Ableton XML behavior;
- parser path, depth, buffering, and memory-release invariants;
- numerical edge cases such as tempo integration and clock normalization;
- interoperability constraints imposed by an export format; or
- test-fixture normalization that would otherwise look like weakened coverage.

Keep a comment immediately above the smallest block it explains. Prefer one
complete thought over a running commentary through every branch.

Avoid comments that:

- translate an assignment, loop, or condition into English;
- duplicate user documentation or command help;
- preserve release history better suited to a changelog or release note;
- describe behavior the code no longer has; or
- compensate for a function that should instead be split or renamed.

## Review checklist

Before merging a comment-only or comment-bearing change, check that:

1. the comment explains intent, an invariant, or a maintenance hazard;
2. the wording matches the current behavior and nearby terminology;
3. the explanation is no longer than needed to prevent misunderstanding;
4. production and maintenance definitions still pass the documentation-quality
   test; and
5. syntax and behavioral tests remain unchanged and passing.
