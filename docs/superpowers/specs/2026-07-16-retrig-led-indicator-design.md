# Indicador de retrigger en la barra de LEDs — Diseño

**Fecha:** 2026-07-16
**Estado:** aprobado por el usuario
**Prerequisito:** Fase 3 (microSD) completa y verificada en hardware, rama `port/rp2350-gamepi13`.
**Riesgo:** bajo — no toca audio, timing, flash ni SD. Solo lectura adicional de estado ya existente para pintar la LCD.

## Objetivo

Distinguir visualmente, en la barra de 8 LEDs virtuales del dashboard, cuándo el motor de
audio está en modo retrigger/stutter (dos botones musicales combinados) en vez de un jump
simple (un solo botón) — hoy el LCD no hace esa distinción, según quedó anotado en
`GAMEPI13-INTERFACE.md` sección 6.

## No-objetivos

- No se toca la lógica de audio/retrigger en sí (`btn_retrig`, `button_on`, `button_on2`,
  `retrig_len()`) — solo se lee su estado existente.
- No se agrega un indicador separado para "jump simple" — ya es visible hoy como el LED
  normal (naranja) que se prende con el beat; el hueco real es distinguir el *stutter*.
- No se anima un fundido/decaimiento al soltar — el cian desaparece en el mismo tick que
  `btn_retrig` pasa a `false`, igual que el resto del motor.

## Mecanismo

La barra de LEDs (`draw_leds()` en `src/gamepi13/ui.cpp`) ya pinta cada uno de los 8
botones musicales en naranja (brillante si `leds[i] >= 128`, tenue si `>= 8`, apagado si
no) según `s.leds[i]`, una amplitud 0-255 que ya trae `LEDArray`. Cuando el retrigger está
activo, los dos botones involucrados (`button_on`, el primero presionado; `button_on2`, el
segundo, que además elige la subdivisión) se pintan en **cian sólido** (`COL_CYAN`,
`0x3DFF` — el mismo tono ya usado para Function B en el resto de la UI), ignorando el
nivel de amplitud: la idea es que sea inconfundible, no una gradación más de brillo.

## Arquitectura

`btn_retrig`, `button_on`, `button_on2` son variables globales de `src/main.cpp`, ya
compartidas hoy sin lock explícito entre la ISR de audio (`pwm_interrupt_handler()`, donde
se escriben) y el loop principal de botones/LCD (mismo core, mismo patrón ya usado por
`bpm_set`/`distortion` — lecturas de un solo byte, atómicas en Cortex-M, sin riesgo de
lectura partida).

### Cambios por archivo

- **`src/gamepi13/ui.h`**: agregar `uint8_t retrig_leds_mask;` a `GamepiUiState` — bitmask
  de 8 bits, uno por botón musical (bit `i` = 1 si el LED `i` debe pintarse cian).
- **`src/main.cpp`**: en el mismo bloque donde ya se arma `uis` cada tick (junto a
  `uis.leds[j] = ledarray.Get(j);`), calcular la máscara:
  ```cpp
  uis.retrig_leds_mask = 0;
  if (btn_retrig) {
    if (button_on < NUM_BUTTONS) uis.retrig_leds_mask |= (uint8_t)(1u << button_on);
    if (button_on2 < NUM_BUTTONS) uis.retrig_leds_mask |= (uint8_t)(1u << button_on2);
  }
  ```
- **`src/gamepi13/ui.cpp`**:
  - `draw_leds()`: si el bit `i` de `s.retrig_leds_mask` está prendido, usar `COL_CYAN` en
    vez de la lógica naranja brillante/tenue existente para ese LED.
  - `gamepi_ui_tick()`: extender el chequeo de "widget sucio" para marcar `dirty[W_LEDS]`
    también cuando `s.retrig_leds_mask != drawn.retrig_leds_mask` (hoy solo compara
    `s.leds` con `memcmp`).

## Manejo de errores

No aplica — no hay entradas externas, fallas de hardware, ni estados inválidos posibles;
la máscara es puramente derivada de estado ya validado por el motor de audio existente.

## Pruebas

1. **Build**: ambas variantes compilan (`build` original sin cambios — todo bajo
   `#if PIKO_GAMEPI13` o en archivos que ya solo compilan con el flag ON).
2. **Hardware**:
   - Presionar un solo botón musical: el LED correspondiente se prende naranja, como
     siempre (sin cambios).
   - Presionar dos botones musicales a la vez: los dos LEDs correspondientes cambian a
     cian mientras ambos estén presionados.
   - Soltar uno de los dos: el cian desaparece de inmediato en ambos LEDs.
   - Regresión: el resto del dashboard (BPM, sample, modo, barras A/B, puntos) sigue
     comportándose igual.

## Riesgos conocidos

Ninguno de nota — cambio aditivo, acotado a 2 archivos ya conocidos de la Fase 2/3, sin
tocar audio/timing/flash/SD.
