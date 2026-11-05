# pikocore_gamepad — E/S por USB: MIDI y audio por el USB-C del modulo, sin jacks MIDI

Fecha: 2026-11-05. Estado: diseno aprobado en conversacion el 2026-11-05, sin
implementar. Se ejecuta en tres etapas, cada una con su rama, su PR y su plan
(`docs/superpowers/plans/`); el orden es 1, 2, 3, y la 3 puede empezar en el
GamePi13 mientras la 2 esta en ruteo.

## Por que

El gamepad habla con un computador o un celular, no con sintes DIN parados
solos (decision del usuario, 2026-11-05). Con eso:

- Los jacks MIDI de la placa (J6 IN con el opto H11L1, J7 OUT con el
  LVC1G17, 10 partes en GP27/GP28, hoja `07_midi`) son peso muerto: ahorran
  unos US$2, dos piezas THT soldadas a mano y dos calados del gabinete, y se
  llevan un firmware escrito el 2026-11-04 que nunca corrio (receptor PIO en
  GP27 con la entrada invertida en el banco de IO, UART0 en GP28).
- El USB-C del modulo ya esta en el borde inferior con calado previsto, carga
  la LiPo (ETA6096) y lleva datos. El firmware ya enumera como dispositivo
  compuesto CDC (cargador de bancos) + clase MIDI (TinyUSB 0.18 del SDK
  2.1.1). MIDI OUT por USB ya funciona (`MidiOut_send` escribe al endpoint).
  MIDI IN por USB no lo lee nadie.
- No hay entrada de audio en ningun lado del hardware. La salida es el motor
  de 8 bits a tasa variable, retenido en una palabra que un DMA en modo
  ENDLESS vuelca al I2S a 48 kHz hacia el PCM5102A.
- Audio por USB es clase UAC2 (TinyUSB la trae con ejemplos). En full speed
  sobra ancho de banda para estereo 48 kHz 16 bits en los dos sentidos
  (192 B por trama por sentido, contra 1023 B por endpoint). Windows 10+,
  macOS y Linux lo toman sin driver.

Restriccion que fija todo: el puerto del modulo es solo dispositivo (CC con
pull-down, VBUS al cargador). El gamepad no puede ser host USB por ahi, asi que
MIDI por USB significa un computador, un celular con OTG o una cajita host.
Colgar un sinte USB directo necesitaria un segundo puerto host por PIO-USB
(fuera de alcance, ver al final).

## Decisiones fijadas por el usuario

| Pregunta | Respuesta |
|---|---|
| Con que habla el MIDI | computador o celular |
| Sentidos del audio por USB | los dos: gamepad a computador y computador a gamepad |
| Para que sirve computador a gamepad | escucharlo en los auriculares y el parlante del gamepad, mezclado con el motor |
| Nucleo de audio | camino A: la palabra retenida por DMA se queda; subtick exacto y realimentacion UAC2 |
| Banco de pruebas | el GamePi13, unico hardware que existe |

## Arquitectura comun

- Un solo dispositivo USB compuesto en el USB-C del modulo. Hoy CDC + MIDI;
  al final de la etapa 3, CDC + MIDI + UAC2.
- La pila TinyUSB no cambia de lugar: `tusb_init()` corre en el core 0 antes
  de lanzar el core 1 (main.cpp), la interrupcion USB queda en el core 0 y
  `tud_task()` sigue en el lazo del core 1 (`piko_sample_manager_core`), que
  es como funciona hoy el cargador de bancos. `CFG_TUSB_OS` es `OPT_OS_PICO`,
  asi que la cola de eventos entre cores ya es segura.
- Todo lo que cruza de un core al otro va por anillos de un productor y un
  consumidor, con indices volatiles y las barreras de `src/piko_barrier.h`,
  sin locks: una cola de paquetes MIDI, un anillo de audio del host y un
  anillo de audio hacia el host.
- El motor de audio (`pwm_interrupt_handler`) no sabe que existe USB: lee y
  escribe esos anillos desde su interrupcion y nada mas.

## Etapa 1: MIDI IN por USB (solo firmware, los dos targets)

**Componentes.** Un header nuevo en `doth/` (header-only, como el resto del
directorio). TinyUSB llama a `tud_midi_rx_cb(itf)` desde `tud_task()` en el
core 1; ahi se vacia el endpoint con `tud_midi_n_packet_read()` a una cola de
64 paquetes de 4 bytes. En el lazo de control del core 0, donde hoy se llama a
`Onewiremidi_receive()`, una funcion saca los paquetes y despacha por el byte
de estado:

| Estado | Callback existente |
|---|---|
| 0xF8 | `midi_timing()` |
| 0xFA | `midi_start()` |
| 0xFB | `midi_continue()` |
| 0xFC | `midi_stop()` |
| 0x9n, velocidad > 0 | `midi_note_on(nota, vel)` |
| 0x9n con velocidad 0, 0x8n | `midi_note_off(nota)` |
| todo lo demas (sysex, CC, sensing...) | descartado |

Las notas siguen sin efecto mientras `MIDI_NOTE_KEY` sea 0; se despachan
para que el camino quede completo.

**Reglas.**

- El despacho USB corre siempre, en los dos targets, sin mirar
  `clock_input_ittybittymidi`: esa bandera elige que hace el jack, y por USB no
  hay jack. En el GamePi13 con la bandera en MIDI y reloj llegando por los dos
  lados se duplican los pulsos; es un error de uso, no se defiende en codigo.
- Cola llena: se pierde el paquete mas nuevo y se cuenta en un contador que
  sale por la traza `DEBUG_MIDI`.
- Esta etapa no toca pines ni placa. El receptor DIN del gamepad (GP27) queda
  hasta la etapa 2.

**Jitter.** Los paquetes llegan agrupados por trama USB de 1 ms. `midi_timing()`
promedia `MIDI_DELTA_COUNT_MAX` deltas para el BPM, asi que el jitter de 1 ms
se diluye; a 120 BPM un pulso de reloj son 20,8 ms.

**Prueba.** En el GamePi13, con un DAW o un script de `mido` mandando reloj y
start/stop: el BPM se engancha en pantalla, start/stop arrancan y paran la
reproduccion. `DEBUG_MIDI` muestra cada mensaje.

## Etapa 2: los jacks fuera de la placa (hardware + firmware + docs)

**Scripts de la placa** (`hardware/pikocore_gamepad/pcb/`):

| Archivo | Cambio |
|---|---|
| `netlist.py` | se van el bloque MIDI (J6, J7, U9, U10, R40-R43, D3, C56), los simbolos `LVC1G17` y `H11L1`, y los LCSC de 10R, 33R y 220R que solo usaban ellos |
| `gen_sch.py` | se va la hoja `07_midi` y su nota; `07_midi.kicad_sch` sale del repo |
| `pinmap.py` | GP27 y GP28 pasan a `FREE = (26, 27, 28)`; docstring |
| `placements.py` | se van las diez entradas y sus comentarios |
| `gen_pcb.py`, `params.py` | solo comentarios que nombran MIDI; revisar |
| `tests/test_netlist.py`, `tests/test_pinmap.py` | pierden sus casos MIDI; `test_refs.py` usa U10 solo como ejemplo de hueco, no cambia |
| `route_cycle.sh` | la ruta del jar pasa a `freerouting-2.5.0.jar` (la 2.4.1 ya no esta en la maquina) |

**Firmware.** `PIN_MIDI_TX` y `PIN_MIDI_RX` salen de `config.h` (la puerta
G-4 sigue verde porque `pinmap.py` cambia en el mismo PR). En `main.cpp` se va
el bloque de GP27 (inversion en el banco de IO) y GP28 (UART0), y el receptor
de un hilo deja de crearse bajo `PIKO_GAMEPAD`. `midi_out.h` pierde la rama
DIN y queda solo el USB. `hw_gamepi13.h` actualiza sus comentarios.

**Layout.** No se mueve nada mas: las dos bandas del borde superior quedan
vacias y el placement verificado se conserva. Igual es un ciclo completo,
porque el placement cambio: `gen_pcb.py`, `manual_tracks.py`,
`plane_vias.py`, export, freerouting 2.5.0, import, `finish_pcb.py`, DRC,
`gen_fab.py`, cerrado con el reporte de la skill pcb-verify. Esperado: 66
partes (hoy 76), dos lineas menos sin LCSC (los dos jacks), dos ventanas menos
en el DXF del gabinete. La 2.5.0 no esta validada contra lo que la skill
documenta de la 2.4.1: la primera corrida se mira con atencion.

**Documentacion.** `hardware/pikocore_gamepad/README.md`,
`docs/hardware/pikocore_gamepad-pinout.md`,
`docs/hardware/pikocore_gamepad-jlcpcb-checklist.md` y el README raiz nombran
los jacks; se actualizan en el mismo PR. La spec del 2026-10-16 queda como
historia.

## Etapa 3: audio por USB en los dos sentidos

### La interrupcion (core 0)

**El subtick.** `pwm_interrupt_handler` corre a 992 kHz (clk_sys 248 MHz, PWM
wrap 250, clkdiv 1). Gana un acumulador entero al principio de cada tick:

- paso = wrap x 256 = 64 000 por tick;
- umbral = 64 x (entero x 256 + fraccion) del divisor del PIO I2S, leido del
  registro `clkdiv` del state machine en el init, no de una constante.

Cuando el acumulador cruza el umbral hay un subtick y se resta el umbral. PWM y
PIO cuelgan del mismo reloj, asi que la razon es exacta: con el divisor de hoy
(248e6 / (64 x 48000) = 80,729; el SDK lo deja en 80 + 187/256 con
`PICO_PIO_CLKDIV_ROUND_NEAREST`, o 186 sin el) el umbral es 1 322 688 y hay
20,667 ticks por cuadro del DAC; el subtick cae exactamente una vez por cuadro
a largo plazo, con jitter de a lo sumo un tick (1 us). Nadie mantiene una
constante sincronizada con el divisor.

En el GamePi13 (salida PWM, sin I2S) el mismo acumulador usa paso 48 000 y
umbral 992 000.

**La mezcla.** `gamepad_i2s_word`, la palabra unica que el DMA ENDLESS vuelca al
I2S, se queda. Se recalcula desde dos entradas:

- el sample del motor, 8 bits sin signo, que llega cuando el motor llama a
  `audio_out()` como hoy; se guarda como 16 bits: `(v - 128) << 8`;
- el par izquierda/derecha del host, 16 bits, que se saca del anillo del host
  en cada subtick (cero si el anillo esta vacio o inactivo).

Cada mitad de la palabra es la suma saturada en 16 bits (`SSAT`, Cortex-M33)
del motor mas el host atenuado 6 dB (`>> 1`, constante de compilacion
`USB_AUDIO_HOST_SHIFT`). Sin host el resultado es identico al de hoy. En el
mismo subtick el sample del motor, solo, se empuja al anillo hacia el host:
asi el DAW nunca se graba a si mismo.

**Costo.** Unos 8 ciclos por tick para el acumulador (3 % del core 0) y unos
60 por subtick (1 %).

### El lado USB (core 1)

**Anillos.**

| Anillo | Tamano | Productor | Consumidor |
|---|---|---|---|
| del host | 1024 cuadros estereo int16 (4 KB, 21 ms), objetivo 512 | `tud_audio_rx_done_post_read_cb` (core 1) | subtick (core 0) |
| hacia el host | 256 samples mono int16 (512 B) | subtick (core 0) | `tud_audio_tx_done_pre_load_cb` (core 1) |

El consumidor del anillo del host arranca recien cuando el llenado llega al
objetivo, y vuelve a esperar despues de un vacio, para que el buffer parta
centrado.

**Callbacks.** Al llegar datos, `tud_audio_rx_done_post_read_cb` copia con
`tud_audio_n_read()` del FIFO de TinyUSB al anillo del host (descarta y cuenta
si esta lleno) y actualiza la realimentacion. Antes de cada envio,
`tud_audio_tx_done_pre_load_cb` saca del anillo hacia el host lo que haya,
hasta 49 samples, y lo escribe con `tud_audio_n_write()`; TinyUSB manda
paquetes de tamano variable (`audiod_tx_packet_size`), que es lo que una
fuente asincrona hace, y el host se adapta.

**Realimentacion.** `CFG_TUD_AUDIO_ENABLE_FEEDBACK_EP 1`, metodo
`AUDIO_FEEDBACK_METHOD_DISABLED`: el valor lo pone la aplicacion con
`tud_audio_n_fb_set()` cada milisegundo desde el callback de recepcion.
Formato 10.14 en full speed: nominal 48 x 2^14 = 786 432. Control
proporcional sobre el error de llenado: `fb = nominal + (objetivo - llenado) x 32`,
o sea 512 cuadros de error equivalen a un cuadro por milisegundo (2 %).
Con una deriva real de 100 ppm el error estacionario es de dos o tres cuadros;
no hace falta integral (ponytail: si un host lo pone a oscilar, un termino
integral chico). Para macOS en full speed TinyUSB trae
`CFG_TUD_AUDIO_ENABLE_FEEDBACK_FORMAT_CORRECTION` (y endpoint de 3 bytes);
queda como interruptor de banco, apagado por defecto.

**Descriptor y configuracion.** Una funcion UAC2 con una fuente de reloj fija
en 48 kHz, un flujo de salida (host a gamepad) estereo 16 bits con su endpoint
de realimentacion, y un flujo de entrada (gamepad a host) mono 16 bits, sin
unidades de volumen ni mute. Se arma a mano en `doth/usb_descriptors.c` con los
bloques `TUD_AUDIO_DESC_*`, tomando `examples/device/uac2_headset` para los
dos flujos y `uac2_speaker_fb` para la realimentacion.

| Interfaz | Endpoints |
|---|---|
| CDC (2, como hoy) | 0x81 notif, 0x02 / 0x82 |
| MIDI (2, como hoy) | 0x03 / 0x83 |
| Audio control (1) | — |
| Audio streaming salida (1) | 0x04 iso OUT (196 B = 49 cuadros estereo), 0x84 realimentacion |
| Audio streaming entrada (1) | 0x85 iso IN (98 B = 49 samples mono) |

7 interfaces, 16 endpoints disponibles en el RP2350. `tusb_config.h` gana
`CFG_TUD_AUDIO 1` y la lista `CFG_TUD_AUDIO_FUNC_1_*` (un formato, 48 kHz,
TX 1 canal, RX 2 canales, buffers de software de 2 paquetes por lado,
`N_AS_INT 2`, `CTRL_BUF_SZ 64`). El PID gana `_PID_MAP(AUDIO, 5)` y
`bcdDevice` sube de 0x0100 a 0x0200, para que Windows no reuse la
configuracion cacheada. El cargador web no filtra por PID
(`web/serial-test.html` solo lo imprime), asi que no se rompe.

### Fallos

- **El host cierra el flujo (alt 0) o se desenchufa.**
  `tud_audio_set_itf_close_EP_cb` marca inactivo y vacia el anillo; el DAC
  vuelve a motor solo sin clic, porque la palabra se recalcula con host cero.
  `tud_audio_set_itf_cb` con alt 1 vuelve a armar el anillo desde cero.
- **Host atrasado.** Se mezclan ceros y se cuenta; con host adelantado se
  descarta y se cuenta. Los contadores salen por la traza de depuracion.
- **Escritura de flash durante una carga de bancos.** La interrupcion no
  corre, el DAC sostiene la ultima palabra como hoy, `tud_task()` no se llama y
  el host ve cortes mientras dura la carga. Aceptable: cargar no es tocar.
- **Bucle en el DAW.** Imposible por construccion: el flujo hacia el host
  lleva el motor solo.

### Banco de pruebas: GamePi13

El GamePi13 es el unico hardware que existe. Bajo `PIKO_GAMEPI13` el mismo
subtick alimenta la salida PWM de 8 bits: nivel = motor + (host mono >> 8 >>
`USB_AUDIO_HOST_SHIFT`), saturado a 8 bits (unas 15 lineas). Ahi se verifica
la enumeracion en Windows, macOS y un celular, el driver UAC2, la
realimentacion y la vuelta completa en un DAW antes de que exista la placa.
La mezcla a 8 bits es solo para probar; el camino real es el I2S del gamepad.

### Chequeo que queda

El acumulador y el controlador son funciones puras en el header. Un chequeo
de host con asserts (`tests/firmware/check_usb_audio.c`), compilado con el
`cl` del entorno de VS que ya usa la receta de build de Windows, confirma que
el acumulador da exactamente N subticks por M ticks para los dos juegos de
constantes y que el controlador converge al objetivo con una deriva
simulada. Lo demas se mide en el banco: con el flujo del host corriendo, el
nivel del anillo tiene que quedar plano y los contadores en cero.

## Verificacion por etapa

| Etapa | Que prueba que esta hecha |
|---|---|
| 1 | compila en los dos targets; en el GamePi13 el BPM se engancha al reloj USB y start/stop responden |
| 2 | pcb-verify todo en verde: G-F, 200+ tests, G-0/G-5/G-4/G-2/P, ERC 0, DRC 0 errores / 0 sin conectar / 0 paridad; `gen_fab.py` sin sufijo NO-FABRICABLE; firmware del gamepad compila sin `PIN_MIDI_*` |
| 3 | el chequeo de host pasa; en el GamePi13: enumera como CDC + MIDI + UAC2 en Windows, macOS y un celular; el DAW graba el motor y reproduce por el gamepad; nivel del anillo plano y contadores en cero durante 10 minutos |

## No verificado hasta tener placa o banco

- Corriente que el cargador del modulo le pide a un celular por OTG: la fija
  Waveshare, no la placa. Con la bateria cargada deberia ser poca.
- Ruido de masa por el USB en los auriculares al colgarlo del computador.
- Latencia host a auriculares: estimada en 13 ms (FIFO de TinyUSB mas 512
  cuadros de anillo) mas el buffer del driver del host.
- macOS en full speed con el endpoint de realimentacion (ver el interruptor).
- Windows con una funcion UAC2 sin unidad de volumen: legal, pero no probado.
- Android: UAC2 depende de la version; iOS lo toma.
- Margen de CPU real del core 0 con el subtick, medido y no estimado.
- Nada de lo anterior corrio en el gamepad: no hay placa construida.

## Fuera de alcance

- Host USB en el gamepad (PIO-USB en GP26/GP27 con un USB-A y 5 V del
  boost): es el unico camino para colgar un sinte USB directo, y es otro
  proyecto. Los tres GPIO que libera la etapa 2 lo dejan posible.
- Samplear en vivo desde el computador a un banco. El flujo host a gamepad
  lo deja posible; necesita interfaz de grabar y pasar por RAM antes de
  flash. El cargador CDC ya lo hace en frio desde un archivo.
- Control de volumen del host desde la UI: constante de compilacion por
  ahora.
- Notas MIDI tocando botones: `MIDI_NOTE_KEY` sigue en 0.
- Dejar el jack MIDI IN como seguro: descartado por el usuario.
