"""Focused unit tests for helper branches behind the public CLI workflows."""

import argparse
import gzip
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

import audit_project  # noqa: E402
import check_project_health  # noqa: E402
import diff_als_semantic  # noqa: E402
import extract_locators  # noqa: E402
import extract_project_manifest  # noqa: E402
import extract_timeline  # noqa: E402


class TtyStream(io.StringIO):
    """String stream that behaves like an interactive terminal."""

    def isatty(self):
        """Report terminal support for color-helper tests."""
        return True


class HelperCoverageTests(unittest.TestCase):
    """Exercise small helper branches that are awkward through CLI fixtures."""

    def test_color_helpers_emit_ansi_for_tty_streams(self):
        modules = (
            audit_project,
            check_project_health,
            diff_als_semantic,
            extract_locators,
            extract_project_manifest,
            extract_timeline,
        )

        with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=False):
            os.environ.pop("NO_COLOR", None)

            for module in modules:
                stream = TtyStream()
                colored = module.colorize(
                    "done",
                    module.FG_GREEN,
                    stream=stream,
                    bold=True,
                )
                self.assertIn(module.ANSI_BOLD, colored)
                self.assertIn(module.FG_GREEN, colored)
                self.assertIn(module.ANSI_RESET, colored)

                module.print_report(
                    "complete",
                    [("count", 1)],
                    stream=stream,
                    status_color=module.FG_GREEN,
                )
                self.assertIn("complete", stream.getvalue())

    def test_argument_parser_error_paths(self):
        parser_cases = (
            (
                extract_locators,
                ["extract_locators.py", "song.als", "--precision=-1"],
                "--precision must be 0 or greater",
            ),
            (
                extract_locators,
                ["extract_locators.py", "song.als", "--track-number-offset=-2"],
                "--track-number-offset only accepts -1 or greater",
            ),
            (
                extract_locators,
                [
                    "extract_locators.py",
                    "song.als",
                    "--no-heading-row",
                    "--time-header=Time",
                ],
                "--no-heading-row cannot be combined",
            ),
            (
                extract_timeline,
                ["extract_timeline.py", "song.als", "--precision=-1"],
                "--precision must be 0 or greater",
            ),
            (
                extract_timeline,
                ["extract_timeline.py", "song.als", "--sample-rate=0"],
                "--sample-rate must be greater than 0",
            ),
            (
                extract_timeline,
                ["extract_timeline.py", "song.als", "--end-beat=-1"],
                "--end-beat must be 0 or greater",
            ),
            (
                extract_project_manifest,
                ["extract_project_manifest.py", "song.als", "--json-format=wide"],
                "invalid choice",
            ),
            (
                check_project_health,
                ["check_project_health.py", "song.als", "--fail-on=bad"],
                "invalid choice",
            ),
            (
                diff_als_semantic,
                ["diff_als_semantic.py", "a.als", "b.als", "--json-format=bad"],
                "invalid choice",
            ),
            (
                audit_project,
                ["audit_project.py", "song.als", "--fail-on=bad"],
                "invalid choice",
            ),
        )

        for module, argv, message in parser_cases:
            with self.subTest(module=module.SCRIPT_NAME, argv=argv):
                with patch.object(sys, "argv", argv), patch(
                    "sys.stderr",
                    new_callable=io.StringIO,
                ) as stderr:
                    with self.assertRaises(SystemExit) as caught:
                        module.parse_args()

                self.assertEqual(caught.exception.code, 2)
                self.assertIn(message, stderr.getvalue())

    def test_shared_path_and_value_helpers(self):
        absolute_path = Path(tempfile.gettempdir()) / "song.als"

        self.assertEqual(extract_locators.user_path(absolute_path), absolute_path)
        self.assertEqual(
            extract_locators.user_path("relative.als"),
            Path.cwd() / "relative.als",
        )
        self.assertTrue(
            str(extract_locators.default_output_path(Path("song.als"))).endswith(
                "song.als.txt"
            )
        )
        self.assertEqual(extract_timeline.user_path(absolute_path), absolute_path)
        self.assertEqual(
            extract_timeline.user_path("relative.als"),
            Path.cwd() / "relative.als",
        )
        self.assertTrue(
            str(extract_timeline.default_output_path(Path("song.als"))).endswith(
                "song.als.timeline.tsv"
            )
        )
        self.assertTrue(
            str(extract_project_manifest.default_output_dir(Path("song.als"))).endswith(
                "song.als.project-manifest"
            )
        )
        self.assertTrue(
            str(audit_project.default_output_dir(Path("song.als"))).endswith(
                "song.als.project-audit"
            )
        )

        self.assertEqual(extract_locators.strip_key_prefix("(D#) Artist"), "Artist")
        self.assertEqual(extract_project_manifest.bool_text(None), "")
        self.assertEqual(extract_project_manifest.safe_text(None), "")
        self.assertEqual(extract_project_manifest.safe_text("a\nb"), "a b")
        self.assertEqual(extract_project_manifest.display_device_type(""), "")
        self.assertEqual(
            extract_project_manifest.display_device_type("AutoFilterEQ"),
            "Auto Filter EQ",
        )

        element = ET.fromstring("<Root><Child Value='yes' /></Root>")
        self.assertEqual(
            extract_project_manifest.direct_child_value(element, "Missing", "fallback"),
            "fallback",
        )

    def test_numeric_and_time_helpers_cover_error_branches(self):
        with self.assertRaises(extract_locators.LocatorToolError):
            extract_locators.require_positive_bpm(0, "tempo")
        self.assertEqual(extract_locators.float_value(None, 1.5, "value"), 1.5)
        with self.assertRaises(extract_locators.LocatorToolError):
            extract_locators.float_value("bad", 1.5, "value")
        self.assertEqual(extract_locators.int_value(None, 7, "value"), 7)
        with self.assertRaises(extract_locators.LocatorToolError):
            extract_locators.int_value("bad", 7, "value")
        with self.assertRaises(extract_locators.LocatorToolError):
            extract_locators.decode_time_signature_value(999)
        self.assertEqual(extract_locators.seconds_for_segment(2, 120, 1, 130), 0.0)

        with self.assertRaises(extract_timeline.TimelineToolError):
            extract_timeline.require_positive_bpm(0, "tempo")
        self.assertEqual(extract_timeline.float_value(None, 1.5, "value"), 1.5)
        with self.assertRaises(extract_timeline.TimelineToolError):
            extract_timeline.float_value("bad", 1.5, "value")
        self.assertEqual(extract_timeline.int_value(None, 7, "value"), 7)
        with self.assertRaises(extract_timeline.TimelineToolError):
            extract_timeline.int_value("bad", 7, "value")
        self.assertTrue(extract_timeline.bool_value(None, True))
        with self.assertRaises(extract_timeline.TimelineToolError):
            extract_timeline.decode_time_signature_value(999)
        self.assertEqual(extract_timeline.seconds_for_segment(2, 120, 1, 130), 0.0)
        self.assertEqual(extract_timeline.format_wall_time(9.6, 0), "00:00:10")
        self.assertEqual(extract_timeline.format_wall_time(3599.9999, 3), "01:00:00.000")
        self.assertEqual(
            extract_timeline.scale_label(extract_timeline.ScaleInfo(None, None, None)),
            "",
        )
        self.assertEqual(
            extract_timeline.scale_label(extract_timeline.ScaleInfo(None, 99, False)),
            "unknown root scale_id=99 (scale mode off)",
        )
        self.assertEqual(
            extract_timeline.scale_label(extract_timeline.ScaleInfo(3, None, None)),
            "D# unknown scale",
        )
        self.assertEqual(extract_timeline.sample_index_at_seconds(-1, None), None)
        self.assertEqual(extract_timeline.sample_index_at_seconds(-1, 48_000), 0)
        self.assertEqual(extract_timeline.bit_depth_source(()), "not_detected")
        self.assertEqual(extract_timeline.bit_depth_source((24,)), "audio_file")
        self.assertEqual(
            extract_timeline.bit_depth_source((16, 24)),
            "mixed_audio_files",
        )


class TimelineCoverageTests(unittest.TestCase):
    """Cover timeline branches that do not need a large ALS fixture."""

    def timeline_raw_data(self):
        """Return synthetic raw timeline data with every event family represented."""
        return extract_timeline.TimelineRawData(
            tempo_events=(
                extract_timeline.TempoEvent(0.0, 100.0),
                extract_timeline.TempoEvent(4.0, 140.0),
                extract_timeline.TempoEvent(8.0, 140.0),
            ),
            time_signature_events=(
                extract_timeline.TimeSignatureEvent(0.0, 3, 4),
                extract_timeline.TimeSignatureEvent(6.0, 4, 4),
            ),
            manual_time_signature_value=None,
            locators=(extract_timeline.LocatorSource("12", 2.0, "Marker"),),
            clips=(
                extract_timeline.ClipSource(
                    clip_id="101",
                    clip_type="audio",
                    name="Clip One",
                    start_beat=1.0,
                    end_beat=5.0,
                    scale=extract_timeline.ScaleInfo(1, 99, False),
                    sample_rate=44_100,
                    bit_depth=24,
                    default_duration_samples=176_400,
                    path="/outside/sample.wav",
                ),
                extract_timeline.ClipSource(
                    clip_id="102",
                    clip_type="midi",
                    name="Clip Two",
                    start_beat=9.0,
                    end_beat=None,
                    scale=extract_timeline.ScaleInfo(None, None, None),
                    sample_rate=48_000,
                    bit_depth=16,
                    relative_path="Samples/two.wav",
                ),
                extract_timeline.ClipSource(
                    clip_id="103",
                    clip_type="audio",
                    name="No Start",
                    start_beat=None,
                    end_beat=None,
                    scale=extract_timeline.ScaleInfo(2, 0, True),
                ),
            ),
            session_scale=extract_timeline.ScaleInfo(0, 0, True),
            creator="Ableton Live Test",
            major_version="5",
            minor_version="12.4_500",
        )

    def test_extract_timeline_builds_all_event_families(self):
        raw_data = self.timeline_raw_data()

        with patch.object(extract_timeline, "parse_als_timeline_data", return_value=raw_data):
            events, metadata = extract_timeline.extract_timeline(
                Path("song.als"),
                grid="beats",
                event_types=extract_timeline.ALL_EVENT_TYPES,
                columns=extract_timeline.ALL_COLUMNS,
                end_beat_override=8.0,
                sample_rate_override=48_000,
                precision=3,
            )

        event_types = {event.event_type for event in events}

        self.assertIn("tempo_ramp", event_types)
        self.assertIn("time_signature", event_types)
        self.assertIn("key", event_types)
        self.assertIn("locator", event_types)
        self.assertIn("clip_start", event_types)
        self.assertIn("clip_end", event_types)
        self.assertIn("bar", event_types)
        self.assertIn("beat", event_types)
        self.assertIn("song_end", event_types)
        self.assertEqual(metadata.sample_rate, 48_000)
        self.assertEqual(metadata.sample_rate_source, "user")
        self.assertEqual(metadata.detected_sample_rates, (44100, 48000))
        self.assertEqual(metadata.detected_bit_depths, (16, 24))
        self.assertEqual(metadata.bit_depth_source, "mixed_audio_files")

    def test_timeline_serializers_cover_all_columns(self):
        event = extract_timeline.TimelineEvent(
            event_type="clip_end",
            beat=2.5,
            seconds=3.25,
            sample_index=156_000,
            song_position="1.3.3",
            bar_number=1,
            displayed_beat=3,
            sixteenth=3,
            tempo_bpm=128.0,
            time_signature="4/4",
            key="C Major",
            name="Clip",
            value="audio",
            event_id="42",
            source="audio_clip",
            source_path="Samples/clip.wav",
            sample_rate=48_000,
            bit_depth=24,
            duration_seconds=1.25,
            details={"clip_id": "42"},
        )
        metadata = extract_timeline.TimelineMetadata(
            sample_rate=48_000,
            sample_rate_source="user",
            detected_sample_rates=(44_100, 48_000),
            detected_bit_depths=(16, 24),
            bit_depth_source="mixed_audio_files",
            end_beat=8.0,
            end_seconds=4.0,
            grid="beats",
            event_types=("clip_end",),
            ableton_creator="Ableton Live Test",
            ableton_major_version="5",
            ableton_minor_version="12.4_500",
        )

        for column in extract_timeline.ALL_COLUMNS:
            self.assertIsNotNone(extract_timeline.tsv_value(event, column, 3))
            self.assertIsNotNone(extract_timeline.json_value(event, column, 3))

        event.duration_seconds = None
        self.assertIsNone(extract_timeline.json_value(event, "duration_seconds", 3))
        with self.assertRaises(extract_timeline.TimelineToolError):
            extract_timeline.tsv_value(event, "unknown", 3)
        with self.assertRaises(extract_timeline.TimelineToolError):
            extract_timeline.json_value(event, "unknown", 3)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tsv_path = temp_path / "timeline.tsv"
            json_path = temp_path / "timeline.json"

            extract_timeline.write_tsv(
                [event],
                tsv_path,
                ("event_type", "details"),
                3,
                include_heading_row=False,
            )
            extract_timeline.write_json_export(
                [event],
                metadata,
                json_path,
                Path("song.als"),
                extract_timeline.ALL_COLUMNS,
                3,
                json_format="compact",
            )

            self.assertIn("clip_end", tsv_path.read_text(encoding="utf-8"))
            self.assertEqual(
                json.loads(json_path.read_text(encoding="utf-8"))["events"][0][
                    "event_id"
                ],
                42,
            )

    def test_timeline_list_parsers_and_parse_options(self):
        self.assertEqual(
            extract_timeline.parse_column_list("default,time,seconds,,"),
            extract_timeline.DEFAULT_COLUMNS,
        )
        self.assertEqual(
            extract_timeline.parse_event_type_list("default,tempo-ramp,,"),
            extract_timeline.DEFAULT_EVENT_TYPES,
        )

        with self.assertRaises(extract_timeline.TimelineToolError):
            extract_timeline.parse_column_list(",,")
        with self.assertRaises(extract_timeline.TimelineToolError):
            extract_timeline.parse_column_list("bad")
        with self.assertRaises(extract_timeline.TimelineToolError):
            extract_timeline.parse_event_type_list(",,")
        with self.assertRaises(extract_timeline.TimelineToolError):
            extract_timeline.parse_event_type_list("bad")

        no_clip_options = extract_timeline.build_parse_options(
            event_types=("tempo",),
            columns=("wall_time",),
            grid="none",
            end_beat_override=4.0,
            sample_rate_override=48_000,
        )
        self.assertFalse(no_clip_options.collect_clips)

        self.assertEqual(
            extract_timeline.normalized_tempo_events(()),
            (extract_timeline.TempoEvent(0.0, extract_timeline.DEFAULT_BPM),),
        )
        self.assertEqual(
            extract_timeline.normalized_tempo_events(
                (
                    extract_timeline.TempoEvent(0.0, 120.0),
                    extract_timeline.TempoEvent(4.0, 130.0),
                    extract_timeline.TempoEvent(4.0, 140.0),
                )
            )[-1].bpm,
            140.0,
        )
        self.assertEqual(
            extract_timeline.normalized_time_signature_events(
                (
                    extract_timeline.TimeSignatureEvent(0.0, 3, 4),
                    extract_timeline.TimeSignatureEvent(4.0, 5, 4),
                    extract_timeline.TimeSignatureEvent(4.0, 7, 8),
                ),
                None,
            )[-1].numerator,
            7,
        )
        tempo_lookup = extract_timeline.build_tempo_at_beat_lookup(
            (
                extract_timeline.TempoEvent(0.0, 120.0),
                extract_timeline.TempoEvent(4.0, 130.0),
                extract_timeline.TempoEvent(4.0, 140.0),
            )
        )
        self.assertEqual(tempo_lookup(4.0), 140.0)
        self.assertEqual(
            extract_timeline.choose_sample_rate(self.timeline_raw_data())[1],
            "mixed",
        )
        self.assertEqual(
            extract_timeline.detected_end_beat(
                self.timeline_raw_data(),
                (extract_timeline.TempoEvent(0.0, 120.0),),
                (extract_timeline.TimeSignatureEvent(0.0, 4, 4),),
            ),
            9.0,
        )
        absolute_media_path = Path(tempfile.gettempdir()) / "absolute.wav"
        self.assertEqual(
            extract_timeline.candidate_audio_paths(
                extract_timeline.ClipSource(
                    clip_id="absolute",
                    clip_type="audio",
                    name="Absolute",
                    relative_path=str(absolute_media_path),
                ),
                Path("song.als"),
            ),
            [absolute_media_path],
        )
        extract_timeline.build_locator_events([], (), {"event_types": ()})
        extract_timeline.build_grid_events(
            [],
            (extract_timeline.TimeSignatureEvent(10.0, 4, 4),),
            {"grid": "bars"},
            2.0,
        )

    def test_timeline_audio_metadata_readers(self):
        wav_payload = b"".join(
            (
                b"RIFF",
                (40).to_bytes(4, "little"),
                b"WAVE",
                b"fmt ",
                (16).to_bytes(4, "little"),
                struct.pack("<HHIIHH", 1, 2, 48_000, 192_000, 4, 24),
            )
        )
        odd_prefixed_wav = b"RIFF\x00\x00\x00\x00WAVEJUNK\x01\x00\x00\x00x\x00" + wav_payload[12:]
        aiff_rate = (16398).to_bytes(2, "big") + (44_100 << 48).to_bytes(8, "big")
        aiff_payload = b"FORM\x00\x00\x00\x26AIFFCOMM\x00\x00\x00\x12" + struct.pack(
            ">hIh",
            2,
            100,
            24,
        ) + aiff_rate
        odd_prefixed_aiff = (
            b"FORM\x00\x00\x00\x31AIFFJUNK\x00\x00\x00\x01x\x00"
            + aiff_payload[12:]
        )
        packed = (48_000 << 44) | ((24 - 1) << 36)
        flac_payload = b"fLaC" + bytes([0x80]) + (18).to_bytes(3, "big")
        flac_payload += b"\x00" * 10 + packed.to_bytes(8, "big")

        self.assertEqual(
            extract_timeline.read_wav_metadata(io.BytesIO(wav_payload)),
            {"sample_rate": 48000, "bit_depth": 24},
        )
        self.assertEqual(
            extract_timeline.read_wav_metadata(io.BytesIO(odd_prefixed_wav)),
            {"sample_rate": 48000, "bit_depth": 24},
        )
        self.assertEqual(extract_timeline.read_wav_metadata(io.BytesIO(b"bad")), {})
        self.assertEqual(extract_timeline.read_wav_metadata(io.BytesIO(b"RIFF1234WAVE")), {})
        self.assertEqual(extract_timeline.extended_80_to_float(b"short"), None)
        self.assertEqual(extract_timeline.extended_80_to_float(b"\x00" * 10), 0.0)
        self.assertEqual(
            extract_timeline.read_aiff_metadata(io.BytesIO(aiff_payload)),
            {"sample_rate": 44100, "bit_depth": 24},
        )
        self.assertEqual(
            extract_timeline.read_aiff_metadata(io.BytesIO(odd_prefixed_aiff)),
            {"sample_rate": 44100, "bit_depth": 24},
        )
        self.assertEqual(extract_timeline.read_aiff_metadata(io.BytesIO(b"bad")), {})
        self.assertEqual(extract_timeline.read_aiff_metadata(io.BytesIO(b"FORM1234AIFF")), {})
        self.assertEqual(
            extract_timeline.read_flac_metadata(io.BytesIO(flac_payload)),
            {"sample_rate": 48000, "bit_depth": 24},
        )
        self.assertEqual(extract_timeline.read_flac_metadata(io.BytesIO(b"bad")), {})
        self.assertEqual(extract_timeline.read_flac_metadata(io.BytesIO(b"fLaC")), {})
        self.assertEqual(
            extract_timeline.read_flac_metadata(
                io.BytesIO(b"fLaC" + bytes([0x81]) + (0).to_bytes(3, "big"))
            ),
            {},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            wav_path = temp_path / "clip.wav"
            aiff_path = temp_path / "clip.aif"
            flac_path = temp_path / "clip.flac"
            unknown_path = temp_path / "clip.bin"
            wav_path.write_bytes(wav_payload)
            aiff_path.write_bytes(aiff_payload)
            flac_path.write_bytes(flac_payload)
            unknown_path.write_bytes(b"????")

            self.assertEqual(
                extract_timeline.read_audio_file_metadata(wav_path)["sample_rate"],
                48000,
            )
            self.assertEqual(
                extract_timeline.read_audio_file_metadata(aiff_path)["sample_rate"],
                44100,
            )
            self.assertEqual(
                extract_timeline.read_audio_file_metadata(flac_path)["sample_rate"],
                48000,
            )
            self.assertEqual(extract_timeline.read_audio_file_metadata(unknown_path), {})

            with patch.object(Path, "open", side_effect=OSError("io")):
                self.assertEqual(extract_timeline.read_audio_file_metadata(wav_path), {})

    def test_timeline_parses_plain_xml_and_media_options(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            plain_als = temp_path / "plain.als"
            audio_path = temp_path / "clip.wav"
            audio_path.write_bytes(
                b"RIFF"
                + (36).to_bytes(4, "little")
                + b"WAVEfmt "
                + (16).to_bytes(4, "little")
                + struct.pack("<HHIIHH", 1, 1, 44100, 88200, 2, 16)
            )
            plain_als.write_text(
                """
                <Ableton Creator="Ableton Live Test" MajorVersion="5" MinorVersion="12">
                  <LiveSet>
                    <ScaleInformation>
                      <Root Value="0" />
                      <Name Value="0" />
                      <InKey Value="true" />
                    </ScaleInformation>
                    <MainTrack><DeviceChain><Mixer><TimeSignature><Manual Value="201" /></TimeSignature></Mixer></DeviceChain></MainTrack>
                    <Tracks>
                      <AudioTrack Id="1">
                        <AudioClip Id="2" Name="Clip" Time="1">
                          <CurrentEnd Value="5" />
                          <ScaleInformation><Root Value="1" /><Name Value="1" /></ScaleInformation>
                          <SampleRef>
                            <DefaultSampleRate Value="44100" />
                            <DefaultDuration Value="176400" />
                            <FileRef>
                              <Path Value="" />
                              <RelativePath Value="clip.wav" />
                            </FileRef>
                          </SampleRef>
                        </AudioClip>
                      </AudioTrack>
                    </Tracks>
                    <Locators>
                      <Locator Id="3"><Time Value="2" /><Name Value="Marker" /></Locator>
                    </Locators>
                  </LiveSet>
                </Ableton>
                """,
                encoding="utf-8",
            )

            raw_without_media = extract_timeline.parse_als_timeline_data(
                plain_als,
                parse_options=extract_timeline.TimelineParseOptions(
                    collect_session_scale=True,
                    collect_clips=True,
                    collect_clip_media=False,
                    inspect_audio_files=False,
                ),
            )
            raw_with_media = extract_timeline.parse_als_timeline_data(
                plain_als,
                parse_options=extract_timeline.TimelineParseOptions(
                    collect_session_scale=True,
                    collect_clips=True,
                    collect_clip_media=True,
                    inspect_audio_files=True,
                ),
            )
            raw_default_options = extract_timeline.parse_als_timeline_data(plain_als)
            raw_default_stream_options = extract_timeline.parse_als_xml_stream(
                io.BytesIO(plain_als.read_bytes())
            )

            self.assertEqual(raw_without_media.clips[0].relative_path, "")
            self.assertEqual(raw_with_media.clips[0].relative_path, "clip.wav")
            self.assertEqual(raw_with_media.clips[0].bit_depth, 16)
            self.assertEqual(raw_default_options.creator, "Ableton Live Test")
            self.assertEqual(raw_default_stream_options.creator, "Ableton Live Test")

            timeline_json = temp_path / "timeline.json"
            result = extract_timeline.run(
                argparse.Namespace(
                    als_path=str(plain_als),
                    output=str(temp_path / "timeline.tsv"),
                    json=str(timeline_json),
                    columns="event_type,name",
                    event_types="locator",
                    grid="none",
                    end_beat=None,
                    sample_rate=None,
                    precision=3,
                    json_format="compact",
                    no_heading_row=False,
                )
            )
            self.assertEqual(result["status"], "complete")
            self.assertTrue(timeline_json.exists())

    def test_timeline_read_error_branches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            corrupt_gzip = temp_path / "corrupt.als"
            bad_xml = temp_path / "bad.als"
            corrupt_gzip.write_bytes(b"\x1f\x8bnot really gzip")
            bad_xml.write_text("<Ableton>", encoding="utf-8")

            for error in (PermissionError("no"), OSError("io")):
                with self.subTest(error=type(error).__name__):
                    with patch.object(Path, "open", side_effect=error):
                        with self.assertRaises(extract_timeline.TimelineToolError):
                            extract_timeline.parse_als_timeline_data(temp_path / "x.als")

            with self.assertRaises(extract_timeline.TimelineToolError):
                extract_timeline.parse_als_timeline_data(corrupt_gzip)
            with self.assertRaises(extract_timeline.TimelineToolError):
                extract_timeline.parse_als_timeline_data(bad_xml)


class LocatorCoverageTests(unittest.TestCase):
    """Cover locator helper branches outside the golden CLI fixtures."""

    def locator_row(self):
        """Return one representative locator row for serializer helper tests."""
        return extract_locators.LocatorExportRow(
            output_seconds=62.5,
            name="Artist | Track\nName",
            locator_id="abc",
            absolute_beats=16.0,
            absolute_seconds=62.5,
            normalized_seconds=0.0,
            tempo_bpm=128.1234,
            song_position="5.1.1",
            time_signature="4/4",
            bar_number=5,
            time_signature_section_start="1.1.1",
            track_number=3,
        )

    def test_locator_serializers_and_column_parsers(self):
        row = self.locator_row()

        for column in extract_locators.ALL_TSV_COLUMNS:
            self.assertIsNotNone(
                extract_locators.tsv_value(row, column, precision=3)
            )
            self.assertIsNotNone(
                extract_locators.json_value(row, column, precision=3)
            )

        with self.assertRaises(extract_locators.LocatorToolError):
            extract_locators.tsv_value(row, "unknown", precision=3)
        with self.assertRaises(extract_locators.LocatorToolError):
            extract_locators.json_value(row, "unknown", precision=3)
        with self.assertRaises(extract_locators.LocatorToolError):
            extract_locators.normalize_column_name("unknown")
        with self.assertRaises(extract_locators.LocatorToolError):
            extract_locators.parse_column_list(",,")

        self.assertEqual(
            extract_locators.parse_column_list("default,all,name,,"),
            extract_locators.ALL_TSV_COLUMNS,
        )
        args = argparse.Namespace(
            columns="time",
            all_columns=True,
            **{f"include_{column}": False for column in extract_locators.OPTIONAL_TSV_COLUMNS},
        )
        self.assertEqual(
            extract_locators.selected_columns_from_args(args),
            extract_locators.ALL_TSV_COLUMNS,
        )

    def test_locator_timing_and_midi_edge_helpers(self):
        self.assertEqual(extract_locators.format_timestamp(59.9999, 3), "01:00.000")
        self.assertEqual(extract_locators.format_reaper_time(3661.25), "1:01:01.250")
        with self.assertRaises(extract_locators.LocatorToolError):
            extract_locators.midi_time_signature_payload(
                extract_locators.TimeSignatureEvent(0, 3, 3)
            )
        self.assertEqual(extract_locators.normalized_tempo_events(()), [(0.0, 120.0)])
        self.assertEqual(
            extract_locators.normalized_tempo_events([(0, 100), (4, 120), (4, 130)])[-1],
            (4, 130),
        )
        self.assertEqual(
            extract_locators.normalized_time_signature_events(
                (
                    extract_locators.TimeSignatureEvent(-1, 3, 4),
                    extract_locators.TimeSignatureEvent(4, 5, 4),
                    extract_locators.TimeSignatureEvent(4, 7, 8),
                ),
                None,
            )[-1].numerator,
            7,
        )
        context_at_beat = extract_locators.build_time_signature_context(
            (
                extract_locators.TimeSignatureEvent(0, 3, 4),
                extract_locators.TimeSignatureEvent(8, 4, 4),
            )
        )
        self.assertEqual(context_at_beat(9).song_position, "3.2.1")
        converter = extract_locators.build_beat_to_seconds_converter(
            [(0, 120), (4, 120)]
        )
        self.assertAlmostEqual(converter(8), 4.0)
        tempo_lookup = extract_locators.build_tempo_at_beat_lookup(
            [(0, 120), (4, 140), (4, 150)]
        )
        self.assertEqual(tempo_lookup(4), 150)

    def test_locator_plain_xml_and_no_locator_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            als_path = Path(temp_dir) / "empty.als"
            als_path.write_text(
                """
                <Ableton Creator="Ableton Live Test">
                  <LiveSet>
                    <MainTrack><DeviceChain><Mixer><TimeSignature><Manual Value="201" /></TimeSignature></Mixer></DeviceChain></MainTrack>
                    <Locators>
                      <Locator Id="1"><Time Value="4" /><Name Value="(C) Marker" /></Locator>
                    </Locators>
                  </LiveSet>
                </Ableton>
                """,
                encoding="utf-8",
            )
            args = argparse.Namespace(
                als_path=str(als_path),
                output=str(Path(temp_dir) / "locators.tsv"),
                mixcloud=None,
                csv=None,
                audition=None,
                webvtt=None,
                cue=None,
                cue_audio=None,
                markdown=None,
                reaper=None,
                midi=None,
                json=None,
                columns=None,
                all_columns=False,
                add_offset=0.0,
                strip_keys=False,
                track_number_offset=0,
                precision=0,
                time_header=None,
                label_header=None,
                no_heading_row=False,
                json_format="pretty",
                midi_timing_map=False,
                **{
                    f"include_{column}": False
                    for column in extract_locators.OPTIONAL_TSV_COLUMNS
                },
                **{name: None for name, _track in extract_locators.DAW_MIDI_PRESETS},
            )

            result = extract_locators.run(args)

            self.assertEqual(result["status"], "complete")
            self.assertEqual(
                extract_locators.extract_locator_rows(als_path, strip_keys=True)[0].name,
                "Marker",
            )
            self.assertEqual(
                extract_locators.extract_locators_with_ramps(als_path)[0][1],
                "(C) Marker",
            )

            empty_als = Path(temp_dir) / "empty.als"
            empty_als.write_text(
                """
                <Ableton Creator="Ableton Live Test">
                  <LiveSet>
                    <MainTrack><DeviceChain><Mixer><TimeSignature><Manual Value="201" /></TimeSignature></Mixer></DeviceChain></MainTrack>
                  </LiveSet>
                </Ableton>
                """,
                encoding="utf-8",
            )
            args.als_path = str(empty_als)
            self.assertEqual(extract_locators.run(args)["status"], "no locators")

            compact_json = Path(temp_dir) / "locators.json"
            extract_locators.write_json_export(
                extract_locators.extract_locator_rows(als_path),
                compact_json,
                ("time", "label"),
                als_path,
                json_format="compact",
            )
            self.assertTrue(compact_json.read_text(encoding="utf-8").startswith("{"))

    def test_locator_read_error_branches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            corrupt_gzip = temp_path / "corrupt.als"
            bad_xml = temp_path / "bad.als"
            corrupt_gzip.write_bytes(b"\x1f\x8bnot really gzip")
            bad_xml.write_text("<Ableton>", encoding="utf-8")

            for error in (PermissionError("no"), OSError("io")):
                with self.subTest(error=type(error).__name__):
                    with patch.object(Path, "open", side_effect=error):
                        with self.assertRaises(extract_locators.LocatorToolError):
                            extract_locators.parse_als_locator_data(temp_path / "x.als")

            with self.assertRaises(extract_locators.LocatorToolError):
                extract_locators.parse_als_locator_data(corrupt_gzip)
            with self.assertRaises(extract_locators.LocatorToolError):
                extract_locators.parse_als_locator_data(bad_xml)


class ManifestAndHealthCoverageTests(unittest.TestCase):
    """Cover manifest and health branches using synthetic records."""

    def sample_manifest(self, temp_path):
        """Build a project manifest with every health-finding category."""
        manifest = extract_project_manifest.ProjectManifest(
            source_file=str(temp_path / "song.als"),
            ableton_creator="Ableton Live Test",
            ableton_major_version="5",
            ableton_minor_version="12.4_500",
        )
        manifest.tracks.append(
            extract_project_manifest.TrackRecord(
                track_index=1,
                track_id="",
                track_type="audio",
                name="",
            )
        )
        manifest.clips.append(
            extract_project_manifest.ClipRecord(
                clip_id="1",
                clip_type="audio",
                track_index=1,
                track_id="1",
                track_name="Audio",
                track_type="audio",
                name="Muted",
                disabled="true",
                area="freeze",
            )
        )
        manifest.samples["missing"] = extract_project_manifest.SampleRecord(
            key="missing",
            path="/outside/missing.wav",
            default_sample_rate="44100",
            usage_count=1,
            tracks={"Audio"},
            clips={"Muted"},
            exists=False,
        )
        manifest.samples["long"] = extract_project_manifest.SampleRecord(
            key="long",
            path="/outside/" + ("a" * 260) + ".wav",
            default_sample_rate="48000",
            usage_count=1,
            tracks={"Audio"},
            clips={"Muted"},
            exists=True,
        )
        manifest.assets["preset"] = extract_project_manifest.AssetRecord(
            key="preset",
            asset_type="preset",
            path="/outside/Default.aupreset",
            usage_count=1,
            reference_types={"PresetRef"},
            tracks={"Audio"},
            devices={"Plugin"},
            exists=False,
            inside_project=False,
        )
        manifest.devices.append(
            extract_project_manifest.DeviceRecord(
                track_index=1,
                track_id="1",
                track_name="Audio",
                track_type="audio",
                device_index=1,
                device_id="device",
                device_type="Vst3PluginDevice",
                name="Plugin",
                manufacturer="Unknown",
                format="VST3",
                category="third_party_plugin",
                enabled="false",
                placeholder="true",
            )
        )
        return manifest

    def test_manifest_asset_helpers_cover_classification_and_dedupe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            als_path = temp_path / "song.als"
            media_path = temp_path / "media.wav"
            media_path.write_text("media", encoding="utf-8")
            track = extract_project_manifest.TrackRecord(1, "1", "audio", "Audio")

            self.assertEqual(
                extract_project_manifest.candidate_asset_paths(
                    str(media_path),
                    str(media_path),
                    als_path,
                ),
                [media_path],
            )
            self.assertFalse(
                extract_project_manifest.path_is_inside(
                    Path("/outside/file.wav"),
                    temp_path,
                )
            )
            self.assertEqual(
                extract_project_manifest.asset_type_for("SampleRef", "", ""),
                "sample",
            )
            self.assertEqual(
                extract_project_manifest.asset_type_for("FileRef", "device.amxd", ""),
                "max_for_live_device",
            )
            self.assertEqual(
                extract_project_manifest.asset_type_for("PresetRef", "preset.adg", ""),
                "preset",
            )
            self.assertEqual(
                extract_project_manifest.asset_type_for("FileRef", "movie.mov", ""),
                "video",
            )
            self.assertEqual(
                extract_project_manifest.asset_type_for("FileRef", "song.wav", ""),
                "audio",
            )
            self.assertEqual(
                extract_project_manifest.asset_type_for("OriginalFileRef", "", ""),
                "source_reference",
            )
            self.assertEqual(
                extract_project_manifest.asset_type_for("FileRef", "unknown.dat", ""),
                "file_reference",
            )

            empty_ref = ET.fromstring("<FileRef />")
            sample_ref_parent = ET.fromstring(
                "<SampleRef><FileRef><OriginalCrc Value='123' /></FileRef></SampleRef>"
            )
            sample_ref = sample_ref_parent.find("./FileRef")
            path_ref = ET.fromstring(
                "<FileRef><RelativePath Value='media.wav' /><OriginalCrc Value='456' /></FileRef>"
            )

            self.assertIsNone(
                extract_project_manifest.asset_record_from_file_ref(
                    empty_ref,
                    track,
                    {},
                    {},
                )
            )
            self.assertIsNotNone(
                extract_project_manifest.asset_record_from_file_ref(
                    sample_ref,
                    track,
                    {sample_ref: sample_ref_parent},
                    {},
                )
            )
            sample_empty_parent = ET.fromstring("<SampleRef><FileRef /></SampleRef>")
            sample_empty_ref = sample_empty_parent.find("./FileRef")
            self.assertIsNone(
                extract_project_manifest.asset_record_from_file_ref(
                    sample_empty_ref,
                    track,
                    {sample_empty_ref: sample_empty_parent},
                    {},
                )
            )
            streamed = extract_project_manifest.streamed_asset_record(
                sample_ref,
                "SampleRef",
                "Main Track",
            )
            self.assertIsNotNone(streamed)
            self.assertIsNone(
                extract_project_manifest.streamed_asset_record(
                    empty_ref,
                    "FileRef",
                    "",
                )
            )
            self.assertIsNone(
                extract_project_manifest.streamed_asset_record(
                    empty_ref,
                    "SampleRef",
                    "",
                )
            )

            clip = extract_project_manifest.ClipRecord(
                clip_id="clip",
                clip_type="audio",
                track_index=1,
                track_id="1",
                track_name="Audio",
                track_type="audio",
                name="Clip",
                relative_path="media.wav",
            )
            samples = {}
            extract_project_manifest.update_sample_manifest(samples, clip, als_path)
            extract_project_manifest.update_sample_manifest(samples, clip, als_path)
            self.assertEqual(samples[next(iter(samples))].usage_count, 2)
            self.assertTrue(samples[next(iter(samples))].exists)

            asset = extract_project_manifest.asset_record_from_file_ref(
                path_ref,
                track,
                {},
                {},
            )
            assets = {}
            extract_project_manifest.update_asset_manifest(assets, asset, als_path)
            extract_project_manifest.update_asset_manifest(assets, asset, als_path)
            self.assertEqual(assets[asset.key].usage_count, 2)
            self.assertTrue(assets[asset.key].inside_project)

            empty_asset = extract_project_manifest.AssetRecord(
                key="empty",
                asset_type="file_reference",
            )
            extract_project_manifest.resolve_asset_record(empty_asset, als_path)
            self.assertEqual(empty_asset.resolved_path, "")

            existing_asset = extract_project_manifest.AssetRecord(
                key="shared",
                asset_type="sample",
            )
            incoming_asset = extract_project_manifest.AssetRecord(
                key="shared",
                asset_type="sample",
                usage_count=1,
                resolved_path=str(media_path),
                exists=True,
                inside_project=True,
            )
            assets = {"shared": existing_asset}
            extract_project_manifest.update_asset_manifest(
                assets,
                incoming_asset,
                als_path,
            )
            self.assertEqual(assets["shared"].resolved_path, str(media_path))

    def test_manifest_xml_helpers_cover_devices_and_clip_area(self):
        plugin_device = ET.fromstring(
            """
            <Vst3PluginDevice Id="5">
              <PluginDesc><Vst3PluginInfo><Name Value="Plugin" /></Vst3PluginInfo></PluginDesc>
              <On><Manual Value="true" /></On>
            </Vst3PluginDevice>
            """
        )
        native_device = ET.fromstring("<AutoFilter Id='6' />")
        empty_plugin = ET.fromstring("<VstPluginDevice><PluginDesc /></VstPluginDevice>")
        freeze_clip = ET.fromstring(
            "<FreezeSequencer><AudioClip Id='1' /></FreezeSequencer>"
        )
        main_clip = ET.fromstring("<MainSequencer><MidiClip Id='2' /></MainSequencer>")
        track = extract_project_manifest.TrackRecord(1, "1", "audio", "Audio")
        freeze_parent = list(freeze_clip.iter())[1]
        main_parent = list(main_clip.iter())[1]

        self.assertIsNone(extract_project_manifest.plugin_info_for_device(native_device))
        self.assertIsNone(extract_project_manifest.plugin_info_for_device(empty_plugin))
        self.assertEqual(
            extract_project_manifest.device_record_from_element(
                plugin_device,
                track,
                1,
                {},
            ).manufacturer,
            "Unknown",
        )
        self.assertEqual(
            extract_project_manifest.device_record_from_element(
                native_device,
                track,
                2,
                {},
            ).manufacturer,
            "Ableton",
        )
        self.assertEqual(
            extract_project_manifest.clip_area(
                freeze_parent,
                {freeze_parent: freeze_clip},
            ),
            "freeze",
        )
        self.assertEqual(
            extract_project_manifest.clip_area(main_parent, {main_parent: main_clip}),
            "main",
        )
        self.assertEqual(extract_project_manifest.clip_area(main_parent, {}), "")

        parsed_track = ET.fromstring(
            """
            <AudioTrack Id="1">
              <Name><UserName Value="Parsed Track" /></Name>
              <FreezeSequencer>
                <AudioClip Id="3" Name="Frozen" Time="0">
                  <CurrentEnd Value="1" />
                  <Disabled Value="true" />
                  <SampleRef><FileRef><OriginalCrc Value="abc" /></FileRef></SampleRef>
                </AudioClip>
              </FreezeSequencer>
              <MainSequencer>
                <MidiClip Id="4" Name="Midi" Time="2"><CurrentEnd Value="3" /></MidiClip>
              </MainSequencer>
            </AudioTrack>
            """
        )
        track, clips, _devices, sample_updates, _asset_updates = (
            extract_project_manifest.parse_track_element(
                parsed_track,
                1,
                Path("song.als"),
            )
        )
        self.assertEqual(track.disabled_clip_count, 1)
        self.assertEqual(track.midi_clip_count, 1)
        self.assertEqual(len(clips), 2)
        self.assertEqual(len(sample_updates), 1)

    def test_manifest_streaming_and_read_error_branches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            als_path = temp_path / "prehear.als"
            als_path.write_text(
                """
                <Ableton Creator="Ableton Live Test">
                  <LiveSet>
                    <PreHearTrack>
                      <DeviceChain>
                        <SampleRef>
                          <FileRef><RelativePath Value="prehear.wav" /></FileRef>
                        </SampleRef>
                      </DeviceChain>
                    </PreHearTrack>
                  </LiveSet>
                </Ableton>
                """,
                encoding="utf-8",
            )
            manifest = extract_project_manifest.parse_project_manifest(als_path)
            self.assertIn("PreHear Track", next(iter(manifest.assets.values())).tracks)

            corrupt_gzip = temp_path / "corrupt.als"
            bad_xml = temp_path / "bad.als"
            corrupt_gzip.write_bytes(b"\x1f\x8bnot really gzip")
            bad_xml.write_text("<Ableton>", encoding="utf-8")

            for error in (PermissionError("no"), OSError("io")):
                with self.subTest(error=type(error).__name__):
                    with patch.object(Path, "open", side_effect=error):
                        with self.assertRaises(
                            extract_project_manifest.ProjectManifestError
                        ):
                            extract_project_manifest.parse_project_manifest(
                                temp_path / "x.als"
                            )

            with self.assertRaises(extract_project_manifest.ProjectManifestError):
                extract_project_manifest.parse_project_manifest(corrupt_gzip)
            with self.assertRaises(extract_project_manifest.ProjectManifestError):
                extract_project_manifest.parse_project_manifest(bad_xml)

    def test_health_helpers_cover_every_finding_category(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manifest = self.sample_manifest(temp_path)
            findings = check_project_health.build_health_findings(
                manifest,
                temp_path / "song.als",
            )
            categories = {finding.category for finding in findings}

            self.assertIn("placeholder_plugins", categories)
            self.assertIn("outside_project_samples", categories)
            self.assertIn("long_sample_paths", categories)
            self.assertIn("mixed_sample_rates", categories)
            self.assertIn("disabled_clips", categories)
            self.assertIn("disabled_devices", categories)
            self.assertIn("unknown_plugin_authors", categories)
            self.assertIn("unnamed_tracks", categories)
            self.assertIn("frozen_clips", categories)
            self.assertEqual(check_project_health.health_status([]), "healthy")
            self.assertEqual(
                check_project_health.health_status(
                    [check_project_health.HealthFinding("warning", "warn", "warn")]
                ),
                "warning",
            )
            self.assertEqual(check_project_health.status_color("warning"), check_project_health.FG_YELLOW)
            self.assertEqual(check_project_health.status_color("healthy"), check_project_health.FG_GREEN)
            self.assertEqual(check_project_health.exit_code_for(findings, "none"), 0)
            self.assertEqual(check_project_health.exit_code_for(findings, "critical"), 1)
            self.assertEqual(check_project_health.exit_code_for(findings, "warning"), 1)
            self.assertEqual(check_project_health.exit_code_for(findings, "any"), 1)

            empty_findings = check_project_health.build_health_findings(
                extract_project_manifest.ProjectManifest(
                    str(temp_path / "empty.als"),
                    samples={
                        "label-only": extract_project_manifest.SampleRecord(
                            key="label-only",
                            original_crc="x" * (
                                check_project_health.LONG_PATH_WARNING_LENGTH + 1
                            ),
                            exists=True,
                        )
                    },
                ),
                temp_path / "empty.als",
            )
            self.assertEqual(empty_findings[0].category, "long_sample_paths")

            no_sample_findings = check_project_health.build_health_findings(
                extract_project_manifest.ProjectManifest(str(temp_path / "empty.als")),
                temp_path / "empty.als",
            )
            self.assertEqual(no_sample_findings[0].category, "no_sample_references")

            relative_sample = extract_project_manifest.SampleRecord(
                key="relative",
                relative_path="Samples/kick.wav",
            )
            self.assertEqual(
                check_project_health.sample_candidate_path(
                    relative_sample,
                    temp_path / "song.als",
                ),
                temp_path / "Samples" / "kick.wav",
            )

            with tempfile.TemporaryDirectory() as report_dir:
                report_path = Path(report_dir) / "health.md"
                check_project_health.write_markdown_report(
                    manifest,
                    [],
                    report_path,
                    temp_path / "song.als",
                    "none",
                )
                self.assertIn(
                    "No project-health findings",
                    report_path.read_text(encoding="utf-8"),
                )


class SemanticDiffAndAuditCoverageTests(unittest.TestCase):
    """Cover semantic diff and audit helper branches."""

    def test_semantic_diff_helpers_cover_summary_and_markdown_branches(self):
        before = {
            "summary": {"track_count": 1},
            "tracks": ["A"],
            "clips": [],
            "samples": [],
            "devices_and_plugins": [],
            "locators": [],
            "tempo_events": [],
            "time_signature_events": [],
        }
        after = {
            "summary": {"track_count": 2},
            "tracks": ["B"],
            "clips": [],
            "samples": [],
            "devices_and_plugins": [],
            "locators": [],
            "tempo_events": [],
            "time_signature_events": [],
        }
        summary_changes, sections = diff_als_semantic.build_semantic_diff(before, after)
        payload = diff_als_semantic.diff_payload(
            Path("before.als"),
            Path("after.als"),
            summary_changes,
            sections,
        )

        self.assertEqual(payload["status"], "different")
        self.assertEqual(diff_als_semantic.rounded("bad"), "bad")
        self.assertEqual(sections[0].added, ["B"])
        self.assertEqual(sections[0].removed, ["A"])
        self.assertIn("\\|", diff_als_semantic.markdown_table(("A|B",), [("C|D",)]))
        self.assertEqual(
            diff_als_semantic.status_color(payload["status"])
            if hasattr(diff_als_semantic, "status_color")
            else diff_als_semantic.FG_YELLOW,
            diff_als_semantic.FG_YELLOW,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            markdown_path = temp_path / "diff.md"
            json_path = temp_path / "diff.json"

            diff_als_semantic.write_markdown_report(
                Path("before.als"),
                Path("after.als"),
                summary_changes,
                sections,
                markdown_path,
            )
            diff_als_semantic.write_json_report(
                Path("before.als"),
                Path("after.als"),
                summary_changes,
                sections,
                json_path,
                "compact",
            )

            self.assertIn("Summary Changes", markdown_path.read_text(encoding="utf-8"))
            self.assertEqual(
                json.loads(json_path.read_text(encoding="utf-8"))["status"],
                "different",
            )

    def test_audit_helpers_cover_status_summary_and_markdown_branches(self):
        health_report = {
            "status": "warning",
            "finding_counts": {"critical": 0, "warning": 1, "info": 0},
            "findings": [
                {
                    "severity": "warning",
                    "category": "outside_project_samples",
                    "count": 1,
                    "message": "Outside sample",
                    "items": [],
                }
            ],
        }
        semantic_diff = {
            "status": "different",
            "change_count": 2,
            "summary_changes": [{"metric": "track_count"}],
            "sections": [{"added_count": 1, "removed_count": 0}],
        }

        self.assertEqual(audit_project.audit_status({"status": "critical"}, None), "critical")
        self.assertEqual(audit_project.audit_status({"status": "healthy"}, semantic_diff), "review")
        self.assertEqual(audit_project.audit_status(health_report, None), "warning")
        self.assertEqual(audit_project.audit_status({"status": "healthy"}, None), "healthy")
        self.assertEqual(audit_project.status_color("critical"), audit_project.FG_RED)
        self.assertEqual(audit_project.status_color("review"), audit_project.FG_YELLOW)
        self.assertEqual(audit_project.status_color("healthy"), audit_project.FG_GREEN)
        self.assertEqual(
            audit_project.diff_summary(semantic_diff),
            {
                "status": "different",
                "change_count": 2,
                "summary_change_count": 1,
                "added_count": 1,
                "removed_count": 0,
            },
        )
        self.assertIsNone(audit_project.diff_summary(None))
        self.assertEqual(
            audit_project.top_findings({"findings": []}),
            [],
        )

        manifest = extract_project_manifest.ProjectManifest("song.als")
        payload = audit_project.audit_payload(
            manifest,
            health_report,
            semantic_diff,
            {"project_audit_json": "audit.json"},
            Path("song.als"),
            Path("before.als"),
            "none",
            False,
            1,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            markdown_path = temp_path / "audit.md"
            json_path = temp_path / "audit.json"
            audit_project.write_audit_markdown(payload, markdown_path)
            audit_project.write_audit_json(payload, json_path, "compact")

            self.assertIn("Semantic Diff", markdown_path.read_text(encoding="utf-8"))
            self.assertEqual(
                json.loads(json_path.read_text(encoding="utf-8"))["status"],
                "review",
            )

    def test_audit_run_fail_on_diff_overrides_healthy_status(self):
        args = argparse.Namespace(
            als_path="after.als",
            before="before.als",
            output_dir="audit",
            json_format="pretty",
            fail_on="critical",
            fail_on_diff=True,
            no_tsv=False,
        )
        manifest = extract_project_manifest.ProjectManifest("after.als")
        before = {
            "summary": {"track_count": 1},
            "tracks": ["A"],
            "clips": [],
            "samples": [],
            "devices_and_plugins": [],
            "locators": [],
            "tempo_events": [],
            "time_signature_events": [],
        }
        after = {
            **before,
            "summary": {"track_count": 2},
            "tracks": ["B"],
        }

        with patch.object(audit_project, "parse_project_manifest", return_value=manifest), patch.object(
            audit_project,
            "build_health_findings",
            return_value=[],
        ), patch.object(
            audit_project,
            "health_payload",
            return_value={
                "status": "healthy",
                "finding_counts": {"critical": 0, "warning": 0, "info": 0},
                "findings": [],
            },
        ), patch.object(
            audit_project,
            "semantic_snapshot",
            return_value=before,
        ), patch.object(
            audit_project,
            "diff_snapshot_from_manifest",
            return_value=after,
        ), patch.object(
            audit_project,
            "write_bundle_outputs",
            return_value=({}, {"status": "review"}),
        ):
            result = audit_project.run(args)

        self.assertEqual(result["exit_code"], 1)

    def test_write_error_branches_raise_user_facing_errors(self):
        event = extract_timeline.TimelineEvent(
            event_type="tempo",
            beat=0.0,
            seconds=0.0,
            sample_index=None,
            song_position="1.1.1",
            bar_number=1,
            displayed_beat=1,
            sixteenth=1,
            tempo_bpm=120.0,
            time_signature="4/4",
            details={},
        )
        metadata = extract_timeline.TimelineMetadata(
            sample_rate=None,
            sample_rate_source="not_detected",
            detected_sample_rates=(),
            detected_bit_depths=(),
            bit_depth_source="not_detected",
            end_beat=0.0,
            end_seconds=0.0,
            grid="none",
            event_types=("tempo",),
            ableton_creator="",
            ableton_major_version="",
            ableton_minor_version="",
        )
        row = extract_locators.LocatorExportRow(
            output_seconds=0.0,
            name="Marker",
            locator_id="1",
            absolute_beats=0.0,
            absolute_seconds=0.0,
            normalized_seconds=0.0,
            tempo_bpm=120.0,
            song_position="1.1.1",
            time_signature="4/4",
            bar_number=1,
            time_signature_section_start="1.1.1",
            track_number=1,
        )
        manifest = extract_project_manifest.ProjectManifest("song.als")
        health_finding = check_project_health.HealthFinding("warning", "cat", "msg")
        diff_section = diff_als_semantic.DiffSection("tracks", ["A"], ["B"])
        audit_payload = {
            "metadata": {
                "source_file": "song.als",
                "ableton": {"creator": "", "major_version": "", "minor_version": ""},
            },
            "status": "healthy",
            "exit_code": 0,
            "summary": extract_project_manifest.summary_payload(manifest),
            "health": {"finding_counts": {}, "findings": []},
            "semantic_diff": None,
            "handoff": {
                "health_status": "healthy",
                "semantic_diff_status": "not_run",
                "has_missing_samples": False,
                "has_placeholder_plugins": False,
                "has_outside_project_samples": False,
                "has_disabled_material": False,
            },
            "outputs": {},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            open_error_cases = (
                (
                    extract_locators.write_tsv,
                    ([row], temp_path / "out.tsv"),
                    {"columns": ("time",), "precision": 0},
                    extract_locators.LocatorToolError,
                ),
                (
                    extract_locators.write_csv_export,
                    ([row], temp_path / "out.csv"),
                    {"columns": ("time",), "precision": 0},
                    extract_locators.LocatorToolError,
                ),
                (
                    extract_locators.write_mixcloud_tracklist,
                    ([row], temp_path / "mixcloud.txt"),
                    {},
                    extract_locators.LocatorToolError,
                ),
                (
                    extract_locators.write_audition_markers,
                    ([row], temp_path / "audition.csv"),
                    {},
                    extract_locators.LocatorToolError,
                ),
                (
                    extract_locators.write_reaper_markers,
                    ([row], temp_path / "reaper.csv"),
                    {},
                    extract_locators.LocatorToolError,
                ),
                (
                    extract_locators.write_webvtt_chapters,
                    ([row], temp_path / "chapters.vtt"),
                    {},
                    extract_locators.LocatorToolError,
                ),
                (
                    extract_locators.write_cue_sheet,
                    ([row], temp_path / "tracks.cue", "audio.wav"),
                    {},
                    extract_locators.LocatorToolError,
                ),
                (
                    extract_locators.write_markdown_report,
                    ([row], temp_path / "locators.md", ("time",), Path("song.als")),
                    {},
                    extract_locators.LocatorToolError,
                ),
                (
                    extract_locators.write_midi_markers,
                    ([row], temp_path / "markers.mid"),
                    {},
                    extract_locators.LocatorToolError,
                ),
                (
                    extract_locators.write_json_export,
                    ([row], temp_path / "locators.json", ("time",), Path("song.als")),
                    {},
                    extract_locators.LocatorToolError,
                ),
                (
                    extract_timeline.write_tsv,
                    ([event], temp_path / "timeline.tsv", ("event_type",), 0),
                    {},
                    extract_timeline.TimelineToolError,
                ),
                (
                    extract_timeline.write_json_export,
                    (
                        [event],
                        metadata,
                        temp_path / "timeline.json",
                        Path("song.als"),
                        ("event_type",),
                        0,
                    ),
                    {},
                    extract_timeline.TimelineToolError,
                ),
                (
                    extract_project_manifest.write_tsv,
                    (temp_path / "manifest.tsv", ("A",), [("B",)]),
                    {},
                    extract_project_manifest.ProjectManifestError,
                ),
                (
                    extract_project_manifest.write_json_report,
                    (manifest, temp_path / "manifest.json", "pretty"),
                    {},
                    extract_project_manifest.ProjectManifestError,
                ),
                (
                    check_project_health.write_json_report,
                    (
                        manifest,
                        [health_finding],
                        temp_path / "health.json",
                        Path("song.als"),
                        "none",
                        "pretty",
                    ),
                    {},
                    extract_project_manifest.ProjectManifestError,
                ),
                (
                    diff_als_semantic.write_json_report,
                    (
                        Path("before.als"),
                        Path("after.als"),
                        [],
                        [diff_section],
                        temp_path / "diff.json",
                        "pretty",
                    ),
                    {},
                    extract_project_manifest.ProjectManifestError,
                ),
                (
                    audit_project.write_audit_json,
                    (audit_payload, temp_path / "audit.json", "pretty"),
                    {},
                    extract_project_manifest.ProjectManifestError,
                ),
            )

            for func, args, kwargs, error_type in open_error_cases:
                with self.subTest(func=func.__module__ + "." + func.__name__):
                    with patch.object(Path, "open", side_effect=PermissionError("no")):
                        with self.assertRaises(error_type):
                            func(*args, **kwargs)
                    with patch.object(Path, "open", side_effect=OSError("io")):
                        with self.assertRaises(error_type):
                            func(*args, **kwargs)

            write_text_error_cases = (
                (
                    extract_project_manifest.write_markdown_report,
                    (manifest, temp_path / "manifest.md"),
                ),
                (
                    check_project_health.write_markdown_report,
                    (
                        manifest,
                        [health_finding],
                        temp_path / "health.md",
                        Path("song.als"),
                        "none",
                    ),
                ),
                (
                    diff_als_semantic.write_markdown_report,
                    (Path("before.als"), Path("after.als"), [], [diff_section], temp_path / "diff.md"),
                ),
                (
                    audit_project.write_audit_markdown,
                    (audit_payload, temp_path / "audit.md"),
                ),
            )

            for func, args in write_text_error_cases:
                with self.subTest(func=func.__module__ + "." + func.__name__):
                    with patch.object(Path, "write_text", side_effect=PermissionError("no")):
                        with self.assertRaises(extract_project_manifest.ProjectManifestError):
                            func(*args)
                    with patch.object(Path, "write_text", side_effect=OSError("io")):
                        with self.assertRaises(extract_project_manifest.ProjectManifestError):
                            func(*args)

            with patch.object(Path, "mkdir", side_effect=PermissionError("no")):
                with self.assertRaises(extract_project_manifest.ProjectManifestError):
                    extract_project_manifest.ensure_output_dir(temp_path / "manifest")
            with patch.object(Path, "mkdir", side_effect=OSError("io")):
                with self.assertRaises(extract_project_manifest.ProjectManifestError):
                    extract_project_manifest.ensure_output_dir(temp_path / "manifest")
            with self.assertRaises(extract_locators.LocatorToolError):
                extract_locators.ensure_parent_directory(temp_path / "missing" / "out.tsv")
            with self.assertRaises(extract_timeline.TimelineToolError):
                extract_timeline.ensure_parent_directory(temp_path / "missing" / "out.tsv")
            for module in (check_project_health, diff_als_semantic):
                for error in (PermissionError("no"), OSError("io")):
                    with self.subTest(module=module.SCRIPT_NAME, error=type(error).__name__):
                        with patch.object(Path, "mkdir", side_effect=error):
                            with self.assertRaises(
                                extract_project_manifest.ProjectManifestError
                            ):
                                module.ensure_parent_directory(
                                    temp_path / "missing" / "out.md"
                                )


if __name__ == "__main__":
    unittest.main()
