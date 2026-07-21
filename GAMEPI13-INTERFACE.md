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

**Mantener Start** en el instante de armar el combo de 2 botones fija la subdivisión a un
valor exacto (el punto medio de esa misma ventana) en vez de sortearla — da control
predecible en vivo. Solo afecta la subdivisión: repeticiones, pitch, filtro y reducción de
volumen del efecto siguen sorteando igual, con o sin Start. Funciona sin importar el orden
en que se presionen los 3 botones (los 2 musicales y Start) — el flag que evita que soltar
Start dispare el toggle de mute/start-stop se marca de forma continua mientras el
retrigger esté activo, no solo en el instante del disparo
([`src/main.cpp`](src/main.cpp), busca `kExactRetrigSel`).

| 2do botón | Nivel exacto con Start |
|---|---|
| Up (0) | 1 |
| Down (1) | 3 |
| Left (2) | 5 |
| Right (3) | 7 |
| Y (4) | 9 |
| X (5) | 11 |
| B (6) | 13 |
| A (7) | 15 |

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

> **APARCADO desde 2026-07-20 — el modo 8 (Browse SD) está detrás del flag
> `PIKO_GAMEPI13_SD`, apagado por defecto.** Con el flag en OFF el selector cicla
> **0–7** (8 modos) y el modo 8 es inalcanzable; la fila muestra 8 íconos, no 9.
> Decisión de producto para enfocar el esfuerzo en la experiencia de uso, no un
> defecto sin resolver: los dos bugs reales de SD (inanición del redibujo y el
> baudrate compartido de spi1) **están corregidos y verificados**. Reactivar con
> `-DPIKO_GAMEPI13_SD=ON`. Cargar samples por USB (.pikobank) no se ve afectado.
> Todo lo que sigue sobre el modo 8 describe el comportamiento con el flag en ON.

Select cicla un índice 0–8 (`gamepi_selector`). Los índices 0–7 determinan qué controla
L/R (Function A) y qué controla Start+L/R (Function B); el índice 8 es un modo aparte
(Browse SD, ver sección 3.1). Los switches reales están en
[`src/main.cpp`](src/main.cpp) (buscar `gamepi_selector < 8` para Function A/B, y el
`switch (gamepi_sd_state)` para el modo 8):

### Select también tiene doble rol

Igual que Start (sección 2): un **toque simple** de Select (presionar y soltar sin
combinar con otro botón) cicla +1 como siempre. **Mantener Select y presionar un botón
musical** salta directo a ese modo, sin tener que cicular uno por uno:

| Botón musical | Modo directo |
|---|---|
| Up | 0 |
| Down | 1 |
| Left | 2 |
| Right | 3 |
| Y | 4 |
| X | 5 |
| B | 6 |
| A | 7 |

El modo 8 (Browse SD) no tiene un botón musical propio (son 9 modos para 8 botones) —
sigue siendo alcanzable solo ciclando. Un flag (`gamepi_select_used_as_modifier`,
[`src/main.cpp`](src/main.cpp)) distingue ambos casos, mismo patrón que
`gamepi_start_used_as_modifier`. Mientras Select está sostenido, el motor de audio
tampoco reacciona al botón musical usado para saltar (ni jump ni retrigger) — ver
sección 5 para un bug real que esto mismo destapó durante las pruebas.

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

Las barras de Function A/B tuvieron un color propio por modo durante un tiempo; se
descartó al pasar el dashboard a monocromático (sección 4). Hoy todas son blancas. Las
tablas `kModeColorA/B` siguen en `ui.cpp` sin uso, por si alguna vez se quiere volver.

Cada ajuste de L/R mueve el valor virtual del knob en pasos de `GAMEPI_KNOB_STEP` (164,
~4% de 4095) cada ~100ms mientras se mantiene presionado
([`src/hw_gamepi13.h`](src/hw_gamepi13.h)) — **excepto Tempo** (modo 7, Function B) y
**Selección de sample** (modo 0, Function A), que tienen su propio ajuste directo en
vez de derivarlo del knob crudo. Tempo: el paso genérico traducido a BPM saltaba en
números muy grandes (descubierto en pruebas de hardware de la Fase 3): toque simple =
±1 BPM, mantener ≥1s = ±5 BPM por paso, mantener ≥3s = ±20 BPM por paso. Rango
20–360 BPM, cualquier valor entero (antes solo múltiplos de 5). Selección de sample:
un solo toque casi nunca cambiaba de sample en bancos con pocas muestras, porque el
paso genérico (164 de 4095) era mucho más chico que el "casillero" de cada sample —
ahora cada toque o repetición mueve exactamente ±1 sample, sin acelerar, con clamp en
los extremos (no da la vuelta). El segundo paso de una tanda espera 350ms en vez de
los 100ms normales (`GAMEPI_FIRST_REPEAT_US`), para que un toque humano real
(150-300ms de presionar a soltar) no dispare un cambio de más — descubierto en
pruebas de hardware: sin ese retraso, un toque "rápido" cambiaba de sample al
presionar y otra vez al soltar.

Ese retraso aplica a **todos** los parámetros de L/R, no sólo a la selección de
sample. Al principio era específico de sample, que es donde el problema se notaba
primero; con las barras segmentadas (sección 4) el doble-paso quedó visible en
todos los modos — un toque avanzaba dos bloques — y en tempo daba ±2 BPM en vez
de ±1. Generalizarlo arregló los tres casos de una vez.

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
  8 — se cierran explícitamente al salir con Select (`gamepi_ui_sd_close()`). Es el
  único overlay que queda en el dashboard (el resto se quitó, ver sección 4).
- No hay detección de tarjeta insertada/retirada en caliente: si sacás o ponés la
  tarjeta con el dispositivo prendido, hace falta reiniciarlo para que se reconozca de
  nuevo. Sin tarjeta, entrar al modo 8 tarda ~5 segundos en mostrar "Sin tarjeta o sin
  archivos" — es el tiempo que tarda el protocolo SPI en agotar sus reintentos sin
  respuesta de la tarjeta; no hay un pin de Card Detect dedicado en este socket.

## 4. Qué muestra el LCD

### Lenguaje visual (versión final)

Tres reglas gobiernan todo el dashboard:

1. **Monocromático.** Nada de color: blanco / grises / negro. El color por modo que hubo
   antes se descartó — el contraste (blanco = activo, gris = inactivo) comunica mejor y
   se lee más rápido en un panel chico. Las únicas "escalas" son grises.
2. **Retícula vertical de 20px.** 20px es la unidad base (altura de un glifo condensado,
   de una barra, de un cuadrado de modo). Todo mide 1U salvo la waveform, que es el
   elemento héroe a 2U=40px (el máximo). Ritmo: 8px entre bloques, 2px dentro de un par
   label+barra, 8px de margen arriba/abajo. Ver el mapa exacto en `kRect[]` de `ui.cpp`.
3. **Dos rieles.** Todo lo alineado a la izquierda arranca en **x0** (el mismo borde donde
   arranca la waveform); todo lo alineado a la derecha termina en **x237** (borde del
   ícono stop). Nada flota en el medio.

**Dashboard** (siempre visible, assets diseñados en Lopaka — `src/gamepi13/ui_bitmaps.h`):
BPM con dígitos condensados propios (proporcionales: 12px, salvo `1` y `/` a 9px) + ícono
de fuente de clock (INT/EXT/MIDI, los tres como gráfico de 20px) + par de íconos
play/stop de 20x20 (el activo en blanco, el otro en gris); nombre del sample en Font20
blanco (máx. 10 chars + "...", recortado dinámicamente para no pisar el contador) +
índice/total con los mismos dígitos condensados (`NN/NN`); **zona de waveform** (ver
abajo); etiquetas de Function A/B como gráfico para los 8 modos, cada una sobre su barra;
y una fila de **cuadrados sólidos de 20x20, uno por modo** — gris el inactivo, blanco el
seleccionado. Los cuadrados se distribuyen centrando cada uno en un slot de
`240/n_modos` px, así el bloque queda simétrico sea cual sea el número de modos
(reemplazan a los íconos de modo dibujados que había antes). Los marcos que Lopaka
mostraba alrededor del nombre de sample y de la waveform eran solo guías de layout, no
assets para dibujarse en tiempo real -- no se renderizan.

**Zona de waveform** (`src/gamepi13/ui.cpp`, `draw_wave()`): muestra la forma de onda del
sample que está **sonando** (`sample` en `main.cpp` — con el FX de túnel activo, puede
diferir del sample *seleccionado* por compás; la waveform sigue al que suena, así que con
túnel activo se VE saltar de sample en sample). 7 líneas tenues dividen la franja en 8
slices (los 8 botones musicales son, literalmente, esos 8 slices). Al ser monocromática,
usa **tres niveles de gris** en vez de los colores que tenía antes: fondo gris tenue
(#404040, la forma de onda siempre visible), slice sonando en gris medio (#808080,
hereda la amplitud que antes prendía el LED físico equivalente), y **retrigger en blanco**
sobre los 2 slices involucrados — el indicador de stutter "gana" y es el más brillante,
que es exactamente lo que hay que ver de un vistazo. Una línea blanca vertical (el
**playhead**) recorre la franja al ritmo de la reproducción.

La waveform es el único elemento que ocupa el ancho completo (x0-x239): los 8 slices son
exactamente 30 columnas cada uno (8×30=240), así que meterla en un riel rompería ese
mapeo 1-botón-por-slice.
El caché de 240 columnas (min/max, 480 bytes) se recalcula de forma bloqueante (~1-4 ms)
cada vez que cambia el sample que suena o cuando el banco termina de mutar (carga
SD/USB) — la ISR de audio preempta este cálculo, así que el audio nunca lo nota. Esta
zona tiene la prioridad de redibujo más baja del dashboard (para no competir con el resto
de widgets por los slots de flush) y el movimiento del playhead está throttleado a ~25 Hz,
alineado con el límite global de refresco.

**Sin overlay temporal**: existió hasta la Fase 5 (nombre de modo al presionar Select,
parámetro con valor y barra de progreso al ajustar L/R) y se quitó — los shortcuts
Select+botón musical (sección 3) ya permiten saltar de modo sin necesitar ese aviso, y
las barras de Function A/B del dashboard normal se actualizan en vivo mientras se
ajustan (el dirty-tracking ya reaccionaba al valor del knob; el overlay era lo único
que bloqueaba que eso se viera). Las pantallas del modo 8 (Browse SD) son la única
excepción: siguen siendo un overlay, y persistente (sección 3.1).

**Barra de selección de sample (modo 0, Function A)**: en vez de un relleno continuo,
un paginador de segmentos — un segmento resaltado por sample, agrupando en potencias de
2 si el banco tiene más de 32 samples (el máximo real es 128, `PIKO_BANK_MAX_SAMPLES`)
para que cada segmento siga siendo distinguible.

**Barras de parámetro (Function B del modo 0, y Function A/B de los modos 1-7)**:
también segmentadas, con 25 bloques de 6 px separados por 1 px (`draw_stepped_bar()`),
más el valor numérico normalizado a 0-127 a la derecha. El control es por botones y
cada pulsación es un paso discreto, así que una barra de relleno continuo mentía sobre
la naturaleza del control: mostrarla en bloques hace que "un toque = un bloque" sea
literal y verificable de un vistazo. La proporción 6+1 px se validó en el panel real.

Ojo con `Paint_DrawRectangle`: **incluye ambos extremos**, así que el ancho de cada
bloque es `x` a `x + kSegW - 1`. Sin el `-1` los bloques se tocan entre sí y la barra
se ve como un relleno continuo — exactamente el bug que se estaba tratando de evitar.

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
  Los 2 LEDs virtuales correspondientes a `button_on`/`button_on2` se pintan en blanco
  sólido (en vez del gris medio normal por amplitud) mientras `btn_retrig` esté activo por
  la combinación de 2 botones (`src/gamepi13/ui.cpp`, `draw_leds()`;
  `src/main.cpp`, campo `retrig_leds_mask` de `GamepiUiState`). Nota de alcance: solo
  cubre el retrigger disparado por combo de 2 botones — el retrigger que a veces se
  dispara por probabilidad (`probability_retrig`, sin un segundo botón presionado) no
  tiene un botón "segundo" que resaltar, así que en ese caso la máscara puede quedar en 0
  o con un solo LED aunque el audio esté igual haciendo stutter.
- **RESUELTO — waveform con playhead en el dashboard.** Estaba en el spec original como
  "Fase 2.1" (fuera de alcance) y se había reclasificado como "riesgo alto" — un estudio
  posterior (`docs/superpowers/specs/2026-07-16-waveform-playhead-design.md`) mostró que
  la decimación por XIP es barata (~1-4 ms una vez por cambio de sample, la ISR de audio
  preempta el cálculo) y que el DMA era innecesario. Implementado fusionado con la
  antigua barra de LEDs (sección 4). Único hallazgo real en hardware: el throttle inicial
  del playhead (100 ms) generaba una demora perceptible entre el audio y el cursor —
  bajado a 40 ms (alineado con el flush global de 25 Hz) para resolverlo.
- **RESUELTO — Select + botón musical para saltar directo de modo.** Ver sección 3 para
  el uso. Durante el diseño se encontró una fragilidad latente ya existente: los 3 combos
  de 4 botones (clock lock, reset FX, mute/start-stop heredado) compartían índices entre
  sí (1 y 6 entre clock-lock/reset-fx; 0 y 7 entre reset-fx/mute-start-stop) y cada uno
  consumía `ChangedHigh(true)` de forma independiente — el mismo patrón de bug ya
  encontrado para Start, pero en código heredado del pikocore original, nunca antes con
  una cuarta consumidora sobre los mismos 8 índices. Se corrigió consolidando la lectura
  de flancos de los 8 botones musicales en un array por tick, leído por los 3 combos y
  por el gesto nuevo.
  **Bug real encontrado en hardware** (no anticipado en el diseño): al pausar el escaneo
  de audio mientras Select está sostenido (para que el botón musical usado en el gesto no
  también dispare un jump/retrigger), el primer intento solo pausó el bloque que actualiza
  `button_on`/`button_on2` — dejó sin pausar un bloque SEPARADO (`main.cpp`, dentro de
  `pwm_interrupt_handler()`, justo después) que arma el retrigger leyendo esos mismos
  valores, ahora congelados. Cada botón musical presionado durante el gesto Select se leía
  como "segundo botón completando un combo" contra el `button_on` obsoleto, disparando
  retriggers ("break fx") al azar — confirmado en hardware. Fix: pausar también ese
  bloque con el mismo flag.
- **RESUELTO — retrigger con subdivisión exacta (Start + 2do botón).** Ver sección 2 para
  el uso. Durante la implementación se encontró un bug real: marcar el flag
  `gamepi_start_used_as_modifier` solo en el instante exacto del disparo (dentro de la ISR
  de audio) no alcanzaba — si Start se presionaba/soltaba en un tick distinto al del
  disparo (casi cualquier secuencia real de dedos), el flag quedaba sin marcar y soltar
  Start terminaba disparando el toggle de mute/start-stop, silenciando el audio.
  Confirmado en hardware. Fix: marcar el flag de forma continua en el loop principal
  mientras `btn_start.On() && btn_retrig` (el segundo se mantiene activo toda la duración
  del efecto, no solo su primer tick) — cubre cualquier orden de presión.
- **CONFIRMADO — modos 5 (grabar/reproducir secuenciador) y 6 (guardar/cargar en
  flash) funcionan correctamente, pero no dan ninguna confirmación visible.** El
  usuario reportó que "no parecen funcionar"; la investigación (lectura de código +
  prueba en hardware: subir Function A en modo 6 para guardar un cambio de parámetro,
  apagar y reprender, confirmar que el cambio persistió) confirmó que la lógica interna
  (`sequencer.SetRecording()`, `save_settings()`, `do_load`, `src/main.cpp`) se ejecuta
  sin problemas. La causa real es que su ÚNICA señal de confirmación en el hardware
  original eran LEDs (`debounce_led_save`/`debounce_led_sequencer`/`debounce_led_load`),
  y en GamePi13 la clase `LED` es un no-op total (`doth/led.h`, cada `gpio_put()` bajo
  `#if !PIKO_GAMEPI13` — Fase 1, "Neutralizar los GPIO de los LEDs", porque esos pines
  están reasignados a otra cosa en este HAT). El overlay genérico que existía hasta la
  Fase 5 tampoco ayudaba (mostraba la misma barra numérica 0-4095 para cualquier modo,
  sin texto de "Grabando"/"Guardado"/"Cargado") y ya no existe (ver sección 4) — la
  barra normal del dashboard ahora se mueve en vivo con el valor del knob, pero sigue
  sin decir "Grabando"/"Guardado"/"Cargado" explícitamente. Sin resolver por ahora — ver
  sección 6 para la mejora propuesta (agregar feedback en el LCD).
  **Hallazgo relacionado, no confirmado como causante de un problema real todavía:**
  `VirtualKnob::Reset()` (`doth/virtualknob.h`) es un no-op, mientras el código que
  cambia de modo (`src/main.cpp`, "prevent spurious changes when changing selection")
  asume que sí resetea el knob. Como el valor de knob1/knob2 es compartido entre los 8
  modos y las acciones de modos 5/6 solo se evalúan en el flanco de `Changed()` (un
  tick justo cuando `Adjust()` cambia el valor), si al entrar a modo 5/6 el knob ya
  está por encima/debajo del umbral de otro ajuste previo en otro modo, la acción no se
  dispara hasta mover el knob de nuevo. No se reprodujo explícitamente en hardware.
- **RESUELTO — el rediseño de la pantalla Browse SD (marco + dígitos gráficos +
  ícono, ver sección 4) al principio nunca aparecía a partir de la segunda entrada al
  modo 8.** Se dibujaba bien la primera vez desde el arranque, pero al salir y volver a
  entrar, el dashboard normal seguía mostrándose (con el ícono de modo correctamente en
  SD) en vez de la pantalla de SD, indefinidamente. Causa real: el bloque de reintento
  de estas pantallas (`gamepi_sd_redraw_kind`, `src/main.cpp`) quedó ubicado *después*
  de `gamepi_ui_tick()` en el mismo tick — y el camino normal de `gamepi_ui_tick()`
  llama a `flush_allowed()` (el límite de 25Hz de refresco del LCD) sin condición en
  cada tick, así que le "ganaba" el turno al bloque de reintento apenas se abría la
  ventana. Mientras el overlay de SD estaba activo (persistente) esto no importaba,
  porque `gamepi_ui_tick()` deja de competir por `flush_allowed()` en ese caso — pero
  al salir del modo 8 y volver el dashboard normal a competir, el reintento quedaba
  bloqueado para siempre. Fix: mover el bloque de reintento para que corra *antes* de
  `gamepi_ui_tick()`, dándole prioridad. Confirmado en hardware: entra y sale del modo 8
  repetidamente sin problema después del fix.
  **Hallazgo relacionado, descartado como bug:** al principio pareció que el indicador
  "Cargado (banco activo)" se perdía al salir y volver a entrar al modo 8 — pero era
  simplemente que reingresar resetea la navegación al primer archivo de la lista (no
  necesariamente el que está cargado). Confirmado en hardware navegando puntualmente
  hasta el archivo cargado tras reingresar: el indicador funciona correctamente.
- **RESUELTO — el cambio de sample no se veía en el dashboard mientras el reproductor
  estaba detenido, solo mientras sonaba.** Causa real: el nombre/índice de sample que
  muestra el dashboard se armaba a partir de `sample_set`, que solo se sincroniza desde
  `sample_change` (lo que escribe el ajuste de L/R) en un evento de compás dentro de la
  ISR de audio (`pwm_interrupt_handler()`) — y esa ISR corta camino antes de llegar a
  esa lógica cuando `do_mute` (detenido) es verdadero, así que el compás nunca ocurre y
  el display queda congelado. Fix: el dashboard pasa a mostrar `sample_change`
  directamente (siempre queda acotado a un rango válido por todos los puntos donde se
  escribe), sin tocar la ISR de audio ni ninguna variable relacionada con el sonido en
  sí (`sample_set`/`sample` siguen intactos). Confirmado en hardware: el nombre/índice y
  la barra segmentada se actualizan al instante, esté sonando o no.
- **RESUELTO — con la intensidad de "break fx" (modo 0, Function B) al máximo, el
  botón de stop no detenía la reproducción** hasta bajar la intensidad a 0. Bug
  preexistente, no relacionado con ningún cambio de esta sesión. Causa real: dentro de
  la ISR de audio, un retrigger puede dispararse puramente al azar en cada compás
  (`if (randint(0, 254) < probability_retrig) { btn_retrig = true; }`) sin que el
  usuario toque ningún segundo botón — y con break fx al máximo, `probability_retrig`
  es tan alta que esto pasa casi todo el tiempo. El manejo de Start marcaba
  `gamepi_start_used_as_modifier = true` con solo `btn_start.On() && btn_retrig`, sin
  distinguir un retrigger real de 2 botones de uno disparado solo por azar — así que
  soltar Start para detener, justo cuando `btn_retrig` estaba en `true` por pura
  casualidad, se interpretaba como "Start usado como modificador de un combo" y
  suprimía el stop. Fix: agregar `&& button_on2 < NUM_BUTTONS` a esa condición —
  `button_on2` solo es válido durante un combo real de 2 botones, nunca en el camino de
  probabilidad pura. Confirmado en hardware: con break fx al máximo, Start ahora
  detiene la reproducción correctamente.
- **RESUELTO (bug preexistente de pikocore, encontrado en un code review) — se
  guardaba a flash el valor de probabilidad equivocado para gate y retrig.** Tres
  instancias del mismo copy-paste (`src/main.cpp`, dos en el switch de knob B y una en
  `param_set_break()`): tras computar `probability_gate`/`probability_retrig`, se
  guardaba `probability_direction`/`probability_jump` en su slot de `save_data`. Como la
  carga al arrancar lee justo esos slots (`probability_gate = save_data[SAVE_PROB_GATE]`,
  etc.), después de un guardado + ciclo de encendido esos dos parámetros se restauraban
  con el valor de reversa/salto en vez del propio. Fix: guardar el valor recién
  computado. Confirmado en hardware con valores extremos (retrig al máximo, jump a 0,
  guardar, reiniciar → se oyen los stutters al azar restaurados; con el bug se cargaba
  el 0 de jump y no había ninguno).
- **LÍMITE CONOCIDO (no es un bug introducido) — con la probabilidad de retrigger al
  máximo, el equipo queda casi inusable.** La ISR de audio dispara retriggers al azar en
  cada compás (`randint(0, 254) < probability_retrig`); al tope, eso ocurre casi
  continuamente y satura la CPU, dejando sin tiempo al lazo de control: Start no detiene
  la reproducción (tarda ~20 s), el playhead no avanza y los parámetros no responden.
  El audio sigue sonando porque va por la ISR, que es justamente la que acapara. Bajar
  la probabilidad devuelve todo a la normalidad. **Cuidado con guardar ese valor a
  flash**: persiste entre arranques y hace parecer que el equipo está roto desde el
  boot — nos costó un ciclo entero de debugging hasta darnos cuenta (la causa se
  atribuyó erróneamente a la microSD). Es un límite heredado del motor de audio
  original, no algo del port.
- **RESUELTO — el LCD quedaba lentísimo después de visitar el modo 8 (Browse SD).** El
  LCD y la microSD comparten spi1, pero el LCD fijaba su velocidad (10 MHz) una sola vez
  al arrancar, mientras que el driver de SD reconfigura el bus cada vez que lo usa
  (100 kHz al abrir, 400 kHz para el init de tarjeta, 12 MHz para datos) sin restaurar
  nada. Al volver del modo 8 el bus quedaba en 100–400 kHz y cada flush del LCD pasaba
  de ~18 ms a ~1.8 s, bloqueando el lazo de control con el mutex tomado. Fix: `flush()`
  reafirma `GAMEPI_LCD_SPI_HZ` en cada llamada (mismo contrato que ya cumple el lado SD:
  quien toma el mutex fija sus propios parámetros de bus). Confirmado en hardware.
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

- **Feedback en el LCD para grabar/reproducir secuenciador y guardar/cargar (modos
  5/6)**: ver sección 5 — la lógica funciona, pero no hay ninguna confirmación visible
  desde que las LEDs quedaron deshabilitadas en este HAT. Agregar texto o ícono en el
  dashboard (ej. "Grabando…"/"Guardado"/"Cargado") resolvería el problema real detrás
  del reporte de que estos modos "no funcionan".
- **Detección de SD en caliente**: hoy hace falta reiniciar el dispositivo después de
  sacar/poner la tarjeta (ver sección 5). El socket no expone Card Detect, así que esto
  requeriría o bien un GPIO físico adicional cableado a mano al socket, o pulir el
  driver vendorizado para forzar una re-inicialización completa en cada entrada al modo
  8 en vez de confiar en su caché de estado interno.
- **Indicador de "banco actualmente cargado" más visible**: ya se agregó uno básico en
  la Fase 3 (nombre combinado en el dashboard + resaltado verde en la lista), pero podría
  sobrevivir a un reinicio (hoy es solo de sesión, se pierde al apagar) si se guardara el
  nombre del archivo en flash junto al resto de `save_data`.
- **IMU (ICM20948, I2C GP2/3)** como modulador de FX — mencionado en el plan original,
  nunca implementado; podría mapear inclinación/movimiento a algún parámetro en vivo.
- **Ícono de reloj MIDI**: el dashboard con bitmaps de Lopaka (ver sección 4) solo
  tiene diseñados los íconos de reloj INT/EXT — el reloj en MIDI sigue mostrando
  "MIDI" en texto hasta que se diseñe ese gráfico. (Las etiquetas de Function A/B de
  los 8 modos ya están todas resueltas como gráfico.)
