# Waveform con playhead en la zona de LEDs — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La franja de 8 LEDs del dashboard pasa a mostrar la forma de onda del sample que suena, con playhead, separadores de slice, slice activo iluminado y retrigger en cian — sin perder nada de lo que la zona ya comunicaba.

**Architecture:** Un caché estático de 240 columnas min/max (480 bytes) en `ui.cpp`, recalculado de forma bloqueante (~1-4 ms, la ISR de audio preempta) cuando cambia el sample que suena o cuando el banco termina de mutar. `main.cpp` agrega 2 campos a `GamepiUiState`: el sample que SUENA (`sample`, que difiere del seleccionado cuando el FX de túnel salta entre samples) y la columna del playhead (desde `phase_sample`). La zona toma el índice de widget más bajo en prioridad (último del enum) y el redibujo por playhead se throttlea a ~100 ms reales, para no matar de hambre al resto del dashboard (que flushea UN widget sucio por slot de 25 Hz, menor índice primero).

**Tech Stack:** C/C++17, pico-sdk 2.1.1. Archivos: `src/gamepi13/ui.h`, `src/gamepi13/ui.cpp`, `src/main.cpp`.

**Spec:** `docs/superpowers/specs/2026-07-16-waveform-playhead-design.md` (aprobado, con el estudio completo). Rama: `port/rp2350-gamepi13`.

---

## Contexto para quien ejecuta

### Entorno de build (Windows) — igual que en todas las fases

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

`BUILDDIR` = `build` (original) o `build-gamepi` (GamePi13). No se toca `CMakeLists.txt` en
este plan, así que no hace falta reconfigurar CMake. Borrar el `.bat` temporal al terminar.

### Hechos ya verificados (no re-descubrir)

1. **Audio**: PCM 8-bit sin signo (128 = centro), 24 kHz, leído por XIP —
   `piko_raw_val(sample_idx, frame)` y `piko_raw_len(sample_idx)` (`src/PikoAudioBank.h`)
   son lecturas de memoria planas, seguras concurrentemente (solo las escrituras a flash
   necesitan lockout). En `main.cpp` existen los alias `raw_val`/`raw_len` (`#define`,
   líneas 43-44); en `ui.cpp` hay que usar los nombres completos `piko_raw_val`/`piko_raw_len`.
2. **Posición de reproducción**: `phase_sample[phase_head]` (globales de `main.cpp`,
   líneas 187/189), mantenida por la ISR; ya sincronizada con timestretch. El sample que
   SUENA es `sample` (línea 180) — con el FX de túnel puede diferir por compás de
   `sample_set` (el seleccionado, que alimenta `uis.sample_idx` para el nombre en pantalla).
3. **`Paint_DrawLine(Xstart, Ystart, Xend, Yend, Color, DOT_PIXEL, LINE_STYLE)`** existe en
   el driver vendorizado (`src/gamepi13/lcd/GUI_Paint.h:132`), con `DOT_PIXEL_1X1` y
   `LINE_STYLE_SOLID` disponibles. Una línea con extremos iguales dibuja al menos 1 píxel.
4. **`gamepi_ui_tick()`** flushea UN widget sucio por slot (~25 Hz), eligiendo el de menor
   índice del enum — por eso la zona waveform debe ser el ÚLTIMO índice.
5. **`piko_audio_bank_mutating()`** (`src/PikoAudioBank.h`) es el guard existente para
   "el banco está siendo reescrito" (carga SD/USB); `ui.cpp` aún no incluye
   `PikoAudioBank.h` — este plan agrega el include.

### Reglas

- Todo lo nuevo vive en archivos que solo compilan bajo `PIKO_GAMEPI13` (`src/gamepi13/*`)
  o dentro de bloques `#if PIKO_GAMEPI13` ya existentes en `main.cpp`. El build original
  (flag OFF) queda byte-idéntico.
- No se toca la lógica de audio/retrigger/timestretch — solo se lee su estado.
- Cada task termina con AMBOS builds compilando (`MAKE_OK` ×2) y un commit.

---

### Task 1: Campos nuevos en `GamepiUiState` + poblarlos en `main.cpp`

**Files:**
- Modify: `src/gamepi13/ui.h`
- Modify: `src/main.cpp`

- [ ] **Step 1: Agregar los campos en `src/gamepi13/ui.h`**

Buscar:
```cpp
  // Bit i set = LED i is one of the two buttons currently driving an active
  // retrigger/stutter (btn_retrig) -- drawn cyan instead of the normal
  // amplitude-based orange, to distinguish stutter from a plain jump.
  uint8_t retrig_leds_mask;
  uint8_t mode;          // selector 0-7
```
Reemplazar por:
```cpp
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
```

- [ ] **Step 2: Poblarlos en `src/main.cpp`**

Buscar (dentro del bloque `#if PIKO_GAMEPI13` que arma `uis` cada tick):
```cpp
        uis.retrig_leds_mask = 0;
        if (btn_retrig) {
          if (button_on < NUM_BUTTONS) {
            uis.retrig_leds_mask |= (uint8_t)(1u << button_on);
          }
          if (button_on2 < NUM_BUTTONS) {
            uis.retrig_leds_mask |= (uint8_t)(1u << button_on2);
          }
        }
        uis.mode = gamepi_selector;
```
Reemplazar por:
```cpp
        uis.retrig_leds_mask = 0;
        if (btn_retrig) {
          if (button_on < NUM_BUTTONS) {
            uis.retrig_leds_mask |= (uint8_t)(1u << button_on);
          }
          if (button_on2 < NUM_BUTTONS) {
            uis.retrig_leds_mask |= (uint8_t)(1u << button_on2);
          }
        }
        {
          // Playing sample (`sample`, ISR-owned; may differ from sample_set
          // while the tunnel FX hops) + playhead column against ITS length,
          // so the cursor always matches what's audible.
          const uint16_t playing = sample;
          uis.wave_sample_idx = playing;
          const uint32_t wave_len = raw_len(playing);
          if (ui_scount > 0 && wave_len > 1) {
            const uint32_t ph = phase_sample[phase_head] % wave_len;
            uis.wave_playhead_col = (uint8_t)(((uint64_t)ph * 240u) / wave_len);
          } else {
            uis.wave_playhead_col = 255;  // no playhead
          }
        }
        uis.mode = gamepi_selector;
```

- [ ] **Step 3: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/` (original) byte-idéntico — los campos solo se escriben
dentro del bloque `#if PIKO_GAMEPI13`, y `ui.h` no se incluye en el build original.
Los campos quedan escritos pero sin lector todavía (Task 2 los consume) — correcto para
este task.

- [ ] **Step 4: Commit**

```bash
git add src/gamepi13/ui.h src/main.cpp
git commit -m "feat: exponer sample sonando + columna de playhead al estado de UI"
```

---

### Task 2: Widget de waveform en `ui.cpp` (caché, dibujo, prioridad, throttle)

**Files:**
- Modify: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Include de `PikoAudioBank.h`**

Buscar:
```cpp
#include "../hw_gamepi13.h"
```
Reemplazar por:
```cpp
#include "../hw_gamepi13.h"
#include "../PikoAudioBank.h"
```

- [ ] **Step 2: Renombrar `W_LEDS` → `W_WAVE` y moverlo al final del enum + `kRect`**

Buscar:
```cpp
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
```
Reemplazar por:
```cpp
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

- [ ] **Step 3: Reemplazar `draw_leds()` por el caché + `draw_wave()`**

Buscar (la versión actual completa, con el branch de retrig de la feature anterior):
```cpp
static void draw_leds(const GamepiUiState &s) {
  clear_zone(kRect[W_LEDS]);
  for (uint8_t i = 0; i < 8; i++) {
    uint16_t x = (uint16_t)(10 + i * 28);  // 8 x 24px + 4px gap = 220 wide
    UWORD col = COL_DARK;
    if (s.retrig_leds_mask & (uint8_t)(1u << i)) {
      // Solid, ignores amplitude on purpose -- this is a state indicator
      // (stutter active), not another brightness gradation.
      col = COL_CYAN;
    } else if (s.leds[i] >= 128) {
      col = COL_ORANGE;
    } else if (s.leds[i] >= 8) {
      col = COL_ORANGE_DIM;
    }
    Paint_DrawRectangle(x, 62, (uint16_t)(x + 23), 85, col, DOT_PIXEL_1X1,
                        DRAW_FILL_FULL);
  }
}
```
Reemplazar por:
```cpp
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
```

Nota: la vieja gradación de 3 niveles (brillante ≥128 / tenue ≥8 / apagado) colapsa a 2
(iluminado ≥8 / fondo tenue) — la waveform tenue ES el nuevo estado "apagado". Decisión
del spec, no un descuido.

- [ ] **Step 4: Actualizar el `switch` de `draw_widget()`**

Buscar:
```cpp
    case W_LEDS:
      draw_leds(s);
      break;
```
Reemplazar por:
```cpp
    case W_WAVE:
      draw_wave(s);
      break;
```
(La posición del `case` dentro del `switch` no importa; solo el nombre.)

- [ ] **Step 5: Mantenimiento del caché + diffing en `gamepi_ui_tick()`**

Buscar (el arranque de la función):
```cpp
void gamepi_ui_tick(const GamepiUiState &s) {
  // Mark widgets whose backing data changed since last draw.
  if (!have_drawn) {
```
Reemplazar por:
```cpp
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
```

Buscar (el diffing actual de LEDs/máscara):
```cpp
    if (memcmp(s.leds, drawn.leds, sizeof(s.leds)) != 0 ||
        s.retrig_leds_mask != drawn.retrig_leds_mask) {
      dirty[W_LEDS] = true;
    }
```
Reemplazar por:
```cpp
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
```
Y agregar la variable de throttle junto a las otras estáticas del archivo — buscar:
```cpp
static uint16_t wave_cached_sample = 0xffff;
static bool wave_cache_valid = false;
```
Reemplazar por:
```cpp
static uint16_t wave_cached_sample = 0xffff;
static bool wave_cache_valid = false;
static uint64_t wave_playhead_mark_us = 0;
```

- [ ] **Step 6: Renombrar la marca del overlay-restore**

Buscar (dentro del bloque de restauración del overlay en `gamepi_ui_tick()`):
```cpp
    dirty[W_LEDS] = true;      // zones the overlay covered
```
Reemplazar por:
```cpp
    dirty[W_WAVE] = true;      // zones the overlay covered
```

- [ ] **Step 7: Verificar que no quede ninguna referencia a `W_LEDS`/`draw_leds`**

```bash
grep -rn "W_LEDS\|draw_leds" /c/pikocore-main/src/
```
Expected: sin resultados.

- [ ] **Step 8: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/` byte-idéntico (`ui.cpp` no forma parte de ese target).

- [ ] **Step 9: Commit**

```bash
git add src/gamepi13/ui.cpp
git commit -m "feat: waveform con playhead, separadores de slice y resaltado en la ex-zona de LEDs"
```

---

### Task 3: Verificación en hardware (requiere al usuario con la placa)

**Files:** ninguno

- [ ] **Step 1: Grabar** `build-gamepi/pikocore.uf2`.
- [ ] **Step 2: Checklist**
  1. Con un banco cargado: la waveform del sample activo aparece en la franja (con sus
     7 separadores); el playhead blanco avanza de izquierda a derecha al ritmo del loop.
  2. Presionar un botón musical: el playhead salta a esa región y el slice se ilumina
     naranja brillante.
  3. Dos botones a la vez (retrigger): los 2 slices se tiñen cian.
  4. Cambiar de sample (modo 0, L/R): la waveform se actualiza; el audio no se corta ni
     hace glitch en el instante del cambio (validación del costo de decimación).
  5. Con túnel activo (modo 4): la waveform salta de sample en sample con cada compás
     que tunelea — es el comportamiento diseñado, no un bug.
  6. Cargar un banco desde SD: al terminar, la waveform muestra el sample nuevo (aunque
     tenga el mismo índice y largo que el anterior).
  7. Sin samples (banco vacío): línea plana central, sin playhead, sin crash.
  8. Regresión: overlays (Select/L/R/tempo), modo Browse SD, y el resto del dashboard
     responden igual de rápido que antes (validación del anti-starvation).
- [ ] **Step 3: Si algo falla de forma difícil de diagnosticar**

Los 2 commits de esta feature son aislados y revertibles con `git revert` sin afectar
nada anterior. Si la sensación de fluidez del dashboard empeora, el primer dial es el
throttle del playhead (100000 → 200000 µs en `gamepi_ui_tick()`).

---

### Task 4: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`
- Modify: `README-GAMEPI13.md`

- [ ] **Step 1: `GAMEPI13-INTERFACE.md` sección 4** — reemplazar la descripción de la
  barra de LEDs por la de la zona waveform (forma de onda del sample que suena, playhead
  blanco, separadores de slice, slice activo naranja brillante, retrigger cian, y la nota
  de que con túnel activo la waveform sigue al sample que realmente suena).
- [ ] **Step 2: `GAMEPI13-INTERFACE.md` sección 6** — quitar el bullet "Waveform con
  playhead en el dashboard" (ya no es futuro) y agregar la entrada RESUELTO
  correspondiente en la sección 5, con referencia al spec y a la reclasificación del
  riesgo (el estudio mostró que el DMA era innecesario).
- [ ] **Step 3: `README-GAMEPI13.md`** — actualizar la sección "pantalla" (la línea que
  menciona "barra de 8 LEDs virtuales") y quitar "waveform con playhead" de la línea
  "Pendiente (Fase 2.1)".
- [ ] **Step 4: Commit**

```bash
git add GAMEPI13-INTERFACE.md README-GAMEPI13.md
git commit -m "docs: documentar la zona de waveform con playhead"
```
