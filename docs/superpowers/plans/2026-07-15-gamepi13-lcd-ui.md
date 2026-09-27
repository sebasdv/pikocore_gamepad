# UI LCD del GamePi13 (Fase 2) — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard en el LCD ST7789 240×240 del GamePi13 (BPM, sample, 8 LEDs virtuales, modo con barras A/B) + overlay temporal al ajustar parámetros, sin afectar el audio ni el build original.

**Architecture:** Render en core0 dentro del lazo de control de 250 Hz existente, con dirty-rect: un widget por tick se redibuja en un framebuffer estático y se envía solo su ventana por SPI1 a 31.25 MHz. Driver Waveshare vendorizado casi intacto en `src/gamepi13/lcd/` con un shim `DEV_Config` propio. Todo compilado solo bajo `PIKO_GAMEPI13`.

**Tech Stack:** pico-sdk 2.1.1, C/C++17, driver ST7789 + GUI_Paint de Waveshare (vendorizado), SPI1, PWM backlight.

**Spec:** `docs/superpowers/specs/2026-07-15-gamepi13-lcd-ui-design.md` (aprobado). Rama de trabajo: `port/rp2350-gamepi13` (continuar ahí, Fase 1 ya mergeada en esa rama).

---

## Contexto para quien ejecuta (léelo completo antes de empezar)

### Entorno de build (Windows, ya establecido en Fase 1 — usar tal cual)

Plain `cmake/make` NO funciona en esta máquina. Receta obligatoria (Bash tool = Git Bash, NO WSL). Para reconstruir un build dir ya configurado:

```bash
cat > /c/pikocore-main/rebuild_TAG.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 (
  echo VCVARSALL_FAILED
  exit /b 1
)
cd /d C:\pikocore-main\BUILDDIR
C:\dtmake\make.exe -j4
if errorlevel 1 (
  echo MAKE_FAILED
  exit /b 1
)
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_TAG.bat"
```

`BUILDDIR` = `build` (original) o `build-gamepi` (GamePi13). `TAG` = nombre distinto por invocación. `C:\dtmake\make.exe` ya existe. Última línea `MAKE_OK` = éxito. Si se modifica `CMakeLists.txt`, el make regenera cmake solo (los build dirs ya están configurados); si el cache se corrompe, reconfigurar agregando antes del make la línea:
`"C:\Program Files\CMake\bin\cmake.exe" -G "MinGW Makefiles" -DCMAKE_MAKE_PROGRAM="C:/dtmake/make.exe" -DPICO_SDK_PATH=../pico-sdk ..` (agregar `-DPIKO_GAMEPI13=ON` para build-gamepi). Borrar los `.bat` temporales al terminar.

### Gotchas del driver Waveshare (descubiertos leyendo el código — NO redescubrir)

1. **`LCD_1IN3_Clear()` aloca `UWORD Image[240*240]` (115 KB) EN EL STACK** (`LCD_1in3.c:236`) — reventaría el stack de core0. **Prohibido llamarla.** Para limpiar: `Paint_Clear()` sobre el framebuffer + `LCD_1IN3_Display(fb)`.
2. **`LCD_1IN3_DisplayWindows` tiene un off-by-one**: `SetWindows` programa una ventana de `Yend-Ystart` filas pero el loop `for (j = Ystart; j < Yend - 1; j++)` envía una fila menos → la última fila queda sin actualizar. Se parchea en Task 1 (cambio de 1 carácter, documentado).
3. **Orden de bytes**: con `Paint_SetScale(65)`, `Paint_SetPixel` escribe big-endian (`Image[Addr]=Color>>8; Image[Addr+1]=Color&0xff`, `GUI_Paint.c:185-188`) y `LCD_1IN3_Display/DisplayWindows` mandan los bytes crudos → **las constantes RGB565 normales funcionan sin swap**. (Solo `LCD_1IN3_Clear` hace swap manual porque no usa Paint — y no la usamos.)
4. `Paint_DrawChar/DrawString_EN(x, y, str, font, Color_Foreground, Color_Background)` — foreground PRIMERO (verificado en `GUI_Paint.c:457`). Con background ≠ `FONT_BACKGROUND` (WHITE), pinta también los píxeles de fondo del glifo — perfecto para sobreescribir texto viejo pasando `COL_BG`.
5. `Paint_ClearWindows(Xstart, Ystart, Xend, Yend, Color)` — ends exclusivos.
6. Fuentes: Font12=7×12, Font16=11×16, Font20=14×20, Font24=17×24 px por carácter.

### Reglas de la fase

- Todo código nuevo compila SOLO bajo `PIKO_GAMEPI13` (excepto el getter de LEDArray, inofensivo en ambos). El build original (flag OFF) no debe cambiar su comportamiento.
- La UI es no-vital: nada en `ui.*`/`dev_shim.*` puede bloquear indefinidamente ni tocar el audio.
- Cada task termina con AMBOS builds compilando (`MAKE_OK` ×2) y un commit.

---

### Task 1: Vendorizar la librería LCD

**Files:**
- Create: `src/gamepi13/lcd/LCD_1in3.c`, `src/gamepi13/lcd/LCD_1in3.h` (copiados de `Gamepi13-RP2040-Demo/C/lib/LCD/`)
- Create: `src/gamepi13/lcd/GUI_Paint.c`, `src/gamepi13/lcd/GUI_Paint.h` (de `.../lib/GUI/`)
- Create: `src/gamepi13/lcd/Debug.h` (de `.../lib/Config/`)
- Create: `src/gamepi13/lcd/fonts.h`, `font12.c`, `font16.c`, `font20.c`, `font24.c` (de `.../lib/Fonts/`)

- [ ] **Step 1: Copiar los archivos**

```bash
cd /c/pikocore-main
mkdir -p src/gamepi13/lcd
cp Gamepi13-RP2040-Demo/C/lib/LCD/LCD_1in3.c src/gamepi13/lcd/
cp Gamepi13-RP2040-Demo/C/lib/LCD/LCD_1in3.h src/gamepi13/lcd/
cp Gamepi13-RP2040-Demo/C/lib/GUI/GUI_Paint.c src/gamepi13/lcd/
cp Gamepi13-RP2040-Demo/C/lib/GUI/GUI_Paint.h src/gamepi13/lcd/
cp Gamepi13-RP2040-Demo/C/lib/Config/Debug.h src/gamepi13/lcd/
cp Gamepi13-RP2040-Demo/C/lib/Fonts/fonts.h src/gamepi13/lcd/
cp Gamepi13-RP2040-Demo/C/lib/Fonts/font12.c src/gamepi13/lcd/
cp Gamepi13-RP2040-Demo/C/lib/Fonts/font16.c src/gamepi13/lcd/
cp Gamepi13-RP2040-Demo/C/lib/Fonts/font20.c src/gamepi13/lcd/
cp Gamepi13-RP2040-Demo/C/lib/Fonts/font24.c src/gamepi13/lcd/
```

- [ ] **Step 2: Parche 1 — include plano de fonts en `GUI_Paint.h`**

En `src/gamepi13/lcd/GUI_Paint.h` línea 5, cambiar:

```c
#include "../Fonts/fonts.h"
```

por:

```c
#include "fonts.h"  // vendored flat; original was ../Fonts/fonts.h
```

- [ ] **Step 3: Parche 2 — off-by-one de `DisplayWindows` en `LCD_1in3.c`**

En `src/gamepi13/lcd/LCD_1in3.c` (~línea 278), cambiar:

```c
    for (j = Ystart; j < Yend - 1; j++) {
```

por:

```c
    // Upstream bug: SetWindows programs Yend-Ystart rows but this loop sent
    // one row less, leaving the last window row stale. Yend is exclusive.
    for (j = Ystart; j < Yend; j++) {
```

- [ ] **Step 4: Verificar que los font .c usan include plano**

```bash
head -40 src/gamepi13/lcd/font12.c | grep -n include
```

Expected: `#include "fonts.h"` (ya son planos en origen). Si alguno incluyera otra ruta, ajustarlo a `"fonts.h"`.

- [ ] **Step 5: Commit**

```bash
git add src/gamepi13/lcd/
git commit -m "feat: vendorizar driver LCD ST7789 + GUI_Paint de Waveshare para GamePi13"
```

(No se compila aún — el wiring de CMake llega en Task 4; estos archivos no afectan a ningún build todavía.)

---

### Task 2: Pines LCD en `hw_gamepi13.h` + shim `DEV_Config`

**Files:**
- Modify: `src/hw_gamepi13.h` (agregar bloque LCD al final)
- Create: `src/gamepi13/lcd/DEV_Config.h` (shim — REEMPLAZA al del demo, no se copia el original)
- Create: `src/gamepi13/dev_shim.c`

- [ ] **Step 1: Agregar pines LCD a `src/hw_gamepi13.h`** (al final del archivo)

```cpp

// LCD ST7789 1.3" 240x240 on SPI1 (Fase 2)
// Pins verified against Gamepi13-RP2040-Demo/C/lib/Config/DEV_Config.c:162-171.
#define GAMEPI_LCD_CS_PIN 8
#define GAMEPI_LCD_CLK_PIN 10
#define GAMEPI_LCD_MOSI_PIN 11
#define GAMEPI_LCD_DC_PIN 25
#define GAMEPI_LCD_RST_PIN 27
#define GAMEPI_LCD_BL_PIN 7  // backlight, PWM
```

- [ ] **Step 2: Crear `src/gamepi13/lcd/DEV_Config.h`** (mismo nombre que el original para que `LCD_1in3.c`/`GUI_Paint.c` compilen sin tocar sus `#include`; contenido nuestro, mínimo)

```c
#pragma once
// Shim replacing Waveshare's DEV_Config for the pikocore GamePi13 build.
// Provides only what LCD_1in3.c / GUI_Paint.c actually use. No i2c, no
// stdio_init_all, no DEV_Module_Init — init lives in gamepi_lcd_dev_init().
#include <stdint.h>

#include "hardware/spi.h"
#include "pico/stdlib.h"

#ifdef __cplusplus
extern "C" {
#endif

#define UBYTE uint8_t
#define UWORD uint16_t
#define UDOUBLE uint32_t

extern int EPD_RST_PIN;
extern int EPD_DC_PIN;
extern int EPD_CS_PIN;
extern int EPD_BL_PIN;

void DEV_Digital_Write(UWORD Pin, UBYTE Value);
UBYTE DEV_Digital_Read(UWORD Pin);
void DEV_SPI_WriteByte(UBYTE Value);
void DEV_SPI_Write_nByte(uint8_t *pData, uint32_t Len);
void DEV_Delay_ms(UDOUBLE xms);
void DEV_Delay_us(UDOUBLE xus);

// pikocore-specific (called from ui.cpp, not from vendored code):
void gamepi_lcd_dev_init(void);
void gamepi_lcd_backlight(uint8_t percent);  // 0-100

#ifdef __cplusplus
}
#endif
```

- [ ] **Step 3: Crear `src/gamepi13/dev_shim.c`**

```c
// Hardware shim for the vendored Waveshare LCD driver (GamePi13 build).
#include "lcd/DEV_Config.h"

#include "hardware/pwm.h"

#include "../hw_gamepi13.h"

#define GAMEPI_SPI spi1

int EPD_RST_PIN = GAMEPI_LCD_RST_PIN;
int EPD_DC_PIN = GAMEPI_LCD_DC_PIN;
int EPD_CS_PIN = GAMEPI_LCD_CS_PIN;
int EPD_BL_PIN = GAMEPI_LCD_BL_PIN;

void DEV_Digital_Write(UWORD Pin, UBYTE Value) { gpio_put(Pin, Value); }
UBYTE DEV_Digital_Read(UWORD Pin) { return gpio_get(Pin); }

void DEV_SPI_WriteByte(UBYTE Value) {
  spi_write_blocking(GAMEPI_SPI, &Value, 1);
}
void DEV_SPI_Write_nByte(uint8_t *pData, uint32_t Len) {
  spi_write_blocking(GAMEPI_SPI, pData, Len);
}

void DEV_Delay_ms(UDOUBLE xms) { sleep_ms(xms); }
void DEV_Delay_us(UDOUBLE xus) { sleep_us(xus); }

void gamepi_lcd_dev_init(void) {
  gpio_init(GAMEPI_LCD_RST_PIN);
  gpio_set_dir(GAMEPI_LCD_RST_PIN, GPIO_OUT);
  gpio_init(GAMEPI_LCD_DC_PIN);
  gpio_set_dir(GAMEPI_LCD_DC_PIN, GPIO_OUT);
  gpio_init(GAMEPI_LCD_CS_PIN);
  gpio_set_dir(GAMEPI_LCD_CS_PIN, GPIO_OUT);
  gpio_put(GAMEPI_LCD_CS_PIN, 1);
  gpio_put(GAMEPI_LCD_DC_PIN, 0);

  spi_init(GAMEPI_SPI, 31250 * 1000);  // 31.25 MHz; bajar a 15625*1000 si hay artefactos
  gpio_set_function(GAMEPI_LCD_CLK_PIN, GPIO_FUNC_SPI);
  gpio_set_function(GAMEPI_LCD_MOSI_PIN, GPIO_FUNC_SPI);

  // Backlight PWM (slice de GP7 = 3; no colisiona con el audio en GP18 = slice 1)
  gpio_set_function(GAMEPI_LCD_BL_PIN, GPIO_FUNC_PWM);
  uint slice = pwm_gpio_to_slice_num(GAMEPI_LCD_BL_PIN);
  pwm_config cfg = pwm_get_default_config();
  pwm_config_set_clkdiv(&cfg, 4.f);
  pwm_init(slice, &cfg, true);
  gamepi_lcd_backlight(0);  // apagado hasta después del splash
}

void gamepi_lcd_backlight(uint8_t percent) {
  if (percent > 100) percent = 100;
  pwm_set_gpio_level(GAMEPI_LCD_BL_PIN,
                     (uint16_t)((uint32_t)percent * 65535u / 100u));
}
```

- [ ] **Step 4: Commit**

```bash
git add src/hw_gamepi13.h src/gamepi13/lcd/DEV_Config.h src/gamepi13/dev_shim.c
git commit -m "feat: shim DEV_Config y pines LCD para el driver vendorizado"
```

---

### Task 3: `ui.h` + `ui.cpp` (init, splash, flush; tick/overlay como stubs funcionales mínimos)

**Files:**
- Create: `src/gamepi13/ui.h`
- Create: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Crear `src/gamepi13/ui.h`**

```cpp
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
```

- [ ] **Step 2: Crear `src/gamepi13/ui.cpp`** (esta task: init+splash+flush+esqueleto; los widgets del dashboard se completan en Task 5 y el overlay en Task 6 — los cuerpos que aquí quedan vacíos son intencionales y compilan)

```cpp
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

// ---- widget draw functions: bodies filled in Task 5 ----
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
  // diffing vs. last drawn state: filled in Task 5
  // overlay TTL handling: filled in Task 6
  (void)s;
}

void gamepi_ui_overlay_mode(uint8_t mode) { (void)mode; }  // Task 6

void gamepi_ui_overlay_param(uint8_t mode, bool is_b, uint16_t val) {  // Task 6
  (void)mode;
  (void)is_b;
  (void)val;
}
```

Nota: `dev_shim`'s `gamepi_lcd_dev_init`/`gamepi_lcd_backlight` se declaran en `lcd/DEV_Config.h`, que ya llega vía los includes de `LCD_1in3.h`/`GUI_Paint.h` (ambos lo incluyen).

Nota 2: hasta que Task 5 rellene los widgets, el compilador emitirá warnings de estáticos sin usar (`kModeA`, `pct`, `flush`, etc.) en los builds de Task 4. **Es esperado y transitorio — NO "arreglarlo"** agregando casts ni borrando símbolos; desaparecen solos en Task 5.

- [ ] **Step 3: Commit**

```bash
git add src/gamepi13/ui.h src/gamepi13/ui.cpp
git commit -m "feat: nucleo de la UI LCD (init, splash, flush, esqueleto de widgets)"
```

---

### Task 4: Wiring de CMake + llamada a `gamepi_ui_init()` — primer build completo

**Files:**
- Modify: `CMakeLists.txt` (dentro del bloque `if(PIKO_GAMEPI13)` existente tras `include(target_compile_definitions.cmake)`)
- Modify: `src/main.cpp` (include + llamada a init)

- [ ] **Step 1: Ampliar el bloque `if(PIKO_GAMEPI13)` en `CMakeLists.txt`**

Buscar:

```cmake
if(PIKO_GAMEPI13)
	target_compile_definitions(${PROJECT_NAME} PRIVATE PIKO_GAMEPI13=1)
endif()
```

Reemplazar por:

```cmake
if(PIKO_GAMEPI13)
	target_compile_definitions(${PROJECT_NAME} PRIVATE PIKO_GAMEPI13=1)
	target_sources(${PROJECT_NAME} PRIVATE
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/LCD_1in3.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/GUI_Paint.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/font12.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/font16.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/font20.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/font24.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/dev_shim.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/ui.cpp
	)
	target_include_directories(${PROJECT_NAME} PRIVATE
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd
	)
	target_link_libraries(${PROJECT_NAME} hardware_spi)
endif()
```

- [ ] **Step 2: Include y llamada en `src/main.cpp`**

Tras el bloque existente `#if PIKO_GAMEPI13 / #include "hw_gamepi13.h" ...` (en la zona de defines de pines, ~línea 50), agregar dentro de ese mismo `#if` (después de `#define WS2812_ENABLED 0`):

```cpp
#include "gamepi13/ui.h"
```

En `main()`, justo DESPUÉS de `btn_r.Init(GAMEPI_BTN_R, 10);` (dentro del `#if PIKO_GAMEPI13` de inicialización de knobs, Task 5 de Fase 1), agregar:

```cpp
  gamepi_ui_init();
```

(Queda antes de habilitar la interrupción de audio — el `sleep_ms(600)` del splash no interfiere con nada.)

- [ ] **Step 3: Build de ambas variantes**

Usar la receta de build del contexto con `BUILDDIR=build-gamepi` y luego `BUILDDIR=build`.
Expected: `MAKE_OK` ×2. El build original no lista los archivos nuevos (flag OFF ⇒ ni se compilan).

- [ ] **Step 4: Commit**

```bash
git add CMakeLists.txt src/main.cpp
git commit -m "feat: wiring CMake de la UI LCD y llamada a gamepi_ui_init"
```

---

### Task 5: Widgets del dashboard + diffing en `tick` + integración de estado en `main.cpp`

**Files:**
- Modify: `doth/ledarray.h` (getter de 1 línea)
- Modify: `src/gamepi13/ui.cpp` (reemplazar `draw_widget` stub y `gamepi_ui_tick`)
- Modify: `src/main.cpp` (llenar `GamepiUiState` y llamar `gamepi_ui_tick` en el lazo de 250 Hz)

- [ ] **Step 1: Getter en `doth/ledarray.h`**

Después del método `LedUpdate` (línea ~25), agregar:

```cpp
  uint8_t Get(uint8_t i) { return vals[i]; }
```

(Se compila en ambas variantes; es un accessor puro sin efectos.)

- [ ] **Step 2: Reemplazar en `src/gamepi13/ui.cpp` el stub `draw_widget` completo por:**

```cpp
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
  Paint_DrawString_EN(8, 32, s.sample_name, &Font12, COL_GRAY, COL_BG);
}

static void draw_leds(const GamepiUiState &s) {
  clear_zone(kRect[W_LEDS]);
  for (uint8_t i = 0; i < 8; i++) {
    uint16_t x = (uint16_t)(10 + i * 28);  // 8 x 24px + 4px gap = 220 wide
    UWORD col = COL_DARK;
    if (s.leds[i] >= 128) {
      col = COL_ORANGE;
    } else if (s.leds[i] >= 8) {
      col = COL_ORANGE_DIM;
    }
    Paint_DrawRectangle(x, 62, (uint16_t)(x + 23), 85, col, DOT_PIXEL_1X1,
                        DRAW_FILL_FULL);
  }
}

static void draw_modename(const GamepiUiState &s) {
  clear_zone(kRect[W_MODENAME]);
  Paint_DrawString_EN(8, 116, kModeA[s.mode & 7], &Font16, COL_PINK, COL_BG);
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
  for (uint8_t i = 0; i < 8; i++) {
    UWORD col = (i == (s.mode & 7)) ? COL_PINK : COL_DARK;
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
    case W_LEDS:
      draw_leds(s);
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
```

- [ ] **Step 3: Reemplazar `gamepi_ui_tick` en `src/gamepi13/ui.cpp` por:**

```cpp
void gamepi_ui_tick(const GamepiUiState &s) {
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
    if (memcmp(s.leds, drawn.leds, sizeof(s.leds)) != 0) dirty[W_LEDS] = true;
    if (s.mode != drawn.mode) {
      dirty[W_MODENAME] = true;
      dirty[W_DOTS] = true;
    }
    if (s.knob_a != drawn.knob_a) dirty[W_BARA] = true;
    if (s.knob_b != drawn.knob_b) dirty[W_BARB] = true;
  }
  drawn = s;
  have_drawn = true;

  // Overlay TTL handling arrives in Task 6; without overlay, just flush
  // at most ONE dirty widget per tick to bound SPI blocking time.
  if (overlay_on) {
    if (overlay_ttl > 0) {
      overlay_ttl--;
    } else {
      overlay_on = false;
      Paint_ClearWindows(kOverlay.x, kOverlay.y,
                         (uint16_t)(kOverlay.x + kOverlay.w),
                         (uint16_t)(kOverlay.y + kOverlay.h), COL_BG);
      flush(kOverlay);
      dirty[W_LEDS] = true;      // zones the overlay covered
      dirty[W_MODENAME] = true;
      dirty[W_BARA] = true;
    }
    if (overlay_on) return;  // never repaint background under the overlay
  }

  for (uint8_t i = 0; i < W_COUNT; i++) {
    if (dirty[i]) {
      draw_widget(i, s);
      flush(kRect[i]);
      dirty[i] = false;
      break;
    }
  }
}
```

- [ ] **Step 4: Integración en `src/main.cpp`** — en el lazo de control, dentro de `if (clock_ms % 16 == 0) {`, inmediatamente DESPUÉS del bloque `#if PIKO_GAMEPI13` de manejo de Select/Start/L/R (Task 5 de Fase 1) y ANTES del comentario `// adc reading`, insertar:

```cpp
#if PIKO_GAMEPI13
      {
        GamepiUiState uis;
        uis.bpm = bpm_set;
        uis.clock_src =
            clock_input_ittybittymidi ? 2 : ((is_syncing && do_sync_play) ? 1 : 0);
        uint16_t ui_scount = (uint16_t)piko_audio_sample_count();
        uis.sample_count = ui_scount;
        uis.sample_idx = ui_scount ? (uint16_t)(sample_set % ui_scount) : 0;
        if (ui_scount > 0) {
          const char *nm = piko_audio_sample(uis.sample_idx).name;
          size_t n = 0;
          while (n < sizeof(uis.sample_name) - 1 && n < 48 && nm[n] != '\0') {
            uis.sample_name[n] = nm[n];
            n++;
          }
          uis.sample_name[n] = '\0';
        } else {
          snprintf(uis.sample_name, sizeof(uis.sample_name), "(sin samples)");
        }
        for (uint8_t j = 0; j < 8; j++) uis.leds[j] = ledarray.Get(j);
        uis.mode = gamepi_selector;
        uis.knob_a = input_knob[1].Value();
        uis.knob_b = input_knob[2].Value();
        gamepi_ui_tick(uis);
      }
#endif
```

- [ ] **Step 5: Build de ambas variantes**

Receta del contexto, `build-gamepi` y `build`. Expected: `MAKE_OK` ×2, sin warnings nuevos del código propio.

- [ ] **Step 6: Commit**

```bash
git add doth/ledarray.h src/gamepi13/ui.cpp src/main.cpp
git commit -m "feat: dashboard LCD con dirty-rect (BPM, sample, LEDs, modo A/B)"
```

---

### Task 6: Overlay temporal + hooks en los handlers de botones

**Files:**
- Modify: `src/gamepi13/ui.cpp` (reemplazar los stubs de overlay)
- Modify: `src/main.cpp` (3 llamadas en el bloque Select/L/R)

- [ ] **Step 1: Reemplazar en `src/gamepi13/ui.cpp` los dos stubs `gamepi_ui_overlay_*` por:**

```cpp
// Draw the overlay panel into fb and flush it. Called from the same 250 Hz
// context as gamepi_ui_tick (all core0) — no concurrency to worry about.
static void overlay_show_panel() {
  overlay_on = true;
  overlay_ttl = OVERLAY_TTL_TICKS;
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
  flush(kOverlay);
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
  flush(kOverlay);
}
```

- [ ] **Step 2: Hooks en `src/main.cpp`** — en el bloque `#if PIKO_GAMEPI13` de Select/Start/L/R (Fase 1), hacer 3 inserciones:

En el handler de Select, después de `input_knob[0].SetBucket(gamepi_selector, 8);`:

```cpp
        gamepi_ui_overlay_mode(gamepi_selector);
```

En el handler de L, después de `input_knob[active_knob].Adjust(-GAMEPI_KNOB_STEP);`:

```cpp
            gamepi_ui_overlay_param(gamepi_selector, active_knob == 2,
                                    input_knob[active_knob].Value());
```

En el handler de R, después de `input_knob[active_knob].Adjust(GAMEPI_KNOB_STEP);`:

```cpp
            gamepi_ui_overlay_param(gamepi_selector, active_knob == 2,
                                    input_knob[active_knob].Value());
```

- [ ] **Step 3: Build de ambas variantes**

Receta del contexto. Expected: `MAKE_OK` ×2.

Nota de presupuesto: el flush del overlay (200×112 px ≈ 45 KB ≈ 11 ms a 31.25 MHz) se dispara como mucho cada 100 ms manteniendo L/R (repeat de Fase 1) — el lazo de control pierde ~2 ticks por refresco, el debounce de botones lo absorbe y el audio (IRQ) no se entera. Si en hardware se notara lag, la optimización documentada es flushear solo la franja del valor+barra en los repeats.

- [ ] **Step 4: Commit**

```bash
git add src/gamepi13/ui.cpp src/main.cpp
git commit -m "feat: overlay temporal de modo/parametro en el LCD"
```

---

### Task 7: Verificación en hardware (requiere al usuario con la placa)

**Files:** ninguno

- [ ] **Step 1: Grabar** `build-gamepi/pikocore.uf2` (BOOT + USB, copiar a la unidad `RP2350`).

- [ ] **Step 2: Checklist** (si algo falla → skill `superpowers:systematic-debugging`, no parchar a ciegas):

1. Splash "pikocore / GamePi13" ~0.6 s y luego dashboard con backlight encendido.
2. **Orientación**: el texto se lee derecho con el GamePi13 en la mano (botones abajo/laterales). Si sale rotado/espejado: cambiar `GAMEPI_LCD_ROTATE` en `ui.cpp` (ROTATE_90/180/270) y/o el argumento de `LCD_1IN3_Init` (`HORIZONTAL`↔`VERTICAL`), recompilar, regrabar. Documentar el valor final.
3. LEDs virtuales: se mueven con el beat (mismo patrón que la Fase 1 mostraba solo por audio).
4. BPM correcto (165 por defecto); "NN/MM" y nombre del sample correctos tras subir samples con la web app (`npm --prefix web run dev`).
5. Select → overlay "MODO n" con nombres A/B; desaparece ~1 s.
6. L/R (y Start+L/R) → overlay de parámetro con % moviéndose; el dashboard vuelve al soltar.
7. **Regresión crítica**: el audio suena idéntico a Fase 1 — sin clicks/glitches nuevos al refrescar la pantalla, botones musicales y knobs virtuales intactos, guardar/cargar funciona.
8. Colores: si se ven invertidos (fondo blanco/colores raros), reportar — sería un tema de byte-order del panel, y el fix es un swap en `Paint_SetPixel` scale 65 o en `flush` (no adivinar: confirmar primero cuál).

- [ ] **Step 3: Registrar resultados y cualquier ajuste de rotación en el commit siguiente.**

---

### Task 8: Documentación

**Files:**
- Modify: `README-GAMEPI13.md`

- [ ] **Step 1: Actualizar la sección de pines y agregar sección de pantalla.** Reemplazar en `README-GAMEPI13.md` la sección `## pines` completa por:

```markdown
## pantalla

Dashboard 240×240: BPM + fuente de clock, sample (número y nombre), barra de
8 LEDs virtuales (reemplaza los LED físicos del pikocore original), modo del
selector con barras A/B, y puntos de modo. Al presionar Select o L/R aparece
un overlay grande con el modo/parámetro que se desvanece ~1 s después.

## pines

Audio GP18 (parlante/jack del HAT) · LED de beat GP28 · clock in GP22 ·
trigger out GP12 · LCD: SPI1 (CLK GP10, MOSI GP11, CS GP8, DC GP25,
RST GP27, backlight GP7) · resto: ver `src/hw_gamepi13.h`.

Pendiente (Fase 2.1): waveform con playhead, iconos de estado (mute/seq/lock).
```

(Eliminar del texto viejo la frase "La UI en el LCD ... es la fase 2 del port" que queda obsoleta.)

- [ ] **Step 2: Commit**

```bash
git add README-GAMEPI13.md
git commit -m "docs: documentar la UI LCD del GamePi13"
```

---

## Fuera de alcance (Fase 2.1, plan futuro)

- Waveform con playhead (requiere decimado del sample desde flash y probablemente render DMA).
- Iconos de estado (mute/seq/lock) en la barra superior.
- Optimización de flush parcial del overlay (solo si se observa lag en hardware).
