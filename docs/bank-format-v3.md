# Pikocore Gamepad bank format v3

Bank v3 moves LCD waveform reduction out of the RP2350 firmware and into the
web loader. The fixed 12 KiB header and 64-byte sample records are unchanged
from v2, but each sample now has a 480-byte waveform block in the payload.

## Per-sample payload

For every sample, the web loader writes:

1. 240 unsigned 8-bit minimum PCM values, one per LCD column.
2. 240 unsigned 8-bit maximum PCM values, one per LCD column.
3. The cropped unsigned 8-bit PCM frames.

The sample record's `offset` remains relative to the start of the bank payload,
but points to the first PCM frame. Its waveform therefore starts at
`offset - 480`. `frame_count` counts PCM frames only. The header's
`audio_bytes` and `capacity_bytes` accounting includes both waveform and PCM
payload bytes.

The browser divides the cropped PCM into 240 proportional buckets and scans
every frame in each bucket for its minimum and maximum. This follows the
bucketed min/max approach in `gowaveform`, with the width fixed to the GamePi13
LCD.

## Firmware behavior

When the playing sample changes, firmware copies the two 240-byte planes from
flash into the existing LCD waveform cache. It does not inspect PCM frames or
calculate peaks. Playback still begins at the record's PCM `offset`.

Firmware metadata advertises:

- `BANK_VERSION 3`
- `BANK_WAVEFORM_COLUMNS 240`

The web loader requires both values. Version 2 banks and older firmware are
intentionally incompatible because they do not contain precomputed waveform
data.
