# Select + botón musical → salto directo de modo — Diseño

**Fecha:** 2026-07-16
**Estado:** aprobado por el usuario
**Prerequisito:** Todas las fases + mejoras de bajo/medio riesgo (retrigger en LEDs,
waveform, retrigger exacto) completas y verificadas, rama `port/rp2350-gamepi13`.
**Riesgo:** medio — segunda vez en esta serie que se toca código compartido con el
hardware original (después del retrigger exacto), y además refactoriza (no solo agrega)
un patrón existente de detección de combos de 4 botones.

## Objetivo

Hoy, Select cicla los 9 modos de a uno por presión (`gamepi_selector = (gamepi_selector + 1) % 9`,
instantáneo al presionar). Se agrega: mientras Select está sostenido, presionar un botón
musical (0-7) salta directo a ese modo — Up=0, Down=1, Left=2, Right=3, Y=4, X=5, B=6, A=7,
mismo orden que ya usa la tabla de modos de Function A/B. Un toque simple de Select (sin
combinar con ningún botón musical) sigue ciclando +1 exactamente como hoy.

## No-objetivos

- El modo 8 (Browse SD) no tiene un botón musical propio (son 9 modos para 8 botones) —
  sigue siendo alcanzable solo ciclando con Select.
- No se cambia ningún otro comportamiento de los botones musicales (jump normal,
  retrigger, los 3 combos de 4 botones) fuera de la ventana en que Select está sostenido.
- No se corrige el caso borde de "botón musical ya sostenido antes de presionar Select"
  (ver Riesgos conocidos) — se documenta, no se resuelve en esta fase.

## Hallazgo que amplía el alcance: fragilidad latente en los combos existentes

Los 3 combos de 4 botones ya existentes (clock lock: 1,2,5,6; reset FX: 0,1,6,7;
mute/start-stop heredado: 0,3,4,7 — `main.cpp:1764-1801`) comparten índices entre sí y
cada uno llama `input_button[i].ChangedHigh(true)` de forma independiente, dentro de un
`for (i=0..7) { input_button[i].Read(); ...combos...}` que además re-evalúa los 3 combos
redundantemente 8 veces por tick (inocuo hoy, porque las comprobaciones no dependen de
`i`, pero confuso y frágil). Como `ChangedHigh(true)` consume el flag una sola vez
(`doth/button.h`), agregar una CUARTA consumidora (el gesto nuevo) sobre los mismos 8
índices sin corregir esto arriesga que mi gesto le robe el flanco a un combo existente, o
viceversa, en el raro caso de coincidir en el mismo tick — el mismo patrón de bug ya
encontrado y corregido para Start esta sesión, pero en código heredado del pikocore
original.

**Fix incluido en este diseño**: consolidar la lectura de flancos de los 8 botones en un
array `bool button_rising[NUM_BUTTONS]`, calculado una sola vez por tick (fuera del loop
de `i`, después de que todos los `.Read()` ya corrieron), consumiendo `ChangedHigh(true)`
ahí y solo ahí. Los 3 combos existentes y el gesto nuevo leen de ese array en vez de
consumir el flag cada uno por su cuenta.

## Mecanismo

### 1. Select con doble rol (espeja el patrón ya usado para Start)

Mismo patrón usado para `gamepi_start_used_as_modifier` (un solo `Changed(true)`,
ramificado con `Rising()`/`Falling()` — no dos llamadas separadas a `Changed()`, que fue
exactamente el bug que tuvimos con Start al principio de esta sesión):

```cpp
if (btn_select.Changed(true)) {
  if (btn_select.Rising()) {
    gamepi_select_used_as_modifier = false;
  } else if (btn_select.Falling() && !gamepi_select_used_as_modifier) {
    // ciclado normal +1, comportamiento actual sin cambios
    const uint8_t was = gamepi_selector;
    gamepi_selector = (gamepi_selector + 1) % 9;
    // ... resto de la lógica actual de entrar/salir del modo 8 ...
  }
}
if (btn_select.On() && !gamepi_select_used_as_modifier) {
  for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
    if (button_rising[i]) {
      gamepi_selector = i;
      gamepi_select_used_as_modifier = true;
      input_knob[0].SetBucket(gamepi_selector, 8);
      gamepi_ui_overlay_mode(gamepi_selector);
      break;  // el primer botón presionado durante este sostenido gana
    }
  }
}
```

Nuevo global: `bool gamepi_select_used_as_modifier = false;` bajo `#if PIKO_GAMEPI13`,
junto a `gamepi_start_used_as_modifier`.

### 2. Consolidación de flancos (ver hallazgo arriba)

```cpp
for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
  if (midi_button1 != i && midi_button2 != i) {
    input_button[i].Read();
  }
}
bool button_rising[NUM_BUTTONS];
for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
  button_rising[i] = input_button[i].ChangedHigh(true);
}
// Los 3 combos existentes, reescritos para leer button_rising[...] en vez
// de llamar ChangedHigh(true) cada uno; movidos fuera del loop de arriba.
```

### 3. Pausar el escaneo de jump/retrigger de audio mientras Select está sostenido

En `pwm_interrupt_handler()` (código compartido), las secciones "check button 1"/"check
button 2" (`main.cpp:681-720`) quedan envueltas en `if (!gamepi_paused_for_select)`:

```cpp
#if PIKO_GAMEPI13
    const bool gamepi_paused_for_select = btn_select.On();
#else
    const bool gamepi_paused_for_select = false;
#endif
    if (!gamepi_paused_for_select) {
      // check button 1 (contenido actual sin cambios)
    }
    if (!gamepi_paused_for_select) {
      // check button 2 (contenido actual sin cambios)
    }
```

`btn_select` solo existe bajo `#if PIKO_GAMEPI13` (igual que `btn_start` en el retrigger
exacto), de ahí el guard.

## Manejo de errores

No aplica — no hay entradas externas ni estados inválidos nuevos.

## Riesgos conocidos

- **Caso borde sin corregir**: si un botón musical ya está sostenido (jump continuo)
  antes de presionar Select, el audio queda congelado en ese beat hasta soltar Select (el
  escaneo que detecta la liberación del botón también está pausado). Documentado, no
  resuelto en esta fase — uso poco común (chord de 3+ dedos simultáneos).
- **Segunda vez que se toca código compartido con el build original** — mismo nivel de
  disciplina de verificación que el retrigger exacto: confirmar que `build/pikocore.uf2`
  (flag OFF) da un resultado provablemente idéntico, y que los 3 combos originales siguen
  funcionando exactamente igual tras la consolidación de flancos.
- El refactor de los combos (moverlos fuera del loop de `i`, consolidar el flag) es un
  cambio de comportamiento interno pero no de comportamiento observable — si algo se
  rompe, debería ser evidente en la verificación de regresión de los 3 combos.

## Pruebas

1. **Build**: ambas variantes compilan; `build/pikocore.uf2` (original) provablemente sin
   cambios de contenido (mismo método de verificación A/B ya usado en el retrigger exacto).
2. **Hardware — gesto nuevo**:
   - Sostener Select y presionar cada uno de los 8 botones musicales: salta al modo
     correspondiente (0-7), overlay visible.
   - Soltar Select sin haber tocado ningún botón musical: cicla +1 como siempre.
   - Mientras se sostiene el botón musical usado para saltar, el audio NO reacciona
     (no hay jump/retrigger visible en el waveform ni en las luces).
   - Soltar Select después de usarlo como modificador: no cicla de nuevo.
3. **Hardware — regresión de los 3 combos existentes** (clock lock, reset FX,
   mute/start-stop heredado): cada uno sigue disparando igual que antes de este cambio.
4. **Hardware — regresión general**: jump normal, retrigger (aleatorio y exacto con
   Start), modo Browse SD, waveform, tempo — todo sin cambios.
5. **Regresión en hardware original** (flag OFF, si el usuario tiene acceso): los 3
   combos de 4 botones se comportan exactamente igual que antes de este cambio.
