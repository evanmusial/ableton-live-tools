#!/usr/bin/env python3
"""Export external plug-ins from Live's scan cache and browser index.

Only AU, VST, and VST3 device identities are included. Live's private SQLite
schemas are inspected before use; no plug-in binary is loaded or executed.
See ``docs/Plugin Inventory.md`` for limitations and schema evidence.
"""

import argparse
from collections import defaultdict
from contextlib import ExitStack, closing
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import sqlite3
import sys
import tempfile


SCRIPT_VERSION = "2026.10.24"
PLUGIN_FILE_TYPE = int.from_bytes(b"plug", "big")
FORMATS = {
    "au": "AU", "auv2": "AU", "au3": "AUv3", "auv3": "AUv3",
    "vst": "VST", "vst2": "VST", "vst3": "VST3",
}
CATEGORIES = {
    "instr": "Instruments", "instrument": "Instruments",
    "audiofx": "Audio Effects", "midifx": "MIDI Effects",
}
CSV_FIELDS = (
    "name", "vendor", "format", "version", "version_source", "path",
    "path_source", "path_exists", "dev_identifier", "live_category",
    "live_tags", "live_browser_paths", "scan_subcategories", "enabled",
    "scanstate", "module_scanstate", "architecture", "processor",
    "domains", "path_candidates", "browser_entries",
)


class InventoryError(Exception):
    """Report an actionable inventory or database error."""


class LiveDatabase:
    """Hold one read-only SQLite transaction and its observed table shapes."""

    def __init__(self, path):
        """Open a WAL-aware read transaction without creating a database."""
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file():
            raise InventoryError(f"Database does not exist: {self.path}")
        self.connection = None
        self._snapshot = None
        self.read_mode = "source_read_only"
        try:
            try:
                self.connect(self.path, "ro")
            except sqlite3.OperationalError as error:
                if str(error) not in ("unable to open database file", "attempt to write a readonly database"):
                    raise
                if self.connection is not None:
                    self.connection.close()
                    self.connection = None
                self._snapshot = snapshot_database(self.path)
                self.connect(Path(self._snapshot.name) / self.path.name, "rw")
                self.read_mode = "temporary_snapshot"
            self.connection.row_factory = sqlite3.Row
            names = self.connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            self.schema = {}
            self.uninspected_tables = {}
            for name, definition in names:
                # Live's FTS tables require its private tokenizer; inventory tables do not.
                if definition and definition.lstrip().upper().startswith("CREATE VIRTUAL TABLE"):
                    self.schema[name] = set()
                    self.uninspected_tables[name] = "Virtual table; private tokenizer not loaded"
                    continue
                self.schema[name] = {
                    column[1] for column in self.connection.execute(
                        f"PRAGMA table_info({quote_identifier(name)})"
                    )
                }
        except Exception:
            self.close()
            raise

    def connect(self, path, mode):
        """Start a query-only transaction, allowing sidecars only on a copy."""
        self.connection = sqlite3.connect(
            path.as_uri() + f"?mode={mode}", uri=True, timeout=5,
        )
        self.connection.execute("PRAGMA query_only = ON")
        self.connection.execute("BEGIN")
        # Opening a connection can succeed before SQLite discovers missing WAL helpers.
        self.connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()

    def close(self):
        """Release the read transaction and database handle."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        if self._snapshot is not None:
            self._snapshot.cleanup()
            self._snapshot = None

    def supports(self, table, *columns):
        """Return whether a table has all requested columns."""
        return table in self.schema and set(columns) <= self.schema[table]

    def require(self, table, *columns):
        """Reject a schema that cannot support an identity-preserving query."""
        if not self.supports(table, *columns):
            raise InventoryError(
                f"Unsupported schema in {self.path}: need {table}"
                f"({', '.join(columns)}). Use --inspect-schema for diagnostics."
            )

    def describe(self):
        """Return source and schema details without exporting table contents."""
        return {
            "path": str(self.path),
            "read_mode": self.read_mode,
            "tables": {name: sorted(columns) for name, columns in sorted(self.schema.items())},
            "uninspected_tables": self.uninspected_tables,
        }


def database_signature(path):
    """Record database and journal identities to detect changes during copying."""
    signature = {}
    for suffix in ("", "-wal", "-journal"):
        candidate = Path(str(path) + suffix)
        try:
            stat = candidate.stat()
        except FileNotFoundError:
            signature[suffix] = None
        else:
            signature[suffix] = (stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    return signature


def snapshot_database(path):
    """Copy a stable database and any journal into disposable writable storage."""
    for _ in range(3):
        temporary = tempfile.TemporaryDirectory(prefix="live-plugin-inventory-")
        try:
            before = database_signature(path)
            for suffix, signature in before.items():
                if signature is not None:
                    destination = Path(temporary.name) / (path.name + suffix)
                    shutil.copy2(Path(str(path) + suffix), destination)
                    destination.chmod(destination.stat().st_mode | 0o200)
            if before == database_signature(path):
                return temporary
        except FileNotFoundError:
            pass
        except Exception:
            temporary.cleanup()
            raise
        temporary.cleanup()
    raise InventoryError(f"Database changed while copying {path}; quit Live and try again.")


def quote_identifier(value):
    """Quote a SQLite identifier obtained from the schema."""
    return '"' + value.replace('"', '""') + '"'


def default_database_dir():
    """Return Live's documented database directory on this operating system."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return base / "Ableton/Live Database"
    return Path.home() / "Library/Application Support/Ableton/Live Database"


def activity_time(path):
    """Include committed WAL activity when comparing database candidates."""
    return max(
        candidate.stat().st_mtime_ns
        for candidate in (path, Path(str(path) + "-wal"))
        if candidate.exists()
    )


def select_database(directory, pattern, explicit, warnings):
    """Select one database generation without merging old Live catalogs."""
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise InventoryError(f"Database does not exist: {path}")
        return path
    candidates = sorted(directory.glob(pattern), key=lambda p: (activity_time(p), p.name))
    if len(candidates) > 1:
        warnings.append(
            f"Several {pattern} files found; selected the most recently written: "
            f"{candidates[-1]}. Use --plugins-db / --files-db to select explicitly."
        )
    return candidates[-1].resolve() if candidates else None


def parse_device_identifier(identifier):
    """Read format and category tokens only from external device identities."""
    if not isinstance(identifier, str):
        return None
    parts = identifier.split(":", 3)
    if len(parts) != 4 or parts[0] != "device" or parts[1].lower() not in FORMATS:
        return None
    return FORMATS[parts[1].lower()], parts[2], parts[3]


def empty_plugin(identifier, name, vendor=None):
    """Build a record with explicit unknowns and the original Live identity."""
    plugin_format, category_token, _ = parse_device_identifier(identifier)
    return {
        "name": name, "vendor": vendor, "format": plugin_format,
        "dev_identifier": identifier, "category_token": category_token,
        "live_category": CATEGORIES.get(category_token),
        "version": None, "version_source": None, "path": None,
        "path_source": None, "path_exists": None, "path_candidates": [],
        "scan_subcategories": None, "enabled": None, "scanstate": None,
        "module_scanstate": None, "architecture": None, "processor": None,
        "plugin_id": None, "module_id": None, "domains": [],
        "live_tags": [], "live_browser_paths": [], "browser_entries": [],
    }


def read_scan_plugins(database):
    """Read each scanned device and module without dropping disabled entries."""
    database.require("plugins", "dev_identifier", "name")
    modules = {}
    if "plugin_modules" in database.schema:
        database.require("plugin_modules", "module_id", "path")
        modules = {
            row["module_id"]: dict(row)
            for row in database.connection.execute("SELECT * FROM plugin_modules")
        }
    domains = defaultdict(list)
    if "plugin_domains" in database.schema:
        database.require("plugin_domains", "module_id")
        for row in database.connection.execute("SELECT * FROM plugin_domains"):
            domains[row["module_id"]].append(dict(row))
    plugins = []
    for result in database.connection.execute("SELECT * FROM plugins"):
        row = dict(result)
        identifier = row["dev_identifier"]
        if not parse_device_identifier(identifier):
            continue
        plugin = empty_plugin(identifier, row["name"], row.get("vendor"))
        module = modules.get(row.get("module_id"), {})
        plugin.update({
            "plugin_id": row.get("plugin_id"), "module_id": row.get("module_id"),
            "version": row.get("version"),
            "version_source": "live_scan" if row.get("version") not in (None, "") else None,
            "path": module.get("path") or row.get("path"),
            "scan_subcategories": row.get("subcategories"),
            "enabled": row.get("enabled"), "scanstate": row.get("scanstate"),
            "module_scanstate": module.get("scanstate"),
            "architecture": module.get("arch"), "processor": module.get("processor"),
            "domains": domains.get(row.get("module_id"), []),
        })
        if plugin["path"]:
            plugin["path_source"] = "live_scan"
        plugins.append(plugin)
    return plugins


def chunks(values, size=400):
    """Yield bounded groups for SQLite parameter lists."""
    for start in range(0, len(values), size):
        yield values[start:start + size]


def collect_ancestors(database, nodes):
    """Fetch only ancestors of plug-ins and their assigned keyword nodes."""
    attempted = set(nodes)
    for _ in range(128):
        missing = sorted({
            row["parent_id"] for row in nodes.values()
            if row["parent_id"] not in (None, 0) and row["parent_id"] not in attempted
        })
        if not missing:
            return
        attempted.update(missing)
        for group in chunks(missing):
            placeholders = ",".join("?" for _ in group)
            for row in database.connection.execute(
                f"SELECT file_id, parent_id, name FROM files WHERE file_id IN ({placeholders})",
                group,
            ):
                nodes[row["file_id"]] = dict(row)
    raise InventoryError("Browser ancestry exceeds 128 levels; cannot preserve its hierarchy.")


def node_path(file_id, nodes):
    """Reconstruct a full indexed path, detecting missing parents and cycles."""
    names = []
    visited = set()
    while file_id not in (None, 0):
        if file_id in visited or file_id not in nodes:
            raise InventoryError(f"Incomplete or cyclic browser ancestry at file_id {file_id}.")
        visited.add(file_id)
        row = nodes[file_id]
        names.append(row["name"])
        file_id = row["parent_id"]
    return list(reversed(names))


def fourcc(value):
    """Decode an integer metadata key without changing textual keys."""
    if isinstance(value, int) and 0 <= value <= 0xFFFFFFFF:
        return value.to_bytes(4, "big").decode("ascii", errors="replace")
    return str(value)


def read_browser_plugins(database, warnings):
    """Read external plug-in rows, effective keyword assignments, and metadata."""
    database.require("files", "file_id", "parent_id", "name", "file_type", "device_id")
    rows = [dict(row) for row in database.connection.execute(
        "SELECT * FROM files WHERE file_type IN (?, ?)", (PLUGIN_FILE_TYPE, "plug"),
    ) if parse_device_identifier(row["device_id"])]
    nodes = {row["file_id"]: row for row in rows}
    assignments = defaultdict(list)
    metadata = defaultdict(lambda: defaultdict(list))
    has_keywords = database.supports("keywords", "file_id", "keyw_id", "is_auto")
    has_metadata = (
        database.supports("metadata", "file_id", "key", "value_id")
        and database.supports("metadata_values", "id", "value")
    )
    if not has_keywords:
        warnings.append("Browser keyword schema unavailable; live_tags are unknown, not inferred.")
    if not has_metadata:
        warnings.append("Browser metadata schema unavailable; raw metadata cannot be exported.")
    for group in chunks(list(nodes)):
        placeholders = ",".join("?" for _ in group)
        if has_keywords:
            for row in database.connection.execute(
                "SELECT k.file_id AS owner_id, k.is_auto, kw.file_id, kw.parent_id, kw.name "
                "FROM keywords k JOIN files kw ON kw.file_id = k.keyw_id "
                f"WHERE k.file_id IN ({placeholders})", group,
            ):
                nodes[row["file_id"]] = dict(row)
                assignments[row["owner_id"]].append((row["file_id"], row["is_auto"]))
        if has_metadata:
            for row in database.connection.execute(
                "SELECT m.file_id, m.key, mv.value FROM metadata m "
                "JOIN metadata_values mv ON mv.id = m.value_id "
                f"WHERE m.file_id IN ({placeholders})", group,
            ):
                metadata[row["file_id"]][fourcc(row["key"])].append(row["value"])
    collect_ancestors(database, nodes)
    entries = []
    for row in rows:
        tags = []
        for keyword_id, is_auto in assignments[row["file_id"]]:
            path = node_path(keyword_id, nodes)
            if path and path[0] == "<keywords>":
                path = path[1:]
            tags.append({
                "path": path, "name": nodes[keyword_id]["name"],
                "is_auto": None if is_auto is None else bool(is_auto),
            })
        entries.append({
            "file_id": row["file_id"], "name": row["name"],
            "dev_identifier": row["device_id"],
            "browser_path": node_path(row["file_id"], nodes),
            "tags": sorted(tags, key=lambda tag: (tag["path"], str(tag["is_auto"]))),
            "tags_available": has_keywords,
            "metadata": dict(metadata[row["file_id"]]),
            "device_type": row.get("device_type"), "device_arch": row.get("device_arch"),
            "flags": row.get("flags"), "colors": row.get("colors"),
        })
    return entries


def merge_browser_entries(plugins, entries):
    """Match exact Live identities while retaining shell and architecture rows."""
    by_identity = defaultdict(list)
    for plugin in plugins:
        by_identity[plugin["dev_identifier"]].append(plugin)
    for entry in entries:
        identifier = entry["dev_identifier"]
        if identifier not in by_identity:
            vendor_values = entry["metadata"].get("DvVP", [])
            vendor = vendor_values[0].split("::", 1)[-1] if vendor_values else None
            plugin = empty_plugin(identifier, entry["name"], vendor)
            plugins.append(plugin)
            by_identity[identifier].append(plugin)
        for plugin in by_identity[identifier]:
            plugin["browser_entries"].append(entry)
            if entry["browser_path"] not in plugin["live_browser_paths"]:
                plugin["live_browser_paths"].append(entry["browser_path"])
            for tag in entry["tags"]:
                if tag not in plugin["live_tags"]:
                    plugin["live_tags"].append(tag)


def au_identity(identifier):
    """Normalize Live's AU manufacturer, subtype, and type component triple."""
    parsed = parse_device_identifier(identifier)
    if not parsed or parsed[0] not in ("AU", "AUv3"):
        return None
    parts = parsed[2].split(":")
    if len(parts) != 3:
        return None
    try:
        return tuple(int(part) & 0xFFFFFFFF for part in parts)
    except ValueError:
        return None


def component_code(value):
    """Read an AudioComponents four-character code as an unsigned integer."""
    if isinstance(value, int):
        return value & 0xFFFFFFFF
    if isinstance(value, str) and len(value) == 4:
        return int.from_bytes(value.encode("mac_roman"), "big")
    raise ValueError("Invalid AudioComponents four-character code")


def load_plist(path):
    """Read bundle metadata without loading a plug-in executable."""
    try:
        with path.open("rb") as stream:
            value = plistlib.load(stream)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, plistlib.InvalidFileException):
        return {}


def default_au_roots():
    """Return macOS component folders, including system Audio Units."""
    if sys.platform != "darwin":
        return []
    return [
        Path.home() / "Library/Audio/Plug-Ins/Components",
        Path("/Library/Audio/Plug-Ins/Components"), Path("/System/Library/Components"),
    ]


def iter_au_bundles(root):
    """Find AU bundles without walking through their executable resources."""
    if root.suffix in (".component", ".appex"):
        yield root
        return
    for directory, names, _ in os.walk(root):
        for name in sorted(names):
            if Path(name).suffix in (".component", ".appex"):
                yield Path(directory) / name
                names.remove(name)


def index_au_bundles(roots, warnings):
    """Index exact component identities and versions from supplied AU folders."""
    candidates = defaultdict(list)
    seen = set()
    for root in roots:
        root = Path(root).expanduser()
        if not root.exists():
            continue
        for bundle in iter_au_bundles(root):
            path = str(bundle.resolve())
            if path in seen:
                continue
            seen.add(path)
            info = load_plist(bundle / "Contents/Info.plist")
            extension = info.get("NSExtension", {})
            attributes = extension.get("NSExtensionAttributes", {}) if isinstance(extension, dict) else {}
            components = info.get("AudioComponents", attributes.get("AudioComponents", [])
                                  if isinstance(attributes, dict) else [])
            if not isinstance(components, list):
                warnings.append(f"Invalid AudioComponents metadata in {bundle}")
                continue
            for component in components:
                if not isinstance(component, dict):
                    continue
                try:
                    identity = tuple(component_code(component[key]) for key in ("manufacturer", "subtype", "type"))
                except (KeyError, ValueError, UnicodeEncodeError):
                    continue
                candidate = {
                    "path": path, "format": "AUv3" if bundle.suffix == ".appex" else "AU",
                    "bundle_version": info.get("CFBundleShortVersionString"),
                    "bundle_build": info.get("CFBundleVersion"),
                    "component_version": component.get("version"),
                    "component_name": component.get("name"),
                }
                if candidate not in candidates[identity]:
                    candidates[identity].append(candidate)
    return candidates


def local_path(path):
    """Avoid interpreting foreign Windows paths as missing files on macOS."""
    if not isinstance(path, str) or not path:
        return None
    windows_path = bool(re.match(r"^[A-Za-z]:[\\/]", path) or path.startswith("\\\\"))
    if windows_path != (sys.platform == "win32"):
        return None
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else None


def enrich_paths_and_versions(plugins, au_bundles):
    """Fill missing bundle facts only when the AU path is unambiguous."""
    for plugin in plugins:
        if plugin["format"] in ("AU", "AUv3") and not plugin["path"]:
            candidates = [
                candidate for candidate in au_bundles.get(au_identity(plugin["dev_identifier"]), [])
                if candidate["format"] == plugin["format"]
            ]
            plugin["path_candidates"] = candidates
            if len(candidates) == 1:
                plugin["path"] = candidates[0]["path"]
                plugin["path_source"] = "au_component_identity"
        path = local_path(plugin["path"])
        plugin["path_exists"] = path.exists() if path else None
        if plugin["version"] in (None, "") and path and path.is_dir():
            info = load_plist(path / "Contents/Info.plist")
            if info.get("CFBundleShortVersionString"):
                plugin["version"] = info["CFBundleShortVersionString"]
                plugin["version_source"] = "bundle_short_version"


def is_system_au(plugin):
    """Identify Apple's built-in AU manufacturer by its registered fourcc."""
    identity = au_identity(plugin["dev_identifier"])
    return identity is not None and identity[0] == int.from_bytes(b"appl", "big")


def creator_key(vendor):
    """Normalize only company suffixes when grouping displayed product names."""
    return re.sub(
        r"(?:[,\s]+(?:inc\.?|llc|ltd\.?|gmbh|corp\.?))+$", "",
        (vendor or "Unknown creator").casefold(),
    ).strip()


def product_name(plugin):
    """Remove known Waves channel-layout suffixes without changing device IDs."""
    name = plugin["name"] or "Unnamed plug-in"
    if creator_key(plugin["vendor"]) == "waves":
        name = re.sub(r"\s+\((?:m|s|m->s|\d+->\d+)\)$", "", name)
        name = re.sub(
            r"\s+(?:Mono|Stereo|Quad|\d+\.\d+(?:\.\d+)?)"
            r"(?:/(?:Mono|Stereo|Quad|\d+\.\d+(?:\.\d+)?))*$", "", name,
        )
    return name.strip()


def group_products(plugins):
    """Group creator/name presentations while keeping every format and path."""
    groups = {}
    for plugin in plugins:
        name = product_name(plugin)
        key = (creator_key(plugin["vendor"]), name.casefold())
        group = groups.setdefault(key, {
            "name": name, "creators": set(), "records": [], "categories": set(),
        })
        group["creators"].add(plugin["vendor"] or "Unknown creator")
        group["records"].append(plugin)
        for tag in plugin["live_tags"]:
            if tag["path"] and tag["path"][0] == "Devices" and len(tag["path"]) > 1:
                group["categories"].add(tuple(tag["path"]))
    for group in groups.values():
        group["creators"] = sorted(group["creators"], key=str.casefold)
        if not group["categories"]:
            group["categories"] = {
                (record["live_category"] or "Uncategorized", "No Live Devices tag")
                for record in group["records"]
            }
        group["categories"] = sorted(group["categories"])
        variants = {}
        for record in group["records"]:
            key = (record["dev_identifier"], record["path"], str(record["version"]))
            if key not in variants:
                variants[key] = dict(record)
                variants[key]["live_tags"] = list(record["live_tags"])
                variants[key]["live_browser_paths"] = list(record["live_browser_paths"])
            else:
                for field in ("live_tags", "live_browser_paths"):
                    for value in record[field]:
                        if value not in variants[key][field]:
                            variants[key][field].append(value)
        group["variants"] = sorted(variants.values(), key=lambda p: (
            p["format"], p["name"], p["path"] or "", str(p["version"]),
        ))
    return sorted(groups.values(), key=lambda group: (
        creator_key(group["creators"][0]), group["name"].casefold(),
    ))


def inventory_summary(plugins, excluded_system_au=0):
    """Distinguish named groups, device identities, and overlapping scan rows."""
    return {
        "named_plugin_groups": len(group_products(plugins)),
        "format_identities": len({p["dev_identifier"] for p in plugins}),
        "module_installations": len({(p["dev_identifier"], p["path"], str(p["version"])) for p in plugins}),
        "records": len(plugins), "excluded_system_au": excluded_system_au,
        "without_version": sum(p["version"] in (None, "") for p in plugins),
        "without_path": sum(not p["path"] for p in plugins),
        "without_browser_entry": sum(not p["browser_entries"] for p in plugins),
        "ambiguous_au_paths": sum(len(p["path_candidates"]) > 1 for p in plugins),
    }


def build_inventory(plugins_db, files_db, au_roots, warnings, include_system_au=False):
    """Assemble a provenance-bearing inventory from the selected databases."""
    with ExitStack() as stack:
        databases = {}
        for path in (plugins_db, files_db):
            if path and path not in databases:
                databases[path] = stack.enter_context(closing(LiveDatabase(path)))
        browser = databases.get(files_db)
        scanner = databases.get(plugins_db)
        if scanner is None and browser and "plugins" in browser.schema:
            scanner = browser
        plugins = read_scan_plugins(scanner) if scanner else []
        if scanner is None:
            warnings.append("Scan cache unavailable; scanner versions and module paths are unknown.")
        if browser:
            merge_browser_entries(plugins, read_browser_plugins(browser, warnings))
        else:
            warnings.append("Browser database unavailable; Live tags and browser paths are unknown.")
        sources = {"plugins_db": str(scanner.path) if scanner else None,
                   "files_db": str(browser.path) if browser else None,
                   "read_modes": {"plugins_db": scanner.read_mode if scanner else None,
                                  "files_db": browser.read_mode if browser else None}}
    excluded_system_au = 0
    if not include_system_au:
        excluded_system_au = sum(is_system_au(plugin) for plugin in plugins)
        plugins = [plugin for plugin in plugins if not is_system_au(plugin)]
    au_bundles = index_au_bundles(au_roots, warnings) if any(
        p["format"] in ("AU", "AUv3") and not p["path"] for p in plugins
    ) else {}
    enrich_paths_and_versions(plugins, au_bundles)
    for plugin in plugins:
        plugin["live_tags"].sort(key=lambda tag: (tag["path"], str(tag["is_auto"])))
        plugin["live_browser_paths"].sort()
        plugin["path_candidates"].sort(key=lambda candidate: candidate["path"])
    plugins.sort(key=lambda p: (
        (p["vendor"] or "").casefold(), (p["name"] or "").casefold(),
        p["format"], p["path"] or "", str(p["plugin_id"]),
    ))
    return {
        "tool_version": SCRIPT_VERSION,
        "computer": platform.node(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "scope": "AU/VST/VST3 devices indexed by Live; includes cached and disabled entries; "
                 + ("includes system Apple AUs" if include_system_au else "excludes system Apple AUs"),
        "summary": inventory_summary(plugins, excluded_system_au),
        "warnings": warnings, "plugins": plugins,
    }


def write_text_report(report, stream):
    """Write manufacturer sections with consolidated products and original tags."""
    title = "ABLETON LIVE - PLUG-IN INVENTORY BY MANUFACTURER"
    stream.write(title + "\n" + "=" * len(title) + "\n\n")
    stream.write(f"Computer: {report.get('computer', 'Unknown')}\n")
    if report.get("live_version"):
        stream.write(f"Live version: {report['live_version']}\n")
    if report.get("scan_completed_at"):
        stream.write(f"Live scan completed: {report['scan_completed_at']}\n")
    stream.write(f"Exported (UTC): {report['generated_at']}\n")
    summary = report["summary"]
    products = group_products(report["plugins"])
    stream.write(f"Named plug-in groups: {len(products)}\n")
    stream.write("Formats, duplicate scan paths, and Waves channel variants are grouped underneath each name.\n")
    stream.write("Groups use creator and display name; separate release names remain separate.\n")
    formats = defaultdict(set)
    for plugin in report["plugins"]:
        formats[plugin["format"]].add(plugin["dev_identifier"])
    stream.write("Format identities (including channel variants): " + ", ".join(
        f"{name}: {len(identities)}" for name, identities in sorted(formats.items())
    ) + "\n")
    stream.write(f"Underlying database records: {summary['records']} (includes overlapping scan entries)\n")
    if summary.get("excluded_system_au"):
        stream.write(f"Built-in Apple Audio Units excluded: {summary['excluded_system_au']}\n")
    stream.write(f"Unknown versions: {summary['without_version']} | Unknown paths: {summary['without_path']}\n")
    stream.write("\nOrder: manufacturer, then plug-in name, like All Plug-ins.\n")
    stream.write("Live's original categories and tag hierarchies are listed with each variant.\n")
    stream.write("Cached and disabled entries are retained; this inventory does not test loadability.\n")
    for warning in report["warnings"]:
        stream.write(f"Note: {warning}\n")
    for note in report.get("catalog_notes", []):
        stream.write(f"Note: {note}\n")
    manufacturers = defaultdict(list)
    for product in products:
        manufacturers[creator_key(product["creators"][0])].append(product)
    stream.write("\nMANUFACTURERS\n-------------\n")
    for products in manufacturers.values():
        noun = "group" if len(products) == 1 else "groups"
        stream.write(f"  {products[0]['creators'][0]}: {len(products)} named {noun}\n")
    for products in manufacturers.values():
        noun = "group" if len(products) == 1 else "groups"
        heading = f"{products[0]['creators'][0]} ({len(products)} named {noun})"
        stream.write("\n\n" + heading + "\n" + "=" * len(heading) + "\n")
        for product in products:
            stream.write(f"\n  {product['name']}\n")
            if len(product["creators"]) > 1:
                stream.write("    Creator labels: " + ", ".join(product["creators"]) + "\n")
            for plugin in product["variants"]:
                write_text_variant(plugin, stream)
    stream.write("\n")


def write_text_variant(plugin, stream):
    """Write one distinct device/path/version combination without losing tags."""
    stream.write(f"\n    {plugin['name']} [{plugin['format']}]\n")
    version = plugin["version"] if plugin["version"] not in (None, "") else "Unknown"
    if plugin["version_source"] == "bundle_short_version":
        version = f"{version} (bundle metadata)"
    stream.write(f"      Version: {version}\n")
    stream.write(f"      Path:    {plugin['path'] or 'Unknown'}\n")
    stream.write(f"      Live type: {plugin['live_category'] or 'Unknown'}\n")
    if plugin["path_exists"] is False:
        stream.write("      Status:  Recorded module path was not found on disk\n")
    if plugin["enabled"] == 0 or (plugin["domains"] and all(
        domain.get("enabled") == 0 for domain in plugin["domains"]
    )):
        stream.write("      Status:  Plug-in or scan source disabled in Live\n")
    for path in plugin["live_browser_paths"]:
        stream.write("      Browser: " + " > ".join(path) + "\n")
    if plugin["live_tags"]:
        stream.write("      Live tags:\n")
        for tag in plugin["live_tags"]:
            suffix = " (auto)" if tag["is_auto"] else ""
            stream.write("        " + " > ".join(tag["path"]) + suffix + "\n")
    else:
        known = plugin["browser_entries"] and all(
            entry["tags_available"] for entry in plugin["browser_entries"]
        )
        stream.write("      Live tags: " + ("None assigned" if known else "Unknown") + "\n")
    if plugin["scan_subcategories"]:
        stream.write(f"      Scan categories: {plugin['scan_subcategories']}\n")
    if len(plugin["path_candidates"]) > 1:
        stream.write("      Multiple installed bundles share this AU identity:\n")
        for candidate in plugin["path_candidates"]:
            stream.write(f"        {candidate['path']} (bundle version: {candidate['bundle_version'] or 'Unknown'})\n")


def write_report(report, stream, output_format):
    """Write lossless JSON or delimited rows with JSON nested-field cells."""
    if output_format == "txt":
        write_text_report(report, stream)
        return
    if output_format == "json":
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        return
    writer = csv.DictWriter(stream, CSV_FIELDS, delimiter="\t" if output_format == "tsv" else ",")
    writer.writeheader()
    for plugin in report.get("plugins", []):
        writer.writerow({
            key: json.dumps(plugin[key], ensure_ascii=False)
            if isinstance(plugin[key], (list, dict)) else plugin[key]
            for key in CSV_FIELDS
        })


def save_report(report, output, output_format, source_paths):
    """Replace an export atomically and prevent writes into Live's DB folders."""
    if output == "-":
        write_report(report, sys.stdout, output_format)
        return
    destination = Path(output).expanduser().resolve()
    if any(destination.is_relative_to(path.parent) for path in source_paths if path):
        raise InventoryError("Choose an output outside Live's database directory.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=destination.parent,
            prefix=".plugin-inventory-", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            write_report(report, stream, output_format)
        temporary.replace(destination)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main(argv=None):
    """Run the inventory CLI and return a conventional process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--database-dir", type=Path, default=default_database_dir(),
                        help="Live Database folder; defaults to this user's macOS/Windows location")
    parser.add_argument("--plugins-db", type=Path, help="Explicit scan cache (or older combined DB)")
    parser.add_argument("--files-db", type=Path, help="Explicit browser database for Live categories/tags")
    parser.add_argument("--au-root", type=Path, action="append", default=[],
                        help="Additional AU folder, .component, or .appex bundle; repeatable")
    parser.add_argument("--output", default="plugins.json", help="Export path, or - for stdout")
    parser.add_argument("--format", choices=("json", "csv", "tsv", "txt"),
                        help="Defaults to the output extension, otherwise JSON")
    parser.add_argument("--require-browser", action="store_true",
                        help="Fail if the browser database or keyword schema is unavailable")
    parser.add_argument("--include-system-au", action="store_true",
                        help="Include built-in Apple Audio Units in addition to third-party plug-ins")
    parser.add_argument("--inspect-schema", action="store_true",
                        help="Export table/column diagnostics as JSON instead of plug-ins")
    args = parser.parse_args(argv)
    warnings = []
    try:
        directory = args.database_dir.expanduser().resolve()
        plugins_db = select_database(directory, "Live-plugins-*.db", args.plugins_db, warnings)
        files_db = select_database(directory, "Live-files-*.db", args.files_db, warnings)
        if not plugins_db and not files_db:
            raise InventoryError(
                f"No Live databases found in {directory}. Run on the Live computer after a "
                "plug-in scan, or supply --database-dir / --plugins-db / --files-db."
            )
        output_format = args.format or Path(args.output).suffix.lstrip(".").lower()
        if output_format not in ("json", "csv", "tsv", "txt"):
            output_format = "json"
        if args.inspect_schema:
            report = {"databases": []}
            for path in dict.fromkeys(p for p in (plugins_db, files_db) if p):
                with closing(LiveDatabase(path)) as database:
                    report["databases"].append(database.describe())
            output_format = "json"
        else:
            if args.require_browser:
                if not files_db:
                    raise InventoryError("--require-browser needs a Live-files database.")
                with closing(LiveDatabase(files_db)) as database:
                    database.require("keywords", "file_id", "keyw_id", "is_auto")
            report = build_inventory(
                plugins_db, files_db, default_au_roots() + args.au_root, warnings,
                include_system_au=args.include_system_au,
            )
        save_report(report, args.output, output_format, (plugins_db, files_db))
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        if not args.inspect_schema:
            print(f"Exported {report['summary']['records']} plug-in records to {args.output}.", file=sys.stderr)
            print(
                f"Unknown versions: {report['summary']['without_version']}; "
                f"unknown paths: {report['summary']['without_path']}; "
                f"without browser entries: {report['summary']['without_browser_entry']}.",
                file=sys.stderr,
            )
        return 0
    except (InventoryError, OSError, sqlite3.Error, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
