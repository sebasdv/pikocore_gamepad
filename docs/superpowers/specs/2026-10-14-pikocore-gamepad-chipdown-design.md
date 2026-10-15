# pikocore_gamepad — RP2350 chip-down (V2)

**Date:** 2026-10-14
**Branch:** `hw/chipdown-rp2350` (from `main` at `9b9cb41`)
**Status:** Draft — design decisions fixed, implementation in progress

## Goal

Replace the Waveshare RP2350-Plus module (U1, soldered on a 2×20 header on the
back) with the same silicon and support circuitry placed directly on the
carrier PCB. Everything else on the board — audio chain, controls, flex panel,
connectors — stays exactly as it is on `main`; the firmware keeps its pin map.

Why: the module plus its header is the tallest thing on the board (≈8.5 mm),
it eats the left half of the back side, and it costs more per unit than its
parts. Why not before: it moves the power path and the MCU from a known-good
module onto an unproven layout. The V1 board on `main` exists to prove the
audio, controls and ergonomics first; this branch can be fabbed after or in
parallel.

## What the module provided, and what replaces it

| Function on the module | Module part | Chip-down part | LCSC | Source of truth |
|---|---|---|---|---|
| MCU | RP2350A | RP2350A, QFN-60 7×7 0.4 mm | C42411118 | RP2350 datasheet; pinout cross-checked: KiCad 10 `MCU_RaspberryPi:RP2350A` symbol **and** pad→net map of RP's official minimal board — identical on all 61 pads |
| Core 1V1 regulator (on-chip SMPS) | L 3.3 µH 2016, 4.7 µF ×3, 33 Ω | same: Abracon AOTA-B201610S3R3-101-T + 4.7 µF 0402 ×3 + 33 Ω | C42411119 | "Hardware design with RP2350" §2.1 (RP insists on this exact inductor, oriented, and this layout) |
| Crystal | 12 MHz | Abracon ABM8-272-T3, 15 pF ×2, 1 kΩ series | C20625731 | Guide §4 (RP: "we highly recommend this crystal along with the accompanying circuitry") |
| Flash | W25Q128JVSIQ (16 MB) | same, SOIC-8 208 mil | C97521 | Guide §3; RP minimal board U3 |
| BOOTSEL / RUN | 2 buttons | 2 small SMD buttons (TS-1187A, C318884): BOOTSEL through 1 kΩ to QSPI_SS, RUN straight to GND (RUN already has its pull-up on-chip; no series resistor) | C318884 | Guide §3.1, §5.4 |
| USB-C | 16P receptacle, CC 5.1 k ×2, 27 Ω ×2 | HCTL HC-TYPE-C-16P-01A, same passives | C2894897 | Waveshare RP2350-Plus schematic; guide §5.1 |
| LiPo charger | ETA6096 (DFN3×3-10), ISET 160 k ≈1 A, 2.2 µH/2 A, 22 µF PMID, 10 µF BAT, 1 µF VIN | same, but **ISET 150 k → 1.2 A** (a datasheet table point, not Waveshare's interpolated 160 k) | C7465538 | ETA6096 datasheet (pinout verified: 1 VIN, 2 PMID, 3 PGND, 4 NC, 5 SW, 6 BATS, 7/10/EP AGND, 8 ISET, 9 STAT) and Waveshare schematic — agree |
| Power OR | MBR230LSFT1G ×2 (VBUS→VSYS, VBAT→VSYS) | same | C126673 | Waveshare schematic |
| 3V3 rail | MP28164 buck-boost | **TI TPS63001** (fixed 3.3 V), 2.2 µH, 10 µF in, 2×10 µF out, VINA 100 Ω + 100 nF | C28060 | TPS6300x datasheet SLVS520C (pinout verified: 1 VOUT, 2 L2, 3 PGND, 4 L1, 5 VIN, 6 EN, 7 PS/SYNC, 8 VINA, 9 GND, 10 FB→VOUT, EP PGND) |
| Power switch input | 3V3_EN pin (100 k to VSYS) | PWR_EN net: 100 k to VSYS → TPS63001 EN; SW15 shorts it to GND, unchanged | — | — |
| Battery connector | MX1.25 2P | Molex PicoBlade 53398-0271 (1.25 mm, vertical SMD) | — | KiCad official footprint |
| VBUS sense | 51 k / 100 k → GP24 | **100 k / 200 k** → GP24 (5 V → 3.33 V, same ratio class; values already on the BOM) | — | Waveshare schematic, values changed |
| VSYS monitor | 200 k / 100 k (+ NMOS) → GP29/ADC3 | 200 k / 100 k + 100 nF → GP29, **no NMOS** (≈6 µA into an unpowered pad, harmless; Pico 2 does the same) | — | Waveshare + Pico 2 convention |
| SMPS mode | GP23 → MP28164 MODE | GP23 → TPS63001 PS/SYNC, 10 k pull-down (power-save by default, firmware can force PWM for lower audio ripple) | — | TPS6300x datasheet |
| User LED | GP25 | **dropped** (nobody sees the back of a handheld) | — | — |
| SWD | 3-pin header | 3 test pads (SWCLK, SWDIO, GND), out of the BOM and the CPL | — | Guide §5.3 |

### Why the TPS63001 and not the module's MP28164

The MP28164 (QFN-11 2×3 mm) has no KiCad footprint, no EasyEDA footprint
(the LCSC listing C3187707 returns nothing from the EasyEDA API) and no
plain-MP28164 LCSC listing. Using it means drawing an 11-pad 0.5 mm QFN by
hand from a package drawing — the exact failure mode this repo already paid
for once (the audio jack). The TPS63001 has an official KiCad footprint
(`Package_SON:Texas_DRC0010J`), a fixed 3.3 V output (no feedback divider to
get wrong), 1.8–5.5 V input (covers a dead LiPo through 5 V USB), up to 1.2 A
at 3.3 V (the 3V3 rail needs < 200 mA), and is in LCSC stock.

### Pin map: unchanged for the firmware, three additions

GP0–GP22 and GP26 keep exactly the functions they have on `main`. New:

| GPIO | Net | Notes |
|---|---|---|
| GP23 | `BB_PS` | TPS63001 PS/SYNC (0 = power-save, 1 = forced PWM) |
| GP24 | `VBUS_SENSE` | 1 = USB present (100 k / 200 k from VBUS) |
| GP29 | `VSYS_ADC` | ADC3, VSYS / 3 |

GP27/GP28 stay free. The firmware header gets three `#define`s; nothing it
already uses moves.

## Layout rules that come from the sources, not from taste

- **Copy, don't redraw:** the RP2350A footprint (with its exposed-pad via
  array) and the AOTA inductor footprint are copied from RP's MIT-licensed
  minimal board (`RPI-RP2350A-MINIMAL_R4-S1`), and so is the relative
  placement of U1, L1, C6/C7/C9, R3 and the crystal. RP: "if you choose not to
  use our example, then you do so at your own risk".
- **Inductor orientation:** the AOTA part has a polarity dot; the footprint
  copy carries it, and the CPL rotation for L1 must be checked against the
  reel, like any polarised part.
- **0402 passives** around the QFN (RP's choice for 0.4 mm pitch), 0603 and
  up elsewhere as today.
- **USB pair:** 27 Ω close to the chip, over unbroken GND (In1 is solid GND
  on this 4-layer stack, which is better than RP's 2-layer reference).
- **Board-wide rules:** Default netclass 0.127 mm track / 0.127 mm
  clearance with 0.45/0.2 mm vias; minimum through drill 0.2 mm (RP's and
  TI's thermal vias). With 0.15/0.15 and KiCad's 0.6 mm default via,
  freerouting left 2 to 15 different signals unrouted per run around the
  0.4 mm QFN. All of it is inside JLCPCB's standard 4-layer process.
  Power netclass 0.4 mm with its own 0.6/0.3 via covers GND, 3V3, VSYS,
  VBUS, VBAT and the switch nodes of the charger and the TPS63001.
- **Two scoped `.kicad_dru` exceptions, both inherited geometry:** J2's pads
  sit 0.18 mm from the connector's own locating NPTHs (HCTL footprint), and
  C32 sits 0.127 mm from 1V1 copper in RP's layout. Each rule names the
  footprint, nothing else gets the relaxed value.
- **Pre-routed copper is protected:** everything in the DSN before
  freerouting (RP core, manual tracks, plane fanouts) goes in as
  `(type protect)`. As `(type route)` freerouting rearranged the regulator's
  1V1 copper into two islands.
- **Core zones are keepouts for the router:** the chip-side zones of the
  copied core (3V3 ring, 1V1 ring, VREG_LX, GND islands) go into the DSN as
  keepouts too. freerouting does not treat another net's zone as an
  obstacle, and once ran seven signals through the 1V1 ring.
- **GPIO escape lanes copied from RP, for three nets only:** LCD_DC,
  LCD_MOSI and BTN_START take RP's own fanout from the pin to 7.5 mm from the
  chip centre (`rp_core.FANOUT_NETS`). freerouting boxed those pins in run
  after run. Copying the fanout of every GPIO was tried and was worse
  (10 to 15 nets open): the stub ends point where RP's board has room and
  this one does not.
- **Pin 1 (IOVDD) into the 3V3 ring by hand:** RP's board feeds it from a
  whole-board 3V3 pour that does not exist here.
- **TPS63001 at 180 deg:** on the back the footprint is mirrored; at 0 deg
  L1/L2 faced away from the inductor and the switch nodes had to cross under
  the chip. L1/L2 are hand-routed at 0.35 mm (0.4 does not leave the 0.5 mm
  pitch with clearance).
- **USB-C GND and VBUS are hand-routed:** the GND pads cannot via down
  (NPTH keepout) and go to the THT shell; the two VBUS pairs are bridged on
  F.Cu through two vias (`manual_tracks.py`).

## Assembly

Everything new is SMD and goes on the **back**, next to the audio chain that
JLCPCB already assembles. QFN-60 0.4 mm and DFN 0.5 mm are machine-only.
Note, not changed here: J4 (panel FPC connector) is on the **front**, so the
board already needs two-sided assembly.

## Not verified by any source yet

- R31 (ISET 150 kΩ 0603) has **no LCSC code**: the EasyEDA API rate-limited
  the lookup. Blank on purpose; fill it before ordering.
- Charger inductor L4 (C3002559, 2.2 µH): saturation current not checked
  against the 1.2 A charge current plus ripple.
- 1.2 A charge rate assumes a cell rated for ≥1 C at its capacity; a small
  cell needs a larger ISET resistor.
- Battery connector polarity: LiPo cells with "MX1.25" plugs come in both
  polarities. Same caveat as the module.
- Thermal: ETA6096 at 1 A next to the QFN. Nothing measured.

## Out of scope

- Moving any audio, control or panel part.
- Firmware beyond the three new `#define`s.
- Enclosure changes (the board outline does not change; the back gets ≈8 mm
  thinner where the module was).
