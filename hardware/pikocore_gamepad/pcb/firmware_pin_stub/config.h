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
#define PIN_BTN_OK       26
