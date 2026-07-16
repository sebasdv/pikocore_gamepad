# Indicador de retrigger en la barra de LEDs — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cuando el motor de audio está en retrigger/stutter (dos botones musicales combinados), los dos LEDs virtuales correspondientes se pintan en cian sólido en vez del naranja normal, para distinguirlo visualmente de un jump simple.

**Architecture:** `main.cpp` ya tiene el estado necesario (`btn_retrig`, `button_on`, `button_on2`) como variables globales compartidas de forma segura entre la ISR de audio y el loop principal. Se agrega un campo `retrig_leds_mask` a `GamepiUiState` (el struct que ya viaja de `main.cpp` a `ui.cpp` cada tick), calculado una vez por tick, y `draw_leds()` lo usa para elegir color por LED.

**Tech Stack:** C/C++17, pico-sdk 2.1.1. Mismos archivos que las Fases 2/3 (`src/gamepi13/ui.h`, `src/gamepi13/ui.cpp`, `src/main.cpp`).

**Spec:** `docs/superpowers/specs/2026-07-16-retrig-led-indicator-design.md` (aprobado). Rama: `port/rp2350-gamepi13`.

---

## Contexto para quien ejecuta

### Entorno de build (Windows) — igual que en Fases 1-3

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

`BUILDDIR` = `build` (original) o `build-gamepi` (GamePi13). No hace falta reconfigurar
CMake (no se toca `CMakeLists.txt` en este plan). Borrar el `.bat` temporal al terminar.

### Hechos ya verificados (no re-descubrir)

1. **`btn_retrig`, `button_on`, `button_on2` son globales de `src/main.cpp`.** Se escriben
   en `pwm_interrupt_handler()` (la ISR de audio) y se leen sin lock explícito desde el
   loop principal de botones/LCD — mismo core (core0), mismo patrón ya usado por
   `bpm_set`/`distortion`. `button_on`/`button_on2` valen `NUM_BUTTONS` (8) cuando no hay
   un botón en esa posición (ningún botón real usa el índice 8, así que es un valor
   "vacío" seguro de chequear con `< NUM_BUTTONS`).
2. **`GamepiUiState` (`src/gamepi13/ui.h`)** es el struct que `main.cpp` arma una vez por
   tick y pasa a `gamepi_ui_tick()`. Ya tiene un array `uint8_t leds[8]` con la amplitud
   0-255 de cada LED virtual.
3. **`draw_leds()` (`src/gamepi13/ui.cpp`)** pinta cada uno de los 8 LEDs en naranja
   (brillante si `s.leds[i] >= 128`, tenue si `>= 8`, apagado si no) usando
   `Paint_DrawRectangle`. `COL_CYAN` (`0x3DFF`) ya existe como constante de color en este
   archivo, usada hoy para Function B / progreso.
4. **`gamepi_ui_tick()`** solo redibuja un widget si está "sucio" (`dirty[W_LEDS]`), y hoy
   ese chequeo compara `s.leds` con `drawn.leds` vía `memcmp`. Si la máscara nueva cambia
   pero `s.leds` no, hay que marcar `dirty[W_LEDS]` explícitamente o el cambio no se
   dibuja hasta el próximo cambio de amplitud.

### Reglas de la fase

- Todo lo nuevo compila SOLO bajo `PIKO_GAMEPI13` (o vive en archivos que ya solo
  compilan con ese flag, como `src/gamepi13/*`). El build original no cambia de tamaño.
- No se toca la lógica de audio/retrigger — solo se lee su estado existente.
- Cada task termina con AMBOS builds compilando (`MAKE_OK` ×2) y un commit.

---

### Task 1: Agregar `retrig_leds_mask` a `GamepiUiState` y calcularlo en `main.cpp`

**Files:**
- Modify: `src/gamepi13/ui.h` (agregar el campo al struct)
- Modify: `src/main.cpp` (calcular la máscara cada tick)

- [ ] **Step 1: Agregar el campo en `src/gamepi13/ui.h`**

Buscar:
```cpp
struct GamepiUiState {
  uint16_t bpm;
  uint8_t clock_src;     // 0=INT, 1=EXT, 2=MIDI
  uint16_t sample_idx;   // 0-based
  uint16_t sample_count;
  char sample_name[22];  // truncated, always NUL-terminated
  char active_bank_name[24];  // "" if no SD bank loaded this session; truncated, NUL-terminated
  uint8_t leds[8];       // target brightness 0-255 (from LEDArray)
  uint8_t mode;          // selector 0-7
  uint16_t knob_a;       // 0-4095
  uint16_t knob_b;       // 0-4095
};
```
Reemplazar por:
```cpp
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
  uint8_t mode;          // selector 0-7
  uint16_t knob_a;       // 0-4095
  uint16_t knob_b;       // 0-4095
};
```

- [ ] **Step 2: Calcular la máscara en `src/main.cpp`**

Buscar (dentro del bloque `#if PIKO_GAMEPI13` que arma `uis` cada tick):
```cpp
        for (uint8_t j = 0; j < 8; j++) uis.leds[j] = ledarray.Get(j);
        uis.mode = gamepi_selector;
```
Reemplazar por:
```cpp
        for (uint8_t j = 0; j < 8; j++) uis.leds[j] = ledarray.Get(j);
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

- [ ] **Step 3: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/` (original) no debe cambiar de tamaño — el campo nuevo del
struct y el cálculo de la máscara solo se usan dentro de código ya condicionado a
`PIKO_GAMEPI13`; el struct en sí (`GamepiUiState`) vive en un header que el build
original ni siquiera incluye.

- [ ] **Step 4: Commit**

```bash
git add src/gamepi13/ui.h src/main.cpp
git commit -m "feat: calcular mascara de LEDs en retrigger activo"
```

---

### Task 2: Pintar los LEDs de retrigger en cian y marcar el widget sucio

**Files:**
- Modify: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Usar la máscara en `draw_leds()`**

Buscar:
```cpp
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
```
Reemplazar por:
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

- [ ] **Step 2: Marcar `dirty[W_LEDS]` cuando cambia la máscara**

Buscar:
```cpp
    if (memcmp(s.leds, drawn.leds, sizeof(s.leds)) != 0) dirty[W_LEDS] = true;
```
Reemplazar por:
```cpp
    if (memcmp(s.leds, drawn.leds, sizeof(s.leds)) != 0 ||
        s.retrig_leds_mask != drawn.retrig_leds_mask) {
      dirty[W_LEDS] = true;
    }
```

- [ ] **Step 3: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/` no cambia — `ui.cpp` no forma parte de ese target.

- [ ] **Step 4: Commit**

```bash
git add src/gamepi13/ui.cpp
git commit -m "feat: pintar en cian los LEDs de un retrigger activo"
```

---

### Task 3: Verificación en hardware (requiere al usuario con la placa)

**Files:** ninguno

- [ ] **Step 1: Grabar** `build-gamepi/pikocore.uf2`.
- [ ] **Step 2: Checklist**
  1. Presionar un solo botón musical: el LED correspondiente se prende naranja, como
     siempre antes de este cambio (sin regresión).
  2. Presionar dos botones musicales a la vez (activa retrigger): los dos LEDs
     correspondientes cambian a **cian** mientras ambos estén presionados.
  3. Soltar uno de los dos botones: el cian desaparece de inmediato en ambos LEDs, vuelve
     el comportamiento naranja normal.
  4. Con el dashboard refrescándose activamente (LEDs moviéndose con el beat) probar
     varias combinaciones de 2 botones distintas — confirmar que siempre son los 2 LEDs
     correctos los que cambian de color, no otros.
  5. Regresión general: el resto del dashboard, los combos de 3-4 botones, y el modo
     Browse SD siguen funcionando igual que al cierre de la Fase 3.
- [ ] **Step 3: Si algo falla de forma difícil de diagnosticar**

```bash
git log --oneline -5
```

Este cambio son 2 commits chicos y aislados sobre un punto ya verificado (cierre de Fase
3) — `git revert` de ambos alcanza para volver atrás sin perder nada más.
