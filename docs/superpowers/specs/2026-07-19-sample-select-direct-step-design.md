# Selección de sample: ajuste directo ±1 (toque = un sample) — Diseño

**Fecha:** 2026-07-19
**Estado:** aprobado por el usuario
**Prerequisito:** Barra de sample segmentada (sub-proyecto 5) completa y verificada
en hardware. Rama `port/rp2350-gamepi13`.
**Riesgo:** bajo — mismo patrón ya usado con éxito para Tempo, acotado a un solo
combo modo+función.

## Objetivo

En modo 0, Function A (selección de sample), un solo toque de L/R casi nunca cambia
de sample: el ajuste hoy pasa por el mapeo genérico de posición del knob
(`sample_change = knob.Value() * sample_count / 4095`), con un paso fijo de
`GAMEPI_KNOB_STEP` (164 de 4095, ~4%) por toque/repetición. Para bancos con pocas
muestras (ej. 8), cada "casillero" de sample ocupa ~512 unidades — mucho más que
164 — así que un solo toque casi nunca alcanza a cruzar al siguiente. Se agrega un
ajuste directo (±1 sample por toque/repetición, sin pasar por la posición del knob),
mismo patrón que ya resolvió este problema para Tempo (modo 7, Function B).

## No-objetivos

- No se toca Function B del modo 0 (intensidad de break fx) — sigue con el mapeo
  genérico del knob, es un parámetro continuo, no una selección discreta.
- No se agrega aceleración por tiempo sostenido (como Tempo) — el usuario confirmó
  que un paso fijo de ±1 por repetición (~100ms, sostenido) alcanza para bancos de
  hasta 128 samples (~13s para recorrer el extremo completo).
- No hace wrap-around — al llegar al último/primer sample, seguir presionando no
  hace nada más (clamp), coincidiendo con el estilo lineal de la barra segmentada.
- No se toca `src/gamepi13/ui.cpp` — la barra segmentada ya lee `sample_idx`/
  `sample_count` (no la posición cruda del knob), así que no necesita ningún cambio.
- No se toca el `case 0: // sample` viejo (lee la posición cruda del knob) — queda
  intacto pero inalcanzable en la práctica en este camino, mismo patrón que el
  `case 7: // tempo` viejo que dejó Tempo.
- No se cambia el timing de cuándo el cambio de sample realmente suena (eso sigue
  sincronizado al próximo compás vía `sample_set = sample_change % sample_count`,
  lógica preexistente y sin relación con este fix).

## Hallazgos de la investigación (verificados en código, no re-descubrir)

- `GAMEPI_KNOB_STEP` (164) y `GAMEPI_REPEAT_US` (100ms) — mismo paso/cadencia que
  usa cualquier ajuste genérico de knob, `src/hw_gamepi13.h`.
- Tempo ya resolvió exactamente este problema con un camino de ajuste directo:
  `is_tempo = (gamepi_selector == 7 && active_knob == 2)`, chequeado en las ramas de
  `btn_l.On()`/`btn_r.On()` (`src/main.cpp`, ~líneas 1978-2024), que evita
  `input_knob[active_knob].Adjust(...)` por completo y en su lugar llama
  `param_set_bpm(...)` directamente.
- `active_knob = btn_start.On() ? 2 : 1;` — Function A es siempre `active_knob==1`
  (Start no sostenido), Function B siempre `active_knob==2` (Start sostenido). Esto
  ya distingue automáticamente Function A (a cambiar) de Function B (sin cambios).
- `sample_change` (global, `uint16_t`) es la variable que ya alimenta el pipeline de
  cambio de sample (`sample_set = sample_change % sample_count` en otro punto del
  código, sincronizado al compás) — el camino directo debe escribir ahí, no en
  `input_knob[1]`.
- La barra segmentada (`draw_sample_bar()`, `src/gamepi13/ui.cpp`) ya lee
  `s.sample_idx`/`s.sample_count` (derivados de `sample_set`, no del knob crudo) —
  confirmado que no depende de `input_knob[1].Value()` en absoluto para el modo 0,
  así que evitar `Adjust()` en este camino no le afecta.

## Mecanismo

Se agrega una condición nueva junto a `is_tempo`:

```cpp
const bool is_tempo = (gamepi_selector == 7 && active_knob == 2);
const bool is_sample_select = (gamepi_selector == 0 && active_knob == 1);
```

En la rama de `btn_l.On()` (decrementar), se agrega un `else if` entre el camino de
Tempo y el camino genérico:

```cpp
if (is_tempo) {
  // ... sin cambios ...
} else if (is_sample_select) {
  const uint16_t sample_count = (uint16_t)piko_audio_sample_count();
  if (sample_count > 0 && sample_change > 0) {
    sample_change--;
    save_data[SAVE_SAMPLE] = sample_change;
  }
} else {
  input_knob[active_knob].Adjust(-GAMEPI_KNOB_STEP);
  if (active_knob == 2) gamepi_start_used_as_modifier = true;
}
```

Mismo patrón, espejado, en la rama de `btn_r.On()` (incrementar, clamp en
`sample_count - 1`):

```cpp
if (is_tempo) {
  // ... sin cambios ...
} else if (is_sample_select) {
  const uint16_t sample_count = (uint16_t)piko_audio_sample_count();
  if (sample_count > 0 && sample_change < sample_count - 1) {
    sample_change++;
    save_data[SAVE_SAMPLE] = sample_change;
  }
} else {
  input_knob[active_knob].Adjust(GAMEPI_KNOB_STEP);
  if (active_knob == 2) gamepi_start_used_as_modifier = true;
}
```

`gamepi_start_used_as_modifier` no se toca en la rama nueva — solo es relevante para
Function B (`active_knob==2`, Start sostenido), y `is_sample_select` es siempre
Function A (`active_knob==1`).

## Arquitectura

Sin cambios de arquitectura — dos `else if` nuevos dentro de un bloque ya existente
en `src/main.cpp`, mismo patrón que Tempo. No se toca `ui.cpp`, `ui.h`, ni ningún
otro archivo.

## Manejo de errores

- `sample_count == 0` (banco vacío): el `if (sample_count > 0 && ...)` evita
  cualquier decremento/incremento o escritura a `save_data`.
- Clamp en ambos extremos (`sample_change > 0` para decrementar,
  `sample_change < sample_count - 1` para incrementar) — sin wrap-around, según lo
  acordado.

## Pruebas

1. Build `build-gamepi`: sin errores.
2. Hardware: en modo 0, Function A, confirmar que un solo toque de L o R cambia
   exactamente un sample (visible en el nombre de sample y en el segmento resaltado
   de la barra, una vez que pase el próximo compás). Confirmar que mantener
   presionado sigue moviendo de a uno cada ~100ms (sin acelerar). Confirmar que al
   llegar al primer/último sample, seguir presionando no hace nada (no da la
   vuelta). Confirmar que Function B del modo 0 (intensidad de break fx) sigue
   funcionando igual que antes (sin cambios).
3. Regresión: Tempo (modo 7) y el resto de los modos sin cambios.

## Riesgos conocidos

Ninguno relevante — cambio acotado a un solo combo modo+función, mismo patrón ya
probado en hardware para Tempo.
