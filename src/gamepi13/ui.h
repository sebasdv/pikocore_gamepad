#pragma once
// GamePi13 LCD UI (Fase 2). Non-vital: nothing here may affect audio.
#include <stdint.h>

struct GamepiUiState {
  uint16_t bpm;
  uint8_t clock_src;     // 0=INT, 1=EXT, 2=MIDI
  uint16_t sample_idx;   // 0-based
  uint16_t sample_count;
  char sample_name[22];  // truncated, always NUL-terminated
  char active_bank_name[24];  // "" if no SD bank loaded this session; truncated, NUL-terminated
  uint8_t leds[8];       // target brightness 0-255 (from LEDArray)
  // Bit i set = LED i is one of the two buttons currently driving an active
  // retrigger/stutter (btn_retrig) -- drawn cyan instead of the normal
  // amplitude-based orange, to distinguish stutter from a plain jump.
  uint8_t retrig_leds_mask;
  // Waveform zone (W_WAVE): identity of the PLAYING sample and the playhead.
  // wave_sample_idx follows main.cpp's `sample` (the ISR's playing sample --
  // can differ per-beat from sample_idx/sample_set while the tunnel FX hops
  // between samples); the waveform caches and shows THIS one so the playhead
  // always matches what's audible. wave_playhead_col is 0-239, or 255 for
  // "no playhead" (empty bank).
  uint16_t wave_sample_idx;
  uint8_t wave_playhead_col;
  uint8_t mode;          // selector 0-7
  uint16_t knob_a;       // 0-4095
  uint16_t knob_b;       // 0-4095
};

void gamepi_ui_init();                      // LCD init + splash (blocking ~1 s, call before audio IRQ is enabled)
void gamepi_ui_tick(const GamepiUiState &s);  // call once per 250 Hz control tick
void gamepi_ui_overlay_mode(uint8_t mode);  // Select pressed
void gamepi_ui_overlay_param(uint8_t mode, bool is_b, uint16_t val);  // L/R adjust
void gamepi_ui_overlay_tempo(uint16_t bpm);  // tempo adjust (mode 7 Function B): real BPM, not %

// Browse-SD mode (modo 8 del selector). Todas reusan el panel del overlay;
// llamarlas SOLO desde el lazo de botones de main.cpp, nunca desde
// gamepi_ui_tick() -- evitan competir con el dashboard normal por pantalla.
void gamepi_ui_sd_listing();
void gamepi_ui_sd_browse(const char *filename, uint32_t index, uint32_t count, bool is_active);
void gamepi_ui_sd_confirm_progress(const char *filename, uint8_t percent);
void gamepi_ui_sd_loading(const char *filename);
void gamepi_ui_sd_result(bool ok, const char *filename);
void gamepi_ui_sd_error(const char *message);
void gamepi_ui_sd_close();  // call when leaving mode 8; closes any open SD screen immediately
