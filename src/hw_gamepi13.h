#pragma once
// Pin map: Waveshare RP2350-PiZero + GamePi13 HAT.
// Verified against Gamepi13-RP2040-Demo/C/lib/Config/DEV_Config.c (LCD/I2C),
// LCD_1in3_test.c (buttons) and Python demos (buzzer=GP18, status LED=GP28).
// Do NOT trust the BCM column of the Waveshare wiki table (X/Y/R/Up differ).

// GamePi13 onboard PWM audio (speaker + headphone jack)
#define GAMEPI_AUDIO_PIN 18
// GamePi13 status LED, used as pikocore's beat LED
#define GAMEPI_LED_PIN 28
// Free header pins
#define GAMEPI_CLOCK_PIN 22  // clock in (same as original pikocore)
#define GAMEPI_TRIGO_PIN 12  // trigger out (original GP21 is button A)

// The 8 pikocore music buttons, pikocore order 0..7:
//                            Up  Dn  Lt  Rt   Y   X   B   A
#define GAMEPI_BUTTON_PINS {15, 6, 16, 13, 9, 5, 20, 21}

// Virtual-knob control buttons
#define GAMEPI_BTN_SELECT 19  // cycles selector (knob 0) through 8 modes
#define GAMEPI_BTN_START 26   // hold = edit Function B (knob 2) instead of A
#define GAMEPI_BTN_L 23       // decrease active knob
#define GAMEPI_BTN_R 4        // increase active knob

#define GAMEPI_KNOB_STEP 164    // ~4% of 4095 per repeat (full sweep ~2.5 s held)
#define GAMEPI_REPEAT_TICKS 25  // repeat every 100 ms at the 250 Hz input scan
