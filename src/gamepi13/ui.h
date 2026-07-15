#pragma once
// GamePi13 LCD UI (Fase 2). Non-vital: nothing here may affect audio.
#include <stdint.h>

struct GamepiUiState {
  uint16_t bpm;
  uint8_t clock_src;     // 0=INT, 1=EXT, 2=MIDI
  uint16_t sample_idx;   // 0-based
  uint16_t sample_count;
  char sample_name[22];  // truncated, always NUL-terminated
  uint8_t leds[8];       // target brightness 0-255 (from LEDArray)
  uint8_t mode;          // selector 0-7
  uint16_t knob_a;       // 0-4095
  uint16_t knob_b;       // 0-4095
};

void gamepi_ui_init();                      // LCD init + splash (blocking ~1 s, call before audio IRQ is enabled)
void gamepi_ui_tick(const GamepiUiState &s);  // call once per 250 Hz control tick
void gamepi_ui_overlay_mode(uint8_t mode);  // Select pressed
void gamepi_ui_overlay_param(uint8_t mode, bool is_b, uint16_t val);  // L/R adjust
