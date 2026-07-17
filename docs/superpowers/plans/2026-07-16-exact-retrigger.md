# Retrigger con subdivisión exacta — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mantener Start presionado en el instante de disparar un retrigger/stutter (combo de 2 botones) fija la subdivisión a un valor exacto (el punto medio de la ventana que hoy se sortea) en vez de aleatorio, sin afectar ninguna otra capa del efecto ni el hardware original.

**Architecture:** Una rama condicional dentro del bloque de trigger de retrigger, ya existente en `pwm_interrupt_handler()` (`src/main.cpp`), envuelta en `#if PIKO_GAMEPI13` porque lee `btn_start` (no existe en el hardware original). Reutiliza el mismo patrón de lectura sin locks de estado compartido entre ISR y loop principal que ya usa el resto del archivo.

**Tech Stack:** C/C++17, pico-sdk 2.1.1. Un solo archivo: `src/main.cpp`.

**Spec:** `docs/superpowers/specs/2026-07-16-exact-retrigger-design.md` (aprobado). Rama: `port/rp2350-gamepi13`.

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

1. **El bloque de trigger de retrigger vive en `pwm_interrupt_handler()`** (la ISR de
   audio, `src/main.cpp`), dentro de `if (btn_retrig && !fx_retrig) { ... }`. Es código
   **compartido** entre el build original y el de GamePi13 (existe en ambos, sin
   `#if PIKO_GAMEPI13` alrededor del bloque completo).
2. **`btn_start` (el objeto `Button` de Start) solo existe bajo `#if PIKO_GAMEPI13`**
   (`src/main.cpp` línea ~120, `Button btn_select, btn_start, btn_l, btn_r;`) — el
   hardware original no tiene un botón Start dedicado. Cualquier referencia a `btn_start`
   fuera de un bloque `#if PIKO_GAMEPI13` rompe la compilación del build original.
3. **`gamepi_start_used_as_modifier`** (bool, también bajo `#if PIKO_GAMEPI13`,
   `src/main.cpp` línea ~127) es el flag existente que evita que soltar Start después de
   usarlo como modificador dispare el toggle de mute/start-stop. Se marca `true` hoy
   dentro del bloque de Function A/B (L/R) cuando `active_knob == 2`; este plan lo marca
   también desde el nuevo camino.
4. **`retrig_sel`** es `uint8_t`, índice 0-18 en la tabla `retrig_q8[19]` de
   `retrig_len()`. La ventana aleatoria actual por botón (`button_on2`, 0-7) es:
   `randint(0,2)`, `randint(2,4)`, `randint(4,6)`, `randint(6,8)`, `randint(8,10)`,
   `randint(10,12)`, `randint(12,14)`, `randint(14,16)` — el punto medio exacto de cada
   una es `1, 3, 5, 7, 9, 11, 13, 15`.
5. **Lectura de `btn_start` desde dentro de la ISR de audio** sigue el mismo patrón sin
   locks ya usado por `bpm_set`/`distortion`/`sample`/`btn_retrig` en este archivo — no es
   sincronización nueva, es el mismo estilo ya aceptado en todo el proyecto.

### Reglas

- El chequeo de `btn_start.On()` y todo lo que dependa de él queda envuelto en
  `#if PIKO_GAMEPI13 ... #endif`. El build original (flag OFF) debe quedar con
  comportamiento **idéntico** al actual — no solo "compila", sino que el `.uf2` resultante
  no cambia de tamaño/contenido.
- No se toca `retrig_max`, pitch, filtro, ni reducción de volumen.
- El task termina con AMBOS builds compilando (`MAKE_OK` ×2) y un commit.

---

### Task 1: Subdivisión exacta con Start sostenido

**Files:**
- Modify: `src/main.cpp`

- [ ] **Step 1: Reemplazar el bloque de selección de `retrig_sel`**

Buscar (dentro de `pwm_interrupt_handler()`, el bloque completo sin cambios):
```cpp
        if (button_on2 >= NUM_BUTTONS) {
          retrig_sel = randint(2, 16);
        } else {
          switch (button_on2) {
            case 0:
              retrig_sel = randint(0, 2);
              break;
            case 1:
              retrig_sel = randint(2, 4);
              break;
            case 2:
              retrig_sel = randint(4, 6);
              break;
            case 3:
              retrig_sel = randint(6, 8);
              break;
            case 4:
              retrig_sel = randint(8, 10);
              break;
            case 5:
              retrig_sel = randint(10, 12);
              break;
            case 6:
              retrig_sel = randint(12, 14);
              break;
            case 7:
              retrig_sel = randint(14, 16);
              break;
          }
        }
```
Reemplazar por:
```cpp
        if (button_on2 >= NUM_BUTTONS) {
          retrig_sel = randint(2, 16);
        } else {
          bool exact_retrig = false;
#if PIKO_GAMEPI13
          // Holding Start at the exact instant a 2-button retrigger fires
          // fixes the subdivision instead of sorting it, for predictable
          // live control. Reuses the button-held-as-modifier flag so
          // releasing Start afterward doesn't also trigger the mute/
          // start-stop toggle (same pattern the Function A/B L/R block
          // already uses).
          if (btn_start.On()) {
            exact_retrig = true;
            gamepi_start_used_as_modifier = true;
          }
#endif
          if (exact_retrig) {
            // Midpoint of the same window sorted below, per button_on2 --
            // keeps the existing "button 0 = slowest, button 7 = fastest"
            // feel, just removes the randomness.
            static const uint8_t kExactRetrigSel[8] = {1, 3, 5, 7, 9, 11, 13, 15};
            retrig_sel = kExactRetrigSel[button_on2];
          } else {
            switch (button_on2) {
              case 0:
                retrig_sel = randint(0, 2);
                break;
              case 1:
                retrig_sel = randint(2, 4);
                break;
              case 2:
                retrig_sel = randint(4, 6);
                break;
              case 3:
                retrig_sel = randint(6, 8);
                break;
              case 4:
                retrig_sel = randint(8, 10);
                break;
              case 5:
                retrig_sel = randint(10, 12);
                break;
              case 6:
                retrig_sel = randint(12, 14);
                break;
              case 7:
                retrig_sel = randint(14, 16);
                break;
            }
          }
        }
```

- [ ] **Step 2: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/pikocore.uf2` (original) debe quedar con el mismo tamaño/MD5
que antes de este cambio — verificar explícitamente (hash antes y después), ya que este es
el primer cambio de esta serie que toca código compartido entre ambos builds (no solo
código detrás de `#if PIKO_GAMEPI13`).

- [ ] **Step 3: Commit**

```bash
git add src/main.cpp
git commit -m "feat: retrigger con subdivision exacta manteniendo Start"
```

---

### Task 2: Verificación en hardware (requiere al usuario con la placa)

**Files:** ninguno

- [ ] **Step 1: Grabar** `build-gamepi/pikocore.uf2`.
- [ ] **Step 2: Checklist**
  1. Combinar 2 botones musicales SIN Start: el retrigger suena como siempre (sorteado,
     variable entre intentos con el mismo par de botones).
  2. Combinar 2 botones musicales CON Start sostenido: la subdivisión es **siempre la
     misma** para un mismo segundo botón — repetible, predecible.
  3. Probar los 8 valores de segundo botón con Start sostenido: cada uno debe sonar en una
     velocidad de subdivisión claramente distinta y consistente entre intentos.
  4. Soltar Start justo después de un retrigger exacto: no debe disparar el toggle de
     mute/start-stop (verificar que el audio sigue sonando normal, no se silencia).
  5. Retrigger disparado por probabilidad (sin segundo botón, `probability_retrig`), con y
     sin Start sostenido: sin cambios en ningún caso (Start no tiene efecto aquí).
  6. Regresión: pitch up/down, filtro, y reducción de volumen del retrigger siguen
     sorteando igual que antes, tanto con Start sostenido como sin él.
  7. Regresión general: el resto del instrumento (modos, SD, waveform, tempo) sigue
     funcionando igual.
- [ ] **Step 3: Regresión en hardware original** (si el usuario tiene acceso a esa build):
  grabar `build/pikocore.uf2` (flag OFF) y confirmar que el retrigger se comporta
  exactamente igual que antes de este cambio — no hay Start en ese hardware, así que no
  debería notarse ninguna diferencia.
- [ ] **Step 4: Si algo falla de forma difícil de diagnosticar**

Es un solo commit, aislado y fácil de revertir con `git revert` sin afectar nada anterior.

---

### Task 3: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: Sección 2** — en la tabla de retrigger/stutter (dos botones musicales),
  agregar una nota: mantener Start en el instante del combo fija la subdivisión al punto
  medio de la ventana del segundo botón, en vez de sortearla — con la tabla de 8 valores
  exactos (botón 0→nivel 1, ..., botón 7→nivel 15).
- [ ] **Step 2: Sección 6** — quitar el bullet "Exponer el retrigger de forma menos
  aleatoria" (ya no es futuro) y agregar la entrada RESUELTO correspondiente en la
  sección 5, con referencia al spec.
- [ ] **Step 3: Commit**

```bash
git add GAMEPI13-INTERFACE.md
git commit -m "docs: documentar el retrigger con subdivision exacta"
```
