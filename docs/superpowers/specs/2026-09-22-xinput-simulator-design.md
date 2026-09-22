# pikocore-sim — simulador nativo Windows del firmware GamePi13, controlado por XInput

Fecha: 2026-09-22
Estado: propuesto, pendiente de aprobación

## Objetivo

Correr el firmware de pikocore para GamePi13 en una PC con Windows, tocándolo con un
control XInput (Xbox o compatible), con audio y LCD, **sin reescribir el motor**: el
simulador compila las mismas fuentes que van al RP2350 y reemplaza solamente el hardware
por debajo (pico-sdk, LCD, flash, PWM de audio).

Criterio de éxito: con un `.pikobank` cargado, cada control del GamePi13 documentado en
[GAMEPI13-INTERFACE.md](../../../GAMEPI13-INTERFACE.md) hace lo mismo que en el hardware
(jump, retrigger con 2 botones, combos de 4, Select/Start con doble rol, L/R con repetición
y aceleración, los 8 modos), el LCD muestra el mismo dashboard y el audio suena sin cortes.

## Decisiones tomadas

| Tema | Decisión |
|---|---|
| Plataforma | App nativa Windows (MSVC 2022 + Windows SDK). Sin dependencias externas. |
| Botones de cara | Mapeo **por posición** (layout SNES): Xbox Y→X, B→A, A→B, X→Y |
| Samples | Archivos `.pikobank` (los que exporta el loader web), por drag & drop o CLI |
| Firmware | Refactor mínimo permitido: `__asm volatile("dmb" ::: "memory")` → `PIKO_DMB()` |

## Fuera de alcance

- Modo 8 (Browse SD) — ya está aparcado en el firmware (`PIKO_GAMEPI13_SD=0`).
- MIDI (entrada/salida), clock externo, trigger out.
- Protocolo USB de carga de samples (`PikoSampleManager.cpp` no se compila).
- Construir bancos desde WAV — se usa el loader web para eso.

## 1. Qué se compila

Fuentes reales del firmware, sin copias ni parches al compilar:

- `src/main.cpp`
- `src/PikoAudioBank.cpp`
- `src/gamepi13/ui.cpp`, `src/gamepi13/dev_shim.c`
- `src/gamepi13/lcd/LCD_1in3.c`, `GUI_Paint.c`, `font12/16/20/24.c`
- headers de `doth/`

Defines: `PIKO_GAMEPI13=1`, `PIKO_GAMEPI13_SD=0`, `PIKO_FIRMWARE_RESERVE=524288u`,
`PICO_FLASH_SIZE_BYTES=16MB`, más las de `target_compile_definitions.cmake` (incluido
directamente desde el CMake del simulador para que no diverjan).

### Cambio en el firmware

Los 7 `__asm volatile("dmb" ::: "memory")` (`main.cpp`, `PikoAudioBank.cpp`,
`PikoSampleManager.cpp`) pasan a una macro `PIKO_DMB()` definida en un header común
(`src/piko_barrier.h`):

- en ARM: `__asm volatile("dmb" ::: "memory")` — código generado idéntico;
- en el simulador (`PIKO_SIM`): `std::atomic_thread_fence(std::memory_order_seq_cst)`.

El working tree tiene cambios sin commitear del usuario en `src/main.cpp` (remapeo del
reset de FX). El refactor se commitea aislado aplicando solo su parche al índice
(`git apply --cached`), sin arrastrar esos cambios.

## 2. Shim del pico-sdk (`sim/shim/`)

Headers con los mismos nombres que los del SDK (`pico/stdlib.h`, `pico/multicore.h`,
`hardware/pwm.h`, `hardware/gpio.h`, `hardware/spi.h`, `hardware/flash.h`,
`hardware/irq.h`, `hardware/sync.h`, `hardware/adc.h`, `hardware/clocks.h`,
`pico/binary_info.h`, `tusb.h`, …) que implementan lo mínimo que usa el firmware:

| Subsistema | Comportamiento en el simulador |
|---|---|
| GPIO | Array de estado por pin. Los 12 pines de botón leen el estado del control (activo en bajo, como con pull-up). GP28 (LED de beat) se muestra en la ventana. |
| PWM | `pwm_set_gpio_level(AUDIO_PIN, x)` guarda el nivel actual para el DAC virtual. El resto (backlight) se registra sin efecto. |
| IRQ | `irq_set_exclusive_handler(PWM_IRQ_WRAP, h)` guarda el handler; `irq_set_enabled` / `pwm_set_irq_enabled` lo habilitan en el planificador. |
| SPI + DC/CS | Alimentan un **emulador de ST7789** (ver §4). |
| Flash | Array de 16 MB. `XIP_BASE` se define como la dirección de ese array, así `flash_header()` y `flash_target_contents` leen de ahí. `flash_range_erase/program` escriben en el array y lo persisten. `flash_do_cmd` responde un JEDEC ID de 16 MB. |
| Tiempo | `time_us_32/64`, `sleep_us/ms`, `__wfi` — ver §3. |
| USB, ADC, MIDI, clocks | Stubs (`tud_mounted()` = false, `adc_read()` = 0, `set_sys_clock_khz` no-op). |
| Multicore | `multicore_launch_core1` no lanza nada del firmware; los `multicore_lockout_*` son no-op (no hay XIP real que proteger). |
| `mutex_t` | No-op: todo el firmware corre en un solo hilo (ver §3). |

### Persistencia de flash

El array se respalda en `pikocore_sim_flash.bin` (junto al `.exe`, o el que se indique con
`--flash`). Se carga al arrancar y se escribe en cada erase/program y al cargar un banco.
Así el banco cargado y lo guardado en el modo 6 sobreviven al reinicio, igual que en el
hardware.

### Carga de `.pikobank` ("core1" del simulador)

Reproduce la secuencia del core1 real: `piko_audio_bank_set_mutating(true)` → copiar el
blob a `PIKO_AUDIO_FLASH_OFFSET` → `piko_audio_bank_rescan()` →
`piko_audio_bank_set_mutating(false)`. Se ejecuta **en el hilo de emulación, entre dos
pasos del planificador**, por eso es atómica respecto de la ISR y de `main()`. Antes de
escribir se valida magic, versión y que `header_size + audio_bytes` entre en la capacidad
de la flash; si no, se rechaza con un mensaje en la barra de estado y la flash queda como
estaba.

## 3. Tiempo y concurrencia: planificador determinista

**Reloj virtual** en ciclos de CPU de 248 MHz (`CLOCK_RATE`).
`time_us_64() = ciclos / 248`.

Un único **hilo de emulación** alterna, de forma determinista, entre:

- **La ISR de audio**, una vez cada 251 ciclos (PWM `wrap=250`, `clkdiv=1` → ~988 kHz),
  mientras esté habilitada.
- **`main()` del firmware, dentro de una Fiber de Win32.** Cuando `main()` llama a
  `__wfi()`, `sleep_us(n)` o `sleep_ms(n)`, cede el control al planificador indicando
  hasta qué instante virtual duerme (`__wfi` = hasta el próximo tick de ISR). El
  planificador ejecuta las ISR que caen en ese intervalo, avanza el reloj y retoma la
  Fiber.

Consecuencias:

- El lazo de control corre a la misma cadencia virtual que en el hardware, así que los
  temporizadores que cuentan iteraciones (`clock_ms % 16`, `debounce_saving = 32000`,
  `debounce_sample = 500`, el `clock_ms == 100` de carga inicial) y los que miden
  `time_us_64()` (repetición de L/R, aceleración de tempo, `flush_allowed()`) se comportan
  como en el RP2350.
- La ISR nunca interrumpe a `main()` a mitad de una instrucción, así que no hay data
  races. Es una simplificación: en el hardware la ISR sí puede preemptar en cualquier
  punto. Se acepta porque el firmware ya tolera ambas situaciones.
- El cómputo de `main()` cuesta 0 tiempo virtual. En el hardware cada vuelta cuesta
  algunos µs más que el `sleep_us(50)`. La diferencia es menor y se documenta.

**Pacing:** el hilo de emulación produce audio en un ring buffer y corre adelantado hasta
~20 ms respecto de lo que ya consumió el dispositivo de audio. Si está adelantado, duerme
~1 ms. El tiempo virtual sigue al real en promedio. En modo headless (§7) no hay pacing y
corre a la máxima velocidad posible.

## 4. LCD: emulador de ST7789

`LCD_1in3.c` y `dev_shim.c` se compilan tal cual. Los bytes que mandan por
`spi_write_blocking` más el nivel del pin DC (GP25) y CS (GP8) alimentan una pequeña
máquina de estados del controlador:

- comandos `0x2A` CASET, `0x2B` RASET, `0x2C` RAMWR (RGB565 big-endian, con auto-avance
  en la ventana), `0x36` MADCTL (orientación), `0x3A` COLMOD; el resto se ignora;
- GRAM de 240×240 RGB565.

La imagen visible es la GRAM transformada por MADCTL y por la rotación física del panel en
el GamePi13. Esa rotación se fija empíricamente: el splash y el dashboard tienen que
leerse derechos. Emular en este nivel (en vez de interceptar `LCD_1IN3_DisplayWindows`)
ejercita también la conversión de rects lógicos → memoria de `flush()` en `ui.cpp`, que ya
tuvo un bug real con la rotación.

El hilo de UI copia la GRAM bajo un mutex liviano a 60 fps para dibujarla; puede haber
tearing de un frame, igual que en el panel real.

## 5. Audio

- **DAC virtual:** cada muestra de salida a 48 kHz es el promedio del nivel PWM (0–250)
  en su intervalo (~20.6 ticks de ISR), lo que emula el filtro RC de la salida.
- Normalización `(nivel − 125) / 125` y un **filtro de DC** de un polo (~10 Hz), el
  capacitor de acople: saca el escalón de 0 → 128 del arranque y cualquier offset.
- Salida por **WASAPI en modo compartido, event-driven**, float 32 estéreo (mono
  duplicado). Latencia objetivo: ~30 ms de punta a punta.
- Si no hay dispositivo de audio, el simulador sigue corriendo (el pacing pasa a usar el
  reloj de pared) y lo avisa en la barra de estado.

## 6. Entrada

Un hilo de entrada lee `XInputGetState` a 500 Hz sobre el primer control conectado y
combina el resultado con el teclado (el hilo de UI mantiene su estado). El resultado es un
bitmask atómico de 12 botones que lee `gpio_get()`.

Para evitar el costo conocido de `XInputGetState` cuando no hay control conectado, se
reintenta la detección cada 1 s y no a 500 Hz.

| GamePi13 | XInput | Teclado |
|---|---|---|
| Up / Down / Left / Right | D-pad | flechas |
| X (arriba) | Y | W |
| A (derecha) | B | D |
| B (abajo) | A | S |
| Y (izquierda) | X | A |
| L | LB | Q |
| R | RB | E |
| Select | Back / View | Backspace |
| Start | Start / Menu | Enter |

El D-pad del control Xbox, igual que el NAV5, no permite Up+Down a la vez, así que el
remapeo del reset de FX (`Down+Right+B+A`) es accionable.

## 7. Ventana y modo headless

### Ventana (Win32 + GDI, 60 fps)

- Carcasa del GamePi13 dibujada, con cada botón que se ilumina mientras está apretado y
  el LED de beat (GP28).
- LCD escalado ×2 (480×480), nearest-neighbor.
- Barra de estado: control conectado o no, banco cargado (nombre y cantidad de samples),
  estado del audio.
- Drag & drop de `.pikobank` (`WM_DROPFILES`); también `pikocore_sim.exe banco.pikobank`.

### Modo headless (verificación y tests)

```
pikocore_sim.exe --headless --bank banco.pikobank --run-ms 5000 \
  --press "1000:A+B,1500:-A,2000:-B" --dump-lcd out.bmp --dump-wav out.wav
```

Sin ventana, sin dispositivo de audio y sin pacing. `--press` es una lista de eventos
`tiempo_ms:+BOTON` / `-BOTON`, con `+` implícito. `--dump-lcd` guarda la imagen visible al
final como BMP y `--dump-wav` guarda toda la salida de audio. Sirve para verificar
comportamiento sin hardware y como base de tests de regresión.

## 8. Estructura y build

```
sim/
  CMakeLists.txt          independiente del build del pico-sdk
  shim/                   headers falsos del pico-sdk + su implementación
  core/                   planificador (fibers), flash, emulador ST7789, DAC, input mask
  platform/               ventana Win32/GDI, WASAPI, XInput, teclado
  app/                    main del simulador, CLI, modo headless
  tests/                  unit tests (ST7789, DAC, parser de --press, carga de banco)
```

Build:

```
cmake -S sim -B build-sim -G "Visual Studio 17 2022" -A x64
cmake --build build-sim --config Release
```

Compilado con `/std:c++20` para C++ y C11 para las fuentes C. `PIKO_SIM=1` es el único
define nuevo que ve el código del firmware (usado solo por `PIKO_DMB()`).

## 9. Testing

- **Unit tests** (ejecutable `pikocore_sim_tests`, sin framework externo; asserts
  propios, registrado en CTest): emulador ST7789 (ventanas, auto-avance, MADCTL), DAC
  (promedio y filtro de DC), parser de `--press`, validación de `.pikobank`.
- **Tests de integración headless** con un banco de prueba sintético generado por el
  propio test:
  - arranque: el LCD muestra el dashboard y hay audio distinto de silencio;
  - Start (toque) → mute: el audio queda en silencio;
  - Select + botón musical → el modo cambia (verificado por el cuadrado resaltado del LCD).
- **Verificación manual** con el control real al final: los combos de GAMEPI13-INTERFACE.md
  uno por uno.

## 10. Riesgos

| Riesgo | Mitigación |
|---|---|
| MSVC no compila algún GCC-ismo del firmware | `/std:c++20`, macros en un header forzado (`/FI`) para `__attribute__` y afines; si algo exige tocar `src/`, se consulta antes. |
| ~1 M llamadas/s a la ISR más cambios de fiber ahogan un core | La ISR es liviana (medido en la primera iteración); los cambios de fiber son ~20 k/s. Si no alcanza, se agrupan ticks sin cambiar la semántica. |
| La orientación del LCD sale rotada o espejada | Se fija empíricamente con el dump BMP del modo headless antes de dibujar la ventana. |
