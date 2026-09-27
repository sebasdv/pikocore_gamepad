# Reintento de dibujo de las pantallas de Browse SD — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir que las pantallas del modo 8 (Browse SD) puedan no dibujarse nunca
si su única oportunidad de dibujo cae en un tick donde `flush_allowed()` deniega —
agregando un mecanismo de reintento por tick en `main.cpp`.

**Architecture:** 5 de las 6 funciones de dibujo de `src/gamepi13/ui.cpp` pasan de
`void` a `bool` (indicando si realmente dibujaron). `main.cpp` deja de llamarlas
directamente en cada punto de transición de estado y en su lugar marca una bandera
("qué pantalla hace falta mostrar"), que un bloque nuevo — junto a la llamada ya
existente a `gamepi_ui_tick()` — reintenta en cada tick hasta que la llamada
correspondiente devuelva `true`.

**Tech Stack:** C/C++17, sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-19-sd-screen-redraw-retry-design.md`
(aprobado). Rama: `port/rp2350-gamepi13`.

---

## Contexto para quien ejecuta

### Entorno de build (Windows)

Este plan toca `src/main.cpp`, compartido entre el hardware original y GamePi13 —
**hay que compilar los dos targets**, no solo `build-gamepi`.

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

Expected: `MAKE_GAMEPI_OK` y `MAKE_ORIGINAL_OK`. Si `build/` no existe como carpeta de
build del hardware original, usar solo `build-gamepi` y anotarlo — no es bloqueante
para este plan (el cambio de `main.cpp` queda detrás de `#if PIKO_GAMEPI13` salvo el
cambio de firma `void`→`bool`, que es válido en C++ para el hardware original también
aunque no use el valor de retorno).

### Hallazgos que hay que respetar

- `gamepi_ui_sd_loading()` (`src/gamepi13/ui.cpp:635-643`) **no tiene** el guard
  `if (!flush_allowed()) return;` — a propósito (comentario: es la última escritura
  antes de que el core0 deje de tocar spi1 durante la carga real, y necesita la
  garantía de estar en pantalla antes de esa ventana). Al pasarla a `bool`, simplemente
  siempre devuelve `true` al final — no se le agrega ningún guard nuevo.
- Las otras 4 (`gamepi_ui_sd_listing`, `gamepi_ui_sd_browse`, `gamepi_ui_sd_result`,
  `gamepi_ui_sd_error`) sí tienen `if (!flush_allowed()) return;` — ese `return` pasa a
  `return false;`.
- `gamepi_ui_sd_confirm_progress()` **no cambia** — ya se llama en cada tick mientras
  se mantiene R, fuera de alcance de este plan.
- Solo hay **un** punto de entrada a modo 8 (ciclando con Select, `main.cpp:1880-1892`)
  — el salto directo Select+botón musical no puede aterrizar en modo 8 (no tiene botón
  musical propio), confirmado leyendo el código.

### Reglas de la fase

- Cada task termina con `build-gamepi` (y `build` si existe) compilando y un commit.

---

### Task 1: Cambiar las firmas de 5 funciones a `bool`

**Files:**
- Modify: `src/gamepi13/ui.h`
- Modify: `src/gamepi13/ui.cpp`

- [ ] **Step 1: Declaraciones en `ui.h`**

Buscar:
```cpp
// Browse-SD mode (modo 8 del selector). Todas reusan el panel del overlay;
// llamarlas SOLO desde el lazo de botones de main.cpp, nunca desde
// gamepi_ui_tick() -- evitan competir con el dashboard normal por pantalla.
void gamepi_ui_sd_listing();
void gamepi_ui_sd_browse(const char *filename, uint32_t index, uint32_t count, bool is_active);
void gamepi_ui_sd_confirm_progress(const char *filename, uint8_t percent);
void gamepi_ui_sd_loading(const char *filename);
void gamepi_ui_sd_result(bool ok, const char *filename);
void gamepi_ui_sd_error(const char *message);
void gamepi_ui_sd_close();  // call when leaving mode 8; closes any open SD screen immediately
```

Reemplazar:
```cpp
// Browse-SD mode (modo 8 del selector). Todas reusan el panel del overlay;
// llamarlas SOLO desde el lazo de botones de main.cpp, nunca desde
// gamepi_ui_tick() -- evitan competir con el dashboard normal por pantalla.
// Las que devuelven bool: false si flush_allowed() denegó esta vez (el
// llamador debe reintentar en un tick posterior, no asumir que ya se dibujó).
bool gamepi_ui_sd_listing();
bool gamepi_ui_sd_browse(const char *filename, uint32_t index, uint32_t count, bool is_active);
void gamepi_ui_sd_confirm_progress(const char *filename, uint8_t percent);
bool gamepi_ui_sd_loading(const char *filename);
bool gamepi_ui_sd_result(bool ok, const char *filename);
bool gamepi_ui_sd_error(const char *message);
void gamepi_ui_sd_close();  // call when leaving mode 8; closes any open SD screen immediately
```

- [ ] **Step 2: `gamepi_ui_sd_listing()` en `ui.cpp`**

Buscar:
```cpp
void gamepi_ui_sd_listing() {
  if (!flush_allowed()) return;
  sd_panel_title("SD", COL_GRAY);
  draw_truncated("Leyendo tarjeta...", (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
}
```

Reemplazar:
```cpp
bool gamepi_ui_sd_listing() {
  if (!flush_allowed()) return false;
  sd_panel_title("SD", COL_GRAY);
  draw_truncated("Leyendo tarjeta...", (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
  return true;
}
```

- [ ] **Step 3: `gamepi_ui_sd_browse()` en `ui.cpp`**

Buscar:
```cpp
void gamepi_ui_sd_browse(const char *filename, uint32_t index, uint32_t count,
                         bool is_active) {
  if (!flush_allowed()) return;
  overlay_show_panel(true);  // persistent, mismo criterio que sd_panel_title()
  char idx[8];
  snprintf(idx, sizeof(idx), "%02lu/%02lu", (unsigned long)(index + 1),
           (unsigned long)count);
  // Posición y tamaño de esta franja y las 3 de abajo: coordenadas absolutas
  // de MODE_SD_OVERLAY.txt (mismo criterio que kOverlay/kSdOverlayFrame).
  draw_digit_string(89, 72, idx, kBankDigits, kBankSlash, 7, 15, false);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 57),
                is_active ? COL_GREEN : COL_PINK);
  // Ícono en vez de texto para "L: ciclar" -- el rol de L quedaba poco claro
  // mostrando solo el hint de R durante pruebas de hardware (ver historial).
  Paint_DrawImage((const unsigned char *)kSdLCycle, 52, 138, 141, 15);
  draw_truncated(is_active ? "Cargado (banco activo)" : "Mantener R: cargar",
                (uint16_t)(kOverlay.y + 102), COL_GRAY);
  flush(kOverlay);
}
```

Reemplazar:
```cpp
bool gamepi_ui_sd_browse(const char *filename, uint32_t index, uint32_t count,
                         bool is_active) {
  if (!flush_allowed()) return false;
  overlay_show_panel(true);  // persistent, mismo criterio que sd_panel_title()
  char idx[8];
  snprintf(idx, sizeof(idx), "%02lu/%02lu", (unsigned long)(index + 1),
           (unsigned long)count);
  // Posición y tamaño de esta franja y las 3 de abajo: coordenadas absolutas
  // de MODE_SD_OVERLAY.txt (mismo criterio que kOverlay/kSdOverlayFrame).
  draw_digit_string(89, 72, idx, kBankDigits, kBankSlash, 7, 15, false);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 57),
                is_active ? COL_GREEN : COL_PINK);
  // Ícono en vez de texto para "L: ciclar" -- el rol de L quedaba poco claro
  // mostrando solo el hint de R durante pruebas de hardware (ver historial).
  Paint_DrawImage((const unsigned char *)kSdLCycle, 52, 138, 141, 15);
  draw_truncated(is_active ? "Cargado (banco activo)" : "Mantener R: cargar",
                (uint16_t)(kOverlay.y + 102), COL_GRAY);
  flush(kOverlay);
  return true;
}
```

- [ ] **Step 4: `gamepi_ui_sd_loading()` en `ui.cpp`**

Buscar:
```cpp
void gamepi_ui_sd_loading(const char *filename) {
  // Flushed once, unthrottled: this is the LAST LCD write before core0 stops
  // touching spi1 for the duration of the actual SD-read+flash-write (see
  // main.cpp's mode-8 handler) -- deliberately bypasses flush_allowed() so
  // the message is guaranteed on screen before that quiet window starts.
  sd_panel_title("Cargando...", COL_CYAN);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
}
```

Reemplazar:
```cpp
bool gamepi_ui_sd_loading(const char *filename) {
  // Flushed once, unthrottled: this is the LAST LCD write before core0 stops
  // touching spi1 for the duration of the actual SD-read+flash-write (see
  // main.cpp's mode-8 handler) -- deliberately bypasses flush_allowed() so
  // the message is guaranteed on screen before that quiet window starts.
  // Nunca deniega -- siempre devuelve true (no participa del reintento salvo
  // por uniformidad de firma con las demás).
  sd_panel_title("Cargando...", COL_CYAN);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
  return true;
}
```

- [ ] **Step 5: `gamepi_ui_sd_result()` en `ui.cpp`**

Buscar:
```cpp
void gamepi_ui_sd_result(bool ok, const char *filename) {
  if (!flush_allowed()) return;
  sd_panel_title(ok ? "Listo" : "Error", ok ? COL_GREEN : COL_PINK);
  draw_truncated(ok ? filename : "No se pudo cargar",
                 (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
}
```

Reemplazar:
```cpp
bool gamepi_ui_sd_result(bool ok, const char *filename) {
  if (!flush_allowed()) return false;
  sd_panel_title(ok ? "Listo" : "Error", ok ? COL_GREEN : COL_PINK);
  draw_truncated(ok ? filename : "No se pudo cargar",
                 (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
  return true;
}
```

- [ ] **Step 6: `gamepi_ui_sd_error()` en `ui.cpp`**

Buscar:
```cpp
void gamepi_ui_sd_error(const char *message) {
  if (!flush_allowed()) return;
  sd_panel_title("SD", COL_GRAY);
  draw_truncated(message, (uint16_t)(kOverlay.y + 50), COL_PINK);
  flush(kOverlay);
```

Reemplazar:
```cpp
bool gamepi_ui_sd_error(const char *message) {
  if (!flush_allowed()) return false;
  sd_panel_title("SD", COL_GRAY);
  draw_truncated(message, (uint16_t)(kOverlay.y + 50), COL_PINK);
  flush(kOverlay);
  return true;
```

(Nota: el `Buscar` de este último paso incluye la línea de apertura de la función y
las 4 líneas del cuerpo, pero NO la llave de cierre `}` — para no confundirla con
otras llaves de cierre en el archivo. Verificar después de reemplazar que la llave
de cierre original sigue inmediatamente después, intacta.)

- [ ] **Step 7: Build**

```bash
cat > /c/pikocore-main/rebuild_sdr1.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_sdr1.bat"
```

Expected: `MAKE_OK` (esperable: las llamadas en `main.cpp` siguen siendo válidas
ignorando el valor de retorno -- no debería haber ningún error de compilación en este
punto, todavía no se usa el `bool` para nada). Borrar el `.bat` al terminar.

- [ ] **Step 8: Commit**

```bash
cd /c/pikocore-main
git add src/gamepi13/ui.h src/gamepi13/ui.cpp
git commit -m "feat: las funciones de dibujo del modo 8 devuelven bool (exito o no)"
```

---

### Task 2: Mecanismo de reintento en `main.cpp`

**Files:**
- Modify: `src/main.cpp`

- [ ] **Step 1: Agregar el enum y las variables globales, justo antes del `#else`
      que cierra el bloque de estado de modo 8**

Buscar:
```cpp
#define GAMEPI_SD_RESULT_US 1500000  // ~1.5 s
char gamepi_active_bank_name[24] = "";  // "" until a bank is loaded from SD this session
#else
```

Reemplazar:
```cpp
#define GAMEPI_SD_RESULT_US 1500000  // ~1.5 s
char gamepi_active_bank_name[24] = "";  // "" until a bank is loaded from SD this session
// Qué pantalla del modo 8 falta (re)dibujar -- ver el bloque junto a
// gamepi_ui_tick() más abajo, que reintenta cada tick hasta que la llamada
// correspondiente devuelva true (flush_allowed() puede denegar la primera
// vez sin que eso signifique que la pantalla nunca deba mostrarse).
enum GamepiSdRedrawKind {
  GAMEPI_SD_REDRAW_NONE,
  GAMEPI_SD_REDRAW_LISTING,
  GAMEPI_SD_REDRAW_BROWSE,
  GAMEPI_SD_REDRAW_LOADING,
  GAMEPI_SD_REDRAW_RESULT,
  GAMEPI_SD_REDRAW_ERROR,
};
GamepiSdRedrawKind gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_NONE;
char gamepi_sd_redraw_error_msg[32] = "";
#else
```

- [ ] **Step 2: Reemplazar la llamada de "entrar a modo 8"**

Buscar:
```cpp
            // gamepi_selector == 8: entering Browse SD, kick off the async
            // directory listing.
            gamepi_sd_state = GAMEPI_SD_LISTING;
            gamepi_sd_index = 0;
            gamepi_sd_hold_start_us = 0;
            gamepi_sd_list_done = false;
            __asm volatile("dmb" ::: "memory");
            gamepi_sd_list_requested = true;
            gamepi_ui_sd_listing();
```

Reemplazar:
```cpp
            // gamepi_selector == 8: entering Browse SD, kick off the async
            // directory listing.
            gamepi_sd_state = GAMEPI_SD_LISTING;
            gamepi_sd_index = 0;
            gamepi_sd_hold_start_us = 0;
            gamepi_sd_list_done = false;
            __asm volatile("dmb" ::: "memory");
            gamepi_sd_list_requested = true;
            gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_LISTING;
```

- [ ] **Step 3: Reemplazar las 2 llamadas del `case GAMEPI_SD_LISTING`**

Buscar:
```cpp
          case GAMEPI_SD_LISTING:
            if (gamepi_sd_list_done) {
              if (gamepi_sd_file_count() == 0) {
                gamepi_ui_sd_error("Sin tarjeta o sin archivos");
                gamepi_sd_state = GAMEPI_SD_IDLE;
              } else {
                gamepi_sd_index = 0;
                gamepi_sd_state = GAMEPI_SD_BROWSE;
                const bool is_active = gamepi_active_bank_name[0] != '\0' &&
                    strcmp(gamepi_sd_file_name(0), gamepi_active_bank_name) == 0;
                gamepi_ui_sd_browse(gamepi_sd_file_name(0), 0,
                                    gamepi_sd_file_count(), is_active);
              }
            }
            break;
```

Reemplazar:
```cpp
          case GAMEPI_SD_LISTING:
            if (gamepi_sd_list_done) {
              if (gamepi_sd_file_count() == 0) {
                strncpy(gamepi_sd_redraw_error_msg, "Sin tarjeta o sin archivos",
                       sizeof(gamepi_sd_redraw_error_msg) - 1);
                gamepi_sd_redraw_error_msg[sizeof(gamepi_sd_redraw_error_msg) - 1] = '\0';
                gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_ERROR;
                gamepi_sd_state = GAMEPI_SD_IDLE;
              } else {
                gamepi_sd_index = 0;
                gamepi_sd_state = GAMEPI_SD_BROWSE;
                gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_BROWSE;
              }
            }
            break;
```

- [ ] **Step 4: Reemplazar la llamada de "navegar con L" en `case GAMEPI_SD_BROWSE`**

Buscar:
```cpp
            if (moved) {
              gamepi_sd_hold_start_us = 0;
              const bool is_active = gamepi_active_bank_name[0] != '\0' &&
                  strcmp(gamepi_sd_file_name(gamepi_sd_index), gamepi_active_bank_name) == 0;
              gamepi_ui_sd_browse(gamepi_sd_file_name(gamepi_sd_index),
                                  gamepi_sd_index, count, is_active);
            }
```

Reemplazar:
```cpp
            if (moved) {
              gamepi_sd_hold_start_us = 0;
              gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_BROWSE;
            }
```

- [ ] **Step 5: Reemplazar la llamada de "cruzar el umbral de hold con R" en
      `case GAMEPI_SD_BROWSE`**

Buscar:
```cpp
                } else {
                  gamepi_ui_sd_loading(gamepi_sd_file_name(gamepi_sd_index));
                  gamepi_sd_load_index = gamepi_sd_index;
                  gamepi_sd_load_done = false;
                  __asm volatile("dmb" ::: "memory");
                  gamepi_sd_load_requested = true;
                  gamepi_sd_state = GAMEPI_SD_LOADING;
                }
```

Reemplazar:
```cpp
                } else {
                  gamepi_sd_load_index = gamepi_sd_index;
                  gamepi_sd_load_done = false;
                  __asm volatile("dmb" ::: "memory");
                  gamepi_sd_load_requested = true;
                  gamepi_sd_state = GAMEPI_SD_LOADING;
                  gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_LOADING;
                }
```

- [ ] **Step 6: Reemplazar la llamada de "soltar R a mitad de hold" en
      `case GAMEPI_SD_BROWSE`**

Buscar:
```cpp
              if (gamepi_sd_hold_start_us != 0) {
                // Was mid-hold (showing the confirm-progress overlay) and
                // got released before reaching the threshold -- restore the
                // browse screen. SD overlays are persistent now (no
                // auto-expiry), so without this the "Cargando... XX%"
                // screen would stay frozen on-screen indefinitely.
                const bool is_active = gamepi_active_bank_name[0] != '\0' &&
                    strcmp(gamepi_sd_file_name(gamepi_sd_index), gamepi_active_bank_name) == 0;
                gamepi_ui_sd_browse(gamepi_sd_file_name(gamepi_sd_index),
                                    gamepi_sd_index, count, is_active);
              }
```

Reemplazar:
```cpp
              if (gamepi_sd_hold_start_us != 0) {
                // Was mid-hold (showing the confirm-progress overlay) and
                // got released before reaching the threshold -- restore the
                // browse screen. SD overlays are persistent now (no
                // auto-expiry), so without this the "Cargando... XX%"
                // screen would stay frozen on-screen indefinitely.
                gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_BROWSE;
              }
```

- [ ] **Step 7: Reemplazar la llamada de "fin de carga" en `case GAMEPI_SD_LOADING`**

Buscar:
```cpp
              gamepi_ui_sd_result(gamepi_sd_load_ok,
                                  gamepi_sd_file_name(gamepi_sd_load_index));
              gamepi_sd_result_deadline_us = time_us_64() + GAMEPI_SD_RESULT_US;
              gamepi_sd_state = GAMEPI_SD_RESULT;
```

Reemplazar:
```cpp
              gamepi_sd_result_deadline_us = time_us_64() + GAMEPI_SD_RESULT_US;
              gamepi_sd_state = GAMEPI_SD_RESULT;
              gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_RESULT;
```

- [ ] **Step 8: Reemplazar la llamada de "fin del timeout de resultado" en
      `case GAMEPI_SD_RESULT`**

Buscar:
```cpp
            } else {
              gamepi_sd_state = GAMEPI_SD_BROWSE;
              const bool is_active = gamepi_active_bank_name[0] != '\0' &&
                  strcmp(gamepi_sd_file_name(gamepi_sd_index), gamepi_active_bank_name) == 0;
              gamepi_ui_sd_browse(gamepi_sd_file_name(gamepi_sd_index),
                                  gamepi_sd_index, gamepi_sd_file_count(), is_active);
            }
```

Reemplazar:
```cpp
            } else {
              gamepi_sd_state = GAMEPI_SD_BROWSE;
              gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_BROWSE;
            }
```

- [ ] **Step 9: Agregar el bloque de reintento, justo después de `gamepi_ui_tick(uis);`**

Buscar:
```cpp
        uis.knob_a = input_knob[1].Value();
        uis.knob_b = input_knob[2].Value();
        uis.playing = !do_mute;
        gamepi_ui_tick(uis);
      }
#endif
```

Reemplazar:
```cpp
        uis.knob_a = input_knob[1].Value();
        uis.knob_b = input_knob[2].Value();
        uis.playing = !do_mute;
        gamepi_ui_tick(uis);
      }
      if (gamepi_sd_redraw_kind != GAMEPI_SD_REDRAW_NONE) {
        bool ok = false;
        switch (gamepi_sd_redraw_kind) {
          case GAMEPI_SD_REDRAW_LISTING:
            ok = gamepi_ui_sd_listing();
            break;
          case GAMEPI_SD_REDRAW_BROWSE: {
            const uint32_t count = gamepi_sd_file_count();
            const bool is_active = count > 0 && gamepi_active_bank_name[0] != '\0' &&
                strcmp(gamepi_sd_file_name(gamepi_sd_index), gamepi_active_bank_name) == 0;
            ok = count > 0 && gamepi_ui_sd_browse(gamepi_sd_file_name(gamepi_sd_index),
                                                  gamepi_sd_index, count, is_active);
            break;
          }
          case GAMEPI_SD_REDRAW_LOADING:
            ok = gamepi_ui_sd_loading(gamepi_sd_file_name(gamepi_sd_load_index));
            break;
          case GAMEPI_SD_REDRAW_RESULT:
            ok = gamepi_ui_sd_result(gamepi_sd_load_ok,
                                     gamepi_sd_file_name(gamepi_sd_load_index));
            break;
          case GAMEPI_SD_REDRAW_ERROR:
            ok = gamepi_ui_sd_error(gamepi_sd_redraw_error_msg);
            break;
          default:
            break;
        }
        if (ok) gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_NONE;
      }
#endif
```

- [ ] **Step 10: Limpiar la bandera pendiente al salir del modo 8**

Buscar (en `src/gamepi13/ui.cpp`, no en `main.cpp` -- `gamepi_ui_sd_close()` vive ahí):
```cpp
void gamepi_ui_sd_close() {
  // Called when leaving mode 8: expire the persistent SD overlay immediately
  // so gamepi_ui_tick()'s normal (non-persistent) path reverts to the
  // regular dashboard on its next call, reusing that existing revert logic
  // instead of duplicating it here.
  overlay_persistent = false;
  overlay_deadline_us = time_us_64();
}
```

Este archivo no tiene acceso a `gamepi_sd_redraw_kind` (es una variable de
`main.cpp`) — en su lugar, limpiar la bandera directamente en `main.cpp`, en los 2
lugares que llaman a `gamepi_ui_sd_close()` (indentación distinta en cada uno, dos
ediciones separadas):

Buscar (primer sitio, ciclando con Select, indentación de 12 espacios):
```cpp
          if (was == 8) {
            // Leaving Browse SD: unmount, don't leave the card open, and close
            // whatever SD screen was on-screen -- it's a persistent overlay
            // (see gamepi_ui_sd_close()'s comment), so it won't time out on
            // its own.
            gamepi_sd_unmount_requested = true;
            gamepi_sd_state = GAMEPI_SD_IDLE;
            gamepi_ui_sd_close();
          }
```

Reemplazar:
```cpp
          if (was == 8) {
            // Leaving Browse SD: unmount, don't leave the card open, and close
            // whatever SD screen was on-screen -- it's a persistent overlay
            // (see gamepi_ui_sd_close()'s comment), so it won't time out on
            // its own.
            gamepi_sd_unmount_requested = true;
            gamepi_sd_state = GAMEPI_SD_IDLE;
            gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_NONE;
            gamepi_ui_sd_close();
          }
```

Buscar (segundo sitio, salto directo Select+botón musical, indentación de 14 espacios):
```cpp
            if (was == 8) {
              // Leaving Browse SD via a direct jump -- same cleanup the
              // Falling()-cycling path above does, so every way out of
              // mode 8 reliably unmounts the card. A direct jump can only
              // ever land on i < 8, so there's no matching "entering
              // Browse SD" branch needed here.
              gamepi_sd_unmount_requested = true;
              gamepi_sd_state = GAMEPI_SD_IDLE;
              gamepi_ui_sd_close();
            }
```

Reemplazar:
```cpp
            if (was == 8) {
              // Leaving Browse SD via a direct jump -- same cleanup the
              // Falling()-cycling path above does, so every way out of
              // mode 8 reliably unmounts the card. A direct jump can only
              // ever land on i < 8, so there's no matching "entering
              // Browse SD" branch needed here.
              gamepi_sd_unmount_requested = true;
              gamepi_sd_state = GAMEPI_SD_IDLE;
              gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_NONE;
              gamepi_ui_sd_close();
            }
```

- [ ] **Step 11: Build**

```bash
cat > /c/pikocore-main/rebuild_sdr2.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 ( echo VCVARSALL_FAILED & exit /b 1 )
cd /d C:\pikocore-main\build-gamepi
C:\dtmake\make.exe -j4
if errorlevel 1 ( echo MAKE_FAILED & exit /b 1 )
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_sdr2.bat"
```

Expected: `MAKE_OK`. Borrar el `.bat` al terminar. Si existe una carpeta `build/`
(hardware original), repetir con `cd /d C:\pikocore-main\build` y confirmar que
también compila (el enum/bloque de reintento están detrás de `#if PIKO_GAMEPI13`, así
que no deberían afectarlo).

- [ ] **Step 12: Commit**

```bash
cd /c/pikocore-main
git add src/main.cpp
git commit -m "fix: reintentar el dibujo de las pantallas del modo 8 hasta que tengan exito"
```

---

### Task 3: Verificación en hardware (requiere al usuario con la placa)

No delegar a un subagente -- requiere el dispositivo físico. Pasos a pedirle al
usuario:

1. Flashear `build-gamepi/pikocore.uf2` en el GamePi13.
2. Entrar y salir del modo 8 (Select) **muchas veces seguidas** (al menos 10-15
   intentos), confirmando que la pantalla de SD (marco + contenido) aparece
   **siempre**, no solo a veces.
3. Repetir con tarjeta puesta y sin tarjeta (para ejercitar `gamepi_ui_sd_error`).
4. Navegar la lista con L, mantener R hasta cargar un banco, soltar R a mitad de
   camino — confirmar que cada pantalla se ve consistentemente en todos los casos,
   no solo la primera vez que se prueba.
5. Regresión: el resto del dashboard (fuera del modo 8) sin cambios.

Si algo falla, diagnosticar leyendo el código (no adivinar) y corregir.

---

### Task 4: Documentación

**Files:**
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: Agregar un hallazgo a la sección 5**

Buscar:
```markdown
- **RESUELTO — lecturas XIP fantasma en el arranque.** En esta placa, las lecturas de
```

Reemplazar:
```markdown
- **RESUELTO — las pantallas del modo 8 (Browse SD) podían no aparecer nunca.** Cada
  pantalla de Browse SD se dibujaba una sola vez por transición de estado, gateada por
  `flush_allowed()` (límite global de 25Hz que `gamepi_ui_tick()` también consume sin
  condición en cada tick). Si esa única oportunidad caía en un tick "recién usado", la
  pantalla no se dibujaba nunca, y como el overlay nunca se activaba, el dashboard
  normal seguía mostrando su fallback de modo 0 indefinidamente (con el ícono de modo
  correctamente en SD, ya que ese sí se dibuja por el camino normal) — confirmado en
  hardware. Fix: las 5 funciones de dibujo relevantes devuelven `bool` (si dibujaron o
  no), y un mecanismo de reintento en `main.cpp` (bandera `gamepi_sd_redraw_kind`,
  revisada junto a `gamepi_ui_tick()` en cada tick) reintenta hasta que la llamada
  correspondiente tenga éxito, en vez de una sola oportunidad.
- **RESUELTO — lecturas XIP fantasma en el arranque.** En esta placa, las lecturas de
```

- [ ] **Step 2: Commit**

```bash
git add GAMEPI13-INTERFACE.md
git commit -m "docs: documentar el reintento de dibujo de las pantallas del modo 8"
```
