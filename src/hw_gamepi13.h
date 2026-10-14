#pragma once
#if PIKO_GAMEPAD
// Pin map: pikocore_gamepad carrier PCB (Waveshare RP2350-Plus module).
// The PCB pins (PIN_*) come from src/boards/pikocore_gamepad/config.h, which
// gate G-4 keeps in sync with hardware/pikocore_gamepad/pcb/pinmap.py. This
// block only maps them onto the GAMEPI_* names the shared GamePi13 input/UI
// layer already uses, plus the firmware-only choices below.
#include "boards/pikocore_gamepad/config.h"

// No PWM audio: the engine ticks off a PWM slice with no GPIO routed to it
// (slice 0 = GP0/GP1, both D-pad inputs) and the samples go out over I2S --
// see src/gamepad/audio_i2s.h.
#define GAMEPI_AUDIO_TICK_SLICE 0
#define GAMEPI_I2S_HZ 48000
#define GAMEPI_I2S_PIO pio0  // pio1 sm0 is the one-wire MIDI receiver
#define GAMEPI_I2S_SM 0
// RP2350-Plus onboard LED (module-internal GP25, not on the header).
#define GAMEPI_LED_PIN 25
// The carrier PCB has no clock jack nor trigger jack. GP27/GP28 are the two
// FREE (unconnected, ADC-capable) header pins per pinmap.py; parking the
// clock input there with its pull-up reads idle HIGH (no false clock pulses,
// same reasoning as the GamePi13 branch in main()), and the trigger output
// toggles a pin nothing listens to. Wire them to a jack and they just work.
#define GAMEPI_CLOCK_PIN 27
#define GAMEPI_TRIGO_PIN 28

// The 8 pikocore music buttons, pikocore order 0..7 (same as GamePi13):
//                            Up            Dn              Lt              Rt              Y          X          B          A
#define GAMEPI_BUTTON_PINS {PIN_DPAD_UP, PIN_DPAD_DOWN, PIN_DPAD_LEFT, PIN_DPAD_RIGHT, PIN_BTN_Y, PIN_BTN_X, PIN_BTN_B, PIN_BTN_A}

#define GAMEPI_BTN_SELECT PIN_BTN_SELECT
#define GAMEPI_BTN_START PIN_BTN_START
#define GAMEPI_BTN_L PIN_BTN_L
#define GAMEPI_BTN_R PIN_BTN_R
// NAV5 centre press: a second Start (Button::Init(pin, debounce, alt_pin)).
#define GAMEPI_BTN_OK PIN_BTN_OK

// LCD ST7789 1.3" 240x240 on SPI0, 7-pin module: no CS line (tied low on
// the panel), so EPD_CS_PIN is -1 and dev_shim.c skips it.
#define GAMEPI_LCD_CS_PIN -1
#define GAMEPI_LCD_CLK_PIN PIN_LCD_SCK
#define GAMEPI_LCD_MOSI_PIN PIN_LCD_MOSI
#define GAMEPI_LCD_DC_PIN PIN_LCD_DC
#define GAMEPI_LCD_RST_PIN PIN_LCD_RES
#define GAMEPI_LCD_BL_PIN PIN_LCD_BLK
#define GAMEPI_SPI spi0
// ponytail: same 10 MHz the GamePi13 wiring needed. The carrier PCB has short
// traces and nothing else on spi0, so try 31.25/62.5 MHz once there is a
// board on the bench; flush() reasserts this value on every transfer.
#define GAMEPI_LCD_SPI_HZ (10000 * 1000)
#else
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

// LCD ST7789 1.3" 240x240 on SPI1 (Fase 2)
// Pins verified against Gamepi13-RP2040-Demo/C/lib/Config/DEV_Config.c:162-171.
#define GAMEPI_LCD_CS_PIN 8
#define GAMEPI_LCD_CLK_PIN 10
#define GAMEPI_LCD_MOSI_PIN 11
#define GAMEPI_LCD_DC_PIN 25
#define GAMEPI_LCD_RST_PIN 27
#define GAMEPI_LCD_BL_PIN 7  // backlight, PWM

// El LCD y la microSD COMPARTEN spi1. El driver de SD reconfigura el bus cada
// vez que lo usa (my_spi.c lo abre a 100 kHz, sd_spi.c baja a 400 kHz para el
// init de tarjeta y sube a 12 MHz para datos) y no restaura nada al terminar --
// no sabe que el LCD existe. Por eso el LCD tiene que reafirmar SU velocidad
// cada vez que toma el bus (ver flush() en ui.cpp), no solo una vez al
// arrancar. Sin eso, al volver del modo 8 (Browse SD) los flush quedaban
// corriendo a 100-400 kHz para siempre: confirmado en hardware, un flush de
// zona pasaba de ~18 ms a ~1.8 s y bloqueaba el lazo de control (botones sin
// responder, cambio de modo tardando segundos, mientras el audio seguía porque
// va por la ISR de PWM). El valor es el que usa el demo de Waveshare para este
// panel/cableado -- ver en dev_shim.c por qué no se sube más.
#define GAMEPI_SPI spi1
#define GAMEPI_LCD_SPI_HZ (10000 * 1000)
#endif  // PIKO_GAMEPAD

#define GAMEPI_KNOB_STEP 164    // ~4% of 4095 per repeat (full sweep ~2.5 s held)
// Real elapsed time via time_us_64(), not loop-iteration ticks -- the old
// GAMEPI_REPEAT_TICKS=25 assumed a 250 Hz input scan, but the actual rate
// (measured from the ~988 kHz audio PWM IRQ this loop is gated on) is
// ~61.7 kHz, ~247x faster, so the tick-counted delay fired in well under a
// millisecond instead of the intended ~100 ms.
#define GAMEPI_REPEAT_US 100000  // repeat every 100 ms while L/R is held
// Un toque humano "rápido" real dura 150-300ms entre presionar y soltar -- más
// que GAMEPI_REPEAT_US, así que el mecanismo de repetición disparaba un SEGUNDO
// paso (el primer "repeat") antes de que soltaras, percibido como "avanza dos"
// o "cambia al presionar y al soltar" en vez de exactamente una vez. Mismo
// patrón que el "typematic delay" de un teclado: el primer paso es inmediato,
// el SEGUNDO espera este intervalo más largo, y del tercero en adelante vuelve
// a la cadencia normal de 100ms.
// Aplica a TODOS los parámetros de L/R (genéricos, selección de sample y
// tempo). Al principio era sólo para selección de sample, donde el problema se
// notaba primero; con las barras segmentadas (1 bloque = 1 paso) el doble-paso
// quedó visible en todos los modos, así que se generalizó.
#define GAMEPI_FIRST_REPEAT_US 350000  // 350 ms antes del 2do paso

// Tempo (mode 7 / Volumen, Function B) direct bpm_set adjustment. BPM's
// practical range (20-360) is much narrower than the generic 0-4095 knobs
// GAMEPI_KNOB_STEP was tuned for, so it gets its own tap/hold-1s/hold-3s
// acceleration instead of the flat step-per-repeat every other parameter
// uses.
#define GAMEPI_TEMPO_MIN_BPM 20
#define GAMEPI_TEMPO_MAX_BPM 360  // matches param_set_bpm()'s own upper guard
#define GAMEPI_TEMPO_STEP_FINE 1   // tap (held < 1 s): +/-1 BPM per repeat
#define GAMEPI_TEMPO_STEP_MED 5    // held 1-3 s: +/-5 BPM per repeat
#define GAMEPI_TEMPO_STEP_FAST 20  // held > 3 s: +/-20 BPM per repeat
#define GAMEPI_TEMPO_TIER2_US 1000000ull  // 1 s
#define GAMEPI_TEMPO_TIER3_US 3000000ull  // 3 s
