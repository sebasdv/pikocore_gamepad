# pikocore_gamepad PCB — Fork GAMESETUP's KiCad Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Unlike the superseded manual-GUI plan, **every task here is a text-file edit or a
> CLI command** — `pinmap.py`/`netlist.py`/`placements.py` are plain Python, and
> ERC/DRC run through `kicad-cli`, not the KiCad GUI. Normal autonomous execution
> applies.

**Goal:** Fork `C:\midigame\GAMESETUP\pcb\` (a scriptable KiCad generation pipeline
already built and verified for the same Waveshare RP2350-Plus target) into
`hardware/pikocore_gamepad/pcb/` in this repo, strip the subsystems pikocore_gamepad
doesn't have (MIDI I/O, microSD, the 2 nav switches, and the PCF8574 I2C button
expanders that only existed because MIDI+microSD+I2C ate the free GPIOs), and repoint
the 12 buttons to direct GPIO. Everything else — the RP2350-Plus socket footprint,
the 7-pin CS-less ST7789 LCD, and the full PCM5102A→NJM4556AD→PAM8302A+boost audio
chain — carries over with **zero rewiring**, because GAMESETUP's `pinmap.py` is the
single source of truth every other file derives from.

**Architecture:** Same as GAMESETUP: `pinmap.py` (GPIO→function) is authoritative;
`netlist.py` (symbols + instances, pure Python) is consumed by `gen_sch.py` to write
the `.kicad_sch` and by `checks/` to validate; `placements.py` (rewritten by
`parse_dxf.py` from a Rhino-edited board outline) holds footprint positions;
`gen_pcb.py` builds the `.kicad_pcb` from both. This plan touches `pinmap.py` and
`netlist.py` structurally, `placements.py` by deletion only (no new footprint
positions — those get assigned at layout time, out of scope here), and leaves
`gen_sch.py`/`gen_pcb.py`/`gen_fp.py`/`route_io.py`/`finish_pcb.py` untouched.

**Tech Stack:** Python 3.11 (matching GAMESETUP's `__pycache__` artifacts), KiCad 9.0
(`kicad-cli.exe` for ERC/DRC — confirm the same install path GAMESETUP's
`PENDIENTES.md` documents: `$LOCALAPPDATA/Programs/KiCad/9.0/bin/`), git.

---

## Why this fork removes exactly these five subsystems

pikocore_gamepad's hardware spec
([`docs/superpowers/specs/2026-08-11-pikocore-gamepad-hardware-design.md`](../specs/2026-08-11-pikocore-gamepad-hardware-design.md))
calls for 12 buttons, an ST7789 LCD, and an audio path with a speaker + headphone
jack — no MIDI, no microSD, no second control surface. GAMESETUP has those *plus*:

| GAMESETUP-only subsystem | Components | Why GAMESETUP needed it |
|---|---|---|
| MIDI IN/OUT | `H11L1` opto (U6), 2× `JACK_TRS` (J2, J3), R18–R24, D1, C29–C31 | Groovebox feature pikocore_gamepad doesn't have |
| microSD | `MICROSD` (J6), R22–R24, C30–C31 | pikocore_gamepad's spec fixed internal-flash-only storage |
| Nav switches (nav1/nav2, 5-way) | `NAV_WS1004` ×2 (SW13, SW14) | Extra cursor controls pikocore_gamepad's 12-button layout doesn't include |
| PCF8574 I2C expanders ×3 | U10–U12, R1–R3, C1–C3, TP1–TP2 | Only needed because MIDI+microSD+I2C consumed enough GPIO that 22 switch contacts no longer fit directly — **pikocore_gamepad's 12 buttons fit in direct GPIO without this**, since we're not spending pins on MIDI/SD/I2C |
| Expansion header | `Conn_01x09` (J7) | Exposed the PCF8574's now-moot spare GPIO; nothing left to expose once the expanders are gone |

Removing these frees enough GPIO (GP0,1,4,9,10,11,12,13,14,15,18,19 — 12 pins) that
every button wires straight to the RP2350-Plus, matching pikocore_gamepad's original
spec intent (no PCF8574 in the BOM) while keeping GAMESETUP's already-verified
button/LCD/audio component choices and footprints untouched.

---

### Task 1: Fork the pcb/ directory into this repo

**Files:**
- Create: `hardware/pikocore_gamepad/pcb/` (copied from GAMESETUP)
- Create: `docs/hardware/pikocore_gamepad-pinout.md` (already exists from the
  superseded plan — this task updates it to match the fork's actual pin map, see
  Task 2)

- [x] **Step 1: Copy the pipeline, excluding generated/cache artifacts**

```bash
mkdir -p hardware/pikocore_gamepad/pcb
cp -r "C:/midigame/GAMESETUP/pcb/"* hardware/pikocore_gamepad/pcb/
cd hardware/pikocore_gamepad/pcb
rm -rf checks/__pycache__ __pycache__ tests/__pycache__ logs/*.log logs/*.json logs/*.rpt
rm -f a.kicad_prl chk.kicad_prl cy.kicad_prl g.kicad_prl m.kicad_prl m270.kicad_prl \
      m90.kicad_prl probe.kicad_prl r0.kicad_prl r180.kicad_prl r270.kicad_prl \
      r90.kicad_prl t.kicad_prl x.kicad_prl
rm -f gamesetup.dsn gamesetup.kicad_pcb gamesetup.net gamesetup.ses \
      gamesetup_template.dxf gamesetup_template_mod.dxf
```

The stray `.kicad_prl` files (`a.kicad_prl`, `chk.kicad_prl`, etc.) are leftover
per-session KiCad state from GAMESETUP's own work — not part of the pipeline, don't
carry them over. The `.kicad_pcb`/`.dsn`/`.net`/`.ses`/template DXFs are *generated*
by `gen_pcb.py`/`gen_template_dxf.py`/`route_io.py`/freerouting — this fork
regenerates its own once `gen_pcb.py` runs (out of scope for this plan, which stops
at the schematic).

- [x] **Step 2: Rename the KiCad project files**

```bash
mv gamesetup.kicad_pro pikocore_gamepad.kicad_pro
mv gamesetup.kicad_sch pikocore_gamepad.kicad_sch
mv gamesetup.kicad_sym pikocore_gamepad.kicad_sym
```

**Keep the `gamesetup_fp` / `gamesetup_lcsc` library nicknames as-is** in
`fp-lib-table`, `sym-lib-table`, and every `"FP": "gamesetup_fp:..."` /
`"gamesetup_lcsc:..."` string inside `netlist.py` — renaming them touches dozens of
lines for zero functional benefit (they're internal library identifiers, not
user-facing). Only the project's own root-sheet name needs to match the `.kicad_pro`
filename, which Step 2 just did.

- [x] **Step 3: Open the project once to confirm it loads**

Open `hardware/pikocore_gamepad/pcb/pikocore_gamepad.kicad_pro` in KiCad. Confirm the
schematic editor opens without complaining about a missing root sheet (KiCad expects
`<project>.kicad_sch` to exist, which Step 2 provided) and that both `gamesetup_fp`
and `gamesetup_lcsc` resolve in the library manager (they should, since `fp-lib-table`
paths are relative to the project directory, which moved as a unit). Close without
saving — no GUI edits happen in this plan.

- [x] **Step 4: Commit the raw fork before any adaptation**

```bash
cd ../../..
git add hardware/pikocore_gamepad/pcb
git commit -m "hw: fork GAMESETUP's kicad pipeline as pikocore_gamepad starting point"
```

Committing before Task 2's edits keeps a clean "this is exactly GAMESETUP, renamed"
checkpoint to diff against later.

---

### Task 2: Rewrite `pinmap.py` for pikocore_gamepad's 12-button, no-MIDI, no-SD layout

**Files:**
- Modify: `hardware/pikocore_gamepad/pcb/pinmap.py`
- Modify: `docs/hardware/pikocore_gamepad-pinout.md`

- [x] **Step 1: Replace the GPIO assignment table**

In `hardware/pikocore_gamepad/pcb/pinmap.py`, replace the `GPIO = {...}` dict and the
`FREE = (...)` tuple with:

```python
GPIO = {
    0:  "DPAD_UP",
    1:  "DPAD_DOWN",
    2:  "LCD_SCK",     # SPI0 SCK
    3:  "LCD_MOSI",    # SPI0 TX
    4:  "DPAD_LEFT",
    5:  "LCD_DC",
    6:  "LCD_RES",
    7:  "LCD_BLK",     # PWM de backlight
    8:  "I2S_DIN",     # PIO
    9:  "DPAD_RIGHT",
    10: "BTN_X",
    11: "BTN_Y",
    12: "BTN_A",
    13: "BTN_B",
    14: "BTN_START",
    15: "BTN_SELECT",
    16: "I2S_BCK",     # PIO
    17: "I2S_LRCK",    # PIO — DEBE ser BCK+1
    18: "BTN_L",
    19: "BTN_R",
    20: "SPK_SHDN",    # salida: 1 = parlante encendido
    21: "JACK_DET",    # entrada con pull-up: 0 = plug insertado
    22: "DAC_XSMT",    # pulldown 100k: arranca muteado
}

# Sin MIDI, sin microSD, sin expansores I2C: no queda nada que enrutar por
# expansion salvo estos 3, con ADC.
FREE = (26, 27, 28)
```

This drops `MIDI_TX`/`MIDI_RX`/`PCF_INT`/`SD_SCK`/`SD_MOSI`/`SD_MISO`/`SD_CS`/
`I2C_SDA`/`I2C_SCL` entirely and moves the 12 button functions onto the GPIOs those
freed up. `LCD_SCK`/`LCD_MOSI`/`LCD_DC`/`LCD_RES`/`LCD_BLK`/`I2S_BCK`/`I2S_LRCK`/
`I2S_DIN`/`SPK_SHDN`/`JACK_DET`/`DAC_XSMT` keep the **exact same GPIO numbers**
GAMESETUP already verified — only the button pins are new assignments.

Every button net name (`DPAD_UP`, `DPAD_DOWN`, `DPAD_LEFT`, `DPAD_RIGHT`, `BTN_X`,
`BTN_Y`, `BTN_A`, `BTN_B`, `BTN_START`, `BTN_SELECT`, `BTN_L`, `BTN_R`) matches what
`netlist.py`'s `TACTS` list and the `SW9`/`SW10` angled-trigger instances already
reference literally — Task 4 removes the PCF8574 detour those net names used to run
through, but the net names themselves don't change, so nothing else in `netlist.py`
needs touching for the button rewiring to take effect.

- [x] **Step 2: Verify the module docstring's pin-range claim still holds**

The file's module docstring already says "GP0-GP22 y GP26-GP28" are exposed and
GP23/24/25/29 are internal — that claim doesn't change with this fork (same
physical module), so leave it as-is.

- [x] **Step 3: Update the pinout reference doc**

Replace the pin table in `docs/hardware/pikocore_gamepad-pinout.md` (written for the
superseded manual-GUI plan) with the table below, and add a note pointing at the
fork:

```markdown
# pikocore_gamepad — GPIO Pin Map

Source of truth: `hardware/pikocore_gamepad/pcb/pinmap.py` (forked from
`C:\midigame\GAMESETUP\pcb\pinmap.py` — see
`docs/superpowers/plans/2026-08-11-pikocore-gamepad-pcb-fork.md`). Any change to a
net name or GPIO assignment must be made in `pinmap.py` first — `checks/run_all.py`'s
G-2/G-4 gates catch drift between it, the schematic, and the firmware config.h stub.

| GPIO | Net name | Function |
|---|---|---|
| GP0 | `DPAD_UP` | D-pad up |
| GP1 | `DPAD_DOWN` | D-pad down |
| GP2 | `LCD_SCK` | Display SPI clock (SPI0 SCK) |
| GP3 | `LCD_MOSI` | Display SPI data (SPI0 TX) |
| GP4 | `DPAD_LEFT` | D-pad left |
| GP5 | `LCD_DC` | Display data/command select |
| GP6 | `LCD_RES` | Display reset |
| GP7 | `LCD_BLK` | Display backlight (PWM) |
| GP8 | `I2S_DIN` | PCM5102A data in (PIO) |
| GP9 | `DPAD_RIGHT` | D-pad right |
| GP10 | `BTN_X` | Face button X |
| GP11 | `BTN_Y` | Face button Y |
| GP12 | `BTN_A` | Face button A |
| GP13 | `BTN_B` | Face button B |
| GP14 | `BTN_START` | Start button |
| GP15 | `BTN_SELECT` | Select button |
| GP16 | `I2S_BCK` | PCM5102A bit clock (PIO) |
| GP17 | `I2S_LRCK` | PCM5102A word select (PIO, must be BCK+1) |
| GP18 | `BTN_L` | Left shoulder (angled tact) |
| GP19 | `BTN_R` | Right shoulder (angled tact) |
| GP20 | `SPK_SHDN` | Speaker amp shutdown (1 = speaker on) |
| GP21 | `JACK_DET` | Headphone jack detect (0 = plug inserted, needs pull-up) |
| GP22 | `DAC_XSMT` | DAC mute control (starts muted via 100k pulldown) |
| GP26, GP27, GP28 | — | Reserved, unconnected (battery voltage sense candidate) |
| GP23, GP24, GP25, GP29 | — | Not broken out (module-internal: MP28164 mode, VBUS sense, onboard LED, VSYS monitor) |

Unlike the original from-scratch pin map this superseded, buttons are **not**
wired switch-to-GPIO-to-GND with internal pull-ups — GAMESETUP's `SW_Push`/
`SW_Push_RA` tact footprints wire straight into these GPIO nets and the firmware
still needs `gpio_pull_up()` on each, same mechanism, just inherited from the forked
schematic instead of designed fresh.
```

- [x] **Step 4: Commit**

```bash
git add hardware/pikocore_gamepad/pcb/pinmap.py docs/hardware/pikocore_gamepad-pinout.md
git commit -m "hw: pikocore_gamepad pin map — 12 direct-GPIO buttons, no MIDI/SD/I2C"
```

---

### Task 3: Remove MIDI and microSD from `netlist.py`

**Files:**
- Modify: `hardware/pikocore_gamepad/pcb/netlist.py`

- [x] **Step 1: Delete the MIDI/microSD symbol definitions**

In the `SYMS = {...}` dict, delete these three entries entirely (each is a
`"NAME": dict(...)` block ending in `),`): `"H11L1"`, `"JACK_TRS"`, `"MICROSD"`.

- [x] **Step 2: Delete the MIDI/microSD instances block**

Delete the entire section starting at the comment
`# ============================================================ MIDI y microSD`
through the end of that `INSTANCES += [ ... ]` block (it ends with the microSD
decoupling capacitor `C31` and the closing `]`). This removes R18–R24, D1, `J2`,
`J3`, `U6`, `J6`, and C29–C31 in one deletion — the whole block is self-contained
between that comment and the next top-level statement.

- [x] **Step 3: Delete the MIDI/microSD footprint constants**

Delete these two lines (just above the block deleted in Step 2):

```python
TRS_FP = "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"
SD_FP = "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical"
```

and the `FOOTPRINTS_PROVISIONALES.update({...})` call that follows them (the one
adding `"TRS_FP"` and `"SD_FP"` entries).

- [x] **Step 4: Delete the `OPTO_FP` constant and its provisional-footprint entry**

Delete the line `OPTO_FP = "Package_SO:SO-6_4.4x3.6mm_P1.27mm"` and the
`"OPTO_FP": "el H11L1 que se eligio..."` entry inside `FOOTPRINTS_PROVISIONALES`.

- [x] **Step 5: Update `PINOUT_SIN_VERIFICAR`**

Change:

```python
PINOUT_SIN_VERIFICAR = ("TPS61023", "H11L1", "JACK_AUDIO", "JACK_TRS", "MICROSD")
```

to:

```python
PINOUT_SIN_VERIFICAR = ("TPS61023", "JACK_AUDIO")
```

`H11L1`, `JACK_TRS`, and `MICROSD` are gone; `TPS61023` and `JACK_AUDIO` are still
genuinely unverified for pikocore_gamepad the same way they were for GAMESETUP (see
Task 6).

- [x] **Step 6: Commit**

```bash
git add hardware/pikocore_gamepad/pcb/netlist.py
git commit -m "hw: remove MIDI I/O and microSD from pikocore_gamepad netlist"
```

---

### Task 4: Remove nav switches and PCF8574 expanders, wire buttons direct

**Files:**
- Modify: `hardware/pikocore_gamepad/pcb/netlist.py`

- [x] **Step 1: Delete the `PCF8574` and `NAV_WS1004` symbol definitions**

In `SYMS = {...}`, delete the `"PCF8574"` and `"NAV_WS1004"` entries.

- [x] **Step 2: Delete the PCF8574 support code**

Delete, as one contiguous removal: the `PCF_MAP = {...}` dict, the comment above it,
the `PCF_ADDR_BITS = {...}` line, the comment block about "Los expansores arrancan en
U10...", the `_pcf_instances()` function definition, and the
`PCF_P_PINS = ["4", "5", "6", "7", "9", "10", "11", "12"]` constant (defined earlier,
just above `_mcu_nets()`).

- [x] **Step 3: Delete the PCF8574 pull-up/decouple instances and the expander
  instantiation call**

Delete the line `INSTANCES += _pcf_instances()` and the entire following
`INSTANCES += [...]` block (its comment header is
`# Pull-ups del bus...` through the `TP2` testpoint line) — this removes R1–R3,
C1–C3, TP1, TP2.

- [x] **Step 4: Delete the nav switch instances**

Delete the `# ------------------------------------------------------------ nav switches`
block: the `INSTANCES += [...]` containing `SW13` (`NAV1`) and `SW14` (`NAV2`).

- [x] **Step 5: Delete the expansion header instance**

In the `# --------------------------------------------------- alimentacion y EXP`
block, delete just the `("Conn_01x09", "J7", "EXP", ...)` tuple — **keep** the
`("SK12D07", "SW15", "PWR", ...)` power-switch tuple right above it, that one stays.

- [x] **Step 6: Delete the `PCF_FP`, `NAV_FP`, and `TP_FP` constants**

Delete:

```python
NAV_FP = "gamesetup_lcsc:SW-TH_WS-1004-ARL10026"
PCF_FP = "Package_SO:TSSOP-16_4.4x5mm_P0.65mm"
TP_FP = "TestPoint:TestPoint_Pad_D1.5mm"
```

(`BTN_FP`, `BTN_RA_FP`, `R_FP`, `C_FP` stay — the 12 tacts and their footprint
constants are unaffected by this task.)

- [x] **Step 7: Confirm the `TACTS` list needs no changes**

Re-read the `TACTS` list and the `SW9`/`SW10` angled-trigger instances: they already
reference `DPAD_UP`, `DPAD_DOWN`, `DPAD_LEFT`, `DPAD_RIGHT`, `BTN_X`, `BTN_Y`,
`BTN_A`, `BTN_B`, `BTN_START`, `BTN_SELECT`, `BTN_L`, `BTN_R` as net names — the same
names Task 2 just gave direct GPIO pins in `pinmap.py`. **No edit needed here**; the
switches now land on the RP2350-Plus's GPIO automatically once `_mcu_nets()` (which
Task 2 didn't touch) re-derives the socket's pin↔net map from the updated
`pinmap.GPIO`.

- [x] **Step 8: Commit**

```bash
git add hardware/pikocore_gamepad/pcb/netlist.py
git commit -m "hw: remove nav switches and PCF8574 expanders, buttons go direct to GPIO"
```

---

### Task 5: Prune `placements.py` to match the removed components

**Files:**
- Modify: `hardware/pikocore_gamepad/pcb/placements.py`

- [x] **Step 1: Delete placement rows for every removed reference**

In the `PLACEMENTS = [...]` list, delete the rows for: `U10`, `U11`, `U12` (PCF8574
expanders), `TP1`, `TP2` (testpoints), `U6` (H11L1 opto), `J6` (microSD stand-in
header), `J7` (expansion header), `J2`, `J3` (MIDI TRS jacks), `SW13`, `SW14` (nav
switches).

**Keep every other row** — `J4` (LCD), `SW1`–`SW12` (all 12 tacts, including the
angled `SW9`/`SW10`), `SW15` (power slide switch), `U1` (RP2350-Plus socket), `U2`
(boost), `U5` (PCM5102A), `U3` (op-amp), `U4` (PAM8302A), `J1` (phones jack), `J5`
(speaker JST).

- [x] **Step 2: Leave `FREE_REGIONS` untouched for now**

`placements.py`'s own docstring says positions are provisional and get rewritten by
`parse_dxf.py` once someone lays the board out in Rhino — removing 10 components
changes what's free, but recomputing that by hand now would just be discarded at the
next Rhino cycle. Note it as a known stale spot, don't fix it in this task.

- [x] **Step 3: Commit**

```bash
git add hardware/pikocore_gamepad/pcb/placements.py
git commit -m "hw: prune placements for removed MIDI/SD/nav/expander components"
```

---

### Task 6: Firmware pin-map stub for the G-4 gate

**Files:**
- Create: `hardware/pikocore_gamepad/pcb/firmware_pin_stub/config.h`
- Modify: `hardware/pikocore_gamepad/pcb/checks/check_pinmap.py`

pikocore_gamepad's firmware repin (wiring these GPIOs into actual pikocore C++ driver
code) is out of scope for this plan — same boundary the hardware spec already drew.
But `checks/check_pinmap.py` (gate G-4) needs *some* `config.h` with matching
`#define PIN_*` lines to diff against, or the check pipeline can't run end-to-end.
This task creates a **stub that only the check reads** — it isn't wired into any
CMake build.

- [x] **Step 1: Generate the stub's `#define` lines from `pinmap.py`**

Create `hardware/pikocore_gamepad/pcb/firmware_pin_stub/config.h`:

```c
#pragma once

// ============================================================
// pikocore_gamepad — firmware pin-map STUB, not a real board config.
//
// Exists only so checks/check_pinmap.py (gate G-4) has something to diff
// pinmap.py against. NOT included by any CMake target. When the real
// firmware repin happens (separate plan, per the hardware design spec's
// "out of scope" section), replace every reference to this file in
// check_pinmap.py with the real board config header and delete this stub.
//
// Source of truth: hardware/pikocore_gamepad/pcb/pinmap.py
// ============================================================

#define PIN_DPAD_UP      0
#define PIN_DPAD_DOWN    1
#define PIN_LCD_SCK      2
#define PIN_LCD_MOSI     3
#define PIN_DPAD_LEFT    4
#define PIN_LCD_DC       5
#define PIN_LCD_RES      6
#define PIN_LCD_BLK      7
#define PIN_I2S_DIN      8
#define PIN_DPAD_RIGHT   9
#define PIN_BTN_X        10
#define PIN_BTN_Y        11
#define PIN_BTN_A        12
#define PIN_BTN_B        13
#define PIN_BTN_START    14
#define PIN_BTN_SELECT   15
#define PIN_I2S_BCK      16
#define PIN_I2S_LRCK     17
#define PIN_BTN_L        18
#define PIN_BTN_R        19
#define PIN_SPK_SHDN     20
#define PIN_JACK_DET     21
#define PIN_DAC_XSMT     22
```

Every line here must equal a `pinmap.GPIO` entry from Task 2 — that's exactly what
Step 3 verifies.

- [x] **Step 2: Point `check_pinmap.py` at the stub**

In `hardware/pikocore_gamepad/pcb/checks/check_pinmap.py`, change:

```python
CONFIG_H = os.path.join(PCB, "..", "boards", "rp2350plus_v2", "config.h")
```

to:

```python
CONFIG_H = os.path.join(PCB, "firmware_pin_stub", "config.h")
```

(GAMESETUP's `boards/rp2350plus_v2/config.h` lives in the `GAMESETUP` repo, which
this fork does not have — and pikocore_gamepad's real firmware config doesn't exist
yet, hence the stub.)

- [x] **Step 3: Run the check**

```bash
cd hardware/pikocore_gamepad/pcb
python checks/check_pinmap.py
```

Expected: `OK: 23 pines coinciden entre PCB y firmware.` (23 = the number of entries
in `pinmap.GPIO` after Task 2's rewrite). If it reports a mismatch, the stub's
`#define` values and `pinmap.py`'s `GPIO` dict have drifted — fix whichever one is
wrong before continuing.

- [x] **Step 4: Commit**

```bash
git add hardware/pikocore_gamepad/pcb/firmware_pin_stub hardware/pikocore_gamepad/pcb/checks/check_pinmap.py
git commit -m "hw: firmware pin-map stub so G-4 gate has something to check against"
```

---

### Task 7: Run the full check pipeline and ERC

**Files:**
- Modify: none (verification only)
- Create: `hardware/pikocore_gamepad/pcb/logs/erc.log` (generated, committed as
  evidence)

- [x] **Step 1: Regenerate the schematic from the edited netlist**

```bash
cd hardware/pikocore_gamepad/pcb
"$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" gen_sch.py
```

Expected: it overwrites `pikocore_gamepad.kicad_sch` and exits 0. If it errors on an
undefined symbol or net, one of Tasks 3–5's deletions left a dangling reference —
search `netlist.py` for the deleted ref/symbol name and remove what Step 1 missed.

- [x] **Step 2: Run the Python check gates**

```bash
"$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" checks/run_all.py
```

Expected: `TODAS LAS PUERTAS PASAN.` — G-0 will likely still report the same
pre-existing provisional items GAMESETUP's own `PARTES.md`/`PENDIENTES.md` documented
(`TPS61023` and `JACK_AUDIO` pinouts unverified, `BOOST_L`/`BOOST_RFB_TOP`/
`BOOST_RFB_BOT` provisional, `BTN_FP`/`BTN_RA_FP`/`OPAMP_FP`/`JACK_FP` provisional
footprints, `LCD_PIN_ROW_Y`/`LCD_HOLE_INSET` unmeasured) — **that's expected and not
a regression**, this plan doesn't resolve GAMESETUP's own open part-sourcing
questions, it only removes subsystems pikocore_gamepad doesn't need. G-4 (pinmap) and
G-5 (duplicate refs) should show **0** issues from this fork's changes specifically.

- [x] **Step 3: Run ERC**

```bash
"$LOCALAPPDATA/Programs/KiCad/9.0/bin/kicad-cli.exe" sch erc \
  --output logs/erc.log pikocore_gamepad.kicad_sch
```

Expected: 0 errors. Warnings about the 3 reserved-free GPIO (GP26–28) being
unconnected are fine (matches the intentional "reserved" entries in the pin map doc)
— every other warning must be resolved before moving on to layout.

- [x] **Step 4: Commit the logs as evidence**

```bash
git add hardware/pikocore_gamepad/pcb/logs/erc.log
git commit -m "hw: pikocore_gamepad schematic — checks green, ERC clean"
```

---

## Execution notes (added after running the plan, 2026-08-11)

All 7 tasks executed via subagent-driven-development, each with a spec-compliance
review and a code-quality review; every task needed at least one fix-and-re-review
round. Final state: 174 tests passing, `checks/run_all.py` shows only gate G-0
failing (GAMESETUP's own pre-existing provisional part/constant list — audio jack,
tact switch, boost inductor values, LCD measurements — not something this fork
introduced or was scoped to resolve), and `kicad-cli sch erc` reports 0 errors with
exactly the 3 expected `EXP_GP26`/`27`/`28` dangling-label warnings.

**One fix went beyond Task 7's literal file list** (which said "Modify: none —
verification only"): running ERC for the first time surfaced that `sym-lib-table`
still registered the project's own symbol library under the nickname `"gamesetup"`,
while `gen_sch.py`'s `PROJECT = "pikocore_gamepad"` constant (set in a Task 1
follow-up fix) emits every schematic symbol's `lib_id` with a `"pikocore_gamepad:"`
prefix — a nickname that didn't exist, producing 62 spurious `lib_symbol_issues`
warnings. Fixed by renaming the `sym-lib-table` nickname to match (not the `uri`,
already correct; the unrelated `gamesetup_fp`/`gamesetup_lcsc` footprint-library
nicknames were left untouched, per Task 1's original instruction to preserve those).
Re-verified: ERC dropped from 65 to 3 warnings, test suite and G-4 pinmap check both
still green. Commit `68d27b5`.

Also committed as part of Task 7, beyond the plan's original "verification only"
framing: the regenerated `pikocore_gamepad.kicad_sch`/`.kicad_sym`/`.kicad_pcb`/
`.net` files themselves (not gitignored; matches GAMESETUP's own convention of
tracking these). The `.kicad_pcb` is placement-only — 0 tracks, 0 vias — consistent
with PCB routing being explicitly out of scope for this plan.

Branch: `pikocore-gamepad-hardware`. Ready for the out-of-scope items below.

## Out of scope (tracked for future plans, not this one)

- PCB copper layout and routing (`gen_pcb.py`/`route_io.py`/freerouting cycle) —
  GAMESETUP's own `PENDIENTES.md` §5 documents that workflow; pikocore_gamepad
  follows the same steps once its own board outline exists
- Resolving GAMESETUP's inherited open part-sourcing items (audio jack LCSC part,
  tact switch LCSC part, boost inductor/feedback resistor values, LCD physical
  measurements) — these block *GAMESETUP's* fabrication gate G-0 and now also
  pikocore_gamepad's, since the fork inherited them unresolved
- 3D-printed enclosure model
- Real firmware repin — replacing the Task 6 stub with an actual pikocore C++ board
  config wired into this repo's CMake build
- Bill-of-materials purchase order with confirmed LCSC/vendor part numbers
