# pikocore_gamepad

A new, independent handheld sampler/mangler — same purpose as the pikocore port in
this repo's root, but built from scratch around the **Waveshare RP2350-Plus** core
module with its own carrier PCB, not the RP2350-PiZero + GamePi13 HAT the rest of
this repo targets.

- **Hardware design & BOM:** [`docs/superpowers/specs/2026-08-11-pikocore-gamepad-hardware-design.md`](../../docs/superpowers/specs/2026-08-11-pikocore-gamepad-hardware-design.md)
- **GPIO pin map (source of truth: `pcb/pinmap.py`):** [`docs/hardware/pikocore_gamepad-pinout.md`](../../docs/hardware/pikocore_gamepad-pinout.md)
- **PCB pipeline plan & execution notes:** [`docs/superpowers/plans/2026-08-11-pikocore-gamepad-pcb-fork.md`](../../docs/superpowers/plans/2026-08-11-pikocore-gamepad-pcb-fork.md)
- **NAV5 D-pad + speaker relocation (later layout change):** [`docs/superpowers/specs/2026-08-11-pikocore-gamepad-nav5-speaker-reloc-design.md`](../../docs/superpowers/specs/2026-08-11-pikocore-gamepad-nav5-speaker-reloc-design.md) · [plan](../../docs/superpowers/plans/2026-08-11-pikocore-gamepad-nav5-speaker-reloc.md)

## `pcb/`

A scriptable KiCad generation pipeline (Python: `pinmap.py`, `netlist.py`,
`gen_sch.py`, `gen_pcb.py`, `checks/`), forked and adapted from a sibling project
(`GAMESETUP`) that targets the same RP2350-Plus module.

**Current state (2026-10-14):** 120 × 80 mm, 4 layers, 63 parts, fully routed
(0 unconnected), every gate green — 201 tests, G-0 (all constants and footprints
verified), G-5/G-4/G-2, placement, ERC (0 errors), DRC (0 errors, 0 parity
mismatches) — and `gen_fab.py` produces the JLCPCB package. The 13 BOM lines
without an LCSC code are all hand-soldered THT parts (buttons, jack, LCD, module,
speaker header) plus the two 470 µF coupling caps, by design. Still open: the
enclosure, the **firmware repin** (the firmware in this repo targets the
RP2350-PiZero + GamePi13; this board needs its own board config with the pin map
in `pinmap.py` and an I2S driver for the PCM5102A), the external DFM check
(G-7) and the BOM purchase. Run `.claude/skills/pcb-verify` for the full gate
report. On this machine KiCad 9 lives in `C:\Program Files\KiCad\9.0\bin`, not
`%LOCALAPPDATA%` as the older docs assume.

`PARTES.md` and `PENDIENTES.md` inside `pcb/` are inherited from GAMESETUP and
describe *that* project, not this one — kept for the component research they
contain (verified footprints, part-sourcing decisions), marked historical at the
top of each file.
