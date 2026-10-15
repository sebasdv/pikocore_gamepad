# pikocore_gamepad — Game Boy Micro layout at 100 × 60 mm, with TRS MIDI

Date: 2026-10-15. Branch: `hw/chipdown-rp2350` (builds on the RP2350A
chip-down, commits f606d16 and b680c50). Status: design approved in chat,
spec written for review.

## Goal

Rearrange the board into the Game Boy Micro's horizontal layout — screen in
the centre, D-pad on the left, face buttons on the right, shoulder buttons on
the top corners — on a **100 × 60 mm** outline, and add **MIDI IN and MIDI
OUT on 3.5 mm TRS jacks, type A**. Everything electrical from the chip-down
stays: RP2350A core, charger, buck-boost, audio chain, 12 × 6 mm tacts, the
two 470 µF coupling capacitors.

What was decided and why:

- **100 × 60, not the Micro's 100 × 50.** The user asked for the Micro's
  *layout*, not its size. 60 mm keeps the two 470 µF capacitors and the THT
  tacts without fighting for back-side area, and keeps the Start/Select pair
  below the face buttons instead of squeezing them beside the flex tail.
- **Jacks on the top edge.** Phones, MIDI IN and MIDI OUT all leave through
  the top edge, between the shoulder buttons, so cables point away from the
  hands. USB-C stays on the back, bottom-left.
- **MIDI on the hardware UART1, type A wiring.** No PIO, no new footprints:
  the two MIDI jacks reuse the phones jack part (CUI SJ1-3535NG, already
  verified on this board).

## Front layout

Coordinates in mm from the board's top-left corner, X right, Y down. Each
button group keeps today's internal pitch (6 mm tacts, 8.5 mm between
centres in a cross).

| Group | Refs | Centre | Footprint span |
|---|---|---|---|
| Panel 1.3" (active 23.4 × 23.4) | LCD1 | x 50, y 24 (active-area centre) | x 36.9–63.1, y 10.7–40.0 (active area sits 1.56 mm below the outline's top) |
| D-pad cross | SW1–SW4 | x 18, y 24 | x 6.5–29.5, y 12.5–35.5 |
| X / Y / A / B diamond | SW5–SW8 | x 82, y 24 | x 70.5–93.5, y 12.5–35.5 |
| Select, Start | SW12, SW11 | x 76 and x 88, y 46 | below the diamond, as on the Micro |
| L, R shoulder tacts | SW9, SW10 | x 12 and x 88, y 1.9 | top corners, angled, actuated from the edge |
| Panel flex connector | J4 | x 50, y 52.4, rot 180 | 16.6 × 6.3; 12.4 mm from the panel outline's bottom to J4's centre, as today |
| Power slide switch | SW15 | x 25, y 57.7 | bottom edge, left of J4 |

Clearances that follow from the table: 7.4 mm between each button group and
the panel outline (the Micro has about 4), 3 mm from the D-pad to the left
edge, 6.5 mm from the diamond to the right edge. The panel's active area is
vertically centred on the button crosses.

`placements.py` keeps its structure (one row per footprint, `NUCLEO` for the
core block, `FREE_REGIONS` for the packer) and is rewritten with these
numbers. `_LCD_Y` is no longer derived from the top margin: the panel is
placed by its active-area centre.

## Back layout

Three zones, all on B.Cu, drawn so that the through-hole legs of the 14
front tacts, the slide switch and J4's SMD pads are avoided:

| Zone | What | Where (x, y) | Why there |
|---|---|---|---|
| Top strip | J1 phones, J6 MIDI IN, J7 MIDI OUT (each 9.2 wide × 19.1 deep), MIDI opto and buffer beside them | x 25–75, y 0–20 | between the shoulder tacts; cables up |
| Bottom-left | J2 USB-C, U8 charger and its loop, D1/D2, J3 battery connector | x 0–22, y 40–60 and the left margin | away from the panel; USB cable down |
| Centre band | RP2350A core (`NUCLEO`), U7 TPS63001 loop | behind the panel, x 30–70, y 20–45 | the one area with no THT legs on either side |
| Right | DAC, op-amp, PAM8302A, C23/C24 470 µF (6.3 mm dia, 5.4 mm tall SMD), J5 speaker header | x 70–100, y 36–60 and the right margin | next to the phones jack path |

Nothing changes in the audio or power schematics; only positions move.
`manual_tracks.py` already expresses the USB-C, TPS63001 and RP2350A tracks
relative to `_POS`/`NUCLEO`, so they follow their parts.

Thickness: the tallest parts are the 470 µF capacitors (5.4 mm) on the back
and the 6 mm tacts (5 mm) on the front; with a 1.6 mm board and 1.5 mm walls
the enclosure can be about 15 mm, below the Micro's 17.2. The LiPo lies
beside the core on the back, not under the capacitors.

## MIDI

**Electrical standard.** MIDI 1.0 electrical specification, 3.3 V variant
(MIDI Association CA-033), on 3.5 mm TRS **type A** (MIDI Association
RP-054): Tip = DIN pin 5 (current sink), Ring = DIN pin 4 (current source),
Sleeve = DIN pin 2 (shield).

**MIDI OUT (J7).**
- Ring ← 33 Ω (R40) ← 3V3.
- Tip ← 10 Ω (R41) ← output of U9, a 74LVC1G17 Schmitt buffer, input from
  `MIDI_TX`. The buffer takes the 5 mA loop current and protects the GPIO.
- Sleeve → GND.

**MIDI IN (J6).**
- Tip → 220 Ω (R42) → anode of U10's LED; Ring → cathode. D3 1N4148 (SOD-123)
  in anti-parallel across the LED for reverse polarity.
- U10 = H11L1 Schmitt-output optocoupler (DIP-6 or SMD-6 package), Vcc 3V3,
  100 nF decoupling (C56), output (open collector) → 4.7 kΩ pull-up (R43) to
  3V3 → `MIDI_RX`.
- Sleeve **not connected**: the receiver must not ground the shield.

**GPIO.** `VBUS_SENSE` moves from GP24 to GP27. GP24 becomes `MIDI_TX`
(UART1 TX) and GP25 `MIDI_RX` (UART1 RX). GP28 stays free. Firmware:
`src/boards/pikocore_gamepad/config.h` gets `PIN_MIDI_TX 24`,
`PIN_MIDI_RX 25` and `PIN_VBUS_SENSE 27`; gate G-4 keeps it in step with
`pinmap.py`.

**Schematic.** New sheet `07_midi` ("MIDI - entrada y salida TRS tipo A")
with J6, J7, U9, U10, D3, R40–R43, C56 and a note that states the type-A
pinout and the 3.3 V resistor values.

**New parts.**

| Ref | Part | Package | LCSC | Verified |
|---|---|---|---|---|
| J6, J7 | CUI SJ1-3535NG 3.5 mm TRS | THT horizontal | same as J1 | footprint yes (J1) |
| U9 | 74LVC1G17 | SOT-353 / SC-70-5 | — | pinout from TI datasheet before netlist |
| U10 | H11L1 (or H11L1M SMD) | DIP-6 / SMD-6 | — | pinout from onsemi datasheet before netlist |
| D3 | 1N4148W | SOD-123 | — | standard |
| R40–R43 | 33 Ω, 10 Ω, 220 Ω, 4.7 kΩ | 0603 | from `LCSC_PASIVOS` where present | |
| C56 | 100 nF | 0603 | C14663 | |

LCSC codes left blank are filled before `gen_fab.py`, never guessed.

## Pipeline changes

| File | Change |
|---|---|
| `params.py` | `BOARD_H` 80 → 60 (verified: it is a design choice, not a measurement) |
| `pinmap.py` | GP24 `MIDI_TX`, GP25 `MIDI_RX`, GP27 `VBUS_SENSE`; `FREE = (28,)` |
| `netlist.py` | MIDI instances, `MIDI_TX`/`MIDI_RX` nets, U1 pads 24/25/27 renamed |
| `gen_sch.py` | sheet `07_midi`, root note updated |
| `placements.py` | rewritten per the two tables above |
| `manual_tracks.py` | no new tracks expected; J2/U7/U1 tracks follow their parts |
| `gen_template_dxf.py` output | regenerated for 100 × 60 |
| `src/boards/pikocore_gamepad/config.h` | three defines |
| `tests/` | pinmap: UART1 pairing (24 TX, 25 RX); netlist: MIDI nets and sleeve of J6 open; placement: all front parts inside 100 × 60 |
| `hardware/pikocore_gamepad/README.md`, this spec | state |

Routing: the full cycle (`gen_sch` → netlist → `gen_pcb` → `manual_tracks`
→ `plane_vias` → `route_io export` → freerouting → `route_io import` →
`finish_pcb` → DRC), two passes with the second kept only if it leaves fewer
open connections, as established on the chip-down. Expect several
placement iterations: the back is denser than at 100 × 80.

## Verification

All `pcb-verify` gates. Pass means: tests green, G-5/G-4/G-2/placement
green, ERC 0, DRC 0 errors / 0 unconnected / 0 parity. G-0 stays red for
`LCD_FPC_PIN_ORDER` until the panel is measured, as on `main`. Two more
gates specific to this change:

- A test that `MIDI_TX`/`MIDI_RX` sit on a UART1 TX/RX pair of the RP2350A.
- A test that J6's sleeve pad has no net.

## Not verified by any source yet

- H11L1 and 74LVC1G17 pinouts and LCSC codes: to be taken from the
  datasheets when the netlist is written.
- Whether the 0603 10 Ω and 33 Ω parts exist in `LCSC_PASIVOS`; add them
  with a code or leave blank.
- MIDI IN at 3.3 V with an H11L1: the datasheet allows Vcc down to 3 V;
  check on the bench with a 5 V sender.
- The enclosure study for 100 × 60 (button holes, jack cut-outs on the top
  edge) is not part of this spec.

## Out of scope

- Any change to the audio or power circuits.
- A 100 × 50 variant.
- MIDI over USB (the RP2350A already enumerates as USB; a class driver is a
  firmware task).
- Firmware beyond the three `#define`s.
