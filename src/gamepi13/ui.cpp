#include "ui.h"

#include <stdio.h>
#include <string.h>

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

// Rotation is validated on hardware (plan Task 8); adjust here if mirrored.
#define GAMEPI_LCD_ROTATE ROTATE_0

static UBYTE fb[LCD_1IN3_WIDTH * LCD_1IN3_HEIGHT * 2];  // 115 200 B static

struct Rect {
  uint16_t x, y, w, h;
};

// Widget zones (full-width strips; y per approved spec layout)
enum {
  W_TOP = 0,   // BPM + clock src | "NN/MM"
  W_NAME,      // sample name
  W_LEDS,      // 8 virtual LEDs
  W_MODENAME,  // mode name
  W_BARA,      // bar A + label
  W_BARB,      // bar B + label
  W_DOTS,      // 8 mode dots
  W_COUNT
};

static const Rect kRect[W_COUNT] = {
    {0, 0, 240, 28},    // W_TOP
    {0, 28, 240, 24},   // W_NAME
    {0, 52, 240, 44},   // W_LEDS
    {0, 112, 240, 24},  // W_MODENAME
    {0, 136, 240, 32},  // W_BARA
    {0, 168, 240, 32},  // W_BARB
    {0, 208, 240, 20},  // W_DOTS
};

static bool dirty[W_COUNT];
static GamepiUiState drawn;
static bool have_drawn = false;

static const Rect kOverlay = {20, 64, 200, 112};
static bool overlay_on = false;
static uint16_t overlay_ttl = 0;
#define OVERLAY_TTL_TICKS 250  // ~1 s at 250 Hz

static const char *kModeA[8] = {"SAMPLE",     "FILTRO",     "GATE",
                                "PROB SALTO", "PROB TUNEL", "SEC GRABAR",
                                "GUARDAR",    "VOLUMEN"};
static const char *kModeB[8] = {"BREAK FX",    "STRETCH",      "PROB GATE",
                                "PROB RETRIG", "PROB REVERSA", "SEC PLAY",
                                "CARGAR",      "-"};

// Flush one rect of the framebuffer to the panel. DisplayWindows takes
// exclusive ends and assumes full-frame stride (patched off-by-one in Task 1).
static void flush(const Rect &r) {
  LCD_1IN3_DisplayWindows(r.x, r.y, (uint16_t)(r.x + r.w),
                          (uint16_t)(r.y + r.h), (UWORD *)fb);
}

static uint8_t pct(uint16_t v) { return (uint8_t)((uint32_t)v * 100u / 4095u); }

// ---- widget draw functions: bodies filled in a later task ----
static void draw_widget(uint8_t i, const GamepiUiState &s) {
  (void)i;
  (void)s;
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
  // diffing vs. last drawn state: filled in a later task
  // overlay TTL handling: filled in a later task
  (void)s;
}

void gamepi_ui_overlay_mode(uint8_t mode) { (void)mode; }  // later task

void gamepi_ui_overlay_param(uint8_t mode, bool is_b, uint16_t val) {  // later task
  (void)mode;
  (void)is_b;
  (void)val;
}
