# Refresh de UI estilo Elektron — Diseño (visión + decomposición)

**Fecha:** 2026-07-20
**Estado:** visión aprobada por el usuario (mockups). Rama `port/rp2350-gamepi13`.
**Checkpoint de rollback:** tag `pre-ui-refresh-2026-07-20` (commit `8f3942e`).
**Riesgo:** medio — muchos cambios visuales acumulados; se mitiga con la decomposición
en sub-proyectos chicos, cada uno con su verificación en hardware, y el tag de rollback.

## Objetivo

El dashboard actual "no resuena" en tres ejes concretos que el usuario señaló, bajo un
norte estético claro: **verse moderno y dinámico como Elektron** (Digitakt/Model:Samples).
Los tres ejes:

1. **Tipografía**: la fuente actual se ve genérica/blanda. Se quiere condensada técnica
   (mayúsculas con tracking, números condensados pesados) — look "instrumento de estudio".
2. **Barras**: como no hay knobs, el control es por pasos de botón. Un relleno continuo
   miente sobre eso; **pasos discretos + el valor numérico** son más concretos.
3. **Ausencias**: los modos de grabar/reproducir secuencia (5) y guardar/cargar (6) no
   dan feedback visible; el reloj MIDI todavía es texto plano.

**Requisito transversal:** **todo el texto en inglés** (hoy hay español en Browse SD,
placeholders y fallbacks de etiquetas).

## Decisiones de diseño (aprobadas con mockups)

- **Barras (Function A/B):** segmentadas — ~25 bloques (1 bloque = 1 paso de botón, ya
  que `GAMEPI_KNOB_STEP=164` de 4095 ≈ 25 pasos), encendidos hasta el paso actual en el
  color del modo, + un **valor normalizado 0–127** en números condensados grandes a la
  derecha (`val = knob * 127 / 4095`). Estilo Elektron.
  - Excepción: selección de sample (modo 0, Function A) sigue siendo un paginador con
    su índice de sample (no 0–127), ya que representa una selección discreta, no un
    parámetro continuo.
- **Tipografía:** condensada técnica (dirección "Elektron Digitakt"). Se realiza como
  **bitmaps nuevos** diseñados en Lopaka (dígitos 0–9 + "/", e íconos), ya que todo el
  texto del dispositivo es bitmap. El texto dinámico (nombres de archivo) sigue en la
  fuente vendorizada genérica (sin fuente custom completa por ahora).
- **Feedback modos 5/6:** indicadores **persistentes** mientras el estado dure (**REC**
  rojo mientras graba el secuenciador, **SEQ** cian mientras reproduce) + un **flash
  breve** para eventos momentáneos (**SAVED** / **LOADED**). Encaja con el "feedback en
  vivo" que ya se buscó al quitar los overlays.
- **Ícono MIDI:** conector DIN de 5 pines, en el mismo estilo que los íconos INT/EXT
  existentes (reemplaza el texto "MIDI").
- **Idioma:** todo el texto on-screen en inglés.

## Decomposición en sub-proyectos

Se separa lo que es **código puro** (sin dependencia de assets) de lo que **depende de
que el usuario diseñe bitmaps en Lopaka**, para trabajar en paralelo. Cada sub-proyecto
tiene su propio ciclo spec→plan→implementación→verificación en hardware.

| # | Sub-proyecto | Assets de Lopaka (usuario) | Depende de |
|---|---|---|---|
| 1 | **Texto a inglés** (Browse SD, placeholders, fallbacks de `kModeA`/`kModeB`) | — (code-only) | — |
| 2 | **Dígitos condensados nuevos** → swap BPM + índice de sample al nuevo estilo | dígitos 0–9 + "/" | — |
| 3 | **Barras segmentadas con valor 0–127** (generaliza el paginador a todas las barras) | usa dígitos de #2 | #2 |
| 4 | **Feedback modos 5/6 + ícono MIDI** (REC/SEQ persistentes + flash SAVED/LOADED + DIN MIDI) | íconos REC/SEQ/MIDI | — |
| 5 | **Etiquetas de modo restyled** (condensadas + inglés, re-exportadas) | 16 etiquetas | estilo de #2 |

**Orden de integración sugerido:** 1 → 2 → 3 → 4 → 5.

**Trabajo en paralelo:** el sub-proyecto #1 (inglés) es code-only y arranca de inmediato
mientras el usuario diseña en Lopaka los assets para #2/#3/#4/#5.

## Detalle de texto a inglés (#1, para arrancar ya)

Cadenas a traducir (todas en `src/gamepi13/ui.cpp` salvo el placeholder en `main.cpp`):
- Browse SD: `"Leyendo tarjeta..."` → `"Reading card..."`; `"L: ciclar lista"` (o el
  ícono `kSdLCycle`, que ya es gráfico) → hint en inglés; `"Cargado (banco activo)"` →
  `"Loaded (active bank)"`; `"Mantener R: cargar"` → `"Hold R: load"`; `"Cargando..."`
  → `"Loading..."`; `"Listo"` → `"Done"`; `"Error"` → `"Error"`; `"No se pudo cargar"`
  → `"Load failed"`; `"Sin tarjeta o sin archivos"` → `"No card or files"`.
- Placeholder de sample (`src/main.cpp`): `"(sin samples)"` → `"(no samples)"`.
- Fallbacks de etiqueta `kModeA`/`kModeB` (hoy en español, hoy inalcanzables porque los
  8 modos tienen bitmap): pasar a inglés por consistencia (`"FILTRO"`→`"FILTER"`,
  `"PROB SALTO"`→`"JUMP PROB"`, `"SEC GRABAR"`→`"REC SEQ"`, `"GUARDAR"`→`"SAVE"`, etc.).
- Nota: el ícono `kSdLCycle` ya es gráfico ("L: cycle") — no es texto, no requiere
  traducción; si su bitmap dice algo en un idioma, se re-exporta en el sub-proyecto de
  íconos.

## Arquitectura

Sin cambios de arquitectura estructural. Todo pasa por los mecanismos ya existentes:
tabla de bitmaps en `ui_bitmaps.h` (import mecánico vía `sed` + verificación de conteo),
zonas/dirty-tracking de `ui.cpp`, y `GamepiUiState` para exponer estado nuevo desde
`main.cpp` (valor 0–127 de barras — derivable de `knob_a`/`knob_b`; flags de
`recording`/`seq_playing`; evento transitorio de save/load). El feedback persistente usa
el mismo patrón de widget/dirty que el resto del dashboard.

## Pruebas

Cada sub-proyecto se verifica en hardware por separado (el usuario con la placa), igual
que toda la sesión. El tag `pre-ui-refresh-2026-07-20` permite rollback de emergencia.

## Riesgos conocidos

- **Dependencia de assets de Lopaka**: #2/#3/#4/#5 no pueden integrarse hasta que el
  usuario produzca los bitmaps correspondientes. #1 (inglés) no depende de nada.
- **Legibilidad de ~25 segmentos finos** en el LCD real: se validó la dirección con
  mockup; el ancho real (≤224px menos el espacio del número) se ajusta en hardware.
- **Espacio horizontal para el valor 0–127**: la barra se angosta para dejar lugar al
  número a la derecha (como en el mockup, opción C) — geometría a confirmar en hardware.
