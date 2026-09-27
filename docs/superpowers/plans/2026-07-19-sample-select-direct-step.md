# Selección de sample: ajuste directo ±1 — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que un solo toque de L/R en modo 0, Function A (selección de sample) cambie
exactamente un sample, en vez de depender del mapeo genérico de posición del knob.

**Architecture:** Un `else if` nuevo en cada una de las dos ramas de L/R sostenido
(`src/main.cpp`), mismo patrón ya usado por Tempo (`is_tempo`) — evita
`input_knob[active_knob].Adjust(...)` y escribe `sample_change` directamente.

**Tech Stack:** C/C++17, sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-19-sample-select-direct-step-design.md`
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

### Hallazgos que hay que respetar

- `active_knob = btn_start.On() ? 2 : 1;` — Function A es siempre `active_knob==1`,
  Function B siempre `active_knob==2`. `is_sample_select` solo debe ser `true` para
  Function A del modo 0.
- `sample_change` (global `uint16_t`, ya existente) es la variable a escribir — no
  tocar `input_knob[1]` en este camino.
- El `case 0: // sample` viejo (lee la posición cruda del knob) no se toca — queda
  intacto pero inalcanzable en este camino, mismo patrón que dejó Tempo con su
  `case 7` viejo.
- No se toca `src/gamepi13/ui.cpp` — la barra segmentada ya lee `sample_idx`/
  `sample_count`, no depende de `input_knob[1].Value()`.

### Reglas de la fase

- Cada task termina con `build-gamepi` compilando (`MAKE_OK`) y un commit.

---

### Task 1: Ajuste directo de sample en las ramas de L/R sostenido

**Files:**
- Modify: `src/main.cpp`

- [ ] **Step 1: Agregar `is_sample_select` junto a `is_tempo`**

Buscar:
```cpp
        const bool is_tempo = (gamepi_selector == 7 && active_knob == 2);
        if (btn_l.On()) {
```

Reemplazar:
```cpp
        const bool is_tempo = (gamepi_selector == 7 && active_knob == 2);
        // Selección de sample (modo 0, Function A) tiene el mismo problema que
        // tuvo Tempo: el paso genérico de knob (GAMEPI_KNOB_STEP=164 de 4095)
        // es mucho más chico que el "casillero" de cada sample cuando el
        // banco tiene pocas muestras, así que un solo toque casi nunca
        // alcanza a cruzar al siguiente. Mismo mecanismo que is_tempo: evita
        // Adjust() y escribe sample_change directamente, ±1 por
        // toque/repetición, sin acelerar, con clamp en los extremos (sin dar
        // la vuelta) -- ver docs/superpowers/specs/2026-07-19-sample-select-direct-step-design.md.
        const bool is_sample_select = (gamepi_selector == 0 && active_knob == 1);
        if (btn_l.On()) {
```

- [ ] **Step 2: Agregar la rama de decremento en `btn_l.On()`**

Buscar:
```cpp
              param_set_bpm(new_bpm, bpm_set, beat_thresh, audio_clk_thresh);
              gamepi_start_used_as_modifier = true;
            } else {
              input_knob[active_knob].Adjust(-GAMEPI_KNOB_STEP);
              if (active_knob == 2) gamepi_start_used_as_modifier = true;
            }
            gamepi_next_repeat_l_us = now_repeat_us + GAMEPI_REPEAT_US;
```

Reemplazar:
```cpp
              param_set_bpm(new_bpm, bpm_set, beat_thresh, audio_clk_thresh);
              gamepi_start_used_as_modifier = true;
            } else if (is_sample_select) {
              const uint16_t sample_count = (uint16_t)piko_audio_sample_count();
              if (sample_count > 0 && sample_change > 0) {
                sample_change--;
                save_data[SAVE_SAMPLE] = sample_change;
              }
            } else {
              input_knob[active_knob].Adjust(-GAMEPI_KNOB_STEP);
              if (active_knob == 2) gamepi_start_used_as_modifier = true;
            }
            gamepi_next_repeat_l_us = now_repeat_us + GAMEPI_REPEAT_US;
```

- [ ] **Step 3: Agregar la rama de incremento en `btn_r.On()`**

Buscar:
```cpp
              param_set_bpm(new_bpm, bpm_set, beat_thresh, audio_clk_thresh);
              gamepi_start_used_as_modifier = true;
            } else {
              input_knob[active_knob].Adjust(GAMEPI_KNOB_STEP);
              if (active_knob == 2) gamepi_start_used_as_modifier = true;
            }
            gamepi_next_repeat_r_us = now_repeat_us + GAMEPI_REPEAT_US;
```

Reemplazar:
```cpp
              param_set_bpm(new_bpm, bpm_set, beat_thresh, audio_clk_thresh);
              gamepi_start_used_as_modifier = true;
            } else if (is_sample_select) {
              const uint16_t sample_count = (uint16_t)piko_audio_sample_count();
              if (sample_count > 0 && sample_change < sample_count - 1) {
                sample_change++;
                save_data[SAVE_SAMPLE] = sample_change;
              }
            } else {
              input_knob[active_knob].Adjust(GAMEPI_KNOB_STEP);
              if (active_knob == 2) gamepi_start_used_as_modifier = true;
            }
            gamepi_next_repeat_r_us = now_repeat_us + GAMEPI_REPEAT_US;
```

- [ ] **Step 4: Build**

```bash
cat > /c/pikocore-main/rebuild_ss1.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_ss1.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar. Si existe una carpeta `build/`
(hardware original), repetir ahí también y confirmar que compila.

- [ ] **Step 5: Commit**

```bash
cd /c/pikocore-main
git add src/main.cpp
git commit -m "feat: ajuste directo +-1 para seleccion de sample en modo 0 Function A"
```

---

### Task 2: Verificación en hardware (requiere al usuario con la placa)

No delegar a un subagente -- requiere el dispositivo físico. Pasos a pedirle al
usuario:

1. Flashear `build-gamepi/pikocore.uf2` en el GamePi13.
2. En modo 0, Function A: tocar L o R una sola vez y confirmar que cambia exactamente
   un sample (visible en el nombre de sample, y en el segmento resaltado de la barra
   una vez que pase el próximo compás).
3. Mantener presionado L o R y confirmar que sigue moviendo de a uno cada ~100ms, sin
   acelerar.
4. Llegar al primer/último sample del banco y confirmar que seguir presionando no
   hace nada (no da la vuelta).
5. Confirmar que Function B del modo 0 (intensidad de break fx) sigue funcionando
   igual que antes.
6. Regresión: Tempo (modo 7) y el resto de los modos sin cambios.

Si algo falla, diagnosticar leyendo el código (no adivinar) y corregir.

---

### Task 3: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: Actualizar la sección 3 (tabla de modos) para mencionar el ajuste
      directo de sample**

Buscar:
```markdown
Cada ajuste de L/R mueve el valor virtual del knob en pasos de `GAMEPI_KNOB_STEP` (164,
~4% de 4095) cada ~100ms mientras se mantiene presionado
([`src/hw_gamepi13.h`](src/hw_gamepi13.h)) — **excepto Tempo** (modo 7, Function B), que
tiene su propio ajuste directo sobre el BPM en vez de derivarlo del knob crudo, porque el
paso genérico traducido a BPM saltaba en números muy grandes (descubierto en pruebas de
hardware de la Fase 3): toque simple = ±1 BPM, mantener ≥1s = ±5 BPM por paso, mantener
≥3s = ±20 BPM por paso. Rango 20–360 BPM, cualquier valor entero (antes solo múltiplos
de 5).
```

Reemplazar:
```markdown
Cada ajuste de L/R mueve el valor virtual del knob en pasos de `GAMEPI_KNOB_STEP` (164,
~4% de 4095) cada ~100ms mientras se mantiene presionado
([`src/hw_gamepi13.h`](src/hw_gamepi13.h)) — **excepto Tempo** (modo 7, Function B) y
**Selección de sample** (modo 0, Function A), que tienen su propio ajuste directo en
vez de derivarlo del knob crudo. Tempo: el paso genérico traducido a BPM saltaba en
números muy grandes (descubierto en pruebas de hardware de la Fase 3): toque simple =
±1 BPM, mantener ≥1s = ±5 BPM por paso, mantener ≥3s = ±20 BPM por paso. Rango
20–360 BPM, cualquier valor entero (antes solo múltiplos de 5). Selección de sample:
un solo toque casi nunca cambiaba de sample en bancos con pocas muestras, porque el
paso genérico (164 de 4095) era mucho más chico que el "casillero" de cada sample —
ahora cada toque o repetición mueve exactamente ±1 sample, sin acelerar, con clamp en
los extremos (no da la vuelta).
```

- [ ] **Step 2: Commit**

```bash
git add GAMEPI13-INTERFACE.md
git commit -m "docs: documentar el ajuste directo de seleccion de sample"
```
