#pragma once
// ============================================================
// pikocore_gamepad PCB -- pin map. Same GP0-22/GP26 functions on the
// RP2350-Plus module build (main) and on the RP2350A chip-down build
// (branch hw/chipdown-rp2350, which adds BB_PS/VBUS_SENSE/VSYS_ADC below).
//
// Source of truth: hardware/pikocore_gamepad/pcb/pinmap.py. Gate G-4
// (hardware/pikocore_gamepad/pcb/checks/check_pinmap.py) parses the
// "#define PIN_* <gpio>" lines of THIS file and diffs them against pinmap.py
// in both directions, so:
//   - every PCB function must appear here as PIN_<FUNC> with the same GPIO;
//   - nothing else may be named PIN_* (the checker flags it as a pin the
//     PCB does not know about).
// Firmware-only choices (which slice ticks the audio engine, the module's
// onboard LED, the unconnected pins reused as clock-in/trigger-out stubs)
// live in src/hw_gamepi13.h under PIKO_GAMEPAD, not here.
// ============================================================

#define PIN_DPAD_UP      0
#define PIN_DPAD_DOWN    1
#define PIN_LCD_SCK      2   // SPI0 SCK
#define PIN_LCD_MOSI     3   // SPI0 TX
#define PIN_DPAD_LEFT    4
#define PIN_LCD_DC       5
#define PIN_LCD_RES      6
#define PIN_LCD_BLK      7   // backlight, PWM (slice 3)
#define PIN_I2S_DIN      8   // PIO
#define PIN_DPAD_RIGHT   9
#define PIN_BTN_X        10
#define PIN_BTN_Y        11
#define PIN_BTN_A        12
#define PIN_BTN_B        13
#define PIN_BTN_START    14
#define PIN_BTN_SELECT   15
#define PIN_I2S_BCK      16  // PIO side-set
#define PIN_I2S_LRCK     17  // PIO side-set, MUST be BCK+1
#define PIN_BTN_L        18
#define PIN_BTN_R        19
#define PIN_SPK_SHDN     20  // out: 1 = PAM8302A on
#define PIN_JACK_DET     21  // in, pull-up: 0 = plug inserted
#define PIN_DAC_XSMT     22  // out: 100k pulldown on the PCB, boots muted
#define PIN_BB_PS        23  // out: TPS63001 PS/SYNC, 0 = power-save (10k pulldown), 1 = forced PWM
#define PIN_VBUS_SENSE   24  // in: 1 = USB present (100k/200k from VBUS)
#define PIN_LCD_TE       26  // panel tearing-effect out (input, optional, unused)
#define PIN_VSYS_ADC     29  // ADC3: VSYS / 3 (200k/100k), battery level
