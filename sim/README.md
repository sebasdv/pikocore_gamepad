# pikocore-sim

Simulador para Windows del firmware de pikocore en GamePi13, controlado con un
control XInput (Xbox o compatible) o con el teclado. Compila **las mismas
fuentes** que van al RP2350 (`src/main.cpp`, `src/gamepi13/ui.cpp`, el driver
del LCD, `PikoAudioBank.cpp`) contra un shim del pico-sdk: el motor de audio,
los combos de botones y el dashboard son los del firmware, no una reescritura.

Diseño: [docs/superpowers/specs/2026-09-22-xinput-simulator-design.md](../docs/superpowers/specs/2026-09-22-xinput-simulator-design.md)

## Compilar

Requiere Visual Studio 2022 (C++ de escritorio) y CMake ≥ 3.20.

```
cmake -S sim -B build-sim -G "Visual Studio 17 2022" -A x64
cmake --build build-sim --config Release
ctest --test-dir build-sim -C Release
```

El ejecutable queda en `build-sim/bin/pikocore_sim.exe`.

## Usar

```
build-sim\bin\pikocore_sim.exe mi_banco.pikobank
```

Los bancos `.pikobank` se arman y se descargan con el loader web (`web/`).
También se pueden arrastrar a la ventana mientras corre. La flash simulada
(banco y lo guardado en el modo 6) persiste en `pikocore_sim_flash.bin`,
junto al `.exe`.

Para probar el simulador sin pasar por el loader web:
`build-sim\bin\pikocore_sim_itest.exe dump_bank prueba.pikobank` genera un
`.pikobank` sintético de 4 samples, que después se puede abrir con
`pikocore_sim.exe prueba.pikobank`.

| GamePi13 | Control Xbox | Teclado |
|---|---|---|
| Up / Down / Left / Right | D-pad | flechas |
| X (arriba) | Y | W |
| A (derecha) | B | D |
| B (abajo) | A | S |
| Y (izquierda) | X | A |
| L / R | LB / RB | Q / E |
| Select | Back (View) | Backspace |
| Start | Start (Menu) | Enter |

Los botones de cara van **por posición**, no por letra: el de arriba del
control es el de arriba del GamePi13. Qué hace cada control está en
[GAMEPI13-INTERFACE.md](../GAMEPI13-INTERFACE.md).

## Modo headless

Sin ventana ni audio y lo más rápido posible. Sirve para probar cambios del
firmware sin hardware:

```
pikocore_sim.exe --headless --bank b.pikobank --run-ms 8000 ^
  --press "6000:SELECT,6100:RIGHT,6200:-RIGHT,6300:-SELECT" ^
  --dump-lcd pantalla.bmp --dump-wav audio.wav
```

`--press` es una lista `ms:BOTON+BOTON` (apretar) / `ms:-BOTON` (soltar). El
firmware tarda ~4.5 s virtuales en arrancar (splash + espera de USB).
`pikocore_sim.exe --help` imprime la lista completa de opciones (sale con
código 0).

## Cómo funciona

- `sim/shim/sim_pico.h` reemplaza al pico-sdk. GPIO, PWM, SPI, flash y timer
  delegan en `sim/runtime/sim_hal.cpp`.
- `sim/runtime/machine.cpp` es un planificador determinista sobre un reloj
  virtual de 248 MHz: la ISR de audio corre cada 251 ciclos y el `main()` del
  firmware en una Fiber que cede el control en `__wfi()`, `sleep_*()` y cada
  lectura del timer. Los temporizadores del firmware (los que cuentan vueltas
  del lazo y los de `time_us_64()`) corren a la cadencia del hardware.
- El audio es el nivel PWM promediado por muestra (el filtro RC) más un
  filtro de DC, a 48 kHz por WASAPI. Si WASAPI no puede arrancar (por
  ejemplo, sin dispositivo de audio), la barra de estado muestra
  `Sin audio (<motivo>)` y el simulador sigue corriendo. Si el dispositivo se
  pierde a mitad de sesión, la barra pasa a mostrar `Audio perdido` y el
  ritmo de simulación se apoya en el reloj de pared en lugar del nivel del
  buffer de audio.
- El LCD es un emulador de ST7789 alimentado por el SPI real de
  `LCD_1in3.c`.

## Limitaciones

- No simula: modo 8 (SD, aparcado en el firmware), MIDI, clock externo, trigger
  out ni el protocolo USB del loader.
- La ISR nunca interrumpe a `main()` a mitad de una instrucción (en el RP2350
  sí puede); el cómputo de `main()` no consume tiempo virtual.
- `doth/easing.h` se compila desde una copia aplanada (`else if` → `if`,
  equivalente porque cada rama hace `return`) por el límite de anidamiento de
  MSVC.
- Al cargar un `.pikobank` exportado del loader web se corrige su campo
  `capacity_bytes` (el loader escribe 16 MB, más que la capacidad real). Ver
  la nota en `sim/core/bank_file.h`.
- Las transferencias SPI al LCD y el código del firmware no consumen tiempo
  virtual, así que redibujar la UI no frena el lazo de control como en el
  dispositivo (en el hardware un cuadro completo tarda ~90 ms a 10 MHz). La
  respuesta del simulador durante un redibujado es optimista.
- Si el dispositivo de audio se pierde a mitad de sesión, el simulador sigue
  corriendo sin audio (la barra muestra `Audio perdido`) hasta que se lo
  reinicia.
- Latencia botón → sonido: ~20 ms de emulación adelantada más el buffer de
  WASAPI.
