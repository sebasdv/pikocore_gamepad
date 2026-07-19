# Dashboard con bitmaps de Lopaka (modo 0) — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el dashboard de texto/formas por los bitmaps diseñados en Lopaka
(`MODE_0.txt` + los dos sets de dígitos), para los elementos compartidos entre los 9
modos y, específicamente para el modo 0, las etiquetas "SAMPLE"/"BREAK FX".

**Architecture:** Todos los assets se vendorizan en un archivo nuevo,
`src/gamepi13/ui_bitmaps.h` (datos + dos helpers de blit nuevos), extraídos
mecánicamente con `sed`/`cat` desde los 3 `.txt` (nunca retipeados a mano — ya
verificado que los 41 arrays cuentan exacto contra su ancho×alto declarado).
`ui.cpp` se modifica para dibujar estos bitmaps en las zonas ya existentes del sistema
`kRect[]`/`dirty[]`, sin tocar el mecanismo de throttle/redibujado. La lógica dinámica
de la waveform no cambia.

**Tech Stack:** C/C++17, `GUI_Paint` (Waveshare, ya vendorizado), RGB565.

**Spec:** `docs/superpowers/specs/2026-07-19-dashboard-bitmap-mode0-design.md`
(aprobado). Rama: `port/rp2350-gamepi13`.

---

## Contexto para quien ejecuta (léelo completo antes de empezar)

### Entorno de build (Windows)

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

`BUILDDIR` = `build-gamepi` (único build que compila `ui.cpp` — este feature es 100%
exclusivo de GamePi13). El build original (`build`) no toca ninguno de estos archivos,
pero confirmar igual que sigue compilando en Task 3 (única tarea que toca `main.cpp`,
código potencialmente compartido). Ningún task de este plan cambia `CMakeLists.txt` —
`ui_bitmaps.h` es un header incluido solo desde `ui.cpp`, ya en el build.

### Hallazgos que hay que respetar (verificados en código, no redescubrir)

1. **Los 3 archivos fuente** (`src/gamepi13/MODE_0.txt`, `"Digits for BPM.txt"`,
   `"Digits for bank files.txt"`) contienen 41 arrays en total (10 dígitos BPM + 10
   dígitos banco + 19 assets de `MODE_0.txt` en `uint16_t`/RGB565, + 2 en
   `unsigned char`/1bpp para play/stop). **Ya verificado**: cada array cuenta EXACTO
   contra el ancho×alto de su propio `tft.pushImage`/`tft.drawBitmap` — la extracción
   mecánica vía `sed` (Task 1) reproduce esto sin riesgo de transcripción.
2. **`PROGMEM` se quita siempre** (no existe en este target) — mismo criterio que
   `splash_logo.h`.
3. **`Paint_DrawImage()`** ya usado para la splash acepta directamente estos arrays
   `uint16_t` vía cast `(const unsigned char*)`, sin conversión — mismo razonamiento de
   endianness ya validado ahí.
4. **`GUI_Paint` no tiene equivalente a `tft.drawBitmap`** (monocromo, 1bpp, un color de
   relleno) — hace falta una función nueva, `Paint_DrawMonoBitmap` (Task 1).
5. **`Paint_SetPixel()` ya descarta silenciosamente coordenadas fuera de rango**
   (`if(Xpoint > Paint.Width || Ypoint > Paint.Height) return;`, `GUI_Paint.c:116`) —
   si el ancho real de un número de 3 dígitos empujara el cálculo de alineado a la
   derecha por debajo de `x=0` (un `uint16_t` daría *underflow*, un número enorme), esas
   columnas de más a la izquierda simplemente no se dibujan (recortadas), sin crashear
   ni corromper memoria. Caso extremo aceptado, no se agrega clamping extra.
6. **El "BPM_Slash" del mockup NO va entre los dos íconos de reloj** (así aparece en
   `MODE_0.txt` porque Lopaka no simula estados condicionales — mostró ambos íconos de
   referencia). En tiempo real va SIEMPRE entre los dígitos de BPM y el ícono de reloj
   que corresponda (el que esté activo).
7. **El campo `playing` no existe todavía en `GamepiUiState`** — hace falta agregarlo
   (Task 2) y poblarlo desde `do_mute` (global ya existente en `main.cpp:177`,
   `bool do_mute = false;`) como `!do_mute`.
8. **`W_MODENAME` desaparece como zona propia** — el diseño de Lopaka no tiene una
   etiqueta de "modo" genérica separada; en su lugar, cada barra (Function A/B) trae su
   propia etiqueta (`SAMPLE_WORD`/`BREAK_FX_WORD` para modo 0, texto para el resto) justo
   antes de la barra. Se fusiona en `W_BARA`/`W_BARB` (Task 3).
9. **El overlay temporal** (`kOverlay = {20,64,200,112}`, cubre y64-176) con los nuevos
   rects se solapa también con `W_BARB` (antes solo tocaba una franja mínima de 8px) —
   la lista de "zonas a redibujar al cerrar el overlay" debe incluir `W_BARB` ahora
   (Task 3), o queda contenido viejo del overlay pegado en pantalla.

### Reglas de la fase

- Todo lo nuevo vive en `src/gamepi13/ui.cpp`/`ui_bitmaps.h`/`ui.h`, ya exclusivos de
  GamePi13 — nada de esto se compila en el build original salvo el campo nuevo de
  `GamepiUiState`/`main.cpp` (Task 2), que sí es código compartido y debe confirmarse
  sin cambios de comportamiento en el build original.
- Cada task termina con `build-gamepi` compilando (`MAKE_OK`) y un commit. Task 2
  también confirma `build` (original).

---

### Task 1: Vendorizar bitmaps + dígitos + helpers de dibujo

**Files:**
- Create: `src/gamepi13/ui_bitmaps.h`

- [ ] **Step 1: Extraer los 41 arrays mecánicamente (sin retipear)**

Desde `C:\pikocore-main\src\gamepi13`, correr:

```bash
cd /c/pikocore-main/src/gamepi13

extract() {
  sed -n "s/.*${2}\[\] = {\(.*\)};.*/\1/p" "$1"
}

{
  echo '// GamePi13 dashboard bitmaps, designed in Lopaka (lopaka.app), exported'
  echo '// for TFT_eSPI/M5/Lovyan and adapted here (PROGMEM dropped, arrays'
  echo '// renamed for clarity -- the originals in MODE_0.txt/"Digits for'
  echo '// BPM.txt"/"Digits for bank files.txt" all used generic names like'
  echo '// image__0_pixels that collide across files).'
  echo '//'
  echo '// All uint16_t arrays are RGB565, consumed via Paint_DrawImage() with a'
  echo '// (const unsigned char*) cast -- verified byte-compatible on this'
  echo '// little-endian target (ARM Cortex-M33), same reasoning as splash_logo.h.'
  echo '// image_play_bits/image_stop_bits are 1bpp packed (MSB first), consumed'
  echo '// via the new Paint_DrawMonoBitmap() instead.'
  echo '//'
  echo '// Pixel counts verified against each source w*h before import (see'
  echo '// docs/superpowers/plans/2026-07-19-dashboard-bitmap-mode0.md Task 1).'
  echo '#pragma once'
  echo '#include <stdint.h>'
  echo ''

  echo '// ---- BPM digits (10, variable width) ----'
  for i in 0 1 2 3 4 5 6 7 8 9; do
    printf 'static const uint16_t kBpmDigit%s[] = {%s};\n' "$i" "$(extract "Digits for BPM.txt" "image__${i}_pixels")"
  done
  echo ''

  echo '// ---- Sample-bank digits (10, variable width) ----'
  for i in 0 1 2 3 4 5 6 7 8 9; do
    printf 'static const uint16_t kBankDigit%s[] = {%s};\n' "$i" "$(extract "Digits for bank files.txt" "image__${i}_pixels")"
  done
  echo ''

  echo '// ---- MODE_0 shared frame assets ----'
  printf 'static const uint16_t kIntClock[] = {%s};\n' "$(extract "MODE_0.txt" "image_Int_clock_pixels")"
  printf 'static const uint16_t kExtClock[] = {%s};\n' "$(extract "MODE_0.txt" "image_Ext_clock_pixels")"
  printf 'static const uint16_t kBpmSlash[] = {%s};\n' "$(extract "MODE_0.txt" "image_BPM_Slash_pixels")"
  printf 'static const uint16_t kBankSlash[] = {%s};\n' "$(extract "MODE_0.txt" "image_file_bank_slash_pixels")"
  printf 'static const uint16_t kFilenameFrame[] = {%s};\n' "$(extract "MODE_0.txt" "image_filename_sample_frame_pixels")"
  printf 'static const uint16_t kWaveformFrame[] = {%s};\n' "$(extract "MODE_0.txt" "image_waveform_frame_pixels")"
  printf 'static const uint16_t kSampleWord[] = {%s};\n' "$(extract "MODE_0.txt" "image_SAMPLE_WORD_pixels")"
  printf 'static const uint16_t kSampleBar[] = {%s};\n' "$(extract "MODE_0.txt" "image_SAMPLE_BAR_pixels")"
  printf 'static const uint16_t kBreakFxWord[] = {%s};\n' "$(extract "MODE_0.txt" "image_BREAK_FX_WORD_pixels")"
  printf 'static const uint16_t kBreakFxBar[] = {%s};\n' "$(extract "MODE_0.txt" "image_BREAK_FX_BAR_pixels")"
  for i in 0 1 2 3 4 5 6 7; do
    printf 'static const uint16_t kModeIcon%s[] = {%s};\n' "$i" "$(extract "MODE_0.txt" "image_M_${i}_pixels")"
  done
  printf 'static const uint16_t kModeIconSd[] = {%s};\n' "$(extract "MODE_0.txt" "image_M_SD_pixels")"
  echo ''
  echo '// ---- play/stop (1bpp mono, MSB first) ----'
  printf 'static const unsigned char kPlayBits[] = {%s};\n' "$(extract "MODE_0.txt" "image_play_bits")"
  printf 'static const unsigned char kStopBits[] = {%s};\n' "$(extract "MODE_0.txt" "image_stop_bits")"
} > ui_bitmaps.h
```

- [ ] **Step 2: Verificar que los 41 arrays cuentan exacto contra su ancho×alto**

```bash
cd /c/pikocore-main/src/gamepi13
python3 - << 'EOF'
import re

expected = {
    'kBpmDigit0': 150, 'kBpmDigit1': 150, 'kBpmDigit2': 150, 'kBpmDigit3': 165,
    'kBpmDigit4': 126, 'kBpmDigit5': 150, 'kBpmDigit6': 150, 'kBpmDigit7': 150,
    'kBpmDigit8': 150, 'kBpmDigit9': 150,
    'kBankDigit0': 84, 'kBankDigit1': 77, 'kBankDigit2': 96, 'kBankDigit3': 96,
    'kBankDigit4': 70, 'kBankDigit5': 99, 'kBankDigit6': 96, 'kBankDigit7': 88,
    'kBankDigit8': 84, 'kBankDigit9': 96,
    'kIntClock': 532, 'kExtClock': 560, 'kBpmSlash': 280, 'kBankSlash': 105,
    'kFilenameFrame': 3820, 'kWaveformFrame': 11520, 'kSampleWord': 1760,
    'kSampleBar': 4800, 'kBreakFxWord': 2380, 'kBreakFxBar': 4800,
    'kModeIcon0': 336, 'kModeIcon1': 336, 'kModeIcon2': 336, 'kModeIcon3': 336,
    'kModeIcon4': 336, 'kModeIcon5': 336, 'kModeIcon6': 336, 'kModeIcon7': 336,
    'kModeIconSd': 651,
    'kPlayBits': 24, 'kStopBits': 24,
}

text = open('ui_bitmaps.h', encoding='utf-8').read()
ok = True
for name, exp in expected.items():
    m = re.search(re.escape(name) + r'\[\] = \{([^}]*)\}', text)
    if not m:
        print(f"MISSING: {name}")
        ok = False
        continue
    count = m.group(1).count(',') + 1 if m.group(1).strip() else 0
    status = "OK" if count == exp else "MISMATCH"
    if status != "OK":
        ok = False
    print(f"{name}: got={count} expected={exp} {status}")
print("ALL OK" if ok else "SOME FAILED")
EOF
```

Expected: `ALL OK`. Si algo da `MISMATCH` o `MISSING`, no seguir — reportar como
BLOCKED, el problema está en el archivo fuente o el comando `extract`, no en este
plan.

- [ ] **Step 3: Agregar las tablas de dígitos, estructuras y helpers de dibujo al
      mismo archivo**

Agregar al final de `src/gamepi13/ui_bitmaps.h` (después del último array,
`kStopBits`):

```cpp

// ---- digit glyph tables (real per-digit width, no fixed grid) ----
struct DigitGlyph {
  const uint16_t *pixels;
  uint8_t w, h;
};

static const DigitGlyph kBpmDigits[10] = {
    {kBpmDigit0, 10, 15}, {kBpmDigit1, 10, 15}, {kBpmDigit2, 10, 15},
    {kBpmDigit3, 11, 15}, {kBpmDigit4, 9, 14},  {kBpmDigit5, 10, 15},
    {kBpmDigit6, 10, 15}, {kBpmDigit7, 10, 15}, {kBpmDigit8, 10, 15},
    {kBpmDigit9, 10, 15},
};

static const DigitGlyph kBankDigits[10] = {
    {kBankDigit0, 7, 12}, {kBankDigit1, 7, 11}, {kBankDigit2, 8, 12},
    {kBankDigit3, 8, 12}, {kBankDigit4, 7, 10}, {kBankDigit5, 9, 11},
    {kBankDigit6, 8, 12}, {kBankDigit7, 8, 11}, {kBankDigit8, 7, 12},
    {kBankDigit9, 8, 12},
};

// ---- optional per-mode Function A/B label bitmap (nullptr = no graphic yet,
// caller falls back to Paint_DrawString_EN with kModeA[mode]/kModeB[mode]) ----
struct ModeLabelBitmap {
  const uint16_t *pixels;
  uint8_t w, h;
};
static const ModeLabelBitmap kSampleWordBitmap = {kSampleWord, 88, 20};
static const ModeLabelBitmap kBreakFxWordBitmap = {kBreakFxWord, 119, 20};
// Index 0 = mode 0 ("SAMPLE"/"BREAK FX"), designed. Indices 1-7: nullptr until
// the user designs those modes' labels in Lopaka (same pattern as the splash
// and the IMU-era MIDI-clock fallback: missing asset -> text, not a blocker).
static const ModeLabelBitmap *kModeABitmap[8] = {&kSampleWordBitmap, nullptr,
                                                  nullptr,           nullptr,
                                                  nullptr,           nullptr,
                                                  nullptr,           nullptr};
static const ModeLabelBitmap *kModeBBitmap[8] = {&kBreakFxWordBitmap, nullptr,
                                                  nullptr,             nullptr,
                                                  nullptr,             nullptr,
                                                  nullptr,             nullptr};

// ---- 9 mode-indicator icons (M_0..M_7 + M_SD), color, 16x21 (M_SD: 31x21) --
struct ModeIcon {
  const uint16_t *pixels;
  uint8_t w, h;
};
static const ModeIcon kModeIcons[9] = {
    {kModeIcon0, 16, 21}, {kModeIcon1, 16, 21}, {kModeIcon2, 16, 21},
    {kModeIcon3, 16, 21}, {kModeIcon4, 16, 21}, {kModeIcon5, 16, 21},
    {kModeIcon6, 16, 21}, {kModeIcon7, 16, 21}, {kModeIconSd, 31, 21},
};

// ---- monochrome (1bpp, MSB-first) bitmap blit -- GUI_Paint has no
// equivalent to Adafruit_GFX's tft.drawBitmap(). Rows are byte-aligned (each
// row consumes ceil(w/8) bytes), matching how Lopaka packs image_play_bits/
// image_stop_bits. Only pixels whose bit is 1 get painted, in `color` --
// pixels whose bit is 0 are left untouched (transparent background).
static inline void Paint_DrawMonoBitmap(uint16_t x, uint16_t y,
                                         const unsigned char *bits, uint16_t w,
                                         uint16_t h, uint16_t color) {
  const uint16_t row_bytes = (uint16_t)((w + 7) / 8);
  for (uint16_t j = 0; j < h; j++) {
    for (uint16_t i = 0; i < w; i++) {
      const unsigned char byte = bits[j * row_bytes + i / 8];
      if (byte & (0x80 >> (i % 8))) {
        Paint_SetPixel((uint16_t)(x + i), (uint16_t)(y + j), color);
      }
    }
  }
}

// ---- RGB565 brightness scaling, for dimming the 8 inactive mode icons ----
// factor 0..255 (255 = unchanged, 0 = black). Scales each of the 5/6/5-bit
// channels independently; 0x0000 (background) maps to itself, so drawing a
// dimmed icon never "lightens" the black background pixels around the glyph.
static inline uint16_t dim_rgb565(uint16_t color, uint8_t factor) {
  if (color == 0x0000) return 0x0000;
  const uint8_t r = (uint8_t)(((color >> 11) & 0x1F) * factor / 255);
  const uint8_t g = (uint8_t)(((color >> 5) & 0x3F) * factor / 255);
  const uint8_t b = (uint8_t)((color & 0x1F) * factor / 255);
  return (uint16_t)((r << 11) | (g << 5) | b);
}

// Blits a color bitmap pixel-by-pixel through dim_rgb565() at the given
// factor (255 = draws identical to Paint_DrawImage). Used for the 8 inactive
// mode icons; the active one still uses the plain Paint_DrawImage() path.
static inline void Paint_DrawImageDimmed(const uint16_t *pixels, uint16_t x,
                                          uint16_t y, uint16_t w, uint16_t h,
                                          uint8_t factor) {
  for (uint16_t j = 0; j < h; j++) {
    for (uint16_t i = 0; i < w; i++) {
      Paint_SetPixel((uint16_t)(x + i), (uint16_t)(y + j),
                     dim_rgb565(pixels[j * w + i], factor));
    }
  }
}

// ---- variable-width digit-string blit (BPM, sample idx/count) ----
// Draws `text` (digits '0'-'9' plus an optional '/') left to right, each
// character advancing the cursor by ITS OWN real width -- no fixed grid, same
// "pegado" look as the Lopaka mockup. If right_align, the string is measured
// first so its RIGHT edge lands exactly at `x` (growing leftward as the
// digit count increases) instead of its left edge starting there. Pass
// slash_pixels=nullptr if `text` never contains '/' (e.g. plain BPM).
static inline void draw_digit_string(uint16_t x, uint16_t y, const char *text,
                                      const DigitGlyph *digits,
                                      const uint16_t *slash_pixels,
                                      uint8_t slash_w, uint8_t slash_h,
                                      bool right_align) {
  if (right_align) {
    uint16_t total = 0;
    for (const char *p = text; *p; p++) {
      total = (uint16_t)(total + (*p == '/' ? slash_w : digits[*p - '0'].w));
    }
    x = (uint16_t)(x - total);
  }
  for (const char *p = text; *p; p++) {
    if (*p == '/') {
      Paint_DrawImage((const unsigned char *)slash_pixels, x, y, slash_w,
                       slash_h);
      x = (uint16_t)(x + slash_w);
    } else {
      const DigitGlyph &g = digits[*p - '0'];
      Paint_DrawImage((const unsigned char *)g.pixels, x, y, g.w, g.h);
      x = (uint16_t)(x + g.w);
    }
  }
}
```

- [ ] **Step 4: Commit**

Nota: este header todavía no se incluye desde ningún `.cpp` (eso es Task 3) — no hay
nada que buildear de forma aislada. La verificación real de que compila ocurre en
Task 3, cuando `ui.cpp` lo incluye y se compila el proyecto completo. El Step 2 de
este task (conteo de píxeles) ya es la verificación aplicable acá.

```bash
cd /c/pikocore-main
git add src/gamepi13/ui_bitmaps.h
git commit -m "feat: vendorizar bitmaps del dashboard de Lopaka (modo 0) + helpers de blit"
```

---

### Task 2: Campo `playing` en `GamepiUiState` + poblarlo desde `do_mute`

**Files:**
- Modify: `src/gamepi13/ui.h`
- Modify: `src/main.cpp`

- [ ] **Step 1: Agregar el campo a `GamepiUiState`**

Buscar (en `src/gamepi13/ui.h`):
```cpp
  uint8_t mode;          // selector 0-7
  uint16_t knob_a;       // 0-4095
  uint16_t knob_b;       // 0-4095
};
```

Reemplazar:
```cpp
  uint8_t mode;          // selector 0-7
  uint16_t knob_a;       // 0-4095
  uint16_t knob_b;       // 0-4095
  bool playing;          // !do_mute -- drives the play/stop icon pair
};
```

- [ ] **Step 2: Poblarlo en `main.cpp`**

Buscar:
```cpp
        uis.knob_a = input_knob[1].Value();
        uis.knob_b = input_knob[2].Value();
        gamepi_ui_tick(uis);
```

Reemplazar:
```cpp
        uis.knob_a = input_knob[1].Value();
        uis.knob_b = input_knob[2].Value();
        uis.playing = !do_mute;
        gamepi_ui_tick(uis);
```

- [ ] **Step 3: Build ambas variantes**

```bash
cat > /c/pikocore-main/rebuild_bm2.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_bm2.bat"
```

Expected: `MAKE_OK`. Agregar un campo nuevo (`playing`) que `ui.cpp` todavía no lee es
válido en C++ -- no hace falta que `ui.cpp` lo use todavía (eso es Task 3). Repetir
para `build` (BUILDDIR=`build`, tag `rebuild_bm2_orig.bat`) -- el bloque completo
`GamepiUiState uis; ...; gamepi_ui_tick(uis);` (incluida la línea nueva
`uis.playing = !do_mute;`) vive dentro de un mismo `#if PIKO_GAMEPI13` en `main.cpp`
(línea 2138), así que el build original no compila nada de esto; confirmar que sigue
dando `MAKE_OK` con el mismo tamaño de antes.

Borrar ambos `.bat` al terminar.

- [ ] **Step 4: Commit**

```bash
git add src/gamepi13/ui.h src/main.cpp
git commit -m "feat: agregar campo playing a GamepiUiState (para el icono play/stop)"
```

---

### Task 3: Reescribir `ui.cpp` para usar los bitmaps

**Files:**
- Modify: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Incluir el header de bitmaps**

Buscar:
```cpp
#include "../hw_gamepi13.h"
#include "../PikoAudioBank.h"
#include "splash_logo.h"

extern "C" {
#include "lcd/GUI_Paint.h"
#include "lcd/LCD_1in3.h"
}
```

Reemplazar:
```cpp
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
```

- [ ] **Step 2: Reemplazar el enum y `kRect[]`**

Buscar:
```cpp
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
```

Reemplazar:
```cpp
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
```

- [ ] **Step 3: Reescribir `draw_top` (BPM real, ícono de reloj, play/stop; ya NO
      dibuja "NN/MM" -- eso se mueve a `draw_name`)**

Buscar:
```cpp
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
```

Reemplazar:
```cpp
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
```

- [ ] **Step 4: Reescribir `draw_name` (agrega el marco + los dígitos de sample
      idx/count, que antes vivían en `draw_top`)**

Buscar:
```cpp
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
```

Reemplazar:
```cpp
static void draw_name(const GamepiUiState &s) {
  clear_zone(kRect[W_NAME]);
  Paint_DrawImage((const unsigned char *)kFilenameFrame, 0, 29, 191, 20);
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
```

- [ ] **Step 5: Eliminar `draw_modename` y el `draw_bar` viejo; agregar
      `draw_function_label`/`draw_bar`(nueva firma)/`draw_function_a`/`draw_function_b`**

Buscar:
```cpp
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
```

Reemplazar:
```cpp
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

static void draw_function_a(const GamepiUiState &s) {
  clear_zone(kRect[W_BARA]);
  const uint8_t m = (s.mode < 8) ? s.mode : 0;
  draw_function_label(107, kModeABitmap[m], kModeA[m], COL_PINK);
  draw_bar(132, s.knob_a, COL_PINK);
}

static void draw_function_b(const GamepiUiState &s) {
  clear_zone(kRect[W_BARB]);
  const uint8_t m = (s.mode < 8) ? s.mode : 0;
  draw_function_label(157, kModeBBitmap[m], kModeB[m], COL_CYAN);
  draw_bar(182, s.knob_b, COL_CYAN);
}
```

- [ ] **Step 6: Reescribir `draw_dots` → 9 íconos de modo (color, atenuado
      calculado)**

Buscar:
```cpp
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
```

Reemplazar:
```cpp
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
```

- [ ] **Step 7: Actualizar `draw_widget` (sin `W_MODENAME`, `draw_bar` con nueva
      firma)**

Buscar:
```cpp
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
```

Reemplazar:
```cpp
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
```

- [ ] **Step 8: Agregar el marco estático de la waveform (`waveform_frame`) --
      dibujado antes que el contenido dinámico, sin tocarlo**

Buscar:
```cpp
static void draw_wave(const GamepiUiState &s) {
  clear_zone(kRect[W_WAVE]);
  constexpr uint16_t kTop = 54;  // 39px band inside the 52..96 zone
  constexpr uint16_t kBot = 93;
```

Reemplazar:
```cpp
static void draw_wave(const GamepiUiState &s) {
  clear_zone(kRect[W_WAVE]);
  Paint_DrawImage((const unsigned char *)kWaveformFrame, 0, 54, 240, 48);
  constexpr uint16_t kTop = 54;  // 39px band inside the 52..96 zone
  constexpr uint16_t kBot = 93;
```

- [ ] **Step 9: Actualizar la lógica de "sucio" en `gamepi_ui_tick()` (mover la
      dependencia de `sample_idx`/`sample_count` de `W_TOP` a `W_NAME`, agregar
      `playing` a `W_TOP`, `W_BARA`/`W_BARB` juntos en vez de `W_MODENAME`)**

Buscar:
```cpp
    if (s.bpm != drawn.bpm || s.clock_src != drawn.clock_src ||
        s.sample_idx != drawn.sample_idx ||
        s.sample_count != drawn.sample_count) {
      dirty[W_TOP] = true;
    }
    if (strcmp(s.sample_name, drawn.sample_name) != 0) dirty[W_NAME] = true;
```

Reemplazar:
```cpp
    if (s.bpm != drawn.bpm || s.clock_src != drawn.clock_src ||
        s.playing != drawn.playing) {
      dirty[W_TOP] = true;
    }
    if (strcmp(s.sample_name, drawn.sample_name) != 0 ||
        s.sample_idx != drawn.sample_idx ||
        s.sample_count != drawn.sample_count) {
      dirty[W_NAME] = true;
    }
```

Buscar:
```cpp
    if (s.mode != drawn.mode) {
      dirty[W_MODENAME] = true;
      dirty[W_DOTS] = true;
    }
```

Reemplazar:
```cpp
    if (s.mode != drawn.mode) {
      dirty[W_BARA] = true;
      dirty[W_BARB] = true;
      dirty[W_DOTS] = true;
    }
```

- [ ] **Step 10: Actualizar la lista de zonas a redibujar al cerrar el overlay
      (ahora también cubre `W_BARB`, no solo `W_BARA`)**

Buscar:
```cpp
    dirty[W_WAVE] = true;      // zones the overlay covered
    dirty[W_MODENAME] = true;
    dirty[W_BARA] = true;
```

Reemplazar:
```cpp
    dirty[W_WAVE] = true;      // zones the overlay covered
    dirty[W_BARA] = true;
    dirty[W_BARB] = true;
```

- [ ] **Step 11: Build**

```bash
cat > /c/pikocore-main/rebuild_bm3.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_bm3.bat"
```

Expected: `MAKE_OK`. Este task no toca `main.cpp` ni ningún archivo compartido con el
build original -- no hace falta rebuildearlo. Borrar el `.bat` al terminar.

- [ ] **Step 12: Commit**

```bash
git add src/gamepi13/ui.cpp
git commit -m "feat: dashboard con bitmaps de Lopaka (modo 0) -- BPM, reloj, play/stop, sample idx/count, Function A/B, 9 iconos de modo"
```

---

### Task 4: Verificación en hardware (requiere al usuario con la placa)

No delegar a un subagente -- requiere el dispositivo físico. Pasos a pedirle al
usuario:

1. Flashear `build-gamepi/pikocore.uf2` en el GamePi13.
2. En modo 0: BPM se ve con los dígitos de Lopaka (no la fuente de antes), reloj INT
   muestra el ícono `Int_clock`, cambiar a EXT (si hay forma de simularlo) muestra
   `Ext_clock`; el separador (`BPM_Slash`) queda entre el BPM y el ícono de reloj.
3. Play/stop: el ícono correspondiente al estado actual (sonando o muteado) se ve en
   blanco brillante, el otro en gris atenuado.
4. Nombre de sample: se ve dentro del marco (`filename_sample_frame`); a la derecha,
   el índice/total de samples con los dígitos de banco (formato `NN/NN`).
5. Waveform: el marco nuevo se ve alrededor de la franja, el playhead y el resaltado
   naranja/cian siguen funcionando exactamente igual que antes.
6. "SAMPLE" y "BREAK FX" se ven como gráfico (no texto) sobre sus barras
   correspondientes.
7. Los 9 íconos de modo: el que corresponde al modo activo se ve a full color, los
   otros 8 atenuados. Cambiar de modo (Select) mueve el resaltado correctamente.
   Entrar a modo 8 (Browse SD) resalta el ícono `M_SD`.
8. Cambiar a un modo 1-7: "SAMPLE"/"BREAK FX" desaparecen y se ve el nombre de ese
   modo en texto (fallback), sin romper el layout.
9. Si el atenuado de los 8 íconos inactivos (`kInactiveDim = 90`) se ve muy oscuro o
   muy parecido al activo, avisar para ajustar ese valor.
10. Cambiar el BPM de 2 a 3 dígitos (ej. 99→100, con Start+L/R en modo 3): los dígitos
    no colisionan con el ícono de reloj, el número crece hacia la izquierda.
11. Regresión: overlay temporal de Select/L/R, pantallas de Browse SD, tempo, tres
    combos de 4 botones -- todo sin cambios.
12. Si el usuario tiene acceso al hardware original (flag OFF): confirmar que
    `main.cpp`'s cambio (campo `playing`) no alteró ningún comportamiento ahí (el
    campo vive detrás de `#if PIKO_GAMEPI13`).

Si algo falla, diagnosticar leyendo el código (no adivinar) y corregir antes de
continuar a Task 5.

---

### Task 5: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: Actualizar la sección "Qué muestra el LCD"**

Describir el nuevo dashboard con bitmaps: BPM con dígitos propios, ícono de reloj
INT/EXT (MIDI en texto), play/stop, marco de nombre de archivo + índice de sample como
dígitos, marco de waveform (contenido dinámico sin cambios), "SAMPLE"/"BREAK FX" como
gráfico en modo 0 (resto de los modos en texto, pendiente de diseño), 9 íconos de modo
reemplazando los puntos.

- [ ] **Step 2: Agregar una entrada en "mejoras futuras" (sección 6)**

Etiquetas Function A/B gráficas para los modos 1-7 y el ícono de reloj MIDI —
pendientes de que el usuario las diseñe en Lopaka.

- [ ] **Step 3: Commit**

```bash
git add GAMEPI13-INTERFACE.md
git commit -m "docs: documentar el dashboard con bitmaps de Lopaka (modo 0)"
```
