# Select + botón musical → salto directo de modo — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mientras Select está sostenido, presionar un botón musical (0-7) salta directo a ese modo; un toque simple de Select sigue ciclando +1 como siempre. El motor de audio no reacciona al botón musical usado como parte del combo.

**Architecture:** Se consolida la lectura de flancos de los 8 botones musicales en un array calculado una vez por tick (corrige una fragilidad latente en los 3 combos de 4 botones ya existentes, que compartían índices y consumían el flag cada uno por su cuenta). Select gana un doble rol (toque vs. mantenido-modificador) espejando el patrón ya usado para Start. El escaneo de jump/retrigger en la ISR de audio se pausa mientras Select está sostenido.

**Tech Stack:** C/C++17, pico-sdk 2.1.1. Un solo archivo: `src/main.cpp`.

**Spec:** `docs/superpowers/specs/2026-07-16-select-direct-mode-jump-design.md` (aprobado). Rama: `port/rp2350-gamepi13`.

---

## Contexto para quien ejecuta

### Entorno de build (Windows) — igual que en toda la sesión

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

`BUILDDIR` = `build` (original) o `build-gamepi` (GamePi13). No se toca `CMakeLists.txt`,
no hace falta reconfigurar. Borrar el `.bat` temporal al terminar.

### Hechos ya verificados (no re-descubrir)

1. **Los 3 combos de 4 botones existentes** (clock lock: botones 1,2,5,6; reset FX:
   0,1,6,7; mute/start-stop heredado: 0,3,4,7 — todos código COMPARTIDO, sin
   `#if PIKO_GAMEPI13`) viven dentro de un `for (i=0..7) { input_button[i].Read(); ...}` en
   `src/main.cpp`, evaluándose redundantemente 8 veces por tick (inocuo hoy porque no
   dependen de `i`, pero confuso). Cada uno llama `ChangedHigh(true)` de forma
   independiente sobre índices que se solapan entre sí.
2. **`Button::ChangedHigh(true)`/`Changed(true)` consumen el flag de cambio una sola vez**
   (`doth/button.h`) — dos llamadas separadas sobre el MISMO botón en el MISMO tick
   pueden pisarse. Ya nos pasó con Start esta sesión; el fix ahí fue consolidar en una
   sola llamada `Changed(true)` y ramificar con `Rising()`/`Falling()`. Este plan aplica
   la misma lección a los 8 botones musicales de forma general (un array, no una
   variable).
3. **`btn_select`/`gamepi_start_used_as_modifier` solo existen bajo `#if PIKO_GAMEPI13`**
   — el hardware original no tiene Select ni Start dedicados. El escaneo de jump
   (`pwm_interrupt_handler()`, "check button 1"/"check button 2") es código COMPARTIDO;
   cualquier referencia a `btn_select` ahí necesita su propio guard.
4. **Orden de botones musicales = orden de modos**: Up=0, Down=1, Left=2, Right=3, Y=4,
   X=5, B=6, A=7 (mismo array `GAMEPI_BUTTON_PINS` de `src/hw_gamepi13.h`, mismo orden que
   ya usa la tabla de 8 modos de Function A/B).

### Reglas

- Las Tasks 2 y 4 tocan código COMPARTIDO con el build original (no todo detrás de
  `#if PIKO_GAMEPI13`) — a diferencia de tareas anteriores de esta sesión donde el build
  original quedaba byte-idéntico, acá el comportamiento debe ser idéntico pero el binario
  compilado del build original **puede** diferir en bytes (es un refactor real de código
  compartido, no solo código nuevo detrás de un flag). La verificación real es
  comportamental (Task 5), no un hash.
- Cada task termina con AMBOS builds compilando (`MAKE_OK` ×2) y un commit.

---

### Task 1: Agregar el flag de modificador para Select

**Files:**
- Modify: `src/main.cpp`

- [ ] **Step 1: Agregar el global**

Buscar:
```cpp
bool gamepi_start_used_as_modifier = false;
```
Reemplazar por:
```cpp
bool gamepi_start_used_as_modifier = false;
// Mirrors gamepi_start_used_as_modifier: Select's own tap-vs-hold-modifier
// distinction (see the Select handler in main()) for the new "hold Select +
// musical button = jump directly to that mode" gesture.
bool gamepi_select_used_as_modifier = false;
```

- [ ] **Step 2: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/pikocore.uf2` (original) mismo tamaño/MD5 que antes — este
campo vive bajo `#if PIKO_GAMEPI13` (mismo bloque que `gamepi_start_used_as_modifier`),
así que el build original queda sin tocar en absoluto en este task.

- [ ] **Step 3: Commit**

```bash
git add src/main.cpp
git commit -m "feat: agregar flag de modificador para el gesto Select+boton"
```

---

### Task 2: Consolidar flancos de botones musicales + reescribir los 3 combos

**Files:**
- Modify: `src/main.cpp`

- [ ] **Step 1: Reemplazar el loop de lectura + los 3 combos**

Buscar (bloque completo, incluye el `for` de lectura, los 3 combos, y el bloque
`DEBUG_BUTTONS`):
```cpp
    if (clock_ms % 16 == 0) {  // 250 Hz
      // read gpio inputs
      for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
        if (midi_button1 != i && midi_button2 != i) {
          input_button[i].Read();
        }
        // if (input_button[i].ChangedHigh(false)) {
        //   MidiOut_on(midiout, midi_notes[(i % 8)], 127);
        // }
        if (input_button[1].ChangedHigh(true) ||
            input_button[2].ChangedHigh(true) ||
            input_button[5].ChangedHigh(true) ||
            input_button[6].ChangedHigh(true)) {
          if (input_button[1].On() && input_button[2].On() &&
              input_button[5].On() && input_button[6].On()) {
            debounce_lock_clock = 80;
            do_lock_clock = !do_lock_clock;
          }
        }
        if (input_button[0].ChangedHigh(true) ||
            input_button[1].ChangedHigh(true) ||
            input_button[6].ChangedHigh(true) ||
            input_button[7].ChangedHigh(true)) {
          if (input_button[0].On() && input_button[1].On() &&
              input_button[6].On() && input_button[7].On()) {
            // reset fx
            param_set_break(0, filter_fc, distortion, probability_jump,
                            probability_retrig, probability_gate,
                            probability_direction, probability_tunnel,
                            save_data);
          }
        }
        if (input_button[0].ChangedHigh(true) ||
            input_button[3].ChangedHigh(true) ||
            input_button[4].ChangedHigh(true) ||
            input_button[7].ChangedHigh(true)) {
          // button combo
          if (input_button[0].On() && input_button[3].On() &&
              input_button[4].On() && input_button[7].On()) {
            if (do_mute) {
              do_start_everything();
            } else {
              do_stop_everything();
            }
            // printf("switching do mute: %d\n", do_mute);
          }
        }
#ifdef DEBUG_BUTTONS
        if (input_button[i].Changed(false)) {
          printf("[%6d] %d: %d", clock_ms, i, input_button[i].On());
          if (input_button[i].Rising()) {
            printf("rising");
          }
          if (input_button[i].Falling()) {
            printf("falling");
          }
          printf("\n");
        }
#endif
      }
```
Reemplazar por:
```cpp
    if (clock_ms % 16 == 0) {  // 250 Hz
      // read gpio inputs
      for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
        if (midi_button1 != i && midi_button2 != i) {
          input_button[i].Read();
        }
        // if (input_button[i].ChangedHigh(false)) {
        //   MidiOut_on(midiout, midi_notes[(i % 8)], 127);
        // }
#ifdef DEBUG_BUTTONS
        if (input_button[i].Changed(false)) {
          printf("[%6d] %d: %d", clock_ms, i, input_button[i].On());
          if (input_button[i].Rising()) {
            printf("rising");
          }
          if (input_button[i].Falling()) {
            printf("falling");
          }
          printf("\n");
        }
#endif
      }
      // Capture each button's rising edge ONCE per tick, after all 8 have
      // been read above. Button::ChangedHigh(true) consumes the edge (see
      // doth/button.h) -- the 3 combo checks below used to each call it
      // independently, redundantly re-evaluated once per loop iteration
      // above (harmless there since none of them depend on `i`, but the
      // combos' button-index sets overlap each other: 1 appears in both the
      // clock-lock and reset-fx combos, 0 and 7 appear in both reset-fx and
      // mute/start-stop), so one consumer could silently eat an edge before
      // another saw it -- the same class of bug already found and fixed for
      // Start earlier this project. Consolidating into one array read here
      // removes both the redundancy and that latent risk, and lets the new
      // Select+musical-button gesture (added in a later task) share the same
      // capture safely.
      bool button_rising[NUM_BUTTONS];
      for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
        button_rising[i] = input_button[i].ChangedHigh(true);
      }
      if (button_rising[1] || button_rising[2] || button_rising[5] ||
          button_rising[6]) {
        if (input_button[1].On() && input_button[2].On() &&
            input_button[5].On() && input_button[6].On()) {
          debounce_lock_clock = 80;
          do_lock_clock = !do_lock_clock;
        }
      }
      if (button_rising[0] || button_rising[1] || button_rising[6] ||
          button_rising[7]) {
        if (input_button[0].On() && input_button[1].On() &&
            input_button[6].On() && input_button[7].On()) {
          // reset fx
          param_set_break(0, filter_fc, distortion, probability_jump,
                          probability_retrig, probability_gate,
                          probability_direction, probability_tunnel,
                          save_data);
        }
      }
      if (button_rising[0] || button_rising[3] || button_rising[4] ||
          button_rising[7]) {
        // button combo
        if (input_button[0].On() && input_button[3].On() &&
            input_button[4].On() && input_button[7].On()) {
          if (do_mute) {
            do_start_everything();
          } else {
            do_stop_everything();
          }
          // printf("switching do mute: %d\n", do_mute);
        }
      }
```

- [ ] **Step 2: Build de ambas variantes**

Expected: `MAKE_OK` ×2. Este task reestructura código COMPARTIDO (los 3 combos no están
detrás de `#if PIKO_GAMEPI13`) — el binario del build original puede diferir en bytes
respecto de antes de este task, y **eso es esperado**: es un refactor comportamentalmente
equivalente, no un cambio de comportamiento. No verificar hash; la verificación real de
que los 3 combos siguen funcionando igual pasa en la Task 5 (hardware).

- [ ] **Step 3: Commit**

```bash
git add src/main.cpp
git commit -m "refactor: consolidar flancos de botones musicales en un array por tick"
```

---

### Task 3: Select con doble rol (toque vs. mantenido) + salto directo

**Files:**
- Modify: `src/main.cpp`

- [ ] **Step 1: Reemplazar el manejador de Select**

Buscar (bloque completo sin cambios):
```cpp
      if (btn_select.ChangedHigh(true) && btn_select.On()) {
        const uint8_t was = gamepi_selector;
        gamepi_selector = (gamepi_selector + 1) % 9;
        if (was == 8) {
          // Leaving Browse SD: unmount, don't leave the card open, and close
          // whatever SD screen was on-screen -- it's a persistent overlay
          // (see gamepi_ui_sd_close()'s comment), so it won't time out on
          // its own. Done BEFORE the entering-mode-0 overlay below (the only
          // mode reachable from here, since Select only increments) so that
          // overlay's real ~1s deadline isn't immediately clobbered by this
          // call's "expire right now" semantics.
          gamepi_sd_unmount_requested = true;
          gamepi_sd_state = GAMEPI_SD_IDLE;
          gamepi_ui_sd_close();
        }
        if (gamepi_selector < 8) {
          input_knob[0].SetBucket(gamepi_selector, 8);
          gamepi_ui_overlay_mode(gamepi_selector);
        } else {
          // gamepi_selector == 8: entering Browse SD, kick off the async
          // directory listing.
          gamepi_sd_state = GAMEPI_SD_LISTING;
          gamepi_sd_index = 0;
          gamepi_sd_hold_start_us = 0;
          gamepi_sd_list_done = false;
          __asm volatile("dmb" ::: "memory");
          gamepi_sd_list_requested = true;
          gamepi_ui_sd_listing();
        }
      }
```
Reemplazar por:
```cpp
      if (btn_select.Changed(true)) {
        if (btn_select.Rising()) {
          gamepi_select_used_as_modifier = false;
        } else if (btn_select.Falling() && !gamepi_select_used_as_modifier) {
          const uint8_t was = gamepi_selector;
          gamepi_selector = (gamepi_selector + 1) % 9;
          if (was == 8) {
            // Leaving Browse SD: unmount, don't leave the card open, and close
            // whatever SD screen was on-screen -- it's a persistent overlay
            // (see gamepi_ui_sd_close()'s comment), so it won't time out on
            // its own. Done BEFORE the entering-mode-0 overlay below (the only
            // mode reachable from here, since Select only increments) so that
            // overlay's real ~1s deadline isn't immediately clobbered by this
            // call's "expire right now" semantics.
            gamepi_sd_unmount_requested = true;
            gamepi_sd_state = GAMEPI_SD_IDLE;
            gamepi_ui_sd_close();
          }
          if (gamepi_selector < 8) {
            input_knob[0].SetBucket(gamepi_selector, 8);
            gamepi_ui_overlay_mode(gamepi_selector);
          } else {
            // gamepi_selector == 8: entering Browse SD, kick off the async
            // directory listing.
            gamepi_sd_state = GAMEPI_SD_LISTING;
            gamepi_sd_index = 0;
            gamepi_sd_hold_start_us = 0;
            gamepi_sd_list_done = false;
            __asm volatile("dmb" ::: "memory");
            gamepi_sd_list_requested = true;
            gamepi_ui_sd_listing();
          }
        }
      }
      if (btn_select.On() && !gamepi_select_used_as_modifier) {
        // Hold Select + a musical button to jump directly to that button's
        // mode (0-7) instead of cycling one step at a time. Mirrors Start's
        // tap-vs-hold-modifier split above -- a plain Select tap (Falling()
        // with the modifier flag still false) still cycles as before.
        for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
          if (button_rising[i]) {
            gamepi_selector = i;
            gamepi_select_used_as_modifier = true;
            input_knob[0].SetBucket(gamepi_selector, 8);
            gamepi_ui_overlay_mode(gamepi_selector);
            break;  // first musical button pressed this hold wins
          }
        }
      }
```

- [ ] **Step 2: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/pikocore.uf2` (original) mismo tamaño/MD5 que antes de este
task — este bloque completo vive dentro de `#if PIKO_GAMEPI13` (ya lo estaba antes de
este plan), así que nada de este task afecta al build original. `button_rising[]`
(declarada en la Task 2, en código compartido) sigue en scope acá porque C++ no cierra el
scope de una variable por un `#if` anidado dentro del mismo bloque de llaves.

- [ ] **Step 3: Commit**

```bash
git add src/main.cpp
git commit -m "feat: Select mantenido + boton musical salta directo al modo"
```

---

### Task 4: Pausar el escaneo de jump/retrigger de audio mientras Select está sostenido

**Files:**
- Modify: `src/main.cpp`

- [ ] **Step 1: Envolver "check button 1"/"check button 2" en `pwm_interrupt_handler()`**

Buscar (bloque completo sin cambios):
```cpp
    // check button 1
    if (button_on < NUM_BUTTONS) {
      if (!input_button[button_on].On()) {
        // button is off
        button_on = NUM_BUTTONS;
        button_on2 = NUM_BUTTONS;
        select_beat_freeze = 0;
        button_filter_on = false;
        // hm
        retrig_volume_reduce = 0;
        retrig_volume_reduce_change = 0;  // reset

        if (btn_reset) {
          retrig_count = retrig_max;
        }
      }
    } else if (do_mute_debounce == 0) {
      for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
        if (input_button[i].On()) {
          if (button_on >= NUM_BUTTONS) {
            select_beat_freeze = (select_beat / NUM_BUTTONS) * NUM_BUTTONS;
          }
          button_on = i;

// select new beat
#ifdef DEBUG_BUTTONS
          printf("%d on\n", button_on);
#endif
          break;
        }
      }
    }

    // check button 2
    if (button_on2 < NUM_BUTTONS) {
      if (!input_button[button_on2].On()) {
        button_on2 = NUM_BUTTONS;
        button_filter_on = false;
      }
    }
```
Reemplazar por:
```cpp
#if PIKO_GAMEPI13
    // Pausing the beat-select scan below while Select is held keeps a
    // musical button used as part of "Select + button = jump to mode N"
    // (see the Select handler in main()) from also making the audio engine
    // jump/retrigger on that same press. btn_select only exists under
    // PIKO_GAMEPI13, hence the guard; the original build's gate is always
    // false (never pauses), i.e. unchanged behavior there.
    const bool gamepi_paused_for_select = btn_select.On();
#else
    const bool gamepi_paused_for_select = false;
#endif
    // check button 1
    if (!gamepi_paused_for_select) {
      if (button_on < NUM_BUTTONS) {
        if (!input_button[button_on].On()) {
          // button is off
          button_on = NUM_BUTTONS;
          button_on2 = NUM_BUTTONS;
          select_beat_freeze = 0;
          button_filter_on = false;
          // hm
          retrig_volume_reduce = 0;
          retrig_volume_reduce_change = 0;  // reset

          if (btn_reset) {
            retrig_count = retrig_max;
          }
        }
      } else if (do_mute_debounce == 0) {
        for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
          if (input_button[i].On()) {
            if (button_on >= NUM_BUTTONS) {
              select_beat_freeze = (select_beat / NUM_BUTTONS) * NUM_BUTTONS;
            }
            button_on = i;

// select new beat
#ifdef DEBUG_BUTTONS
            printf("%d on\n", button_on);
#endif
            break;
          }
        }
      }
    }

    // check button 2
    if (!gamepi_paused_for_select) {
      if (button_on2 < NUM_BUTTONS) {
        if (!input_button[button_on2].On()) {
          button_on2 = NUM_BUTTONS;
          button_filter_on = false;
        }
      }
    }
```

- [ ] **Step 2: Build de ambas variantes**

Expected: `MAKE_OK` ×2. En el build original, `gamepi_paused_for_select` es
`const bool ... = false;` y el compilador debería eliminar la rama `if (!false)` por
constant-folding, produciendo código idéntico — pero no es una garantía absoluta según
nivel de optimización. Verificar el hash de `build/pikocore.uf2`; si difiere, no es un
fallo del task (ver nota de la Task 2 sobre por qué esto ya no aplica estrictamente en
esta serie de cambios) — confirmar razonando sobre el código en vez de bloquear el task
por eso.

- [ ] **Step 3: Commit**

```bash
git add src/main.cpp
git commit -m "feat: pausar el escaneo de jump de audio mientras Select esta sostenido"
```

---

### Task 5: Verificación en hardware (requiere al usuario con la placa)

**Files:** ninguno

- [ ] **Step 1: Grabar** `build-gamepi/pikocore.uf2`.
- [ ] **Step 2: Checklist — gesto nuevo**
  1. Sostener Select y presionar cada uno de los 8 botones musicales (Up, Down, Left,
     Right, Y, X, B, A): salta al modo 0, 1, 2, 3, 4, 5, 6, 7 respectivamente — overlay
     visible con el nombre del modo.
  2. Soltar Select sin haber tocado ningún botón musical: cicla +1 como siempre.
  3. Mientras se mantiene el botón musical usado para saltar (con Select todavía
     sostenido): el audio NO reacciona (sin jump audible, sin cambio en la waveform/LEDs).
  4. Soltar Select después de usarlo como modificador: no cicla de nuevo al soltar.
- [ ] **Step 3: Checklist — regresión de los 3 combos existentes**
  1. Combo clock lock (Down+Left+X+B): sigue alternando el lock como antes.
  2. Combo reset FX (Up+Down+B+A): sigue reseteando filtro/distorsión/probabilidades.
  3. Combo mute/start-stop heredado (Up+Right+Y+A): sigue alternando mute/start-stop.
- [ ] **Step 4: Checklist — regresión general**
  1. Jump normal (un solo botón musical, sin Select): funciona igual que siempre.
  2. Retrigger (dos botones musicales, aleatorio y exacto con Start sostenido): sin
     cambios respecto a la fase anterior.
  3. Modo Browse SD, waveform, tempo: sin cambios.
- [ ] **Step 5: Regresión en hardware original** (flag OFF, si el usuario tiene acceso):
  los 3 combos de 4 botones se comportan exactamente igual que antes de este cambio (no
  hay Select en ese hardware, así que el gesto nuevo no aplica ahí en absoluto).
- [ ] **Step 6: Si algo falla de forma difícil de diagnosticar**

Son 4 commits chicos y secuenciales sobre un punto ya verificado — revertir el último
(`git revert`) y volver a probar acota rápidamente en cuál de los 4 está el problema.

---

### Task 6: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: Sección 3** — agregar una nota sobre el gesto Select+botón musical (salto
  directo a modo 0-7), con la tabla de mapeo botón→modo.
- [ ] **Step 2: Sección 5** — agregar entrada RESUELTO sobre la fragilidad latente
  encontrada y corregida en los 3 combos de 4 botones (consumo de flag compartido entre
  combos con índices solapados), con referencia al spec.
- [ ] **Step 3: Commit**

```bash
git add GAMEPI13-INTERFACE.md
git commit -m "docs: documentar Select + boton musical (salto directo de modo)"
```
