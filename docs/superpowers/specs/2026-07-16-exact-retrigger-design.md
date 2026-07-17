# Retrigger con subdivisión exacta (Start + 2do botón) — Diseño

**Fecha:** 2026-07-16
**Estado:** aprobado por el usuario
**Prerequisito:** Todas las fases + mejoras de bajo riesgo (retrigger en LEDs, waveform con
playhead) completas y verificadas, rama `port/rp2350-gamepi13`.
**Riesgo:** bajo-medio — toca la ISR de audio (`pwm_interrupt_handler()`), pero de forma
quirúrgica: una rama condicional adicional sobre lógica que ya existe, sin nuevo estado
compartido entre núcleos ni cambios cuando la condición no se cumple.

## Objetivo

Hoy, al activar el retrigger/stutter (dos botones musicales combinados), la subdivisión
(`retrig_sel`) se sortea con `randint()` dentro de una ventana de 2 niveles determinada por
el segundo botón presionado (`main.cpp:773-802`). Se agrega la posibilidad de fijar esa
subdivisión a un valor EXACTO (sin azar) manteniendo Start presionado en el instante del
disparo, dando control predecible en vivo cuando se lo necesita, sin perder el
comportamiento aleatorio original cuando no se usa Start.

## No-objetivos

- No se toca `retrig_max` (repeticiones), pitch up/down, filtro, ni reducción de volumen —
  esas capas siguen sorteando exactamente igual, con o sin Start sostenido.
- No se agrega ningún indicador visual nuevo en el LCD para este modo — es un gesto
  momentáneo, no un toggle con estado persistente que necesite mostrarse.
- No se cambia el comportamiento del retrigger disparado por probabilidad
  (`probability_retrig`, sin segundo botón) — Start no tiene efecto ahí, porque no hay un
  "segundo botón" cuyo valor fijar.

## Mecanismo

En el bloque que arma el trigger de retrigger (`main.cpp`, dentro de
`pwm_interrupt_handler()`, `if (btn_retrig && !fx_retrig) { ... }`), donde hoy:

```cpp
if (button_on2 >= NUM_BUTTONS) {
  retrig_sel = randint(2, 16);
} else {
  switch (button_on2) {
    case 0: retrig_sel = randint(0, 2); break;
    case 1: retrig_sel = randint(2, 4); break;
    // ... hasta case 7: retrig_sel = randint(14, 16); break;
  }
}
```

Se agrega: si `btn_start.On()` es verdadero Y `button_on2 < NUM_BUTTONS` (hay un segundo
botón real, no el camino de probabilidad), `retrig_sel` toma el **punto medio** de la misma
ventana que hoy se sortea, en vez de llamar a `randint()`:

| 2do botón | Ventana actual (aleatoria) | Valor exacto con Start |
|---|---|---|
| 0 | randint(0, 2) | 1 |
| 1 | randint(2, 4) | 3 |
| 2 | randint(4, 6) | 5 |
| 3 | randint(6, 8) | 7 |
| 4 | randint(8, 10) | 9 |
| 5 | randint(10, 12) | 11 |
| 6 | randint(12, 14) | 13 |
| 7 | randint(14, 16) | 15 |

El punto medio preserva la intuición ya existente de "botón 0 = más lento, botón 7 = más
rápido" — mismo mapeo mental que hoy, sin el componente aleatorio.

## Integración con el doble rol de Start

Start ya distingue toque simple (mute/start-stop) de mantenido-como-modificador
(`gamepi_start_used_as_modifier`, ver sección "El botón Start tiene doble rol" en
`GAMEPI13-INTERFACE.md`). Cuando se fija la subdivisión exacta, se marca
`gamepi_start_used_as_modifier = true` en el mismo instante — así, soltar Start después de
un retrigger exacto no dispara el toggle de mute/start-stop por accidente (mismo patrón ya
usado en el bloque de Function A/B con L/R).

## Arquitectura

- `btn_start` es un objeto global ya leído desde el loop principal (`main.cpp`) con el
  mismo patrón sin locks que el resto del estado compartido entre la ISR de audio y el loop
  de botones (`bpm_set`, `distortion`, `sample`, etc.) — leerlo también desde dentro de la
  ISR (`pwm_interrupt_handler()`) no introduce sincronización nueva; ya es la misma clase de
  lectura cross-core/cross-contexto que ya existe en este archivo.
- **`btn_start` solo existe bajo `#if PIKO_GAMEPI13`** (`main.cpp:118-120`) — el hardware
  original no tiene un botón Start dedicado. El bloque de trigger de retrigger
  (`pwm_interrupt_handler()`) es código COMPARTIDO entre ambos builds, así que el nuevo
  chequeo de `btn_start.On()` debe quedar envuelto en su propio `#if PIKO_GAMEPI13 ... #endif`
  dentro de ese bloque compartido. Con el flag OFF, el comportamiento queda exactamente
  igual al actual (siempre sortea).
- El cambio vive enteramente en `main.cpp`, en el bloque de trigger de retrigger — no toca
  `retrig_len()`, `ui.cpp`, ni `GamepiUiState`.

## Manejo de errores

No aplica — no hay entradas externas ni estados inválidos nuevos; es una rama condicional
sobre datos ya validados (`button_on2 < NUM_BUTTONS` ya se chequea hoy para elegir el
`switch`).

## Pruebas

1. **Build**: ambas variantes compilan; la original (flag OFF) queda con comportamiento
   idéntico al actual (el chequeo de `btn_start.On()` está envuelto en `#if PIKO_GAMEPI13`,
   ver Arquitectura).
2. **Hardware**:
   - Combinar 2 botones SIN Start: el retrigger se sortea como siempre (sin cambios).
   - Combinar 2 botones CON Start sostenido: la subdivisión es siempre la misma para un
     mismo segundo botón (repetible), y corresponde al punto medio de la tabla.
   - Soltar Start después de un retrigger exacto: no dispara el toggle de mute/start-stop.
   - Retrigger por probabilidad (sin segundo botón), con o sin Start: comportamiento sin
     cambios (Start no tiene efecto ahí).
   - Regresión: el resto del motor de audio (pitch, filtro, volumen, repeticiones) sigue
     sorteando igual que antes, con o sin Start.
3. **Regresión en hardware original** (flag OFF, sin GamePi13): el retrigger se comporta
   exactamente igual que antes de este cambio — no hay Start en ese hardware, así que el
   bloque nuevo queda completamente compilado afuera.

## Riesgos conocidos

- Es el primer cambio de esta serie de mejoras que toca la ISR de audio directamente
  (las anteriores — retrigger en LEDs, waveform — solo leían estado ya existente desde el
  loop de UI). El cambio es pequeño y acotado, pero amerita la misma disciplina de
  verificación en hardware que el resto del proyecto — y en este caso, verificación en
  AMBOS builds (original y GamePi13), ya que se toca código compartido.
