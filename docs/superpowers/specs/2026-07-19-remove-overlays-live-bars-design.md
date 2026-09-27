# Quitar overlay + barras en vivo + barra de sample segmentada — Diseño

**Fecha:** 2026-07-19
**Estado:** aprobado por el usuario
**Prerequisito:** Dashboard con bitmaps de Lopaka (modo 0) + etiquetas de Function A/B
para los 8 modos + colores por modo, todos completos y verificados en hardware. Rama
`port/rp2350-gamepi13`.
**Riesgo:** medio — toca `main.cpp` (llamadas a funciones que se eliminan) además de
`ui.cpp`/`ui.h`, y cambia el comportamiento de renderizado de una barra existente.

## Objetivo

Sub-proyecto 5 del backlog aprobado, agrupa 3 puntos relacionados del feedback
original del usuario:

1. Quitar el sistema de overlays temporales de modo/parámetro/tempo — ya no son
   necesarios ahora que existen shortcuts (Select + botón musical para saltar de modo
   directamente, ver `GAMEPI13-INTERFACE.md` sección 3). Queda **solo** el overlay
   persistente de Browse SD (modo 8, a rediseñar aparte en el sub-proyecto 6).
2. Como consecuencia: los cambios de valor de knob (Function A/B) deben verse en vivo
   en las barras normales del dashboard, ya que el overlay era la única confirmación
   visual de "esto cambió" que existía.
3. La barra de selección de sample (modo 0, Function A) pasa de un relleno continuo
   proporcional al valor crudo del knob a un **segmentado tipo paginador**: un
   segmento resaltado por sample (agrupando en potencias de 2 si hay muchos),
   reflejando que la selección ya es discreta internamente.

## No-objetivos

- No se toca el mecanismo de overlay **persistente** (`overlay_show_panel(persistent=true)`,
  usado por el modo 8 / Browse SD) — ese overlay sigue existiendo tal cual, se rediseña
  en un sub-proyecto aparte.
- El segmentado tipo paginador es exclusivo de la barra de Function A del modo 0
  (selección de sample). Ninguna otra barra cambia su estilo de relleno: Function B
  del modo 0 (intensidad de break fx) y Function A/B de los modos 1-7 (parámetros
  continuos: filtro, gate, probabilidades, volumen, etc.) siguen con el relleno
  continuo actual, solo que ahora en vivo (ver punto 2).
- No cambia la lógica de selección de sample en sí (`sample_change = input_knob[i].Value()
  * sample_count / input_knob[i].ValueMax()`, `main.cpp`) — ya es correcta y discreta,
  solo cambia cómo se **dibuja**.

## Hallazgos de la investigación (verificados en código, no re-descubrir)

- El dirty-tracking de `gamepi_ui_tick()` (`src/gamepi13/ui.cpp:465-466`) **ya** marca
  `W_BARA`/`W_BARB` sucios cuando cambia `s.knob_a`/`s.knob_b`, no solo cuando cambia
  el modo. El único motivo por el que hoy la barra normal del dashboard no se ve
  actualizar en vivo es que, mientras el overlay está activo (`overlay_on == true`),
  `gamepi_ui_tick()` retorna temprano (línea 479, `if (overlay_persistent ||
  time_us_64() < overlay_deadline_us) return;`) sin llegar nunca al loop de flush que
  procesa esas banderas. Al quitar las 3 funciones de overlay no-persistente (que son
  las únicas que ponen `overlay_on = true` fuera del modo 8), las barras normales
  quedan libres para actualizarse en vivo sin necesitar ningún mecanismo nuevo.
- Las 3 funciones a borrar y sus 6 sitios de llamada (`src/main.cpp`):
  - `gamepi_ui_overlay_mode(uint8_t mode)` — líneas 1885 y 1921 (al cambiar de modo).
  - `gamepi_ui_overlay_tempo(uint16_t bpm)` — líneas 1981 y 2009 (ajuste de tempo,
    modo 7 Function B).
  - `gamepi_ui_overlay_param(uint8_t mode, bool is_b, uint16_t val)` — líneas 1985 y
    2013 (cualquier otro ajuste de Function A/B vía L/R).
- `overlay_show_panel(bool persistent = false)` es la función compartida que las 3
  funciones de overlay no-persistente y `sd_panel_title()` (modo 8) usan para activar
  `overlay_on`/`overlay_deadline_us`/dibujar el marco. Solo se borran las 3 funciones
  de overlay no-persistente; `overlay_show_panel()` y `sd_panel_title()` quedan
  intactas (siguen sirviendo al modo 8).
- El banco de audio soporta hasta `PIKO_BANK_MAX_SAMPLES = 128` samples reales
  (`src/PikoAudioBank.h`) — no es un límite teórico, hay que diseñar el segmentado
  para ese caso extremo, no solo para bancos típicos pequeños.
- `GamepiUiState` (`src/gamepi13/ui.h`) ya expone `sample_idx`/`sample_count`
  (`uint16_t`, usados hoy por `draw_name()`) — no hace falta agregar campos nuevos
  para el segmentado.

## Mecanismo

### 1. Quitar overlay no-persistente

- Borrar `gamepi_ui_overlay_mode()`, `gamepi_ui_overlay_param()`,
  `gamepi_ui_overlay_tempo()` de `src/gamepi13/ui.cpp` y sus 3 declaraciones de
  `src/gamepi13/ui.h`.
- Borrar los 6 sitios de llamada en `src/main.cpp` (sin reemplazarlos por nada — no
  hace falta ningún otro código en su lugar, ya que el dirty-tracking existente se
  encarga de que la barra normal refleje el cambio en el siguiente tick).
- `overlay_show_panel()`/`sd_panel_title()`/`gamepi_ui_sd_close()` y todo lo demás del
  mecanismo de overlay persistente (modo 8) quedan sin cambios.

### 2. Barra de sample segmentada (modo 0, Function A)

- `draw_function_a()` (`ui.cpp`), cuando `m == 0`, llama a una función nueva
  `draw_sample_bar(bar_y, sample_idx, sample_count, col)` en vez de `draw_bar()`. Para
  el resto de los modos (`m != 0`) sigue llamando a `draw_bar()` como hoy, sin cambios.
- `draw_sample_bar()`:
  - Si `sample_count <= 1`: dibuja un único segmento resaltado ocupando todo el ancho
    (224px) — no hay selección real que mostrar, pero la barra no queda vacía/confusa.
  - Si no: calcula `group_size` como la menor potencia de 2 (empezando en 1) tal que
    `ceil(sample_count / group_size) <= 32`. Dibuja `ceil(sample_count / group_size)`
    segmentos (nunca más de 32) dentro del mismo ancho de 224px (`x` de 8 a 231, igual
    que `draw_bar()` hoy), con 1px de espacio entre segmentos, cada uno de ancho
    `(224 - (n_segments - 1)) / n_segments` px. El segmento resaltado es
    `sample_idx / group_size` (división entera) — se dibuja con el color `col` (el
    mismo color por modo que ya recibe `draw_bar()`); el resto de los segmentos se
    dibuja en `COL_DARK` (igual que el track vacío de `draw_bar()` hoy).
  - Con el techo de 32: en la práctica casi ningún banco necesita agrupar (la mayoría
    tiene pocos samples, 1 segmento = 1 sample); en el peor caso real
    (`sample_count == 128`) se agrupa de a 4 (`group_size = 4`, ya que
    `ceil(128/2)=64 > 32` pero `ceil(128/4)=32 <= 32`) → exactamente 32 segmentos de
    ~6px cada uno, visualmente distinguibles con su espacio de 1px.

## Arquitectura

Sin cambios de arquitectura. `draw_sample_bar()` es una función nueva, autocontenida,
en el mismo archivo (`ui.cpp`), con la misma firma de "color como parámetro" que
`draw_bar()` ya usa — no introduce ningún widget, zona (`kRect`) ni mecanismo de
dirty-tracking nuevo (sigue siendo parte de `W_BARA`, que ya existe y ya dispara
redibujado cuando cambia `s.knob_a`, y ahora también cuando cambia `s.sample_idx`,
detalle cubierto en Manejo de errores).

## Manejo de errores

- El dirty-tracking de `W_BARA` hoy compara `s.knob_a != drawn.knob_a` — como
  `draw_sample_bar()` en modo 0 depende de `s.sample_idx`/`s.sample_count` (no
  directamente de `s.knob_a`), hay que agregar esas dos comparaciones a la condición
  que marca `W_BARA` sucio, para que un cambio de sample sin cambio de `knob_a` bruto
  (poco común, pero posible por redondeo de la división entera) igual redibuje la
  barra. Se agrega junto a la comparación existente, sin duplicar lógica.
- División por cero: `group_size` nunca puede ser 0 (arranca en 1 y solo se duplica),
  y el camino `sample_count <= 1` está cubierto aparte, así que no hay riesgo de
  dividir por `sample_count` cero en ningún cálculo.

## Pruebas

1. Build `build-gamepi`: sin errores (las 6 llamadas borradas de `main.cpp` no dejan
   ninguna referencia colgante a las 3 funciones eliminadas).
2. Hardware:
   - Cambiar de modo (Select) y ajustar cualquier parámetro (L/R): confirmar que NO
     aparece ningún overlay/recuadro temporal en el centro de la pantalla, y que la
     barra normal correspondiente se actualiza en vivo, sin demora, mientras se
     mantiene presionado L/R.
   - Modo 0, Function A: confirmar que la barra se ve segmentada (no un relleno
     liso), que el segmento resaltado coincide con el sample realmente seleccionado
     (visible en el nombre/índice del dashboard, `draw_name()`), y que navegar con
     L/R mueve el resaltado de forma discreta.
   - Confirmar que modo 8 (Browse SD) no se ve afectado — su overlay persistente
     sigue funcionando exactamente igual.
   - Regresión: el resto del dashboard (BPM, reloj, play/stop, waveform, 9 íconos de
     modo, colores por modo) sin cambios.

## Riesgos conocidos

- **Legibilidad de segmentos muy angostos en el caso extremo (32 segmentos, ~6px
  cada uno)** — mitigado por el techo de 32 (elegido para mantener un ancho mínimo
  razonable dentro de los 224px disponibles); si en hardware se ve demasiado angosto,
  es un ajuste de una sola constante (el techo de 32), no un cambio de diseño.
- **Quitar el overlay elimina también la única lectura numérica (%) de un parámetro**
  — aceptado explícitamente por el usuario como parte del pedido (las barras ya
  comunican la posición relativa sin necesitar el número exacto); no se agrega un
  reemplazo textual en este sub-proyecto.
