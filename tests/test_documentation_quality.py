"""Regression checks for production and maintenance-script docstrings."""

import ast
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTED_DIRECTORIES = (REPO_ROOT / "src", REPO_ROOT / "scripts")
DEFINITION_TYPES = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


class DocumentationQualityTests(unittest.TestCase):
    """Keep the repository's concise docstring baseline from regressing."""

    def test_production_definitions_have_concise_docstrings(self):
        """Require module and definition docstrings with complete summaries."""
        failures = []

        for directory in DOCUMENTED_DIRECTORIES:
            for path in sorted(directory.glob("*.py")):
                relative_path = path.relative_to(REPO_ROOT)
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                module_docstring = ast.get_docstring(tree)

                if not module_docstring:
                    failures.append(f"{relative_path}: missing module docstring")

                for node in ast.walk(tree):
                    if not isinstance(node, DEFINITION_TYPES):
                        continue

                    docstring = ast.get_docstring(node)
                    location = f"{relative_path}:{node.lineno} {node.name}"

                    if not docstring:
                        failures.append(f"{location}: missing docstring")
                        continue

                    summary = docstring.splitlines()[0].strip()
                    if not summary.endswith((".", "!", "?")):
                        failures.append(
                            f"{location}: summary must end with punctuation"
                        )

        self.assertEqual(failures, [], "\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
