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
