# Etiquetas de Function A/B para los modos 1-7 — Diseño

**Fecha:** 2026-07-19
**Estado:** aprobado por el usuario
**Prerequisito:** Dashboard con bitmaps de Lopaka (modo 0) completo, verificado en
hardware, y limpio de los frames referenciales. Rama `port/rp2350-gamepi13`.
**Riesgo:** bajo — extensión directa de una tabla ya construida, sin cambios de
arquitectura ni de `ui.cpp`.

## Objetivo

Los modos 1-7 muestran hoy su nombre de Function A/B en texto (`Paint_DrawString_EN`,
fallback ya implementado en `draw_function_label()`) porque `kModeABitmap[1..7]`/
`kModeBBitmap[1..7]` apuntan a `nullptr`. El usuario ya diseñó en Lopaka las 14
etiquetas gráficas faltantes (`MODE_1.txt`..`MODE_7.txt`, 2 por modo). Se agregan esas
14 bitmaps y se reemplazan los `nullptr` correspondientes — los 7 modos pasan a
mostrar su etiqueta como gráfico, igual que modo 0.

## No-objetivos

- No cambia nada de `ui.cpp` — `draw_function_label()`/`draw_function_a()`/
  `draw_function_b()` ya soportan el mecanismo bitmap-o-texto tal cual están.
- No cambia el mapeo de modos ni sus nombres de texto (`kModeA`/`kModeB`).
- No incluye el ícono de reloj MIDI (sigue pendiente, no relacionado a este cambio).

## Hallazgos de la investigación (verificados en código, no re-descubrir)

- **Los 7 archivos** (`MODE_1.txt`..`MODE_7.txt`) comparten el mismo frame completo
  que `MODE_0.txt` (BPM, reloj, play/stop, dígitos de sample idx/count, 9 íconos de
  modo, mismas posiciones) — la ÚNICA diferencia real entre ellos son las dos
  etiquetas de Function A/B. El resto de esos assets duplicados NO se vuelven a
  importar (ya están vendorizados desde modo 0).
- **Las 14 etiquetas usan exactamente las mismas coordenadas que modo 0**: Function A
  siempre en `(1, 107)`, Function B siempre en `(0, 157)`, alto 20px en las 14 —
  confirmado leyendo los `tft.pushImage(...)` de los 7 archivos. Solo cambia el ancho
  de cada una.
- **Mapeo modo → nombres de archivo → nombres de texto ya existentes**
  (`kModeA`/`kModeB` en `src/gamepi13/ui.cpp`), anchos confirmados:

  | Modo | Function A: asset (ancho) | Function B: asset (ancho) |
  |---|---|---|
  | 1 (FILTRO/STRETCH) | `image_FILTER_pixels` (92) | `image_STRETCH_pixels` (105) |
  | 2 (GATE/PROB GATE) | `image_GATE_1_pixels` (62) | `image_P_GATE_pixels` (93) |
  | 3 (PROB SALTO/PROB RETRIG) | `image_JUMP_pixels` (62) | `image_P_RETRIG_pixels` (120) |
  | 4 (PROB TUNEL/PROB REVERSA) | `image_TUNNEL_pixels` (90) | `image_P_REVERSE_pixels` (134) |
  | 5 (SEC GRABAR/SEC PLAY) | `image_REC_SEQ_pixels` (105) | `image_PLAY_SEQ_pixels` (120) |
  | 6 (GUARDAR/CARGAR) | `image_SAVE_pixels` (61) | `image_LOAD_pixels` (63) |
  | 7 (VOLUMEN/TEMPO) | `image_VOLUME_pixels` (92) | `image_TEMPO_pixels` (77) |

- **Mismo patrón de importación ya usado dos veces este mes** (splash, dashboard modo
  0): extracción mecánica vía `sed` desde los archivos fuente, verificación de conteo
  de píxeles contra ancho×alto antes de dar por buena la extracción.

## Mecanismo

Se agregan 14 arrays nuevos (`kFilterLabel`, `kStretchLabel`, `kGate1Label`,
`kPGateLabel`, `kJumpLabel`, `kPRetrigLabel`, `kTunnelLabel`, `kPReverseLabel`,
`kRecSeqLabel`, `kPlaySeqLabel`, `kSaveLabel`, `kLoadLabel`, `kVolumeLabel`,
`kTempoLabel`) a `src/gamepi13/ui_bitmaps.h`, cada uno envuelto en un
`ModeLabelBitmap` (struct ya existente: `{pixels, w, h}`, alto siempre 20). Se
reemplazan las 14 entradas `nullptr` de `kModeABitmap[1..7]`/`kModeBBitmap[1..7]`
(hoy `nullptr` para los índices 1-7) por punteros a estos nuevos
`ModeLabelBitmap`. `draw_function_label()` ya elige bitmap-o-texto según si el
puntero es `nullptr` — no se toca esa función.

## Arquitectura

Sin cambios de arquitectura — solo datos nuevos en un archivo ya existente
(`ui_bitmaps.h`). `ui.cpp` no se modifica en absoluto.

## Manejo de errores

No aplica — no hay entradas externas ni estados inválidos nuevos.

## Pruebas

1. Build `build-gamepi`: sin errores.
2. Hardware: cambiar de modo (Select) a cada uno de los modos 1-7 y confirmar que
   "Function A"/"Function B" aparecen como gráfico (ya no como texto) en la posición
   correcta, sin invadir la barra ni el ícono vecino. Confirmar que modo 0 y el modo 8
   (Browse SD, sin etiqueta propia) siguen sin cambios.

## Riesgos conocidos

- **Volumen de datos**: 14 arrays más a importar — mismo riesgo de transcripción ya
  mitigado con importación mecánica vía `sed` + verificación de conteo, igual que las
  veces anteriores.
- Ninguno más relevante — cambio de bajo riesgo, sin tocar lógica.
