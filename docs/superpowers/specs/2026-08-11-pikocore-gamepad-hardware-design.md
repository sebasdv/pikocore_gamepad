# pikocore_gamepad — Hardware Design & BOM

**Date:** 2026-08-11
**Status:** Approved (hardware/BOM scope only — firmware port and PCB layout are separate follow-on work)

## Context

The existing repo (`pikocore-main`, branch `port/rp2350-gamepi13`) is a port of pikocore
onto a **Waveshare RP2350-PiZero + GamePi13 HAT** — see `README.md`. `pikocore_gamepad` is a **new,
independent device**: not a HAT-based build, but a custom handheld built from scratch
around the **Waveshare RP2350-Plus** core module, with its own carrier PCB, enclosure,
and audio/power subsystem. It keeps the same purpose as the original pikocore and the
current port — a hackable lo-fi sampler/mangler — just on new physical hardware.

The pikocore audio engine (sample playback, slicing, retrigger/stutter, effects,
filter, timestretch) is untouched by this hardware change. What changes is the I/O
layer (button GPIOs) and the audio output driver (PWM → I2S), following the same
kind of repin work already done for the GamePi13 port.

## Core module: Waveshare RP2350-Plus

- RP2350A, dual-core Arm Cortex-M33 + dual-core Hazard3 RISC-V, up to 150MHz
- 520KB SRAM, **16MB on-board flash** (W25Q128JVSIQ) — chosen for parity with the
  current port's `.pikobank` bank size/format
- 26 multi-function GPIO, Pico-2-compatible pinout: 2×SPI, 2×I2C, 2×UART, 4×12-bit ADC,
  16 PWM channels, 12 PIO state machines
- Onboard **ETA6096** LiPo charge/discharge manager + **MP28164** DC-DC buck-boost
  (2A max load) — battery charging and power regulation are already handled by the
  module; no separate charger IC (e.g. TP4056) is needed on the carrier PCB
- USB-C, onboard user LED, BOOT/RESET buttons
- **The unit on hand has pre-soldered THT pinheaders** (not the bare castellated
  variant) — the design accounts for this specifically (see Mounting below)

### Mounting

The RP2350-Plus's THT pins are **soldered directly into through-holes on the carrier
PCB** — no intermediate female headers. This was chosen over a socketed/pluggable
mount to keep the stack height low; the trade-off is the module is not
field-replaceable without desoldering. Carrier PCB footprint: 2× rows of 20 THT pads,
0.1" pitch, spaced per the Pico-2 pinout.

## Subsystem BOM

> **Buttons row superseded 2026-08-11.** The D-pad became a single 5-way NAV5 nav
> switch instead of 4 discrete tacts — see
> [2026-08-11-pikocore-gamepad-nav5-speaker-reloc-design.md](2026-08-11-pikocore-gamepad-nav5-speaker-reloc-design.md).
> The rest of this table is still current.

| Subsystem | Component | Part | Notes |
|---|---|---|---|
| Core | RP2350-Plus, THT pinheader version, 16MB flash | Waveshare RP2350-Plus | Soldered direct to carrier PCB, see Mounting |
| Display | ST7789 240×240 SPI LCD, 1.3" | Standalone module, **THT pin connector** (not FPC) | Reuses vendored driver in `src/gamepi13/lcd/`, repinned to new SPI bus |
| Buttons | 12× tactile switches | D-pad: 4×6mm + 4-way cross · Face (Y/X/B/A): 4×6mm round + keycaps · Select/Start: 2×3×6mm · L/R: 2×6mm mounted edge-on | Same logical button mapping as the current port — input layer changes GPIO numbers only |
| Audio DAC | PCM5102A | I2S DAC IC/breakout | Replaces the current PWM audio path; firmware driver moves from PWM to I2S (BCK/LRCK/DIN) |
| Audio amp | PAM8403 | Stereo class-D, 2×3W | Drives the speaker from the DAC's line-level output |
| Audio speaker | 1× mono speaker, 8Ω 1W, ~28mm | — | **Mono** — L+R summed, matching the original pikocore/GamePi13 approach. True stereo is only realized through the headphone jack. |
| Audio jack | 3.5mm TRS, normally-closed switch contact | — | NC contact cuts the speaker amp when a plug is inserted |
| Battery | LiPo 3.7V, **2000mAh** | Connects via MX1.25 to the RP2350-Plus's onboard battery header | Charge + power management already integrated (ETA6096); no separate charge circuit needed |
| Power switch | Slide switch, SPDT | In series between battery and the RP2350-Plus's MX1.25 header | Prevents standby battery drain — the RP2350-Plus itself has no on/off switch |
| Enclosure | 3D-printed case (FDM) | PLA or PETG, custom design | M2 heat-set inserts (qty TBD by final case design) |
| PCB | Custom carrier PCB, 2-layer | KiCad | Hosts: RP2350-Plus THT mount, LCD THT connector, button switches, PCM5102A + PAM8403, headphone jack, battery header passthrough, power switch |

## Storage

Samples live in the RP2350-Plus's internal 16MB flash only, loaded via the existing
USB WebUSB bank-loader web app (`web/`). No microSD — this mirrors the current port's
default configuration (`PIKO_GAMEPI13_SD` stays off).

## Out of scope for this spec

- PCB schematic/layout (KiCad) — separate implementation task
- Enclosure 3D model and exact case dimensions (battery form factor, standoff count,
  button cutouts) — depends on final component footprints once parts are in hand
- Firmware repin (button GPIOs, I2S audio driver) — separate implementation task,
  follows the pattern already established in the GamePi13 port's I/O layer rewrite
- Exact LCD module part number/vendor — "1.3\" ST7789 240×240, THT pin connector"
  is the spec; final part chosen when sourcing

## Open questions resolved during this design pass

1. Battery capacity: **2000mAh** (chosen over smaller cells; final enclosure volume
   must accommodate this).
2. Amp channel usage: PAM8403 is stereo-capable but drives a **single mono speaker**
   (L+R summed); true stereo is only exposed via the headphone jack.
3. LCD connector type: **THT pins**, not FPC — to match the RP2350-Plus's THT mounting
   approach and simplify assembly.
