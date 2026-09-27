# pikocore_gamepad PCB — NAV5 D-pad + Speaker Relocation

**Date:** 2026-08-11
**Status:** Approved

## Context

`hardware/pikocore_gamepad/pcb/` (forked and adapted from GAMESETUP's KiCad
pipeline — see
[2026-08-11-pikocore-gamepad-pcb-fork.md](../plans/2026-08-11-pikocore-gamepad-pcb-fork.md))
has a working, checks-clean schematic and placement-only PCB. This spec covers two
layout changes to that existing design, worked out interactively (with visual
mockups) before writing this doc:

1. Replace the 4-switch D-pad with a single 5-way nav switch (NAV5), repositioned to
   mirror the X/Y/A/B diamond.
2. Relocate the speaker connector from the bottom edge to the area behind the
   RP2350-Plus module, freeing the board to get shorter.

Both changes are placement/component swaps within the existing forked pipeline — no
new subsystem, no new part sourcing (the NAV5's footprint/symbol already exists in
the fork's library, left over from before Task 4 removed GAMESETUP's own nav
switches).

## Change 1: D-pad → NAV5

**Component:** Reuse the WS-1004-ARL10026 5-way nav switch (LCSC `C42377836`,
footprint `gamesetup_lcsc:SW-TH_WS-1004-ARL10026`) — this footprint file
(`lib/gamesetup_lcsc.pretty/SW-TH_WS-1004-ARL10026.kicad_mod`) survived the Task 4
cleanup even though its `netlist.py` symbol/instance definitions were deleted (Task
4 removed GAMESETUP's *own* nav switches, which used this same part, for a different
reason — GAMESETUP had 2 of them for cursor navigation; pikocore_gamepad needs
exactly 1, replacing the D-pad). Pinout (already verified against the part's
datasheet in GAMESETUP's history): 6 pins — `COM`, `LEFT`, `CENTER`, `UP`, `RIGHT`,
`DOWN`. `COM` goes to GND; each direction (including `CENTER`) closes to `COM` when
pressed and needs its own GPIO with a pull-up, same mechanism as every other button
in this design.

**Wiring:** `LEFT`→`DPAD_LEFT`, `UP`→`DPAD_UP`, `RIGHT`→`DPAD_RIGHT`,
`DOWN`→`DPAD_DOWN` (same net names the 4 deleted `SW_Push` D-pad instances used —
no `pinmap.py` renaming needed for those 4). `CENTER`→ a new net, `BTN_OK`, which
needs a **new GPIO assignment** in `pinmap.py` (one of the 3 currently-reserved
`FREE` pins, GP26/27/28 — pick one, leaving 2 still reserved).

**Reference designator:** `SW13` (the ref GAMESETUP's own first nav switch used,
freed up since Task 4 — reusing it keeps the ref sequence tidy instead of jumping to
a new number).

**Position:** X=22.5mm, Y=83mm — mirrors the X/Y/A/B diamond's position (X=67.5mm,
Y=83mm) exactly across the board's vertical center, so both control clusters sit on
the same horizontal row. This replaces the D-pad's old position (X=22.5mm,
Y=100–116mm span) — NAV5 sits noticeably higher on the board than the old D-pad did.

**Removed:** `SW1`, `SW2`, `SW3`, `SW4` (the 4 individual D-pad `SW_Push` instances)
and their `PLACEMENTS` rows.

## Change 2: Speaker connector relocation

**What moves:** Only `J5` (the 2-pin JST header the speaker wire connects to) moves
on the PCB — the physical speaker driver itself was never mounted to the PCB (it's
enclosure-mounted, per the original hardware spec's BOM: "El parlante se monta al
enclosure y no a la PCB"). Today `J5` sits at (12, 124), near the board's bottom
edge. It relocates to roughly (18, 30) — inside the X/Y footprint that `U1`
(RP2350-Plus) occupies on the DORSO (back face).

**Why this is possible:** the RP2350-Plus is mounted on the back face; the front
face directly above/behind that same X/Y footprint currently has nothing mounted
there (the LCD and both button clusters sit elsewhere). Relocating `J5` there lets
the physical speaker (screwed/glued to the enclosure on the front, wired to `J5`)
occupy that already-claimed volume instead of needing dedicated space of its own
near the board's bottom edge.

**Consequence — board height:** with nothing left requiring room near the bottom
edge, `BOARD_H` (currently 90×**130**mm, both provisional — gate V-0) can shrink.
Set it to **105mm** (from 90×130 to 90×105): with the D-pad and `J5` gone from the
Y100–130 range, the lowest remaining front-face content is the X/Y/A/B diamond's
bottom point (`B`, Y=91mm), so 105mm leaves the same ~10–14mm bottom margin the
board already keeps elsewhere. Keep `BOARD_H`'s `verified=False`/provisional status
in `params.py` exactly as `BOARD_W` already has it — 105mm is a reasoned placeholder
consistent with the rest of the layout, not a final fabrication dimension; the real
number still comes from the Rhino layout pass like the rest of the contour
(`gen_template_dxf.py` → `parse_dxf.py` cycle, per the fork plan's "Out of scope"
section).

**Not changed:** `J5`'s wiring (`SPK_P`/`SPK_N`, the amplifier's BTL output — still
untouched), the audio chain, and every other connector/component.

## Files touched (implementation-plan-level, not exhaustive)

- `pinmap.py`: add one `FREE` pin → `BTN_OK`
- `netlist.py`: remove `SW_Push` D-pad instances (`SW1`-`SW4`) and their `TACTS`
  entries; add back the `NAV_WS1004` `SYMS` entry and a single instance (`SW13`,
  wired per above) — this is largely restoring code Task 4 deleted, with the wiring
  adjusted for pikocore_gamepad's single-NAV5 layout instead of GAMESETUP's dual-nav
  layout
- `placements.py`: remove `SW1`-`SW4` rows, add `SW13` (NAV5) at (22.5, 83), move
  `J5`'s row to its new position near `U1`
- `params.py`: `BOARD_H` provisional value 130 → 105 (keep `verified=False`)
- `docs/hardware/pikocore_gamepad-pinout.md`: add `BTN_OK`'s GPIO, note `DPAD_*`
  nets now originate from the NAV5 instead of 4 discrete switches (no pin-number
  changes for those 4)

## Testing

Same verification pipeline the fork plan already established:
`python -m unittest discover tests` (existing tests for the 4 D-pad switches need
updating to reflect the NAV5 swap; new tests for the `CENTER`→`BTN_OK` wiring),
`checks/run_all.py` (G-2/G-4/G-5 must stay clean; G-0 will keep failing on the
already-known pre-existing provisional items, now plus the new `BOARD_H` value
until it's Rhino-finalized), and `kicad-cli sch erc` (0 errors, warnings limited to
the 2 remaining reserved `EXP_GP` pins).

## Out of scope

- The exact final `BOARD_H` value (Rhino layout pass, separate from this spec)
- PCB copper routing
- Enclosure design for the speaker mount and NAV5 cutout
- Sourcing/confirming the NAV5 part is still in stock at LCSC (it was verified once
  during GAMESETUP's own history; re-confirming stock before ordering is a BOM task)
