"""Exercise inventory joins, metadata fidelity, and read-only CLI behavior."""

from contextlib import closing
import csv
import hashlib
import json
import os
from pathlib import Path
import plistlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
import extract_plugin_inventory as inventory  # noqa: E402


EQ_ID = "device:vst3:audiofx:12345678-1234-1234-1234-123456789abc"
VST_ID = "device:vst:audiofx:1234?n=Example EQ"
AU_ID = "device:au:instr:1415672692:1398361684:1635085685"


def create_scan_database(path):
    """Create the observed scan schema with shared modules and disabled sources."""
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript("""
            CREATE TABLE plugins (
                plugin_id INTEGER, module_id INTEGER, dev_identifier TEXT,
                name TEXT, vendor TEXT, version TEXT, sdk_version TEXT,
                flags INTEGER, scanstate INTEGER, subcategories TEXT, enabled INTEGER
            );
            CREATE TABLE plugin_modules (
                module_id INTEGER, path TEXT, arch INTEGER, processor INTEGER,
                scanstate INTEGER, fingerprint BLOB
            );
            CREATE TABLE plugin_domains (id TEXT, module_id INTEGER, relpath TEXT, enabled INTEGER);
            CREATE TABLE version (version INTEGER, platform INTEGER);
            INSERT INTO version VALUES (1, 2);
            INSERT INTO plugin_modules VALUES (10, '/missing/Example.vst3', 64, 2, 1, X'0102');
            INSERT INTO plugin_modules VALUES (11, 'C:\\VST\\Example.dll', 64, 1, 1, X'03');
            INSERT INTO plugin_domains VALUES ('global', 10, 'Example.vst3', 1);
            INSERT INTO plugin_domains VALUES ('custom', 11, 'Example.dll', 0);
        """)
        connection.executemany(
            "INSERT INTO plugins VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 10, EQ_ID, 'Example, "EQ"', "Example Audio", "2.1.7", "3.7", 1, 1, "Fx|EQ|Filter", 1),
                (2, 10, "device:vst3:audiofx:second-class", "Shell Second", "Example Audio", "2.1.7", "3.7", 1, 1, "Fx|Dynamics", 0),
                (3, 11, VST_ID, "Example EQ", "Example Audio", "1.8.0", "2.4", 0, 1, "", 1),
                (4, None, "device:ableton:audiofx:Eq8", "EQ Eight", "Ableton", None, None, 0, 1, None, 1),
            ],
        )


def create_browser_database(path):
    """Create plug-in, preset, native-device, tag-tree, and metadata rows."""
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript("""
            CREATE TABLE files (
                file_id INTEGER PRIMARY KEY, parent_id INTEGER, name TEXT,
                file_type INTEGER, device_id TEXT, device_type INTEGER,
                device_arch INTEGER, flags INTEGER, colors INTEGER
            );
            CREATE TABLE keywords (file_id INTEGER, keyw_id INTEGER, is_auto INTEGER);
            CREATE TABLE metadata (file_id INTEGER, key INTEGER, value_id INTEGER);
            CREATE TABLE metadata_values (id INTEGER PRIMARY KEY, value TEXT);
            CREATE TABLE version (version INTEGER, platform INTEGER);
            INSERT INTO version VALUES (12300, 2);
        """)
        nodes = [
            (1, 0, "<plugins>", "fldr", None),
            (2, 1, "VST3", "fldr", None),
            (3, 2, "Example Audio", "fldr", None),
            (4, 3, 'Example, "EQ"', "plug", EQ_ID),
            (5, 1, "AUv2", "fldr", None),
            (6, 5, "Test Audio", "fldr", None),
            (7, 6, "Test Synth", "plug", AU_ID),
            (8, 3, "Remembered FX", "plug", "device:vst3:audiofx:remembered"),
            (9, 0, "A preset.adv", "adv ", EQ_ID),
            (10, 0, "EQ Eight", "plug", "device:ableton:audiofx:Eq8"),
            (11, 0, "Max Device", "amp ", "device:amxd:audiofx:max"),
            (100, 0, "<keywords>", "fldr", None),
            (101, 100, "Devices", "keyw", None),
            (102, 101, "Audio Effects", "keyw", None),
            (103, 102, "EQ", "keyw", None),
            (104, 100, "My Categories", "keyw", None),
            (105, 104, "Mix | Master", "keyw", None),
        ]
        connection.executemany(
            "INSERT INTO files VALUES (?, ?, ?, ?, ?, 2, 16, 3, 0)",
            [(file_id, parent_id, name, int.from_bytes(kind.encode(), "big"), device_id)
             for file_id, parent_id, name, kind, device_id in nodes],
        )
        connection.execute("UPDATE files SET device_type = 1, device_arch = 4 WHERE file_id = 7")
        connection.execute("UPDATE files SET flags = 19, colors = 5 WHERE file_id = 8")
        connection.executemany("INSERT INTO keywords VALUES (?, ?, ?)", [(4, 103, 1), (4, 105, 0)])
        connection.executemany("INSERT INTO metadata_values VALUES (?, ?)", [
            (1, "AUv2::Test Audio"), (2, "Creator|Test Audio"), (3, "Devices|Audio Effects|EQ"),
        ])
        connection.executemany("INSERT INTO metadata VALUES (?, ?, ?)", [
            (7, int.from_bytes(b"DvVP", "big"), 1),
            (7, int.from_bytes(b"Keyw", "big"), 2),
            (4, int.from_bytes(b"Keyw", "big"), 3),
        ])


def create_au_bundle(root, name="Test Synth", short_version="3.4.5"):
    """Write an AU plist whose component triple matches the browser fixture."""
    bundle = root / f"{name}.component"
    (bundle / "Contents").mkdir(parents=True)
    info = {"CFBundleVersion": "234", "AudioComponents": [{
        "manufacturer": "Tast", "subtype": "SYNT", "type": "aumu",
        "name": "Test Audio: Test Synth", "version": 0x00030405,
    }]}
    if short_version:
        info["CFBundleShortVersionString"] = short_version
    with (bundle / "Contents/Info.plist").open("wb") as stream:
        plistlib.dump(info, stream)
    return bundle


class PluginInventoryTests(unittest.TestCase):
    """Protect external-device identity, categories, paths, and failure reporting."""

    def setUp(self):
        """Create isolated Live-like databases and an AU component directory."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.db_dir = self.root / "Live Database"
        self.db_dir.mkdir()
        self.plugins_db = self.db_dir / "Live-plugins-1.db"
        self.files_db = self.db_dir / "Live-files-12300.db"
        create_scan_database(self.plugins_db)
        create_browser_database(self.files_db)
        self.au_root = self.root / "Components"
        self.au_root.mkdir()

    def build(self, **overrides):
        """Build using fixture sources without consulting installed components."""
        options = dict(plugins_db=self.plugins_db, files_db=self.files_db,
                       au_roots=[self.au_root], warnings=[])
        options.update(overrides)
        return inventory.build_inventory(**options)

    def run_cli(self, *arguments):
        """Execute the standalone script using the active Python interpreter."""
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "src/extract_plugin_inventory.py"),
             "--database-dir", str(self.db_dir), *map(str, arguments)],
            text=True, capture_output=True, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_includes_browser_only_aus_and_keeps_formats_and_shell_devices(self):
        report = self.build()
        self.assertEqual(report["summary"]["records"], 5)
        by_identity = {plugin["dev_identifier"]: plugin for plugin in report["plugins"]}
        self.assertEqual(by_identity[EQ_ID]["format"], "VST3")
        self.assertEqual(by_identity[VST_ID]["format"], "VST")
        self.assertEqual(by_identity[AU_ID]["format"], "AU")
        self.assertEqual(by_identity[AU_ID]["vendor"], "Test Audio")
        self.assertEqual(sum(plugin["module_id"] == 10 for plugin in report["plugins"]), 2)
        self.assertFalse(any(plugin["vendor"] == "Ableton" for plugin in report["plugins"]))

    def test_preserves_tag_hierarchy_custom_names_and_auto_assignment_state(self):
        plugin = next(p for p in self.build()["plugins"] if p["dev_identifier"] == EQ_ID)
        self.assertEqual(plugin["live_category"], "Audio Effects")
        self.assertEqual(plugin["scan_subcategories"], "Fx|EQ|Filter")
        self.assertEqual(plugin["live_tags"], [
            {"path": ["Devices", "Audio Effects", "EQ"], "name": "EQ", "is_auto": True},
            {"path": ["My Categories", "Mix | Master"], "name": "Mix | Master", "is_auto": False},
        ])
        self.assertEqual(plugin["live_browser_paths"], [["<plugins>", "VST3", "Example Audio", 'Example, "EQ"']])
        self.assertEqual(plugin["browser_entries"][0]["metadata"]["Keyw"], ["Devices|Audio Effects|EQ"])

    def test_keeps_disabled_and_stale_rows_without_claiming_loadability(self):
        plugins = self.build()["plugins"]
        disabled = next(p for p in plugins if p["name"] == "Shell Second")
        self.assertEqual(disabled["enabled"], 0)
        vst = next(p for p in plugins if p["dev_identifier"] == VST_ID)
        self.assertEqual(vst["domains"][0]["enabled"], 0)
        stale = next(p for p in plugins if p["name"] == "Remembered FX")
        self.assertEqual(stale["browser_entries"][0]["flags"], 19)
        self.assertEqual(stale["browser_entries"][0]["colors"], 5)
        self.assertIsNone(stale["path"])

    def test_resolves_au_by_component_identity_and_labels_bundle_version(self):
        bundle = create_au_bundle(self.au_root)
        plugin = next(p for p in self.build()["plugins"] if p["dev_identifier"] == AU_ID)
        self.assertEqual(plugin["path"], str(bundle.resolve()))
        self.assertEqual(plugin["version"], "3.4.5")
        self.assertEqual(plugin["path_source"], "au_component_identity")
        self.assertEqual(plugin["version_source"], "bundle_short_version")
        self.assertEqual(plugin["path_candidates"][0]["component_version"], 0x00030405)
        self.assertTrue(plugin["path_exists"])

    def test_duplicate_au_installations_remain_ambiguous(self):
        create_au_bundle(self.au_root, "First", "1.0")
        create_au_bundle(self.au_root, "Second", "2.0")
        report = self.build()
        plugin = next(p for p in report["plugins"] if p["dev_identifier"] == AU_ID)
        self.assertIsNone(plugin["path"])
        self.assertIsNone(plugin["version"])
        self.assertEqual(len(plugin["path_candidates"]), 2)
        self.assertEqual(report["summary"]["ambiguous_au_paths"], 1)

    def test_auv3_nested_metadata_does_not_resolve_to_an_auv2_bundle(self):
        create_au_bundle(self.au_root, "Version 2", "2.0")
        extension = self.au_root / "Example.app/Contents/PlugIns/Synth.appex"
        (extension / "Contents").mkdir(parents=True)
        with (extension / "Contents/Info.plist").open("wb") as stream:
            plistlib.dump({
                "CFBundleShortVersionString": "3.0",
                "NSExtension": {"NSExtensionAttributes": {"AudioComponents": [{
                    "manufacturer": "Tast", "subtype": "SYNT", "type": "aumu",
                }]}},
            }, stream)
        identifier = AU_ID.replace("device:au:", "device:auv3:")
        with closing(sqlite3.connect(self.files_db)) as connection, connection:
            connection.execute("UPDATE files SET device_id = ? WHERE file_id = 7", (identifier,))
        plugin = next(p for p in self.build()["plugins"] if p["dev_identifier"] == identifier)
        self.assertEqual(plugin["format"], "AUv3")
        self.assertEqual(plugin["path"], str(extension.resolve()))
        self.assertEqual(plugin["version"], "3.0")
        self.assertEqual(len(plugin["path_candidates"]), 1)

    def test_scan_version_wins_over_bundle_version(self):
        bundle = create_au_bundle(self.au_root)
        with closing(sqlite3.connect(self.plugins_db)) as connection, connection:
            connection.execute("UPDATE plugin_modules SET path = ? WHERE module_id = 10", (str(bundle),))
        plugin = next(p for p in self.build()["plugins"] if p["dev_identifier"] == EQ_ID)
        self.assertEqual(plugin["version"], "2.1.7")
        self.assertEqual(plugin["version_source"], "live_scan")

    def test_missing_scanner_or_browser_produces_explicit_incomplete_reports(self):
        browser_only = self.build(plugins_db=None)
        self.assertEqual(browser_only["summary"]["records"], 3)
        self.assertIsNone(browser_only["sources"]["plugins_db"])
        self.assertIn("Scan cache unavailable", browser_only["warnings"][0])
        scanner_only = self.build(files_db=None)
        self.assertEqual(scanner_only["summary"]["records"], 3)
        self.assertEqual(scanner_only["summary"]["without_browser_entry"], 3)
        self.assertIn("Browser database unavailable", scanner_only["warnings"][0])

    def test_old_combined_database_is_a_supported_scan_source(self):
        with closing(sqlite3.connect(self.files_db)) as connection, connection:
            connection.execute("ATTACH DATABASE ? AS scan", (str(self.plugins_db),))
            for table in ("plugins", "plugin_modules", "plugin_domains"):
                connection.execute(f"CREATE TABLE {table} AS SELECT * FROM scan.{table}")
        report = self.build(plugins_db=None)
        self.assertEqual(report["summary"]["records"], 5)
        self.assertEqual(report["sources"]["plugins_db"], str(self.files_db.resolve()))

    def test_same_identity_in_two_architectures_is_not_deduplicated(self):
        with closing(sqlite3.connect(self.plugins_db)) as connection, connection:
            connection.execute("INSERT INTO plugins SELECT 9, 11, dev_identifier, name, vendor, version, sdk_version, flags, scanstate, subcategories, enabled FROM plugins WHERE plugin_id = 1")
        matches = [p for p in self.build()["plugins"] if p["dev_identifier"] == EQ_ID]
        self.assertEqual(len(matches), 2)
        self.assertTrue(all(p["live_tags"] for p in matches))

    def test_read_only_handle_rejects_writes_and_reads_committed_wal_rows(self):
        connection = sqlite3.connect(self.plugins_db)
        self.addCleanup(connection.close)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("UPDATE plugins SET version = '9.9.9' WHERE plugin_id = 1")
        connection.commit()
        database = inventory.LiveDatabase(self.plugins_db)
        self.addCleanup(database.close)
        with self.assertRaises(sqlite3.OperationalError):
            database.connection.execute("DELETE FROM plugins")
        plugin = next(p for p in inventory.read_scan_plugins(database) if p["plugin_id"] == 1)
        self.assertEqual(plugin["version"], "9.9.9")

    def test_temporary_snapshot_fallback_preserves_wal_data_and_source_bytes(self):
        writer = sqlite3.connect(self.plugins_db)
        self.addCleanup(writer.close)
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("UPDATE plugins SET version = '8.7.6' WHERE plugin_id = 1")
        writer.commit()
        before = self.plugins_db.read_bytes()
        original_connect = sqlite3.connect

        def missing_helpers(database_uri, **options):
            """Reproduce drift's SQLite failure without changing the database."""
            if database_uri == self.plugins_db.resolve().as_uri() + "?mode=ro":
                raise sqlite3.OperationalError("unable to open database file")
            return original_connect(database_uri, **options)

        with patch.object(inventory.sqlite3, "connect", side_effect=missing_helpers):
            database = inventory.LiveDatabase(self.plugins_db)
        snapshot_path = Path(database._snapshot.name)
        try:
            self.assertEqual(database.read_mode, "temporary_snapshot")
            plugin = next(p for p in inventory.read_scan_plugins(database) if p["plugin_id"] == 1)
            self.assertEqual(plugin["version"], "8.7.6")
            with self.assertRaises(sqlite3.OperationalError):
                database.connection.execute("DELETE FROM plugins")
        finally:
            database.close()
        self.assertFalse(snapshot_path.exists())
        self.assertEqual(self.plugins_db.read_bytes(), before)

    def test_snapshot_rejects_a_source_that_keeps_changing(self):
        original_copy = inventory.shutil.copy2

        def changing_source(source, destination):
            """Change the source after each copy to simulate an active scanner."""
            result = original_copy(source, destination)
            with Path(source).open("ab") as stream:
                stream.write(b"changed")
            return result

        with patch.object(inventory.shutil, "copy2", side_effect=changing_source):
            with self.assertRaisesRegex(inventory.InventoryError, "quit Live"):
                inventory.snapshot_database(self.plugins_db)

    def test_browser_private_search_tokenizer_is_not_needed_for_inventory(self):
        with closing(sqlite3.connect(self.files_db)) as connection, connection:
            connection.execute("CREATE VIRTUAL TABLE private_search USING fts4(content, tokenize=porter)")
            connection.execute("PRAGMA writable_schema=ON")
            connection.execute("UPDATE sqlite_master SET sql=replace(sql, 'tokenize=porter', 'tokenize=AbletonTokenizer') WHERE name='private_search'")
        report = self.build()
        self.assertEqual(report["summary"]["records"], 5)
        with closing(inventory.LiveDatabase(self.files_db)) as database:
            self.assertIn("private_search", database.describe()["uninspected_tables"])

    def test_extract_does_not_modify_source_database_contents(self):
        before = {p: hashlib.sha256(p.read_bytes()).digest() for p in (self.plugins_db, self.files_db)}
        result = self.run_cli("--output", self.root / "plugins.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).digest() for p in before})

    def test_cli_json_csv_and_tsv_preserve_nested_tags_and_quoted_names(self):
        for suffix, delimiter in (("json", None), ("csv", ","), ("tsv", "\t")):
            with self.subTest(suffix=suffix):
                output = self.root / f"plugins.{suffix}"
                result = self.run_cli("--output", output, "--au-root", self.au_root)
                self.assertEqual(result.returncode, 0, result.stderr)
                with output.open(newline="", encoding="utf-8") as stream:
                    if delimiter is None:
                        plugins = json.load(stream)["plugins"]
                    else:
                        plugins = list(csv.DictReader(stream, delimiter=delimiter))
                        for plugin in plugins:
                            plugin["live_tags"] = json.loads(plugin["live_tags"])
                plugin = next(p for p in plugins if p["dev_identifier"] == EQ_ID)
                self.assertEqual(plugin["name"], 'Example, "EQ"')
                self.assertEqual(plugin["live_tags"][1]["path"], ["My Categories", "Mix | Master"])

    def test_cli_stdout_contains_only_parseable_json(self):
        result = self.run_cli("--output", "-")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["summary"]["records"], 5)
        self.assertIn("Exported 5", result.stderr)

    def test_text_report_groups_manufacturers_and_keeps_versions_paths_and_tags(self):
        bundle = create_au_bundle(self.au_root)
        output = self.root / "plugins.txt"
        result = self.run_cli("--output", output, "--au-root", self.au_root)
        self.assertEqual(result.returncode, 0, result.stderr)
        content = output.read_text(encoding="utf-8")
        self.assertIn("Named plug-in groups: 5", content)
        self.assertIn("Example Audio (3 named groups)", content)
        self.assertIn("Test Audio (1 named group)", content)
        self.assertLess(content.index("\nExample Audio ("), content.index("\nTest Audio ("))
        self.assertIn('Example, "EQ" [VST3]', content)
        self.assertIn("Version: 2.1.7", content)
        self.assertIn(str(bundle.resolve()), content)
        self.assertIn("Devices > Audio Effects > EQ (auto)", content)
        self.assertIn("My Categories > Mix | Master", content)
        self.assertIn("Recorded module path was not found", content)

    def test_product_groups_consolidate_waves_layouts_and_duplicate_scan_paths(self):
        records = []
        for identifier, name, plugin_format in (
            ("device:au:audiofx:1:2:3", "API-2500 (m)", "AU"),
            ("device:vst3:audiofx:mono", "API-2500 Mono", "VST3"),
            ("device:vst3:audiofx:stereo", "API-2500 Stereo", "VST3"),
        ):
            record = inventory.empty_plugin(identifier, name, "Waves")
            record["path"] = "/Library/Audio/Plug-Ins/" + plugin_format
            record["version"] = "17.4"
            record["live_tags"] = [{"path": ["Devices", "Dynamics"], "name": "Dynamics", "is_auto": True}]
            records.append(record)
        records.append(dict(records[1]))
        groups = inventory.group_products(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["name"], "API-2500")
        self.assertEqual(len(groups[0]["variants"]), 3)
        self.assertEqual(groups[0]["categories"], [("Devices", "Dynamics")])
        self.assertEqual(records[0]["name"], "API-2500 (m)")
        summary = inventory.inventory_summary(records)
        self.assertEqual(summary["records"], 4)
        self.assertEqual(summary["format_identities"], 3)
        self.assertEqual(summary["named_plugin_groups"], 1)

    def test_grouping_preserves_different_creators_with_the_same_product_name(self):
        records = [inventory.empty_plugin(f"device:vst3:audiofx:{index}", "Chorus", vendor)
                   for index, vendor in enumerate(("First Audio", "Second Audio", "First Audio, Inc."))]
        groups = inventory.group_products(records)
        self.assertEqual(len(groups), 2)
        first = next(group for group in groups if "First Audio" in group["creators"])
        self.assertEqual(first["creators"], ["First Audio", "First Audio, Inc."])
        self.assertEqual(len(first["variants"]), 2)

    def test_system_apple_aus_are_excluded_unless_requested(self):
        apple_id = AU_ID.replace("1415672692", str(int.from_bytes(b"appl", "big")))
        with closing(sqlite3.connect(self.files_db)) as connection, connection:
            connection.execute("UPDATE files SET device_id = ? WHERE file_id = 7", (apple_id,))
            connection.execute("UPDATE metadata_values SET value = 'AUv2::Apple' WHERE id = 1")
        report = self.build()
        self.assertEqual(report["summary"]["excluded_system_au"], 1)
        self.assertFalse(any(plugin["vendor"] == "Apple" for plugin in report["plugins"]))
        self.assertEqual(self.build(include_system_au=True)["summary"]["records"], 5)

    def test_explicit_sources_and_inspection_work_with_an_unrecognized_schema(self):
        unknown = self.db_dir / "unrecognized.db"
        with closing(sqlite3.connect(unknown)) as connection, connection:
            connection.execute("CREATE TABLE changed_schema (some_field TEXT)")
        result = self.run_cli("--plugins-db", unknown, "--output", "-")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unsupported schema", result.stderr)
        result = self.run_cli("--plugins-db", unknown, "--inspect-schema", "--output", "-")
        self.assertEqual(result.returncode, 0, result.stderr)
        schema = json.loads(result.stdout)["databases"][0]["tables"]
        self.assertEqual(schema["changed_schema"], ["some_field"])

    def test_missing_database_and_bad_cli_arguments_have_distinct_exit_codes(self):
        missing = self.run_cli("--plugins-db", self.root / "missing.db")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("Database does not exist", missing.stderr)
        invalid = self.run_cli("--format", "invalid")
        self.assertEqual(invalid.returncode, 2)
        self.plugins_db.unlink()
        self.files_db.unlink()
        absent = self.run_cli()
        self.assertEqual(absent.returncode, 1)
        self.assertIn("No Live databases found", absent.stderr)

    def test_output_cannot_replace_any_file_in_the_database_directory(self):
        original = self.plugins_db.read_bytes()
        result = self.run_cli("--output", self.plugins_db)
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside Live's database directory", result.stderr)
        self.assertEqual(self.plugins_db.read_bytes(), original)

    def test_newest_database_is_selected_without_merging_and_can_be_overridden(self):
        older = self.db_dir / "Live-plugins-0.db"
        older.write_bytes(self.plugins_db.read_bytes())
        os.utime(older, ns=(1, 1))
        result = self.run_cli("--output", "-")
        report = json.loads(result.stdout)
        self.assertEqual(report["summary"]["records"], 5)
        self.assertEqual(report["sources"]["plugins_db"], str(self.plugins_db.resolve()))
        self.assertIn("Several", result.stderr)
        result = self.run_cli("--plugins-db", older, "--output", "-")
        self.assertEqual(json.loads(result.stdout)["sources"]["plugins_db"], str(older.resolve()))

    def test_require_browser_rejects_missing_keyword_schema(self):
        with closing(sqlite3.connect(self.files_db)) as connection, connection:
            connection.execute("DROP TABLE keywords")
        result = self.run_cli("--require-browser", "--output", "-")
        self.assertEqual(result.returncode, 1)
        self.assertIn("keywords", result.stderr)
        self.assertEqual(result.stdout, "")
        report = self.build()
        self.assertTrue(any("keyword schema unavailable" in warning for warning in report["warnings"]))
        self.assertTrue(all(not p["live_tags"] for p in report["plugins"]))

    def test_cycle_in_browser_hierarchy_is_reported(self):
        with closing(sqlite3.connect(self.files_db)) as connection, connection:
            connection.execute("UPDATE files SET parent_id = 3 WHERE file_id = 2")
        result = self.run_cli("--output", "-")
        self.assertEqual(result.returncode, 1)
        self.assertIn("cyclic browser ancestry", result.stderr)

    def test_foreign_paths_remain_unknown_and_malformed_plists_are_ignored(self):
        with patch.object(inventory.sys, "platform", "darwin"):
            self.assertIsNone(inventory.local_path("C:\\VST\\Example.dll"))
            self.assertIsNone(inventory.local_path("relative/path.vst3"))
        bad = self.au_root / "Bad.component/Contents"
        bad.mkdir(parents=True)
        (bad / "Info.plist").write_text("not a plist", encoding="utf-8")
        self.assertEqual(inventory.index_au_bundles([self.au_root], []), {})
        self.assertIsNone(inventory.au_identity("device:au:instr:not-a-component"))


if __name__ == "__main__":
    unittest.main()
