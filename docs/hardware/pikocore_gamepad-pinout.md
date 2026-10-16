# pikocore_gamepad — GPIO Pin Map

Source of truth: `hardware/pikocore_gamepad/pcb/pinmap.py` (forked from
`C:\midigame\GAMESETUP\pcb\pinmap.py` — see
`docs/superpowers/plans/2026-08-11-pikocore-gamepad-pcb-fork.md`). Any change to a
net name or GPIO assignment must be made in `pinmap.py` first — `checks/run_all.py`'s
G-2/G-4 gates catch drift between it, the schematic, and the firmware board config.

Firmware side: [`src/boards/pikocore_gamepad/config.h`](../../src/boards/pikocore_gamepad/config.h)
holds one `#define PIN_<NET> <gpio>` per row of the table below and nothing else named
`PIN_*` — that file is what gate G-4 (`checks/check_pinmap.py`) diffs against `pinmap.py`.
`src/hw_gamepi13.h` maps those onto the names the shared GamePi13 input/UI layer uses
when built with `-DPIKO_GAMEPAD=ON` (see `hardware/pikocore_gamepad/README.md`).

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
| GP26 | `LCD_TE` | Panel tearing-effect output (input to the MCU, optional; firmware defines `PIN_LCD_TE` and does not use it yet). Was `BTN_OK` (NAV5 centre) until 2026-10-14, when the D-pad went back to four discrete 6×6 tacts (SW1–SW4): a single 5-way actuator cannot press two directions at once, which Up+Down+B+A and Down+Left+X+B need. |
| GP27, GP28 | — | Reserved, unconnected (battery voltage sense candidate). Firmware parks pikocore's clock-in (GP27, pull-up) and trigger-out (GP28) here so the stock engine code runs unchanged; wire a jack and they just work |
| GP23, GP24, GP25, GP29 | — | Not broken out (module-internal: MP28164 mode, VBUS sense, onboard LED, VSYS monitor). Firmware uses the GP25 onboard LED as the beat LED |

Display (since 2026-10-14): bare 1.3" panel DisplayModule DM-TFT13-377, 24-pin
0.5 mm FPC into J4 (XUNPU FPC-05FB-24PH20). 4-SPI with IM=1; CS is tied to GND
(always selected, as the old 7-pin module was), RD and DB0–DB7 to GND. Backlight:
2 white LEDs from VSYS through R21 (27 Ω) and Q1 (2N7002) switched by `LCD_BLK`.

The electrical topology is the same one the superseded from-scratch plan called for
— each button switches its GPIO net to GND, and firmware enables `gpio_pull_up()` on
every button pin. What's different is only *where that wiring comes from*: instead of
being designed fresh for this project, it's inherited as-is from GAMESETUP's already
laid-out `SW_Push`/`SW_Push_RA` tact footprints, which this fork's `netlist.py` reuses
unmodified — this pin map just tells `_mcu_nets()` which GPIO each of those already-wired
net names should land on.
