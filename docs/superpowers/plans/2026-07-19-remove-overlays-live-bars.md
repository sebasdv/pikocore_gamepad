# Quitar overlay + barras en vivo + barra de sample segmentada — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quitar el overlay temporal de modo/parámetro/tempo (dejando intacto el
overlay persistente de Browse SD), lo que además libera el dirty-tracking existente
para que las barras de Function A/B se actualicen en vivo, y segmentar la barra de
selección de sample (modo 0, Function A) en un paginador de segmentos.

**Architecture:** Sustractivo en su mayor parte (3 funciones + 6 llamadas + 1 helper
que queda huérfano) más una función nueva autocontenida (`draw_sample_bar()`) que
reemplaza `draw_bar()` solo para el caso de modo 0 Function A. `overlay_show_panel()`
y todo el mecanismo del modo 8 (Browse SD) no se tocan.

**Tech Stack:** C/C++17, sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-19-remove-overlays-live-bars-design.md`
(aprobado). Rama: `port/rp2350-gamepi13`.

---

## Contexto para quien ejecuta

### Entorno de build (Windows)

```bash
cat > /c/pikocore-main/rebuild_TAG.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 (
  echo VCVARSALL_FAILED
  exit /b 1
)
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 (
  echo MAKE_FAILED
  exit /b 1
)
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_TAG.bat"
```

Solo `build-gamepi` compila estos archivos (100% exclusivos de GamePi13). Este plan
toca `src/main.cpp` (compartido con el hardware original) además de
`src/gamepi13/ui.cpp`/`ui.h` — las llamadas que se borran de `main.cpp` están dentro
de bloques `#if PIKO_GAMEPI13`, así que el hardware original (`build`) no se ve
afectado, pero no hace falta verificarlo aparte (fuera de alcance de este sub-proyecto).

### Hallazgos que hay que respetar

- El dirty-tracking de `gamepi_ui_tick()` (`src/gamepi13/ui.cpp:465-466`) **ya** marca
  `W_BARA`/`W_BARB` sucios cuando cambia `s.knob_a`/`s.knob_b` — no hace falta agregar
  ningún mecanismo de actualización en vivo nuevo, alcanza con quitar lo que lo bloquea
  (el overlay).
- `overlay_show_panel(bool persistent = false)` y `sd_panel_title()` (que la llama con
  `persistent=true`, exclusivo del modo 8) **no se tocan**.
- Al borrar `gamepi_ui_overlay_param()`, su único uso de `pct()` (`ui.cpp:156`)
  desaparece — `pct()` queda huérfana y se borra también (mismo criterio que los
  assets huérfanos de sub-proyectos anteriores: no se deja código muerto).
- El banco de audio soporta hasta 128 samples reales (`PIKO_BANK_MAX_SAMPLES`,
  `src/PikoAudioBank.h`) — el segmentado debe funcionar correctamente en ese caso
  extremo, no solo con bancos chicos.

### Reglas de la fase

- Cada task termina con `build-gamepi` compilando (`MAKE_OK`) y un commit.

---

### Task 1: Quitar el overlay no-persistente

**Files:**
- Modify: `src/gamepi13/ui.cpp`
- Modify: `src/gamepi13/ui.h`
- Modify: `src/main.cpp`

- [ ] **Step 1: Borrar `pct()` y las 3 funciones de overlay no-persistente de
      `src/gamepi13/ui.cpp`**

Buscar:
```cpp
static uint8_t pct(uint16_t v) { return (uint8_t)((uint32_t)v * 100u / 4095u); }

// ---- widget draw functions ----
```

Reemplazar:
```cpp
// ---- widget draw functions ----
```

Buscar (bloque completo, las 3 funciones seguidas):
```cpp
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
```

Reemplazar:
```cpp
static void sd_panel_title(const char *title, UWORD color) {
```

- [ ] **Step 2: Borrar las 3 declaraciones de `src/gamepi13/ui.h`**

Buscar:
```cpp
void gamepi_ui_init();                      // LCD init + splash (blocking ~2 s, call before audio IRQ is enabled)
void gamepi_ui_tick(const GamepiUiState &s);  // call once per 250 Hz control tick
void gamepi_ui_overlay_mode(uint8_t mode);  // Select pressed
void gamepi_ui_overlay_param(uint8_t mode, bool is_b, uint16_t val);  // L/R adjust
void gamepi_ui_overlay_tempo(uint16_t bpm);  // tempo adjust (mode 7 Function B): real BPM, not %
```

Reemplazar:
```cpp
void gamepi_ui_init();                      // LCD init + splash (blocking ~2 s, call before audio IRQ is enabled)
void gamepi_ui_tick(const GamepiUiState &s);  // call once per 250 Hz control tick
```

- [ ] **Step 3: Borrar las 2 llamadas a `gamepi_ui_overlay_mode()` en `src/main.cpp`
      (aparece 2 veces, texto idéntico — reemplazar ambas apariciones)**

Buscar (aparece 2 veces):
```cpp
            input_knob[0].SetBucket(gamepi_selector, 8);
            gamepi_ui_overlay_mode(gamepi_selector);
```

Reemplazar (en ambas apariciones):
```cpp
            input_knob[0].SetBucket(gamepi_selector, 8);
```

- [ ] **Step 4: Borrar la llamada a `gamepi_ui_overlay_tempo()`/`gamepi_ui_overlay_param()`
      en la rama de `btn_l` (L sostenido)**

Buscar:
```cpp
            if (is_tempo) {
              const uint64_t held_us = now_repeat_us - gamepi_tempo_hold_l_us;
              const uint16_t step =
                  held_us >= GAMEPI_TEMPO_TIER3_US ? GAMEPI_TEMPO_STEP_FAST
                  : held_us >= GAMEPI_TEMPO_TIER2_US ? GAMEPI_TEMPO_STEP_MED
                                                     : GAMEPI_TEMPO_STEP_FINE;
              uint16_t new_bpm = bpm_set > (uint16_t)(GAMEPI_TEMPO_MIN_BPM + step)
                                      ? (uint16_t)(bpm_set - step)
                                      : GAMEPI_TEMPO_MIN_BPM;
              param_set_bpm(new_bpm, bpm_set, beat_thresh, audio_clk_thresh);
              gamepi_start_used_as_modifier = true;
              gamepi_ui_overlay_tempo(bpm_set);
            } else {
              input_knob[active_knob].Adjust(-GAMEPI_KNOB_STEP);
              if (active_knob == 2) gamepi_start_used_as_modifier = true;
              gamepi_ui_overlay_param(gamepi_selector, active_knob == 2,
                                      input_knob[active_knob].Value());
            }
```

Reemplazar:
```cpp
            if (is_tempo) {
              const uint64_t held_us = now_repeat_us - gamepi_tempo_hold_l_us;
              const uint16_t step =
                  held_us >= GAMEPI_TEMPO_TIER3_US ? GAMEPI_TEMPO_STEP_FAST
                  : held_us >= GAMEPI_TEMPO_TIER2_US ? GAMEPI_TEMPO_STEP_MED
                                                     : GAMEPI_TEMPO_STEP_FINE;
              uint16_t new_bpm = bpm_set > (uint16_t)(GAMEPI_TEMPO_MIN_BPM + step)
                                      ? (uint16_t)(bpm_set - step)
                                      : GAMEPI_TEMPO_MIN_BPM;
              param_set_bpm(new_bpm, bpm_set, beat_thresh, audio_clk_thresh);
              gamepi_start_used_as_modifier = true;
            } else {
              input_knob[active_knob].Adjust(-GAMEPI_KNOB_STEP);
              if (active_knob == 2) gamepi_start_used_as_modifier = true;
            }
```

- [ ] **Step 5: Borrar la llamada a `gamepi_ui_overlay_tempo()`/`gamepi_ui_overlay_param()`
      en la rama de `btn_r` (R sostenido)**

Buscar:
```cpp
            if (is_tempo) {
              const uint64_t held_us = now_repeat_us - gamepi_tempo_hold_r_us;
              const uint16_t step =
                  held_us >= GAMEPI_TEMPO_TIER3_US ? GAMEPI_TEMPO_STEP_FAST
                  : held_us >= GAMEPI_TEMPO_TIER2_US ? GAMEPI_TEMPO_STEP_MED
                                                     : GAMEPI_TEMPO_STEP_FINE;
              uint16_t new_bpm = (uint16_t)(bpm_set + step);
              if (new_bpm > GAMEPI_TEMPO_MAX_BPM) new_bpm = GAMEPI_TEMPO_MAX_BPM;
              param_set_bpm(new_bpm, bpm_set, beat_thresh, audio_clk_thresh);
              gamepi_start_used_as_modifier = true;
              gamepi_ui_overlay_tempo(bpm_set);
            } else {
              input_knob[active_knob].Adjust(GAMEPI_KNOB_STEP);
              if (active_knob == 2) gamepi_start_used_as_modifier = true;
              gamepi_ui_overlay_param(gamepi_selector, active_knob == 2,
                                      input_knob[active_knob].Value());
            }
```

Reemplazar:
```cpp
            if (is_tempo) {
              const uint64_t held_us = now_repeat_us - gamepi_tempo_hold_r_us;
              const uint16_t step =
                  held_us >= GAMEPI_TEMPO_TIER3_US ? GAMEPI_TEMPO_STEP_FAST
                  : held_us >= GAMEPI_TEMPO_TIER2_US ? GAMEPI_TEMPO_STEP_MED
                                                     : GAMEPI_TEMPO_STEP_FINE;
              uint16_t new_bpm = (uint16_t)(bpm_set + step);
              if (new_bpm > GAMEPI_TEMPO_MAX_BPM) new_bpm = GAMEPI_TEMPO_MAX_BPM;
              param_set_bpm(new_bpm, bpm_set, beat_thresh, audio_clk_thresh);
              gamepi_start_used_as_modifier = true;
            } else {
              input_knob[active_knob].Adjust(GAMEPI_KNOB_STEP);
              if (active_knob == 2) gamepi_start_used_as_modifier = true;
            }
```

- [ ] **Step 6: Verificar que no queda ninguna referencia**

```bash
grep -rn "gamepi_ui_overlay_mode\|gamepi_ui_overlay_param\|gamepi_ui_overlay_tempo\|\bpct(" /c/pikocore-main/src/
```

Expected: sin resultados.

- [ ] **Step 7: Build**

```bash
cat > /c/pikocore-main/rebuild_ol1.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_ol1.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar.

- [ ] **Step 8: Commit**

```bash
cd /c/pikocore-main
git add src/gamepi13/ui.cpp src/gamepi13/ui.h src/main.cpp
git commit -m "fix: quitar el overlay temporal de modo/parametro/tempo (las barras ya se actualizan en vivo)"
```

---

### Task 2: Barra de sample segmentada (modo 0, Function A)

**Files:**
- Modify: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Agregar `draw_sample_bar()` justo antes de `draw_function_a()`, y
      usarla en modo 0**

Buscar:
```cpp
static void draw_function_a(const GamepiUiState &s) {
  clear_zone(kRect[W_BARA]);
  const uint8_t m = (s.mode < 8) ? s.mode : 0;
  draw_function_label(107, kModeABitmap[m], kModeA[m], kModeColorA[m]);
  draw_bar(132, s.knob_a, kModeColorA[m]);
}
```

Reemplazar:
```cpp
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
```

- [ ] **Step 2: Actualizar el dirty-tracking para que `W_BARA` también dependa de
      `sample_idx`/`sample_count`**

Buscar:
```cpp
    if (s.mode != drawn.mode) {
      dirty[W_BARA] = true;
      dirty[W_BARB] = true;
      dirty[W_DOTS] = true;
    }
    if (s.knob_a != drawn.knob_a) dirty[W_BARA] = true;
    if (s.knob_b != drawn.knob_b) dirty[W_BARB] = true;
```

Reemplazar:
```cpp
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
```

- [ ] **Step 3: Build**

```bash
cat > /c/pikocore-main/rebuild_ol2.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_ol2.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar.

- [ ] **Step 4: Commit**

```bash
cd /c/pikocore-main
git add src/gamepi13/ui.cpp
git commit -m "feat: segmentar la barra de seleccion de sample (modo 0, Function A) en un paginador"
```

---

### Task 3: Verificación en hardware (requiere al usuario con la placa)

No delegar a un subagente -- requiere el dispositivo físico. Pasos a pedirle al
usuario:

1. Flashear `build-gamepi/pikocore.uf2` en el GamePi13.
2. Cambiar de modo (Select) y ajustar cualquier parámetro con L/R: confirmar que **no**
   aparece ningún recuadro/overlay temporal en el centro de la pantalla, y que la barra
   correspondiente (Function A o B) se actualiza en vivo, sin demora, mientras se
   mantiene presionado L/R.
3. Modo 0, Function A: confirmar que la barra se ve segmentada (bloques separados por
   un espacio fino, no un relleno liso), que el segmento resaltado coincide con el
   sample realmente seleccionado (visible en el nombre/índice del dashboard), y que
   navegar con L/R mueve el resaltado de forma discreta, de a un segmento por vez (o
   agrupado si el banco tiene muchos samples).
4. Confirmar que modo 8 (Browse SD) no se ve afectado — su overlay persistente sigue
   funcionando exactamente igual (listado, navegación, progreso, carga, resultado).
5. Regresión: BPM, reloj, play/stop, sample idx/count, waveform, 9 íconos de modo,
   colores por modo — todo sin cambios.

Si algo falla, diagnosticar leyendo el código (no adivinar) y corregir.

---

### Task 4: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: Quitar la mención al overlay de Tempo (sección 3, ya no existe)**

Buscar:
```markdown
≥3s = ±20 BPM por paso. Rango 20–360 BPM, cualquier valor entero (antes solo múltiplos
de 5). El overlay de Tempo muestra el BPM real ("142 BPM"), no un porcentaje.
```

Reemplazar:
```markdown
≥3s = ±20 BPM por paso. Rango 20–360 BPM, cualquier valor entero (antes solo múltiplos
de 5).
```

- [ ] **Step 2: Actualizar la sección 3.1 (Browse SD) — ya no hay "el resto de los
      overlays" con qué compararse**

Buscar:
```markdown
- Las pantallas de este modo (listado, navegación, progreso, carga, resultado) son
  overlays **persistentes** (no se cierran solas por tiempo) mientras estés en el modo
  8 — se cierran explícitamente al salir con Select (`gamepi_ui_sd_close()`). Esto es
  distinto del resto de los overlays (Select/L/R en los otros modos), que sí se
  desvanecen solos tras ~1s real.
```

Reemplazar:
```markdown
- Las pantallas de este modo (listado, navegación, progreso, carga, resultado) son
  overlays **persistentes** (no se cierran solas por tiempo) mientras estés en el modo
  8 — se cierran explícitamente al salir con Select (`gamepi_ui_sd_close()`). Es el
  único overlay que queda en el dashboard (el resto se quitó, ver sección 4).
```

- [ ] **Step 3: Reemplazar la sección "Overlay temporal" de la sección 4 por una
      descripción de las barras en vivo + la barra de sample segmentada**

Buscar:
```markdown
**Overlay temporal**: al presionar Select aparece el nombre del modo nuevo (Function A y
B); al presionar L/R aparece el parámetro activo con su valor en grande y una barra de
progreso. Se desvanece ~1 segundo real después (ver sección 5 sobre la calibración de
este tiempo). Las pantallas del modo 8 (Browse SD) son la excepción: son persistentes,
ver sección 3.1.
```

Reemplazar:
```markdown
**Sin overlay temporal**: existió hasta la Fase 5 (nombre de modo al presionar Select,
parámetro con valor y barra de progreso al ajustar L/R) y se quitó — los shortcuts
Select+botón musical (sección 3) ya permiten saltar de modo sin necesitar ese aviso, y
las barras de Function A/B del dashboard normal se actualizan en vivo mientras se
ajustan (el dirty-tracking ya reaccionaba al valor del knob; el overlay era lo único
que bloqueaba que eso se viera). Las pantallas del modo 8 (Browse SD) son la única
excepción: siguen siendo un overlay, y persistente (sección 3.1).

**Barra de selección de sample (modo 0, Function A)**: en vez de un relleno continuo,
un paginador de segmentos — un segmento resaltado por sample, agrupando en potencias de
2 si el banco tiene más de 32 samples (el máximo real es 128, `PIKO_BANK_MAX_SAMPLES`)
para que cada segmento siga siendo distinguible. El resto de las barras (Function B del
modo 0, y Function A/B de los modos 1-7) siguen con el relleno continuo de siempre.
```

- [ ] **Step 4: Actualizar la mención a `gamepi_ui_overlay_param()` en el hallazgo de
      modos 5/6 (sección 5, la función ya no existe)**

Buscar:
```markdown
están reasignados a otra cosa en este HAT). El overlay genérico del LCD
  (`gamepi_ui_overlay_param()`) tampoco ayuda: muestra la misma barra numérica 0-4095
  para cualquier modo, sin texto de "Grabando"/"Guardado"/"Cargado". Sin resolver por
  ahora — ver sección 6 para la mejora propuesta (agregar feedback en el LCD).
```

Reemplazar:
```markdown
están reasignados a otra cosa en este HAT). El overlay genérico que existía hasta la
  Fase 5 tampoco ayudaba (mostraba la misma barra numérica 0-4095 para cualquier modo,
  sin texto de "Grabando"/"Guardado"/"Cargado") y ya no existe (ver sección 4) — la
  barra normal del dashboard ahora se mueve en vivo con el valor del knob, pero sigue
  sin decir "Grabando"/"Guardado"/"Cargado" explícitamente. Sin resolver por ahora — ver
  sección 6 para la mejora propuesta (agregar feedback en el LCD).
```

- [ ] **Step 5: Commit**

```bash
git add GAMEPI13-INTERFACE.md
git commit -m "docs: documentar la baja del overlay temporal, barras en vivo y sample bar segmentada"
```
