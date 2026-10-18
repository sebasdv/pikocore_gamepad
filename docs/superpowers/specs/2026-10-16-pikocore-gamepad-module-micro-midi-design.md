# pikocore_gamepad — Micro layout (100 × 60 mm) and TRS MIDI on the RP2350-Plus module

Date: 2026-10-16. Branch: `hw/modulo-micro-midi`, cut from `origin/main` (9b9cb41).
Status: design approved in chat (direct soldering, start from `main`); spec written for review.

## Why this exists

The chip-down board (branch `hw/chipdown-rp2350`, PR #2, closed) was dropped on
2026-10-16: the JLCPCB quote for 4 layers, two-sided assembly and ~120 SMD parts
was not justifiable. This spec ports the two things that do not depend on the
chip-down — the Game Boy Micro layout on 100 × 60 mm and the TRS MIDI — onto the
Waveshare RP2350-Plus **module**, which already carries the MCU, flash, USB-C,
LiPo charger and 3V3 regulation.

## What carries over, and what does not

Taken from `hw/chipdown-rp2350` (all verified there: 210+ tests, ERC 0/0, DRC
0/0/0):

- Front layout: panel and flex connector J4, D-pad cross, X/Y/A/B diamond,
  Select/Start under the diamond, L/R shoulder tacts, slide switch.
- The MIDI circuit: J6/J7 jacks, U9 SN74LVC1G17 (C10425), U10 H11L1SR2M
  (C20082), D3, R40–R43, C56, with both pinouts verified against datasheets
  (copies in `hardware/pikocore_gamepad/datasheets/`) and the Tip/Ring
  polarity corrected (DIN 4 = Ring feeds the opto anode).
- Pipeline fixes that are not chip-down specific: `wx.DisableAsserts()` in
  `route_io.py` (the DSN export hung on a modal wx dialog), the protected
  pre-routed copper and the two-pass routing with a keep-only-if-better guard,
  the firmware guards for pin stubs set to -1.

Dropped: the RP2350A core block (`rp_core*.py`, `import_rp_minimal.py`,
`lib/rp_minimal.pretty`), the whole power section (J2, U8, U7, D1/D2, L4/L5,
the divider resistors), BOOTSEL/RUN and the SWD pads (the module has its own
BOOT and RESET buttons on its top face and a 3-pin SWD footprint), the JST GH
battery connector J3 (see "Battery"). 57 of the chip-down's 138 footprints
disappear; no QFN and no DFN remain, which is what made the quote expensive.

## Module mounting: direct soldering by castellations

`main` puts the module on a 2×20 socket. In the Micro layout the socket's pin
tails would come out in the middle of the front, where the panel, the flex
and the tact legs are. The module is therefore soldered flat to the back by its
castellated edges (Waveshare: "Castellated module allows soldering directly to
carrier boards").

**Footprint: KiCad's official `Module:RaspberryPi_Pico_SMD_HandSolder`.** The
RP2350-Plus is pin-compatible with the Pico and its geometry matches, checked
against Waveshare's dimension drawing (`datasheets/RP2350-Plus_dimensions_waveshare.jpg`,
from the wiki figure `RP2350-Plus-details-size`):

| Quantity | Waveshare drawing | KiCad Pico footprint |
|---|---|---|
| Board | 21.00 × 51.00 mm | 51.0 long (courtyard ±25.5) |
| Pad pitch | 2.54 mm | 2.54 mm |
| First pad from the short edge | 1.37 mm | 25.5 − 24.13 = 1.37 mm |
| Row spacing, centre to centre | 17.78 mm | ±8.89 mm |
| Hole centre from the long edge | 1.61 mm | (21 − 17.78) / 2 = 1.61 mm |
| Pads per side | 20 (pins 1–20 and 21–40) | 40 numbered pads |

Pin numbers are the Pico's, so `pinmap.HEADER_ORDER` and the existing U1 netlist
net names stay as they are. The "HandSolder" variant is used because JLCPCB does
not assemble the module: it is soldered by hand, the rest of the board by
machine. Verifying the copper shape of the Plus's pads against the Pico's is a
physical step before ordering: print the footprint 1:1 and lay the module on it.

The module sits flat on the board. Under its 22.2 × 51 mm outline (pads reach
x ±11.09 and y ±25.5) there must be **no through-hole tail from the front and
no SMD part**; copper under it is fine.

## Pin map

GP0–GP22 and GP26 keep their functions. The module exposes GP0–GP22 and
GP26–GP28; GP23/24/25 and GP29 are internal to it. The two free pins carry the
MIDI:

| GPIO | Net | Notes |
|---|---|---|
| GP28 | `MIDI_TX` | UART0 TX capable; through U9 to MIDI OUT |
| GP27 | `MIDI_RX` | no hardware UART RX on GP27: the firmware uses a PIO UART receiver (it already uses PIO for I2S and the one-wire MIDI input) |

`FREE` becomes empty. `config.h` gains `PIN_MIDI_TX 28` and `PIN_MIDI_RX 27`;
G-4 keeps it in step with `pinmap.py`. The firmware stubs that sit on those pins
today (`GAMEPI_CLOCK_PIN` 27, `GAMEPI_TRIGO_PIN` 28 in `src/hw_gamepi13.h`) go to
-1 with the guards already written on the chip-down branch, and a test checks
the literals against `pinmap.py`. The module's own LED (GP25) stays as the beat
LED. A PIO UART RX driver is firmware work and is out of scope here.

## Back layout

Front is the chip-down's, unchanged. On the back the module is placed vertically
in the one band with no front leg tails, x 31–69, with its USB-C at the bottom
edge (the Micro's USB position):

- **Module** centre (50, 33.0), long axis along Y, USB-C end toward y = 60. The
  hand-solder pads end at y ≈ 58.5, 1.5 mm from the edge. The module's BOOT and
  RESET buttons and its BAT header face the back and stay reachable.
- **Jacks.** The module's top end (y ≈ 7.5) blocks the centre of the top edge,
  so the three jacks are split: MIDI IN in the top-left band (centre x ≈ 30),
  MIDI OUT in the top-right band (x ≈ 69.5), both clear of the UP and X tact
  legs; the phones jack on the **left edge**, rotated 90° (barrel through the
  left edge, centre y ≈ 45), in the area below the D-pad legs and left of the
  slide switch legs.
- **Audio, boost and MIDI parts** go in the free bands: left, x 0–38 below the
  D-pad legs; right, y 51–60 below the Select/Start legs; and the 7 mm band
  between the diamond and Select/Start, where the two 470 µF capacitors (6.3 mm
  can) sit as before.

These coordinates are a starting hypothesis. `check_placement.py`, the packer's
`FREE_REGIONS` and DRC arbitrate, as they did for the chip-down layout. Free
back area outside the keep-outs is an estimate of ~2,500 mm² against ~1,600
mm² of SMD parts; if it does not close, the fallback is a 100 × 65 outline.

## Battery

The module has its own battery header (Waveshare: "Onboard Lithium battery
recharge/discharge header"; the connector model is not stated on the wiki and
not identifiable from the drawing) and the carrier cannot reach that line. The
user's cells have JST GH (1.25 mm, latched) plugs. If the module's header is
MX1.25, as is usual for these boards, the cells need a GH-to-MX1.25 pigtail or a
re-crimped plug. **Open item**: look at the module's connector with the module in
hand.

## Pipeline changes

| File | Change |
|---|---|
| `pinmap.py` | GP27 `MIDI_RX`, GP28 `MIDI_TX`, `FREE = ()`; docstring and UART tables updated |
| `netlist.py` | MIDI instances and symbols from the branch; U1 footprint `Module:RaspberryPi_Pico_SMD_HandSolder` |
| `gen_sch.py` | sheet `07_midi` and its note |
| `placements.py` | rewritten for the Micro front and the back above |
| `gen_pcb.py`, `gen_fp.py` | module model reference, socket footprint copy removed |
| `params.py` | `BOARD_H` 80 → 60 |
| `route_io.py`, `finish_pcb.py` | wx asserts, protected copper, two-pass routing |
| `src/boards/pikocore_gamepad/config.h`, `src/hw_gamepi13.h`, `src/main.cpp` | MIDI pins, stubs off, guards |
| `tests/` | pin tests, MIDI netlist tests, firmware-stub test, placement tests |

Routing runs through the existing cycle; the chip-down experience says to budget
several iterations.

## Verification

All `pcb-verify` gates. Pass means tests green, G-5/G-4/G-2/placement green,
ERC 0, DRC 0 errors / 0 unconnected / 0 parity. G-0 stays red for
`LCD_FPC_PIN_ORDER` until the panel is measured. Specific checks: U1's pad
numbers match the Pico header order; no footprint other than U1 overlaps the
module outline; the USB-C end faces the bottom edge in a render.

## Not verified (state on 2026-10-16, after routing)

The board is routed and every automated gate except G-0 is green: 201 tests,
G-5/G-4/G-2/placement, ERC 0, DRC 0 errors / 0 unconnected / 0 parity (15
silkscreen and library warnings). **G-0 stays red for `LCD_FPC_PIN_ORDER`**, as
on `main`, until the panel is measured; `gen_fab.py --force` therefore writes
`pikocore_gamepad_fab_NO-FABRICABLE.zip`, and the freshness gate stays red on
the missing unsuffixed zip for the same reason. What no gate checks:

- The Plus's castellation copper shape against the Pico footprint's. The
  footprint is KiCad's Pico hand-solder footprint without the mounting holes.
  Pitch, row spacing and pad count match Waveshare's drawing, and the user
  states (2026-10-17) that the Plus footprint is identical to the Pico's; how
  that was checked is not recorded, so a 1:1 paper print laid over the module
  is still the physical proof, and it also shows whether the underside is flat.
- The module's battery connector model against the user's JST GH 1.25 cells.
  The carrier cannot reach the module's battery line, so the cells need a
  GH-to-MX1.25 pigtail or a re-crimped plug. The model is still to be confirmed
  with the module in hand (see "Battery").
- Back area: it closed at 100 × 60 with the module. The packer placed all 36 of
  36 back passives with no part left without a place, so the 100 × 65 fallback
  was not needed. No free/used area figures were measured.
- A PIO UART receiver on GP27, and GP28's UART0 TX use, are firmware work.
- Enclosure: USB-C cutout at the bottom edge, access holes for BOOT/RESET,
  jack cut-outs (MIDI at the top edge, phones on the left edge), and the LiPo's
  place behind the module.
- MIDI decoupling: U9 has no bypass capacitor of its own and the only MIDI
  100 nF, C56, sits ~27 mm from U10. It should work at 31.25 kbaud off the 3V3
  plane, but a 100 nF at U9 pin 5 and C56 next to U10 would need one more
  placement + routing cycle.
- The module's 3D model in the render is offset (renders only, not the board).
- No board has been built.

## Out of scope

- Any change to the audio circuit or the panel and its flex (`LCD_FPC_PIN_ORDER`
  stays open).
- The firmware's MIDI drivers.
- Reviving the chip-down.
