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
| Select | Cicla el selector de modo (0–8) | GP19 |
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

## 3. El selector de modo y los 9 modos

Select cicla un índice 0–8 (`gamepi_selector`). Los índices 0–7 determinan qué controla
L/R (Function A) y qué controla Start+L/R (Function B); el índice 8 es un modo aparte
(Browse SD, ver sección 3.1). Los switches reales están en
[`src/main.cpp`](src/main.cpp) (buscar `gamepi_selector < 8` para Function A/B, y el
`switch (gamepi_sd_state)` para el modo 8):

| Modo | Function A (L/R) | Function B (Start+L/R) |
|---|---|---|
| 0 | Selección de sample | Intensidad del "break" FX |
| 1 | Filtro (LPF) | Timestretch |
| 2 | Noise gate | Probabilidad de gate |
| 3 | Probabilidad de salto (jump) | Probabilidad de retrigger |
| 4 | Probabilidad de túnel (salto entre samples) | Probabilidad de reversa |
| 5 | Grabar secuenciador | Reproducir secuenciador |
| 6 | Guardar en flash | Cargar desde flash |
| 7 | Volumen / distorsión | **Tempo (BPM)** |
| 8 | Browse SD — ver sección 3.1 | (no aplica) |

Cada ajuste de L/R mueve el valor virtual del knob en pasos de `GAMEPI_KNOB_STEP` (164,
~4% de 4095) cada ~100ms mientras se mantiene presionado
([`src/hw_gamepi13.h`](src/hw_gamepi13.h)) — **excepto Tempo** (modo 7, Function B), que
tiene su propio ajuste directo sobre el BPM en vez de derivarlo del knob crudo, porque el
paso genérico traducido a BPM saltaba en números muy grandes (descubierto en pruebas de
hardware de la Fase 3): toque simple = ±1 BPM, mantener ≥1s = ±5 BPM por paso, mantener
≥3s = ±20 BPM por paso. Rango 20–360 BPM, cualquier valor entero (antes solo múltiplos
de 5). El overlay de Tempo muestra el BPM real ("142 BPM"), no un porcentaje.

### 3.1 Modo 8: Browse SD

Ver la sección [microSD del README](README-GAMEPI13.md#microsd) para el uso básico.
Detalles de la mecánica de botones (`src/main.cpp`, `GamepiSdState`):

- Al entrar (Select llega a 8): se monta la tarjeta y se lista el directorio raíz de
  forma asíncrona en core1 (mientras tanto el LCD muestra "Leyendo tarjeta...").
- **L** cicla la lista un archivo por toque, en una sola dirección (siempre llega a
  todos los archivos igual). **R** está dedicado exclusivamente a mantener-para-cargar
  — no navega. (En una iteración anterior R también navegaba con un toque, pero toques
  rápidos y repetidos podían dejar el botón leyendo "presionado" de forma continua entre
  toques —rebote/debounce—, acumulando tiempo real de "mantenido" hasta cruzar el umbral
  de 1s sin que el usuario realmente lo hubiera sostenido nunca: una carga no deseada.
  Separar navegar (L) de confirmar (R) elimina esa clase de bug por completo.)
- El archivo resaltado que coincide con el banco actualmente cargado se muestra en
  **verde** con el texto "Cargado (banco activo)"; el nombre del banco cargado también
  queda visible de forma persistente en el dashboard normal, junto al nombre del sample
  (`sample.wav | banco.pikobank`).
- Las pantallas de este modo (listado, navegación, progreso, carga, resultado) son
  overlays **persistentes** (no se cierran solas por tiempo) mientras estés en el modo
  8 — se cierran explícitamente al salir con Select (`gamepi_ui_sd_close()`). Esto es
  distinto del resto de los overlays (Select/L/R en los otros modos), que sí se
  desvanecen solos tras ~1s real.
- No hay detección de tarjeta insertada/retirada en caliente: si sacás o ponés la
  tarjeta con el dispositivo prendido, hace falta reiniciarlo para que se reconozca de
  nuevo. Sin tarjeta, entrar al modo 8 tarda ~5 segundos en mostrar "Sin tarjeta o sin
  archivos" — es el tiempo que tarda el protocolo SPI en agotar sus reintentos sin
  respuesta de la tarjeta; no hay un pin de Card Detect dedicado en este socket.

## 4. Qué muestra el LCD

**Dashboard** (siempre visible): BPM + fuente de clock (INT/EXT/MIDI), número y nombre
del sample activo (+ nombre del banco `.pikobank` cargado desde SD, si alguno), barra de
8 LEDs virtuales (reemplaza los LED físicos del pikocore original — se prende con el
beat), nombre del modo activo con barras A/B, y una fila de 8 puntos indicando qué modo
está seleccionado (el modo 8 no ilumina ninguno de los 8 puntos, ya que no tiene uno
propio; el nombre del modo pasa a decir "SD").

**Overlay temporal**: al presionar Select aparece el nombre del modo nuevo (Function A y
B); al presionar L/R aparece el parámetro activo con su valor en grande y una barra de
progreso. Se desvanece ~1 segundo real después (ver sección 5 sobre la calibración de
este tiempo). Las pantallas del modo 8 (Browse SD) son la excepción: son persistentes,
ver sección 3.1.

Todo el render vive en `src/gamepi13/ui.cpp`, corre en core0 dentro del mismo lazo de
control que escanea los botones (ver sección 5 sobre su frecuencia real), y está
limitado a ~25 refrescos de pantalla por segundo (`flush_allowed()`) para no competir
por bus SPI con el audio.

## 5. Cosas descubiertas durante las pruebas en hardware

Vale la pena registrarlas porque no son evidentes mirando el código y afectan directamente
cualquier ajuste fino que se quiera hacer a la sensibilidad de los controles:

- **RESUELTO (Fase 3) — el comentario `// 250 Hz` en `src/main.cpp` era engañoso, y
  afectaba de verdad al modo Browse SD.** Ese bloque de control corre una vez por cada
  interrupción de wrap del PWM de audio (`sys_clk` 248MHz, `wrap=250` → ~988kHz),
  dividido por el `% 16 == 0` que lo gatea → **~61.7 kHz reales, no 250Hz** (medido, no
  estimado). Todo lo calibrado en "N ticks" asumiendo 250Hz corría ~247 veces más rápido
  de lo previsto: el TTL del overlay (`OVERLAY_TTL_TICKS=250` ≈ "1s") se desvanecía en
  ~4ms real, el resultado "Listo"/"Error" del modo SD (`GAMEPI_SD_RESULT_TICKS=100` ≈
  "0.4s") en ~1.6ms, y el umbral de "mantener R para cargar" (`GAMEPI_REPEAT_TICKS*10`
  ≈ "1s") en ~4ms — esto último permitía que un toque breve al navegar disparara una
  carga a flash sin que el usuario realmente sostuviera nada. Fix: los 4 temporizadores
  se migraron de contar ticks a medir tiempo real con `time_us_64()` (el mismo patrón
  que ya usaba con éxito `flush_allowed()` y el rescan de arranque), y las pantallas del
  modo Browse SD pasaron a ser overlays *persistentes* (no expiran por tiempo, se cierran
  explícitamente al salir del modo) en vez de depender de un TTL. Ver
  `gamepi_ui_sd_close()` (`src/gamepi13/ui.cpp`) y los `#define GAMEPI_*_US` en
  `src/hw_gamepi13.h`/`src/main.cpp`.
- **RESUELTO (Fase 3) — Function B del modo Volumen (7) ya controlaba Tempo/BPM, pero
  la pantalla mostraba "-".** El motor de audio compartido (heredado del pikocore
  original) siempre mapeó `selector_knob==7` + Function B a BPM
  (`src/main.cpp`, `case 7: // tempo`); solo la tabla de etiquetas de la UI
  (`kModeB[7]` en `ui.cpp`) nunca se actualizó para decirlo. Corregido, y de paso se le
  dio a Tempo su propio ajuste directo con aceleración por tiempo de mantenido (ver
  sección 3), en vez de heredar el paso genérico de knob que traducido a BPM saltaba en
  números muy grandes.
- **Limitación conocida, no un bug — sin detección de SD en caliente.** El socket
  integrado no tiene (o no se cableó) un pin de Card Detect; sin tarjeta, entrar al modo
  Browse SD tarda ~5s en reportar "sin archivos" (es el tiempo que tarda el protocolo SPI
  en agotar sus reintentos de comando sin respuesta — `sd_command=2000ms × 3 reintentos`
  en la librería vendorizada, `RP2350-PiZero/C/03-MicroSD/src/src/sd_timeouts.c`). Sacar
  o poner la tarjeta con el dispositivo prendido no se detecta: hace falta reiniciar.
  Confirmado que ni el propio ejemplo de referencia de la librería para esta placa usa
  Card Detect (`use_card_detect = false` en su `hw_config.c`), así que no es una
  configuración nuestra incompleta — es una limitación real del socket.
- **RESUELTO — indicador visual de qué botón(es) están generando el retrigger actual.**
  Los 2 LEDs virtuales correspondientes a `button_on`/`button_on2` se pintan en cian
  sólido (en vez del naranja normal por amplitud) mientras `btn_retrig` esté activo por
  la combinación de 2 botones (`src/gamepi13/ui.cpp`, `draw_leds()`;
  `src/main.cpp`, campo `retrig_leds_mask` de `GamepiUiState`). Nota de alcance: solo
  cubre el retrigger disparado por combo de 2 botones — el retrigger que a veces se
  dispara por probabilidad (`probability_retrig`, sin un segundo botón presionado) no
  tiene un botón "segundo" que resaltar, así que en ese caso la máscara puede quedar en 0
  o con un solo LED aunque el audio esté igual haciendo stutter.
- **RESUELTO — lecturas XIP fantasma en el arranque.** En esta placa, las lecturas de
  flash vía XIP durante los primeros instantes después de `set_sys_clock_khz(248000)`
  devuelven datos corruptos de forma determinista (el header del banco de audio se leía
  con campos en cero, haciendo "desaparecer" las muestras en cada arranque — aunque
  nunca dejaron de estar físicamente en flash). Milisegundos después, la misma dirección
  se lee bien. La cura: un reintento de rescan en el lazo de control
  ([`src/main.cpp`](src/main.cpp), busca `gamepi_next_rescan_us`) que sana el banco en el
  primer pase — confirmado en hardware: el dispositivo arranca y suena solo,
  inmediatamente. En el camino se descartaron (y quedaron como mejoras igualmente
  válidas) la sincronización multicore de escrituras a flash y el divisor QSPI a 4.

## 6. Ideas para mejoras futuras

Con las Fases 2 (LCD) y 3 (microSD) funcionando, estas son líneas de trabajo que
quedaron abiertas o se volvieron obvias durante las pruebas:

- **Detección de SD en caliente**: hoy hace falta reiniciar el dispositivo después de
  sacar/poner la tarjeta (ver sección 5). El socket no expone Card Detect, así que esto
  requeriría o bien un GPIO físico adicional cableado a mano al socket, o pulir el
  driver vendorizado para forzar una re-inicialización completa en cada entrada al modo
  8 en vez de confiar en su caché de estado interno.
- **Indicador de "banco actualmente cargado" más visible**: ya se agregó uno básico en
  la Fase 3 (nombre combinado en el dashboard + resaltado verde en la lista), pero podría
  sobrevivir a un reinicio (hoy es solo de sesión, se pierde al apagar) si se guardara el
  nombre del archivo en flash junto al resto de `save_data`.
- **Waveform con playhead en el dashboard** (ya estaba en el spec original como "Fase 2.1",
  fuera de alcance): mostrar la forma de onda del sample activo con un cursor de
  reproducción — requiere decimar el audio desde flash, candidato a render por DMA en vez
  de SPI bloqueante.
- **Exponer el retrigger de forma menos aleatoria**: hoy el segundo botón sortea DENTRO
  de una ventana de 2 subdivisiones — se podría, por ejemplo, usar Start+segundo-botón
  para fijar una subdivisión EXACTA en vez de aleatoria, dando más control predecible en
  vivo.
- **IMU (ICM20948, I2C GP2/3)** como modulador de FX — mencionado en el plan original,
  nunca implementado; podría mapear inclinación/movimiento a algún parámetro en vivo.
