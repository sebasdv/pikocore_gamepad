#include "ui.h"

#include <stdio.h>
#include <string.h>

#include "pico/time.h"

#include "../hw_gamepi13.h"
#include "../PikoAudioBank.h"
#include "splash_logo.h"

extern "C" {
#include "lcd/GUI_Paint.h"
#include "lcd/LCD_1in3.h"
}

// ui_bitmaps.h calls Paint_SetPixel()/Paint_DrawImage() (both declared above,
// with C linkage from the extern "C" block) -- must be included after it.
#include "ui_bitmaps.h"

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
#define COL_RED 0xFB8E       // #f87171
#define COL_ORANGE2 0xFC87   // #fb923c (distinto de COL_ORANGE/amber ya existente)
#define COL_YELLOW 0xFE62    // #facc15
#define COL_TEAL 0x269D      // #22d3ee
#define COL_VIOLET 0xA45F    // #a78bfa

// Confirmed on hardware 2026-07-15: ROTATE_0 displayed 90 CW from correct
// reading orientation. ROTATE_270 (== 90 CCW) fixes it; matches the
// orientation the Waveshare demo itself uses for this exact panel/enclosure
// (Gamepi13-RP2040-Demo/C/examples/LCD_1in3_test.c: Paint_SetRotate(ROTATE_270)).
#define GAMEPI_LCD_ROTATE ROTATE_270

static UBYTE fb[LCD_1IN3_WIDTH * LCD_1IN3_HEIGHT * 2];  // 115 200 B static

struct Rect {
  uint16_t x, y, w, h;
};

// Widget zones (full-width strips; y per Lopaka MODE_0 layout). W_MODENAME
// from the old text-only dashboard is gone -- Lopaka's design has no generic
// "mode name" line; instead each bar (W_BARA/W_BARB) carries its own Function
// A/B label right above it, so that concept folded into those two zones.
enum {
  W_TOP = 0,   // BPM digits + clock-src icon + play/stop icons
  W_NAME,      // filename frame + sample idx/count digits
  W_BARA,      // Function A label (bitmap mode 0 / text fallback) + bar
  W_BARB,      // Function B label (bitmap mode 0 / text fallback) + bar
  W_DOTS,      // 9 mode-indicator icons (M_0..M_7 + M_SD)
  // Waveform frame + playhead + slice highlights. Deliberately LAST:
  // gamepi_ui_tick() flushes ONE dirty widget per slot, lowest index first,
  // and this zone dirties often (moving playhead) -- lowest priority keeps
  // it from starving every other widget.
  W_WAVE,
  W_COUNT
};

static const Rect kRect[W_COUNT] = {
    {0, 0, 240, 28},    // W_TOP
    {0, 28, 240, 24},   // W_NAME
    {0, 105, 240, 47},  // W_BARA (label y107-127, bar y132-152)
    {0, 155, 240, 47},  // W_BARB (label y157-177, bar y182-202)
    {0, 205, 240, 26},  // W_DOTS (9 icons, y207-228)
    {0, 54, 240, 48},   // W_WAVE
};

static bool dirty[W_COUNT];
static GamepiUiState drawn;
static bool have_drawn = false;

static const Rect kOverlay = {18, 50, 205, 138};  // matches kSdOverlayFrame bitmap exactly
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

// ---- widget draw functions ----
static void clear_zone(const Rect &r) {
  Paint_ClearWindows(r.x, r.y, (uint16_t)(r.x + r.w), (uint16_t)(r.y + r.h),
                     COL_BG);
}

static void draw_top(const GamepiUiState &s) {
  clear_zone(kRect[W_TOP]);
  char buf[8];
  snprintf(buf, sizeof(buf), "%u", s.bpm);
  // BPM digits right-aligned so their RIGHT edge always lands at x=30 (just
  // before the clock-source slash/icon), growing leftward as the digit count
  // changes (e.g. 99 -> 100) instead of colliding with what's to the right.
  draw_digit_string(30, 6, buf, kBpmDigits, nullptr, 0, 0, true);
  // BPM_Slash: always between the BPM digits and whichever clock-source icon
  // is active. MODE_0.txt's own mockup shows it between the Int_clock and
  // Ext_clock reference icons instead -- that's just how Lopaka laid out two
  // static examples side by side (it doesn't simulate the real INT/EXT
  // conditional), not the real runtime position.
  Paint_DrawImage((const unsigned char *)kBpmSlash, 30, 3, 14, 20);
  if (s.clock_src == 0) {
    Paint_DrawImage((const unsigned char *)kIntClock, 44, 6, 38, 14);
  } else if (s.clock_src == 1) {
    Paint_DrawImage((const unsigned char *)kExtClock, 44, 6, 40, 14);
  } else {
    // MIDI has no graphic yet (see the design spec's Riesgos conocidos) --
    // text fallback, same pattern as the not-yet-designed Function A/B
    // labels for modes 1-7 below.
    Paint_DrawString_EN(44, 10, "MIDI", &Font12, COL_GRAY, COL_BG);
  }
  Paint_DrawMonoBitmap(212, 7, kPlayBits, 12, 12,
                       s.playing ? COL_WHITE : COL_GRAY);
  Paint_DrawMonoBitmap(226, 7, kStopBits, 12, 12,
                       s.playing ? COL_GRAY : COL_WHITE);
}

static void draw_name(const GamepiUiState &s) {
  clear_zone(kRect[W_NAME]);
  char buf[48];
  if (s.active_bank_name[0] != '\0') {
    snprintf(buf, sizeof(buf), "%s | %s", s.sample_name, s.active_bank_name);
  } else {
    snprintf(buf, sizeof(buf), "%s", s.sample_name);
  }
  // Defensive hard truncation: at Font12's ~7px/char, this zone's 191px
  // frame width (leaving room for the sample idx/count digits to its right)
  // holds fewer visible characters than the full 240px screen would --
  // Paint_DrawString_EN does not clip for us.
  if (strlen(buf) > 24) buf[24] = '\0';
  Paint_DrawString_EN(8, 32, buf, &Font12, COL_GRAY, COL_BG);
  char idx[8];
  if (s.sample_count > 0) {
    snprintf(idx, sizeof(idx), "%02u/%02u", (unsigned)(s.sample_idx + 1),
             (unsigned)s.sample_count);
  } else {
    snprintf(idx, sizeof(idx), "00/00");
  }
  draw_digit_string(238, 32, idx, kBankDigits, kBankSlash, 7, 15, true);
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
  constexpr uint16_t kTop = 54;  // 39px band inside the 52..96 zone
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
      // Collapsed from the old LED strip's 3-tier brightness (off/dim/bright)
      // to 2 tiers here: the dim waveform IS the new "off" state, so this
      // "lit" threshold (>= 8) reuses the old bright color at a lower bar
      // than before, not the same threshold as the old >=128 bright tier.
      col = COL_ORANGE;
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

// mode 8 (Browse SD) has no slot in the 8-entry label tables -- these two
// zones sit behind the SD mode's persistent overlay while mode 8 is active,
// so falling back to mode 0's label there is invisible, not a bug (unlike
// the old draw_modename/draw_dots aliasing bug this replaces, which WAS
// visible since nothing covered those zones).
static void draw_function_label(uint16_t y, const ModeLabelBitmap *bmp,
                                const char *text, UWORD text_col) {
  if (bmp) {
    Paint_DrawImage((const unsigned char *)bmp->pixels, 0, y, bmp->w, bmp->h);
  } else {
    Paint_DrawString_EN(8, y, text, &Font16, text_col, COL_BG);
  }
}

static void draw_bar(uint16_t bar_y, uint16_t val, UWORD col) {
  // frame + fill: 224 px wide, 14 px tall (unchanged geometry, new y)
  Paint_DrawRectangle(8, bar_y, 231, (uint16_t)(bar_y + 13), COL_DARK,
                      DOT_PIXEL_1X1, DRAW_FILL_FULL);
  uint16_t w = (uint16_t)((uint32_t)val * 224u / 4095u);
  if (w > 0) {
    Paint_DrawRectangle(8, bar_y, (uint16_t)(8 + w), (uint16_t)(bar_y + 13),
                        col, DOT_PIXEL_1X1, DRAW_FILL_FULL);
  }
}

// Un color por modo para la barra de Function A/B (y el fallback de texto de
// draw_function_label(), aunque hoy sea inalcanzable con los 8 modos ya
// bitmapeados). Ver docs/superpowers/specs/2026-07-19-mode-colors-design.md.
static const uint16_t kModeColorA[8] = {COL_RED,     COL_ORANGE2, COL_YELLOW, COL_GREEN,
                                        COL_TEAL,    COL_BLUE,    COL_VIOLET, COL_PINK};
static const uint16_t kModeColorB[8] = {COL_BLUE,    COL_VIOLET,  COL_PINK,   COL_RED,
                                        COL_ORANGE2, COL_YELLOW,  COL_GREEN,  COL_TEAL};

// Selección de sample (modo 0, Function A): en vez de un relleno continuo
// proporcional al valor crudo del knob, un paginador de segmentos -- refleja
// que la selección ya es discreta (sample_change = knob * sample_count / 4095,
// main.cpp). Se agrupa en potencias de 2 si sample_count no entra en 32
// segmentos, para que cada segmento siga siendo distinguible aun con el
// máximo real de 128 samples por banco (PIKO_BANK_MAX_SAMPLES).
static void draw_sample_bar(uint16_t bar_y, uint16_t sample_idx,
                            uint16_t sample_count, UWORD col) {
  Paint_DrawRectangle(8, bar_y, 231, (uint16_t)(bar_y + 13), COL_DARK,
                      DOT_PIXEL_1X1, DRAW_FILL_FULL);
  if (sample_count <= 1) {
    Paint_DrawRectangle(8, bar_y, 231, (uint16_t)(bar_y + 13), col,
                        DOT_PIXEL_1X1, DRAW_FILL_FULL);
    return;
  }
  uint16_t group_size = 1;
  while ((sample_count + group_size - 1) / group_size > 32) {
    group_size = (uint16_t)(group_size * 2);
  }
  uint16_t n_segments =
      (uint16_t)((sample_count + group_size - 1) / group_size);
  uint16_t active_segment = (uint16_t)(sample_idx / group_size);
  uint16_t seg_w = (uint16_t)((224u - (n_segments - 1)) / n_segments);
  uint16_t x = (uint16_t)(8 + active_segment * (seg_w + 1));
  // Clamp: grouping arithmetic can push the LAST segment 1px past the right
  // edge (231) when n_segments evenly divides 225 -- e.g. n_segments=3,5,9,
  // 15,25. Confirmed via exhaustive brute-force check over every valid
  // sample_count/sample_idx combination up to 128.
  if ((uint16_t)(x + seg_w) > 231) {
    seg_w = (uint16_t)(231 - x);
  }
  Paint_DrawRectangle(x, bar_y, (uint16_t)(x + seg_w), (uint16_t)(bar_y + 13),
                      col, DOT_PIXEL_1X1, DRAW_FILL_FULL);
}

static void draw_function_a(const GamepiUiState &s) {
  clear_zone(kRect[W_BARA]);
  const uint8_t m = (s.mode < 8) ? s.mode : 0;
  draw_function_label(107, kModeABitmap[m], kModeA[m], kModeColorA[m]);
  if (m == 0) {
    draw_sample_bar(132, s.sample_idx, s.sample_count, kModeColorA[m]);
  } else {
    draw_bar(132, s.knob_a, kModeColorA[m]);
  }
}

static void draw_function_b(const GamepiUiState &s) {
  clear_zone(kRect[W_BARB]);
  const uint8_t m = (s.mode < 8) ? s.mode : 0;
  draw_function_label(157, kModeBBitmap[m], kModeB[m], kModeColorB[m]);
  draw_bar(182, s.knob_b, kModeColorB[m]);
}

static void draw_dots(const GamepiUiState &s) {
  clear_zone(kRect[W_DOTS]);
  // 9 icons (M_0..M_7 + M_SD), 18px pitch starting at x=27 -- matches
  // MODE_0.txt exactly (M_SD sits right after M_7 at x=27+8*18=171).
  // Dimming factor is a first-attempt value (~35% brightness), tune on
  // hardware per the design spec's Riesgos conocidos.
  constexpr uint8_t kInactiveDim = 90;
  for (uint8_t i = 0; i < 9; i++) {
    const ModeIcon &icon = kModeIcons[i];
    const uint16_t x = (uint16_t)(27 + i * 18);
    const bool active = (i < 8) ? (s.mode == i) : (s.mode == 8);
    if (active) {
      Paint_DrawImage((const unsigned char *)icon.pixels, x, 207, icon.w,
                       icon.h);
    } else {
      Paint_DrawImageDimmed(icon.pixels, x, 207, icon.w, icon.h,
                            kInactiveDim);
    }
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
    case W_BARA:
      draw_function_a(s);
      break;
    case W_BARB:
      draw_function_b(s);
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
  // splash: "pikocore" wordmark, designed in Lopaka (see splash_logo.h) --
  // drawn once into the framebuffer at full brightness. The fade-in below
  // is done via the backlight PWM, not by blending pixel colors -- there's
  // no alpha/blend support in Paint_DrawImage(), and ramping the backlight
  // is both simpler and cheaper (no extra SPI redraws).
  Paint_DrawImage((const unsigned char *)kSplashLogoPixels, 36, 97,
                   SPLASH_LOGO_WIDTH, SPLASH_LOGO_HEIGHT);
  LCD_1IN3_Display((UWORD *)fb);
  // Fade the backlight in over ~300ms, then hold at splash brightness for
  // the rest of a ~2s total on-screen time before the dashboard takes over.
  constexpr uint8_t kSplashBacklightPercent = 60;  // matches dashboard level
  constexpr uint32_t kSplashFadeInMs = 300;
  constexpr uint8_t kFadeSteps = 20;
  for (uint8_t i = 1; i <= kFadeSteps; i++) {
    gamepi_lcd_backlight((uint8_t)(kSplashBacklightPercent * i / kFadeSteps));
    sleep_ms(kSplashFadeInMs / kFadeSteps);
  }
  sleep_ms(2000 - kSplashFadeInMs);
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
        s.playing != drawn.playing) {
      dirty[W_TOP] = true;
    }
    if (strcmp(s.sample_name, drawn.sample_name) != 0 ||
        s.sample_idx != drawn.sample_idx ||
        s.sample_count != drawn.sample_count) {
      dirty[W_NAME] = true;
    }
    if (memcmp(s.leds, drawn.leds, sizeof(s.leds)) != 0 ||
        s.retrig_leds_mask != drawn.retrig_leds_mask) {
      dirty[W_WAVE] = true;
    }
    if (s.wave_playhead_col != drawn.wave_playhead_col &&
        time_us_64() - wave_playhead_mark_us >= 40000) {
      // Playhead motion alone redraws at most ~25 Hz -- matches
      // flush_allowed()'s own global throttle, so this floor no longer adds
      // extra lag on top of it (was 100ms/~10Hz; measured on hardware as a
      // perceptible playhead-vs-audio delay, tightened here). Still bounded:
      // without this the wave zone would dirty every tick and, even at
      // lowest priority, consume a flush slot every time nothing else
      // changed.
      wave_playhead_mark_us = time_us_64();
      dirty[W_WAVE] = true;
    }
    if (s.mode != drawn.mode) {
      dirty[W_BARA] = true;
      dirty[W_BARB] = true;
      dirty[W_DOTS] = true;
    }
    if (s.knob_a != drawn.knob_a) dirty[W_BARA] = true;
    if (s.knob_b != drawn.knob_b) dirty[W_BARB] = true;
    // Modo 0 Function A depende de sample_idx/sample_count (barra
    // segmentada), no directamente de knob_a -- un cambio de sample sin
    // cambio de knob_a bruto (redondeo de la división entera) igual debe
    // redibujar.
    if (s.sample_idx != drawn.sample_idx ||
        s.sample_count != drawn.sample_count) {
      dirty[W_BARA] = true;
    }
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
    dirty[W_BARA] = true;
    dirty[W_BARB] = true;
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
  // El bitmap ya cubre el rect completo (kOverlay.w x kOverlay.h) con su propio
  // relleno + borde -- no hace falta un Paint_ClearWindows previo.
  Paint_DrawImage((const unsigned char *)kSdOverlayFrame, kOverlay.x, kOverlay.y,
                  kOverlay.w, kOverlay.h);
}

static uint16_t centered_x(const char *txt, uint16_t glyph_w) {
  uint16_t w = (uint16_t)(strlen(txt) * glyph_w);
  return (uint16_t)(kOverlay.x + (kOverlay.w > w ? (kOverlay.w - w) / 2 : 0));
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
  overlay_show_panel(true);  // persistent, mismo criterio que sd_panel_title()
  char idx[8];
  snprintf(idx, sizeof(idx), "%02lu/%02lu", (unsigned long)(index + 1),
           (unsigned long)count);
  // Posición y tamaño de esta franja y las 3 de abajo: coordenadas absolutas
  // de MODE_SD_OVERLAY.txt (mismo criterio que kOverlay/kSdOverlayFrame).
  draw_digit_string(89, 72, idx, kBankDigits, kBankSlash, 7, 15, false);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 57),
                is_active ? COL_GREEN : COL_PINK);
  // Ícono en vez de texto para "L: ciclar" -- el rol de L quedaba poco claro
  // mostrando solo el hint de R durante pruebas de hardware (ver historial).
  Paint_DrawImage((const unsigned char *)kSdLCycle, 52, 138, 141, 15);
  draw_truncated(is_active ? "Cargado (banco activo)" : "Mantener R: cargar",
                (uint16_t)(kOverlay.y + 102), COL_GRAY);
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
