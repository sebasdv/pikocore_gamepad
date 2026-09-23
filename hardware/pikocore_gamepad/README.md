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
(`GAMESETUP`) that targets the same RP2350-Plus module. Current state: schematic
generates cleanly, ERC passes (0 errors), the pipeline's own automated check suite
passes except for pre-existing GAMESETUP-inherited provisional part/measurement
items (gate G-0 — audio jack part, tact switch part, boost inductor value, LCD
physical measurements). PCB copper routing, the enclosure, firmware repin, and a
confirmed BOM purchase order are explicitly out of scope so far — see the plan
doc's "Out of scope" section for what's next.

`PARTES.md` and `PENDIENTES.md` inside `pcb/` are inherited from GAMESETUP and
describe *that* project, not this one — kept for the component research they
contain (verified footprints, part-sourcing decisions), marked historical at the
top of each file.
