#include "ui.h"

#include <stdio.h>
#include <string.h>

#include "pico/time.h"

#include "../hw_gamepi13.h"
#include "../PikoAudioBank.h"

extern "C" {
#include "lcd/GUI_Paint.h"
#include "lcd/LCD_1in3.h"
}

// ---- palette (RGB565; Paint scale 65 stores big-endian, no swap needed) ----
#define COL_BG 0x0000        // black
#define COL_WHITE 0xFFFF
#define COL_GREEN 0x4EF0     // #4ade80
#define COL_BLUE 0x653F      // #60a5fa
#define COL_PINK 0xF396      // #f472b6
#define COL_CYAN 0x3DFF      // #38bdf8
#define COL_ORANGE 0xF4E1    // #f59e0b
#define COL_ORANGE_DIM 0x7A40  // #7c4a03
#define COL_GRAY 0x632C      // #666666
#define COL_DARK 0x18C3      // #1a1a1a

// Confirmed on hardware 2026-07-15: ROTATE_0 displayed 90 CW from correct
// reading orientation. ROTATE_270 (== 90 CCW) fixes it; matches the
// orientation the Waveshare demo itself uses for this exact panel/enclosure
// (Gamepi13-RP2040-Demo/C/examples/LCD_1in3_test.c: Paint_SetRotate(ROTATE_270)).
#define GAMEPI_LCD_ROTATE ROTATE_270

static UBYTE fb[LCD_1IN3_WIDTH * LCD_1IN3_HEIGHT * 2];  // 115 200 B static

struct Rect {
  uint16_t x, y, w, h;
};

// Widget zones (full-width strips; y per approved spec layout)
enum {
  W_TOP = 0,   // BPM + clock src | "NN/MM"
  W_NAME,      // sample name
  W_MODENAME,  // mode name
  W_BARA,      // bar A + label
  W_BARB,      // bar B + label
  W_DOTS,      // 8 mode dots
  // Waveform + playhead + slice highlights (ex "8 virtual LEDs" strip).
  // Deliberately LAST: gamepi_ui_tick() flushes ONE dirty widget per slot,
  // lowest index first, and this zone dirties often (moving playhead) --
  // lowest priority keeps it from starving every other widget.
  W_WAVE,
  W_COUNT
};

static const Rect kRect[W_COUNT] = {
    {0, 0, 240, 28},    // W_TOP
    {0, 28, 240, 24},   // W_NAME
    {0, 112, 240, 24},  // W_MODENAME
    {0, 136, 240, 32},  // W_BARA
    {0, 168, 240, 32},  // W_BARB
    {0, 208, 240, 20},  // W_DOTS
    {0, 52, 240, 44},   // W_WAVE
};

static bool dirty[W_COUNT];
static GamepiUiState drawn;
static bool have_drawn = false;

static const Rect kOverlay = {20, 64, 200, 112};
static bool overlay_on = false;
static bool overlay_persistent = false;  // true: SD-mode screens, no auto-expiry
static uint64_t overlay_deadline_us = 0;
// Real elapsed time via time_us_64(), NOT loop-iteration ticks -- ticks
// turned out to run the button/UI block at ~61.7 kHz in practice (measured
// from the ~988 kHz audio PWM IRQ this loop is gated on, divided by the
// "% 16 == 0" gate in main.cpp), not the "250 Hz" a tick-counted TTL
// assumed, so OVERLAY_TTL_TICKS=250 expired in ~4 ms instead of ~1 s.
#define OVERLAY_TTL_US 1000000  // ~1 s

static const char *kModeA[8] = {"SAMPLE",     "FILTRO",     "GATE",
                                "PROB SALTO", "PROB TUNEL", "SEC GRABAR",
                                "GUARDAR",    "VOLUMEN"};
static const char *kModeB[8] = {"BREAK FX",    "STRETCH",      "PROB GATE",
                                "PROB RETRIG", "PROB REVERSA", "SEC PLAY",
                                "CARGAR",      "TEMPO"};

// Caps how often the LCD is allowed to do a blocking SPI flush, independent
// of how often gamepi_ui_tick()/gamepi_ui_overlay_*() get called. Confirmed
// on hardware: with unthrottled flushing (a widget flush on every call where
// something is dirty, and the "250 Hz" main-loop tick actually running far
// faster than that comment implies -- ~988 kHz per the audio PWM wrap
// config), sustained SPI traffic while holding L/R for the overlay visibly
// degraded audio quality. Flushing is a "nice to have" (dashboard/overlay
// are non-vital per design), so it's safe to drop frames here; audio never
// waits on this.
#define MIN_FLUSH_INTERVAL_US 40000  // ~25 Hz max LCD flush rate
static uint64_t last_flush_us = 0;

static bool flush_allowed() {
  const uint64_t now = time_us_64();
  if (now - last_flush_us < MIN_FLUSH_INTERVAL_US) return false;
  last_flush_us = now;
  return true;
}

// Flush one rect of the framebuffer to the panel. LCD_1IN3_DisplayWindows()
// addresses raw panel/memory space, but our widget rects are in LOGICAL
// (pre-rotation) drawing space -- the same space Paint_SetPixel() maps
// through GAMEPI_LCD_ROTATE before writing into fb (see its Paint.Rotate
// switch in GUI_Paint.c). Convert the logical rect to the matching
// memory-space rect for the active rotation before flushing, or the panel
// window opens over the wrong bytes: with ROTATE_0 this was a no-op (logical
// == memory), which is why it stayed hidden until rotation was enabled --
// confirmed on hardware as garbled/overlapping widget content once
// ROTATE_270 was turned on. DisplayWindows takes exclusive ends and assumes
// full-frame stride (patched off-by-one in Task 1).
static void flush(const Rect &r) {
  mutex_enter_blocking(&gamepi_spi1_mutex);
#if GAMEPI_LCD_ROTATE == ROTATE_270
  const uint16_t mx0 = r.y;
  const uint16_t mx1 = (uint16_t)(r.y + r.h);
  const uint16_t my0 = (uint16_t)(LCD_1IN3_WIDTH - (r.x + r.w));
  const uint16_t my1 = (uint16_t)(LCD_1IN3_WIDTH - r.x);
  LCD_1IN3_DisplayWindows(mx0, my0, mx1, my1, (UWORD *)fb);
#elif GAMEPI_LCD_ROTATE == ROTATE_90
  const uint16_t mx0 = (uint16_t)(LCD_1IN3_HEIGHT - (r.y + r.h));
  const uint16_t mx1 = (uint16_t)(LCD_1IN3_HEIGHT - r.y);
  const uint16_t my0 = r.x;
  const uint16_t my1 = (uint16_t)(r.x + r.w);
  LCD_1IN3_DisplayWindows(mx0, my0, mx1, my1, (UWORD *)fb);
#elif GAMEPI_LCD_ROTATE == ROTATE_180
  const uint16_t mx0 = (uint16_t)(LCD_1IN3_WIDTH - (r.x + r.w));
  const uint16_t mx1 = (uint16_t)(LCD_1IN3_WIDTH - r.x);
  const uint16_t my0 = (uint16_t)(LCD_1IN3_HEIGHT - (r.y + r.h));
  const uint16_t my1 = (uint16_t)(LCD_1IN3_HEIGHT - r.y);
  LCD_1IN3_DisplayWindows(mx0, my0, mx1, my1, (UWORD *)fb);
#else
  LCD_1IN3_DisplayWindows(r.x, r.y, (uint16_t)(r.x + r.w),
                          (uint16_t)(r.y + r.h), (UWORD *)fb);
#endif
  mutex_exit(&gamepi_spi1_mutex);
}

static uint8_t pct(uint16_t v) { return (uint8_t)((uint32_t)v * 100u / 4095u); }

// ---- widget draw functions ----
static void clear_zone(const Rect &r) {
  Paint_ClearWindows(r.x, r.y, (uint16_t)(r.x + r.w), (uint16_t)(r.y + r.h),
                     COL_BG);
}

static void draw_top(const GamepiUiState &s) {
  clear_zone(kRect[W_TOP]);
  char buf[16];
  snprintf(buf, sizeof(buf), "%3u", s.bpm);
  Paint_DrawString_EN(8, 4, buf, &Font20, COL_GREEN, COL_BG);
  static const char *kSrc[3] = {"INT", "EXT", "MIDI"};
  Paint_DrawString_EN(58, 10, kSrc[s.clock_src < 3 ? s.clock_src : 0], &Font12,
                      COL_GRAY, COL_BG);
  if (s.sample_count > 0) {
    snprintf(buf, sizeof(buf), "%02u/%02u", (unsigned)(s.sample_idx + 1),
             (unsigned)s.sample_count);
  } else {
    snprintf(buf, sizeof(buf), "--/--");
  }
  Paint_DrawString_EN(240 - 8 - 5 * 11, 6, buf, &Font16, COL_BLUE, COL_BG);
}

static void draw_name(const GamepiUiState &s) {
  clear_zone(kRect[W_NAME]);
  char buf[48];
  if (s.active_bank_name[0] != '\0') {
    snprintf(buf, sizeof(buf), "%s | %s", s.sample_name, s.active_bank_name);
  } else {
    snprintf(buf, sizeof(buf), "%s", s.sample_name);
  }
  // Defensive hard truncation: at Font12's ~7px/char, this zone's 240px
  // width holds ~32 visible characters from x=8 before running off the
  // physical screen -- the combined sample+bank string can exceed that even
  // though each field is individually truncated to fit on its own (22 and
  // 24 chars respectively). Paint_DrawString_EN does not clip for us.
  if (strlen(buf) > 32) buf[32] = '\0';
  Paint_DrawString_EN(8, 32, buf, &Font12, COL_GRAY, COL_BG);
}

// ---- waveform cache (W_WAVE) ----
// 240 columns of min/max over the PLAYING sample (s.wave_sample_idx), 8-bit
// unsigned PCM (128 = center). 480 bytes of RAM; recomputed synchronously on
// sample change -- ~7.7k XIP reads = ~1-4 ms once, and the audio ISR preempts
// this loop, so playback never notices. Full cost study in the design spec
// (docs/superpowers/specs/2026-07-16-waveform-playhead-design.md).
static uint8_t wave_min[240];
static uint8_t wave_max[240];
static uint16_t wave_cached_sample = 0xffff;
static bool wave_cache_valid = false;
static uint64_t wave_playhead_mark_us = 0;

static void wave_recompute(uint16_t sample_idx) {
  const uint32_t len = piko_raw_len(sample_idx);
  if (piko_audio_sample_count() == 0 || len <= 1) {
    for (uint16_t c = 0; c < 240; c++) {
      wave_min[c] = 128;
      wave_max[c] = 128;
    }
    return;
  }
  for (uint32_t c = 0; c < 240; c++) {
    const uint32_t start = (uint32_t)(((uint64_t)len * c) / 240u);
    uint32_t end = (uint32_t)(((uint64_t)len * (c + 1)) / 240u);
    if (end <= start) end = start + 1;
    // Up to ~32 evenly spaced probes per column: plenty for a 240px lo-fi
    // outline, and caps the whole recompute at ~7.7k flash reads.
    uint32_t step = (end - start) / 32u;
    if (step == 0) step = 1;
    uint8_t mn = 255;
    uint8_t mx = 0;
    for (uint32_t f = start; f < end; f += step) {
      const uint8_t v = piko_raw_val(sample_idx, f);
      if (v < mn) mn = v;
      if (v > mx) mx = v;
    }
    wave_min[c] = mn;
    wave_max[c] = mx;
  }
}

static void draw_wave(const GamepiUiState &s) {
  clear_zone(kRect[W_WAVE]);
  constexpr uint16_t kTop = 54;  // 40px band inside the 52..96 zone
  constexpr uint16_t kBot = 93;
  // Slice separators first (subtle, behind the waveform): the 8 music
  // buttons ARE the 8 slices of the loop, 30 columns each.
  for (uint8_t b = 1; b < 8; b++) {
    const uint16_t x = (uint16_t)(b * 30);
    Paint_DrawLine(x, kTop, x, kBot, COL_DARK, DOT_PIXEL_1X1,
                   LINE_STYLE_SOLID);
  }
  for (uint16_t c = 0; c < 240; c++) {
    const uint8_t slice = (uint8_t)(c / 30);
    UWORD col = COL_ORANGE_DIM;  // background waveform
    if (s.retrig_leds_mask & (uint8_t)(1u << slice)) {
      col = COL_CYAN;  // stutter indicator wins, same as the old LED strip
    } else if (s.leds[slice] >= 8) {
      col = COL_ORANGE;  // slice currently lit (inherits the LED semantics)
    }
    const uint16_t y0 =
        (uint16_t)(kBot - ((uint16_t)wave_max[c] * (kBot - kTop)) / 255u);
    const uint16_t y1 =
        (uint16_t)(kBot - ((uint16_t)wave_min[c] * (kBot - kTop)) / 255u);
    Paint_DrawLine(c, y0, c, y1, col, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
  }
  if (s.wave_playhead_col < 240) {
    Paint_DrawLine(s.wave_playhead_col, kTop, s.wave_playhead_col, kBot,
                   COL_WHITE, DOT_PIXEL_1X1, LINE_STYLE_SOLID);
  }
}

static void draw_modename(const GamepiUiState &s) {
  clear_zone(kRect[W_MODENAME]);
  // Mode 8 (Browse SD) has no slot in the 8-entry kModeA table -- naively
  // masking with & 7 would alias it onto mode 0 ("SAMPLE"), which read as a
  // real bug during hardware testing (looked like the wrong mode was active).
  const char *name = (s.mode == 8) ? "SD" : kModeA[s.mode & 7];
  Paint_DrawString_EN(8, 116, name, &Font16, COL_PINK, COL_BG);
}

static void draw_bar(const Rect &zone, uint16_t bar_y, uint16_t val, UWORD col,
                     char ab) {
  clear_zone(zone);
  // frame + fill: 224 px wide, 14 px tall
  Paint_DrawRectangle(8, bar_y, 231, (uint16_t)(bar_y + 13), COL_DARK,
                      DOT_PIXEL_1X1, DRAW_FILL_FULL);
  uint16_t w = (uint16_t)((uint32_t)val * 224u / 4095u);
  if (w > 0) {
    Paint_DrawRectangle(8, bar_y, (uint16_t)(8 + w), (uint16_t)(bar_y + 13),
                        col, DOT_PIXEL_1X1, DRAW_FILL_FULL);
  }
  char buf[12];
  snprintf(buf, sizeof(buf), "%c %u%%", ab, pct(val));
  Paint_DrawString_EN(8, (uint16_t)(bar_y + 16), buf, &Font12, COL_GRAY,
                      COL_BG);
}

static void draw_dots(const GamepiUiState &s) {
  clear_zone(kRect[W_DOTS]);
  // 8 dots, radius 4, 14 px pitch, centered: start x = 67
  // Mode 8 (Browse SD) has no dot of its own -- leave all 8 dark rather than
  // falsely lighting dot 0 via an & 7 alias (same bug as draw_modename above).
  for (uint8_t i = 0; i < 8; i++) {
    UWORD col = (s.mode != 8 && i == s.mode) ? COL_PINK : COL_DARK;
    Paint_DrawCircle((uint16_t)(71 + i * 14), 218, 4, col, DOT_PIXEL_1X1,
                     DRAW_FILL_FULL);
  }
}

static void draw_widget(uint8_t i, const GamepiUiState &s) {
  switch (i) {
    case W_TOP:
      draw_top(s);
      break;
    case W_NAME:
      draw_name(s);
      break;
    case W_WAVE:
      draw_wave(s);
      break;
    case W_MODENAME:
      draw_modename(s);
      break;
    case W_BARA:
      draw_bar(kRect[W_BARA], 140, s.knob_a, COL_PINK, 'A');
      break;
    case W_BARB:
      draw_bar(kRect[W_BARB], 172, s.knob_b, COL_CYAN, 'B');
      break;
    case W_DOTS:
      draw_dots(s);
      break;
    default:
      break;
  }
}

void gamepi_ui_init() {
  gamepi_lcd_dev_init();
  LCD_1IN3_Init(HORIZONTAL);
  Paint_NewImage(fb, LCD_1IN3_WIDTH, LCD_1IN3_HEIGHT, GAMEPI_LCD_ROTATE, BLACK);
  Paint_SetScale(65);
  Paint_Clear(COL_BG);
  // splash: "pikocore" Font24 (8*17=136 px) / "GamePi13" Font16 (8*11=88 px)
  Paint_DrawString_EN(52, 96, "pikocore", &Font24, COL_PINK, COL_BG);
  Paint_DrawString_EN(76, 130, "GamePi13", &Font16, COL_GRAY, COL_BG);
  LCD_1IN3_Display((UWORD *)fb);
  gamepi_lcd_backlight(60);
  sleep_ms(600);
  Paint_Clear(COL_BG);
  LCD_1IN3_Display((UWORD *)fb);
  for (uint8_t i = 0; i < W_COUNT; i++) dirty[i] = true;
}

void gamepi_ui_tick(const GamepiUiState &s) {
  // Waveform cache upkeep: invalidate while the bank is being rewritten
  // (covers SD/USB reloads even when the new sample keeps the same index
  // and length), recompute synchronously once it settles or the playing
  // sample changes. Blocking ~1-4 ms worst case, once per change -- the
  // audio ISR preempts this loop, so playback never notices.
  if (piko_audio_bank_mutating()) {
    wave_cache_valid = false;
  } else if (!wave_cache_valid || s.wave_sample_idx != wave_cached_sample) {
    wave_recompute(s.wave_sample_idx);
    wave_cached_sample = s.wave_sample_idx;
    wave_cache_valid = true;
    dirty[W_WAVE] = true;
  }

  // Mark widgets whose backing data changed since last draw.
  if (!have_drawn) {
    for (uint8_t i = 0; i < W_COUNT; i++) dirty[i] = true;
  } else {
    if (s.bpm != drawn.bpm || s.clock_src != drawn.clock_src ||
        s.sample_idx != drawn.sample_idx ||
        s.sample_count != drawn.sample_count) {
      dirty[W_TOP] = true;
    }
    if (strcmp(s.sample_name, drawn.sample_name) != 0) dirty[W_NAME] = true;
    if (memcmp(s.leds, drawn.leds, sizeof(s.leds)) != 0 ||
        s.retrig_leds_mask != drawn.retrig_leds_mask) {
      dirty[W_WAVE] = true;
    }
    if (s.wave_playhead_col != drawn.wave_playhead_col &&
        time_us_64() - wave_playhead_mark_us >= 100000) {
      // Playhead motion alone redraws at most ~10 Hz; without this the wave
      // zone would dirty every tick and, even at lowest priority, consume a
      // flush slot every time nothing else changed.
      wave_playhead_mark_us = time_us_64();
      dirty[W_WAVE] = true;
    }
    if (s.mode != drawn.mode) {
      dirty[W_MODENAME] = true;
      dirty[W_DOTS] = true;
    }
    if (s.knob_a != drawn.knob_a) dirty[W_BARA] = true;
    if (s.knob_b != drawn.knob_b) dirty[W_BARB] = true;
  }
  drawn = s;
  have_drawn = true;

  // Flush at most ONE dirty widget per allowed flush window (see
  // flush_allowed()) to bound total SPI blocking time.
  if (overlay_on) {
    // Persistent overlays (SD-mode screens) never expire on a timer -- they
    // stay up until gamepi_ui_sd_close() is called explicitly (main.cpp,
    // when leaving mode 8). Everything else (mode/param flash) times out
    // after OVERLAY_TTL_US of real elapsed time.
    if (overlay_persistent || time_us_64() < overlay_deadline_us) {
      return;  // still showing; nothing else to draw this call
    }
    if (!flush_allowed()) return;  // wait for a flush slot before restoring
    overlay_on = false;
    Paint_ClearWindows(kOverlay.x, kOverlay.y,
                       (uint16_t)(kOverlay.x + kOverlay.w),
                       (uint16_t)(kOverlay.y + kOverlay.h), COL_BG);
    flush(kOverlay);
    dirty[W_WAVE] = true;      // zones the overlay covered
    dirty[W_MODENAME] = true;
    dirty[W_BARA] = true;
    return;  // used this call's flush slot on the restore
  }

  if (!flush_allowed()) return;
  for (uint8_t i = 0; i < W_COUNT; i++) {
    if (dirty[i]) {
      draw_widget(i, s);
      flush(kRect[i]);
      dirty[i] = false;
      break;
    }
  }
}

// Draw the overlay panel into fb and flush it. Called from the same 250 Hz
// context as gamepi_ui_tick (all core0) — no concurrency to worry about.
static void overlay_show_panel(bool persistent = false) {
  overlay_on = true;
  overlay_persistent = persistent;
  overlay_deadline_us = time_us_64() + OVERLAY_TTL_US;
  Paint_ClearWindows(kOverlay.x, kOverlay.y,
                     (uint16_t)(kOverlay.x + kOverlay.w),
                     (uint16_t)(kOverlay.y + kOverlay.h), COL_DARK);
  Paint_DrawRectangle(kOverlay.x, kOverlay.y,
                      (uint16_t)(kOverlay.x + kOverlay.w - 1),
                      (uint16_t)(kOverlay.y + kOverlay.h - 1), COL_PINK,
                      DOT_PIXEL_2X2, DRAW_FILL_EMPTY);
}

static uint16_t centered_x(const char *txt, uint16_t glyph_w) {
  uint16_t w = (uint16_t)(strlen(txt) * glyph_w);
  return (uint16_t)(kOverlay.x + (kOverlay.w > w ? (kOverlay.w - w) / 2 : 0));
}

void gamepi_ui_overlay_mode(uint8_t mode) {
  mode &= 7;
  overlay_show_panel();
  char title[12];
  snprintf(title, sizeof(title), "MODO %u", (unsigned)(mode + 1));
  Paint_DrawString_EN(centered_x(title, 11), (uint16_t)(kOverlay.y + 12),
                      title, &Font16, COL_GRAY, COL_DARK);
  Paint_DrawString_EN(centered_x(kModeA[mode], 14), (uint16_t)(kOverlay.y + 40),
                      kModeA[mode], &Font20, COL_PINK, COL_DARK);
  Paint_DrawString_EN(centered_x(kModeB[mode], 11), (uint16_t)(kOverlay.y + 74),
                      kModeB[mode], &Font16, COL_CYAN, COL_DARK);
  if (flush_allowed()) flush(kOverlay);
}

void gamepi_ui_overlay_param(uint8_t mode, bool is_b, uint16_t val) {
  mode &= 7;
  overlay_show_panel();
  const char *name = is_b ? kModeB[mode] : kModeA[mode];
  UWORD col = is_b ? COL_CYAN : COL_PINK;
  Paint_DrawString_EN(centered_x(name, 11), (uint16_t)(kOverlay.y + 10), name,
                      &Font16, col, COL_DARK);
  char v[8];
  snprintf(v, sizeof(v), "%u%%", (unsigned)pct(val));
  Paint_DrawString_EN(centered_x(v, 17), (uint16_t)(kOverlay.y + 38), v,
                      &Font24, COL_WHITE, COL_DARK);
  // progress bar: 170 px wide, centered
  uint16_t bx = (uint16_t)(kOverlay.x + (kOverlay.w - 170) / 2);
  uint16_t by = (uint16_t)(kOverlay.y + 86);
  Paint_DrawRectangle(bx, by, (uint16_t)(bx + 170), (uint16_t)(by + 10),
                      COL_BG, DOT_PIXEL_1X1, DRAW_FILL_FULL);
  uint16_t w = (uint16_t)((uint32_t)val * 170u / 4095u);
  if (w > 0) {
    Paint_DrawRectangle(bx, by, (uint16_t)(bx + w), (uint16_t)(by + 10), col,
                        DOT_PIXEL_1X1, DRAW_FILL_FULL);
  }
  if (flush_allowed()) flush(kOverlay);
}

// Tempo shows the real BPM integer, not a raw-knob percentage -- unlike
// every other Function A/B parameter, bpm_set is adjusted directly (see
// main.cpp's is_tempo branch) rather than derived from input_knob[]'s 0-4095
// range, so a "%" readout wouldn't mean anything here.
void gamepi_ui_overlay_tempo(uint16_t bpm) {
  overlay_show_panel();
  Paint_DrawString_EN(centered_x("TEMPO", 11), (uint16_t)(kOverlay.y + 10),
                      "TEMPO", &Font16, COL_CYAN, COL_DARK);
  char v[12];
  snprintf(v, sizeof(v), "%u BPM", (unsigned)bpm);
  Paint_DrawString_EN(centered_x(v, 17), (uint16_t)(kOverlay.y + 38), v,
                      &Font24, COL_WHITE, COL_DARK);
  uint16_t bx = (uint16_t)(kOverlay.x + (kOverlay.w - 170) / 2);
  uint16_t by = (uint16_t)(kOverlay.y + 86);
  Paint_DrawRectangle(bx, by, (uint16_t)(bx + 170), (uint16_t)(by + 10),
                      COL_BG, DOT_PIXEL_1X1, DRAW_FILL_FULL);
  const uint16_t clamped =
      bpm < GAMEPI_TEMPO_MIN_BPM ? GAMEPI_TEMPO_MIN_BPM
      : bpm > GAMEPI_TEMPO_MAX_BPM ? GAMEPI_TEMPO_MAX_BPM : bpm;
  const uint16_t w = (uint16_t)((uint32_t)(clamped - GAMEPI_TEMPO_MIN_BPM) *
                                170u /
                                (GAMEPI_TEMPO_MAX_BPM - GAMEPI_TEMPO_MIN_BPM));
  if (w > 0) {
    Paint_DrawRectangle(bx, by, (uint16_t)(bx + w), (uint16_t)(by + 10),
                        COL_CYAN, DOT_PIXEL_1X1, DRAW_FILL_FULL);
  }
  if (flush_allowed()) flush(kOverlay);
}

static void sd_panel_title(const char *title, UWORD color) {
  overlay_show_panel(true);  // persistent: SD screens don't auto-expire
  Paint_DrawString_EN(centered_x(title, 11), (uint16_t)(kOverlay.y + 12),
                      title, &Font16, color, COL_DARK);
}

// Truncate long filenames to what the overlay's 200px width can show at
// Font12 (7px/char) with some margin: ~26 chars.
static void draw_truncated(const char *text, uint16_t y, UWORD color) {
  char buf[27];
  size_t len = strlen(text);
  if (len > sizeof(buf) - 1) len = sizeof(buf) - 1;
  memcpy(buf, text, len);
  buf[len] = '\0';
  Paint_DrawString_EN(centered_x(buf, 7), y, buf, &Font12, color, COL_DARK);
}

void gamepi_ui_sd_close() {
  // Called when leaving mode 8: expire the persistent SD overlay immediately
  // so gamepi_ui_tick()'s normal (non-persistent) path reverts to the
  // regular dashboard on its next call, reusing that existing revert logic
  // instead of duplicating it here.
  overlay_persistent = false;
  overlay_deadline_us = time_us_64();
}

void gamepi_ui_sd_listing() {
  if (!flush_allowed()) return;
  sd_panel_title("SD", COL_GRAY);
  draw_truncated("Leyendo tarjeta...", (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
}

void gamepi_ui_sd_browse(const char *filename, uint32_t index, uint32_t count,
                         bool is_active) {
  if (!flush_allowed()) return;
  char pos[12];
  snprintf(pos, sizeof(pos), "%lu/%lu", (unsigned long)(index + 1),
           (unsigned long)count);
  sd_panel_title(pos, COL_GRAY);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50),
                is_active ? COL_GREEN : COL_PINK);
  // Two lines: L/R's navigation role was previously left implicit (only the
  // hold-to-load hint was shown), which read as "L does nothing" during
  // hardware testing.
  draw_truncated("L: ciclar lista", (uint16_t)(kOverlay.y + 72), COL_GRAY);
  draw_truncated(is_active ? "Cargado (banco activo)" : "Mantener R: cargar",
                (uint16_t)(kOverlay.y + 88), COL_GRAY);
  flush(kOverlay);
}

void gamepi_ui_sd_confirm_progress(const char *filename, uint8_t percent) {
  if (!flush_allowed()) return;
  sd_panel_title("Cargando...", COL_CYAN);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50), COL_WHITE);
  uint16_t bx = (uint16_t)(kOverlay.x + (kOverlay.w - 170) / 2);
  uint16_t by = (uint16_t)(kOverlay.y + 86);
  Paint_DrawRectangle(bx, by, (uint16_t)(bx + 170), (uint16_t)(by + 10),
                      COL_BG, DOT_PIXEL_1X1, DRAW_FILL_FULL);
  uint16_t w = (uint16_t)((uint32_t)percent * 170u / 100u);
  if (w > 0) {
    Paint_DrawRectangle(bx, by, (uint16_t)(bx + w), (uint16_t)(by + 10),
                        COL_CYAN, DOT_PIXEL_1X1, DRAW_FILL_FULL);
  }
  flush(kOverlay);
}

void gamepi_ui_sd_loading(const char *filename) {
  // Flushed once, unthrottled: this is the LAST LCD write before core0 stops
  // touching spi1 for the duration of the actual SD-read+flash-write (see
  // main.cpp's mode-8 handler) -- deliberately bypasses flush_allowed() so
  // the message is guaranteed on screen before that quiet window starts.
  sd_panel_title("Cargando...", COL_CYAN);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
}

void gamepi_ui_sd_result(bool ok, const char *filename) {
  if (!flush_allowed()) return;
  sd_panel_title(ok ? "Listo" : "Error", ok ? COL_GREEN : COL_PINK);
  draw_truncated(ok ? filename : "No se pudo cargar",
                 (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
}

void gamepi_ui_sd_error(const char *message) {
  if (!flush_allowed()) return;
  sd_panel_title("SD", COL_GRAY);
  draw_truncated(message, (uint16_t)(kOverlay.y + 50), COL_PINK);
  flush(kOverlay);
}
