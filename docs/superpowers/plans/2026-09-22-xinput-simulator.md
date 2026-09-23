# pikocore-sim — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simulador nativo de Windows del firmware pikocore para GamePi13. Compila las fuentes reales del firmware contra un shim del pico-sdk y se toca con un control XInput, con audio (WASAPI) y el LCD emulado.

**Architecture:** El firmware (`src/main.cpp`, `ui.cpp`, driver del LCD, `PikoAudioBank.cpp`) se compila sin cambios de comportamiento contra `sim/shim/sim_pico.h`, un único header que reemplaza al pico-sdk y delega en funciones `sim_*`. Un planificador determinista (`runtime/machine.cpp`) corre el `main()` del firmware en una Fiber de Win32 y la ISR de audio cada 251 ciclos de un reloj virtual de 248 MHz. La ISR alimenta un DAC virtual, y el SPI del LCD alimenta un emulador de ST7789. El resto del simulador (entrada XInput/teclado, WASAPI, ventana GDI y modo headless) vive afuera, en `core/`, `platform/` y `app/`.

**Tech Stack:** C++20 / C11, MSVC 2022 (generador "Visual Studio 17 2022"), CMake ≥ 3.20, Win32 (Fibers, GDI, XInput 1.4, WASAPI), CTest. Sin dependencias externas.

**Spec:** [docs/superpowers/specs/2026-09-22-xinput-simulator-design.md](../specs/2026-09-22-xinput-simulator-design.md)

## Global Constraints

- Plataforma: Windows x64, MSVC 2022. Sin librerías de terceros.
- El firmware se compila tal cual. El único cambio permitido en `src/` es la macro `PIKO_DMB()` (Task 1), que genera el mismo código ARM.
- Defines del firmware en el simulador: `PIKO_GAMEPI13=1`, `PIKO_GAMEPI13_SD=0`, `PIKO_SIM=1`, `PIKO_FIRMWARE_RESERVE=524288u`, más las de `target_compile_definitions.cmake` (incluido, no copiado).
- Reloj virtual: 248 MHz (`CLOCK_RATE`); período PWM de 251 ciclos (`wrap=250`, `clkdiv=1`); salida de audio a 48 kHz.
- Botones de cara por posición: Xbox Y→X, B→A, A→B, X→Y. Resto: D-pad→D-pad, LB→L, RB→R, Back→Select, Start→Start. Teclado: flechas, W/D/S/A (X/A/B/Y), Q/E (L/R), Backspace (Select), Enter (Start).
- Flash persistente en `pikocore_sim_flash.bin` junto al `.exe` en modo ventana. En `--headless`, solo en memoria salvo que se pase `--flash`.
- Textos visibles para el usuario en español. Comentarios en español, como el código reciente del repo.
- El working tree tiene cambios del usuario sin commitear en `src/main.cpp`, `GAMEPI13-INTERFACE.md` y `build-gamepi/pikocore.uf2`. **Nunca** se stagean ni se commitean. Cada commit agrega rutas explícitas; nunca `git add -A` ni `git commit -a`.
- Build dir: `build-sim/` (gitignoreado). Ejecutables en `build-sim/bin/`.
- Todos los comandos corren desde `C:\pikocore-main` en Git Bash.

---

## Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `src/piko_barrier.h` | Macro `PIKO_DMB()`: `dmb` en ARM, fence de C++ en el simulador |
| `sim/CMakeLists.txt` | Targets: `piko_fw`, `sim_core`, `sim_runtime`, `pikocore_sim`, tests |
| `sim/cmake/flatten_easing.cmake` | Genera una copia de `doth/easing.h` sin cadenas `else if` (límite C1061 de MSVC) |
| `sim/shim/sim_pico.h` | Reemplazo de todo el pico-sdk que usa el firmware |
| `sim/shim/pico/*.h`, `sim/shim/hardware/*.h`, `sim/shim/tusb.h` | Reenvían a `sim_pico.h` |
| `sim/shim/onewiremidi.pio.h` | Sustituto del header que genera pioasm |
| `sim/core/st7789.{h,cpp}` | Emulador del controlador del LCD |
| `sim/core/pwm_dac.{h,cpp}` | Nivel PWM → muestras a 48 kHz (promedio + filtro de DC) |
| `sim/core/audio_ring.h` | Cola SPSC sin locks de la emulación a WASAPI |
| `sim/core/flash_store.{h,cpp}` | Flash NOR simulada con persistencia en archivo |
| `sim/core/bank_file.{h,cpp}` | Validación de `.pikobank` y corrección de `capacity_bytes` |
| `sim/core/buttons.{h,cpp}` | Enum de botones, pines, mapeo XInput/teclado/nombres |
| `sim/core/press_script.{h,cpp}` | Parser y aplicación de `--press` |
| `sim/core/file_io.{h,cpp}` | Leer archivos, escribir BMP y WAV |
| `sim/runtime/machine.{h,cpp}` | Planificador con Fibers: reloj virtual, ISR, `main()` del firmware |
| `sim/runtime/sim_hal.cpp` | Implementación de las funciones `sim_*` del shim |
| `sim/runtime/sim_io.h` | API C++ del estado de E/S (botones, LED, backlight, flash) |
| `sim/runtime/firmware_entry.h` | Declaración de `piko_firmware_main()` |
| `sim/runtime/firmware_glue.cpp` | Símbolos de core1/SD que el firmware referencia |
| `sim/runtime/bank_hotload.{h,cpp}` | Escribir un banco en flash; carga en caliente como el core1 real |
| `sim/runtime/headless.{h,cpp}` | Corrida sin ventana, base del CLI y de los tests de integración |
| `sim/platform/audio_out.{h,cpp}` | WASAPI |
| `sim/platform/pad_input.{h,cpp}` | Hilo de XInput y combinación con el teclado |
| `sim/platform/sim_window.{h,cpp}` | Ventana Win32/GDI |
| `sim/app/cli.{h,cpp}` | Parser de la línea de comandos |
| `sim/app/windowed.{h,cpp}` | Modo ventana: hilos, pacing, carga por drag & drop |
| `sim/app/main.cpp` | `wmain`: despacha a headless o ventana |
| `sim/tests/test.h`, `sim/tests/unit_main.cpp` | Mini framework de unit tests |
| `sim/tests/unit_*.cpp` | Unit tests del core |
| `sim/tests/synth_bank.{h,cpp}` | Banco `.pikobank` sintético para los tests |
| `sim/tests/itest_main.cpp` | Tests de integración (un escenario por proceso) |
| `sim/README.md` | Uso del simulador |

Comandos de build, usados en todas las tareas:

```bash
cmake -S sim -B build-sim -G "Visual Studio 17 2022" -A x64
cmake --build build-sim --config Release
```

---

### Task 1: `PIKO_DMB()` en el firmware

**Files:**
- Create: `src/piko_barrier.h`
- Modify: `src/main.cpp` (3 `__asm dmb`, + include), `src/PikoAudioBank.cpp` (1, + include), `src/PikoSampleManager.cpp` (3, + include)

**Interfaces:**
- Produces: macro `PIKO_DMB()` en `src/piko_barrier.h`. Con `PIKO_SIM` definido es `std::atomic_thread_fence(std::memory_order_seq_cst)`; si no, `__asm volatile("dmb" ::: "memory")`.

El test de esta tarea es que el código objeto ARM quede idéntico. Se compilan los tres `.cpp` con los mismos flags que `build-gamepi/`, sin tocar ese árbol de build, antes y después del cambio.

- [ ] **Step 1: Compilar la línea base ARM**

```bash
ARMCHK=$(mktemp -d)
arm_objs() {  # $1 = sufijo de salida
  local F=build-gamepi/CMakeFiles/pikocore.dir/flags.make
  local DEFS INCS FLAGS
  DEFS=$(sed -n 's/^CXX_DEFINES = //p' $F)
  INCS=$(sed -n 's/^CXX_INCLUDES = //p' $F | sed 's#\\#/#g')
  FLAGS=$(sed -n 's/^CXX_FLAGS = //p' $F)
  for f in main PikoAudioBank PikoSampleManager; do
    eval "\"/c/Program Files/DaisyToolchain/bin/arm-none-eabi-g++.exe\" $DEFS $INCS $FLAGS -c src/$f.cpp -o $ARMCHK/${f}_$1.o" || return 1
    "/c/Program Files/DaisyToolchain/bin/arm-none-eabi-objdump.exe" -d $ARMCHK/${f}_$1.o | tail -n +3 > $ARMCHK/${f}_$1.dis
  done
}
arm_objs base && ls $ARMCHK
```

Expected: seis archivos, `{main,PikoAudioBank,PikoSampleManager}_base.{o,dis}`, sin errores de compilación. (El shell tiene que ser el mismo en los Steps 1–4: `ARMCHK` y `arm_objs` se usan después.)

- [ ] **Step 2: Crear `src/piko_barrier.h`**

```c
#pragma once
// Barrera de memoria completa. En el RP2350 es la instrucción "dmb" de ARM; en
// el simulador de PC (sim/, PIKO_SIM=1) es un fence de C++, porque MSVC x64 no
// acepta asm inline. El código generado para ARM no cambia.
#if defined(PIKO_SIM)
#include <atomic>
#define PIKO_DMB() std::atomic_thread_fence(std::memory_order_seq_cst)
#else
#define PIKO_DMB() __asm volatile("dmb" ::: "memory")
#endif
```

- [ ] **Step 3: Reemplazar los `__asm` y agregar los includes**

```bash
piko_dmb_edit() {  # $1 = main.cpp, $2 = PikoAudioBank.cpp, $3 = PikoSampleManager.cpp
  sed -i '0,/^#include "PikoSampleManager.h"$/s//#include "PikoSampleManager.h"\n#include "piko_barrier.h"/' "$1"
  sed -i 's|^#include "hardware/flash.h"$|#include "hardware/flash.h"\n#include "piko_barrier.h"|' "$2" "$3"
  sed -i 's/__asm volatile("dmb" ::: "memory");/PIKO_DMB();/' "$1" "$2" "$3"
}
piko_dmb_edit src/main.cpp src/PikoAudioBank.cpp src/PikoSampleManager.cpp
grep -rn '__asm' src/main.cpp src/PikoAudioBank.cpp src/PikoSampleManager.cpp
grep -c 'PIKO_DMB();' src/main.cpp src/PikoAudioBank.cpp src/PikoSampleManager.cpp
grep -c '#include "piko_barrier.h"' src/main.cpp src/PikoAudioBank.cpp src/PikoSampleManager.cpp
```

Expected: el primer grep no imprime nada. El segundo, `src/main.cpp:3`, `src/PikoAudioBank.cpp:1`, `src/PikoSampleManager.cpp:3`. El tercero, `1` en los tres.

- [ ] **Step 4: Verificar que el código ARM es idéntico**

```bash
arm_objs new && for f in main PikoAudioBank PikoSampleManager; do cmp $ARMCHK/${f}_base.dis $ARMCHK/${f}_new.dis && echo "$f idéntico"; done
```

Expected: `main idéntico`, `PikoAudioBank idéntico`, `PikoSampleManager idéntico`. Si alguno difiere, parar e investigar. No seguir con un cambio que altere el firmware.

- [ ] **Step 5: Commitear solo el refactor, sin los cambios del usuario**

`src/main.cpp` tiene cambios del usuario sin commitear, así que se stagea `HEAD` + la misma edición en lugar del archivo del working tree.

```bash
STAGE=$(mktemp -d)
for f in main PikoAudioBank PikoSampleManager; do git show HEAD:src/$f.cpp > $STAGE/$f.cpp; done
piko_dmb_edit $STAGE/main.cpp $STAGE/PikoAudioBank.cpp $STAGE/PikoSampleManager.cpp
for f in main PikoAudioBank PikoSampleManager; do
  git update-index --cacheinfo 100644,$(git hash-object -w --path=src/$f.cpp $STAGE/$f.cpp),src/$f.cpp
done
git add src/piko_barrier.h
git diff --cached --stat
git diff --cached src/main.cpp | grep '^[-+]' | grep -v '^+++\|^---'
```

Expected: el `--stat` muestra 4 archivos. El diff de `main.cpp` tiene solo la línea `+#include "piko_barrier.h"` y tres pares `-  __asm volatile...` / `+  PIKO_DMB();` (o con la indentación que corresponda). No aparece nada del remapeo del reset de FX.

```bash
git commit -m "firmware: PIKO_DMB() en vez de asm dmb inline

Mismo código ARM (verificado comparando objdump antes/después); permite
compilar el firmware con MSVC para el simulador de PC (PIKO_SIM).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short src/
```

Expected: `M src/main.cpp` sigue apareciendo (son los cambios del usuario). `PikoAudioBank.cpp` y `PikoSampleManager.cpp` ya no aparecen.

---

### Task 2: Shim del pico-sdk y el firmware compilando con MSVC

**Files:**
- Create: `sim/CMakeLists.txt`, `sim/cmake/flatten_easing.cmake`, `sim/shim/sim_pico.h`, `sim/shim/onewiremidi.pio.h`, `sim/shim/tusb.h`, `sim/shim/pico/{stdlib,time,sync,multicore,binary_info}.h`, `sim/shim/hardware/{adc,clocks,flash,irq,pwm,sync,spi,gpio,pio}.h`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `PIKO_DMB()` (Task 1).
- Produces:
  - Target `piko_fw` (librería estática). Su include `PUBLIC` es `sim/shim`.
  - Funciones C que los tasks siguientes tienen que implementar (Task 7), declaradas en `sim_pico.h`:
    ```c
    extern uint8_t sim_flash_mem[];
    uint64_t sim_time_us(void);
    void sim_sleep_until_us(uint64_t t_us);
    void sim_wfi(void);
    bool sim_gpio_get(uint pin);
    void sim_gpio_put(uint pin, bool value);
    void sim_pwm_set_level(uint pin, uint16_t level);
    void sim_pwm_irq_enable(bool enabled);
    void sim_irq_set_handler(void (*handler)(void));
    void sim_irq_enable(bool enabled);
    void sim_spi_write(const uint8_t *src, size_t len);
    void sim_flash_erase(uint32_t offset, size_t count);
    void sim_flash_program(uint32_t offset, const uint8_t *data, size_t count);
    ```
  - `main()` del firmware renombrado a `int piko_firmware_main();` (C++).
  - Símbolos que el firmware referencia y que el simulador tiene que definir (Task 7): `piko_sample_manager_set_ready`, `piko_sample_manager_core`, `gamepi_sd_*` (7 variables y 2 funciones de `src/PikoSampleManager.h`).

El "test" de esta tarea es que el firmware compile. Sin el shim, o sin aplanar `easing.h`, MSVC falla: con `C1061` en `doth/easing.h:469` y con "no se encuentra hardware/adc.h".

- [ ] **Step 1: Crear `sim/cmake/flatten_easing.cmake`**

```cmake
# doth/easing.h (generado por doth/generate_easing.py) tiene cadenas "else if"
# de cientos de eslabones, y MSVC corta en 128 niveles de anidamiento (error
# C1061). Como cada rama termina en return, "} else if (" -> "}\n  if (" es
# semánticamente idéntico. Se genera una copia aplanada en el build; el
# original no se toca.
function(piko_flatten_easing src dst)
  file(READ "${src}" content)
  string(REPLACE "} else if (" "}\n  if (" content "${content}")
  string(FIND "${content}" "else" leftover)
  if(NOT leftover EQUAL -1)
    message(FATAL_ERROR "${src} tiene un 'else' que no es 'else if': aplanarlo ya no es seguro")
  endif()
  file(WRITE "${dst}.tmp" "${content}")
  configure_file("${dst}.tmp" "${dst}" COPYONLY)
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${src}")
endfunction()
```

- [ ] **Step 2: Crear `sim/shim/sim_pico.h`**

```c
#pragma once
// Shim único del pico-sdk para el simulador de PC. Cada header pico/... y
// hardware/... de este directorio solo incluye este. Implementa lo mínimo que
// usa el firmware; lo que toca "hardware" delega en las funciones sim_* de
// sim/runtime/sim_hal.cpp.
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef unsigned int uint;
typedef uint64_t absolute_time_t;

// ---- implementado en sim/runtime/sim_hal.cpp ----
extern uint8_t sim_flash_mem[];
uint64_t sim_time_us(void);
void sim_sleep_until_us(uint64_t t_us);
void sim_wfi(void);
bool sim_gpio_get(uint pin);
void sim_gpio_put(uint pin, bool value);
void sim_pwm_set_level(uint pin, uint16_t level);
void sim_pwm_irq_enable(bool enabled);
void sim_irq_set_handler(void (*handler)(void));
void sim_irq_enable(bool enabled);
void sim_spi_write(const uint8_t *src, size_t len);
void sim_flash_erase(uint32_t offset, size_t count);
void sim_flash_program(uint32_t offset, const uint8_t *data, size_t count);

// La flash XIP apunta al buffer simulado: flash_header() de PikoAudioBank.cpp y
// flash_target_contents de main.cpp leen de ahí.
#define XIP_BASE ((uintptr_t)sim_flash_mem)
#define FLASH_PAGE_SIZE (1u << 8)
#define FLASH_SECTOR_SIZE (1u << 12)
#define PICO_NO_HARDWARE 0
#define PICO_PIO_VERSION 0

// ---- tiempo ----
static inline uint64_t time_us_64(void) { return sim_time_us(); }
static inline uint32_t time_us_32(void) { return (uint32_t)sim_time_us(); }
static inline absolute_time_t get_absolute_time(void) { return sim_time_us(); }
static inline uint32_t to_ms_since_boot(absolute_time_t t) { return (uint32_t)(t / 1000u); }
static inline absolute_time_t make_timeout_time_ms(uint32_t ms) { return sim_time_us() + (uint64_t)ms * 1000u; }
static inline bool time_reached(absolute_time_t t) { return sim_time_us() >= t; }
static inline void sleep_us(uint64_t us) { sim_sleep_until_us(sim_time_us() + us); }
static inline void sleep_ms(uint32_t ms) { sleep_us((uint64_t)ms * 1000u); }
static inline void __wfi(void) { sim_wfi(); }
static inline uint32_t save_and_disable_interrupts(void) { return 0; }
static inline void restore_interrupts(uint32_t status) { (void)status; }
static inline bool set_sys_clock_khz(uint32_t khz, bool required) { (void)khz; (void)required; return true; }
enum clock_index { clk_sys = 5 };
static inline uint32_t clock_get_hz(enum clock_index clk) { (void)clk; return 248000000u; }
static inline bool stdio_init_all(void) { return true; }

// ---- gpio ----
enum gpio_function { GPIO_FUNC_SPI = 1, GPIO_FUNC_PWM = 4, GPIO_FUNC_SIO = 5, GPIO_FUNC_PIO0 = 6, GPIO_FUNC_PIO1 = 7 };
#define GPIO_OUT 1
#define GPIO_IN 0
static inline void gpio_init(uint pin) { (void)pin; }
static inline void gpio_set_dir(uint pin, bool out) { (void)pin; (void)out; }
static inline void gpio_pull_up(uint pin) { (void)pin; }
static inline void gpio_pull_down(uint pin) { (void)pin; }
static inline void gpio_set_function(uint pin, enum gpio_function fn) { (void)pin; (void)fn; }
static inline bool gpio_get(uint pin) { return sim_gpio_get(pin); }
static inline void gpio_put(uint pin, bool value) { sim_gpio_put(pin, value); }

// ---- irq (solo existe la del wrap del PWM de audio) ----
#define PWM_IRQ_WRAP 8
#define USBCTRL_IRQ 14
typedef void (*irq_handler_t)(void);
static inline void irq_set_priority(uint num, uint8_t p) { (void)num; (void)p; }
static inline void irq_set_exclusive_handler(uint num, irq_handler_t h) { if (num == PWM_IRQ_WRAP) sim_irq_set_handler(h); }
static inline void irq_set_enabled(uint num, bool en) { if (num == PWM_IRQ_WRAP) sim_irq_enable(en); }

// ---- pwm ----
typedef struct { uint32_t csr, div, top; } pwm_config;
static inline uint pwm_gpio_to_slice_num(uint pin) { return (pin >> 1u) & 7u; }
static inline void pwm_clear_irq(uint slice) { (void)slice; }
static inline void pwm_set_irq_enabled(uint slice, bool en) { (void)slice; sim_pwm_irq_enable(en); }
static inline pwm_config pwm_get_default_config(void) { pwm_config c = {0, 16, 0xffff}; return c; }
static inline void pwm_config_set_clkdiv(pwm_config *c, float div) { (void)c; (void)div; }
static inline void pwm_config_set_wrap(pwm_config *c, uint16_t wrap) { c->top = wrap; }
static inline void pwm_init(uint slice, pwm_config *c, bool start) { (void)slice; (void)c; (void)start; }
static inline void pwm_set_gpio_level(uint pin, uint16_t level) { sim_pwm_set_level(pin, level); }

// ---- spi ----
typedef struct spi_inst spi_inst_t;
#define spi0 ((spi_inst_t *)0)
#define spi1 ((spi_inst_t *)1)
static inline uint spi_init(spi_inst_t *spi, uint baud) { (void)spi; return baud; }
static inline uint spi_set_baudrate(spi_inst_t *spi, uint baud) { (void)spi; return baud; }
static inline int spi_write_blocking(spi_inst_t *spi, const uint8_t *src, size_t len) { (void)spi; sim_spi_write(src, len); return (int)len; }

// ---- flash ----
static inline void flash_range_erase(uint32_t off, size_t count) { sim_flash_erase(off, count); }
static inline void flash_range_program(uint32_t off, const uint8_t *data, size_t count) { sim_flash_program(off, data, count); }
static inline void flash_do_cmd(const uint8_t *tx, uint8_t *rx, size_t count) {
  // JEDEC ID de un chip de 16 MB: fabricante 0xEF, código de capacidad 24.
  (void)tx;
  memset(rx, 0, count);
  if (count >= 4) { rx[1] = 0xef; rx[2] = 0x40; rx[3] = 24; }
}

// ---- adc (el GamePi13 usa knobs virtuales) ----
static inline void adc_init(void) {}
static inline void adc_gpio_init(uint pin) { (void)pin; }
static inline void adc_select_input(uint input) { (void)input; }
static inline uint16_t adc_read(void) { return 0; }

// ---- sync / multicore: el firmware entero corre en un solo hilo ----
typedef struct { int unused; } mutex_t;
static inline void mutex_init(mutex_t *m) { (void)m; }
static inline void mutex_enter_blocking(mutex_t *m) { (void)m; }
static inline void mutex_exit(mutex_t *m) { (void)m; }
static inline void multicore_launch_core1(void (*entry)(void)) { (void)entry; }
static inline void multicore_lockout_victim_init(void) {}
static inline void multicore_lockout_start_blocking(void) {}
static inline void multicore_lockout_end_blocking(void) {}

// ---- pio (solo lo usa el receptor MIDI de un cable, que nunca recibe) ----
typedef struct pio_hw pio_hw_t;
typedef pio_hw_t *PIO;
#define pio0 ((PIO)0)
#define pio1 ((PIO)1)
typedef struct { uint32_t clkdiv, execctrl, shiftctrl, pinctrl; } pio_sm_config;
struct pio_program { const uint16_t *instructions; uint8_t length; int8_t origin; uint8_t pio_version; };
static inline uint pio_add_program(PIO pio, const struct pio_program *p) { (void)pio; (void)p; return 0; }
static inline pio_sm_config pio_get_default_sm_config(void) { pio_sm_config c = {0, 0, 0, 0}; return c; }
static inline void sm_config_set_wrap(pio_sm_config *c, uint t, uint w) { (void)c; (void)t; (void)w; }
static inline void sm_config_set_in_pins(pio_sm_config *c, uint p) { (void)c; (void)p; }
static inline void sm_config_set_set_pins(pio_sm_config *c, uint p, uint n) { (void)c; (void)p; (void)n; }
static inline void sm_config_set_in_shift(pio_sm_config *c, bool r, bool a, uint t) { (void)c; (void)r; (void)a; (void)t; }
static inline void pio_sm_set_consecutive_pindirs(PIO pio, uint sm, uint p, uint n, bool out) { (void)pio; (void)sm; (void)p; (void)n; (void)out; }
static inline void pio_sm_init(PIO pio, uint sm, uint off, const pio_sm_config *c) { (void)pio; (void)sm; (void)off; (void)c; }
static inline void pio_sm_set_clkdiv(PIO pio, uint sm, float div) { (void)pio; (void)sm; (void)div; }
static inline void pio_sm_set_enabled(PIO pio, uint sm, bool en) { (void)pio; (void)sm; (void)en; }
static inline bool pio_sm_is_rx_fifo_empty(PIO pio, uint sm) { (void)pio; (void)sm; return true; }
static inline uint32_t pio_sm_get(PIO pio, uint sm) { (void)pio; (void)sm; return 0; }

// ---- tinyusb (nunca hay host USB) ----
static inline bool tusb_init(void) { return true; }
static inline void tud_task(void) {}
static inline bool tud_mounted(void) { return false; }
static inline uint32_t tud_midi_n_stream_write(uint8_t itf, uint8_t cable, const uint8_t *buf, uint32_t n) { (void)itf; (void)cable; (void)buf; return n; }

#define bi_decl(x)

#ifdef __cplusplus
}
#endif
```

- [ ] **Step 3: Crear los headers que reenvían al shim y `onewiremidi.pio.h`**

```bash
mkdir -p sim/shim/pico sim/shim/hardware
for h in stdlib time sync multicore binary_info; do printf '#pragma once\n#include "../sim_pico.h"\n' > sim/shim/pico/$h.h; done
for h in adc clocks flash irq pwm sync spi gpio pio; do printf '#pragma once\n#include "../sim_pico.h"\n' > sim/shim/hardware/$h.h; done
printf '#pragma once\n#include "sim_pico.h"\n' > sim/shim/tusb.h
ls sim/shim sim/shim/pico sim/shim/hardware
```

Crear `sim/shim/onewiremidi.pio.h`:

```c
#pragma once
// Sustituto del header que pioasm genera a partir de doth/onewiremidi.pio
// (build-gamepi/onewiremidi.pio.h). El simulador no emula la recepción MIDI de
// un cable: el programa se "carga" pero nunca corre.
#include "hardware/pio.h"

#define midi_rx_wrap_target 0
#define midi_rx_wrap 7

static const uint16_t midi_rx_program_instructions[] = {
    0x2020, 0x20a0, 0xed27, 0xbd42, 0x4001, 0x0043, 0x8000, 0x0000};

static const struct pio_program midi_rx_program = {midi_rx_program_instructions, 8, -1, 1};

static inline pio_sm_config midi_rx_program_get_default_config(uint offset) {
  pio_sm_config c = pio_get_default_sm_config();
  sm_config_set_wrap(&c, offset + midi_rx_wrap_target, offset + midi_rx_wrap);
  return c;
}
```

- [ ] **Step 4: Crear `sim/CMakeLists.txt` con el target del firmware**

```cmake
cmake_minimum_required(VERSION 3.20)
project(pikocore_sim C CXX)

if(NOT MSVC)
  message(FATAL_ERROR "pikocore-sim se compila con MSVC (Visual Studio 2022)")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)
# $<0:> evita el subdirectorio por configuración: todo queda en build-sim/bin.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin/$<0:>)

set(PIKO_ROOT ${CMAKE_CURRENT_LIST_DIR}/..)
set(SIM_ROOT ${CMAKE_CURRENT_LIST_DIR})

include(${SIM_ROOT}/cmake/flatten_easing.cmake)
piko_flatten_easing(${PIKO_ROOT}/doth/easing.h ${CMAKE_BINARY_DIR}/gen/doth/easing.h)

# ---- el firmware real, compilado contra el shim ----
add_library(piko_fw STATIC
  ${PIKO_ROOT}/src/main.cpp
  ${PIKO_ROOT}/src/PikoAudioBank.cpp
  ${PIKO_ROOT}/src/gamepi13/ui.cpp
  ${PIKO_ROOT}/src/gamepi13/dev_shim.c
  ${PIKO_ROOT}/src/gamepi13/lcd/LCD_1in3.c
  ${PIKO_ROOT}/src/gamepi13/lcd/GUI_Paint.c
  ${PIKO_ROOT}/src/gamepi13/lcd/font12.c
  ${PIKO_ROOT}/src/gamepi13/lcd/font16.c
  ${PIKO_ROOT}/src/gamepi13/lcd/font20.c
  ${PIKO_ROOT}/src/gamepi13/lcd/font24.c
)
target_include_directories(piko_fw PUBLIC ${SIM_ROOT}/shim)
# gen/ va antes que la raíz del repo: "doth/easing.h" resuelve a la copia aplanada.
target_include_directories(piko_fw PRIVATE
  ${CMAKE_BINARY_DIR}/gen
  ${PIKO_ROOT}
  ${PIKO_ROOT}/src
  ${PIKO_ROOT}/src/gamepi13
  ${PIKO_ROOT}/src/gamepi13/lcd
)
# Mismas defines que el build del RP2350 (target_compile_definitions.cmake usa
# ${PROJECT_NAME} como target).
set(PIKO_SIM_PROJECT_NAME ${PROJECT_NAME})
set(PROJECT_NAME piko_fw)
include(${PIKO_ROOT}/target_compile_definitions.cmake)
set(PROJECT_NAME ${PIKO_SIM_PROJECT_NAME})
target_compile_definitions(piko_fw PRIVATE
  PIKO_GAMEPI13=1
  PIKO_GAMEPI13_SD=0
  PIKO_SIM=1
  PIKO_FIRMWARE_RESERVE=524288u
  _CRT_SECURE_NO_WARNINGS
)
# El main() del firmware no puede llamarse main: lo arranca el simulador.
set_source_files_properties(${PIKO_ROOT}/src/main.cpp PROPERTIES
  COMPILE_DEFINITIONS "main=piko_firmware_main")
# /W1: el firmware no es nuestro para limpiar warnings de MSVC. C4828: fonts.h
# tiene bytes latin-1.
target_compile_options(piko_fw PRIVATE /W1 /wd4828)
```

- [ ] **Step 5: Ignorar el build y la flash del simulador**

Agregar al final de `.gitignore`:

```
# Simulador de PC (sim/)
build-sim/
pikocore_sim_flash.bin
```

- [ ] **Step 6: Compilar el firmware**

```bash
cmake -S sim -B build-sim -G "Visual Studio 17 2022" -A x64 && cmake --build build-sim --config Release --target piko_fw 2>&1 | grep -E 'error|piko_fw.vcxproj ->'
grep -c 'else if' build-sim/gen/doth/easing.h
```

Expected: una sola línea, `piko_fw.vcxproj -> ...\piko_fw.lib`, y ninguna con `error`. El `grep -c` imprime `0`. Si aparece `C1061`, el include de `gen/` no está quedando primero.

- [ ] **Step 7: Commit**

```bash
git add sim/CMakeLists.txt sim/cmake sim/shim .gitignore
git commit -m "sim: shim del pico-sdk; el firmware GamePi13 compila con MSVC

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Framework de tests y emulador de ST7789

**Files:**
- Create: `sim/tests/test.h`, `sim/tests/unit_main.cpp`, `sim/core/st7789.h`, `sim/core/st7789.cpp`, `sim/tests/unit_st7789.cpp`
- Modify: `sim/CMakeLists.txt` (agregar `sim_core` y `pikocore_sim_tests`)

**Interfaces:**
- Produces:
  - `TEST(name)`, `CHECK(cond)`, `CHECK_EQ(a, b)` para enteros, en `tests/test.h`.
  - `class sim::St7789 { static constexpr int kSize = 240; void set_dc(bool data); void set_cs(bool level); void write(const uint8_t*, size_t); uint16_t raw(int col, int row) const; void snapshot_view(uint16_t* out) const; uint32_t pixels_written() const; }`. `set_cs` recibe el nivel del pin (activo en bajo). `snapshot_view` escribe 240×240 RGB565 tal como se ve el GamePi13.
  - Target `sim_core` (include `PUBLIC`: `sim/` y `src/`) y target `pikocore_sim_tests`.

La transformación de la vista viene del código, no es empírica: `ui.cpp` dibuja con `GUI_Paint` en `ROTATE_270` (memoria X = y lógica, memoria Y = 239 − x lógica), y `flush()` → `LCD_1IN3_DisplayWindows()` copia la memoria al espacio de direcciones (columna = X de memoria, fila = Y de memoria). Por eso vista(lx, ly) = raw(col = ly, row = 239 − lx). En el hardware, panel + MADCTL + montaje muestran esa imagen lógica derecha. Por eso no se modela MADCTL.

- [ ] **Step 1: Crear el mini framework (`sim/tests/test.h` y `sim/tests/unit_main.cpp`)**

`sim/tests/test.h`:

```cpp
#pragma once
// Mini framework de unit tests: sin dependencias externas.
#include <cstdio>
#include <vector>

namespace simtest {
struct Case {
  const char* name;
  void (*fn)();
};
std::vector<Case>& registry();
extern int g_failures;
struct Registrar {
  Registrar(const char* name, void (*fn)()) { registry().push_back({name, fn}); }
};
}  // namespace simtest

#define TEST(name)                                         \
  static void name();                                      \
  static simtest::Registrar name##_registrar(#name, name); \
  static void name()

#define CHECK(cond)                                                           \
  do {                                                                        \
    if (!(cond)) {                                                            \
      std::printf("  FALLO %s:%d: %s\n", __FILE__, __LINE__, #cond);          \
      ++simtest::g_failures;                                                  \
    }                                                                         \
  } while (0)

// Solo para enteros (imprime ambos valores como long long).
#define CHECK_EQ(a, b)                                                         \
  do {                                                                         \
    const long long va_ = static_cast<long long>(a);                           \
    const long long vb_ = static_cast<long long>(b);                           \
    if (va_ != vb_) {                                                          \
      std::printf("  FALLO %s:%d: %s == %s (%lld vs %lld)\n", __FILE__,        \
                  __LINE__, #a, #b, va_, vb_);                                 \
      ++simtest::g_failures;                                                   \
    }                                                                          \
  } while (0)
```

`sim/tests/unit_main.cpp`:

```cpp
#include <cstdio>
#include <cstring>

#include "test.h"

namespace simtest {
std::vector<Case>& registry() {
  static std::vector<Case> cases;
  return cases;
}
int g_failures = 0;
}  // namespace simtest

// Uso: pikocore_sim_tests [filtro]  -- corre los tests cuyo nombre contiene filtro.
int main(int argc, char** argv) {
  const char* filter = argc > 1 ? argv[1] : nullptr;
  int run = 0;
  for (const simtest::Case& c : simtest::registry()) {
    if (filter != nullptr && std::strstr(c.name, filter) == nullptr) continue;
    const int before = simtest::g_failures;
    c.fn();
    ++run;
    std::printf("%s %s\n", simtest::g_failures == before ? "ok  " : "FAIL", c.name);
  }
  std::printf("%d tests, %d fallas\n", run, simtest::g_failures);
  return simtest::g_failures == 0 ? 0 : 1;
}
```

- [ ] **Step 2: Escribir los tests del ST7789 (`sim/tests/unit_st7789.cpp`)**

```cpp
#include <initializer_list>
#include <vector>

#include "core/st7789.h"
#include "test.h"

using sim::St7789;

namespace {
// Igual que LCD_1IN3_SendCommand/SendData: DC en bajo = comando, CS en bajo.
void cmd(St7789& lcd, uint8_t c, std::initializer_list<uint8_t> params) {
  lcd.set_cs(false);
  lcd.set_dc(false);
  lcd.write(&c, 1);
  lcd.set_dc(true);
  for (uint8_t p : params) lcd.write(&p, 1);
  lcd.set_cs(true);
}

void window(St7789& lcd, uint16_t x0, uint16_t x1, uint16_t y0, uint16_t y1) {
  cmd(lcd, 0x2A, {uint8_t(x0 >> 8), uint8_t(x0), uint8_t(x1 >> 8), uint8_t(x1)});
  cmd(lcd, 0x2B, {uint8_t(y0 >> 8), uint8_t(y0), uint8_t(y1 >> 8), uint8_t(y1)});
}

void pixels(St7789& lcd, std::initializer_list<uint16_t> px) {
  const uint8_t ramwr = 0x2C;
  lcd.set_cs(false);
  lcd.set_dc(false);
  lcd.write(&ramwr, 1);
  lcd.set_dc(true);
  for (uint16_t p : px) {
    const uint8_t b[2] = {uint8_t(p >> 8), uint8_t(p)};
    lcd.write(b, 2);
  }
  lcd.set_cs(true);
}
}  // namespace

TEST(st7789_writes_window_row_major) {
  St7789 lcd;
  window(lcd, 10, 11, 20, 21);
  pixels(lcd, {0x1234, 0x5678, 0x9abc, 0xdef0});
  CHECK_EQ(lcd.raw(10, 20), 0x1234);
  CHECK_EQ(lcd.raw(11, 20), 0x5678);
  CHECK_EQ(lcd.raw(10, 21), 0x9abc);
  CHECK_EQ(lcd.raw(11, 21), 0xdef0);
  CHECK_EQ(lcd.pixels_written(), 4);
}

TEST(st7789_wraps_to_window_start) {
  St7789 lcd;
  window(lcd, 10, 11, 20, 21);
  pixels(lcd, {1, 2, 3, 4, 0x1111});
  CHECK_EQ(lcd.raw(10, 20), 0x1111);
  CHECK_EQ(lcd.raw(11, 20), 2);
}

TEST(st7789_ignores_bytes_with_cs_high) {
  St7789 lcd;
  window(lcd, 0, 0, 0, 0);
  lcd.set_cs(true);
  lcd.set_dc(false);
  const uint8_t ramwr = 0x2C;
  lcd.write(&ramwr, 1);
  lcd.set_dc(true);
  const uint8_t b[2] = {0xff, 0xff};
  lcd.write(b, 2);
  CHECK_EQ(lcd.raw(0, 0), 0);
  CHECK_EQ(lcd.pixels_written(), 0);
}

TEST(st7789_other_commands_keep_window) {
  St7789 lcd;
  window(lcd, 5, 5, 6, 6);
  cmd(lcd, 0x36, {0x70});
  cmd(lcd, 0x3A, {0x05});
  pixels(lcd, {0xabcd});
  CHECK_EQ(lcd.raw(5, 6), 0xabcd);
}

TEST(st7789_view_undoes_rotate_270) {
  St7789 lcd;
  // Píxel lógico (x=7, y=5) -> memoria/direcciones (col=5, fila=239-7=232).
  window(lcd, 5, 5, 232, 232);
  pixels(lcd, {0x0f0f});
  std::vector<uint16_t> view(St7789::kSize * St7789::kSize);
  lcd.snapshot_view(view.data());
  CHECK_EQ(view[5 * St7789::kSize + 7], 0x0f0f);
}
```

- [ ] **Step 3: Registrar los targets en `sim/CMakeLists.txt`**

Agregar al final:

```cmake
# ---- núcleo del simulador (sin firmware ni Win32; testeable aislado) ----
add_library(sim_core STATIC
  core/st7789.cpp
)
target_include_directories(sim_core PUBLIC ${SIM_ROOT} ${PIKO_ROOT}/src)
target_compile_options(sim_core PRIVATE /W4 /utf-8)

enable_testing()
add_executable(pikocore_sim_tests
  tests/unit_main.cpp
  tests/unit_st7789.cpp
)
target_link_libraries(pikocore_sim_tests PRIVATE sim_core)
target_compile_options(pikocore_sim_tests PRIVATE /W4 /utf-8)
add_test(NAME unit COMMAND pikocore_sim_tests)
```

- [ ] **Step 4: Verificar que falla**

```bash
cmake -S sim -B build-sim > /dev/null; cmake --build build-sim --config Release --target pikocore_sim_tests 2>&1 | grep -E 'error' | head -3
```

Expected: error. Al configurar falta `core/st7789.cpp`; si no, al compilar falta `core/st7789.h`.

- [ ] **Step 5: Implementar `sim/core/st7789.h`**

```cpp
#pragma once
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <vector>

namespace sim {

// Emulador mínimo del controlador ST7789 del LCD 1.3" del GamePi13. Recibe los
// bytes de SPI tal como los manda src/gamepi13/lcd/LCD_1in3.c (DC en bajo =
// comando, en alto = dato; solo con CS en bajo) y arma la GRAM en espacio de
// direcciones: columna = CASET, fila = RASET. Solo modela CASET, RASET y
// RAMWR; el resto de los comandos se ignora.
// Thread-safe: la emulación escribe y la ventana lee desde otro hilo.
class St7789 {
 public:
  static constexpr int kSize = 240;

  St7789();
  void set_dc(bool data);
  void set_cs(bool level);  // nivel del pin; activo en bajo
  void write(const uint8_t* bytes, size_t len);

  // Píxel RGB565 en espacio de direcciones del controlador.
  uint16_t raw(int col, int row) const;
  // Imagen tal como se ve en el GamePi13: 240x240, fila por fila. ui.cpp
  // dibuja en ROTATE_270 y flush() copia su memoria al espacio de direcciones,
  // así que vista(x, y) = raw(col = y, fila = 239 - x).
  void snapshot_view(uint16_t* out) const;
  uint32_t pixels_written() const;

 private:
  static constexpr uint8_t kCaSet = 0x2A;
  static constexpr uint8_t kRaSet = 0x2B;
  static constexpr uint8_t kRamWr = 0x2C;

  void command(uint8_t cmd);
  void data(uint8_t value);
  void set_range(uint16_t* start, uint16_t* end, uint8_t value);
  void store_pixel(uint16_t pixel);

  mutable std::mutex mutex_;
  std::vector<uint16_t> gram_;
  bool dc_ = false;
  bool cs_low_ = false;
  uint8_t cmd_ = 0;
  int param_ = 0;
  uint16_t xs_ = 0, xe_ = kSize - 1, ys_ = 0, ye_ = kSize - 1;
  uint16_t x_ = 0, y_ = 0;
  bool have_high_ = false;
  uint8_t high_ = 0;
  uint32_t pixels_written_ = 0;
};

}  // namespace sim
```

- [ ] **Step 6: Implementar `sim/core/st7789.cpp`**

```cpp
#include "core/st7789.h"

namespace sim {

St7789::St7789() : gram_(static_cast<size_t>(kSize) * kSize, 0) {}

void St7789::set_dc(bool data) {
  std::lock_guard<std::mutex> lock(mutex_);
  dc_ = data;
}

void St7789::set_cs(bool level) {
  std::lock_guard<std::mutex> lock(mutex_);
  cs_low_ = !level;
}

void St7789::write(const uint8_t* bytes, size_t len) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!cs_low_) return;
  for (size_t i = 0; i < len; ++i) {
    if (dc_) {
      data(bytes[i]);
    } else {
      command(bytes[i]);
    }
  }
}

void St7789::command(uint8_t cmd) {
  cmd_ = cmd;
  param_ = 0;
  if (cmd == kRamWr) {
    x_ = xs_;
    y_ = ys_;
    have_high_ = false;
  }
}

void St7789::data(uint8_t value) {
  switch (cmd_) {
    case kCaSet:
      set_range(&xs_, &xe_, value);
      break;
    case kRaSet:
      set_range(&ys_, &ye_, value);
      break;
    case kRamWr:
      // RGB565 big-endian: primero el byte alto.
      if (!have_high_) {
        high_ = value;
        have_high_ = true;
        return;
      }
      have_high_ = false;
      store_pixel(static_cast<uint16_t>((high_ << 8) | value));
      break;
    default:
      break;
  }
}

void St7789::set_range(uint16_t* start, uint16_t* end, uint8_t value) {
  switch (param_++) {
    case 0: *start = static_cast<uint16_t>(value << 8); break;
    case 1: *start = static_cast<uint16_t>(*start | value); break;
    case 2: *end = static_cast<uint16_t>(value << 8); break;
    case 3: *end = static_cast<uint16_t>(*end | value); break;
    default: break;
  }
}

void St7789::store_pixel(uint16_t pixel) {
  // La GRAM real es de 240x320; lo que cae fuera del panel de 240x240 no se ve.
  if (x_ < kSize && y_ < kSize) gram_[static_cast<size_t>(y_) * kSize + x_] = pixel;
  ++pixels_written_;
  if (x_ >= xe_) {
    x_ = xs_;
    y_ = (y_ >= ye_) ? ys_ : static_cast<uint16_t>(y_ + 1);
  } else {
    ++x_;
  }
}

uint16_t St7789::raw(int col, int row) const {
  std::lock_guard<std::mutex> lock(mutex_);
  if (col < 0 || row < 0 || col >= kSize || row >= kSize) return 0;
  return gram_[static_cast<size_t>(row) * kSize + col];
}

void St7789::snapshot_view(uint16_t* out) const {
  std::lock_guard<std::mutex> lock(mutex_);
  for (int y = 0; y < kSize; ++y) {
    for (int x = 0; x < kSize; ++x) {
      out[static_cast<size_t>(y) * kSize + x] =
          gram_[static_cast<size_t>(kSize - 1 - x) * kSize + y];
    }
  }
}

uint32_t St7789::pixels_written() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return pixels_written_;
}

}  // namespace sim
```

- [ ] **Step 7: Correr los tests**

```bash
cmake --build build-sim --config Release --target pikocore_sim_tests 2>&1 | grep -E ' error ' ; build-sim/bin/pikocore_sim_tests.exe
```

Expected: 5 líneas `ok   st7789_...` y al final `5 tests, 0 fallas`.

- [ ] **Step 8: Commit**

```bash
git add sim/CMakeLists.txt sim/tests/test.h sim/tests/unit_main.cpp sim/tests/unit_st7789.cpp sim/core/st7789.h sim/core/st7789.cpp
git commit -m "sim: emulador de ST7789 y framework de unit tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: DAC virtual y ring de audio

**Files:**
- Create: `sim/core/pwm_dac.h`, `sim/core/pwm_dac.cpp`, `sim/core/audio_ring.h`, `sim/tests/unit_audio.cpp`
- Modify: `sim/CMakeLists.txt`

**Interfaces:**
- Produces:
  - `class sim::PwmDac { PwmDac(uint64_t cpu_hz, uint32_t period_cycles, uint32_t out_rate); void set_sink(std::function<void(float)>); void tick(uint16_t level); uint32_t out_rate() const; }`. `tick()` se llama una vez por período de PWM. El nivel va de 0 a `period_cycles`, que es el duty sobre `wrap+1`.
  - `class sim::AudioRing { explicit AudioRing(size_t capacity); bool push(float); size_t pop(float* out, size_t n); size_t size() const; }`. Es SPSC y header-only.

- [ ] **Step 1: Escribir los tests (`sim/tests/unit_audio.cpp`)**

```cpp
#include <cmath>
#include <cstdint>
#include <vector>

#include "core/audio_ring.h"
#include "core/pwm_dac.h"
#include "test.h"

using sim::AudioRing;
using sim::PwmDac;

namespace {
constexpr uint64_t kCpuHz = 248000000;
constexpr uint32_t kPeriod = 251;
constexpr uint32_t kTicksPerSecond = 988047;  // 248 MHz / 251
}  // namespace

TEST(dac_emits_out_rate_samples_per_second) {
  PwmDac dac(kCpuHz, kPeriod, 48000);
  uint32_t n = 0;
  dac.set_sink([&](float) { ++n; });
  for (uint32_t i = 0; i < kTicksPerSecond; ++i) dac.tick(125);
  CHECK(n >= 47999 && n <= 48000);
}

TEST(dac_blocks_dc) {
  PwmDac dac(kCpuHz, kPeriod, 48000);
  std::vector<float> out;
  dac.set_sink([&](float s) { out.push_back(s); });
  for (uint32_t i = 0; i < kTicksPerSecond; ++i) dac.tick(200);
  CHECK(!out.empty());
  CHECK(std::fabs(out.front()) < 1e-6f);
  CHECK(std::fabs(out.back()) < 1e-3f);
}

TEST(dac_step_up_gives_positive_transient) {
  PwmDac dac(kCpuHz, kPeriod, 48000);
  std::vector<float> out;
  dac.set_sink([&](float s) { out.push_back(s); });
  for (uint32_t i = 0; i < kTicksPerSecond / 2; ++i) dac.tick(125);
  const size_t mark = out.size();
  for (uint32_t i = 0; i < 100; ++i) dac.tick(250);
  CHECK(out.size() > mark + 1);
  CHECK(out[mark + 1] > 0.4f);
}

TEST(ring_keeps_order) {
  AudioRing ring(8);
  CHECK(ring.push(1.0f));
  CHECK(ring.push(2.0f));
  CHECK(ring.push(3.0f));
  float out[3] = {};
  CHECK_EQ(ring.pop(out, 3), 3);
  CHECK(out[0] == 1.0f && out[1] == 2.0f && out[2] == 3.0f);
  CHECK_EQ(ring.size(), 0);
}

TEST(ring_rejects_when_full) {
  AudioRing ring(4);
  for (int i = 0; i < 4; ++i) CHECK(ring.push(float(i)));
  CHECK(!ring.push(9.0f));
  float out[10] = {};
  CHECK_EQ(ring.pop(out, 10), 4);
  CHECK(ring.push(9.0f));
}
```

- [ ] **Step 2: Registrar en CMake y verificar que falla**

En `sim/CMakeLists.txt`, agregar `core/pwm_dac.cpp` a `add_library(sim_core ...)` y `tests/unit_audio.cpp` a `add_executable(pikocore_sim_tests ...)`.

```bash
cmake -S sim -B build-sim > /dev/null; cmake --build build-sim --config Release --target pikocore_sim_tests 2>&1 | grep -E 'error' | head -3
```

Expected: error. Faltan `core/pwm_dac.cpp` o `core/audio_ring.h`.

- [ ] **Step 3: Implementar `sim/core/audio_ring.h`**

```cpp
#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace sim {

// Cola sin locks de un productor (hilo de emulación) y un consumidor (WASAPI).
class AudioRing {
 public:
  explicit AudioRing(size_t capacity) : buf_(capacity) {}

  bool push(float value) {
    const uint64_t w = write_.load(std::memory_order_relaxed);
    if (w - read_.load(std::memory_order_acquire) >= buf_.size()) return false;
    buf_[w % buf_.size()] = value;
    write_.store(w + 1, std::memory_order_release);
    return true;
  }

  size_t pop(float* out, size_t n) {
    const uint64_t r = read_.load(std::memory_order_relaxed);
    const uint64_t avail = write_.load(std::memory_order_acquire) - r;
    const size_t k = static_cast<size_t>(avail < n ? avail : n);
    for (size_t i = 0; i < k; ++i) out[i] = buf_[(r + i) % buf_.size()];
    read_.store(r + k, std::memory_order_release);
    return k;
  }

  size_t size() const { return static_cast<size_t>(write_.load() - read_.load()); }

 private:
  std::vector<float> buf_;
  std::atomic<uint64_t> write_{0};
  std::atomic<uint64_t> read_{0};
};

}  // namespace sim
```

- [ ] **Step 4: Implementar `sim/core/pwm_dac.h` y `sim/core/pwm_dac.cpp`**

`sim/core/pwm_dac.h`:

```cpp
#pragma once
#include <cstdint>
#include <functional>

namespace sim {

// DAC virtual de la salida PWM de audio. El nivel del PWM se promedia en cada
// intervalo de muestra de salida, que es lo que hace el filtro RC del
// hardware, y pasa por un pasa-altos de un polo a ~10 Hz (el capacitor de
// acople), que saca el offset y el escalón del arranque.
class PwmDac {
 public:
  PwmDac(uint64_t cpu_hz, uint32_t period_cycles, uint32_t out_rate);
  void set_sink(std::function<void(float)> sink) { sink_ = std::move(sink); }
  // Pasó un período de PWM con este nivel (0..period_cycles = duty 0..100%).
  void tick(uint16_t level);
  uint32_t out_rate() const { return out_rate_; }

 private:
  uint64_t cpu_hz_;
  uint32_t period_cycles_;
  uint32_t out_rate_;
  uint64_t phase_ = 0;
  uint64_t sum_ = 0;
  uint32_t count_ = 0;
  bool primed_ = false;
  float prev_x_ = 0.0f;
  float prev_y_ = 0.0f;
  float r_;
  std::function<void(float)> sink_;
};

}  // namespace sim
```

`sim/core/pwm_dac.cpp`:

```cpp
#include "core/pwm_dac.h"

#include <algorithm>

namespace sim {

namespace {
constexpr float kDcCutoffHz = 10.0f;
constexpr float kGain = 0.9f;
constexpr float kPi = 3.14159265f;
}  // namespace

PwmDac::PwmDac(uint64_t cpu_hz, uint32_t period_cycles, uint32_t out_rate)
    : cpu_hz_(cpu_hz),
      period_cycles_(period_cycles),
      out_rate_(out_rate),
      r_(1.0f - 2.0f * kPi * kDcCutoffHz / static_cast<float>(out_rate)) {}

void PwmDac::tick(uint16_t level) {
  sum_ += std::min<uint32_t>(level, period_cycles_);
  ++count_;
  phase_ += static_cast<uint64_t>(period_cycles_) * out_rate_;
  if (phase_ < cpu_hz_) return;
  phase_ -= cpu_hz_;

  const float duty = static_cast<float>(sum_) /
                     (static_cast<float>(count_) * static_cast<float>(period_cycles_));
  sum_ = 0;
  count_ = 0;
  const float x = duty * 2.0f - 1.0f;
  if (!primed_) {
    // Arrancar el filtro en el primer valor evita un "pop" inicial.
    prev_x_ = x;
    primed_ = true;
  }
  const float y = x - prev_x_ + r_ * prev_y_;
  prev_x_ = x;
  prev_y_ = y;
  if (sink_) sink_(y * kGain);
}

}  // namespace sim
```

- [ ] **Step 5: Correr los tests**

```bash
cmake --build build-sim --config Release --target pikocore_sim_tests 2>&1 | grep -E ' error ' ; build-sim/bin/pikocore_sim_tests.exe
```

Expected: `10 tests, 0 fallas`.

- [ ] **Step 6: Commit**

```bash
git add sim/CMakeLists.txt sim/core/pwm_dac.h sim/core/pwm_dac.cpp sim/core/audio_ring.h sim/tests/unit_audio.cpp
git commit -m "sim: DAC virtual del PWM de audio y ring SPSC

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Flash simulada y validación de `.pikobank`

**Files:**
- Create: `sim/core/flash_store.h`, `sim/core/flash_store.cpp`, `sim/core/bank_file.h`, `sim/core/bank_file.cpp`, `sim/tests/synth_bank.h`, `sim/tests/synth_bank.cpp`, `sim/tests/unit_flash_bank.cpp`
- Modify: `sim/CMakeLists.txt`

**Interfaces:**
- Consumes: `src/PikoAudioBank.h`: `PikoBankHeader`, `PikoBankSampleRecord` y las constantes `PIKO_BANK_*`, `PIKO_COMPILED_FLASH_TOTAL_BYTES` y `PIKO_AUDIO_FLASH_OFFSET`.
- Produces:
  - `class sim::FlashStore { FlashStore(uint8_t* mem, size_t size); bool open(const std::filesystem::path&, std::string* err); void erase(uint32_t offset, size_t count); void program(uint32_t offset, const uint8_t* data, size_t count); size_t size() const; }`. Con un path vacío la flash vive solo en memoria.
  - `struct sim::BankCheck { bool ok; std::string error; uint32_t sample_count; bool capacity_patched; };`
  - `uint32_t sim::device_audio_capacity();`
  - `sim::BankCheck sim::check_and_patch_bank(std::vector<uint8_t>& blob);`
  - `std::vector<uint8_t> make_synth_bank(uint32_t count);` en `tests/synth_bank.h`. Namespace global, solo para tests.

**Por qué se corrige `capacity_bytes`:** el botón de descarga del loader web (`web/src/App.tsx:486`, `SD_BANK_CAPACITY_BYTES = 16 MB`) escribe 16 MB en ese campo. Ese valor supera la capacidad real (16 MB − 512 KB − 12 KB), así que `piko_audio_bank_rescan()` rechazaría el banco. Lo mismo le pasaría a `validate_header()` en el modo SD del firmware, que hoy está aparcado.

- [ ] **Step 1: Crear el banco sintético (`sim/tests/synth_bank.h` y `.cpp`)**

`sim/tests/synth_bank.h`:

```cpp
#pragma once
#include <cstdint>
#include <vector>

// Banco .pikobank sintético para los tests: `count` samples de 4 beats a 120
// BPM (48000 frames a 24 kHz). Cada beat es un golpe senoidal que decae, con
// una frecuencia distinta por sample. PCM de 8 bits sin signo, centro 128.
std::vector<uint8_t> make_synth_bank(uint32_t count);
```

`sim/tests/synth_bank.cpp`:

```cpp
#include "synth_bank.h"

#include <cmath>
#include <cstdio>
#include <cstring>

#include "PikoAudioBank.h"
#include "core/bank_file.h"

std::vector<uint8_t> make_synth_bank(uint32_t count) {
  constexpr uint32_t kFrames = 48000;
  constexpr uint32_t kBeatFrames = 12000;
  std::vector<uint8_t> blob(PIKO_BANK_HEADER_SIZE + count * kFrames, 0xff);

  PikoBankHeader h;
  std::memset(&h, 0xff, sizeof(h));
  h.magic = PIKO_BANK_MAGIC;
  h.version = PIKO_BANK_VERSION;
  h.header_size = PIKO_BANK_HEADER_SIZE;
  h.sample_rate = PIKO_BANK_SAMPLE_RATE;
  h.sample_count = count;
  h.audio_bytes = count * kFrames;
  h.capacity_bytes = sim::device_audio_capacity();
  h.reserved0 = 0;
  for (uint32_t i = 0; i < count; ++i) {
    PikoBankSampleRecord& s = h.samples[i];
    std::memset(&s, 0, sizeof(s));
    s.offset = i * kFrames;
    s.frame_count = kFrames;
    s.source_bpm = 120;
    s.beat_count = 4;
    s.peak = 228;
    std::snprintf(s.name, sizeof(s.name), "synth_%u", i + 1);
    const double freq = 110.0 * (i + 1);
    for (uint32_t f = 0; f < kFrames; ++f) {
      const double t = (f % kBeatFrames) / 24000.0;
      const double v = std::sin(2.0 * 3.14159265358979 * freq * t) * std::exp(-t * 6.0);
      blob[PIKO_BANK_HEADER_SIZE + s.offset + f] = static_cast<uint8_t>(128.0 + 100.0 * v);
    }
  }
  std::memcpy(blob.data(), &h, sizeof(h));
  return blob;
}
```

- [ ] **Step 2: Escribir los tests (`sim/tests/unit_flash_bank.cpp`)**

```cpp
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <vector>

#include "core/bank_file.h"
#include "core/flash_store.h"
#include "synth_bank.h"
#include "test.h"

using sim::FlashStore;

namespace {
constexpr size_t kSize = 65536;
}

TEST(flash_memory_only_starts_erased) {
  std::vector<uint8_t> mem(kSize, 0);
  FlashStore f(mem.data(), mem.size());
  std::string err;
  CHECK(f.open({}, &err));
  CHECK_EQ(mem[0], 0xff);
  CHECK_EQ(mem[kSize - 1], 0xff);
}

TEST(flash_program_ands_and_erase_resets) {
  std::vector<uint8_t> mem(kSize, 0);
  FlashStore f(mem.data(), mem.size());
  std::string err;
  CHECK(f.open({}, &err));
  const uint8_t a = 0x0f, b = 0xf0;
  f.program(10, &a, 1);
  CHECK_EQ(mem[10], 0x0f);
  f.program(10, &b, 1);
  CHECK_EQ(mem[10], 0x00);
  f.erase(0, 4096);
  CHECK_EQ(mem[10], 0xff);
}

TEST(flash_out_of_range_is_clamped) {
  std::vector<uint8_t> mem(kSize, 0);
  FlashStore f(mem.data(), mem.size());
  std::string err;
  CHECK(f.open({}, &err));
  f.erase(kSize, 10);  // no debe romper nada
  const uint8_t zeros[4] = {0, 0, 0, 0};
  f.program(kSize - 2, zeros, 4);
  CHECK_EQ(mem[kSize - 2], 0);
  CHECK_EQ(mem[kSize - 1], 0);
}

TEST(flash_persists_to_file) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test_flash.bin";
  std::filesystem::remove(path);
  std::string err;
  {
    std::vector<uint8_t> mem(kSize);
    FlashStore f(mem.data(), mem.size());
    CHECK(f.open(path, &err));
    const uint8_t d[3] = {1, 2, 3};
    f.program(1000, d, 3);
  }
  {
    std::vector<uint8_t> mem(kSize, 0);
    FlashStore f(mem.data(), mem.size());
    CHECK(f.open(path, &err));
    CHECK_EQ(mem[1000], 1);
    CHECK_EQ(mem[1002], 3);
    CHECK_EQ(mem[999], 0xff);
  }
  std::filesystem::remove(path);
}

TEST(flash_replaces_file_of_wrong_size) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test_flash_bad.bin";
  {
    FILE* junk = _wfopen(path.c_str(), L"wb");
    const uint8_t zeros[10] = {};
    std::fwrite(zeros, 1, sizeof(zeros), junk);
    std::fclose(junk);
  }
  std::string err;
  {
    std::vector<uint8_t> mem(kSize, 0);
    FlashStore f(mem.data(), mem.size());
    CHECK(f.open(path, &err));
    CHECK_EQ(mem[0], 0xff);
  }
  CHECK_EQ(std::filesystem::file_size(path), kSize);
  std::filesystem::remove(path);
}

TEST(bank_accepts_synth_bank) {
  std::vector<uint8_t> b = make_synth_bank(3);
  const sim::BankCheck c = sim::check_and_patch_bank(b);
  CHECK(c.ok);
  CHECK_EQ(c.sample_count, 3);
  CHECK(!c.capacity_patched);
}

TEST(bank_rejects_bad_magic) {
  std::vector<uint8_t> b = make_synth_bank(1);
  b[0] ^= 0xff;
  const sim::BankCheck c = sim::check_and_patch_bank(b);
  CHECK(!c.ok);
  CHECK(!c.error.empty());
}

TEST(bank_rejects_truncated_file) {
  std::vector<uint8_t> b = make_synth_bank(1);
  b.pop_back();
  CHECK(!sim::check_and_patch_bank(b).ok);
}

TEST(bank_rejects_sample_past_end) {
  std::vector<uint8_t> b = make_synth_bank(1);
  const uint32_t too_long = 48001;  // frame_count del sample 0 (offset 32 + 4)
  std::memcpy(b.data() + 36, &too_long, sizeof(too_long));
  CHECK(!sim::check_and_patch_bank(b).ok);
}

TEST(bank_patches_sd_capacity) {
  std::vector<uint8_t> b = make_synth_bank(1);
  const uint32_t sd_capacity = 16u * 1024u * 1024u;  // lo que escribe el loader web
  std::memcpy(b.data() + 24, &sd_capacity, sizeof(sd_capacity));
  const sim::BankCheck c = sim::check_and_patch_bank(b);
  CHECK(c.ok);
  CHECK(c.capacity_patched);
  uint32_t patched = 0;
  std::memcpy(&patched, b.data() + 24, sizeof(patched));
  CHECK_EQ(patched, sim::device_audio_capacity());
}
```

- [ ] **Step 3: Registrar en CMake y verificar que falla**

En `sim/CMakeLists.txt`, agregar `core/flash_store.cpp core/bank_file.cpp` a `sim_core`, y `tests/unit_flash_bank.cpp tests/synth_bank.cpp` a `pikocore_sim_tests`.

```bash
cmake -S sim -B build-sim > /dev/null; cmake --build build-sim --config Release --target pikocore_sim_tests 2>&1 | grep -E 'error' | head -3
```

Expected: error por archivos faltantes.

- [ ] **Step 4: Implementar `sim/core/flash_store.h` y `.cpp`**

`sim/core/flash_store.h`:

```cpp
#pragma once
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <string>

namespace sim {

// Flash NOR simulada sobre un buffer en memoria, opcionalmente respaldada en un
// archivo del mismo tamaño. Borrar pone 0xFF; programar hace AND bit a bit,
// como el chip real, que solo puede bajar bits a 0.
class FlashStore {
 public:
  FlashStore(uint8_t* mem, size_t size) : mem_(mem), size_(size) {}
  ~FlashStore();
  FlashStore(const FlashStore&) = delete;
  FlashStore& operator=(const FlashStore&) = delete;

  // path vacío = solo memoria. Si el archivo no existe o tiene otro tamaño se
  // recrea en blanco (0xFF).
  bool open(const std::filesystem::path& path, std::string* err);
  void erase(uint32_t offset, size_t count);
  void program(uint32_t offset, const uint8_t* data, size_t count);
  size_t size() const { return size_; }

 private:
  bool clamp(uint32_t offset, size_t* count) const;
  void persist(uint32_t offset, size_t count);

  uint8_t* mem_;
  size_t size_;
  FILE* file_ = nullptr;
};

}  // namespace sim
```

`sim/core/flash_store.cpp`:

```cpp
#include "core/flash_store.h"

#include <cstring>
#include <system_error>

namespace sim {

FlashStore::~FlashStore() {
  if (file_ != nullptr) std::fclose(file_);
}

bool FlashStore::open(const std::filesystem::path& path, std::string* err) {
  if (file_ != nullptr) {
    std::fclose(file_);
    file_ = nullptr;
  }
  std::memset(mem_, 0xff, size_);
  if (path.empty()) return true;

  std::error_code ec;
  const bool reuse = std::filesystem::exists(path, ec) &&
                     std::filesystem::file_size(path, ec) == size_;
  file_ = _wfopen(path.c_str(), reuse ? L"r+b" : L"w+b");
  if (file_ == nullptr) {
    if (err != nullptr) *err = "no se pudo abrir el archivo de flash";
    return false;
  }
  if (reuse) {
    if (std::fread(mem_, 1, size_, file_) != size_) {
      if (err != nullptr) *err = "no se pudo leer el archivo de flash";
      return false;
    }
  } else {
    persist(0, size_);
  }
  return true;
}

bool FlashStore::clamp(uint32_t offset, size_t* count) const {
  if (offset >= size_) return false;
  if (*count > size_ - offset) *count = size_ - offset;
  return *count > 0;
}

void FlashStore::erase(uint32_t offset, size_t count) {
  if (!clamp(offset, &count)) return;
  std::memset(mem_ + offset, 0xff, count);
  persist(offset, count);
}

void FlashStore::program(uint32_t offset, const uint8_t* data, size_t count) {
  if (!clamp(offset, &count)) return;
  for (size_t i = 0; i < count; ++i) mem_[offset + i] &= data[i];
  persist(offset, count);
}

void FlashStore::persist(uint32_t offset, size_t count) {
  if (file_ == nullptr) return;
  _fseeki64(file_, offset, SEEK_SET);
  std::fwrite(mem_ + offset, 1, count, file_);
  std::fflush(file_);
}

}  // namespace sim
```

- [ ] **Step 5: Implementar `sim/core/bank_file.h` y `.cpp`**

`sim/core/bank_file.h`:

```cpp
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace sim {

struct BankCheck {
  bool ok = false;
  std::string error;
  uint32_t sample_count = 0;
  bool capacity_patched = false;
};

// Capacidad de audio de la flash de 16 MB del GamePi13. Es la misma cuenta que
// capacity_from_flash_size() en src/PikoAudioBank.cpp.
uint32_t device_audio_capacity();

// Valida un .pikobank con las mismas reglas que validate_header()
// (src/PikoSampleManager.cpp). Si capacity_bytes supera la capacidad del
// equipo, lo corrige en el blob: el loader web escribe 16 MB en ese campo al
// exportar (web/src/App.tsx, SD_BANK_CAPACITY_BYTES), y con ese valor
// piko_audio_bank_rescan() rechazaría el banco.
BankCheck check_and_patch_bank(std::vector<uint8_t>& blob);

}  // namespace sim
```

`sim/core/bank_file.cpp`:

```cpp
#include "core/bank_file.h"

#include <cstddef>
#include <cstring>

#include "PikoAudioBank.h"

namespace sim {

uint32_t device_audio_capacity() {
  return PIKO_COMPILED_FLASH_TOTAL_BYTES - PIKO_AUDIO_FLASH_OFFSET - PIKO_BANK_HEADER_SIZE;
}

BankCheck check_and_patch_bank(std::vector<uint8_t>& blob) {
  BankCheck r;
  if (blob.size() < PIKO_BANK_HEADER_SIZE) {
    r.error = "el archivo es demasiado chico para ser un .pikobank";
    return r;
  }
  PikoBankHeader h;
  std::memcpy(&h, blob.data(), sizeof(h));
  const uint32_t cap = device_audio_capacity();
  const uint64_t audio_bytes = blob.size() - PIKO_BANK_HEADER_SIZE;

  if (h.magic != PIKO_BANK_MAGIC) {
    r.error = "no es un .pikobank (magic incorrecto)";
    return r;
  }
  if (h.version != PIKO_BANK_VERSION) {
    r.error = "versión de banco no soportada: " + std::to_string(h.version);
    return r;
  }
  if (h.header_size != PIKO_BANK_HEADER_SIZE || h.sample_rate != PIKO_BANK_SAMPLE_RATE) {
    r.error = "header de banco inválido";
    return r;
  }
  if (h.sample_count > PIKO_BANK_MAX_SAMPLES) {
    r.error = "el banco tiene más de 128 samples";
    return r;
  }
  if (h.audio_bytes != audio_bytes) {
    r.error = "el tamaño del archivo no coincide con el header";
    return r;
  }
  if (h.audio_bytes > cap) {
    r.error = "el banco no entra en la flash";
    return r;
  }
  for (uint32_t i = 0; i < h.sample_count; ++i) {
    const PikoBankSampleRecord& s = h.samples[i];
    if (s.frame_count == 0 || s.source_bpm == 0 || s.beat_count == 0 ||
        s.offset > h.audio_bytes || s.frame_count > h.audio_bytes - s.offset) {
      r.error = "el sample " + std::to_string(i + 1) + " del banco es inválido";
      return r;
    }
  }
  if (h.capacity_bytes > cap) {
    std::memcpy(blob.data() + offsetof(PikoBankHeader, capacity_bytes), &cap, sizeof(cap));
    r.capacity_patched = true;
  }
  r.ok = true;
  r.sample_count = h.sample_count;
  return r;
}

}  // namespace sim
```

- [ ] **Step 6: Correr los tests**

```bash
cmake --build build-sim --config Release --target pikocore_sim_tests 2>&1 | grep -E ' error ' ; build-sim/bin/pikocore_sim_tests.exe
```

Expected: `20 tests, 0 fallas`.

- [ ] **Step 7: Commit**

```bash
git add sim/CMakeLists.txt sim/core/flash_store.h sim/core/flash_store.cpp sim/core/bank_file.h sim/core/bank_file.cpp sim/tests/synth_bank.h sim/tests/synth_bank.cpp sim/tests/unit_flash_bank.cpp
git commit -m "sim: flash NOR simulada y validación de .pikobank

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Botones, guion de `--press` y archivos BMP/WAV

**Files:**
- Create: `sim/core/buttons.h`, `sim/core/buttons.cpp`, `sim/core/press_script.h`, `sim/core/press_script.cpp`, `sim/core/file_io.h`, `sim/core/file_io.cpp`, `sim/tests/unit_input_io.cpp`
- Modify: `sim/CMakeLists.txt`

**Interfaces:**
- Consumes: `src/hw_gamepi13.h` (`GAMEPI_BUTTON_PINS`, `GAMEPI_BTN_*`).
- Produces:
  - `enum sim::Button : uint8_t { kUp, kDown, kLeft, kRight, kY, kX, kB, kA, kSelect, kStart, kL, kR, kButtonCount };`
  - `sim::kButtonPins[kButtonCount]`, `constexpr uint16_t sim::bit(Button)`, `const char* sim::button_name(Button)`, `int sim::button_from_name(const std::string&)`, `uint16_t sim::map_xinput(uint16_t)` e `int sim::button_for_vk(unsigned)`.
  - `struct sim::PressEvent { uint32_t at_ms; uint16_t press; uint16_t release; };`, `bool sim::parse_press_script(const std::string&, std::vector<PressEvent>*, std::string* err)` y `uint16_t sim::apply_press_events(const std::vector<PressEvent>&, size_t* next, uint32_t now_ms, uint16_t mask)`.
  - `bool sim::read_file(const std::filesystem::path&, std::vector<uint8_t>*)`, `bool sim::write_bmp(const std::filesystem::path&, int w, int h, const std::function<uint32_t(int x, int y)>& rgb)`, `bool sim::write_bmp_rgb565(const std::filesystem::path&, const uint16_t*, int w, int h, int scale)`, `uint32_t sim::rgb565_to_rgb888(uint16_t)` y `bool sim::write_wav_mono16(const std::filesystem::path&, const std::vector<float>&, uint32_t rate)`.

- [ ] **Step 1: Escribir los tests (`sim/tests/unit_input_io.cpp`)**

```cpp
#include <filesystem>
#include <string>
#include <vector>

#include "core/buttons.h"
#include "core/file_io.h"
#include "core/press_script.h"
#include "test.h"

using namespace sim;

TEST(buttons_pins_match_hw_header) {
  CHECK_EQ(kButtonPins[kUp], 15);
  CHECK_EQ(kButtonPins[kA], 21);
  CHECK_EQ(kButtonPins[kSelect], 19);
  CHECK_EQ(kButtonPins[kStart], 26);
  CHECK_EQ(kButtonPins[kR], 4);
}

TEST(buttons_xinput_face_by_position) {
  CHECK_EQ(map_xinput(0x8000), bit(kX));  // Xbox Y (arriba)
  CHECK_EQ(map_xinput(0x2000), bit(kA));  // Xbox B (derecha)
  CHECK_EQ(map_xinput(0x1000), bit(kB));  // Xbox A (abajo)
  CHECK_EQ(map_xinput(0x4000), bit(kY));  // Xbox X (izquierda)
}

TEST(buttons_xinput_rest) {
  CHECK_EQ(map_xinput(0x0001 | 0x0008), bit(kUp) | bit(kRight));
  CHECK_EQ(map_xinput(0x0100), bit(kL));
  CHECK_EQ(map_xinput(0x0200), bit(kR));
  CHECK_EQ(map_xinput(0x0020), bit(kSelect));
  CHECK_EQ(map_xinput(0x0010), bit(kStart));
}

TEST(buttons_keyboard) {
  CHECK_EQ(button_for_vk('W'), kX);
  CHECK_EQ(button_for_vk('S'), kB);
  CHECK_EQ(button_for_vk(0x0D), kStart);
  CHECK_EQ(button_for_vk(0x26), kUp);
  CHECK_EQ(button_for_vk('Z'), -1);
}

TEST(buttons_names) {
  CHECK_EQ(button_from_name("start"), kStart);
  CHECK_EQ(button_from_name("Up"), kUp);
  CHECK_EQ(button_from_name("foo"), -1);
  CHECK(std::string(button_name(kSelect)) == "SELECT");
}

TEST(press_parses_press_and_release) {
  std::vector<PressEvent> ev;
  std::string err;
  CHECK(parse_press_script("1500:-A,1000:A+b", &ev, &err));
  CHECK_EQ(ev.size(), 2);
  CHECK_EQ(ev[0].at_ms, 1000);
  CHECK_EQ(ev[0].press, bit(kA) | bit(kB));
  CHECK_EQ(ev[1].release, bit(kA));
}

TEST(press_rejects_garbage) {
  std::vector<PressEvent> ev;
  std::string err;
  CHECK(!parse_press_script("abc", &ev, &err));
  CHECK(!parse_press_script("100:FOO", &ev, &err));
  CHECK(!parse_press_script("x:A", &ev, &err));
  CHECK(!parse_press_script("100:", &ev, &err));
  CHECK(!parse_press_script("99999999999:A", &ev, &err));
}

TEST(press_empty_script_is_ok) {
  std::vector<PressEvent> ev;
  std::string err;
  CHECK(parse_press_script("", &ev, &err));
  CHECK(ev.empty());
}

TEST(press_apply_in_time_order) {
  std::vector<PressEvent> ev;
  std::string err;
  CHECK(parse_press_script("1000:A+B,1500:-A", &ev, &err));
  size_t next = 0;
  uint16_t m = 0;
  m = apply_press_events(ev, &next, 999, m);
  CHECK_EQ(m, 0);
  m = apply_press_events(ev, &next, 1000, m);
  CHECK_EQ(m, bit(kA) | bit(kB));
  m = apply_press_events(ev, &next, 2000, m);
  CHECK_EQ(m, bit(kB));
}

TEST(file_io_rgb565) {
  CHECK_EQ(rgb565_to_rgb888(0xFFFF), 0xFFFFFF);
  CHECK_EQ(rgb565_to_rgb888(0xF800), 0xFF0000);
  CHECK_EQ(rgb565_to_rgb888(0x0000), 0);
}

TEST(file_io_bmp_layout) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test.bmp";
  const uint16_t px[4] = {0xF800, 0x07E0, 0x001F, 0xFFFF};
  CHECK(write_bmp_rgb565(path, px, 2, 2, 1));
  std::vector<uint8_t> d;
  CHECK(read_file(path, &d));
  CHECK_EQ(d.size(), 70);  // 54 de header + 2 filas de 8 bytes (6 + padding)
  CHECK(d[0] == 'B' && d[1] == 'M');
  // BMP arranca por la fila de abajo: primer píxel = (0, 1) = azul -> B, G, R.
  CHECK_EQ(d[54], 0xff);
  CHECK_EQ(d[55], 0);
  CHECK_EQ(d[56], 0);
  std::filesystem::remove(path);
}

TEST(file_io_wav_layout) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test.wav";
  CHECK(write_wav_mono16(path, {0.0f, 1.0f, -1.0f}, 48000));
  std::vector<uint8_t> d;
  CHECK(read_file(path, &d));
  CHECK_EQ(d.size(), 50);
  CHECK(d[0] == 'R' && d[1] == 'I' && d[2] == 'F' && d[3] == 'F');
  CHECK_EQ(d[46], 0xff);  // 32767 little-endian
  CHECK_EQ(d[47], 0x7f);
  std::filesystem::remove(path);
}
```

- [ ] **Step 2: Registrar en CMake y verificar que falla**

En `sim/CMakeLists.txt`, agregar `core/buttons.cpp core/press_script.cpp core/file_io.cpp` a `sim_core` y `tests/unit_input_io.cpp` a `pikocore_sim_tests`.

```bash
cmake -S sim -B build-sim > /dev/null; cmake --build build-sim --config Release --target pikocore_sim_tests 2>&1 | grep -E 'error' | head -3
```

Expected: error por archivos faltantes.

- [ ] **Step 3: Implementar `sim/core/buttons.h` y `.cpp`**

`sim/core/buttons.h`:

```cpp
#pragma once
#include <cstdint>
#include <string>

#include "hw_gamepi13.h"

namespace sim {

// Mismo orden que los 8 botones musicales de pikocore (GAMEPI_BUTTON_PINS) y
// después los 4 de control.
enum Button : uint8_t {
  kUp, kDown, kLeft, kRight, kY, kX, kB, kA,
  kSelect, kStart, kL, kR,
  kButtonCount
};

inline constexpr uint8_t kMusicPins[8] = GAMEPI_BUTTON_PINS;
inline constexpr uint8_t kButtonPins[kButtonCount] = {
    kMusicPins[0], kMusicPins[1], kMusicPins[2], kMusicPins[3],
    kMusicPins[4], kMusicPins[5], kMusicPins[6], kMusicPins[7],
    GAMEPI_BTN_SELECT, GAMEPI_BTN_START, GAMEPI_BTN_L, GAMEPI_BTN_R};

constexpr uint16_t bit(Button b) { return static_cast<uint16_t>(1u << b); }

const char* button_name(Button b);
// Sin distinguir mayúsculas; -1 si no existe.
int button_from_name(const std::string& name);
// wButtons de XINPUT_GAMEPAD -> máscara de Button. Botones de cara por
// posición: el de arriba del control Xbox (Y) es el de arriba del GamePi13 (X).
uint16_t map_xinput(uint16_t xinput_buttons);
// Tecla virtual de Windows -> Button, o -1.
int button_for_vk(unsigned vk);

}  // namespace sim
```

`sim/core/buttons.cpp`:

```cpp
#include "core/buttons.h"

#include <cctype>

namespace sim {

namespace {
const char* const kNames[kButtonCount] = {"UP", "DOWN", "LEFT", "RIGHT", "Y", "X",
                                          "B", "A", "SELECT", "START", "L", "R"};

// Constantes de Xinput.h, repetidas acá para que el core no dependa de windows.h.
constexpr uint16_t kXDpadUp = 0x0001, kXDpadDown = 0x0002, kXDpadLeft = 0x0004,
                   kXDpadRight = 0x0008, kXStart = 0x0010, kXBack = 0x0020,
                   kXLeftShoulder = 0x0100, kXRightShoulder = 0x0200, kXA = 0x1000,
                   kXB = 0x2000, kXX = 0x4000, kXY = 0x8000;

struct XMap {
  uint16_t xinput;
  Button button;
};
constexpr XMap kXMap[] = {
    {kXDpadUp, kUp},       {kXDpadDown, kDown}, {kXDpadLeft, kLeft},
    {kXDpadRight, kRight}, {kXY, kX},           {kXB, kA},
    {kXA, kB},             {kXX, kY},           {kXLeftShoulder, kL},
    {kXRightShoulder, kR}, {kXBack, kSelect},   {kXStart, kStart}};

struct VkMap {
  unsigned vk;
  Button button;
};
constexpr VkMap kVkMap[] = {
    {0x26, kUp},  {0x28, kDown},  {0x25, kLeft},  {0x27, kRight},  // flechas
    {'W', kX},    {'D', kA},      {'S', kB},      {'A', kY},
    {'Q', kL},    {'E', kR},      {0x08, kSelect}, {0x0D, kStart}};  // Backspace, Enter
}  // namespace

const char* button_name(Button b) { return b < kButtonCount ? kNames[b] : "?"; }

int button_from_name(const std::string& name) {
  std::string upper;
  for (char c : name) upper.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(c))));
  for (int i = 0; i < kButtonCount; ++i) {
    if (upper == kNames[i]) return i;
  }
  return -1;
}

uint16_t map_xinput(uint16_t xinput_buttons) {
  uint16_t mask = 0;
  for (const XMap& e : kXMap) {
    if (xinput_buttons & e.xinput) mask = static_cast<uint16_t>(mask | bit(e.button));
  }
  return mask;
}

int button_for_vk(unsigned vk) {
  for (const VkMap& e : kVkMap) {
    if (e.vk == vk) return e.button;
  }
  return -1;
}

}  // namespace sim
```

- [ ] **Step 4: Implementar `sim/core/press_script.h` y `.cpp`**

`sim/core/press_script.h`:

```cpp
#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace sim {

struct PressEvent {
  uint32_t at_ms = 0;
  uint16_t press = 0;    // máscara de Button a apretar
  uint16_t release = 0;  // máscara de Button a soltar
};

// "1000:A+B,1500:-A": a los 1000 ms se aprietan A y B; a los 1500 se suelta A.
// Nombres de botones: los de button_name(). Queda ordenado por tiempo.
bool parse_press_script(const std::string& text, std::vector<PressEvent>* out, std::string* err);

// Aplica a `mask` los eventos con at_ms <= now_ms a partir de *next y avanza *next.
uint16_t apply_press_events(const std::vector<PressEvent>& events, size_t* next,
                            uint32_t now_ms, uint16_t mask);

}  // namespace sim
```

`sim/core/press_script.cpp`:

```cpp
#include "core/press_script.h"

#include <algorithm>
#include <sstream>

#include "core/buttons.h"

namespace sim {

namespace {
std::vector<std::string> split(const std::string& s, char sep) {
  std::vector<std::string> parts;
  std::string part;
  std::istringstream in(s);
  while (std::getline(in, part, sep)) parts.push_back(part);
  return parts;
}
}  // namespace

bool parse_press_script(const std::string& text, std::vector<PressEvent>* out, std::string* err) {
  out->clear();
  if (text.empty()) return true;
  for (const std::string& token : split(text, ',')) {
    const size_t colon = token.find(':');
    if (colon == std::string::npos || colon == 0) {
      *err = "falta 'ms:' en \"" + token + "\"";
      return false;
    }
    const std::string ms = token.substr(0, colon);
    if (ms.size() > 9 || ms.find_first_not_of("0123456789") != std::string::npos) {
      *err = "tiempo inválido en \"" + token + "\"";
      return false;
    }
    PressEvent ev;
    ev.at_ms = static_cast<uint32_t>(std::stoul(ms));
    for (std::string item : split(token.substr(colon + 1), '+')) {
      const bool release = !item.empty() && item[0] == '-';
      if (release) item.erase(0, 1);
      const int b = button_from_name(item);
      if (b < 0) {
        *err = "botón desconocido \"" + item + "\"";
        return false;
      }
      uint16_t& target = release ? ev.release : ev.press;
      target = static_cast<uint16_t>(target | bit(static_cast<Button>(b)));
    }
    if (ev.press == 0 && ev.release == 0) {
      *err = "no hay botones en \"" + token + "\"";
      return false;
    }
    out->push_back(ev);
  }
  std::stable_sort(out->begin(), out->end(),
                   [](const PressEvent& a, const PressEvent& b) { return a.at_ms < b.at_ms; });
  return true;
}

uint16_t apply_press_events(const std::vector<PressEvent>& events, size_t* next,
                            uint32_t now_ms, uint16_t mask) {
  while (*next < events.size() && events[*next].at_ms <= now_ms) {
    mask = static_cast<uint16_t>((mask | events[*next].press) & ~events[*next].release);
    ++*next;
  }
  return mask;
}

}  // namespace sim
```

- [ ] **Step 5: Implementar `sim/core/file_io.h` y `.cpp`**

`sim/core/file_io.h`:

```cpp
#pragma once
#include <cstdint>
#include <filesystem>
#include <functional>
#include <vector>

namespace sim {

bool read_file(const std::filesystem::path& path, std::vector<uint8_t>* out);
// BMP de 24 bits; rgb(x, y) devuelve 0xRRGGBB, con y = 0 arriba.
bool write_bmp(const std::filesystem::path& path, int w, int h,
               const std::function<uint32_t(int x, int y)>& rgb);
// Imagen RGB565 (como la del LCD) ampliada `scale` veces.
bool write_bmp_rgb565(const std::filesystem::path& path, const uint16_t* px, int w, int h,
                      int scale);
uint32_t rgb565_to_rgb888(uint16_t p);
// WAV PCM mono de 16 bits.
bool write_wav_mono16(const std::filesystem::path& path, const std::vector<float>& samples,
                      uint32_t rate);

}  // namespace sim
```

`sim/core/file_io.cpp`:

```cpp
#include "core/file_io.h"

#include <algorithm>
#include <cstdio>

namespace sim {

namespace {
struct File {
  FILE* f = nullptr;
  ~File() {
    if (f != nullptr) std::fclose(f);
  }
};

void put16(std::vector<uint8_t>& b, uint16_t v) {
  b.push_back(static_cast<uint8_t>(v));
  b.push_back(static_cast<uint8_t>(v >> 8));
}

void put32(std::vector<uint8_t>& b, uint32_t v) {
  put16(b, static_cast<uint16_t>(v));
  put16(b, static_cast<uint16_t>(v >> 16));
}

void put_tag(std::vector<uint8_t>& b, const char* tag) {
  for (int i = 0; i < 4; ++i) b.push_back(static_cast<uint8_t>(tag[i]));
}

bool write_all(const std::filesystem::path& path, const std::vector<uint8_t>& data) {
  File file;
  file.f = _wfopen(path.c_str(), L"wb");
  if (file.f == nullptr) return false;
  return std::fwrite(data.data(), 1, data.size(), file.f) == data.size();
}
}  // namespace

bool read_file(const std::filesystem::path& path, std::vector<uint8_t>* out) {
  File file;
  file.f = _wfopen(path.c_str(), L"rb");
  if (file.f == nullptr) return false;
  _fseeki64(file.f, 0, SEEK_END);
  const long long n = _ftelli64(file.f);
  _fseeki64(file.f, 0, SEEK_SET);
  if (n < 0) return false;
  out->resize(static_cast<size_t>(n));
  return n == 0 || std::fread(out->data(), 1, out->size(), file.f) == out->size();
}

uint32_t rgb565_to_rgb888(uint16_t p) {
  const uint32_t r = ((p >> 11) & 31u) * 255u / 31u;
  const uint32_t g = ((p >> 5) & 63u) * 255u / 63u;
  const uint32_t b = (p & 31u) * 255u / 31u;
  return (r << 16) | (g << 8) | b;
}

bool write_bmp(const std::filesystem::path& path, int w, int h,
               const std::function<uint32_t(int x, int y)>& rgb) {
  const uint32_t row = (static_cast<uint32_t>(w) * 3u + 3u) & ~3u;
  const uint32_t data_size = row * static_cast<uint32_t>(h);
  std::vector<uint8_t> b;
  b.reserve(54 + data_size);
  b.push_back('B');
  b.push_back('M');
  put32(b, 54 + data_size);
  put32(b, 0);
  put32(b, 54);
  put32(b, 40);
  put32(b, static_cast<uint32_t>(w));
  put32(b, static_cast<uint32_t>(h));
  put16(b, 1);
  put16(b, 24);
  put32(b, 0);
  put32(b, data_size);
  put32(b, 2835);
  put32(b, 2835);
  put32(b, 0);
  put32(b, 0);
  for (int y = h - 1; y >= 0; --y) {  // BMP va de abajo hacia arriba
    for (int x = 0; x < w; ++x) {
      const uint32_t c = rgb(x, y);
      b.push_back(static_cast<uint8_t>(c));
      b.push_back(static_cast<uint8_t>(c >> 8));
      b.push_back(static_cast<uint8_t>(c >> 16));
    }
    for (uint32_t pad = static_cast<uint32_t>(w) * 3u; pad < row; ++pad) b.push_back(0);
  }
  return write_all(path, b);
}

bool write_bmp_rgb565(const std::filesystem::path& path, const uint16_t* px, int w, int h,
                      int scale) {
  return write_bmp(path, w * scale, h * scale, [&](int x, int y) {
    return rgb565_to_rgb888(px[static_cast<size_t>(y / scale) * w + x / scale]);
  });
}

bool write_wav_mono16(const std::filesystem::path& path, const std::vector<float>& samples,
                      uint32_t rate) {
  const uint32_t data_size = static_cast<uint32_t>(samples.size() * 2);
  std::vector<uint8_t> b;
  b.reserve(44 + data_size);
  put_tag(b, "RIFF");
  put32(b, 36 + data_size);
  put_tag(b, "WAVE");
  put_tag(b, "fmt ");
  put32(b, 16);
  put16(b, 1);  // PCM
  put16(b, 1);  // mono
  put32(b, rate);
  put32(b, rate * 2);
  put16(b, 2);
  put16(b, 16);
  put_tag(b, "data");
  put32(b, data_size);
  for (float s : samples) {
    const float c = std::clamp(s, -1.0f, 1.0f);
    put16(b, static_cast<uint16_t>(static_cast<int16_t>(c * 32767.0f)));
  }
  return write_all(path, b);
}

}  // namespace sim
```

- [ ] **Step 6: Correr los tests**

```bash
cmake --build build-sim --config Release --target pikocore_sim_tests 2>&1 | grep -E ' error ' ; build-sim/bin/pikocore_sim_tests.exe
```

Expected: `32 tests, 0 fallas`.

- [ ] **Step 7: Commit**

```bash
git add sim/CMakeLists.txt sim/core/buttons.h sim/core/buttons.cpp sim/core/press_script.h sim/core/press_script.cpp sim/core/file_io.h sim/core/file_io.cpp sim/tests/unit_input_io.cpp
git commit -m "sim: mapeo de botones XInput/teclado, guion --press y BMP/WAV

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Runtime — planificador con Fibers, HAL y arranque headless

**Files:**
- Create: `sim/runtime/machine.h`, `sim/runtime/machine.cpp`, `sim/runtime/sim_io.h`, `sim/runtime/sim_hal.cpp`, `sim/runtime/firmware_entry.h`, `sim/runtime/firmware_glue.cpp`, `sim/runtime/bank_hotload.h`, `sim/runtime/bank_hotload.cpp`, `sim/runtime/headless.h`, `sim/runtime/headless.cpp`, `sim/tests/itest_main.cpp`
- Modify: `sim/CMakeLists.txt`

**Interfaces:**
- Consumes: todo lo de las Tasks 2–6. Del firmware, `piko_audio_bank_set_mutating()`, `piko_audio_bank_rescan()` y `piko_audio_sample_count()` (`src/PikoAudioBank.h`), y el global `uint8_t gamepi_selector` (`src/main.cpp:139`).
- Produces:
  - Constantes `sim::kCpuHz`, `sim::kCyclesPerUs`, `sim::kPwmPeriodCycles`, `sim::kAudioRate` y `sim::kTimeReadCycles`, en `runtime/machine.h`.
  - `class sim::Machine { static Machine& get(); void boot(int (*)()); void run_until(uint64_t cycles); uint64_t now_cycles() const; uint64_t now_us() const; PwmDac& dac(); St7789& lcd(); ... }`.
  - `sim::FlashStore& sim::flash()`, `void sim::set_button_mask(uint16_t)`, `uint16_t sim::button_mask()`, `bool sim::beat_led()` y `uint16_t sim::backlight_level()`, en `runtime/sim_io.h`.
  - `void sim::write_bank_to_flash(const std::vector<uint8_t>&)` y `void sim::hot_load_bank(const std::vector<uint8_t>&)`, en `runtime/bank_hotload.h`.
  - `struct sim::HeadlessOptions`, `struct sim::HeadlessResult` y `bool sim::run_headless(const HeadlessOptions&, HeadlessResult*, std::string*)`, en `runtime/headless.h`.
  - `int piko_firmware_main();`, en `runtime/firmware_entry.h`.
  - Target `sim_runtime`, target `pikocore_sim_itest` y el test de CTest `itest_boot`.

**Semántica del planificador (spec §3):** `run_until` alterna entre los ticks de PWM, cada 251 ciclos, y la Fiber del firmware. En cada tick corre la ISR si está habilitada y alimenta el DAC con el nivel actual. `main()` cede el control en `__wfi()` (hasta el próximo tick), en `sleep_*` y en cada lectura del timer (+32 ciclos, así un lazo que solo espera a `time_us_64()` no se cuelga con el tiempo congelado). La ISR nunca corre en medio de una instrucción de `main()`.

- [ ] **Step 1: Escribir el test de integración de arranque (`sim/tests/itest_main.cpp`)**

```cpp
// Tests de integración: un escenario por proceso, porque el firmware tiene
// estado global y solo se puede arrancar una vez.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>

#include "PikoAudioBank.h"
#include "core/press_script.h"
#include "runtime/headless.h"
#include "runtime/machine.h"
#include "synth_bank.h"

extern uint8_t gamepi_selector;  // src/main.cpp

namespace {
constexpr uint16_t kWhite = 0xFFFF;  // COL_WHITE de src/gamepi13/ui.cpp
constexpr uint16_t kGray = 0x632C;   // COL_GRAY de src/gamepi13/ui.cpp
int g_failures = 0;

void expect(bool ok, const char* what) {
  std::printf("%s %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) ++g_failures;
}

double rms(const std::vector<float>& a, uint32_t from_ms, uint32_t to_ms) {
  const size_t per_ms = sim::kAudioRate / 1000;
  const size_t from = static_cast<size_t>(from_ms) * per_ms;
  const size_t to = std::min(a.size(), static_cast<size_t>(to_ms) * per_ms);
  if (to <= from) return 0.0;
  double acc = 0.0;
  for (size_t i = from; i < to; ++i) acc += static_cast<double>(a[i]) * a[i];
  return std::sqrt(acc / static_cast<double>(to - from));
}

// Centro del cuadrado del modo i en la fila de modos (draw_dots() en ui.cpp:
// 8 slots de 30 px, cuadrados de 20 px en y = 212..231).
uint16_t mode_square(const sim::HeadlessResult& r, int i) {
  return r.lcd[static_cast<size_t>(222) * 240 + i * 30 + 15];
}

bool run(const sim::HeadlessOptions& o, sim::HeadlessResult* r) {
  std::string err;
  if (!sim::run_headless(o, r, &err)) {
    std::printf("FAIL run_headless: %s\n", err.c_str());
    return false;
  }
  std::printf("     %u ms virtuales en %.2f s reales (x%.2f)\n", o.run_ms, r->wall_seconds,
              o.run_ms / 1000.0 / r->wall_seconds);
  return true;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    std::printf("uso: pikocore_sim_itest boot\n");
    return 2;
  }
  const std::string scenario = argv[1];
  sim::HeadlessOptions o;
  sim::HeadlessResult r;
  o.bank = make_synth_bank(2);

  if (scenario == "boot") {
    o.run_ms = 6000;
    if (!run(o, &r)) return 1;
    expect(rms(r.audio, 5000, 6000) > 0.01, "hay audio después del arranque");
    size_t lit = 0;
    for (uint16_t p : r.lcd) lit += p != 0;
    expect(lit > 1000, "el LCD muestra el dashboard");
    expect(mode_square(r, 0) == kWhite, "modo 0 resaltado");
    expect(mode_square(r, 1) == kGray, "modo 1 en gris");
  } else {
    std::printf("escenario desconocido: %s\n", scenario.c_str());
    return 2;
  }
  return g_failures == 0 ? 0 : 1;
}
```

- [ ] **Step 2: Registrar en CMake y verificar que falla**

Agregar al final de `sim/CMakeLists.txt`:

```cmake
# ---- runtime: conecta el firmware con el simulador ----
add_library(sim_runtime STATIC
  runtime/machine.cpp
  runtime/sim_hal.cpp
  runtime/firmware_glue.cpp
  runtime/bank_hotload.cpp
  runtime/headless.cpp
)
target_link_libraries(sim_runtime PUBLIC piko_fw sim_core)
target_compile_definitions(sim_runtime PRIVATE PIKO_GAMEPI13=1 PIKO_GAMEPI13_SD=0 NOMINMAX WIN32_LEAN_AND_MEAN)
target_compile_options(sim_runtime PRIVATE /W4 /utf-8)

add_executable(pikocore_sim_itest tests/itest_main.cpp tests/synth_bank.cpp)
target_link_libraries(pikocore_sim_itest PRIVATE sim_runtime)
target_include_directories(pikocore_sim_itest PRIVATE ${SIM_ROOT}/tests)
target_compile_options(pikocore_sim_itest PRIVATE /W4 /utf-8)
foreach(scenario boot)
  add_test(NAME itest_${scenario} COMMAND pikocore_sim_itest ${scenario})
endforeach()
```

```bash
cmake -S sim -B build-sim > /dev/null; cmake --build build-sim --config Release --target pikocore_sim_itest 2>&1 | grep -E 'error' | head -3
```

Expected: error por archivos faltantes de `runtime/`.

- [ ] **Step 3: Implementar `sim/runtime/machine.h`**

```cpp
#pragma once
#include <cstdint>

#include "core/pwm_dac.h"
#include "core/st7789.h"

namespace sim {

constexpr uint64_t kCpuHz = 248000000ull;          // CLOCK_RATE de src/main.cpp
constexpr uint64_t kCyclesPerUs = kCpuHz / 1000000ull;
constexpr uint64_t kPwmPeriodCycles = 251;          // wrap = 250, clkdiv = 1
constexpr uint32_t kAudioRate = 48000;
// Costo de leer el timer desde main(): evita que un lazo que solo espera a
// time_us_64() se cuelgue con el reloj virtual congelado.
constexpr uint64_t kTimeReadCycles = 32;

// Planificador determinista del RP2350 simulado. El main() del firmware corre
// en una Fiber de Win32 y cede el control en __wfi(), sleep_*() y cada lectura
// del timer; entre medio, run_until() corre los ticks de PWM (ISR de audio
// + DAC). Todo el firmware corre en el hilo que llamó a boot().
class Machine {
 public:
  static Machine& get();

  // Convierte el hilo actual en Fiber y prepara el main() del firmware.
  // Llamar una vez, desde el hilo que después llama a run_until().
  void boot(int (*firmware_main)());
  // Avanza el reloj virtual hasta `cycles`, corriendo ISR y main().
  void run_until(uint64_t cycles);
  uint64_t now_cycles() const { return now_; }
  uint64_t now_us() const { return now_ / kCyclesPerUs; }

  // ---- lado firmware (vía runtime/sim_hal.cpp) ----
  bool in_main() const;
  void main_sleep_until(uint64_t cycles);
  void main_wfi();
  void set_irq_handler(void (*handler)()) { isr_ = handler; }
  void set_irq_enabled(bool enabled) { irq_enabled_ = enabled; }
  void set_pwm_irq_enabled(bool enabled) { pwm_irq_enabled_ = enabled; }
  void set_audio_level(uint16_t level) { audio_level_ = level; }

  PwmDac& dac() { return dac_; }
  St7789& lcd() { return lcd_; }

 private:
  Machine();
  static void __stdcall fiber_entry(void* arg);

  void* scheduler_fiber_ = nullptr;
  void* main_fiber_ = nullptr;
  int (*firmware_main_)() = nullptr;
  uint64_t now_ = 0;
  uint64_t next_pwm_ = kPwmPeriodCycles;
  uint64_t main_wake_ = 0;
  void (*isr_)() = nullptr;
  bool irq_enabled_ = false;
  bool pwm_irq_enabled_ = false;
  uint16_t audio_level_ = 0;
  PwmDac dac_;
  St7789 lcd_;
};

}  // namespace sim
```

- [ ] **Step 4: Implementar `sim/runtime/machine.cpp`**

```cpp
#include "runtime/machine.h"

#include <windows.h>

#include <algorithm>
#include <cstdio>
#include <cstdlib>

namespace sim {

Machine& Machine::get() {
  static Machine machine;
  return machine;
}

Machine::Machine() : dac_(kCpuHz, static_cast<uint32_t>(kPwmPeriodCycles), kAudioRate) {}

void Machine::boot(int (*firmware_main)()) {
  firmware_main_ = firmware_main;
  scheduler_fiber_ = ConvertThreadToFiber(nullptr);
  main_fiber_ = CreateFiber(1u << 20, &Machine::fiber_entry, this);
  if (scheduler_fiber_ == nullptr || main_fiber_ == nullptr) {
    std::fprintf(stderr, "pikocore-sim: no se pudieron crear las fibers\n");
    std::abort();
  }
  main_wake_ = now_;
}

void __stdcall Machine::fiber_entry(void* arg) {
  Machine* m = static_cast<Machine*>(arg);
  m->firmware_main_();
  // El main() del firmware no vuelve nunca; si volviera, queda dormido.
  for (;;) m->main_sleep_until(UINT64_MAX);
}

bool Machine::in_main() const {
  return main_fiber_ != nullptr && GetCurrentFiber() == main_fiber_;
}

void Machine::main_sleep_until(uint64_t cycles) {
  main_wake_ = std::max(cycles, now_);
  SwitchToFiber(scheduler_fiber_);
}

void Machine::main_wfi() { main_sleep_until(next_pwm_); }

void Machine::run_until(uint64_t target) {
  while (now_ < target) {
    if (main_wake_ <= now_) {
      SwitchToFiber(main_fiber_);
      continue;
    }
    const uint64_t event = std::min(target, main_wake_);
    while (next_pwm_ <= event) {
      now_ = next_pwm_;
      if (isr_ != nullptr && irq_enabled_ && pwm_irq_enabled_) isr_();
      dac_.tick(audio_level_);
      next_pwm_ += kPwmPeriodCycles;
    }
    now_ = event;
  }
}

}  // namespace sim
```

- [ ] **Step 5: Implementar `sim/runtime/sim_io.h`, `sim/runtime/firmware_entry.h` y `sim/runtime/sim_hal.cpp`**

`sim/runtime/sim_io.h`:

```cpp
#pragma once
#include <cstdint>

namespace sim {

class FlashStore;

// La flash simulada de 16 MB (sim_flash_mem).
FlashStore& flash();
// Botones apretados; bits = sim::Button. Thread-safe.
void set_button_mask(uint16_t mask);
uint16_t button_mask();
// LED de beat (GP28).
bool beat_led();
// Nivel PWM del backlight del LCD (GP7), 0-65535.
uint16_t backlight_level();

}  // namespace sim
```

`sim/runtime/firmware_entry.h`:

```cpp
#pragma once
// main() de src/main.cpp, renombrado al compilar (ver sim/CMakeLists.txt).
int piko_firmware_main();
```

`sim/runtime/sim_hal.cpp`:

```cpp
// Implementación de las funciones sim_* que declara sim/shim/sim_pico.h: acá el
// "hardware" del RP2350 se conecta con la Machine y el resto del simulador.
#include <atomic>

#include "PikoAudioBank.h"
#include "core/buttons.h"
#include "core/flash_store.h"
#include "hw_gamepi13.h"
#include "runtime/machine.h"
#include "runtime/sim_io.h"
#include "sim_pico.h"

uint8_t sim_flash_mem[PIKO_COMPILED_FLASH_TOTAL_BYTES];

namespace {
constexpr uint32_t kPinCount = 48;
std::atomic<bool> g_pin_low[kPinCount];  // salidas: true = el firmware escribió 0
std::atomic<uint16_t> g_buttons{0};
std::atomic<uint16_t> g_backlight{0};
std::atomic<bool> g_led{false};
sim::FlashStore g_flash(sim_flash_mem, sizeof(sim_flash_mem));

int button_for_pin(uint pin) {
  for (int b = 0; b < sim::kButtonCount; ++b) {
    if (sim::kButtonPins[b] == pin) return b;
  }
  return -1;
}
}  // namespace

namespace sim {
FlashStore& flash() { return g_flash; }
void set_button_mask(uint16_t mask) { g_buttons = mask; }
uint16_t button_mask() { return g_buttons; }
bool beat_led() { return g_led; }
uint16_t backlight_level() { return g_backlight; }
}  // namespace sim

extern "C" {

uint64_t sim_time_us(void) {
  sim::Machine& m = sim::Machine::get();
  if (m.in_main()) m.main_sleep_until(m.now_cycles() + sim::kTimeReadCycles);
  return m.now_us();
}

void sim_sleep_until_us(uint64_t t_us) {
  sim::Machine& m = sim::Machine::get();
  if (m.in_main()) m.main_sleep_until(t_us * sim::kCyclesPerUs);
}

void sim_wfi(void) {
  sim::Machine& m = sim::Machine::get();
  if (m.in_main()) m.main_wfi();
}

bool sim_gpio_get(uint pin) {
  const int b = button_for_pin(pin);
  // Botones con pull-up: apretado = 0.
  if (b >= 0) return (g_buttons.load() & sim::bit(static_cast<sim::Button>(b))) == 0;
  return pin < kPinCount ? !g_pin_low[pin].load() : true;
}

void sim_gpio_put(uint pin, bool value) {
  if (pin >= kPinCount) return;
  g_pin_low[pin] = !value;
  sim::Machine& m = sim::Machine::get();
  if (pin == GAMEPI_LCD_DC_PIN) {
    m.lcd().set_dc(value);
  } else if (pin == GAMEPI_LCD_CS_PIN) {
    m.lcd().set_cs(value);
  } else if (pin == GAMEPI_LED_PIN) {
    g_led = value;
  }
}

void sim_pwm_set_level(uint pin, uint16_t level) {
  if (pin == GAMEPI_AUDIO_PIN) {
    sim::Machine::get().set_audio_level(level);
  } else if (pin == GAMEPI_LCD_BL_PIN) {
    g_backlight = level;
  }
}

void sim_pwm_irq_enable(bool enabled) { sim::Machine::get().set_pwm_irq_enabled(enabled); }
void sim_irq_set_handler(void (*handler)(void)) { sim::Machine::get().set_irq_handler(handler); }
void sim_irq_enable(bool enabled) { sim::Machine::get().set_irq_enabled(enabled); }
void sim_spi_write(const uint8_t* src, size_t len) { sim::Machine::get().lcd().write(src, len); }
void sim_flash_erase(uint32_t offset, size_t count) { g_flash.erase(offset, count); }
void sim_flash_program(uint32_t offset, const uint8_t* data, size_t count) {
  g_flash.program(offset, data, count);
}

}  // extern "C"
```

- [ ] **Step 6: Implementar `sim/runtime/firmware_glue.cpp`**

```cpp
// Símbolos que src/main.cpp referencia y que en el RP2350 vienen de
// PikoSampleManager.cpp (core1: protocolo USB y modo SD). El simulador no
// compila ese archivo: carga bancos con runtime/bank_hotload.cpp, y el modo SD
// está aparcado (PIKO_GAMEPI13_SD=0, el selector nunca llega al modo 8).
#include "PikoSampleManager.h"

volatile bool gamepi_sd_list_requested = false;
volatile bool gamepi_sd_list_done = false;
volatile bool gamepi_sd_load_requested = false;
volatile uint32_t gamepi_sd_load_index = 0;
volatile bool gamepi_sd_load_done = false;
volatile bool gamepi_sd_load_ok = false;
volatile bool gamepi_sd_unmount_requested = false;

uint32_t gamepi_sd_file_count() { return 0; }
const char* gamepi_sd_file_name(uint32_t index) {
  (void)index;
  return "";
}

void piko_sample_manager_set_ready() {}
void piko_sample_manager_core() {}
```

- [ ] **Step 7: Implementar `sim/runtime/bank_hotload.h` y `.cpp`**

`sim/runtime/bank_hotload.h`:

```cpp
#pragma once
#include <cstdint>
#include <vector>

namespace sim {

// Escribe un .pikobank ya validado (check_and_patch_bank) en la flash simulada,
// sin avisarle al firmware. Sirve antes del boot: piko_audio_bank_init() lo lee.
void write_bank_to_flash(const std::vector<uint8_t>& blob);

// Carga en caliente con la misma secuencia que el core1 real
// (src/PikoSampleManager.cpp): mutating -> escribir flash -> rescan ->
// !mutating. Llamar solo entre dos run_until(), desde el hilo de emulación.
void hot_load_bank(const std::vector<uint8_t>& blob);

}  // namespace sim
```

`sim/runtime/bank_hotload.cpp`:

```cpp
#include "runtime/bank_hotload.h"

#include "PikoAudioBank.h"
#include "core/flash_store.h"
#include "runtime/sim_io.h"

namespace sim {

void write_bank_to_flash(const std::vector<uint8_t>& blob) {
  const size_t erase_len = (blob.size() + PIKO_FLASH_SECTOR_SIZE - 1) &
                           ~static_cast<size_t>(PIKO_FLASH_SECTOR_SIZE - 1);
  flash().erase(PIKO_AUDIO_FLASH_OFFSET, erase_len);
  flash().program(PIKO_AUDIO_FLASH_OFFSET, blob.data(), blob.size());
}

void hot_load_bank(const std::vector<uint8_t>& blob) {
  piko_audio_bank_set_mutating(true);
  write_bank_to_flash(blob);
  piko_audio_bank_rescan();
  piko_audio_bank_set_mutating(false);
}

}  // namespace sim
```

- [ ] **Step 8: Implementar `sim/runtime/headless.h` y `.cpp`**

`sim/runtime/headless.h`:

```cpp
#pragma once
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "core/press_script.h"

namespace sim {

struct HeadlessOptions {
  std::vector<uint8_t> bank;          // vacío = lo que ya haya en la flash
  std::filesystem::path flash_path;   // vacío = flash solo en memoria
  uint32_t run_ms = 5000;
  std::vector<PressEvent> presses;
  uint32_t hot_load_at_ms = 0;        // 0 = no cargar nada en caliente
  std::vector<uint8_t> hot_bank;
};

struct HeadlessResult {
  std::vector<float> audio;     // mono, kAudioRate
  std::vector<uint16_t> lcd;    // 240x240 RGB565, como se ve en el GamePi13
  double wall_seconds = 0.0;
};

// Arranca el firmware y lo corre run_ms de tiempo virtual, sin pacing. Solo se
// puede llamar una vez por proceso: el firmware tiene estado global.
bool run_headless(const HeadlessOptions& options, HeadlessResult* result, std::string* err);

}  // namespace sim
```

`sim/runtime/headless.cpp`:

```cpp
#include "runtime/headless.h"

#include <chrono>

#include "core/bank_file.h"
#include "core/flash_store.h"
#include "runtime/bank_hotload.h"
#include "runtime/firmware_entry.h"
#include "runtime/machine.h"
#include "runtime/sim_io.h"

namespace sim {

bool run_headless(const HeadlessOptions& o, HeadlessResult* r, std::string* err) {
  if (!flash().open(o.flash_path, err)) return false;
  if (!o.bank.empty()) {
    std::vector<uint8_t> blob = o.bank;
    const BankCheck c = check_and_patch_bank(blob);
    if (!c.ok) {
      *err = c.error;
      return false;
    }
    write_bank_to_flash(blob);
  }
  std::vector<uint8_t> hot = o.hot_bank;
  if (o.hot_load_at_ms > 0) {
    const BankCheck c = check_and_patch_bank(hot);
    if (!c.ok) {
      *err = c.error;
      return false;
    }
  }

  Machine& m = Machine::get();
  r->audio.clear();
  r->audio.reserve(static_cast<size_t>(o.run_ms) * kAudioRate / 1000 + 16);
  m.dac().set_sink([r](float s) { r->audio.push_back(s); });

  const auto t0 = std::chrono::steady_clock::now();
  m.boot(&piko_firmware_main);
  uint16_t mask = 0;
  size_t next = 0;
  for (uint32_t ms = 0; ms < o.run_ms; ++ms) {
    mask = apply_press_events(o.presses, &next, ms, mask);
    set_button_mask(mask);
    if (o.hot_load_at_ms > 0 && ms == o.hot_load_at_ms) hot_load_bank(hot);
    m.run_until(static_cast<uint64_t>(ms + 1) * (kCpuHz / 1000));
  }
  r->wall_seconds =
      std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  r->lcd.assign(static_cast<size_t>(St7789::kSize) * St7789::kSize, 0);
  m.lcd().snapshot_view(r->lcd.data());
  return true;
}

}  // namespace sim
```

- [ ] **Step 9: Compilar y correr el test de arranque**

```bash
cmake --build build-sim --config Release --target pikocore_sim_itest 2>&1 | grep -E ' error |LNK' ; build-sim/bin/pikocore_sim_itest.exe boot; echo "exit=$?"
```

Expected: 4 líneas `ok   ...`, la línea `6000 ms virtuales en X s reales (xN)` y `exit=0`. **Revisar la velocidad:** tiene que ser **x1.5 o más**; si no, el modo ventana no va a llegar a tiempo real. Si la velocidad es menor, medir con el profiler de Visual Studio antes de seguir. Candidatos: la cantidad de cambios de fiber por lecturas del timer y el `std::function` del sink del DAC.

Si falla `hay audio después del arranque`, correr `build-sim/bin/pikocore_sim_itest.exe boot` y comparar con la línea de tiempo del arranque: splash de ~2 s en `gamepi_ui_init()`, `service_usb_startup(1500)`, y la ISR que se habilita al final del setup de `main()`. Con `run_ms = 6000` el audio tiene que arrancar antes de los ~4.5 s.

Si falla un chequeo del LCD, puede ser la orientación. Para mirar la imagen, agregar temporalmente al final del escenario `sim::write_bmp_rgb565("lcd.bmp", r.lcd.data(), 240, 240, 2);` (con `#include "core/file_io.h"`) y abrir el BMP con la herramienta Read. Si está rotada o espejada, corregir `St7789::snapshot_view()` y el test `st7789_view_undoes_rotate_270`. Sacar el volcado temporal antes de commitear.

- [ ] **Step 10: Correr todos los tests por CTest**

```bash
ctest --test-dir build-sim -C Release --output-on-failure
```

Expected: `100% tests passed, 0 tests failed out of 2` (`unit` e `itest_boot`).

- [ ] **Step 11: Commit**

```bash
git add sim/CMakeLists.txt sim/runtime sim/tests/itest_main.cpp
git commit -m "sim: planificador con fibers, HAL y arranque headless del firmware

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Tests de integración de interacción

**Files:**
- Modify: `sim/tests/itest_main.cpp`, `sim/CMakeLists.txt`

**Interfaces:**
- Consumes: `run_headless`, `HeadlessOptions::presses/hot_load_at_ms/hot_bank`, `parse_press_script`, `gamepi_selector` y `piko_audio_sample_count()`.
- Produces: los tests de CTest `itest_mute`, `itest_mode_jump` e `itest_hotload`.

Estos tests validan que el comportamiento de GAMEPI13-INTERFACE.md se reproduce: Start (toque) → mute; Select + botón musical → salto directo de modo; carga en caliente de banco. Si fallan, el error está en el simulador (planificador, HAL o debounce), no en el firmware, que en el hardware funciona.

- [ ] **Step 1: Agregar los escenarios a `sim/tests/itest_main.cpp`**

Reemplazar la cadena `if (scenario == "boot") { ... } else { ... }` por:

```cpp
  std::string err;
  if (scenario == "boot") {
    o.run_ms = 6000;
    if (!run(o, &r)) return 1;
    expect(rms(r.audio, 5000, 6000) > 0.01, "hay audio después del arranque");
    size_t lit = 0;
    for (uint16_t p : r.lcd) lit += p != 0;
    expect(lit > 1000, "el LCD muestra el dashboard");
    expect(mode_square(r, 0) == kWhite, "modo 0 resaltado");
    expect(mode_square(r, 1) == kGray, "modo 1 en gris");
  } else if (scenario == "mute") {
    // Start con un toque simple alterna mute (GAMEPI13-INTERFACE.md §2).
    sim::parse_press_script("6000:START,6150:-START", &o.presses, &err);
    o.run_ms = 7500;
    if (!run(o, &r)) return 1;
    expect(rms(r.audio, 5000, 6000) > 0.01, "suena antes de tocar Start");
    expect(rms(r.audio, 7000, 7500) < 0.001, "silencio después de tocar Start");
  } else if (scenario == "mode_jump") {
    // Select sostenido + Right salta directo al modo 3 (GAMEPI13-INTERFACE.md §3).
    sim::parse_press_script("6000:SELECT,6100:RIGHT,6200:-RIGHT,6300:-SELECT", &o.presses, &err);
    o.run_ms = 7000;
    if (!run(o, &r)) return 1;
    expect(gamepi_selector == 3, "Select+Right salta al modo 3");
    expect(mode_square(r, 3) == kWhite, "modo 3 resaltado en el LCD");
    expect(mode_square(r, 0) == kGray, "modo 0 ya no está resaltado");
  } else if (scenario == "hotload") {
    o.hot_load_at_ms = 5000;
    o.hot_bank = make_synth_bank(5);
    o.run_ms = 6500;
    if (!run(o, &r)) return 1;
    expect(piko_audio_sample_count() == 5, "el banco cargado en caliente tiene 5 samples");
    expect(rms(r.audio, 6000, 6500) > 0.01, "sigue sonando después de la carga");
  } else {
    std::printf("escenario desconocido: %s\n", scenario.c_str());
    return 2;
  }
```

Y en el mensaje de uso, cambiar `"uso: pikocore_sim_itest boot\n"` por `"uso: pikocore_sim_itest boot|mute|mode_jump|hotload|dump_bank ARCHIVO\n"`.

Agregar además, justo después de `const std::string scenario = argv[1];`, la utilidad que escribe el banco sintético a disco. La usan las Tasks 9 y 10 para probar el ejecutable; no se registra en CTest:

```cpp
  if (scenario == "dump_bank") {
    if (argc < 3) {
      std::printf("uso: pikocore_sim_itest dump_bank ARCHIVO\n");
      return 2;
    }
    const std::vector<uint8_t> blob = make_synth_bank(4);
    FILE* f = std::fopen(argv[2], "wb");
    if (f == nullptr) return 1;
    const bool ok = std::fwrite(blob.data(), 1, blob.size(), f) == blob.size();
    std::fclose(f);
    std::printf("banco sintético -> %s\n", argv[2]);
    return ok ? 0 : 1;
  }
```

- [ ] **Step 2: Registrar los escenarios en CMake**

En `sim/CMakeLists.txt`, cambiar `foreach(scenario boot)` por:

```cmake
foreach(scenario boot mute mode_jump hotload)
```

- [ ] **Step 3: Correr todos los tests**

```bash
cmake -S sim -B build-sim > /dev/null; cmake --build build-sim --config Release 2>&1 | grep -E ' error |LNK'; ctest --test-dir build-sim -C Release --output-on-failure
```

Expected: `100% tests passed, 0 tests failed out of 5`. Además:

```bash
build-sim/bin/pikocore_sim_itest.exe dump_bank $(mktemp -d)/b.pikobank; echo "exit=$?"
```

Expected: `banco sintético -> ...b.pikobank` y `exit=0`.

Si falla `mute` o `mode_jump`, correr el escenario directo (`build-sim/bin/pikocore_sim_itest.exe mute`) y revisar el debounce: `Button::Init(pin, 10)` cuenta 10 lecturas, y el bloque `clock_ms % 16` corre ~1.2 kHz virtuales, así que 100–150 ms de pulsación sobran. Si no alcanzan, el planificador está corriendo el lazo de control más lento de lo esperado: medir cuántas veces se llama `sim_wfi` por segundo virtual. Con `__wfi` + `sleep_us(50)` tiene que ser ~19 k/s.

- [ ] **Step 4: Commit**

```bash
git add sim/CMakeLists.txt sim/tests/itest_main.cpp
git commit -m "sim: tests de integración de mute, salto de modo y carga en caliente

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Ejecutable `pikocore_sim` con modo headless

**Files:**
- Create: `sim/app/cli.h`, `sim/app/cli.cpp`, `sim/app/main.cpp`
- Modify: `sim/CMakeLists.txt`

**Interfaces:**
- Consumes: `run_headless`, `read_file`, `write_bmp_rgb565`, `write_wav_mono16`, `parse_press_script` y `kAudioRate`.
- Produces:
  - `struct Cli { std::filesystem::path bank, dump_lcd, dump_wav, flash, capture; bool headless; bool flash_given; bool help; uint32_t run_ms; uint32_t exit_after_ms; std::string press; };`, `bool parse_cli(int argc, wchar_t** argv, Cli* cli, std::string* err)`, `void print_usage()` y `std::string narrow(const std::wstring&)`, en `app/cli.h`, namespace global.
  - `build-sim/bin/pikocore_sim.exe --headless ...`.

- [ ] **Step 1: Implementar `sim/app/cli.h` y `.cpp`**

`sim/app/cli.h`:

```cpp
#pragma once
#include <cstdint>
#include <filesystem>
#include <string>

struct Cli {
  std::filesystem::path bank;
  std::filesystem::path dump_lcd;
  std::filesystem::path dump_wav;
  std::filesystem::path flash;
  std::filesystem::path capture;
  bool headless = false;
  bool flash_given = false;
  bool help = false;
  uint32_t run_ms = 5000;
  uint32_t exit_after_ms = 0;
  std::string press;
};

bool parse_cli(int argc, wchar_t** argv, Cli* cli, std::string* err);
void print_usage();
// Solo para textos ASCII (flags, guion de --press); lo demás pasa a '?'.
std::string narrow(const std::wstring& text);
```

`sim/app/cli.cpp`:

```cpp
#include "app/cli.h"

#include <cstdio>
#include <cwchar>

std::string narrow(const std::wstring& text) {
  std::string out;
  for (wchar_t c : text) out.push_back(c < 128 ? static_cast<char>(c) : '?');
  return out;
}

void print_usage() {
  std::fprintf(stderr,
               "uso: pikocore_sim [banco.pikobank] [opciones]\n"
               "  --bank ARCHIVO        banco .pikobank a cargar al arrancar\n"
               "  --flash ARCHIVO       flash persistente (default: pikocore_sim_flash.bin\n"
               "                        junto al .exe; con --headless, solo en memoria)\n"
               "  --headless            sin ventana ni audio, lo más rápido posible\n"
               "  --run-ms N            (headless) ms virtuales a correr (default 5000)\n"
               "  --press GUION         (headless) botones, ej. \"6000:A+B,6200:-A\"\n"
               "  --dump-lcd ARCHIVO    (headless) guarda la pantalla final como BMP\n"
               "  --dump-wav ARCHIVO    (headless) guarda el audio como WAV\n"
               "  --capture ARCHIVO     (ventana) guarda la ventana como BMP al salir\n"
               "  --exit-after-ms N     (ventana) se cierra sola después de N ms\n"
               "botones: UP DOWN LEFT RIGHT A B X Y L R SELECT START\n");
}

bool parse_cli(int argc, wchar_t** argv, Cli* cli, std::string* err) {
  for (int i = 1; i < argc; ++i) {
    const std::wstring arg = argv[i];
    const bool takes_value = arg == L"--bank" || arg == L"--flash" || arg == L"--run-ms" ||
                             arg == L"--press" || arg == L"--dump-lcd" ||
                             arg == L"--dump-wav" || arg == L"--capture" ||
                             arg == L"--exit-after-ms";
    if (takes_value && i + 1 >= argc) {
      *err = "falta el valor de " + narrow(arg);
      return false;
    }
    if (arg == L"--help" || arg == L"-h") {
      cli->help = true;
    } else if (arg == L"--headless") {
      cli->headless = true;
    } else if (arg == L"--bank") {
      cli->bank = argv[++i];
    } else if (arg == L"--flash") {
      cli->flash = argv[++i];
      cli->flash_given = true;
    } else if (arg == L"--run-ms") {
      cli->run_ms = static_cast<uint32_t>(std::wcstoul(argv[++i], nullptr, 10));
      if (cli->run_ms == 0) {
        *err = "--run-ms tiene que ser mayor que 0";
        return false;
      }
    } else if (arg == L"--press") {
      cli->press = narrow(argv[++i]);
    } else if (arg == L"--dump-lcd") {
      cli->dump_lcd = argv[++i];
    } else if (arg == L"--dump-wav") {
      cli->dump_wav = argv[++i];
    } else if (arg == L"--capture") {
      cli->capture = argv[++i];
    } else if (arg == L"--exit-after-ms") {
      cli->exit_after_ms = static_cast<uint32_t>(std::wcstoul(argv[++i], nullptr, 10));
    } else if (!arg.empty() && arg[0] == L'-') {
      *err = "opción desconocida: " + narrow(arg);
      return false;
    } else {
      cli->bank = arg;
    }
  }
  return true;
}
```

- [ ] **Step 2: Implementar `sim/app/main.cpp`**

```cpp
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "app/cli.h"
#include "core/file_io.h"
#include "core/press_script.h"
#include "core/st7789.h"
#include "runtime/headless.h"
#include "runtime/machine.h"

namespace {

int run_headless_cli(const Cli& cli) {
  sim::HeadlessOptions o;
  o.run_ms = cli.run_ms;
  o.flash_path = cli.flash;  // vacío = solo memoria
  if (!cli.bank.empty() && !sim::read_file(cli.bank, &o.bank)) {
    std::fprintf(stderr, "no se pudo leer el banco\n");
    return 1;
  }
  std::string err;
  if (!sim::parse_press_script(cli.press, &o.presses, &err)) {
    std::fprintf(stderr, "--press: %s\n", err.c_str());
    return 2;
  }
  sim::HeadlessResult r;
  if (!sim::run_headless(o, &r, &err)) {
    std::fprintf(stderr, "error: %s\n", err.c_str());
    return 1;
  }
  std::printf("pikocore-sim: %u ms virtuales en %.2f s (x%.2f)\n", o.run_ms, r.wall_seconds,
              o.run_ms / 1000.0 / r.wall_seconds);
  if (!cli.dump_lcd.empty()) {
    if (!sim::write_bmp_rgb565(cli.dump_lcd, r.lcd.data(), sim::St7789::kSize,
                               sim::St7789::kSize, 2)) {
      std::fprintf(stderr, "no se pudo escribir el BMP\n");
      return 1;
    }
    std::printf("LCD -> %s\n", narrow(cli.dump_lcd.wstring()).c_str());
  }
  if (!cli.dump_wav.empty()) {
    if (!sim::write_wav_mono16(cli.dump_wav, r.audio, sim::kAudioRate)) {
      std::fprintf(stderr, "no se pudo escribir el WAV\n");
      return 1;
    }
    std::printf("audio -> %s (%zu muestras)\n", narrow(cli.dump_wav.wstring()).c_str(),
                r.audio.size());
  }
  return 0;
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
  Cli cli;
  std::string err;
  if (!parse_cli(argc, argv, &cli, &err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    print_usage();
    return 2;
  }
  if (cli.help) {
    print_usage();
    return 0;
  }
  if (cli.headless) return run_headless_cli(cli);
  std::fprintf(stderr, "el modo con ventana llega en la Task 10; usá --headless\n");
  return 2;
}
```

- [ ] **Step 3: Registrar el ejecutable en CMake**

Agregar al final de `sim/CMakeLists.txt`:

```cmake
# ---- el simulador ----
add_executable(pikocore_sim
  app/main.cpp
  app/cli.cpp
)
target_link_libraries(pikocore_sim PRIVATE sim_runtime)
target_include_directories(pikocore_sim PRIVATE ${SIM_ROOT})
target_compile_definitions(pikocore_sim PRIVATE NOMINMAX WIN32_LEAN_AND_MEAN UNICODE _UNICODE)
target_compile_options(pikocore_sim PRIVATE /W4 /utf-8)
```

- [ ] **Step 4: Compilar y generar un pantallazo y un WAV**

```bash
cmake -S sim -B build-sim > /dev/null; cmake --build build-sim --config Release --target pikocore_sim 2>&1 | grep -E ' error |LNK'
OUT=$(mktemp -d)
build-sim/bin/pikocore_sim_itest.exe dump_bank $OUT/test.pikobank
build-sim/bin/pikocore_sim.exe --headless --bank $OUT/test.pikobank --run-ms 6000 --dump-lcd $OUT/lcd.bmp --dump-wav $OUT/audio.wav; echo "exit=$?"; ls -la $OUT
build-sim/bin/pikocore_sim.exe --help; echo "exit=$?"
```

Expected: `banco sintético -> ...test.pikobank`; `pikocore-sim: 6000 ms virtuales en ...`; `LCD -> ...lcd.bmp`; `audio -> ...audio.wav (≈288000 muestras)`; `exit=0`. Después, el texto de uso y `exit=0`.

- [ ] **Step 5: Verificar la orientación del LCD mirando el pantallazo**

Abrir `$OUT/lcd.bmp` con la herramienta Read, que muestra imágenes. Debe verse el dashboard **derecho**: BPM arriba a la izquierda, los íconos play/stop arriba a la derecha y la fila de 8 cuadrados abajo, con el primero en blanco. El texto tiene que leerse, no espejado.

Si está rotado o espejado, corregir la fórmula de `St7789::snapshot_view()` en `sim/core/st7789.cpp` y el test `st7789_view_undoes_rotate_270`, que asume vista(x, y) = raw(y, 239 − x). Después correr `ctest --test-dir build-sim -C Release` de nuevo.

- [ ] **Step 6: Verificar los errores de la línea de comandos**

```bash
build-sim/bin/pikocore_sim.exe --headless --press "100:FOO"; echo "exit=$?"
build-sim/bin/pikocore_sim.exe --nada; echo "exit=$?"
```

Expected: `--press: botón desconocido "FOO"` con `exit=2`; `opción desconocida: --nada`, el uso y `exit=2`.

- [ ] **Step 7: Commit**

```bash
git add sim/CMakeLists.txt sim/app/cli.h sim/app/cli.cpp sim/app/main.cpp
git commit -m "sim: ejecutable pikocore_sim con modo headless (--dump-lcd/--dump-wav)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Modo ventana — XInput, WASAPI y GDI

**Files:**
- Create: `sim/platform/audio_out.h`, `sim/platform/audio_out.cpp`, `sim/platform/pad_input.h`, `sim/platform/pad_input.cpp`, `sim/platform/sim_window.h`, `sim/platform/sim_window.cpp`, `sim/app/windowed.h`, `sim/app/windowed.cpp`
- Modify: `sim/app/main.cpp`, `sim/CMakeLists.txt`

**Interfaces:**
- Consumes: `Machine`, `sim_io.h`, `hot_load_bank`, `write_bank_to_flash`, `check_and_patch_bank`, `AudioRing`, `map_xinput`, `button_for_vk`, `write_bmp`, `rgb565_to_rgb888`, `Cli`, `piko_audio_sample_count()` y `piko_firmware_main`.
- Produces:
  - `class sim::AudioOut { bool start(AudioRing*, std::string* err); void stop(); uint64_t frames_consumed() const; }`.
  - `class sim::PadInput { void start(std::function<void(uint16_t)> on_mask); void stop(); void set_keyboard_mask(uint16_t); bool connected() const; }`.
  - `struct sim::WindowHooks` e `int sim::run_window(const WindowHooks&, const std::filesystem::path& capture, uint32_t exit_after_ms)`.
  - `int run_windowed(const Cli&)`, en `app/windowed.h`.

**Hilos en modo ventana:**
- **Principal:** ventana y message loop.
- **Emulación:** `Machine::boot` + `run_until` en tramos de 1 ms, con pacing: corre si lo producido va menos de 30 ms por delante de lo que WASAPI consumió. También aplica las cargas de banco pendientes.
- **WASAPI.**
- **XInput:** 500 Hz.

Estado compartido: la máscara de botones (atómica), la GRAM del LCD (con mutex) y `Shared` (con mutex).

- [ ] **Step 1: Implementar `sim/platform/audio_out.h` y `.cpp`**

`sim/platform/audio_out.h`:

```cpp
#pragma once
#include <atomic>
#include <cstdint>
#include <future>
#include <string>
#include <thread>

#include "core/audio_ring.h"

namespace sim {

// Salida de audio por WASAPI en modo compartido, event-driven. Lee el ring
// (mono, 48 kHz, float) y duplica a estéreo; Windows convierte a la
// frecuencia del dispositivo (AUTOCONVERTPCM).
class AudioOut {
 public:
  ~AudioOut();
  bool start(AudioRing* ring, std::string* err);
  void stop();
  // Frames entregados al dispositivo (incluye silencio si el ring estaba vacío).
  uint64_t frames_consumed() const { return consumed_.load(); }

 private:
  void run(AudioRing* ring, std::promise<std::string>* ready);

  std::thread thread_;
  std::atomic<bool> quit_{false};
  std::atomic<uint64_t> consumed_{0};
};

}  // namespace sim
```

`sim/platform/audio_out.cpp`:

```cpp
#include "platform/audio_out.h"

#include <windows.h>
#include <mmreg.h>
#include <audioclient.h>
#include <ksmedia.h>
#include <mmdeviceapi.h>

#include <cstdio>
#include <vector>

namespace sim {

namespace {
template <class T>
void release(T*& p) {
  if (p != nullptr) {
    p->Release();
    p = nullptr;
  }
}
}  // namespace

AudioOut::~AudioOut() { stop(); }

bool AudioOut::start(AudioRing* ring, std::string* err) {
  std::promise<std::string> ready;
  std::future<std::string> result = ready.get_future();
  quit_ = false;
  thread_ = std::thread([this, ring, &ready] { run(ring, &ready); });
  const std::string failure = result.get();
  if (!failure.empty()) {
    thread_.join();
    if (err != nullptr) *err = failure;
    return false;
  }
  return true;
}

void AudioOut::stop() {
  quit_ = true;
  if (thread_.joinable()) thread_.join();
}

void AudioOut::run(AudioRing* ring, std::promise<std::string>* ready) {
  CoInitializeEx(nullptr, COINIT_MULTITHREADED);
  IMMDeviceEnumerator* enumerator = nullptr;
  IMMDevice* device = nullptr;
  IAudioClient* client = nullptr;
  IAudioRenderClient* render = nullptr;
  HANDLE event = CreateEventW(nullptr, FALSE, FALSE, nullptr);

  WAVEFORMATEXTENSIBLE fmt = {};
  fmt.Format.wFormatTag = WAVE_FORMAT_EXTENSIBLE;
  fmt.Format.nChannels = 2;
  fmt.Format.nSamplesPerSec = 48000;
  fmt.Format.wBitsPerSample = 32;
  fmt.Format.nBlockAlign = 8;
  fmt.Format.nAvgBytesPerSec = 48000 * 8;
  fmt.Format.cbSize = sizeof(WAVEFORMATEXTENSIBLE) - sizeof(WAVEFORMATEX);
  fmt.Samples.wValidBitsPerSample = 32;
  fmt.dwChannelMask = SPEAKER_FRONT_LEFT | SPEAKER_FRONT_RIGHT;
  fmt.SubFormat = KSDATAFORMAT_SUBTYPE_IEEE_FLOAT;

  UINT32 buffer_frames = 0;
  HRESULT hr = CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                                __uuidof(IMMDeviceEnumerator), reinterpret_cast<void**>(&enumerator));
  if (SUCCEEDED(hr)) hr = enumerator->GetDefaultAudioEndpoint(eRender, eConsole, &device);
  if (SUCCEEDED(hr)) {
    hr = device->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr,
                          reinterpret_cast<void**>(&client));
  }
  if (SUCCEEDED(hr)) {
    hr = client->Initialize(AUDCLNT_SHAREMODE_SHARED,
                            AUDCLNT_STREAMFLAGS_EVENTCALLBACK | AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM |
                                AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY,
                            100000 /* 10 ms */, 0, &fmt.Format, nullptr);
  }
  if (SUCCEEDED(hr)) hr = client->SetEventHandle(event);
  if (SUCCEEDED(hr)) hr = client->GetBufferSize(&buffer_frames);
  if (SUCCEEDED(hr)) {
    hr = client->GetService(__uuidof(IAudioRenderClient), reinterpret_cast<void**>(&render));
  }
  if (SUCCEEDED(hr)) hr = client->Start();

  std::string failure;
  if (FAILED(hr)) {
    char msg[64];
    std::snprintf(msg, sizeof(msg), "WASAPI falló (0x%08lx)", static_cast<unsigned long>(hr));
    failure = msg;
  }
  ready->set_value(failure);  // después de esto no se toca más `ready`

  std::vector<float> mono(buffer_frames);
  while (failure.empty() && !quit_) {
    WaitForSingleObject(event, 100);
    UINT32 padding = 0;
    if (FAILED(client->GetCurrentPadding(&padding))) break;
    const UINT32 avail = buffer_frames - padding;
    if (avail == 0) continue;
    BYTE* data = nullptr;
    if (FAILED(render->GetBuffer(avail, &data))) break;
    const size_t got = ring->pop(mono.data(), avail);
    float* out = reinterpret_cast<float*>(data);
    for (UINT32 i = 0; i < avail; ++i) {
      const float s = i < got ? mono[i] : 0.0f;
      out[2 * i] = s;
      out[2 * i + 1] = s;
    }
    render->ReleaseBuffer(avail, 0);
    consumed_ += avail;
  }

  if (client != nullptr) client->Stop();
  release(render);
  release(client);
  release(device);
  release(enumerator);
  CloseHandle(event);
  CoUninitialize();
}

}  // namespace sim
```

- [ ] **Step 2: Implementar `sim/platform/pad_input.h` y `.cpp`**

`sim/platform/pad_input.h`:

```cpp
#pragma once
#include <atomic>
#include <cstdint>
#include <functional>
#include <thread>

namespace sim {

// Lee el primer control XInput conectado a 500 Hz, lo combina con el teclado y
// entrega la máscara de sim::Button a on_mask (desde su propio hilo).
class PadInput {
 public:
  ~PadInput();
  void start(std::function<void(uint16_t)> on_mask);
  void stop();
  void set_keyboard_mask(uint16_t mask) { keyboard_ = mask; }
  bool connected() const { return connected_; }

 private:
  void run();

  std::thread thread_;
  std::atomic<bool> quit_{false};
  std::atomic<uint16_t> keyboard_{0};
  std::atomic<bool> connected_{false};
  std::function<void(uint16_t)> on_mask_;
};

}  // namespace sim
```

`sim/platform/pad_input.cpp`:

```cpp
#include "platform/pad_input.h"

#include <windows.h>
#include <Xinput.h>

#include <chrono>

#include "core/buttons.h"

namespace sim {

PadInput::~PadInput() { stop(); }

void PadInput::start(std::function<void(uint16_t)> on_mask) {
  on_mask_ = std::move(on_mask);
  quit_ = false;
  thread_ = std::thread([this] { run(); });
}

void PadInput::stop() {
  quit_ = true;
  if (thread_.joinable()) thread_.join();
}

void PadInput::run() {
  using clock = std::chrono::steady_clock;
  int slot = -1;
  clock::time_point next_scan = clock::now();
  while (!quit_) {
    uint16_t pad = 0;
    const clock::time_point now = clock::now();
    if (slot < 0 && now >= next_scan) {
      // XInputGetState es caro sobre un slot vacío: buscar una vez por segundo.
      for (DWORD i = 0; i < XUSER_MAX_COUNT && slot < 0; ++i) {
        XINPUT_STATE state = {};
        if (XInputGetState(i, &state) == ERROR_SUCCESS) slot = static_cast<int>(i);
      }
      next_scan = now + std::chrono::seconds(1);
    }
    if (slot >= 0) {
      XINPUT_STATE state = {};
      if (XInputGetState(static_cast<DWORD>(slot), &state) == ERROR_SUCCESS) {
        pad = map_xinput(state.Gamepad.wButtons);
      } else {
        slot = -1;
        next_scan = now + std::chrono::seconds(1);
      }
    }
    connected_ = slot >= 0;
    on_mask_(static_cast<uint16_t>(pad | keyboard_.load()));
    Sleep(2);
  }
}

}  // namespace sim
```

- [ ] **Step 3: Implementar `sim/platform/sim_window.h`**

```cpp
#pragma once
#include <cstdint>
#include <filesystem>
#include <functional>
#include <string>

namespace sim {

struct WindowHooks {
  std::function<void(uint16_t* out)> snapshot_lcd;  // 240x240 RGB565, vista
  std::function<uint16_t()> button_mask;            // bits = sim::Button
  std::function<bool()> beat_led;
  std::function<uint16_t()> backlight;               // 0-65535
  std::function<std::wstring()> status;
  std::function<void(uint16_t)> keyboard_mask;
  std::function<void(const std::filesystem::path&)> file_dropped;
};

// Abre la ventana y corre el message loop hasta que se cierre. Con
// exit_after_ms > 0 se cierra sola, y si capture no está vacío guarda la
// ventana como BMP antes: sirve para verificarla sin intervención.
int run_window(const WindowHooks& hooks, const std::filesystem::path& capture,
               uint32_t exit_after_ms);

}  // namespace sim
```

- [ ] **Step 4: Implementar `sim/platform/sim_window.cpp`**

```cpp
#include "platform/sim_window.h"

#include <windows.h>
#include <shellapi.h>

#include <vector>

#include "core/buttons.h"
#include "core/file_io.h"
#include "core/st7789.h"

namespace sim {

namespace {

constexpr int kW = 820;
constexpr int kH = 600;
constexpr int kLcdX = 170;
constexpr int kLcdY = 30;
constexpr int kLcdPx = St7789::kSize * 2;  // LCD escalado x2

struct Shape {
  Button button;
  RECT rect;
  bool round;
  const wchar_t* label;
};

// D-pad centrado en (85, 270), botones de cara en (730, 270), con 52 px entre centros.
const Shape kShapes[] = {
    {kUp, {63, 196, 107, 240}, false, L"\u25B2"},
    {kDown, {63, 300, 107, 344}, false, L"\u25BC"},
    {kLeft, {11, 248, 55, 292}, false, L"\u25C0"},
    {kRight, {115, 248, 159, 292}, false, L"\u25B6"},
    {kX, {708, 196, 752, 240}, true, L"X"},
    {kY, {656, 248, 700, 292}, true, L"Y"},
    {kA, {760, 248, 804, 292}, true, L"A"},
    {kB, {708, 300, 752, 344}, true, L"B"},
    {kL, {30, 40, 140, 70}, false, L"L"},
    {kR, {680, 40, 790, 70}, false, L"R"},
    {kSelect, {30, 470, 140, 500}, false, L"SELECT"},
    {kStart, {680, 470, 790, 500}, false, L"START"},
};

struct State {
  const WindowHooks* hooks = nullptr;
  std::filesystem::path capture;
  uint32_t exit_after_ms = 0;
  ULONGLONG start_ms = 0;
  HDC mem_dc = nullptr;
  HBITMAP dib = nullptr;
  HGDIOBJ old_bitmap = nullptr;
  uint32_t* dib_px = nullptr;
  HFONT label_font = nullptr;
  HFONT status_font = nullptr;
  uint16_t keyboard = 0;
  std::vector<uint16_t> lcd = std::vector<uint16_t>(St7789::kSize * St7789::kSize);
  std::vector<uint32_t> lcd_rgb = std::vector<uint32_t>(St7789::kSize * St7789::kSize);
};
State g;

BITMAPINFO bitmap_info(int w, int h) {
  BITMAPINFO bmi = {};
  bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  bmi.bmiHeader.biWidth = w;
  bmi.bmiHeader.biHeight = -h;  // de arriba hacia abajo
  bmi.bmiHeader.biPlanes = 1;
  bmi.bmiHeader.biBitCount = 32;
  bmi.bmiHeader.biCompression = BI_RGB;
  return bmi;
}

void fill(HDC dc, const RECT& r, COLORREF color) {
  HBRUSH brush = CreateSolidBrush(color);
  FillRect(dc, &r, brush);
  DeleteObject(brush);
}

void draw_shape(HDC dc, const Shape& s, bool pressed) {
  HBRUSH brush = CreateSolidBrush(pressed ? RGB(235, 235, 235) : RGB(78, 78, 86));
  HPEN pen = CreatePen(PS_SOLID, 1, RGB(20, 20, 24));
  HGDIOBJ old_brush = SelectObject(dc, brush);
  HGDIOBJ old_pen = SelectObject(dc, pen);
  if (s.round) {
    Ellipse(dc, s.rect.left, s.rect.top, s.rect.right, s.rect.bottom);
  } else {
    RoundRect(dc, s.rect.left, s.rect.top, s.rect.right, s.rect.bottom, 10, 10);
  }
  SelectObject(dc, old_brush);
  SelectObject(dc, old_pen);
  DeleteObject(brush);
  DeleteObject(pen);
  SetTextColor(dc, pressed ? RGB(20, 20, 20) : RGB(225, 225, 225));
  RECT r = s.rect;
  DrawTextW(dc, s.label, -1, &r, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
}

void draw_lcd(HDC dc) {
  g.hooks->snapshot_lcd(g.lcd.data());
  const uint32_t backlight = g.hooks->backlight();
  for (size_t i = 0; i < g.lcd.size(); ++i) {
    const uint32_t c = rgb565_to_rgb888(g.lcd[i]);
    const uint32_t r = ((c >> 16) & 255u) * backlight / 65535u;
    const uint32_t gr = ((c >> 8) & 255u) * backlight / 65535u;
    const uint32_t b = (c & 255u) * backlight / 65535u;
    g.lcd_rgb[i] = (r << 16) | (gr << 8) | b;
  }
  const BITMAPINFO bmi = bitmap_info(St7789::kSize, St7789::kSize);
  SetStretchBltMode(dc, COLORONCOLOR);
  StretchDIBits(dc, kLcdX, kLcdY, kLcdPx, kLcdPx, 0, 0, St7789::kSize, St7789::kSize,
                g.lcd_rgb.data(), &bmi, DIB_RGB_COLORS, SRCCOPY);
}

void paint(HDC dc) {
  const RECT all = {0, 0, kW, kH};
  fill(dc, all, RGB(24, 24, 27));

  HBRUSH body = CreateSolidBrush(RGB(52, 52, 58));
  HGDIOBJ old_brush = SelectObject(dc, body);
  HGDIOBJ old_pen = SelectObject(dc, GetStockObject(NULL_PEN));
  RoundRect(dc, 10, 10, 810, 540, 40, 40);
  SelectObject(dc, old_brush);
  SelectObject(dc, old_pen);
  DeleteObject(body);

  const RECT bezel = {kLcdX - 6, kLcdY - 6, kLcdX + kLcdPx + 6, kLcdY + kLcdPx + 6};
  fill(dc, bezel, RGB(0, 0, 0));
  draw_lcd(dc);

  SetBkMode(dc, TRANSPARENT);
  HGDIOBJ old_font = SelectObject(dc, g.label_font);
  const uint16_t mask = g.hooks->button_mask();
  for (const Shape& s : kShapes) draw_shape(dc, s, (mask & bit(s.button)) != 0);

  // LED de beat (GP28)
  HBRUSH led = CreateSolidBrush(g.hooks->beat_led() ? RGB(255, 60, 40) : RGB(70, 30, 30));
  old_brush = SelectObject(dc, led);
  old_pen = SelectObject(dc, GetStockObject(NULL_PEN));
  Ellipse(dc, 78, 113, 93, 128);
  SelectObject(dc, old_brush);
  SelectObject(dc, old_pen);
  DeleteObject(led);

  SelectObject(dc, g.status_font);
  SetTextColor(dc, RGB(170, 170, 170));
  RECT status = {16, 548, kW - 16, 592};
  const std::wstring text = g.hooks->status();
  DrawTextW(dc, text.c_str(), -1, &status, DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS);
  SelectObject(dc, old_font);
}

void capture_and_close(HWND hwnd) {
  KillTimer(hwnd, 1);
  if (!g.capture.empty()) {
    paint(g.mem_dc);
    GdiFlush();
    write_bmp(g.capture, kW, kH, [](int x, int y) {
      return g.dib_px[static_cast<size_t>(y) * kW + x] & 0xFFFFFFu;
    });
  }
  DestroyWindow(hwnd);
}

void set_keyboard(uint16_t mask) {
  g.keyboard = mask;
  g.hooks->keyboard_mask(mask);
}

LRESULT CALLBACK wnd_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
  switch (msg) {
    case WM_CREATE: {
      HDC window_dc = GetDC(hwnd);
      g.mem_dc = CreateCompatibleDC(window_dc);
      ReleaseDC(hwnd, window_dc);
      const BITMAPINFO bmi = bitmap_info(kW, kH);
      g.dib = CreateDIBSection(g.mem_dc, &bmi, DIB_RGB_COLORS,
                               reinterpret_cast<void**>(&g.dib_px), nullptr, 0);
      g.old_bitmap = SelectObject(g.mem_dc, g.dib);
      g.label_font = CreateFontW(-15, 0, 0, 0, FW_BOLD, 0, 0, 0, DEFAULT_CHARSET, 0, 0,
                                 CLEARTYPE_QUALITY, 0, L"Segoe UI");
      g.status_font = CreateFontW(-14, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0,
                                  CLEARTYPE_QUALITY, 0, L"Segoe UI");
      DragAcceptFiles(hwnd, TRUE);
      SetTimer(hwnd, 1, 16, nullptr);
      g.start_ms = GetTickCount64();
      return 0;
    }
    case WM_TIMER:
      if (g.exit_after_ms > 0 && GetTickCount64() - g.start_ms >= g.exit_after_ms) {
        capture_and_close(hwnd);
        return 0;
      }
      InvalidateRect(hwnd, nullptr, FALSE);
      return 0;
    case WM_ERASEBKGND:
      return 1;
    case WM_PAINT: {
      PAINTSTRUCT ps;
      HDC dc = BeginPaint(hwnd, &ps);
      paint(g.mem_dc);
      BitBlt(dc, 0, 0, kW, kH, g.mem_dc, 0, 0, SRCCOPY);
      EndPaint(hwnd, &ps);
      return 0;
    }
    case WM_KEYDOWN:
    case WM_KEYUP:
    case WM_SYSKEYDOWN:
    case WM_SYSKEYUP: {
      const int b = button_for_vk(static_cast<unsigned>(wp));
      if (b < 0) break;
      const bool down = msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN;
      const uint16_t bitmask = bit(static_cast<Button>(b));
      set_keyboard(static_cast<uint16_t>(down ? (g.keyboard | bitmask) : (g.keyboard & ~bitmask)));
      return 0;
    }
    case WM_KILLFOCUS:
      set_keyboard(0);
      return 0;
    case WM_DROPFILES: {
      HDROP drop = reinterpret_cast<HDROP>(wp);
      wchar_t path[MAX_PATH];
      if (DragQueryFileW(drop, 0, path, MAX_PATH) > 0) g.hooks->file_dropped(path);
      DragFinish(drop);
      return 0;
    }
    case WM_DESTROY:
      KillTimer(hwnd, 1);
      PostQuitMessage(0);
      return 0;
    default:
      break;
  }
  return DefWindowProcW(hwnd, msg, wp, lp);
}

}  // namespace

int run_window(const WindowHooks& hooks, const std::filesystem::path& capture,
               uint32_t exit_after_ms) {
  g.hooks = &hooks;
  g.capture = capture;
  g.exit_after_ms = exit_after_ms;

  HINSTANCE instance = GetModuleHandleW(nullptr);
  WNDCLASSW wc = {};
  wc.lpfnWndProc = wnd_proc;
  wc.hInstance = instance;
  wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
  wc.lpszClassName = L"PikocoreSim";
  RegisterClassW(&wc);

  const DWORD style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
  RECT r = {0, 0, kW, kH};
  AdjustWindowRect(&r, style, FALSE);
  HWND hwnd = CreateWindowW(L"PikocoreSim", L"pikocore-sim — GamePi13", style, CW_USEDEFAULT,
                            CW_USEDEFAULT, r.right - r.left, r.bottom - r.top, nullptr, nullptr,
                            instance, nullptr);
  if (hwnd == nullptr) return 1;
  ShowWindow(hwnd, SW_SHOW);

  MSG msg;
  while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
    TranslateMessage(&msg);
    DispatchMessageW(&msg);
  }

  SelectObject(g.mem_dc, g.old_bitmap);
  DeleteObject(g.dib);
  DeleteDC(g.mem_dc);
  DeleteObject(g.label_font);
  DeleteObject(g.status_font);
  return 0;
}

}  // namespace sim
```

- [ ] **Step 5: Implementar `sim/app/windowed.h` y `.cpp`**

`sim/app/windowed.h`:

```cpp
#pragma once
#include "app/cli.h"

// Modo normal: ventana, audio WASAPI y control XInput.
int run_windowed(const Cli& cli);
```

`sim/app/windowed.cpp`:

```cpp
#include "app/windowed.h"

#include <windows.h>
#include <timeapi.h>

#include <atomic>
#include <chrono>
#include <cstdio>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include "PikoAudioBank.h"
#include "core/audio_ring.h"
#include "core/bank_file.h"
#include "core/file_io.h"
#include "core/flash_store.h"
#include "platform/audio_out.h"
#include "platform/pad_input.h"
#include "platform/sim_window.h"
#include "runtime/bank_hotload.h"
#include "runtime/firmware_entry.h"
#include "runtime/machine.h"
#include "runtime/sim_io.h"

namespace {

struct Shared {
  std::mutex mutex;
  std::optional<std::vector<uint8_t>> pending_bank;  // protegido por mutex
  std::wstring pending_name;                          // protegido por mutex
  std::wstring bank_status;                           // protegido por mutex; "" = sin cargar
  std::atomic<uint32_t> sample_count{0};
  std::atomic<float> speed{0.0f};
  std::atomic<bool> quit{false};
};

std::wstring utf8_to_wide(const std::string& s) {
  if (s.empty()) return {};
  const int n = MultiByteToWideChar(CP_UTF8, 0, s.data(), static_cast<int>(s.size()), nullptr, 0);
  std::wstring w(static_cast<size_t>(n), L'\0');
  MultiByteToWideChar(CP_UTF8, 0, s.data(), static_cast<int>(s.size()), w.data(), n);
  return w;
}

std::filesystem::path default_flash_path() {
  wchar_t exe[MAX_PATH];
  GetModuleFileNameW(nullptr, exe, MAX_PATH);
  return std::filesystem::path(exe).parent_path() / L"pikocore_sim_flash.bin";
}

std::wstring loaded_status(const sim::BankCheck& check, const std::wstring& name) {
  std::wstring s = L"Banco: " + std::to_wstring(check.sample_count) + L" samples (" + name + L")";
  if (check.capacity_patched) s += L", capacidad corregida";
  return s;
}

// Corre en el hilo de emulación, entre dos run_until(): atómico respecto del firmware.
void apply_pending_bank(Shared* sh) {
  std::vector<uint8_t> blob;
  std::wstring name;
  {
    std::lock_guard<std::mutex> lock(sh->mutex);
    if (!sh->pending_bank) return;
    blob = std::move(*sh->pending_bank);
    name = sh->pending_name;
    sh->pending_bank.reset();
  }
  const sim::BankCheck check = sim::check_and_patch_bank(blob);
  if (check.ok) sim::hot_load_bank(blob);
  std::lock_guard<std::mutex> lock(sh->mutex);
  sh->bank_status = check.ok ? loaded_status(check, name)
                             : L"Banco rechazado (" + name + L"): " + utf8_to_wide(check.error);
}

void emulation_thread(Shared* sh, sim::AudioRing* ring, const sim::AudioOut* audio, bool audio_ok) {
  using clock = std::chrono::steady_clock;
  sim::Machine& m = sim::Machine::get();
  uint64_t produced = 0;
  m.dac().set_sink([&](float s) {
    ring->push(s);
    ++produced;
  });
  m.boot(&piko_firmware_main);

  constexpr uint64_t kLeadFrames = sim::kAudioRate * 30 / 1000;  // 30 ms por delante
  const clock::time_point wall0 = clock::now();
  clock::time_point speed_mark = wall0;
  uint64_t speed_cycles = 0;
  while (!sh->quit) {
    apply_pending_bank(sh);
    const clock::time_point now = clock::now();
    const uint64_t consumed =
        audio_ok ? audio->frames_consumed()
                 : static_cast<uint64_t>(std::chrono::duration<double>(now - wall0).count() *
                                         sim::kAudioRate);
    if (produced < consumed + kLeadFrames) {
      m.run_until(m.now_cycles() + sim::kCpuHz / 1000);
    } else {
      Sleep(1);
    }
    sh->sample_count = piko_audio_sample_count();
    const double elapsed = std::chrono::duration<double>(now - speed_mark).count();
    if (elapsed >= 0.5) {
      sh->speed = static_cast<float>((m.now_cycles() - speed_cycles) /
                                     static_cast<double>(sim::kCpuHz) / elapsed);
      speed_cycles = m.now_cycles();
      speed_mark = now;
    }
  }
}

}  // namespace

int run_windowed(const Cli& cli) {
  // Si nos lanzaron con doble click, la consola es nuestra: se oculta.
  DWORD pids[2];
  if (GetConsoleProcessList(pids, 2) <= 1) FreeConsole();
  timeBeginPeriod(1);  // Sleep(1) de verdad ~1 ms, para el pacing

  Shared sh;
  std::string err;
  const std::filesystem::path flash_path = cli.flash_given ? cli.flash : default_flash_path();
  if (!sim::flash().open(flash_path, &err)) {
    MessageBoxW(nullptr, utf8_to_wide(err).c_str(), L"pikocore-sim", MB_ICONERROR);
    timeEndPeriod(1);
    return 1;
  }
  if (!cli.bank.empty()) {
    std::vector<uint8_t> blob;
    const std::wstring name = cli.bank.filename().wstring();
    if (!sim::read_file(cli.bank, &blob)) {
      sh.bank_status = L"Banco: no se pudo leer " + name;
    } else {
      const sim::BankCheck check = sim::check_and_patch_bank(blob);
      if (check.ok) {
        sim::write_bank_to_flash(blob);  // antes del boot: el firmware lo lee al arrancar
        sh.bank_status = loaded_status(check, name);
      } else {
        sh.bank_status = L"Banco rechazado (" + name + L"): " + utf8_to_wide(check.error);
      }
    }
  }

  sim::AudioRing ring(sim::kAudioRate / 2);  // 500 ms de margen
  sim::AudioOut audio;
  std::string audio_err;
  const bool audio_ok = audio.start(&ring, &audio_err);
  sim::PadInput pad;
  pad.start([](uint16_t mask) { sim::set_button_mask(mask); });
  std::thread emu(emulation_thread, &sh, &ring, &audio, audio_ok);

  sim::WindowHooks hooks;
  hooks.snapshot_lcd = [](uint16_t* out) { sim::Machine::get().lcd().snapshot_view(out); };
  hooks.button_mask = [] { return sim::button_mask(); };
  hooks.beat_led = [] { return sim::beat_led(); };
  hooks.backlight = [] { return sim::backlight_level(); };
  hooks.keyboard_mask = [&pad](uint16_t mask) { pad.set_keyboard_mask(mask); };
  hooks.file_dropped = [&sh](const std::filesystem::path& path) {
    std::vector<uint8_t> blob;
    const bool ok = sim::read_file(path, &blob);
    std::lock_guard<std::mutex> lock(sh.mutex);
    if (!ok) {
      sh.bank_status = L"Banco: no se pudo leer " + path.filename().wstring();
      return;
    }
    sh.pending_bank = std::move(blob);
    sh.pending_name = path.filename().wstring();
  };
  hooks.status = [&sh, &pad, audio_ok] {
    std::wstring s = pad.connected()
                         ? L"Control XInput conectado"
                         : L"Sin control: flechas, W/A/S/D, Q/E, Enter, Backspace";
    std::wstring bank;
    {
      std::lock_guard<std::mutex> lock(sh.mutex);
      bank = sh.bank_status;
    }
    if (bank.empty()) {
      bank = sh.sample_count > 0
                 ? L"Banco: " + std::to_wstring(sh.sample_count.load()) + L" samples (en la flash)"
                 : L"Banco: ninguno, arrastrá un .pikobank a la ventana";
    }
    s += L"  ·  " + bank;
    s += audio_ok ? L"  ·  Audio WASAPI" : L"  ·  Sin audio";
    wchar_t speed[32];
    swprintf(speed, 32, L"  ·  x%.2f", sh.speed.load());
    return s + speed;
  };

  const int rc = sim::run_window(hooks, cli.capture, cli.exit_after_ms);
  sh.quit = true;
  emu.join();
  pad.stop();
  audio.stop();
  timeEndPeriod(1);
  return rc;
}
```

- [ ] **Step 6: Despachar al modo ventana desde `sim/app/main.cpp`**

Agregar `#include "app/windowed.h"` y reemplazar estas dos líneas:

```cpp
  std::fprintf(stderr, "el modo con ventana llega en la Task 10; usá --headless\n");
  return 2;
```

por:

```cpp
  return run_windowed(cli);
```

- [ ] **Step 7: Registrar en CMake**

En `sim/CMakeLists.txt`, reemplazar el `add_executable(pikocore_sim ...)` y el `target_link_libraries(pikocore_sim ...)` de la Task 9 por:

```cmake
add_executable(pikocore_sim
  app/main.cpp
  app/cli.cpp
  app/windowed.cpp
  platform/audio_out.cpp
  platform/pad_input.cpp
  platform/sim_window.cpp
)
target_link_libraries(pikocore_sim PRIVATE sim_runtime xinput ole32 user32 gdi32 shell32 winmm)
```

Las líneas `target_include_directories`, `target_compile_definitions` y `target_compile_options` de `pikocore_sim` quedan como estaban.

- [ ] **Step 8: Compilar y capturar la ventana sin intervención**

```bash
cmake -S sim -B build-sim > /dev/null; cmake --build build-sim --config Release 2>&1 | grep -E ' error |LNK'
OUT=$(mktemp -d)
build-sim/bin/pikocore_sim.exe --flash $OUT/flash.bin --capture $OUT/window.bmp --exit-after-ms 7000; echo "exit=$?"; ls -la $OUT
```

Expected: la ventana aparece ~7 s y se cierra sola; `exit=0`; existe `window.bmp` (≈1.47 MB) y también `flash.bin` (16 MB). Abrir `window.bmp` con la herramienta Read y confirmar:
- la carcasa gris, con D-pad a la izquierda, X/Y/A/B a la derecha y L/R/SELECT/START;
- el LCD en el centro con el dashboard derecho (el splash ya terminó a los ~4 s);
- la barra de estado con el control, `Banco: ninguno, arrastrá...`, el audio y `x1.0` aproximadamente.

- [ ] **Step 9: Verificar con un banco y con la flash persistente**

```bash
build-sim/bin/pikocore_sim_itest.exe dump_bank $OUT/test.pikobank
build-sim/bin/pikocore_sim.exe $OUT/test.pikobank --flash $OUT/flash.bin --capture $OUT/w1.bmp --exit-after-ms 7000
build-sim/bin/pikocore_sim.exe --flash $OUT/flash.bin --capture $OUT/w2.bmp --exit-after-ms 7000
```

Expected: `w1.bmp` muestra `Banco: 4 samples (test.pikobank)`. `w2.bmp`, sin pasar el banco, muestra `Banco: 4 samples (en la flash)`, porque la flash persistió. En ambos, el nombre del sample del dashboard es `synth_1`.

- [ ] **Step 10: Verificación manual con el control (el usuario)**

Pedirle al usuario que corra `build-sim/bin/pikocore_sim.exe <banco>.pikobank` con un control Xbox conectado y que confirme:
1. suena el loop y el LED de beat parpadea;
2. D-pad / X / Y / A / B saltan a slices (el playhead de la waveform salta);
3. dos botones musicales a la vez producen stutter, y los 2 slices se ven en blanco;
4. Start (toque) → silencio; otro toque → vuelve;
5. Select (toque) avanza de modo; Select + Right → modo 3;
6. LB/RB mueven la barra de Function A; Start + LB/RB, la de Function B;
7. `Down + Right + B + A` resetea los FX;
8. arrastrar otro `.pikobank` a la ventana lo carga sin cortar el programa.

No marcar esta tarea como completa sin esa confirmación. Anotar cualquier falla para corregirla antes del commit.

- [ ] **Step 11: Correr la suite completa y commitear**

```bash
ctest --test-dir build-sim -C Release --output-on-failure
git add sim/CMakeLists.txt sim/platform sim/app/windowed.h sim/app/windowed.cpp sim/app/main.cpp
git commit -m "sim: modo ventana con XInput, WASAPI y LCD emulado

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected de ctest: `100% tests passed, 0 tests failed out of 5`.

---

### Task 11: Documentación

**Files:**
- Create: `sim/README.md`
- Modify: `docs/superpowers/specs/2026-09-22-xinput-simulator-design.md`

**Interfaces:**
- Consumes: todo lo anterior. Es solo documentación.

- [ ] **Step 1: Escribir `sim/README.md`**

````markdown
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
firmware tarda ~4.5 s virtuales en arrancar (splash + espera de USB). Ver
`pikocore_sim.exe --help` para el resto de las opciones.

## Cómo funciona

- `sim/shim/sim_pico.h` reemplaza al pico-sdk. GPIO, PWM, SPI, flash y timer
  delegan en `sim/runtime/sim_hal.cpp`.
- `sim/runtime/machine.cpp` es un planificador determinista sobre un reloj
  virtual de 248 MHz: la ISR de audio corre cada 251 ciclos y el `main()` del
  firmware en una Fiber que cede el control en `__wfi()`, `sleep_*()` y cada
  lectura del timer. Los temporizadores del firmware (los que cuentan vueltas
  del lazo y los de `time_us_64()`) corren a la cadencia del hardware.
- El audio es el nivel PWM promediado por muestra (el filtro RC) más un
  filtro de DC, a 48 kHz por WASAPI.
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
````

- [ ] **Step 2: Actualizar el spec con lo que cambió durante la implementación**

En `docs/superpowers/specs/2026-09-22-xinput-simulator-design.md`:

1. Cambiar `Estado: propuesto, pendiente de aprobación` por `Estado: implementado (plan: docs/superpowers/plans/2026-09-22-xinput-simulator.md)`.
2. En §1, debajo de "Cambio en el firmware", agregar:

```markdown
### Compatibilidad con MSVC sin tocar el firmware

`doth/easing.h` tiene cadenas `else if` de cientos de eslabones y MSVC corta en
128 niveles de anidamiento (C1061). Como cada rama hace `return`, el build del
simulador genera una copia aplanada (`} else if (` → `}\n  if (`) en
`build-sim/gen/doth/easing.h`, que tiene prioridad en el include path
(`sim/cmake/flatten_easing.cmake`). El archivo original no cambia.
```

3. En §2, "Carga de `.pikobank`", agregar al final:

```markdown
El loader web escribe `capacity_bytes = 16 MB` al exportar (`web/src/App.tsx`,
`SD_BANK_CAPACITY_BYTES`), más que la capacidad real de audio (16 MB − 512 KB −
12 KB), y `piko_audio_bank_rescan()` rechaza ese banco. El simulador corrige el
campo al cargar. El mismo `validate_header()` del modo SD (aparcado) rechazaría
esos archivos en el hardware.
```

4. En §3, debajo de la lista de consecuencias, agregar:

```markdown
- Cada lectura del timer desde `main()` cuesta 32 ciclos virtuales y cede el
  control, así un lazo que solo espera a `time_us_64()` no se cuelga con el
  tiempo congelado.
```

- [ ] **Step 3: Commit**

```bash
git add sim/README.md docs/superpowers/specs/2026-09-22-xinput-simulator-design.md
git commit -m "docs: README del simulador y spec actualizado con lo implementado

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
