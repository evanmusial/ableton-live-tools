import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples" / "validation"
ALS_PATH = EXAMPLES_DIR / "RYM_2026-03.als"
LOCATORS_SCRIPT = REPO_ROOT / "src" / "extract_locators.py"
TIMELINE_SCRIPT = REPO_ROOT / "src" / "extract_timeline.py"
MANIFEST_SCRIPT = REPO_ROOT / "src" / "extract_project_manifest.py"
HEALTH_SCRIPT = REPO_ROOT / "src" / "check_project_health.py"
DIFF_SCRIPT = REPO_ROOT / "src" / "diff_als_semantic.py"


class CliValidationTests(unittest.TestCase):
    """
    End-to-end CLI checks against the canonical validation ALS file.

    These tests intentionally use the command-line scripts instead of importing
    private functions. That makes them slower than unit tests, but it verifies
    the exact workflow users run: argument parsing, file writing, exit codes,
    and fixture-compatible output.
    """

    def run_cli(self, *args, check=True):
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        result = subprocess.run(
            ["python3", *map(str, args)],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        if check and result.returncode != 0:
            self.fail(
                "Command failed with exit code "
                f"{result.returncode}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )

        return result

    def assert_files_match(self, expected_path, actual_path):
        expected = Path(expected_path).read_text(encoding="utf-8")
        actual = Path(actual_path).read_text(encoding="utf-8")
        self.assertEqual(actual, expected)

    def assert_binary_files_match(self, expected_path, actual_path):
        expected = Path(expected_path).read_bytes()
        actual = Path(actual_path).read_bytes()
        self.assertEqual(actual, expected)

    def test_extract_locators_highres_fixtures_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            actual_tsv = temp_path / "RYM_2026-03_locators_highres.tsv"
            actual_mixcloud = temp_path / "RYM_2026-03_mixcloud_highres.txt"

            self.run_cli(
                LOCATORS_SCRIPT,
                ALS_PATH,
                "--precision=3",
                "--output",
                actual_tsv,
                "--mixcloud",
                actual_mixcloud,
                "--time-header=Time",
                "--label-header=Title",
                "--add-offset=27",
            )

            self.assert_files_match(
                EXAMPLES_DIR / "RYM_2026-03_locators_highres.tsv",
                actual_tsv,
            )
            self.assert_files_match(
                EXAMPLES_DIR / "RYM_2026-03_mixcloud_highres.txt",
                actual_mixcloud,
            )

    def test_extract_locators_metadata_fixtures_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            actual_tsv = temp_path / "RYM_2026-03_locators_metadata.tsv"
            actual_json = temp_path / "RYM_2026-03_locators_metadata.json"

            self.run_cli(
                LOCATORS_SCRIPT,
                ALS_PATH,
                "--add-offset=27",
                "--columns=all",
                "--output",
                actual_tsv,
                "--json",
                actual_json,
                "--json-format=pretty",
            )

            self.assert_files_match(
                EXAMPLES_DIR / "RYM_2026-03_locators_metadata.tsv",
                actual_tsv,
            )

            expected = json.loads(
                (EXAMPLES_DIR / "RYM_2026-03_locators_metadata.json").read_text(
                    encoding="utf-8"
                )
            )
            actual = json.loads(actual_json.read_text(encoding="utf-8"))

            # The fixture records the absolute path from the machine that
            # generated it. The script version also changes as releases are
            # cut. Normalize both fields so clones in other locations can still
            # verify the semantic JSON output.
            expected["version"] = "<normalized>"
            actual["version"] = "<normalized>"
            expected["source_file"] = "<normalized>"
            actual["source_file"] = "<normalized>"
            self.assertEqual(actual, expected)

    def test_extract_locators_audition_marker_fixture_matches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            actual_tsv = temp_path / "RYM_2026-03_locators.tsv"
            actual_audition = temp_path / "RYM_2026-03_audition_markers.csv"

            self.run_cli(
                LOCATORS_SCRIPT,
                ALS_PATH,
                "--add-offset=27",
                "--output",
                actual_tsv,
                "--audition",
                actual_audition,
            )

            self.assert_files_match(
                EXAMPLES_DIR / "RYM_2026-03_audition_markers.csv",
                actual_audition,
            )

    def test_extract_locators_interchange_format_fixtures_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            actual_tsv = temp_path / "RYM_2026-03_locators.tsv"
            actual_csv = temp_path / "RYM_2026-03_locators_metadata.csv"
            actual_webvtt = temp_path / "RYM_2026-03_chapters.vtt"
            actual_cue = temp_path / "RYM_2026-03_tracks.cue"
            actual_reaper = temp_path / "RYM_2026-03_reaper_markers.csv"

            self.run_cli(
                LOCATORS_SCRIPT,
                ALS_PATH,
                "--add-offset=27",
                "--columns=all",
                "--output",
                actual_tsv,
                "--csv",
                actual_csv,
                "--webvtt",
                actual_webvtt,
                "--cue",
                actual_cue,
                "--cue-audio=RYM_2026-03.wav",
                "--reaper",
                actual_reaper,
            )

            self.assert_files_match(
                EXAMPLES_DIR / "RYM_2026-03_locators_metadata.csv",
                actual_csv,
            )
            self.assert_files_match(
                EXAMPLES_DIR / "RYM_2026-03_chapters.vtt",
                actual_webvtt,
            )
            self.assert_files_match(
                EXAMPLES_DIR / "RYM_2026-03_tracks.cue",
                actual_cue,
            )
            self.assert_files_match(
                EXAMPLES_DIR / "RYM_2026-03_reaper_markers.csv",
                actual_reaper,
            )

    def test_extract_locators_markdown_and_midi_fixtures_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            actual_tsv = temp_path / "RYM_2026-03_locators.tsv"
            actual_markdown = temp_path / "RYM_2026-03_locators_metadata.md"
            actual_midi = temp_path / "RYM_2026-03_markers.mid"

            self.run_cli(
                LOCATORS_SCRIPT,
                ALS_PATH,
                "--add-offset=27",
                "--columns=all",
                "--output",
                actual_tsv,
                "--markdown",
                actual_markdown,
                "--midi",
                actual_midi,
            )

            self.assert_files_match(
                EXAMPLES_DIR / "RYM_2026-03_locators_metadata.md",
                actual_markdown,
            )
            self.assert_binary_files_match(
                EXAMPLES_DIR / "RYM_2026-03_markers.mid",
                actual_midi,
            )

    def test_extract_locators_midi_timing_map_fixture_matches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            actual_tsv = temp_path / "RYM_2026-03_locators.tsv"
            actual_midi = temp_path / "RYM_2026-03_markers_timing.mid"

            self.run_cli(
                LOCATORS_SCRIPT,
                ALS_PATH,
                "--add-offset=27",
                "--columns=all",
                "--output",
                actual_tsv,
                "--midi",
                actual_midi,
                "--midi-timing-map",
            )

            self.assert_binary_files_match(
                EXAMPLES_DIR / "RYM_2026-03_markers_timing.mid",
                actual_midi,
            )

    def test_extract_locators_daw_midi_presets_write_marker_maps(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            actual_tsv = temp_path / "RYM_2026-03_locators.tsv"
            daw_outputs = {
                "logic": temp_path / "logic_markers.mid",
                "pro_tools": temp_path / "pro_tools_markers.mid",
                "cubase": temp_path / "cubase_markers.mid",
                "nuendo": temp_path / "nuendo_markers.mid",
            }

            self.run_cli(
                LOCATORS_SCRIPT,
                ALS_PATH,
                "--output",
                actual_tsv,
                "--logic-midi",
                daw_outputs["logic"],
                "--pro-tools-midi",
                daw_outputs["pro_tools"],
                "--cubase-midi",
                daw_outputs["cubase"],
                "--nuendo-midi",
                daw_outputs["nuendo"],
            )

            expected_track_names = {
                "logic": b"Logic Pro Marker Map",
                "pro_tools": b"Pro Tools Marker Map",
                "cubase": b"Cubase Marker Map",
                "nuendo": b"Nuendo Marker Map",
            }

            for key, path in daw_outputs.items():
                payload = path.read_bytes()
                self.assertTrue(payload.startswith(b"MThd"), key)
                self.assertIn(b"MTrk", payload, key)
                self.assertIn(expected_track_names[key], payload, key)
                self.assertIn(b"HAYLA - Fall Again", payload, key)

    def test_timeline_locator_rows_match_locator_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            actual_tsv = Path(temp_dir) / "RYM_2026-03.timeline-locators.tsv"

            self.run_cli(
                TIMELINE_SCRIPT,
                ALS_PATH,
                "--precision=3",
                "--event-types=locator",
                "--columns=wall_seconds,name,event_id,absolute_beats",
                "--output",
                actual_tsv,
            )

            metadata_rows = [
                line.rstrip("\n").split("\t")
                for line in (EXAMPLES_DIR / "RYM_2026-03_locators_metadata.tsv")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            timeline_rows = [
                line.rstrip("\n").split("\t")
                for line in actual_tsv.read_text(encoding="utf-8").splitlines()
            ]

            expected_rows = [["Wall Seconds", "Name", "Event ID", "Absolute Beats"]]

            for row in metadata_rows[1:]:
                expected_rows.append([row[5], row[1], row[10], row[7]])

            self.assertEqual(timeline_rows, expected_rows)

    def test_project_manifest_outputs_inventory_tables(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "project_manifest"

            self.run_cli(
                MANIFEST_SCRIPT,
                ALS_PATH,
                "--output-dir",
                output_dir,
            )

            expected_files = (
                "project_inventory.md",
                "project_manifest.json",
                "tracks.tsv",
                "clips.tsv",
                "samples.tsv",
                "devices.tsv",
                "plugins_by_author.tsv",
                "plugins_by_name.tsv",
            )

            for filename in expected_files:
                self.assertTrue((output_dir / filename).exists(), filename)

            manifest = json.loads(
                (output_dir / "project_manifest.json").read_text(encoding="utf-8")
            )
            summary = manifest["summary"]

            self.assertEqual(summary["track_count"], 160)
            self.assertEqual(summary["audio_track_count"], 92)
            self.assertEqual(summary["group_track_count"], 68)
            self.assertEqual(summary["clip_count"], 742)
            self.assertEqual(summary["audio_clip_count"], 742)
            self.assertEqual(summary["unique_sample_count"], 162)
            self.assertEqual(summary["device_count"], 161)
            self.assertEqual(summary["third_party_plugin_count"], 55)
            self.assertEqual(summary["ableton_native_device_count"], 106)
            self.assertEqual(summary["locator_count"], 66)
            self.assertEqual(summary["tempo_event_count"], 23)
            self.assertEqual(summary["time_signature_event_count"], 1)

            device_names = {device["name"] for device in manifest["devices"]}
            manufacturers = {device["manufacturer"] for device in manifest["devices"]}

            self.assertIn("Ozone 11 Master Rebalance", device_names)
            self.assertIn("Filter EQ3", device_names)
            self.assertIn("iZotope", manufacturers)
            self.assertIn("Ableton", manufacturers)

            markdown = (output_dir / "project_inventory.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("| Midi Track Count | 0 |", markdown)
            self.assertIn("| Existing Sample Count | 0 |", markdown)

    def test_project_health_reports_missing_samples(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            markdown_path = temp_path / "health.md"
            json_path = temp_path / "health.json"

            result = self.run_cli(
                HEALTH_SCRIPT,
                ALS_PATH,
                "--fail-on=none",
                "--markdown",
                markdown_path,
                "--json",
                json_path,
            )

            self.assertEqual(result.returncode, 0)
            self.assertTrue(markdown_path.exists())
            self.assertTrue(json_path.exists())

            health = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(health["status"], "critical")
            self.assertEqual(health["summary"]["unique_sample_count"], 162)
            self.assertEqual(health["summary"]["missing_sample_count"], 162)
            self.assertIn(
                "missing_samples",
                {finding["category"] for finding in health["findings"]},
            )

            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("# Project Health", markdown)
            self.assertIn("missing_samples", markdown)

    def test_semantic_diff_same_file_has_no_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            markdown_path = temp_path / "semantic_diff.md"
            json_path = temp_path / "semantic_diff.json"

            result = self.run_cli(
                DIFF_SCRIPT,
                ALS_PATH,
                ALS_PATH,
                "--markdown",
                markdown_path,
                "--json",
                json_path,
            )

            self.assertEqual(result.returncode, 0)
            self.assertTrue(markdown_path.exists())
            self.assertTrue(json_path.exists())

            diff = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(diff["status"], "same")
            self.assertEqual(diff["change_count"], 0)
            self.assertEqual(diff["summary_changes"], [])

            for section in diff["sections"]:
                self.assertEqual(section["added_count"], 0, section["name"])
                self.assertEqual(section["removed_count"], 0, section["name"])

    def test_missing_input_returns_error_exit_code(self):
        missing_file = REPO_ROOT / "examples" / "validation" / "missing.als"

        locator_result = self.run_cli(
            LOCATORS_SCRIPT,
            missing_file,
            "--output",
            Path(tempfile.gettempdir()) / "missing-locators.tsv",
            check=False,
        )
        timeline_result = self.run_cli(
            TIMELINE_SCRIPT,
            missing_file,
            "--output",
            Path(tempfile.gettempdir()) / "missing-timeline.tsv",
            check=False,
        )
        manifest_result = self.run_cli(
            MANIFEST_SCRIPT,
            missing_file,
            "--output-dir",
            Path(tempfile.gettempdir()) / "missing-project-manifest",
            check=False,
        )
        health_result = self.run_cli(
            HEALTH_SCRIPT,
            missing_file,
            check=False,
        )
        diff_result = self.run_cli(
            DIFF_SCRIPT,
            missing_file,
            ALS_PATH,
            check=False,
        )

        self.assertEqual(locator_result.returncode, 1)
        self.assertIn("status     error", locator_result.stderr)
        self.assertEqual(timeline_result.returncode, 1)
        self.assertIn("status     error", timeline_result.stderr)
        self.assertEqual(manifest_result.returncode, 1)
        self.assertIn("status     error", manifest_result.stderr)
        self.assertEqual(health_result.returncode, 1)
        self.assertIn("status     error", health_result.stderr)
        self.assertEqual(diff_result.returncode, 1)
        self.assertIn("status     error", diff_result.stderr)

    def test_cue_audio_without_cue_returns_argument_error(self):
        result = self.run_cli(
            LOCATORS_SCRIPT,
            ALS_PATH,
            "--cue-audio=RYM_2026-03.wav",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--cue-audio requires --cue", result.stderr)

    def test_midi_timing_map_without_midi_returns_argument_error(self):
        result = self.run_cli(
            LOCATORS_SCRIPT,
            ALS_PATH,
            "--midi-timing-map",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--midi-timing-map requires --midi", result.stderr)


if __name__ == "__main__":
    unittest.main()
