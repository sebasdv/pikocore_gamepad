# Rediseño de la pantalla Browse SD (modo 8) — Diseño

**Fecha:** 2026-07-19
**Estado:** aprobado por el usuario
**Prerequisito:** Sub-proyectos 1-5 del backlog de feedback completos y verificados en
hardware. Rama `port/rp2350-gamepi13`.
**Riesgo:** medio — toca la geometría compartida de las 6 pantallas del modo 8
(`kOverlay`), no solo la pantalla "browse".

## Objetivo

Sub-proyecto 6 (el último del backlog aprobado): rediseñar la pantalla de navegación
de archivos SD (`gamepi_ui_sd_browse()`) usando el mockup de Lopaka
`src/gamepi13/MODE_SD_OVERLAY.txt`, y adoptar su marco (`OVERLAY_FRAME`) como el nuevo
panel compartido de las 6 pantallas del modo 8 (hoy: `gamepi_ui_sd_listing`,
`gamepi_ui_sd_browse`, `gamepi_ui_sd_confirm_progress`, `gamepi_ui_sd_loading`,
`gamepi_ui_sd_result`, `gamepi_ui_sd_error`), reemplazando el panel genérico actual
(relleno oscuro + borde rosa programático).

## No-objetivos

- Las otras 5 pantallas del modo 8 no cambian su **contenido** — solo se corren junto
  con el marco nuevo (mismos textos, mismos colores, misma barra de progreso), ya que
  todas posicionan su contenido en offsets relativos a `kOverlay.x`/`kOverlay.y`.
- No se rediseña la lógica de navegación/carga (`main.cpp`, `GamepiSdState`) — es
  puramente un cambio de renderizado.
- `BANK_NAME_FRAME` no se dibuja — es una guía de layout de Lopaka (mismo patrón que
  los frames de la Fase 5), no un asset pensado para dibujarse. El nombre real del
  archivo se muestra sin marco.
- Los 4 placeholders `DIGIT_BANK_1` del mockup no se importan como bitmap — son el
  mismo dígito repetido 4 veces (un mock de Lopaka, no 10 dígitos reales). El
  índice/cantidad reutiliza el sistema de dígitos ya vendorizado
  (`kBankDigits`/`kBankSlash`).
- El texto "Hold R: load Bank" del mockup es un placeholder en inglés (convención de
  Lopaka) — se reemplaza por el texto real ya existente en español
  ("Mantener R: cargar" / "Cargado (banco activo)"), no se copia literal.

## Hallazgos de la investigación (verificados en código, no re-descubrir)

- `MODE_SD_OVERLAY.txt` define 5 elementos vía `drawMODE_SD_OVERLAY()`:
  - `OVERLAY_FRAME`: bitmap 205×138 en `(18, 50)` — el marco principal, **se importa**.
  - `BANK_NAME_FRAME`: bitmap 180×25 en `(30, 107)` — referencial, **no se importa**.
  - `DIGIT_BANK_1` (reusado 4 veces) + `DIGIT_SLASH_BANK`: 10×15 en
    `(89,72)/(102,72)/(128,72)/(141,72)` + slash 10×20 en `(115,70)` — placeholder de
    un solo dígito repetido, **no se importa**; se reemplaza por
    `kBankDigits`/`kBankSlash`.
  - `L_CYCLE`: bitmap 141×15 en `(52, 138)` — ícono real, **se importa**.
  - Texto real (GFXfont) "Hold R: load Bank" en `(29, 152)` — placeholder de texto,
    **se reemplaza** por el texto en español ya existente.
- El panel compartido actual (`overlay_show_panel()`, `src/gamepi13/ui.cpp`) rellena
  `kOverlay` con `COL_DARK` y dibuja un borde rosa programático
  (`Paint_DrawRectangle(..., COL_PINK, DOT_PIXEL_2X2, DRAW_FILL_EMPTY)`). `kOverlay`
  hoy es `{20, 64, 200, 112}` — distinto tamaño/posición que `OVERLAY_FRAME`.
- Las 6 pantallas del modo 8 ya posicionan todo su contenido en offsets relativos a
  `kOverlay.x`/`kOverlay.y` (`sd_panel_title()` a `kOverlay.y+12`, `draw_truncated()` a
  `kOverlay.y+50/72/88`, la barra de progreso centrada con `kOverlay.w`) — correr
  `kOverlay` a la posición/tamaño de `OVERLAY_FRAME` reposiciona todo automáticamente,
  sin tocar las 5 pantallas que no cambian de contenido.
- `kBankDigits`/`kBankSlash` (`src/gamepi13/ui_bitmaps.h`, ya vendorizados desde
  `Digits for bank files.txt`) y `draw_digit_string()` (`src/gamepi13/ui_bitmaps.h`) ya
  implementan exactamente lo que necesita el índice/cantidad de esta pantalla — mismo
  patrón usado por el BPM y el sample idx/count del dashboard
  (`draw_digit_string(238, 32, idx, kBankDigits, kBankSlash, 7, 15, true)` en
  `draw_name()`).

## Mecanismo

### 1. Marco nuevo, geometría compartida

- `kOverlay` (`src/gamepi13/ui.cpp`) cambia de `{20, 64, 200, 112}` a
  `{18, 50, 205, 138}`.
- Se agrega `kSdOverlayFrame` (205×138) a `src/gamepi13/ui_bitmaps.h`, extraído
  mecánicamente (`sed`) de `image_OVERLAY_FRAME_pixels` en `MODE_SD_OVERLAY.txt`.
- `overlay_show_panel()` deja de dibujar `Paint_DrawRectangle(..., COL_PINK, ...)` y en
  su lugar hace `Paint_DrawImage((const unsigned char *)kSdOverlayFrame, kOverlay.x,
  kOverlay.y, kOverlay.w, kOverlay.h)` (el `Paint_ClearWindows(..., COL_DARK)` previo
  se reemplaza por limpiar a `COL_BG` ya que el propio bitmap trae su relleno/borde).
- Las 5 pantallas sin rediseño (`gamepi_ui_sd_listing`, `_confirm_progress`,
  `_loading`, `_result`, `_error`) no se tocan — sus llamadas a `sd_panel_title()`/
  `draw_truncated()` siguen usando los mismos offsets relativos, que ahora caen dentro
  del marco nuevo automáticamente.

### 2. Pantalla "browse" rediseñada

`gamepi_ui_sd_browse(filename, index, count, is_active)`:
- Se agrega `kSdLCycle` (141×15) a `ui_bitmaps.h`, extraído de `image_L_CYCLE_pixels`.
- Deja de llamar a `sd_panel_title(pos, COL_GRAY)` (título de texto plano "3/12").
- Dibuja el índice/cantidad con dígitos reales:
  ```cpp
  char idx[8];
  snprintf(idx, sizeof(idx), "%02u/%02u", (unsigned)(index + 1), (unsigned)count);
  draw_digit_string(89, 72, idx, kBankDigits, kBankSlash, 7, 15, false);
  ```
- El nombre de archivo (`draw_truncated`) se centra dentro del ancho de
  `BANK_NAME_FRAME` (x=30..210, sin marco), en `COL_GREEN` si `is_active` o
  `COL_PINK` si no — mismo criterio de color que hoy, nueva posición vertical
  (`kOverlay.y + 57`, dentro de la franja donde estaba `BANK_NAME_FRAME`).
- Reemplaza el renglón de texto "L: ciclar lista" por
  `Paint_DrawImage((const unsigned char *)kSdLCycle, 52, 138, 141, 15)`.
- El renglón inferior sigue siendo texto real, mismo condicional que hoy: "Cargado
  (banco activo)" en `COL_GREEN` si `is_active`, o "Mantener R: cargar" en `COL_WHITE`
  si no, en `(29, 152)`.

## Arquitectura

Sin cambios de arquitectura — dos assets nuevos en `ui_bitmaps.h`, un resize de
`kOverlay`, y un cambio de contenido acotado a `overlay_show_panel()` +
`gamepi_ui_sd_browse()`. El resto del mecanismo de overlay persistente (`sd_panel_title()`,
`gamepi_ui_sd_close()`, `overlay_deadline_us`) no cambia.

## Manejo de errores

No aplica — no hay entradas externas ni estados inválidos nuevos. `filename` sigue
truncándose con la misma lógica defensiva de `draw_truncated()` ya existente.

## Pruebas

1. Build `build-gamepi`: sin errores.
2. Hardware:
   - Entrar al modo 8 (Browse SD): confirmar que las 6 pantallas (leyendo tarjeta,
     navegación, progreso, cargando, resultado, error) muestran el marco nuevo en la
     posición correcta, sin recortar contenido.
   - Pantalla de navegación: confirmar que el índice/cantidad se ve como dígitos
     gráficos (no texto), que el nombre de archivo se ve sin marco alrededor con el
     color correcto (verde si es el banco activo, rosa si no), que el ícono
     "L: ciclar" reemplaza el texto, y que el renglón inferior sigue mostrando
     "Mantener R: cargar" / "Cargado (banco activo)" correctamente.
   - Confirmar que el resto del dashboard (fuera del modo 8) no se ve afectado.

## Riesgos conocidos

- **Franja de nombre de archivo demasiado angosta para nombres largos** — mitigado
  por la misma truncación defensiva que `draw_truncated()` ya aplica (~26 caracteres a
  Font12); sin cambios de comportamiento respecto a hoy.
- **Verificación en hardware real de la posición del marco** — las coordenadas vienen
  directamente del mockup de Lopaka, mismo patrón ya usado con éxito para el dashboard
  de modo 0; si algo se ve desalineado, es un ajuste de constantes, no de diseño.
