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

**Current state (2026-10-14, evening):** **100 × 80 mm**, 4 layers, 72 parts.
Display is now a **bare 1.3" panel on a flex**: DisplayModule DM-TFT13-377
(24-pin variant, LH133T-IF05, ST7789VW) glued to the front, 0.5 mm FPC into
**J4 = XUNPU FPC-05FB-24PH20 (LCSC C2856831)**; CS tied to GND, 4-SPI, TE on
GP26, backlight from VSYS through R21 (24 Ω) and Q1 (2N7002) switched by
`LCD_BLK`. The 7-pin THT module, its 4 mounting holes and the pin-row are
gone. Layout per the ergonomic study (Claude doc "Estudio ergonómico
pikocore_gamepad"): panel at the top edge (active area y 4.6–28), D-pad
(four 6×6 tacts, SW1–SW4) and X/Y/A/B clusters centred at y 53.2, Select and
Start stacked in the centre column below the FPC connector, triggers unchanged.
Routed with freerouting 2.4.1 headless; the boost loop is hand-routed in
`manual_tracks.py`. **G-0 is red on purpose**: `LCD_FPC_PIN_ORDER` in
`params.py` (which way round the FPC contacts face) cannot be verified from
the datasheet and blocks `gen_fab.py` until measured on the physical panel
(continuity LEDA → J4 pad 1; if mirrored, J4 goes to rot 0). Every other gate
green — 201 tests, G-0 (all constants and footprints
verified), G-5/G-4/G-2, placement, ERC (0 errors), DRC (0 errors, 0 parity
mismatches) — and `gen_fab.py` produces the JLCPCB package. The 13 BOM lines
without an LCSC code are all hand-soldered THT parts (buttons, jack, LCD, module,
speaker header) plus the two 470 µF coupling caps, by design. Still open: the
enclosure, the **firmware repin** (the firmware in this repo targets the
RP2350-PiZero + GamePi13; this board needs its own board config with the pin map
in `pinmap.py` and an I2S driver for the PCM5102A), the external DFM check
(G-7) and the BOM purchase. Run `.claude/skills/pcb-verify` for the full gate
report. On this machine KiCad 9 lives in `C:\Program Files\KiCad\9.0\bin`, not
`%LOCALAPPDATA%` as the older docs assume, and it is **9.0.1**, which has three
quirks the pipeline now works around: `Footprint.Flip()` strips inner copper
layers from PTH pads (`reparar_capas_pth` in `gen_pcb.py`), `PCB_VIA.SetWidth`
without a layer argument hangs on a modal assert, and `kicad-cli` rejects user
layer names (`GND`/`PWR`) in `--layers`. The Rhino DXF template was regenerated
for 100 × 80; `pikocore_gamepad_template_MOD.dxf` (the user's last Rhino edit)
still describes the 120 mm board.

`PARTES.md` and `PENDIENTES.md` inside `pcb/` are inherited from GAMESETUP and
describe *that* project, not this one — kept for the component research they
contain (verified footprints, part-sourcing decisions), marked historical at the
top of each file.
