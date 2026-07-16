# Waveform con playhead fusionada en la zona de LEDs — Diseño

**Fecha:** 2026-07-16
**Estado:** aprobado por el usuario
**Prerequisito:** Fases 1-3 completas y verificadas + indicador de retrigger en LEDs (commits `e6942f1`/`b058d92`), rama `port/rp2350-gamepi13`.
**Riesgo:** medio-bajo (reclasificado — ver "Estudio previo" abajo; el "alto" original estaba sobreestimado).

## Objetivo

Mostrar la forma de onda del sample activo con un cursor de reproducción (playhead) en el
dashboard, fusionada con la franja de 8 LEDs virtuales — los 8 LEDs/botones SON los 8
slices del loop, así que una sola zona puede mostrar waveform + slice activo + retrigger
+ playhead sin sacrificar nada de lo que hoy existe.

## Estudio previo (hechos verificados en código, 2026-07-16)

- **Audio**: PCM 8-bit sin signo (128 = centro/silencio), mono, 24 kHz
  (`PikoAudioBank.h`), leído por XIP memory-mapped — `piko_raw_val(sample, frame)` es una
  lectura de memoria plana a `0x10000000 + offset`. Lecturas XIP concurrentes son seguras
  (la ISR ya lee flash 24k veces/s); solo las escrituras necesitan lockout.
- **Posición de reproducción**: `phase_sample[phase_head]` (frame actual, mantenido por la
  ISR), ya sincronizado con timestretch vía `sync_phase_sample_from_timestretch()`
  (`main.cpp`). Fracción = `phase_sample / raw_len(sample)`.
- **Costos**: caché decimado 240 col × min/max = 480 bytes RAM (trivial, ~200KB libres);
  decimación con 32 subsamples/col = 7.680 lecturas XIP ≈ 1-4 ms una vez por cambio de
  sample (la ISR de audio preempta al loop de control — el audio no se entera); flush SPI
  de la zona ≈ 17 ms a 10MHz — igual al costo actual de flushear la zona de LEDs.
- **DMA innecesario**: la sugerencia original del spec de Fase 2 asumía que la decimación
  sería cara; con XIP mapeado no lo es.
- **Riesgo real nuevo**: inanición de widgets — `gamepi_ui_tick()` flushea UN widget por
  slot de 25Hz eligiendo el de menor índice; un playhead siempre-sucio mataría de hambre a
  los índices mayores. Mitigado abajo.

## No-objetivos

- No se toca la lógica de audio, retrigger, timestretch ni slices — solo se lee su estado.
- No se agrega DMA ni render asíncrono.
- No se rediseña el resto del dashboard (el usuario planea rehacer la interfaz con Lopaka
  más adelante; esta zona es el único cambio visual).

## Diseño visual (zona y=52..96, 240×44px, ex-LEDs)

1. **Waveform de fondo**: 240 columnas min/max del sample activo en `COL_ORANGE_DIM`.
   Cada columna = 1/240 del sample, centrada verticalmente (128 = línea media).
2. **Slice activo iluminado**: el segmento correspondiente a `select_beat` (el slice que
   suena) se dibuja en `COL_ORANGE` brillante — hereda la semántica del "LED prendido",
   usando la misma amplitud de `ledarray` que hoy decide brillante/tenue.
3. **Retrigger en cian**: los slices con bit en `retrig_leds_mask` se tiñen `COL_CYAN`
   (preserva el indicador recién agregado).
4. **Playhead**: línea vertical blanca (`COL_WHITE`) de 1px en la columna
   `phase_sample * 240 / raw_len(sample)`.
5. **Separadores de slice**: 7 marcas verticales tenues (`COL_DARK` o un gris) en los
   límites de los 8 slices.

## Arquitectura

### Caché de decimación (en `ui.cpp`)

- `static uint8_t wave_min[240], wave_max[240];` (480 bytes) + un identificador del sample
  cacheado (índice + frame_count como generación, para detectar recarga de banco).
- Recalculo **bloqueante** al detectar cambio de sample: ~32 subsamples equiespaciados por
  columna, min/max sobre `piko_raw_val()`. 1-4 ms una sola vez; sin async.
- Guard: si `piko_audio_bank_mutating()` es verdadero, se pospone el recálculo al próximo
  tick (mismo patrón que el rescan de arranque).
- Sin samples (`raw_len == 1` o `sample_count == 0`): línea central plana, sin playhead.

### Datos nuevos en `GamepiUiState` (`ui.h`)

- `uint8_t wave_playhead_col;` — columna 0-239 del playhead (calculada en `main.cpp` desde
  `phase_sample`/`raw_len`; 255 = sin playhead).
- Se reusan campos existentes: `sample_idx` (para detectar cambio de sample),
  `sample_count`, `leds[8]` (amplitud por slice), `retrig_leds_mask`, y se agrega
  `uint16_t wave_beat;` si hace falta `select_beat` explícito — a decidir en el plan si
  `leds[]` ya codifica suficiente el slice activo.

### Anti-inanición

- La zona waveform toma el **índice de widget más alto** (última prioridad en el for de
  `dirty[]`).
- El redibujo disparado solo por movimiento de playhead se auto-throttlea a ~100 ms reales
  (`time_us_64()`, patrón ya establecido en `flush_allowed()`/repeat/overlay).
- Cambios de slice activo / retrig / amplitud marcan sucio sin throttle extra (ya venían
  haciéndolo a través del diffing de `leds[]`/máscara).

## Manejo de errores

| Caso | Comportamiento |
|---|---|
| Sin samples | Línea central plana, sin playhead ni separadores |
| Banco mutando (carga SD/USB) | Se pospone el recálculo del caché; la zona muestra lo último dibujado |
| Cambio de sample a mitad de decimación | No aplica — el recálculo es bloqueante y atómico respecto al loop de control |

## Pruebas

1. **Builds**: ambas variantes compilan; la original (flag OFF) byte-idéntica.
2. **Hardware**:
   - Con un banco cargado: la waveform del sample activo aparece; cambiar de sample la
     actualiza (con una pausa imperceptible).
   - El playhead avanza de izquierda a derecha al ritmo del loop; saltar de slice con un
     botón mueve el playhead a esa región.
   - El slice activo se ilumina; retrigger tiñe de cian los 2 slices; los separadores se
     ven.
   - Audio sin cortes ni glitches durante cambios de sample (validación del costo de
     decimación) y con el dashboard refrescándose.
   - Regresión: modo Browse SD, overlays, tempo — igual que antes.

## Riesgos conocidos

- El flush de la zona sigue costando ~17 ms (igual que hoy); si en hardware se percibe
  lentitud en otros widgets, ajustar el throttle del playhead (100→200 ms) es el primer
  dial.
- Punto de retorno: el commit anterior al primer task de esta feature.
