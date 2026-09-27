# Colores por modo (barras de Function A/B) — Diseño

**Fecha:** 2026-07-19
**Estado:** aprobado por el usuario
**Prerequisito:** Dashboard con bitmaps de Lopaka (modo 0) + etiquetas de Function A/B
para los 8 modos, ambos completos y verificados en hardware. Rama
`port/rp2350-gamepi13`.
**Riesgo:** bajo — cambia solo qué color se pasa a funciones de dibujo ya existentes,
sin tocar geometría, layout ni el mecanismo bitmap-o-texto.

## Objetivo

Hoy la barra de Function A (`draw_bar()`, llamada desde `draw_function_a()`) siempre
se dibuja en rosa (`COL_PINK`) y la de Function B siempre en cian (`COL_CYAN`), sin
relación con el modo activo. El usuario pidió color por modo ("sample=rojo, fx=azul,
así con todos los elementos correspondientes a los modos"). Se agrega una paleta de 8
colores, uno por modo, reutilizados como par Function A / Function B con un desplazamiento
fijo en el ciclo de 8 — de forma que el modo 0 da exactamente rojo (A) / azul (B), tal
como pidió el usuario.

## No-objetivos

- No se recolorean las 16 etiquetas de Function A/B (bitmaps de Lopaka, imágenes
  RGB565 con el color ya "horneado" en el píxel) — recolorearlas requeriría
  re-exportar 16 assets nuevos desde Lopaka, fuera de alcance de este sub-proyecto.
- No se tocan los 9 íconos de modo (`kModeIcons`) — ya vienen coloreados/diseñados
  por modo desde Lopaka.
- No cambia la geometría, posición ni el mecanismo bitmap-o-texto de
  `draw_function_label()`/`draw_bar()` — solo el color que reciben.

## Hallazgos de la investigación

- `kSampleBar`/`kBreakFxBar` (`src/gamepi13/ui_bitmaps.h`) son dos arrays vendorizados
  de Lopaka que **no se usan en ningún lado** de `ui.cpp` — `draw_bar()` siempre dibuja
  un rectángulo programático liso, nunca esas imágenes. Mismo patrón de asset huérfano
  que `kFilenameFrame`/`kWaveformFrame` (sub-proyecto 1, ya resuelto). El usuario
  confirmó descartarlos y colorear por código en vez de rediseñarlos en Lopaka.
- `draw_function_label()` recibe un parámetro `text_col` que solo se usa en su rama
  `else` (cuando el bitmap es `nullptr`) — hoy inalcanzable en la práctica para los
  modos 0-7, ya que los 8 tienen bitmap asignado desde el sub-proyecto 2. Se mantiene
  el parámetro (robustez ante un futuro bitmap faltante) pero se actualiza su valor
  para quedar consistente con la nueva paleta por modo, en vez de dejarlo desactualizado.

## Mecanismo

Dos tablas nuevas de 8 elementos en `src/gamepi13/ui.cpp`, junto a las macros `COL_*`
existentes, siguiendo el mismo estilo de tabla indexada por modo que ya usa el archivo
(`kModeA`, `kModeABitmap`, etc.):

```cpp
#define COL_RED 0xFB8E      // #f87171
#define COL_ORANGE2 0xFC87  // #fb923c (distinto de COL_ORANGE/amber ya existente)
#define COL_YELLOW 0xFE62   // #facc15
#define COL_TEAL 0x269D     // #22d3ee
#define COL_VIOLET 0xA45F   // #a78bfa

static const uint16_t kModeColorA[8] = {COL_RED,     COL_ORANGE2, COL_YELLOW, COL_GREEN,
                                        COL_TEAL,    COL_BLUE,    COL_VIOLET, COL_PINK};
static const uint16_t kModeColorB[8] = {COL_BLUE,    COL_VIOLET,  COL_PINK,   COL_RED,
                                        COL_ORANGE2, COL_YELLOW,  COL_GREEN,  COL_TEAL};
```

Paleta completa (aprobada visualmente con mockup):

| Modo | Function A | Function B |
|---|---|---|
| 0 (Sample/Break FX) | Rojo `#f87171` | Azul `#60a5fa` |
| 1 (Filtro/Stretch) | Naranja `#fb923c` | Violeta `#a78bfa` |
| 2 (Gate/Prob. gate) | Amarillo `#facc15` | Rosa `#f472b6` |
| 3 (Prob. salto/retrig) | Verde `#4ade80` | Rojo `#f87171` |
| 4 (Prob. túnel/reversa) | Cian `#22d3ee` | Naranja `#fb923c` |
| 5 (Grabar/play seq.) | Azul `#60a5fa` | Amarillo `#facc15` |
| 6 (Guardar/cargar) | Violeta `#a78bfa` | Verde `#4ade80` |
| 7 (Volumen/tempo) | Rosa `#f472b6` | Cian `#22d3ee` |

`COL_GREEN` (#4ade80), `COL_BLUE` (#60a5fa) y `COL_PINK` (#f472b6) ya existen en la
paleta actual y se reutilizan tal cual; `COL_RED`, `COL_ORANGE2`, `COL_YELLOW`,
`COL_TEAL` y `COL_VIOLET` son 5 constantes nuevas, mismo estilo "pastel saturado"
(tailwind-400/500) que las existentes.

`draw_function_a()`/`draw_function_b()` dejan de pasar `COL_PINK`/`COL_CYAN` fijos a
`draw_bar()` y a `draw_function_label()` — usan `kModeColorA[m]`/`kModeColorB[m]` en su
lugar (`m` ya calculado ahí mismo, clamp a 0 si `s.mode >= 8`, sin cambios en esa
lógica). `draw_bar()` no cambia de firma.

`kSampleBar`/`kBreakFxBar` se borran por completo de `src/gamepi13/ui_bitmaps.h` (no
se usan, no se guardan "por si acaso" — mismo criterio que el sub-proyecto 1).

## Arquitectura

Sin cambios de arquitectura — dos tablas de datos nuevas + reemplazo de dos literales
de color por dos lookups indexados por modo, dentro de los mismos archivos ya
existentes. Ningún widget, zona (`kRect`), ni el sistema de dirty-rect cambian.

## Manejo de errores

No aplica — `m` ya está clampeado a `[0,7]` antes de este cambio (código existente),
así que el índice a `kModeColorA`/`kModeColorB` siempre es válido.

## Pruebas

1. Build `build-gamepi`: sin errores.
2. Hardware: recorrer los 8 modos (Select) y confirmar que la barra de Function A y la
   de Function B cambian de color según la tabla de arriba, sin afectar geometría,
   posición, ni el contenido de las etiquetas bitmap. Confirmar que el modo 8 (Browse
   SD) no se ve afectado (sus zonas de barra están cubiertas por el overlay persistente,
   sin cambios).

## Riesgos conocidos

- **Legibilidad de algún color contra el fondo negro** — mitigado con el mockup visual
  ya revisado y aprobado antes de escribir este spec; de todos modos, la verificación en
  hardware (LCD real, distinto contraste/gamma que un monitor) es el chequeo final.
- Ninguno más relevante — cambio de bajo riesgo, solo datos + reemplazo de literales.
