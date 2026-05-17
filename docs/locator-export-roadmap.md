# Locator Export Roadmap

This checklist collects useful or novel locator-position fields we may want to
export from Ableton Live sessions over future releases.

## 2026.05.17 Work

- [x] Tempo at the locator, in BPM.
- [x] Current measure/bar/beat position.
- [x] Current time signature.
- [x] Absolute seconds from the beginning of the session.
- [x] Normalized seconds after earliest-locator normalization and before any user offset.
- [x] Absolute Ableton beat position.
- [x] Bar number.
- [x] Time signature section start.
- [x] Ableton locator ID.
- [x] Track number, with an optional offset.

## Future Candidates

- [ ] Tempo section type, such as constant tempo or linear ramp.
- [ ] Tempo ramp start BPM and end BPM.
- [ ] Offset applied in seconds.
- [ ] Normalization amount in seconds.
- [ ] Time until the next locator.
- [ ] Time since the previous locator.
- [ ] Section duration.
- [ ] Extracted musical key prefix.
- [ ] Clean label while preserving the original locator label.
- [ ] Filename-safe label slug.
- [ ] Active arrangement clips at the locator.
- [ ] Active tracks at the locator.
- [ ] Selected master automation values at the locator.
- [ ] Arrangement loop or cue context.
- [ ] Nearest clip boundary before or at the locator.
