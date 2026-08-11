# pikocore_gamepad PCB Schematic Implementation Plan

> **For agentic workers:** This plan is **GUI-execution**, not autonomous — KiCad
> schematic capture happens in the KiCad desktop app, which no agent (subagent or
> inline) can drive. Use **superpowers:executing-plans** in reviewer/checkpoint mode:
> the human does each KiCad GUI step, then pastes back the ERC report / netlist
> text output for Claude to check against this plan's expected values before moving
> to the next task. Do NOT attempt subagent-driven-development for the KiCad steps —
> there is nothing an agent can execute there. Steps that only touch text files
> (the pinout doc, `.kicad_sym` library files hand-edited as text) can be executed
> normally.

**Goal:** Produce a complete, ERC-clean KiCad schematic (not yet PCB layout) for the
`pikocore_gamepad` carrier board, wiring the RP2350-Plus to the display, buttons,
audio, and power subsystems defined in
[`docs/superpowers/specs/2026-08-11-pikocore-gamepad-hardware-design.md`](../specs/2026-08-11-pikocore-gamepad-hardware-design.md).

**Architecture:** A hierarchical KiCad project with one top sheet and five subsheets
(power, core, display, buttons, audio), connected by hierarchical labels on shared
nets (3V3, GND, and the signal buses). Custom symbols are hand-authored for the parts
with no standard KiCad library entry (RP2350-Plus, PCM5102A, PAM8403, the ST7789
module). PCB footprint assignment and copper layout are **out of scope** — this plan
stops at a schematic that passes ERC with a clean, documented netlist.

**Tech Stack:** KiCad 8.x (schematic editor + `kicad-cli` for ERC/netlist export),
plain text `.kicad_sym`/`.kicad_sch` files (S-expression format) committed to git.

---

## Scope note on pin assignments

The hardware spec fixed *which components* exist but not *which RP2350-Plus GPIO*
each one uses — that's a schematic-level decision this plan makes. The pin map below
is new and is recorded in `docs/hardware/pikocore_gamepad-pinout.md` (Task 1) as the
single source of truth for every later task and for the eventual firmware repin.

| GPIO | Net name | Function |
|---|---|---|
| GP0 | `I2C0_SDA` | Reserved for future expansion (e.g. IMU) |
| GP1 | `I2C0_SCL` | Reserved for future expansion |
| GP2 | `BTN_UP` | D-pad up |
| GP3 | `BTN_DOWN` | D-pad down |
| GP4 | `BTN_LEFT` | D-pad left |
| GP5 | `BTN_RIGHT` | D-pad right |
| GP6 | `BTN_Y` | Face button Y |
| GP7 | `BTN_X` | Face button X |
| GP8 | `BTN_B` | Face button B |
| GP9 | `BTN_A` | Face button A |
| GP10 | `I2S_BCK` | PCM5102A bit clock |
| GP11 | `I2S_LRCK` | PCM5102A word select (L/R clock) |
| GP12 | `I2S_DIN` | PCM5102A data in |
| GP13 | `BTN_SELECT` | Select button |
| GP14 | `BTN_START` | Start button |
| GP15 | `BTN_L` | Left shoulder button |
| GP16 | `BTN_R` | Right shoulder button |
| GP17 | `LCD_CS` | Display chip select (SPI0) |
| GP18 | `LCD_SCK` | Display SPI clock (SPI0 SCK) |
| GP19 | `LCD_MOSI` | Display SPI data (SPI0 TX) |
| GP20 | `LCD_DC` | Display data/command select |
| GP21 | `LCD_RST` | Display reset |
| GP22 | `LCD_BL` | Display backlight (PWM dimmable) |
| GP26 | `BATT_SENSE` | ADC0, battery voltage sense via divider (reserved, not built this pass) |
| GP27 | — | Reserved, unconnected |
| GP28 | — | Reserved, unconnected |
| GP23, GP24, GP25, GP29 | — | Not broken out for external use (SMPS mode, VBUS sense, onboard LED, VSYS monitor — internal to the RP2350-Plus module) |

All 12 buttons are wired **switch-to-GND only** — no external pull resistors. The
RP2350's GPIO pads have configurable internal pull-ups; firmware enables
`gpio_pull_up()` on each button pin (this matches the existing GamePi13 port's
approach, just repointed to new GPIOs).

**⚠️ Verification requirement carried into Task 2:** this pin map assumes the
RP2350-Plus follows the standard Raspberry Pi Pico 40-pin (2×20) physical pinout,
because Waveshare's product page states it is "compatible with Raspberry Pi Pico 2"
pinout and I could not reach the Waveshare wiki page directly (HTTP 403) to
screenshot the exact pin-by-pin silkscreen. **Before wiring any net in Task 4, hold
the physical board next to the pin table in Task 2 and confirm every GPIO label
against the board's silkscreen** — this is a hard blocker, not a formality.

---

### Task 1: Repo layout and pinout reference doc

**Files:**
- Create: `docs/hardware/pikocore_gamepad-pinout.md`
- Create: `hardware/pikocore_gamepad/` (empty dir, KiCad project lands here in Task 2)

- [ ] **Step 1: Create the hardware doc directory and pinout reference**

Create `docs/hardware/pikocore_gamepad-pinout.md` with exactly the pin table from
the "Scope note on pin assignments" section above (copy it verbatim), plus this
header:

```markdown
# pikocore_gamepad — GPIO Pin Map

Source of truth for the KiCad schematic (`hardware/pikocore_gamepad/`) and the
eventual firmware repin. Any change to a net name or GPIO assignment must be made
here first, then propagated to the schematic sheets that reference it.

See `docs/superpowers/plans/2026-08-11-pikocore-gamepad-pcb-schematic.md` for how
this map was derived.
```

- [ ] **Step 2: Create the hardware project directory**

```bash
mkdir -p hardware/pikocore_gamepad/sheets hardware/pikocore_gamepad/libs
```

- [ ] **Step 3: Commit**

```bash
git add docs/hardware/pikocore_gamepad-pinout.md hardware/pikocore_gamepad
git commit -m "docs: pikocore_gamepad GPIO pin map"
```

(If git refuses to add empty directories, add a placeholder `.gitkeep` file in each
of `hardware/pikocore_gamepad/sheets/` and `hardware/pikocore_gamepad/libs/` first.)

---

### Task 2: KiCad project + custom RP2350-Plus symbol

**Files:**
- Create: `hardware/pikocore_gamepad/pikocore_gamepad.kicad_pro`
- Create: `hardware/pikocore_gamepad/libs/pikocore_gamepad.kicad_sym`

- [ ] **Step 1: Create the KiCad project**

In the KiCad GUI: File → New Project → save as
`hardware/pikocore_gamepad/pikocore_gamepad.kicad_pro`. Decline the default schematic
it offers to create alongside the project for now (Task 3 creates the real one as a
hierarchical root).

- [ ] **Step 2: Physically verify the pin map against the board**

Take the RP2350-Plus board on hand. For each of the 26 GPIO pins referenced in
`docs/hardware/pikocore_gamepad-pinout.md`, confirm the silkscreen label matches.
Also locate and note the position of: `3V3(OUT)`, `3V3_EN`, `VSYS`, `VBUS`, `GND`
(multiple), `RUN`, `ADC_VREF` — these are needed for Task 3 (power sheet) even
though they aren't GPIOs.

If any label differs from the standard Pico 40-pin layout assumed above, **stop and
update `docs/hardware/pikocore_gamepad-pinout.md` first**, then continue.

- [ ] **Step 3: Create the custom symbol library**

In KiCad's Symbol Editor: File → New Library → save as
`hardware/pikocore_gamepad/libs/pikocore_gamepad.kicad_sym`. Add it to the project
(Preferences → Manage Symbol Libraries → add as project-local library, nickname
`pikocore_gamepad`).

- [ ] **Step 4: Draw the RP2350-Plus symbol**

Create a new symbol named `RP2350-Plus` in that library: a rectangle body, 20 pins
on the left edge and 20 pins on the right edge, 100 mil (0.1") spacing, matching the
physical THT pin order confirmed in Step 2. Label each pin with its net-relevant name
(`GP0`...`GP28` where applicable, `3V3`, `GND`, `VSYS`, `VBUS`, `RUN`, `3V3_EN`,
`ADC_VREF`) — use the standard Pico pin order unless Step 2 corrected it:

Left column (pins 1–20, top to bottom): GP0, GP1, GND, GP2, GP3, GP4, GP5, GND, GP6,
GP7, GP8, GP9, GND, GP10, GP11, GP12, GP13, GND, GP14, GP15.

Right column (pins 21–40, bottom to top): GP16, GP17, GND, GP18, GP19, GP20, GP21,
GND, GP22, RUN, GP26, GP27, GND, GP28, ADC_VREF, 3V3, 3V3_EN, GND, VSYS, VBUS.

- [ ] **Step 5: Save and verify the symbol loads**

Save the library. Close and reopen the Symbol Editor, confirm `RP2350-Plus` appears
under the `pikocore_gamepad` library with all 40 pins visible and none marked as
"no connect" by default (they should be plain bidirectional/passive pins — the ERC
in Task 9 will catch pin-type mismatches, not this step).

- [ ] **Step 6: Commit**

```bash
git add hardware/pikocore_gamepad/pikocore_gamepad.kicad_pro hardware/pikocore_gamepad/libs/pikocore_gamepad.kicad_sym
git commit -m "hw: kicad project + custom RP2350-Plus symbol"
```

---

### Task 3: Power sheet

**Files:**
- Create: `hardware/pikocore_gamepad/sheets/power.kicad_sch`

- [ ] **Step 1: Create the power subsheet**

In the KiCad Schematic Editor (open the project, it should prompt to create a root
sheet — name it `pikocore_gamepad.kicad_sch` per Task 8, come back to that then).
For now, create a blank sheet file at `hardware/pikocore_gamepad/sheets/power.kicad_sch`
via Sheet → New Sheet from the (temporary) root, sized A4.

- [ ] **Step 2: Place the battery connector**

Add a standard 2-pin JST connector symbol (KiCad library `Connector_JST:JST_ZH_S2B_ZR-SM4A-TF`
is the closest generic MX1.25-pitch 2-pin part — footprint assignment happens in the
PCB layout plan, not here). Label its two pins `BATT_POS` and `GND`.

- [ ] **Step 3: Place the power switch**

Add a generic SPDT slide switch (`Switch:SW_SPDT` from KiCad's standard `Switch`
library). Wire: `BATT_POS` → switch common → switch NO throw → net `VBATT_SW`. Leave
the NC throw unconnected (or route to a test point later — not required now).

- [ ] **Step 4: Wire to the RP2350-Plus battery header net**

Add a hierarchical label `VBATT_SW` and one for `GND`. These will connect in Task 8
to the RP2350-Plus's onboard MX1.25 battery header pads — note that the RP2350-Plus
module's own battery header is *on the module itself*, not something this carrier
board re-exposes as a separate connector unless you want the battery physically
routed through the carrier PCB. **Decision for this pass:** the battery plugs
directly into the RP2350-Plus module's onboard MX1.25 header; this sheet's job is
only the **series power switch inline between the battery and that header** — so the
JST connector in Step 2 is actually a **pass-through pair**: battery cable in on one
side, a short cable out to the RP2350-Plus module's MX1.25 header on the other, with
the SPDT switch cutting the positive leg in between. Adjust the sheet to reflect
this: `BATT_POS` (from battery) → switch → `VBATT_TO_MODULE` (to RP2350-Plus header),
`GND` passes straight through unswitched.

- [ ] **Step 5: Commit**

```bash
git add hardware/pikocore_gamepad/sheets/power.kicad_sch
git commit -m "hw: power sheet (battery inline switch)"
```

---

### Task 4: Core sheet (RP2350-Plus placement)

**Files:**
- Create: `hardware/pikocore_gamepad/sheets/core.kicad_sch`

- [ ] **Step 1: Create the core subsheet**

Same procedure as Task 3 Step 1, file `sheets/core.kicad_sch`.

- [ ] **Step 2: Place the RP2350-Plus symbol**

Drop one instance of the `pikocore_gamepad:RP2350-Plus` symbol from Task 2.

- [ ] **Step 3: Add hierarchical labels for every net in the pin map**

For each row of `docs/hardware/pikocore_gamepad-pinout.md`, wire that GPIO pin to a
hierarchical label with the exact net name from the table (`BTN_UP`, `I2S_BCK`,
`LCD_CS`, etc.). For `GP27` and `GP28` (reserved, unconnected), place a KiCad
"no connect" flag instead of a label — this tells ERC they're intentionally unused.

- [ ] **Step 4: Wire power pins**

Connect the symbol's `3V3`, `GND`, `VSYS` pins to hierarchical labels `3V3`, `GND`,
`VBATT_TO_MODULE` respectively (the last one bridges to the power sheet's output —
name must match exactly what Task 3 Step 4 produced).

- [ ] **Step 5: Commit**

```bash
git add hardware/pikocore_gamepad/sheets/core.kicad_sch
git commit -m "hw: core sheet (RP2350-Plus pin-out to hierarchical labels)"
```

---

### Task 5: Display sheet

**Files:**
- Create: `hardware/pikocore_gamepad/sheets/display.kicad_sch`

- [ ] **Step 1: Create the display subsheet**

File `sheets/display.kicad_sch`.

- [ ] **Step 2: Create a custom ST7789 module symbol**

In the same `pikocore_gamepad.kicad_sym` library from Task 2, add a symbol named
`ST7789_1.3in` with 8 pins: `GND`, `VCC`, `SCL` (clock in), `SDA` (MOSI in), `RES`
(reset), `DC`, `CS`, `BLK` (backlight). This is the standard pinout for the common
1.3" ST7789 SPI breakout — confirm it matches the physical module once purchased
(Task 9's ERC won't catch a wrong pin order on a part you haven't bought yet; flag
this as a re-verification item when the LCD module physically arrives, before PCB
layout).

- [ ] **Step 3: Wire the display**

Place the `ST7789_1.3in` symbol. Connect: `SCL`→hierarchical label `LCD_SCK`,
`SDA`→`LCD_MOSI`, `RES`→`LCD_RST`, `DC`→`LCD_DC`, `CS`→`LCD_CS`, `BLK`→`LCD_BL`,
`VCC`→`3V3`, `GND`→`GND`.

- [ ] **Step 4: Commit**

```bash
git add hardware/pikocore_gamepad/sheets/display.kicad_sch hardware/pikocore_gamepad/libs/pikocore_gamepad.kicad_sym
git commit -m "hw: display sheet (ST7789 SPI wiring)"
```

---

### Task 6: Buttons sheet

**Files:**
- Create: `hardware/pikocore_gamepad/sheets/buttons.kicad_sch`

- [ ] **Step 1: Create the buttons subsheet**

File `sheets/buttons.kicad_sch`.

- [ ] **Step 2: Place 12 switch symbols**

Use KiCad's standard `Switch:SW_Push` for all 12: D-pad Up/Down/Left/Right, Y/X/B/A,
Select, Start, L, R.

- [ ] **Step 3: Wire each switch**

Each switch has one pin to a hierarchical label matching its net name from the pin
map (`BTN_UP`, `BTN_DOWN`, `BTN_LEFT`, `BTN_RIGHT`, `BTN_Y`, `BTN_X`, `BTN_B`, `BTN_A`,
`BTN_SELECT`, `BTN_START`, `BTN_L`, `BTN_R`) and the other pin to `GND`. No pull
resistors — internal RP2350 pull-ups handle this (see the pin-map note above).

- [ ] **Step 4: Commit**

```bash
git add hardware/pikocore_gamepad/sheets/buttons.kicad_sch
git commit -m "hw: buttons sheet (12 switches to GND, internal pull-ups)"
```

---

### Task 7: Audio sheet

**Files:**
- Create: `hardware/pikocore_gamepad/sheets/audio.kicad_sch`

- [ ] **Step 1: Create the audio subsheet**

File `sheets/audio.kicad_sch`.

- [ ] **Step 2: Create custom PCM5102A and PAM8403 symbols**

In `pikocore_gamepad.kicad_sym`:
- `PCM5102A`: pins `VCC`, `GND`, `BCK`, `LRCK`, `DIN`, `SCK` (tie to GND per datasheet
  to use internal PLL — no external MCLK from the RP2350-Plus needed), `OUTL`, `OUTR`.
- `PAM8403`: pins `VCC`, `GND`, `INL`, `INR`, `OUTL+`, `OUTL-`, `OUTR+`, `OUTR-`,
  `SHUTDOWN` (tie to `VCC` through the module's own onboard pull, if using a
  breakout — flag for re-check once the specific breakout is purchased, since
  breakout modules often already tie this internally).

- [ ] **Step 3: Wire the DAC**

`PCM5102A.BCK`→`I2S_BCK`, `.LRCK`→`I2S_LRCK`, `.DIN`→`I2S_DIN`, `.SCK`→`GND`,
`.VCC`→`3V3`, `.GND`→`GND`.

- [ ] **Step 4: Wire the amp and speaker**

`PCM5102A.OUTL`→`PAM8403.INL`, `.OUTR`→`PAM8403.INR` (both channels feed the amp even
though the spec calls for a single mono speaker — Step 5 sums them at the speaker).
`PAM8403.VCC`→`3V3`, `.GND`→`GND`.

Since the spec calls for **one mono speaker** fed by a stereo amp: connect
`PAM8403.OUTL+` and `PAM8403.OUTR+` together to the speaker's `+` terminal through
two isolating resistors (100Ω each, standard practice for summing two class-D
outputs) rather than wiring them directly together — direct-tying two live class-D
outputs together can damage the amp. Add two `R` symbols (`R_SUM_L`, `R_SUM_R`,
100Ω) between each `OUT+` and the speaker's shared `+` node. Tie `OUTL-`/`OUTR-` to
the speaker's `-` terminal the same way through two more 100Ω resistors.

- [ ] **Step 5: Place the speaker and headphone jack**

Add a generic 2-pin `Speaker` symbol (KiCad `Device:Speaker`), wired per Step 4.

Add a 3.5mm TRS jack with switch contact — KiCad standard library has
`Connector_Audio:Jack_3.5mm_WQP-PJ320` (or similar NC-switch variant; pick whichever
`Connector_Audio` symbol explicitly has a switch pin in its symbol, since not all do).
Wire: jack `L` and `R` to `PAM8403.OUTL+`/`OUTR+` directly (ahead of the summing
resistors — headphones get true stereo, only the mono speaker path is summed), jack
`GND` to `GND`, and the jack's switch pin in series with the speaker's `+` connection
so inserting a plug opens that path and silences the speaker.

- [ ] **Step 6: Commit**

```bash
git add hardware/pikocore_gamepad/sheets/audio.kicad_sch hardware/pikocore_gamepad/libs/pikocore_gamepad.kicad_sym
git commit -m "hw: audio sheet (PCM5102A DAC, PAM8403 amp, mono speaker + stereo jack)"
```

---

### Task 8: Top-level hierarchical sheet

**Files:**
- Create: `hardware/pikocore_gamepad/pikocore_gamepad.kicad_sch`

- [ ] **Step 1: Create the root sheet**

If KiCad auto-created a root `.kicad_sch` in Task 3 Step 1, rename/move it to
`hardware/pikocore_gamepad/pikocore_gamepad.kicad_sch` now (matching the project
file name, which KiCad expects for the root sheet).

- [ ] **Step 2: Place the five hierarchical sheet symbols**

Sheet → New Sheet (existing file) for each of: `sheets/power.kicad_sch`,
`sheets/core.kicad_sch`, `sheets/display.kicad_sch`, `sheets/buttons.kicad_sch`,
`sheets/audio.kicad_sch`.

- [ ] **Step 3: Add matching hierarchical pins on each sheet symbol**

For every hierarchical label used inside a subsheet (e.g. `BTN_UP` inside
`buttons.kicad_sch`), KiCad requires a matching sheet pin on that sheet's symbol at
the top level for the net to actually connect across sheets. Add sheet pins for
every net listed in the pin map plus `3V3`, `GND`, `VBATT_TO_MODULE`.

- [ ] **Step 4: Wire the sheet pins together at the top level**

Connect same-named sheet pins across sheets with a top-level wire or a top-level
hierarchical label (e.g. `core.kicad_sch`'s `BTN_UP` pin to `buttons.kicad_sch`'s
`BTN_UP` pin; `power.kicad_sch`'s `VBATT_TO_MODULE` to `core.kicad_sch`'s
`VBATT_TO_MODULE`). `3V3` and `GND` are shared across all five sheets.

- [ ] **Step 5: Commit**

```bash
git add hardware/pikocore_gamepad/pikocore_gamepad.kicad_sch
git commit -m "hw: top-level hierarchical sheet, wire all subsheets together"
```

---

### Task 9: ERC, netlist export, and pin-map cross-check

**Files:**
- Modify: none (verification only)
- Create: `hardware/pikocore_gamepad/erc_report.txt` (generated, committed as evidence)

- [ ] **Step 1: Run Electrical Rules Check**

In KiCad Schematic Editor: Inspect → Electrical Rules Checker → Run. Save the report
as `hardware/pikocore_gamepad/erc_report.txt`.

Expected: **0 errors.** Warnings are acceptable only for: unconnected `GP27`/`GP28`
(intentional, no-connect flagged in Task 4), and the `PAM8403.SHUTDOWN` pin if left
genuinely undecided pending the specific breakout part (flagged in Task 7 Step 2) —
every other warning must be resolved before moving on.

- [ ] **Step 2: Export the netlist**

File → Export → Netlist (KiCad format), save as
`hardware/pikocore_gamepad/pikocore_gamepad.net` (not committed — regenerable, add
to `.gitignore` if one doesn't already cover it).

- [ ] **Step 3: Cross-check every net against the pin map doc**

Open the exported netlist and, for each row in
`docs/hardware/pikocore_gamepad-pinout.md`, confirm the net name appears connecting
exactly the RP2350-Plus pin and its intended peripheral pin (e.g. `LCD_SCK` connects
`RP2350-Plus` pin `GP18` and `ST7789_1.3in` pin `SCL`, nothing else). Any mismatch
means a wiring mistake in Tasks 4–7 — go back and fix the offending sheet.

- [ ] **Step 4: Commit the ERC report as evidence**

```bash
git add hardware/pikocore_gamepad/erc_report.txt
git commit -m "hw: ERC clean pass, netlist cross-checked against pin map"
```

---

## Out of scope (tracked for future plans, not this one)

- PCB footprint assignment and copper layout (2-layer routing, board outline,
  mounting holes) — separate plan once this schematic is ERC-clean
- 3D-printed enclosure model
- Firmware repin (buttons + PWM→I2S audio driver) to the GPIOs fixed in
  `docs/hardware/pikocore_gamepad-pinout.md`
- Bill-of-materials purchase order (part numbers, vendor, cost) — the spec lists
  component *types*; exact purchasable SKUs get pinned down once footprints are
  needed for layout
