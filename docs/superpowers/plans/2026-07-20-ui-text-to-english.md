# UI: todo el texto a inglés — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pasar todo el texto on-screen del dispositivo a inglés (pantallas de Browse
SD, placeholder de sample, mensaje de error de SD, y los fallbacks de texto de las
etiquetas de modo `kModeA`/`kModeB`).

**Architecture:** Puramente sustractivo/traducción — reemplazos de literales string en
`src/gamepi13/ui.cpp` y `src/main.cpp`. Sin cambios de lógica, sin assets de Lopaka, sin
cambios de firma. Sub-proyecto #1 del refresh de UI (ver spec).

**Tech Stack:** C/C++17, sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-20-ui-refresh-elektron-design.md` (aprobado).
Rama: `port/rp2350-gamepi13`. Checkpoint de rollback: tag `pre-ui-refresh-2026-07-20`.

---

## Contexto para quien ejecuta

### Entorno de build (Windows)

Este plan toca `src/main.cpp` (compartido con el hardware original) además de
`src/gamepi13/ui.cpp` — **compilar ambos targets**.

```bash
cat > /c/pikocore-main/rebuild_both.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_GAMEPI_FAILED & exit /b 1 )
echo MAKE_GAMEPI_OK
cd /d C:\pikocore-main\build
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_ORIGINAL_FAILED & exit /b 1 )
echo MAKE_ORIGINAL_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_both.bat"
```

Expected: `MAKE_GAMEPI_OK` y `MAKE_ORIGINAL_OK`. Borrar el `.bat` al terminar.

### Hallazgos que hay que respetar

- Todos los buffers destino tienen margen para el texto en inglés:
  `gamepi_sd_redraw_error_msg[32]` ("No card or files" = 16), `draw_truncated` trunca a
  ~26 chars ("Loaded (active bank)" = 20), `uis.sample_name[22]` ("(no samples)" = 12).
- Los fallbacks `kModeA`/`kModeB` son **inalcanzables hoy** (los 8 modos tienen bitmap,
  ver `kModeABitmap`/`kModeBBitmap`), así que su traducción no se ve en pantalla — se
  hace por consistencia/limpieza, no es verificable a ojo.
- `"Cargando..."` aparece **dos veces** (en `gamepi_ui_sd_confirm_progress` y
  `gamepi_ui_sd_loading`) — hay que traducir ambas.

### Reglas de la fase

- Cada task termina con ambos targets compilando y un commit.

---

### Task 1: Traducir el texto de `src/gamepi13/ui.cpp`

**Files:**
- Modify: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Fallbacks de etiquetas de modo (`kModeA`/`kModeB`)**

Buscar:
```cpp
static const char *kModeA[8] = {"SAMPLE",     "FILTRO",     "GATE",
                                "PROB SALTO", "PROB TUNEL", "SEC GRABAR",
                                "GUARDAR",    "VOLUMEN"};
static const char *kModeB[8] = {"BREAK FX",    "STRETCH",      "PROB GATE",
                                "PROB RETRIG", "PROB REVERSA", "SEC PLAY",
                                "CARGAR",      "TEMPO"};
```

Reemplazar:
```cpp
static const char *kModeA[8] = {"SAMPLE",    "FILTER",     "GATE",
                                "JUMP PROB", "TUNNEL PROB", "REC SEQ",
                                "SAVE",      "VOLUME"};
static const char *kModeB[8] = {"BREAK FX",   "STRETCH",     "GATE PROB",
                                "RETRIG PROB", "REVERSE PROB", "PLAY SEQ",
                                "LOAD",       "TEMPO"};
```

- [ ] **Step 2: "Leyendo tarjeta..." (en `gamepi_ui_sd_listing`)**

Buscar:
```cpp
  draw_truncated("Leyendo tarjeta...", (uint16_t)(kOverlay.y + 50), COL_WHITE);
```

Reemplazar:
```cpp
  draw_truncated("Reading card...", (uint16_t)(kOverlay.y + 50), COL_WHITE);
```

- [ ] **Step 3: Hint de banco activo / cargar (en `gamepi_ui_sd_browse`)**

Buscar:
```cpp
  draw_truncated(is_active ? "Cargado (banco activo)" : "Mantener R: cargar",
                (uint16_t)(kOverlay.y + 102), COL_GRAY);
```

Reemplazar:
```cpp
  draw_truncated(is_active ? "Loaded (active bank)" : "Hold R: load",
                (uint16_t)(kOverlay.y + 102), COL_GRAY);
```

- [ ] **Step 4: "Cargando..." (aparece 2 veces — `confirm_progress` y `loading`)**

Buscar (primera aparición, en `gamepi_ui_sd_confirm_progress`):
```cpp
  sd_panel_title("Cargando...", COL_CYAN);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50), COL_WHITE);
  uint16_t bx = (uint16_t)(kOverlay.x + (kOverlay.w - 170) / 2);
```

Reemplazar:
```cpp
  sd_panel_title("Loading...", COL_CYAN);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50), COL_WHITE);
  uint16_t bx = (uint16_t)(kOverlay.x + (kOverlay.w - 170) / 2);
```

Buscar (segunda aparición, en `gamepi_ui_sd_loading` — el comentario `// Flushed once`
la distingue):
```cpp
  // the message is guaranteed on screen before that quiet window starts.
  sd_panel_title("Cargando...", COL_CYAN);
```

Reemplazar:
```cpp
  // the message is guaranteed on screen before that quiet window starts.
  sd_panel_title("Loading...", COL_CYAN);
```

- [ ] **Step 5: Resultado "Listo"/"No se pudo cargar" (en `gamepi_ui_sd_result`)**

Buscar:
```cpp
  sd_panel_title(ok ? "Listo" : "Error", ok ? COL_GREEN : COL_PINK);
  draw_truncated(ok ? filename : "No se pudo cargar",
                 (uint16_t)(kOverlay.y + 50), COL_WHITE);
```

Reemplazar:
```cpp
  sd_panel_title(ok ? "Done" : "Error", ok ? COL_GREEN : COL_PINK);
  draw_truncated(ok ? filename : "Load failed",
                 (uint16_t)(kOverlay.y + 50), COL_WHITE);
```

(Nota: `"SD"` en `sd_panel_title("SD", ...)` y `"Error"` ya están en inglés — no se
tocan.)

- [ ] **Step 6: Verificar que no queda texto en español en `ui.cpp`**

```bash
grep -n '"Leyendo\|"Cargado\|"Mantener\|"Cargando\|"Listo\|"No se pudo\|FILTRO\|PROB \|SEC \|GUARDAR\|VOLUMEN\|CARGAR\|REVERSA\|SALTO\|TUNEL' /c/pikocore-main/src/gamepi13/ui.cpp
```

Expected: sin resultados (los comentarios en español quedan, pero no debe haber
literales string de UI en español).

- [ ] **Step 7: Build**

```bash
cat > /c/pikocore-main/rebuild_en1.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_en1.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar.

- [ ] **Step 8: Commit**

```bash
cd /c/pikocore-main
git add src/gamepi13/ui.cpp
git commit -m "feat: pasar a ingles el texto de Browse SD y los fallbacks de etiqueta de modo"
```

---

### Task 2: Traducir el texto de `src/main.cpp`

**Files:**
- Modify: `src/main.cpp`

- [ ] **Step 1: Placeholder de sample vacío**

Buscar:
```cpp
          snprintf(uis.sample_name, sizeof(uis.sample_name), "(sin samples)");
```

Reemplazar:
```cpp
          snprintf(uis.sample_name, sizeof(uis.sample_name), "(no samples)");
```

- [ ] **Step 2: Mensaje de error de SD (sin tarjeta/archivos)**

Buscar:
```cpp
                strncpy(gamepi_sd_redraw_error_msg, "Sin tarjeta o sin archivos",
```

Reemplazar:
```cpp
                strncpy(gamepi_sd_redraw_error_msg, "No card or files",
```

- [ ] **Step 3: Verificar que no queda texto de UI en español en `main.cpp`**

```bash
grep -n '"sin samples\|Sin tarjeta' /c/pikocore-main/src/main.cpp
```

Expected: sin resultados.

- [ ] **Step 4: Build ambos targets**

```bash
cat > /c/pikocore-main/rebuild_en2.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_GAMEPI_FAILED & exit /b 1 )
echo MAKE_GAMEPI_OK
cd /d C:\pikocore-main\build
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_ORIGINAL_FAILED & exit /b 1 )
echo MAKE_ORIGINAL_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_en2.bat"
```

Expected: `MAKE_GAMEPI_OK` y `MAKE_ORIGINAL_OK`. Borrar el `.bat` al terminar.

- [ ] **Step 5: Commit**

```bash
cd /c/pikocore-main
git add src/main.cpp
git commit -m "feat: pasar a ingles el placeholder de sample y el mensaje de error de SD"
```

---

### Task 3: Verificación en hardware (requiere al usuario con la placa)

No delegar a un subagente -- requiere el dispositivo físico. Pasos a pedirle al
usuario:

1. Flashear `build-gamepi/pikocore.uf2` en el GamePi13.
2. Entrar al modo 8 (Browse SD) **sin tarjeta**: confirmar que dice **"No card or
   files"** (antes "Sin tarjeta o sin archivos").
3. Con tarjeta: al entrar debe verse **"Reading card..."**, y al navegar la lista, el
   renglón inferior debe decir **"Hold R: load"** (o **"Loaded (active bank)"** en verde
   si es el banco cargado). Mantener R para cargar → **"Loading..."** y luego **"Done"**
   (o "Error" / "Load failed").
4. Con un banco vacío / sin samples, el nombre en el dashboard debe decir **"(no
   samples)"**.
5. Regresión: el resto del dashboard sin cambios (las etiquetas de modo siguen siendo
   los bitmaps de siempre — los fallbacks de texto traducidos son inalcanzables, así que
   no se ven, es esperado).

Si algo se ve mal, diagnosticar leyendo el código (no adivinar) y corregir.

---

### Task 4: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: Actualizar las menciones de los textos de Browse SD a inglés**

Buscar:
```markdown
- El archivo resaltado que coincide con el banco actualmente cargado se muestra en
  **verde** con el texto "Cargado (banco activo)"; el nombre del banco cargado también
```

Reemplazar:
```markdown
- El archivo resaltado que coincide con el banco actualmente cargado se muestra en
  **verde** con el texto "Loaded (active bank)"; el nombre del banco cargado también
```

- [ ] **Step 2: Commit**

```bash
git add GAMEPI13-INTERFACE.md
git commit -m "docs: reflejar el texto de Browse SD en ingles"
```
