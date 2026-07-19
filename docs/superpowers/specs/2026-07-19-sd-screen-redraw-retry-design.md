# Reintento de dibujo de las pantallas de Browse SD — Diseño

**Fecha:** 2026-07-19
**Estado:** aprobado por el usuario
**Prerequisito:** Rediseño de la pantalla Browse SD (sub-proyecto 6) completo. Rama
`port/rp2350-gamepi13`.
**Riesgo:** medio-alto — toca `src/main.cpp` (compartido con el hardware original,
aunque el cambio queda dentro de bloques `#if PIKO_GAMEPI13`) y cambia la firma de 6
funciones públicas de `src/gamepi13/ui.h`/`ui.cpp`.

## Objetivo

Corregir un bug real reportado en hardware: al entrar al modo 8 (Browse SD), el
dashboard normal (con el ícono de modo 8 correctamente encendido) sigue mostrándose en
vez de la pantalla de SD — el overlay nunca llega a activarse. Investigación (lectura
de código, no reproducido con instrumentación de hardware) encontró la causa raíz:
las 6 funciones que dibujan las pantallas del modo 8
(`gamepi_ui_sd_listing/browse/confirm_progress/loading/result/error`, todas en
`src/gamepi13/ui.cpp`) se llaman **una sola vez** por transición de estado desde
`src/main.cpp`, y cada una empieza con `if (!flush_allowed()) return;` — un límite de
velocidad global (25 Hz) compartido con todo el resto del dashboard. Si esa única
llamada cae en un tick donde el límite está "recién usado" (algo que
`gamepi_ui_tick()` consume de forma incondicional en cada tick, haya o no algo para
dibujar), la pantalla de SD nunca se dibuja, `overlay_on` nunca se activa, y el
dashboard normal sigue corriendo con su fallback de modo 0 para las barras Function
A/B indefinidamente — coincide exactamente con el síntoma reportado.

## No-objetivos

- No se toca `flush_allowed()`, `gamepi_ui_tick()`, ni el mecanismo de
  dirty-tracking del dashboard normal — la corrección es aditiva (agrega reintento en
  el lado de `main.cpp`), no cambia cómo se reparte el límite de velocidad.
- `gamepi_ui_sd_confirm_progress()` **no participa** de este mecanismo — ya se llama
  en cada tick mientras se mantiene R (mientras dura el hold, ~1s), así que ya tiene
  muchas oportunidades de acertar el límite de velocidad sin necesitar cambios; no es
  el caso que reprodujo el bug.
- No se rediseña la máquina de estados de Browse SD (`GamepiSdState`) ni su lógica de
  navegación/carga — solo se agrega un mecanismo de reintento sobre las llamadas de
  dibujo ya existentes.

## Hallazgos de la investigación (verificados en código, no re-descubrir)

- `flush_allowed()` (`src/gamepi13/ui.cpp:111-116`) actualiza `last_flush_us`
  apenas retorna `true`, sin importar si el llamador efectivamente dibujó algo.
- `gamepi_ui_tick()` llama `flush_allowed()` sin condición en su camino normal (cuando
  `overlay_on` es falso) — línea 538, antes del loop de widgets sucios — así que
  "gana" el límite de velocidad casi apenas se cumplen los 40ms, haya o no algo sucio.
- Los 6 puntos de llamada en `src/main.cpp` a las funciones de dibujo del modo 8 son,
  cada uno, de una sola vez (edge-triggered): entrar a modo 8 (`gamepi_ui_sd_listing()`,
  ~línea 1895), fin de listado (`gamepi_ui_sd_error()`/`gamepi_ui_sd_browse()`,
  ~líneas 2020/2027), navegar con L (~línea 2052), cruzar el umbral de hold con R
  (`gamepi_ui_sd_loading()`, ~línea 2067), soltar R a mitad de hold (~línea 2084),
  fin de carga (`gamepi_ui_sd_result()`, ~línea 2106), fin del timeout de resultado
  (~línea 2119). Ninguno reintenta si `flush_allowed()` deniega esa única vez.
- `gamepi_sd_index`, `gamepi_active_bank_name`, `gamepi_sd_load_index`,
  `gamepi_sd_load_ok` son globales persistentes en `main.cpp` — recalcular los
  argumentos de cada pantalla en un reintento posterior (en vez de "congelarlos") es
  seguro y ya es exactamente lo que hace cada punto de llamada hoy.

## Mecanismo

### 1. Las 6 funciones de dibujo pasan de `void` a `bool`

En `src/gamepi13/ui.h` y `src/gamepi13/ui.cpp`: `gamepi_ui_sd_listing()`,
`gamepi_ui_sd_browse()`, `gamepi_ui_sd_loading()`, `gamepi_ui_sd_result()`,
`gamepi_ui_sd_error()` devuelven `bool` — `false` en su `if (!flush_allowed()) return
false;` inicial (antes `return;`), `true` al final (después de `flush(kOverlay)`,
antes era `return` implícito de una función `void`). `gamepi_ui_sd_confirm_progress()`
no cambia (fuera de alcance, ver No-objetivos).

### 2. Bandera + enum de "pantalla pendiente" en `main.cpp`

```cpp
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
```

Cada uno de los 6 puntos de llamada existentes deja de invocar la función de dibujo
directamente y en su lugar fija `gamepi_sd_redraw_kind` al valor correspondiente
(y, para el caso de error, copia el mensaje a `gamepi_sd_redraw_error_msg`).

### 3. Bloque de reintento, junto a `gamepi_ui_tick(uis)`

Justo después de la llamada existente a `gamepi_ui_tick(uis);` (mismo lugar donde ya
se recalculan `uis.mode`/`uis.knob_a`/etc. cada tick), se agrega:

```cpp
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
```

Este bloque corre en cada tick (igual que `gamepi_ui_tick()`); mientras
`gamepi_sd_redraw_kind` no sea `NONE`, sigue reintentando la pantalla correspondiente
con argumentos recalculados en el momento, hasta que la llamada realmente tenga éxito
(`ok == true`), y recién ahí deja de insistir. No hace falta "congelar" los
argumentos de antemano porque las 4 variables que los alimentan
(`gamepi_sd_index`, `gamepi_active_bank_name`, `gamepi_sd_load_index`,
`gamepi_sd_load_ok`) son globales persistentes que no cambian entre reintentos del
mismo evento.

### 4. Limpieza al salir del modo 8

`gamepi_ui_sd_close()` (llamada al salir del modo 8) también fija
`gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_NONE;`, para que una pantalla pendiente de
una sesión anterior en modo 8 no se cuele en un reingreso posterior.

## Arquitectura

Cambio contenido: 6 firmas de función (`void`→`bool`) en `ui.h`/`ui.cpp`, y en
`main.cpp` un enum + 2 variables globales nuevas + reemplazo de 7 líneas de llamada
directa por asignaciones al enum + un bloque de reintento nuevo (~20 líneas) junto a
`gamepi_ui_tick()`. No se agregan widgets, zonas ni mecanismos de dirty-tracking
nuevos en `ui.cpp`.

## Manejo de errores

- `GAMEPI_SD_REDRAW_BROWSE` con `count == 0` (defensivo, no debería ocurrir en la
  práctica ya que solo se entra a `BROWSE` con `count > 0`, pero el bloque de
  reintento corre independientemente de en qué `case` del `switch` estemos): `ok`
  queda en `false`, se sigue reintentando sin dibujar nada hasta que `count` sea
  válido o el estado cambie (que a su vez fija otro `gamepi_sd_redraw_kind`).
- `gamepi_sd_redraw_error_msg` es un buffer de 32 bytes — el único mensaje de error
  real hoy ("Sin tarjeta o sin archivos") entra con margen; si se agrega un mensaje
  más largo en el futuro, `strncpy` trunca de forma segura (mismo patrón que otros
  buffers de texto en `main.cpp`).

## Pruebas

1. Build `build-gamepi` y `build` (hardware original): sin errores — confirmar que el
   cambio de firma `void`→`bool` no rompe el build del hardware original aunque el
   enum/bloque de reintento esté detrás de `#if PIKO_GAMEPI13`.
2. Hardware: entrar y salir del modo 8 repetidamente (Select), muchas veces seguidas,
   confirmando que la pantalla de SD (marco + contenido) aparece **siempre**, no solo
   a veces. Repetir con tarjeta y sin tarjeta (para ejercitar el camino de error).
   Navegar con L, mantener R para cargar, soltar a mitad de camino — confirmar que
   cada pantalla se ve consistentemente, no solo la primera vez.
3. Confirmar que el resto del dashboard (fuera del modo 8) no cambia de
   comportamiento — el bloque de reintento no debe alterar el redibujado normal.

## Riesgos conocidos

- **Latencia hasta que la pantalla de SD aparece**: con el reintento, en el peor caso
  la pantalla puede tardar un par de ticks del límite de 25Hz (unas pocas decenas de
  ms) en aparecer, en vez de fallar para siempre. Aceptable — es exactamente el
  trade-off buscado (preferir un pequeño retraso a nunca mostrarse).
- **`main.cpp` es compartido con el hardware original** — el cambio de firma
  `void`→`bool` de las 6 funciones y el enum/bloque de reintento quedan dentro de
  `#if PIKO_GAMEPI13`, así que no deberían afectar el build/comportamiento del
  hardware original; se verifica explícitamente en Pruebas.
