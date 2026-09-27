# Colores por modo (barras Function A/B) — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el color fijo (rosa/cian) de las barras de Function A/B por un
color propio de cada uno de los 8 modos, y borrar los dos assets huérfanos
(`kSampleBar`/`kBreakFxBar`) que nunca se usaron.

**Architecture:** Dos tablas nuevas de 8 elementos (`kModeColorA`/`kModeColorB`) en
`src/gamepi13/ui.cpp`, indexadas por modo igual que las tablas ya existentes
(`kModeA`, `kModeABitmap`, etc.). `draw_function_a()`/`draw_function_b()` dejan de
pasar `COL_PINK`/`COL_CYAN` fijos y usan `kModeColorA[m]`/`kModeColorB[m]`.

**Tech Stack:** C/C++17, sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-19-mode-colors-design.md` (aprobado).
Rama: `port/rp2350-gamepi13`.

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

Solo `build-gamepi` compila estos archivos (100% exclusivos de GamePi13).

### Hallazgos que hay que respetar

- **`kSampleBar` (línea 48) y `kBreakFxBar` (línea 64) de `src/gamepi13/ui_bitmaps.h`
  nunca se usan en ningún lado de `ui.cpp`** — `draw_bar()` siempre dibuja un
  rectángulo programático liso, nunca esas imágenes. Se borran por completo, mismo
  patrón que `kFilenameFrame`/`kWaveformFrame` (sub-proyecto anterior). Son arrays de
  una sola línea cada uno — se borran vía `sed` por patrón, no a mano.
- **Paleta ya aprobada visualmente** (mockup en el navegador, spec):

  | Modo | Function A | Function B |
  |---|---|---|
  | 0 | Rojo `#f87171` | Azul `#60a5fa` |
  | 1 | Naranja `#fb923c` | Violeta `#a78bfa` |
  | 2 | Amarillo `#facc15` | Rosa `#f472b6` |
  | 3 | Verde `#4ade80` | Rojo `#f87171` |
  | 4 | Cian `#22d3ee` | Naranja `#fb923c` |
  | 5 | Azul `#60a5fa` | Amarillo `#facc15` |
  | 6 | Violeta `#a78bfa` | Verde `#4ade80` |
  | 7 | Rosa `#f472b6` | Cian `#22d3ee` |

  `COL_GREEN`/`COL_BLUE`/`COL_PINK` ya existen (`src/gamepi13/ui.cpp` líneas 24-26) y
  se reutilizan tal cual. Los 5 valores RGB565 nuevos (`COL_RED`, `COL_ORANGE2`,
  `COL_YELLOW`, `COL_TEAL`, `COL_VIOLET`) ya están calculados y verificados en el spec
  contra la fórmula estándar (confirmada reproduciendo `COL_BLUE` desde su hex web
  antes de aceptarlos) — no recalcular a mano.
- `draw_function_label()`'s parámetro `text_col` (usado solo en su rama `else`, hoy
  inalcanzable porque los 8 modos ya tienen bitmap) se actualiza igual, por
  consistencia y robustez ante un futuro bitmap faltante.

### Reglas de la fase

- Cada task termina con `build-gamepi` compilando (`MAKE_OK`) y un commit.

---

### Task 1: Agregar la paleta y las tablas de color por modo

**Files:**
- Modify: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Agregar las 5 macros de color nuevas, justo después de la paleta
      existente**

Buscar:
```cpp
#define COL_GRAY 0x632C      // #666666
#define COL_DARK 0x18C3      // #1a1a1a
```

Reemplazar:
```cpp
#define COL_GRAY 0x632C      // #666666
#define COL_DARK 0x18C3      // #1a1a1a
#define COL_RED 0xFB8E       // #f87171
#define COL_ORANGE2 0xFC87   // #fb923c (distinto de COL_ORANGE/amber ya existente)
#define COL_YELLOW 0xFE62    // #facc15
#define COL_TEAL 0x269D      // #22d3ee
#define COL_VIOLET 0xA45F    // #a78bfa
```

- [ ] **Step 2: Agregar las dos tablas de color por modo, justo antes de
      `draw_function_a()`**

Buscar:
```cpp
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

Reemplazar:
```cpp
// Un color por modo para la barra de Function A/B (y el fallback de texto de
// draw_function_label(), aunque hoy sea inalcanzable con los 8 modos ya
// bitmapeados). Ver docs/superpowers/specs/2026-07-19-mode-colors-design.md.
static const uint16_t kModeColorA[8] = {COL_RED,     COL_ORANGE2, COL_YELLOW, COL_GREEN,
                                        COL_TEAL,    COL_BLUE,    COL_VIOLET, COL_PINK};
static const uint16_t kModeColorB[8] = {COL_BLUE,    COL_VIOLET,  COL_PINK,   COL_RED,
                                        COL_ORANGE2, COL_YELLOW,  COL_GREEN,  COL_TEAL};

static void draw_function_a(const GamepiUiState &s) {
  clear_zone(kRect[W_BARA]);
  const uint8_t m = (s.mode < 8) ? s.mode : 0;
  draw_function_label(107, kModeABitmap[m], kModeA[m], kModeColorA[m]);
  draw_bar(132, s.knob_a, kModeColorA[m]);
}

static void draw_function_b(const GamepiUiState &s) {
  clear_zone(kRect[W_BARB]);
  const uint8_t m = (s.mode < 8) ? s.mode : 0;
  draw_function_label(157, kModeBBitmap[m], kModeB[m], kModeColorB[m]);
  draw_bar(182, s.knob_b, kModeColorB[m]);
}
```

- [ ] **Step 3: Build**

```bash
cat > /c/pikocore-main/rebuild_mc1.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_mc1.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar.

- [ ] **Step 4: Commit**

```bash
cd /c/pikocore-main
git add src/gamepi13/ui.cpp
git commit -m "feat: colorear las barras de Function A/B segun el modo activo"
```

---

### Task 2: Borrar los assets huérfanos `kSampleBar`/`kBreakFxBar`

**Files:**
- Modify: `src/gamepi13/ui_bitmaps.h`

- [ ] **Step 1: Borrar las dos líneas**

```bash
cd /c/pikocore-main/src/gamepi13
sed -i '/^static const uint16_t kSampleBar\[\]/d' ui_bitmaps.h
sed -i '/^static const uint16_t kBreakFxBar\[\]/d' ui_bitmaps.h
```

- [ ] **Step 2: Verificar que ya no queda ninguna referencia**

```bash
grep -rn "kSampleBar\|kBreakFxBar" /c/pikocore-main/src/gamepi13/
```

Expected: sin resultados.

- [ ] **Step 3: Build**

```bash
cat > /c/pikocore-main/rebuild_mc2.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_mc2.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar.

- [ ] **Step 4: Commit**

```bash
git add src/gamepi13/ui_bitmaps.h
git commit -m "fix: borrar los arrays kSampleBar/kBreakFxBar (nunca se usaron)"
```

---

### Task 3: Verificación en hardware (requiere al usuario con la placa)

No delegar a un subagente -- requiere el dispositivo físico. Pasos a pedirle al
usuario:

1. Flashear `build-gamepi/pikocore.uf2` en el GamePi13.
2. Recorrer los 8 modos (Select) y confirmar que la barra de Function A y la de
   Function B cambian de color según esta tabla:

   | Modo | Function A | Function B |
   |---|---|---|
   | 0 | Rojo | Azul |
   | 1 | Naranja | Violeta |
   | 2 | Amarillo | Rosa |
   | 3 | Verde | Rojo |
   | 4 | Cian | Naranja |
   | 5 | Azul | Amarillo |
   | 6 | Violeta | Verde |
   | 7 | Rosa | Cian |

3. Confirmar que ningún color se ve mal (ilegible, demasiado oscuro/saturado) contra
   el fondo negro del LCD real.
4. Confirmar que modo 8 (Browse SD) no se ve afectado (sus zonas de barra están
   cubiertas por el overlay persistente).
5. Regresión: geometría/posición de las barras, etiquetas de Function A/B (texto o
   bitmap), y el resto del dashboard sin cambios.

Si algún color se ve mal en el LCD real, ajustar el valor RGB565 correspondiente en
`kModeColorA`/`kModeColorB` (`src/gamepi13/ui.cpp`) y repetir la verificación — no es
necesario volver al spec para un ajuste de tono puntual.

---

### Task 4: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: Actualizar la sección 4 para mencionar el color por modo**

Buscar:
```markdown
**zona de waveform** (contenido dinámico sin cambios, ver detalle abajo); etiquetas de
Function A/B como gráfico para los 8 modos (0-7), cada una sobre su propia barra; y una fila
de 9 íconos de modo (reemplaza los 8 puntos + el caso especial de texto "SD") — el
```

Reemplazar:
```markdown
**zona de waveform** (contenido dinámico sin cambios, ver detalle abajo); etiquetas de
Function A/B como gráfico para los 8 modos (0-7), cada una sobre su propia barra y con
un color propio por modo (ver tabla más abajo); y una fila de 9 íconos de modo
(reemplaza los 8 puntos + el caso especial de texto "SD") — el
```

- [ ] **Step 2: Agregar la tabla de colores justo después de la tabla de modos de la
      sección 3**

Buscar:
```markdown
Cada ajuste de L/R mueve el valor virtual del knob en pasos de `GAMEPI_KNOB_STEP` (164,
```

Reemplazar:
```markdown
| Modo | Color Function A | Color Function B |
|---|---|---|
| 0 | Rojo | Azul |
| 1 | Naranja | Violeta |
| 2 | Amarillo | Rosa |
| 3 | Verde | Rojo |
| 4 | Cian | Naranja |
| 5 | Azul | Amarillo |
| 6 | Violeta | Verde |
| 7 | Rosa | Cian |

Cada ajuste de L/R mueve el valor virtual del knob en pasos de `GAMEPI_KNOB_STEP` (164,
```

- [ ] **Step 3: Commit**

```bash
git add GAMEPI13-INTERFACE.md
git commit -m "docs: documentar los colores por modo de las barras Function A/B"
```
