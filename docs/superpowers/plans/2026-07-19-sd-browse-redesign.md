# Rediseño de la pantalla Browse SD — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adoptar el marco de Lopaka (`OVERLAY_FRAME`) como el panel compartido de las
6 pantallas del modo 8 (Browse SD), y rediseñar el contenido de la pantalla de
navegación de archivos con dígitos gráficos reales, sin marco alrededor del nombre de
archivo, y un ícono real para el hint de "L: ciclar".

**Architecture:** Dos assets nuevos vendorizados (`kSdOverlayFrame`, `kSdLCycle`) en
`src/gamepi13/ui_bitmaps.h`; resize de `kOverlay` + cambio de `overlay_show_panel()`
en `src/gamepi13/ui.cpp` (afecta las 6 pantallas automáticamente, vía los offsets
relativos ya existentes); reescritura acotada de `gamepi_ui_sd_browse()`.

**Tech Stack:** C/C++17, sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-19-sd-browse-redesign-design.md` (aprobado).
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

- Extracción mecánica vía `sed` + verificación de conteo de píxeles, mismo patrón
  usado en todos los sub-proyectos anteriores — nunca retipear arrays a mano.
- `kOverlay` (`src/gamepi13/ui.cpp`) pasa de `{20, 64, 200, 112}` a
  `{18, 50, 205, 138}` (coordenadas exactas de `OVERLAY_FRAME`).
- Las 5 pantallas sin rediseño (`gamepi_ui_sd_listing`, `_confirm_progress`,
  `_loading`, `_result`, `_error`) **no se tocan** — ya posicionan su contenido en
  offsets relativos a `kOverlay.x`/`kOverlay.y`, así que se corren solas junto con el
  resize.
- El índice/cantidad de la pantalla "browse" reutiliza `kBankDigits`/`kBankSlash` +
  `draw_digit_string()` (ya vendorizados) — no se importan dígitos nuevos.
- `BANK_NAME_FRAME` y los 4 placeholders `DIGIT_BANK_1` del mockup **no se importan**
  (guía de layout / dígito repetido, respectivamente).

### Reglas de la fase

- Cada task termina con `build-gamepi` compilando (`MAKE_OK`) y un commit.

---

### Task 1: Vendorizar `kSdOverlayFrame` y `kSdLCycle`

**Files:**
- Modify: `src/gamepi13/ui_bitmaps.h`

- [ ] **Step 1: Generar los 2 arrays y verificarlos antes de insertarlos**

```bash
cd /c/pikocore-main/src/gamepi13

extract() {
  sed -n "s/.*${2}\[\] = {\(.*\)};.*/\1/p" "$1"
}

{
  printf 'static const uint16_t kSdOverlayFrame[] = {%s};\n' "$(extract MODE_SD_OVERLAY.txt image_OVERLAY_FRAME_pixels)"
  printf 'static const uint16_t kSdLCycle[] = {%s};\n' "$(extract MODE_SD_OVERLAY.txt image_L_CYCLE_pixels)"
} > _tmp_sd_overlay_data.txt

wc -l _tmp_sd_overlay_data.txt
```

Expected: `2 _tmp_sd_overlay_data.txt`.

```bash
python3 - << 'EOF'
import re

expected = {'kSdOverlayFrame': 205*138, 'kSdLCycle': 141*15}
text = open('_tmp_sd_overlay_data.txt', encoding='utf-8').read()
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

Expected: `ALL OK`. Si algo falla, reportar BLOCKED — no parchear datos a mano.

- [ ] **Step 2: Insertar los 2 arrays en `ui_bitmaps.h`, justo después del cierre
      `};` de `kModeIcons[9]`**

El archivo hoy tiene esto (no editar a mano — usar el comando `sed` de abajo, que
inserta el contenido de `_tmp_sd_overlay_data.txt` inmediatamente después del `};`
que cierra este bloque específico):

```cpp
static const ModeIcon kModeIcons[9] = {
    {kModeIcon0, 16, 21}, {kModeIcon1, 16, 21}, {kModeIcon2, 16, 21},
    {kModeIcon3, 16, 21}, {kModeIcon4, 16, 21}, {kModeIcon5, 16, 21},
    {kModeIcon6, 16, 21}, {kModeIcon7, 16, 21}, {kModeIconSd, 31, 21},
};
```

```bash
sed -i '/^static const ModeIcon kModeIcons\[9\] = {$/,/^};$/{/^};$/r _tmp_sd_overlay_data.txt
}' ui_bitmaps.h
rm -f _tmp_sd_overlay_data.txt
```

- [ ] **Step 3: Verificar que quedaron bien insertados**

```bash
grep -c "^static const uint16_t kSdOverlayFrame\[\]\|^static const uint16_t kSdLCycle\[\]" ui_bitmaps.h
```

Expected: `2`.

```bash
grep -n "kModeIcons\[9\]\|kSdOverlayFrame\[\]\|kSdLCycle\[\]" ui_bitmaps.h
```

Expected: `kSdOverlayFrame`/`kSdLCycle` aparecen inmediatamente después del cierre `};`
de `kModeIcons[9]`, en ese orden.

- [ ] **Step 4: Build**

```bash
cat > /c/pikocore-main/rebuild_sd1.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_sd1.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar.

- [ ] **Step 5: Commit**

```bash
cd /c/pikocore-main
git add src/gamepi13/ui_bitmaps.h
git commit -m "feat: vendorizar el marco y el icono L_CYCLE del rediseno de Browse SD"
```

---

### Task 2: Marco nuevo + resize de `kOverlay`

**Files:**
- Modify: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Resize de `kOverlay`**

Buscar:
```cpp
static const Rect kOverlay = {20, 64, 200, 112};
```

Reemplazar:
```cpp
static const Rect kOverlay = {18, 50, 205, 138};
```

- [ ] **Step 2: Reemplazar el borde programático por el bitmap del marco**

Buscar:
```cpp
static void overlay_show_panel(bool persistent = false) {
  overlay_on = true;
  overlay_persistent = persistent;
  overlay_deadline_us = time_us_64() + OVERLAY_TTL_US;
  Paint_ClearWindows(kOverlay.x, kOverlay.y,
                     (uint16_t)(kOverlay.x + kOverlay.w),
                     (uint16_t)(kOverlay.y + kOverlay.h), COL_DARK);
  Paint_DrawRectangle(kOverlay.x, kOverlay.y,
                      (uint16_t)(kOverlay.x + kOverlay.w - 1),
                      (uint16_t)(kOverlay.y + kOverlay.h - 1), COL_PINK,
                      DOT_PIXEL_2X2, DRAW_FILL_EMPTY);
}
```

Reemplazar:
```cpp
static void overlay_show_panel(bool persistent = false) {
  overlay_on = true;
  overlay_persistent = persistent;
  overlay_deadline_us = time_us_64() + OVERLAY_TTL_US;
  // El bitmap ya cubre el rect completo (kOverlay.w x kOverlay.h) con su propio
  // relleno + borde -- no hace falta un Paint_ClearWindows previo.
  Paint_DrawImage((const unsigned char *)kSdOverlayFrame, kOverlay.x, kOverlay.y,
                  kOverlay.w, kOverlay.h);
}
```

- [ ] **Step 3: Build**

```bash
cat > /c/pikocore-main/rebuild_sd2.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_sd2.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar.

- [ ] **Step 4: Commit**

```bash
cd /c/pikocore-main
git add src/gamepi13/ui.cpp
git commit -m "feat: usar el marco bitmap de Lopaka en el panel de Browse SD"
```

---

### Task 3: Rediseñar `gamepi_ui_sd_browse()`

**Files:**
- Modify: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Reemplazar el cuerpo de la función**

Buscar:
```cpp
void gamepi_ui_sd_browse(const char *filename, uint32_t index, uint32_t count,
                         bool is_active) {
  if (!flush_allowed()) return;
  char pos[12];
  snprintf(pos, sizeof(pos), "%lu/%lu", (unsigned long)(index + 1),
           (unsigned long)count);
  sd_panel_title(pos, COL_GRAY);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50),
                is_active ? COL_GREEN : COL_PINK);
  // Two lines: L/R's navigation role was previously left implicit (only the
  // hold-to-load hint was shown), which read as "L does nothing" during
  // hardware testing.
  draw_truncated("L: ciclar lista", (uint16_t)(kOverlay.y + 72), COL_GRAY);
  draw_truncated(is_active ? "Cargado (banco activo)" : "Mantener R: cargar",
                (uint16_t)(kOverlay.y + 88), COL_GRAY);
  flush(kOverlay);
}
```

Reemplazar:
```cpp
void gamepi_ui_sd_browse(const char *filename, uint32_t index, uint32_t count,
                         bool is_active) {
  if (!flush_allowed()) return;
  overlay_show_panel(true);  // persistent, mismo criterio que sd_panel_title()
  char idx[8];
  snprintf(idx, sizeof(idx), "%02lu/%02lu", (unsigned long)(index + 1),
           (unsigned long)count);
  draw_digit_string(89, 72, idx, kBankDigits, kBankSlash, 7, 15, false);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 57),
                is_active ? COL_GREEN : COL_PINK);
  Paint_DrawImage((const unsigned char *)kSdLCycle, 52, 138, 141, 15);
  draw_truncated(is_active ? "Cargado (banco activo)" : "Mantener R: cargar",
                (uint16_t)(kOverlay.y + 102), COL_GRAY);
  flush(kOverlay);
}
```

- [ ] **Step 2: Build**

```bash
cat > /c/pikocore-main/rebuild_sd3.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_sd3.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar.

- [ ] **Step 3: Commit**

```bash
cd /c/pikocore-main
git add src/gamepi13/ui.cpp
git commit -m "feat: rediseñar la pantalla de navegacion de Browse SD con los assets de Lopaka"
```

---

### Task 4: Verificación en hardware (requiere al usuario con la placa)

No delegar a un subagente -- requiere el dispositivo físico. Pasos a pedirle al
usuario:

1. Flashear `build-gamepi/pikocore.uf2` en el GamePi13.
2. Entrar al modo 8 (Browse SD) sin tarjeta o con tarjeta: confirmar que las 6
   pantallas (leyendo tarjeta, navegación, progreso, cargando, resultado, error)
   muestran el marco nuevo en la posición correcta, centrado, sin recortar texto.
3. Pantalla de navegación (con tarjeta y al menos 2 archivos): confirmar que el
   índice/cantidad se ve como dígitos gráficos (no texto), que el nombre de archivo
   se ve sin marco alrededor, en verde si coincide con el banco activo o rosa si no,
   que el ícono "L: ciclar" reemplaza el texto anterior, y que el renglón inferior
   sigue mostrando "Mantener R: cargar" / "Cargado (banco activo)" correctamente.
4. Confirmar que el resto del dashboard (fuera del modo 8) no se ve afectado.

Si algún elemento se ve desalineado o con un color que no combina, es un ajuste de
constantes (coordenadas o color), no de diseño — anotar el ajuste y aplicarlo.

---

### Task 5: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: Actualizar la sección 3.1 (Browse SD) con la nueva descripción visual**

Buscar:
```markdown
- El archivo resaltado que coincide con el banco actualmente cargado se muestra en
  **verde** con el texto "Cargado (banco activo)"; el nombre del banco cargado también
  queda visible de forma persistente en el dashboard normal, junto al nombre del sample
  (`sample.wav | banco.pikobank`).
```

Reemplazar:
```markdown
- El archivo resaltado que coincide con el banco actualmente cargado se muestra en
  **verde** con el texto "Cargado (banco activo)"; el nombre del banco cargado también
  queda visible de forma persistente en el dashboard normal, junto al nombre del sample
  (`sample.wav | banco.pikobank`). La pantalla de navegación (diseñada en Lopaka,
  `src/gamepi13/ui_bitmaps.h`) muestra la posición en la lista como dígitos gráficos
  (mismo sistema del BPM/sample idx del dashboard) y un ícono para el hint de L, en vez
  de texto plano.
```

- [ ] **Step 2: Commit**

```bash
git add GAMEPI13-INTERFACE.md
git commit -m "docs: documentar el rediseno de la pantalla Browse SD"
```
