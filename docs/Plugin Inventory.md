# Plug-in Inventory

`src/extract_plugin_inventory.py` exports external plug-ins known to Ableton
Live, including their recorded versions, module paths, browser paths, categories,
and tag hierarchies. It uses Python 3.9+ and the standard library.

This is an installed-library inventory, separate from Project Manifest's list of
plug-ins used in a particular `.als` file. It includes AU, AUv3, VST (VST2), and
VST3 device identities when present in Live's databases. Native Live devices,
Max for Live devices, presets, and samples are excluded. Apple's built-in Audio
Units (manufacturer fourcc `appl`) are excluded by default; use
`--include-system-au` to include them.

## Run

Let Live finish scanning plug-ins, then quit Live so its scan cache and browser
index describe the same completed session. Run on the computer with Live installed:

```bash
python3 src/extract_plugin_inventory.py --require-browser --output plugins.json
python3 src/extract_plugin_inventory.py --require-browser --output plugins.csv
python3 src/extract_plugin_inventory.py --require-browser --output plugins.tsv
python3 src/extract_plugin_inventory.py --require-browser --output plugins.txt
```

JSON retains the report summary, source database paths, warnings, and nested
metadata. Plain text groups plug-ins by manufacturer, like All Plug-ins, then by
name. Each group retains its format/channel variants, versions, full paths, and
original Live categories and tags. CSV/TSV contain one row per device/module record. Their nested fields
use JSON cells so tag names containing separators and multi-level categories
remain unambiguous. The export format defaults to the output extension; use
`--format=json|csv|tsv|txt` to override it. `--output -` writes to standard output,
with progress and warnings on standard error.

The default output is `plugins.json` in the current directory. Existing exports
are replaced atomically. Exports inside the source databases' directories are
refused to protect Live's database files and sidecars.

## Database selection

The default database folder is:

- macOS: `~/Library/Application Support/Ableton/Live Database/`
- Windows: `%LOCALAPPDATA%\Ableton\Live Database\`

The extractor reads one `Live-plugins-*.db` scan cache and one
`Live-files-*.db` browser index. If a separate scan cache is absent, it checks
the selected browser database for the older combined `plugins` table.

If several generations exist, the most recently written database in each family
is selected, including its WAL modification time. The report warns about this
choice. Old catalogs are never merged across generations. To select an exact
catalog, or inspect a copied database directory, supply:

```bash
python3 src/extract_plugin_inventory.py \
  --database-dir "/path/to/Live Database" \
  --output plugins.json

python3 src/extract_plugin_inventory.py \
  --plugins-db "/path/to/Live-plugins-1.db" \
  --files-db "/path/to/Live-files-12300.db" \
  --require-browser --output plugins.json
```

Connections initially use SQLite `mode=ro`, `query_only`, and a read transaction,
with WAL support. Some SQLite builds cannot open a closed WAL database when its
sidecar files are absent. In that case, the extractor copies the database and
any WAL/rollback journal to a temporary directory, verifies that the sources
did not change during copying, and opens the disposable copy with `mode=rw`
and `query_only`. SQLite may create or recover sidecars only on that copy.
The source path and `read_modes` remain in the report. An unstable source is
rejected after three attempts; quitting Live first avoids this situation.

There are no SQL writes to the source databases and no plug-in binaries are
loaded or executed by the extractor. A direct read-only SQLite connection may
use or create shared-memory sidecars in a WAL database directory. A copied
database must include any existing `-wal` file;
copying only an active `.db` can omit recently committed data. The two databases
have separate read transactions, so quitting Live first gives the most useful
cross-database snapshot.

## Categories and identities

Each JSON plug-in record preserves:

- `dev_identifier`: Live's exact external device identity. Matching is by this
  identity, never by a similar plug-in name. AU/VST/VST3 variants stay separate.
- `live_category` and `category_token`: Live's broad instrument/audio-effect/
  MIDI-effect identity, with a standard English Library label when recognized.
- `live_browser_paths`: complete indexed browser hierarchies, including the
  internal `<plugins>` root and the format/vendor folders stored by Live.
- `live_tags`: assigned keyword paths, spelling, hierarchy, and `is_auto` state.
  User tags are retained. For example, `Devices → Audio Effects → EQ` and
  `My Categories → Mix | Master` remain two distinct hierarchical paths.
- `scan_subcategories`: the scanner's original subcategory string, for example
  `Fx|EQ|Filter`. These vendor values are separate from Live's assigned tags.
- `browser_entries`: original browser IDs, raw metadata values keyed by their
  four-character metadata keys, device type/architecture, flags, and collection
  color bitmasks. Custom Collection names and saved-search label definitions are
  not decoded; color assignments are preserved as recorded integers.

The export includes cached, disabled, and remembered entries. It preserves scan
states, enabled values, and scan-domain settings without interpreting undocumented
flags as proof of loadability. A path that exists does not establish that Live
can load the plug-in. Multiple classes in a shell or bundle remain individual
devices; separate architecture/module records are also retained.

The text report consolidates duplicate scan rows for the same device identity,
path, and version. It groups display names across formats under the same creator,
normalizing company suffixes such as `Inc.`/`LLC` and known Waves channel-layout
suffixes such as `(m)`, `Mono`, `Stereo`, and `5.1`. Original names, identifiers,
versions, paths, and per-format tags remain in the variant listings and raw JSON.
It does not infer Live categories from these normalized names. Manufacturer is
the primary ordering; category and tag paths are printed with each variant.

`named_plugin_groups`, `format_identities`, `module_installations`, and `records`
are deliberately separate counts. A named group is a conservative display-name
group, not a license or purchased-package count. Separate release names, such as
RX 11 and RX 12, remain separate. WaveShell products and channel variants can
make raw browser/scan counts much larger than the apparent product library.

## Paths and versions

The scan cache supplies versions and module paths, including VST custom-folder
paths. `version_source=live_scan` distinguishes Live's recorded version from a
bundle metadata fallback. Live's cached version may predate an update until it
rescans the plug-in.

AU browser entries may lack scan-cache rows. For these, the extractor reads
macOS component `Info.plist` metadata and matches the exact manufacturer,
subtype, and type four-character codes from Live's device ID. It checks the
user, system-wide, and system component folders. Additional locations or an
AUv3 application-extension bundle can be supplied:

```bash
python3 src/extract_plugin_inventory.py \
  --au-root "/path/to/other/Components" \
  --au-root "/Applications/Example.app/Contents/PlugIns/Example.appex" \
  --require-browser --output plugins.json
```

AUv3 apps are not automatically searched throughout `/Applications`; an AUv3
entry whose extension cannot be identified keeps an unknown path/version.
Only components already indexed by Live are exported, even when additional
installed bundles are found in these folders.

An unambiguous component path gets `path_source=au_component_identity`. When
Live has no version, an available `CFBundleShortVersionString` gets
`version_source=bundle_short_version`. This is a bundle version and may differ
from the vendor's displayed plug-in version. Raw AU component-version integers
and bundle-build versions are also retained in `path_candidates` when discovered.
If multiple installed bundles have the same component identity, all candidates
of the matching AU format are listed and the path remains unknown. AUv3
identities are not resolved to AUv2 bundles that share their component codes.
Nothing is chosen by name or version.

Unavailable values remain JSON `null` or blank scalar CSV/TSV cells. Summary
counts identify unknown versions, unknown paths, unmatched browser entries, and
ambiguous AU paths. A foreign Windows path inspected on macOS has
`path_exists=null`, since its existence cannot be checked on that host.

## Limits and diagnostics

The inventory covers Live's known plug-ins. It cannot enumerate plug-ins in
folders Live has never scanned, unsupported formats, or failed scans that
produced no device identity. It does not verify licenses, instantiate plug-ins,
or determine whether they will load in a set.

Live's database schemas are private and version dependent. The adapter supports
the observed `plugins`/`plugin_modules`/`plugin_domains` structure and the
`files`/`keywords`/`metadata`/`metadata_values` browser structure. The reader was
also exercised against an actual Live 12.4.6 catalog on Intel macOS 15.7.7 on
2026-10-24, including AU and VST3 entries after a fresh Live scan. VST2 and AUv3
remain covered by synthetic fixtures; Windows has not been qualified live.
The six session-file tools' `.als` compatibility tests are a separate check
from this database reader's fixtures and real-catalog qualification.

Missing optional sources generate explicit warnings and unknown fields. Use
`--require-browser` to reject a missing browser database or keyword schema.
Unknown required schema shapes fail with an error rather than producing an
apparently complete empty inventory. To obtain table/column diagnostics:

```bash
python3 src/extract_plugin_inventory.py --inspect-schema --output schema.json
```

Schema diagnostics contain table and column names, without database row contents.
Virtual search tables are listed without probing their columns, since they may
depend on Live's private `AbletonTokenizer`; inventory queries do not need them.
Exit codes are `0` for a completed export (which may contain documented unknowns),
`1` for an input/schema/output error, and `2` for command-line usage errors.

The implementation follows Ableton's documented database locations and browser
semantics, supplemented by first-hand public schema measurements. It does not
depend on or execute these third-party projects:

- [Ableton: Resetting Live's Database](https://help.ableton.com/hc/en-us/articles/360000794970-Resetting-Live-s-Database)
  documents the separate scan database introduced in Live 12.1.
- [Ableton: Working with the Browser](https://www.ableton.com/en/live-manual/12/working-with-the-browser/)
  explains category/tag groups and Live's mapping of VST3 subcategories.
- [abletoolz: measured scan schema](https://github.com/elixirbeats/abletoolz/blob/9b2361835b211c125dabffa026498d32cecd5116/abletoolz/plugin_parsers/uid_sources.py)
  records scan-module identities and domain state on Live 12.4.5b.
- [vamp: measured browser index](https://github.com/ben-juodvalkis/vamp/blob/039bf475cb2ca6f5a14271172d2a215d29f97c01/docs/plans/general-release/live-index-measurements.md)
  records plug-in/AU rows, metadata keys, and tag structure on Live 12.4.15b4.

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_plugin_inventory.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

The focused tests cover external-only selection, shell devices and architectures,
exact tag hierarchy and custom names, raw metadata and collection colors,
disabled/stale entries, AU identity matching and ambiguity, version provenance,
older combined databases, WAL visibility, rejected writes, unchanged source
database bytes, stable temporary snapshots and cleanup, private search-tokenizer
isolation, text grouping, CSV/TSV quoting, database selection, schema diagnostics, source
protection, and explicit error behavior. A real-catalog run remains necessary
to establish compatibility with a particular Live installation.
