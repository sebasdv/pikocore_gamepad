# Referencia de interfaz — pikocore en GamePi13

Este documento describe en detalle cómo cada control físico del GamePi13 se traduce a
comportamiento del motor de audio de pikocore, y qué produjo cada decisión de diseño.
Es la referencia técnica completa; para instrucciones rápidas de build/flasheo ver
[README-GAMEPI13.md](README-GAMEPI13.md).

## 1. Mapa físico de controles

| Botón físico | Rol en pikocore | GPIO |
|---|---|---|
| Up | Botón musical 0 | GP15 |
| Down | Botón musical 1 | GP6 |
| Left | Botón musical 2 | GP16 |
| Right | Botón musical 3 | GP13 |
| Y | Botón musical 4 | GP9 |
| X | Botón musical 5 | GP5 |
| B | Botón musical 6 | GP20 |
| A | Botón musical 7 | GP21 |
| Select | Cicla el selector de modo (0–7) | GP19 |
| Start | Mantenido = editar Function B en vez de A | GP26 |
| L | Baja el parámetro activo; mantener repite | GP23 |
| R | Sube el parámetro activo; mantener repite | GP4 |

Fuente de la numeración: [`src/hw_gamepi13.h`](src/hw_gamepi13.h).

## 2. Qué hace cada botón musical individualmente

Esto es lo que el motor original de pikocore hace con los 8 botones — no es específico
del port, pero vale la pena tenerlo documentado porque no es obvio jugando a ciegas:

**Un solo botón musical presionado** → salta ("jump") al slice de compás correspondiente
al índice de ese botón dentro del sample actual (`select_beat = button_on + offset`,
[`src/main.cpp:922`](src/main.cpp:922)). Los 8 botones son, en efecto, 8 posiciones fijas
dentro del loop.

**Dos botones musicales presionados a la vez** → activa un efecto de **retrigger/stutter**
(`btn_retrig`). El **segundo** botón que se presiona (no el primero) elige la subdivisión
del retrigger, de más lento a más granular según el índice del botón:

| 2do botón | Rango de subdivisión (más lento→rápido dentro del rango) |
|---|---|
| Up (0) | el más lento (repeticiones largas) |
| Down (1) | — |
| Left (2) | — |
| Right (3) | — |
| Y (4) | — |
| X (5) | — |
| B (6) | — |
| A (7) | el más rápido (stutter granular) |

(Tabla de multiplicadores exacta en [`src/main.cpp:339-341`](src/main.cpp:339), función
`retrig_len()` — 19 niveles Q8 de 1024/256=4x a 16/256=1/16x de la duración de un compás,
el segundo botón restringe el sorteo aleatorio a una ventana de 2 niveles adyacentes.)

**Tres botones específicos combinados** — tres combos de 4 botones fijos, chequeados
contra flancos de subida en cualquiera de sus 4 botones ([`src/main.cpp:1693-1730`](src/main.cpp:1693)):

| Combo | Efecto |
|---|---|
| Down + Left + X + B | Alterna **clock lock** — congela `select_beat` sincronizado al contador de compás en vez de avanzar libremente |
| Up + Down + B + A | **Reset de FX** — pone en cero filtro, distorsión y las 4 probabilidades (jump/retrig/gate/dirección) |
| Up + Right + Y + A | Alterna **mute / start-stop** de todo el motor (heredado del pikocore original; ver también el botón Start abajo, que hace lo mismo de forma más directa en GamePi13) |

### El botón Start tiene doble rol

El pikocore original no tiene un botón de start/stop dedicado — ni el combo de arriba
ni ningún otro; el hardware de fábrica solo trae 8 botones + 3 potenciómetros y ese
combo de 4 botones es la única forma que existía. En el GamePi13 agregamos un uso más
directo aprovechando que el botón físico dice "Start":

- **Toque simple** (presionar y soltar sin tocar L/R mientras está presionado) →
  alterna mute/start-stop — el mismo efecto que el combo Up+Right+Y+A, en un solo botón.
- **Mantenido + L/R** → sigue funcionando igual que siempre, edita Function B en vez de A.

Un flag (`gamepi_start_used_as_modifier`, [`src/main.cpp`](src/main.cpp)) distingue
ambos casos: se resetea al presionar Start y se marca en cuanto L/R lo usan como
modificador, así soltar Start después de haberlo usado para Function B no dispara el
toggle por accidente.

## 3. El selector de modo y los 8 modos

Select cicla un índice 0–7 (`gamepi_selector`). Ese índice determina qué controla L/R
(Function A) y qué controla Start+L/R (Function B). Los switches reales están en
[`src/main.cpp:1738`](src/main.cpp:1738) (Function A) y
[`src/main.cpp:1833`](src/main.cpp:1833) (Function B):

| Modo | Function A (L/R) | Function B (Start+L/R) |
|---|---|---|
| 0 | Selección de sample | Intensidad del "break" FX |
| 1 | Filtro (LPF) | Timestretch |
| 2 | Noise gate | Probabilidad de gate |
| 3 | Probabilidad de salto (jump) | Probabilidad de retrigger |
| 4 | Probabilidad de túnel (salto entre samples) | Probabilidad de reversa |
| 5 | Grabar secuenciador | Reproducir secuenciador |
| 6 | Guardar en flash | Cargar desde flash |
| 7 | Volumen / distorsión | — |

Cada ajuste de L/R mueve el valor virtual del knob en pasos de `GAMEPI_KNOB_STEP` (164,
~4% de 4095) cada ~100ms mientras se mantiene presionado
([`src/hw_gamepi13.h`](src/hw_gamepi13.h)).

## 4. Qué muestra el LCD

**Dashboard** (siempre visible): BPM + fuente de clock (INT/EXT/MIDI), número y nombre
del sample activo, barra de 8 LEDs virtuales (reemplaza los LED físicos del pikocore
original — se prende con el beat), nombre del modo activo con barras A/B, y una fila de
8 puntos indicando qué modo está seleccionado.

**Overlay temporal**: al presionar Select aparece el nombre del modo nuevo (Function A y
B); al presionar L/R aparece el parámetro activo con su valor en grande y una barra de
progreso. Se desvanece tras dejar de presionar.

Todo el render vive en `src/gamepi13/ui.cpp`, corre en core0 dentro del mismo lazo de
250Hz que escanea los botones, y está limitado a ~25 refrescos de pantalla por segundo
(`flush_allowed()`) para no competir por bus SPI con el audio.

## 5. Cosas descubiertas durante las pruebas en hardware, sin resolver todavía

Vale la pena registrarlas porque no son evidentes mirando el código y afectan directamente
cualquier ajuste fino que se quiera hacer a la sensibilidad de los controles:

- **El comentario `// 250 Hz` en `src/main.cpp` es engañoso.** Ese bloque de control
  corre una vez por cada interrupción de wrap del PWM de audio, que con la configuración
  actual (`sys_clk` 248MHz, `wrap=250`) dispara a ~988kHz — no a 250Hz literal. Todo lo que
  se calibra en "N ticks" asumiendo 250Hz (el repeat de L/R a 25 ticks ≈ "100ms", el TTL
  del overlay a 250 ticks ≈ "1s") probablemente corre mucho más rápido de lo que el
  comentario original sugiere. No confirmado en qué medida esto afecta la sensación real
  de "mantener presionado" en la práctica — Fase 1 se sintió bien al usuario, pero no se
  midió con precisión.
- El TTL del overlay (`OVERLAY_TTL_TICKS = 250`) probablemente se desvanece mucho antes
  de lo previsto (¿instantáneo en vez de ~1s?) por la misma razón. Si en el uso diario el
  overlay parece cerrarse "de golpe" apenas soltás el botón, esto lo explica.
- El throttle de refresco de LCD (~25Hz) que se agregó para resolver la degradación de
  audio funciona por tiempo real (`time_us_64()`), no por ticks — así que no hereda este
  problema, pero es la única parte de la Fase 2 que no lo hereda.

## 6. Ideas para mejoras futuras

Con la Fase 2 (LCD) funcionando, estas son líneas de trabajo que quedaron abiertas o que
se volvieron obvias durante las pruebas:

- **Calibrar el tick real del lazo de control** (medir con un timer real cuántas veces
  por segundo corre ese bloque) y reexpresar `GAMEPI_REPEAT_TICKS`/`OVERLAY_TTL_TICKS` en
  microsegundos reales en vez de "ticks", para que el timing de repeat/overlay sea
  predecible independientemente de la frecuencia de PWM configurada.
- **Waveform con playhead en el dashboard** (ya estaba en el spec original como "Fase 2.1",
  fuera de alcance): mostrar la forma de onda del sample activo con un cursor de
  reproducción — requiere decimar el audio desde flash, candidato a render por DMA en vez
  de SPI bloqueante.
- **Exponer el retrigger de forma menos aleatoria**: hoy el segundo botón sortea DENTRO
  de una ventana de 2 subdivisiones — se podría, por ejemplo, usar Start+segundo-botón
  para fijar una subdivisión EXACTA en vez de aleatoria, dando más control predecible en
  vivo.
- **Indicador visual de qué botón(es) están generando el retrigger actual**: ahora mismo
  el LCD no distingue "estoy en jump simple" de "estoy en retrigger stutter" — se podría
  usar el bloque de iconos de estado (pendiente, ver README) para esto.
- **IMU (ICM20948, I2C GP2/3)** como modulador de FX — mencionado en el plan original,
  nunca implementado; podría mapear inclinación/movimiento a algún parámetro en vivo.
- **Carga de muestras desde microSD** del RP2350-PiZero en vez de (o además de) USB —
  el board trae el conector, el puerto no se usa todavía.
