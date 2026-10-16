#pragma once
// ============================================================
// pikocore_gamepad carrier PCB (Waveshare RP2350-Plus module) -- pin map.
//
// Source of truth: hardware/pikocore_gamepad/pcb/pinmap.py. Gate G-4
// (hardware/pikocore_gamepad/pcb/checks/check_pinmap.py) parses the
// "#define PIN_* <gpio>" lines of THIS file and diffs them against pinmap.py
// in both directions, so:
//   - every PCB function must appear here as PIN_<FUNC> with the same GPIO;
//   - nothing else may be named PIN_* (the checker flags it as a pin the
//     PCB does not know about).
// Firmware-only choices (which slice ticks the audio engine, the module's
// onboard LED, the clock-in/trigger-out stubs, off now that GP27/GP28 are MIDI)
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
#define PIN_LCD_TE       26  // panel tearing-effect out (input, optional, unused)
#define PIN_MIDI_TX      28  // UART0 TX -> MIDI OUT jack
#define PIN_MIDI_RX      27  // from the MIDI IN optocoupler; read by a PIO UART
