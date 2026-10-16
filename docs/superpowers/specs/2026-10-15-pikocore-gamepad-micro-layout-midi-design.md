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

Coordinates in mm from the board's top-left corner, X right, Y down. Each button group uses 6 mm tacts at 8.5 mm between body centres in a
cross (today's 12.5 mm pitch does not fit beside a centred panel on 100 mm).

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
| Top strip | J6 MIDI IN (x 36), J1 phones (x 50), J7 MIDI OUT (x 64), each 9.2 wide × 14.5 deep, pads 3 mm from the edge; U10 opto left of J6, U9 buffer right of J7 | x 18–78, y 0–18 | between the shoulder tacts; cables up |
| Bottom-left | J2 USB-C at the bottom edge (mouth down), U8 charger and its loop above it, J3 battery and BOOTSEL/RUN in the left margin | x 0–22, y 36–60 and x 0–6 | away from the panel |
| Centre | RP2350A core (`NUCLEO = (47, 30.5, 270)`), footprints x 33–66, y 23–42 | behind the panel | the one area with no THT legs on either side; rot 270 puts the LCD/I2S/button pin row toward J4 and the DAC |
| Bottom band | U7 TPS63001 loop (left), U3 op-amp (centre), U5 DAC (right), DAC passives packed around them | x 31–69.5, y 49–59 | under the core, behind J4 (front SMD, no conflict); the LCD lanes' corridor x 43.5–53 is kept free of anchored parts |
| Right band | C23/C24 470 µF (6.3 mm dia) and bleeders R19/R20 | x 69.5–94.5, y 36–43 | the 7 mm gap between the diamond's and Select/Start's pads; the body overhang lands on pad annuli, which DRC accepts (two silk-over-copper warnings) |
| Bottom-right | U4 PAM8302A, the TPS61023 boost loop moved as a rigid block, J5 speaker header in the right column | x 69.5–99, y 49–59; J5 at (97, 33) | next to the audio |

**Core block at rot 270, not the chip-down's 90.** At rot 90 pins 1–15 (LCD,
I2S_DIN, D-pad, X/Y/A/B) faced the jacks with J4 and the DAC on the far side
of the chip; two routing cycles left 1 and 5 of those nets open with
freerouting flat from pass 10 on. Half a turn more and that row faces J4;
the next cycle closed every net. `manual_tracks.py` maps its U1-relative
offsets by `NUCLEO`'s rotation.

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
- The sender sources current on DIN 4 and sinks it on DIN 5; type A puts
  DIN 4 on Ring. So: Ring → 220 Ω (R42) → anode of U10's LED; Tip → cathode.
  D3 1N4148 (SOD-123) in anti-parallel across the LED for a reversed (type B)
  cable. (The first draft of this spec had Tip and Ring swapped here; the
  final review caught it.)
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

- Both MIDI pinouts are now verified, copies in
  `hardware/pikocore_gamepad/datasheets/`: U9 (74LVC1G17) against TI SCES351Y
  (rev. October 2025, page 3): DCK 1 NC, 2 A, 3 GND, 4 Y, 5 VCC; U10 (H11L1M)
  against the Fairchild/onsemi datasheet Rev. 1.0.7 (September 2014,
  figure 1): 1 anode, 2 cathode, 3 no connection, 4 VO, 5 GND, 6 VCC;
  operating voltage 3 to 15 V, output sinks 16 mA at 0.4 V.
- LCSC codes for the MIDI parts are in `netlist.py`, each checked on its
  lcsc.com product page on 2026-10-16: C22859 (10 Ω), C23140 (33 Ω), C22962
  (220 Ω), C81598 (1N4148W, ST Semtech SOD-123), C10425 (SN74LVC1G17DCKR,
  SC-70-5), C20082 (H11L1SR2M, the surface-mount gull-wing H11L1M on reel;
  C16587 is the through-hole DIP and does not fit the SMDIP-6 footprint).
  The fab package's 20 remaining blanks are the pre-existing hand-soldered
  lines (buttons, jacks, panel, speaker, LiPo, 24 Ω, 470 µF), as on `main`.
- MIDI IN at 3.3 V with an H11L1M: 3 V is the datasheet's minimum, but its
  threshold current (1.6 mA turn-on) is specified at Vcc = 5 V; the MIDI loop
  delivers about 5 mA, so the margin is ×3. Still worth a bench check with a
  5 V sender.
- `route_io.py` export/repaso used to hang on a modal "wxWidgets Debug Alert"
  (a benign non-closed-outline assert inside `ExportSpecctraDSN`); it now
  calls `wx.DisableAsserts()` at import. Routing is near its limit around the
  QFN: freerouting's result varies run to run, so LCD_DC and LCD_MOSI are
  hand-dropped from the copied lanes to J4 and PWR_EN is hand-routed into the
  slide switch; the copied lanes run to 12.5 mm from the chip centre.
- Gate G-4 reads only `config.h`; firmware-only pins chosen with literal
  numbers in `src/hw_gamepi13.h` (`GAMEPI_LED_PIN`, `GAMEPI_CLOCK_PIN`,
  `GAMEPI_TRIGO_PIN`) are outside it. The final review found the beat LED on
  GP25 (now `MIDI_RX`) and the clock-in stub on GP27 (now `VBUS_SENSE`); both
  moved (LED and trigger-out off, clock-in on GP28) and
  `tests/test_pinmap.py::TestFirmwareStubs` now checks those literals against
  `pinmap.py`. The `PIKO_GAMEPAD` firmware builds; it has not run on hardware.
- The enclosure study for 100 × 60 (button holes, jack cut-outs on the top
  edge) is not part of this spec.
- No board has been built.

## Out of scope

- Any change to the audio or power circuits.
- A 100 × 50 variant.
- MIDI over USB (the RP2350A already enumerates as USB; a class driver is a
  firmware task).
- Firmware beyond the three `#define`s.
