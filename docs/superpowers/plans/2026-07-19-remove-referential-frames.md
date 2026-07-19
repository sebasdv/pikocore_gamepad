# Quitar frames referenciales del dashboard — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quitar el dibujo de `filename_sample_frame`/`waveform_frame` (eran guías de
layout de Lopaka, no assets reales) y borrar sus dos arrays de `ui_bitmaps.h` por
completo.

**Architecture:** Cambio puramente sustractivo en dos archivos ya existentes —
`src/gamepi13/ui.cpp` (dos llamadas a `Paint_DrawImage` menos) y
`src/gamepi13/ui_bitmaps.h` (dos arrays menos, borrados vía `sed` para no tener que
manipular las líneas de datos a mano).

**Tech Stack:** C/C++17, sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-19-remove-referential-frames-design.md`
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

Solo `build-gamepi` compila estos archivos (100% exclusivos de GamePi13) — no hace
falta tocar ni verificar `build` (original).

### Hallazgos que hay que respetar

- **`kFilenameFrame`/`kWaveformFrame` son arrays de una sola línea** (miles de valores
  hexadecimales cada uno) en `src/gamepi13/ui_bitmaps.h` — no se manipulan a mano.
  `sed` borra la línea completa por patrón (cada array vive en exactamente una línea,
  confirmado en el Task 1 original que generó este archivo).
- Las dos llamadas a dibujarlos en `src/gamepi13/ui.cpp` (`draw_name()`/`draw_wave()`)
  sí son ediciones normales de texto (una línea corta cada una).

### Reglas de la fase

- Cada task termina con `build-gamepi` compilando (`MAKE_OK`) y un commit.

---

### Task 1: Quitar las llamadas a dibujar los frames

**Files:**
- Modify: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Quitar el dibujo de `kFilenameFrame` en `draw_name()`**

Buscar:
```cpp
static void draw_name(const GamepiUiState &s) {
  clear_zone(kRect[W_NAME]);
  Paint_DrawImage((const unsigned char *)kFilenameFrame, 0, 29, 191, 20);
  char buf[48];
```

Reemplazar:
```cpp
static void draw_name(const GamepiUiState &s) {
  clear_zone(kRect[W_NAME]);
  char buf[48];
```

- [ ] **Step 2: Quitar el dibujo de `kWaveformFrame` en `draw_wave()`**

Buscar:
```cpp
static void draw_wave(const GamepiUiState &s) {
  clear_zone(kRect[W_WAVE]);
  Paint_DrawImage((const unsigned char *)kWaveformFrame, 0, 54, 240, 48);
  constexpr uint16_t kTop = 54;  // 39px band inside the 52..96 zone
```

Reemplazar:
```cpp
static void draw_wave(const GamepiUiState &s) {
  clear_zone(kRect[W_WAVE]);
  constexpr uint16_t kTop = 54;  // 39px band inside the 52..96 zone
```

- [ ] **Step 3: Build**

Este task deja `build-gamepi` roto a propósito hasta el Task 2 (todavía existen
`kFilenameFrame`/`kWaveformFrame` en `ui_bitmaps.h`, pero ya no se referencian en
`ui.cpp` — esto SÍ compila igual, ya que tener un array sin usar no es un error en
C++, solo una advertencia de "unused variable" si el compilador la tiene habilitada).
Confirmar igual:

```bash
cat > /c/pikocore-main/rebuild_rf1.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_rf1.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar.

- [ ] **Step 4: Commit**

```bash
git add src/gamepi13/ui.cpp
git commit -m "fix: dejar de dibujar filename_sample_frame/waveform_frame (eran guias de Lopaka, no assets reales)"
```

---

### Task 2: Borrar los dos arrays de `ui_bitmaps.h`

**Files:**
- Modify: `src/gamepi13/ui_bitmaps.h`

- [ ] **Step 1: Borrar las líneas de `kFilenameFrame` y `kWaveformFrame`**

```bash
cd /c/pikocore-main/src/gamepi13
sed -i '/^static const uint16_t kFilenameFrame\[\]/d' ui_bitmaps.h
sed -i '/^static const uint16_t kWaveformFrame\[\]/d' ui_bitmaps.h
```

- [ ] **Step 2: Verificar que ya no queda ninguna referencia**

```bash
grep -rn "kFilenameFrame\|kWaveformFrame" /c/pikocore-main/src/gamepi13/
```

Expected: sin resultados (ni en `ui_bitmaps.h` ni en `ui.cpp`, que ya se limpió en el
Task 1).

- [ ] **Step 3: Build**

```bash
cat > /c/pikocore-main/rebuild_rf2.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_rf2.bat"
```

Expected: `MAKE_OK`, con un tamaño de flash algo menor que antes (los dos arrays
borrados suman ~15KB de datos: `kFilenameFrame` es 191×20 px × 2 bytes ≈ 7.64KB,
`kWaveformFrame` es 240×48 px × 2 bytes ≈ 23KB). Borrar el `.bat` al terminar.

- [ ] **Step 4: Commit**

```bash
git add src/gamepi13/ui_bitmaps.h
git commit -m "fix: borrar los arrays kFilenameFrame/kWaveformFrame (ya no se usan)"
```

---

### Task 3: Verificación en hardware (requiere al usuario con la placa)

No delegar a un subagente -- requiere el dispositivo físico. Pasos a pedirle al
usuario:

1. Flashear `build-gamepi/pikocore.uf2` en el GamePi13.
2. Zona de nombre de sample: el nombre y el índice/total de samples se ven
   exactamente igual que antes, sin el marco decorativo alrededor.
3. Zona de waveform: la forma de onda, el playhead y el resaltado de retrigger se ven
   exactamente igual que antes, sin el marco decorativo alrededor.
4. Regresión: el resto del dashboard (BPM, reloj, play/stop, Function A/B, 9 iconos de
   modo) sin cambios.

Si algo falla, diagnosticar leyendo el código (no adivinar) y corregir.

---

### Task 4: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: Actualizar la mención de los frames en la sección 4**

Buscar:
```markdown
**Dashboard** (siempre visible, diseñado en Lopaka — `src/gamepi13/ui_bitmaps.h`): BPM
con dígitos propios (ancho real por dígito, sin grilla fija) + ícono de fuente de clock
(INT/EXT como gráfico; MIDI todavía en texto, ver sección 6) + par de íconos play/stop
(el activo a full brillo, el otro atenuado); nombre del sample dentro de un marco
gráfico + índice/total de samples con el mismo sistema de dígitos (`NN/NN`, reemplaza
el antiguo texto "NN/MM"); **zona de waveform** con marco gráfico estático (contenido
dinámico sin cambios, ver detalle abajo); etiquetas de Function A/B ("SAMPLE"/"BREAK FX"
como gráfico en modo 0, texto en los modos 1-7 hasta que se diseñen esos gráficos, ver
sección 6) cada una sobre su propia barra; y una fila de 9 íconos de modo (reemplaza los
8 puntos + el caso especial de texto "SD") — el activo se dibuja a full color, los otros
8 se atenúan calculando su brillo en tiempo de dibujo (`dim_rgb565()`), sin necesitar
variantes de imagen "apagadas".
```

Reemplazar:
```markdown
**Dashboard** (siempre visible, diseñado en Lopaka — `src/gamepi13/ui_bitmaps.h`): BPM
con dígitos propios (ancho real por dígito, sin grilla fija) + ícono de fuente de clock
(INT/EXT como gráfico; MIDI todavía en texto, ver sección 6) + par de íconos play/stop
(el activo a full brillo, el otro atenuado); nombre del sample + índice/total de
samples con el mismo sistema de dígitos (`NN/NN`, reemplaza el antiguo texto "NN/MM");
**zona de waveform** (contenido dinámico sin cambios, ver detalle abajo); etiquetas de
Function A/B ("SAMPLE"/"BREAK FX" como gráfico en modo 0, texto en los modos 1-7 hasta
que se diseñen esos gráficos, ver sección 6) cada una sobre su propia barra; y una fila
de 9 íconos de modo (reemplaza los 8 puntos + el caso especial de texto "SD") — el
activo se dibuja a full color, los otros 8 se atenúan calculando su brillo en tiempo de
dibujo (`dim_rgb565()`), sin necesitar variantes de imagen "apagadas". Los marcos que
Lopaka mostraba alrededor del nombre de sample y de la waveform eran solo guías de
layout (la cavidad donde va el contenido dinámico), no assets pensados para dibujarse
en tiempo real -- no se renderizan.
```

- [ ] **Step 2: Commit**

```bash
git add GAMEPI13-INTERFACE.md
git commit -m "docs: aclarar que los frames de nombre de sample y waveform eran solo guias de Lopaka"
```
