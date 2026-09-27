# Fase 3: navegación y carga desde microSD — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modo 9 del selector ("Browse SD") que lista archivos `.pikobank` del microSD integrado del RP2350-PiZero, navega con L/R y carga con "mantener R ~1s", reusando el pipeline de validación/escritura a flash ya blindado, sin afectar audio ni el build original.

**Architecture:** Toda la lectura de SD y escritura a flash vive en **core1** (`PikoSampleManager.cpp`), porque ahí es donde `multicore_lockout_victim_init()` ya registró a core0 como "víctima" — solo core1 puede pedir esa pausa. Core0 (botones + LCD) pide trabajo a core1 con el mismo patrón de banderas `volatile` + `dmb` que ya usa el código para el toggle de modo de reloj MIDI, sin bloquear nunca (polling, un chequeo por tick). La SD comparte el periférico `spi1` con el LCD (mismo hardware, pines distintos — verificado contra los registros del RP2350B); se protege con un `mutex_t` propio, tomado brevemente por cada flush del LCD y por cada operación de SD en core1. Mientras core1 hace una carga (lectura de SD + escritura a flash), core0 deliberadamente no toca el LCD — evita competir por `spi1` sin necesidad de locking fino.

**Tech Stack:** pico-sdk 2.1.1, C/C++17, librería `no-OS-FatFS-SD-SDIO-SPI-RPi-Pico` vendorizada (`RP2350-PiZero/C/03-MicroSD/src/`), FatFs, `pico_sync` (mutex).

**Spec:** `docs/superpowers/specs/2026-07-16-gamepi13-microsd-design.md` (aprobado). Rama: `port/rp2350-gamepi13`. **Punto de restauración: tag `fase2-completa-verificada`** — si algo de esta fase falla de forma difícil de diagnosticar en hardware, `git reset --hard fase2-completa-verificada` vuelve al estado anterior, verificado y funcionando.

---

## Contexto para quien ejecuta (léelo completo antes de empezar)

### Entorno de build (Windows) — igual que en Fases 1 y 2

```bash
cat > /c/pikocore-main/rebuild_TAG.bat << 'EOF'
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 (
  echo VCVARSALL_FAILED
  exit /b 1
)
cd /d C:\pikocore-main\BUILDDIR
C:\dtmake\make.exe -j4
if errorlevel 1 (
  echo MAKE_FAILED
  exit /b 1
)
echo MAKE_OK
EOF
cmd.exe //c "C:\pikocore-main\rebuild_TAG.bat"
```

`BUILDDIR` = `build` (original) o `build-gamepi` (GamePi13). `TAG` = nombre distinto por invocación. `C:\dtmake\make.exe` ya existe. Si se modifica `CMakeLists.txt`, agregar antes del make (dentro del mismo `.bat`, tras el `cd /d`):
`"C:\Program Files\CMake\bin\cmake.exe" -G "MinGW Makefiles" -DCMAKE_MAKE_PROGRAM="C:/dtmake/make.exe" -DPICO_SDK_PATH=../pico-sdk [-DPIKO_GAMEPI13=ON] ..`
Borrar los `.bat` temporales al terminar.

### Hallazgos de hardware que hay que respetar (verificados leyendo código y registros — no redescubrir)

1. **El socket de SD y el LCD comparten `spi1`.** GP30 (SCK), GP31 (MOSI), GP40 (MISO) del socket de SD solo tienen función `spi1_*` en la tabla `IO_BANK0_GPIOxx_CTRL_FUNCSEL` del RP2350 — no existe alternativa `spi0`. El LCD ya usa `spi1` en GP10/GP11. Se comparten diferenciados por Chip Select (GP8 el LCD, GP43 la SD) — patrón válido, pero requiere el mutex del Task 2.
2. **`piko_sample_manager_core()` (core1) sale del loop apenas antes de revisar comandos si no hay USB conectado** (`if (!serial_connected()) { sleep_ms(1); continue; }`, `src/PikoSampleManager.cpp` ~línea 395). El chequeo de las banderas de SD **debe ir ANTES de ese corte** — si no, la función de SD nunca funcionaría sin una PC conectada, que es exactamente el caso de uso que se busca. Task 3 lo hace explícito.
3. **La librería FatFs vendorizada ya expone `f_mount`/`f_unmount`/`f_opendir`/`f_readdir`/`f_open`/`f_read`/`f_close`** (ChaN FatFs estándar, `RP2350-PiZero/C/03-MicroSD/src/ff15/source/ff.h`). El prefijo de unidad para montar se obtiene con `sd_get_drive_prefix(sd_get_by_num(0))` (`RP2350-PiZero/C/03-MicroSD/example/src/command.cpp:65,296`), no un string hardcodeado.
4. **`validate_header()`, `safe_flash_erase()`, `safe_flash_program()`, `header_staging[]`, `page_buf[]`** ya existen en `src/PikoSampleManager.cpp` (agregados/blindados en la Fase 2) dentro de un `namespace { ... }` anónimo — internal linkage. El código nuevo de SD debe vivir en el **mismo archivo** para reusarlos directamente; no se exportan.
5. **`FILINFO.fname`** es el campo estándar de FatFs con el nombre del archivo tras `f_readdir`.

### Reglas de la fase

- Todo lo nuevo compila SOLO bajo `PIKO_GAMEPI13`. El build original (flag OFF) no cambia de comportamiento ni de tamaño.
- Nada de esto bloquea el audio: las operaciones de SD/flash corren en core1 sin pausar el ISR de audio (que vive en core0); core0 nunca hace `sleep`/espera bloqueante esperando a core1, solo polling de una bandera por tick.
- Cada task termina con AMBOS builds compilando (`MAKE_OK` ×2) y un commit.

---

### Task 1: Vendorizar la librería FatFS/SD en CMake + `hw_config.c`

**Files:**
- Create: `src/gamepi13/sd_hw_config.c`
- Modify: `CMakeLists.txt` (dentro del bloque `if(PIKO_GAMEPI13)`)

- [ ] **Step 1: Crear `src/gamepi13/sd_hw_config.c`**

Adaptado de `RP2350-PiZero/C/03-MicroSD/example/config/hw_config.c`, con **un solo** `sd_card_t` (el original tiene 4, para hardware que no tenemos) y sin la rama `#ifdef SPI_SD0`/SDIO (no se usa SDIO en esta fase):

```c
// sd_hw_config.c
// Hardware config for the RP2350-PiZero's onboard microSD socket.
// Adapted from RP2350-PiZero/C/03-MicroSD/example/config/hw_config.c,
// trimmed to the single SPI-attached card this board actually has.
// Pins verified against RP2350 IO_BANK0 FUNCSEL registers: GP30/31/40 only
// route to spi1 (no spi0 alternative), same peripheral the LCD uses on
// GP10/GP11 -- shared bus, see the spi1 mutex in dev_shim.c (Task 2).
#include <assert.h>

#include "hw_config.h"

static spi_t spi = {
    .hw_inst = spi1,
    .sck_gpio = 30,
    .mosi_gpio = 31,
    .miso_gpio = 40,
    .set_drive_strength = true,
    .mosi_gpio_drive_strength = GPIO_DRIVE_STRENGTH_2MA,
    .sck_gpio_drive_strength = GPIO_DRIVE_STRENGTH_12MA,
    .no_miso_gpio_pull_up = true,
    .baud_rate = 12 * 1000 * 1000,  // 12 MHz, conservative to start
};

static sd_spi_if_t spi_if = {
    .spi = &spi,
    .ss_gpio = 43,
    .set_drive_strength = true,
    .ss_gpio_drive_strength = GPIO_DRIVE_STRENGTH_2MA,
};

static sd_card_t sd_card = {
    .type = SD_IF_SPI,
    .spi_if_p = &spi_if,
    .use_card_detect = false,
};

size_t sd_get_num() { return 1; }

sd_card_t *sd_get_by_num(size_t num) {
  assert(num == 0);
  return num == 0 ? &sd_card : NULL;
}
```

- [ ] **Step 2: Ampliar el bloque `if(PIKO_GAMEPI13)` en `CMakeLists.txt`**

Buscar (el bloque actual, al final tiene `target_link_libraries(${PROJECT_NAME} hardware_spi)`):

```cmake
	target_link_libraries(${PROJECT_NAME} hardware_spi)
endif()
```

Reemplazar por:

```cmake
	target_link_libraries(${PROJECT_NAME} hardware_spi)

	add_subdirectory(${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/03-MicroSD/src
		${CMAKE_CURRENT_BINARY_DIR}/no-OS-FatFS)
	target_sources(${PROJECT_NAME} PRIVATE
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/sd_hw_config.c
	)
	target_include_directories(${PROJECT_NAME} PRIVATE
		${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/03-MicroSD/include
		${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/03-MicroSD/src/include
		${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/03-MicroSD/src/sd_driver
		${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/03-MicroSD/src/ff15/source
	)
	target_link_libraries(${PROJECT_NAME} no-OS-FatFS-SD-SDIO-SPI-RPi-Pico pico_sync)
endif()
```

- [ ] **Step 3: Build de ambas variantes**

Receta del contexto. `build-gamepi` ahora compila ~30 archivos nuevos de la librería — esperar unos minutos más que builds anteriores. Si hay un error de `PICO_MAX_SHARED_IRQ_HANDLERS` u otra macro ya definida por otro lado, es porque `hardware_pio`/`hardware_dma` ya estaban linkeados (Fase 2, LCD) — no debería chocar, pero si lo hace, reportar el error exacto en vez de intentar arreglarlo a ciegas.

Expected: `MAKE_OK` ×2. `build/` (original) no debe cambiar de tamaño — nada de esto se agrega fuera de `if(PIKO_GAMEPI13)`.

- [ ] **Step 4: Commit**

```bash
git add CMakeLists.txt src/gamepi13/sd_hw_config.c
git commit -m "feat: vendorizar libreria FatFS/SD y hw_config de un solo socket SPI"
```

---

### Task 2: Mutex compartido de `spi1` entre LCD y SD

**Files:**
- Modify: `src/gamepi13/lcd/DEV_Config.h` (declarar el mutex + función de init)
- Modify: `src/gamepi13/dev_shim.c` (definir e inicializar el mutex; tomarlo en el init del LCD)
- Modify: `src/gamepi13/ui.cpp` (tomar el mutex en cada `flush()`)
- Modify: `src/main.cpp` (llamar la init del mutex junto a `multicore_lockout_victim_init()`)

- [ ] **Step 1: Declarar en `src/gamepi13/lcd/DEV_Config.h`**

Contenido actual completo del archivo (37 líneas) confirmado — dos ediciones:

Buscar (línea 8):

```c
#include "hardware/spi.h"
#include "pico/stdlib.h"
```

Reemplazar por:

```c
#include "hardware/spi.h"
#include "pico/stdlib.h"
#include "pico/sync.h"
```

Buscar (líneas 30-32, el bloque final antes del cierre de `extern "C"`):

```c
// pikocore-specific (called from ui.cpp, not from vendored code):
void gamepi_lcd_dev_init(void);
void gamepi_lcd_backlight(uint8_t percent);  // 0-100
```

Reemplazar por:

```c
// pikocore-specific (called from ui.cpp, not from vendored code):
void gamepi_lcd_dev_init(void);
void gamepi_lcd_backlight(uint8_t percent);  // 0-100

// Shared spi1 mutex: the onboard microSD socket (GP30/31/40) and this LCD
// (GP10/11) are both wired to the spi1 peripheral -- verified against the
// RP2350's IO_BANK0 FUNCSEL registers, no spi0 alternative exists for the SD
// pins. Both clients must hold this around any spi1 transaction. Defined in
// dev_shim.c, initialized once in main() before either client runs.
extern mutex_t gamepi_spi1_mutex;
void gamepi_spi1_mutex_init(void);
```

- [ ] **Step 2: Definir e inicializar en `src/gamepi13/dev_shim.c`**

Buscar (línea 13 actual):

```c
int EPD_BL_PIN = GAMEPI_LCD_BL_PIN;
```

Reemplazar por:

```c
int EPD_BL_PIN = GAMEPI_LCD_BL_PIN;

mutex_t gamepi_spi1_mutex;

void gamepi_spi1_mutex_init(void) { mutex_init(&gamepi_spi1_mutex); }
```

En `gamepi_lcd_dev_init()`, envolver el `spi_init(...)` y los dos `gpio_set_function(...)` de SPI con el mutex (para que la inicialización del hardware SPI no se cruce con una operación de SD ya en curso — en la práctica no debería pasar en boot, pero es la disciplina correcta):

Buscar:

```c
  spi_init(GAMEPI_SPI, 10000 * 1000);
  gpio_set_function(GAMEPI_LCD_CLK_PIN, GPIO_FUNC_SPI);
  gpio_set_function(GAMEPI_LCD_MOSI_PIN, GPIO_FUNC_SPI);
```

Reemplazar por:

```c
  mutex_enter_blocking(&gamepi_spi1_mutex);
  spi_init(GAMEPI_SPI, 10000 * 1000);
  gpio_set_function(GAMEPI_LCD_CLK_PIN, GPIO_FUNC_SPI);
  gpio_set_function(GAMEPI_LCD_MOSI_PIN, GPIO_FUNC_SPI);
  mutex_exit(&gamepi_spi1_mutex);
```

- [ ] **Step 3: Tomar el mutex en cada flush del LCD, `src/gamepi13/ui.cpp`**

Buscar el cuerpo de `flush()` (los 4 casos `#if GAMEPI_LCD_ROTATE == ...`), que hoy termina con llamadas directas a `LCD_1IN3_DisplayWindows(...)`. Envolver la función completa: al principio agregar `mutex_enter_blocking(&gamepi_spi1_mutex);` y justo antes de cada `return` implícito (al final de la función, después del último `#endif`) agregar `mutex_exit(&gamepi_spi1_mutex);`. Concretamente, cambiar la firma y el cierre:

```cpp
static void flush(const Rect &r) {
  mutex_enter_blocking(&gamepi_spi1_mutex);
#if GAMEPI_LCD_ROTATE == ROTATE_270
  const uint16_t mx0 = r.y;
  const uint16_t mx1 = (uint16_t)(r.y + r.h);
  const uint16_t my0 = (uint16_t)(LCD_1IN3_WIDTH - (r.x + r.w));
  const uint16_t my1 = (uint16_t)(LCD_1IN3_WIDTH - r.x);
  LCD_1IN3_DisplayWindows(mx0, my0, mx1, my1, (UWORD *)fb);
#elif GAMEPI_LCD_ROTATE == ROTATE_90
  const uint16_t mx0 = (uint16_t)(LCD_1IN3_HEIGHT - (r.y + r.h));
  const uint16_t mx1 = (uint16_t)(LCD_1IN3_HEIGHT - r.y);
  const uint16_t my0 = r.x;
  const uint16_t my1 = (uint16_t)(r.x + r.w);
  LCD_1IN3_DisplayWindows(mx0, my0, mx1, my1, (UWORD *)fb);
#elif GAMEPI_LCD_ROTATE == ROTATE_180
  const uint16_t mx0 = (uint16_t)(LCD_1IN3_WIDTH - (r.x + r.w));
  const uint16_t mx1 = (uint16_t)(LCD_1IN3_WIDTH - r.x);
  const uint16_t my0 = (uint16_t)(LCD_1IN3_HEIGHT - (r.y + r.h));
  const uint16_t my1 = (uint16_t)(LCD_1IN3_HEIGHT - r.y);
  LCD_1IN3_DisplayWindows(mx0, my0, mx1, my1, (UWORD *)fb);
#else
  LCD_1IN3_DisplayWindows(r.x, r.y, (uint16_t)(r.x + r.w),
                          (uint16_t)(r.y + r.h), (UWORD *)fb);
#endif
  mutex_exit(&gamepi_spi1_mutex);
}
```

(Solo se agregan las dos líneas de mutex al principio y al final; el cuerpo `#if/#elif/#else` queda exactamente igual al actual.)

- [ ] **Step 4: Inicializar el mutex en `src/main.cpp`**

Buscar (agregado en la Fase 2, Task de flash safety):

```cpp
  multicore_lockout_victim_init();
  multicore_launch_core1(piko_sample_manager_core);
```

Reemplazar por:

```cpp
#if PIKO_GAMEPI13
  gamepi_spi1_mutex_init();
#endif
  multicore_lockout_victim_init();
  multicore_launch_core1(piko_sample_manager_core);
```

- [ ] **Step 5: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/` no cambia (todo bajo `#if PIKO_GAMEPI13`).

- [ ] **Step 6: Commit**

```bash
git add src/gamepi13/lcd/DEV_Config.h src/gamepi13/dev_shim.c src/gamepi13/ui.cpp src/main.cpp
git commit -m "feat: mutex compartido de spi1 entre LCD y SD (mismo periferico, pines distintos)"
```

---

### Task 3: Subsistema de SD en core1 (montaje, listado, carga)

**Files:**
- Modify: `src/PikoSampleManager.h` (declarar la API que usa core0)
- Modify: `src/PikoSampleManager.cpp` (montaje/listado/carga + banderas de RPC + reestructurar el loop)

- [ ] **Step 1: Declarar la API en `src/PikoSampleManager.h`**

Reemplazar el contenido completo del archivo:

```cpp
#pragma once

#include <stdint.h>

void piko_sample_manager_set_ready();
void piko_sample_manager_core();

#if PIKO_GAMEPI13
// Async request/response API for core0 -> core1 SD operations. Same
// volatile-flag + dmb pattern already used by piko_set_clock_input_ittybittymidi
// (main.cpp), mirrored in the other direction. Core0 must never busy-wait on
// the *_done flags -- poll them once per UI tick instead, so audio (core0's
// ISR) and the rest of the button/LCD loop are never blocked.
extern volatile bool gamepi_sd_list_requested;
extern volatile bool gamepi_sd_list_done;
extern volatile bool gamepi_sd_load_requested;
extern volatile uint32_t gamepi_sd_load_index;
extern volatile bool gamepi_sd_load_done;
extern volatile bool gamepi_sd_load_ok;
extern volatile bool gamepi_sd_unmount_requested;

uint32_t gamepi_sd_file_count();
const char *gamepi_sd_file_name(uint32_t index);
#endif
```

- [ ] **Step 2: Agregar el include de la librería y el estado de SD en `src/PikoSampleManager.cpp`**

Buscar el bloque de includes al principio del archivo:

```cpp
#include "PikoAudioBank.h"
#include "hardware/flash.h"
#include "pico/bootrom.h"
#include "pico/multicore.h"
#include "pico/stdlib.h"
#include "tusb.h"
```

Reemplazar por:

```cpp
#include "PikoAudioBank.h"
#include "hardware/flash.h"
#include "pico/bootrom.h"
#include "pico/multicore.h"
#include "pico/stdlib.h"
#include "tusb.h"

#if PIKO_GAMEPI13
#include "ff.h"
#include "hw_config.h"
#include "sd_card.h"
#endif
```

- [ ] **Step 3: Agregar el subsistema de SD dentro del `namespace { ... }` anónimo**

Buscar el final de `handle_clock_input_mode()` (justo antes de `}  // namespace`):

```cpp
  write_str("OK\n");
  flush_serial();
}

}  // namespace
```

Insertar el bloque de SD entre el cierre de `handle_clock_input_mode()` y `}  // namespace`:

```cpp
  write_str("OK\n");
  flush_serial();
}

#if PIKO_GAMEPI13
constexpr uint32_t kMaxSdFiles = 32;
constexpr uint32_t kSdFilenameLen = 64;

char sd_file_names[kMaxSdFiles][kSdFilenameLen];
uint32_t sd_file_count_internal = 0;
FATFS sd_fatfs;
bool sd_mounted = false;

bool sd_mount() {
  if (sd_mounted) return true;
  const FRESULT fr = f_mount(&sd_fatfs, sd_get_drive_prefix(sd_get_by_num(0)), 1);
  sd_mounted = (fr == FR_OK);
  return sd_mounted;
}

void sd_unmount() {
  if (!sd_mounted) return;
  f_unmount(sd_get_drive_prefix(sd_get_by_num(0)));
  sd_mounted = false;
}

// Case-insensitive ".pikobank" suffix check without pulling in strings.h.
bool has_pikobank_extension(const char *name) {
  static const char kExt[] = ".pikobank";
  const uint32_t ext_len = sizeof(kExt) - 1;
  const uint32_t len = strlen(name);
  if (len <= ext_len) return false;
  const char *suffix = name + (len - ext_len);
  for (uint32_t i = 0; i < ext_len; ++i) {
    char a = suffix[i];
    const char b = kExt[i];
    if (a >= 'A' && a <= 'Z') a = static_cast<char>(a + 32);
    if (a != b) return false;
  }
  return true;
}

void sd_list_files() {
  sd_file_count_internal = 0;
  if (!sd_mount()) return;
  DIR dir;
  if (f_opendir(&dir, sd_get_drive_prefix(sd_get_by_num(0))) != FR_OK) return;
  FILINFO fno;
  while (sd_file_count_internal < kMaxSdFiles &&
         f_readdir(&dir, &fno) == FR_OK && fno.fname[0] != 0) {
    if (fno.fattrib & AM_DIR) continue;
    if (!has_pikobank_extension(fno.fname)) continue;
    strncpy(sd_file_names[sd_file_count_internal], fno.fname, kSdFilenameLen - 1);
    sd_file_names[sd_file_count_internal][kSdFilenameLen - 1] = '\0';
    sd_file_count_internal++;
  }
  f_closedir(&dir);
}

// Mirrors handle_write()'s validate+erase+program sequence, sourcing bytes
// from an SD file instead of the USB serial link. Reuses the same
// header_staging/page_buf staging buffers and the same safe_flash_* helpers
// (multicore-lockout protected, see Fase 2) -- no new flash-writing logic.
bool sd_load_bank(uint32_t index) {
  if (index >= sd_file_count_internal) return false;
  if (!sd_mount()) return false;

  FIL fil;
  if (f_open(&fil, sd_file_names[index], FA_READ) != FR_OK) return false;

  const uint32_t total_len = static_cast<uint32_t>(f_size(&fil));
  if (total_len < PIKO_BANK_HEADER_SIZE ||
      total_len > PIKO_BANK_HEADER_SIZE + piko_audio_capacity_bytes()) {
    f_close(&fil);
    return false;
  }

  UINT br = 0;
  if (f_read(&fil, header_staging, PIKO_BANK_HEADER_SIZE, &br) != FR_OK ||
      br != PIKO_BANK_HEADER_SIZE) {
    f_close(&fil);
    return false;
  }

  const PikoBankHeader *header =
      reinterpret_cast<const PikoBankHeader *>(header_staging);
  if (!validate_header(*header, total_len)) {
    f_close(&fil);
    return false;
  }

  piko_audio_bank_set_mutating(true);

  safe_flash_erase(PIKO_AUDIO_FLASH_OFFSET, PIKO_BANK_HEADER_SIZE);

  uint32_t bytes_written = PIKO_BANK_HEADER_SIZE;
  uint32_t audio_flash_off = PIKO_AUDIO_FLASH_OFFSET + PIKO_BANK_HEADER_SIZE;
  uint32_t next_erase = audio_flash_off;
  bool ok = true;

  while (bytes_written < total_len) {
    const uint32_t remaining = total_len - bytes_written;
    const uint32_t page_fill =
        remaining < kFlashPageSize ? remaining : kFlashPageSize;
    memset(page_buf, 0xff, sizeof(page_buf));
    if (f_read(&fil, page_buf, page_fill, &br) != FR_OK || br != page_fill) {
      ok = false;
      break;
    }
    const uint32_t page_off =
        audio_flash_off + (bytes_written - PIKO_BANK_HEADER_SIZE);
    if (page_off >= next_erase) {
      safe_flash_erase(next_erase, kFlashSectorSize);
      next_erase += kFlashSectorSize;
    }
    safe_flash_program(page_off, page_buf, sizeof(page_buf));
    bytes_written += page_fill;
  }

  if (ok) {
    memset(page_buf, 0xff, sizeof(page_buf));
    for (uint32_t offset = 0; offset < PIKO_BANK_HEADER_SIZE;
         offset += kFlashPageSize) {
      memcpy(page_buf, header_staging + offset, kFlashPageSize);
      safe_flash_program(PIKO_AUDIO_FLASH_OFFSET + offset, page_buf,
                         sizeof(page_buf));
    }
    piko_audio_bank_rescan();
  }

  piko_audio_bank_set_mutating(false);
  f_close(&fil);
  return ok;
}
#endif  // PIKO_GAMEPI13

}  // namespace
```

- [ ] **Step 4: Definir las banderas de RPC (fuera del namespace anónimo, para linkage externo)**

**Ojo**: `command_interface_ready` (línea 43 actual) está DENTRO del `namespace { ... }` anónimo (que abre en la línea 29) — tiene linkage interno, invisible desde `main.cpp`. Eso está bien para esa variable (solo la toca este archivo), pero las banderas nuevas SÍ necesitan que `main.cpp` las lea/escriba directamente, así que tienen que quedar realmente afuera del namespace. El ancla correcta es el cierre del namespace, no esa variable.

Buscar (cierre del namespace anónimo, línea 385 actual, ya existe sin cambios):

```cpp
}  // namespace

void piko_sample_manager_set_ready() {
```

Insertar el bloque de banderas **entre** el cierre del namespace y `piko_sample_manager_set_ready()`:

```cpp
}  // namespace

#if PIKO_GAMEPI13
volatile bool gamepi_sd_list_requested = false;
volatile bool gamepi_sd_list_done = false;
volatile bool gamepi_sd_load_requested = false;
volatile uint32_t gamepi_sd_load_index = 0;
volatile bool gamepi_sd_load_done = false;
volatile bool gamepi_sd_load_ok = false;
volatile bool gamepi_sd_unmount_requested = false;

uint32_t gamepi_sd_file_count() { return sd_file_count_internal; }

const char *gamepi_sd_file_name(uint32_t index) {
  static const char kEmpty[] = "";
  if (index >= sd_file_count_internal) return kEmpty;
  return sd_file_names[index];
}
#endif

void piko_sample_manager_set_ready() {
```

(`gamepi_sd_file_count()`/`gamepi_sd_file_name()` acceden a `sd_file_count_internal`/`sd_file_names`, definidas en el Step 3 dentro del namespace anónimo — como estas dos funciones están en el mismo archivo, aunque textualmente fuera del bloque `namespace { }`, la búsqueda de nombres sin calificar igual las encuentra por estar en el mismo *scope* de traducción; no hace falta declararlas ni calificarlas. `gamepi_sd_list_requested` y el resto de las banderas, en cambio, sí quedan con linkage externo real — accesibles desde `main.cpp` vía los `extern` del Step 1.)

- [ ] **Step 5: Reestructurar `piko_sample_manager_core()` — chequeo de SD ANTES del corte por USB**

Buscar (el inicio del loop):

```cpp
void piko_sample_manager_core() {
  while (true) {
    service_usb();
    if (!serial_connected()) {
      sleep_ms(1);
      continue;
    }
```

Reemplazar por:

```cpp
void piko_sample_manager_core() {
  while (true) {
    service_usb();

#if PIKO_GAMEPI13
    // Checked BEFORE the serial_connected() early-continue below: SD
    // browsing must work with no USB/PC attached at all, which is the whole
    // point of this feature. If this moved below the USB check, standalone
    // use would silently never service these requests.
    if (gamepi_sd_list_requested) {
      gamepi_sd_list_requested = false;
      sd_list_files();
      __asm volatile("dmb" ::: "memory");
      gamepi_sd_list_done = true;
    }
    if (gamepi_sd_load_requested) {
      gamepi_sd_load_requested = false;
      const bool ok = sd_load_bank(gamepi_sd_load_index);
      gamepi_sd_load_ok = ok;
      __asm volatile("dmb" ::: "memory");
      gamepi_sd_load_done = true;
    }
    if (gamepi_sd_unmount_requested) {
      gamepi_sd_unmount_requested = false;
      sd_unmount();
    }
#endif

    if (!serial_connected()) {
      sleep_ms(1);
      continue;
    }
```

- [ ] **Step 6: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/` no cambia — todo lo agregado está bajo `#if PIKO_GAMEPI13`, salvo la reestructura del loop en el Step 5, que para el build original es un `#if 0`-equivalente (el bloque completo queda fuera). Confirmar con el tamaño de `build/pikocore.uf2` sin cambios.

- [ ] **Step 7: Commit**

```bash
git add src/PikoSampleManager.h src/PikoSampleManager.cpp
git commit -m "feat: montaje/listado/carga de bancos desde SD en core1 + RPC async con core0"
```

---

### Task 3.5: Enganchar `gamepi_spi1_mutex` en el driver SD (cierra la ventana de contención real)

**Agregada post-hoc**, tras detectar que las Tareas 2 y 3 (ya commiteadas) dejaron el mutex de `spi1` protegiendo solo el lado del LCD. El spec original (`docs/superpowers/specs/2026-07-16-gamepi13-microsd-design.md`, sección "Mutex de `spi1`") pedía enganchar también el lado de la SD "implementando los hooks de bajo nivel que la librería expone (`sd_spi_acquire`/`sd_spi_release`, o el punto equivalente en `sd_driver/SPI/my_spi.c`)" — ese enganche nunca se transcribió a una tarea concreta durante el self-review del plan original. Sin esto, `sd_mount()`/`sd_list_files()`/`sd_load_bank()` en core1 pueden ejecutar transacciones SPI reales sobre `spi1` al mismo tiempo que `flush()` del LCD en core0, con el mutex existente sin efecto real (cada lado usa un mutex distinto: la SD usa el suyo propio, interno a la librería, que no sabe nada de `gamepi_spi1_mutex`).

**Files:**
- Modify: `RP2350-PiZero/C/03-MicroSD/src/sd_driver/SPI/my_spi.h` (único cuello de botella: toda transacción SD pasa por `spi_lock`/`spi_unlock`, llamadas desde `sd_spi_acquire`/`sd_spi_release`)

- [ ] **Step 1: Enganchar el mutex compartido en `spi_lock`/`spi_unlock`**

Buscar:
```c
static inline void spi_lock(spi_t *spi_p) {
    myASSERT(mutex_is_initialized(&spi_p->mutex));
    mutex_enter_blocking(&spi_p->mutex);
}
static inline void spi_unlock(spi_t *spi_p) {
    myASSERT(mutex_is_initialized(&spi_p->mutex));
    mutex_exit(&spi_p->mutex);
}
```

Reemplazar por:
```c
// pikocore/GamePi13: this SPI peripheral (spi1) is physically shared with
// the GamePi13's LCD, driven by a separate driver on core0
// (src/gamepi13/dev_shim.c / ui.cpp). Real hardware bus contention, not
// just software tidiness -- verified against the RP2350's IO_BANK0 FUNCSEL
// registers (SD pins GP30/31/40 only route to spi1, same peripheral as the
// LCD's GP10/11). Defined and initialized once in dev_shim.c; every spi1
// client, on either core, must hold it around any transaction.
extern mutex_t gamepi_spi1_mutex;

static inline void spi_lock(spi_t *spi_p) {
    myASSERT(mutex_is_initialized(&spi_p->mutex));
    mutex_enter_blocking(&spi_p->mutex);
    mutex_enter_blocking(&gamepi_spi1_mutex);
}
static inline void spi_unlock(spi_t *spi_p) {
    mutex_exit(&gamepi_spi1_mutex);
    myASSERT(mutex_is_initialized(&spi_p->mutex));
    mutex_exit(&spi_p->mutex);
}
```

No hay riesgo de deadlock: el lado LCD (`dev_shim.c`/`ui.cpp`) nunca toca `spi_p->mutex` (es privado de la librería SD), así que solo este archivo llega a tomar ambos mutexes a la vez, siempre en el mismo orden (`spi_p->mutex` primero, `gamepi_spi1_mutex` después) y los libera en orden inverso.

- [ ] **Step 2: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/` no cambia — este archivo vendorizado solo se compila cuando `PIKO_GAMEPI13` está ON (Task 1 lo agrega al build vía `add_subdirectory` dentro del `if(PIKO_GAMEPI13)`), así que no hace falta ningún `#if` adicional en este archivo.

- [ ] **Step 3: Commit**

```bash
git add RP2350-PiZero/C/03-MicroSD/src/sd_driver/SPI/my_spi.h
git commit -m "fix: enganchar mutex compartido de spi1 en el driver SD (cierra ventana de contencion con el LCD)"
```

---

### Task 4: Renderizado del modo Browse SD en el LCD

**Files:**
- Modify: `src/gamepi13/ui.h` (declarar las funciones nuevas)
- Modify: `src/gamepi13/ui.cpp` (implementarlas, reusando el panel de overlay existente)

- [ ] **Step 1: Declarar en `src/gamepi13/ui.h`**

Buscar el final del archivo:

```cpp
void gamepi_ui_overlay_mode(uint8_t mode);  // Select pressed
void gamepi_ui_overlay_param(uint8_t mode, bool is_b, uint16_t val);  // L/R adjust
```

Agregar después:

```cpp
// Browse-SD mode (modo 8 del selector). Todas reusan el panel del overlay;
// llamarlas SOLO desde el lazo de botones de main.cpp, nunca desde
// gamepi_ui_tick() -- evitan competir con el dashboard normal por pantalla.
void gamepi_ui_sd_listing();
void gamepi_ui_sd_browse(const char *filename, uint32_t index, uint32_t count);
void gamepi_ui_sd_confirm_progress(const char *filename, uint8_t percent);
void gamepi_ui_sd_loading(const char *filename);
void gamepi_ui_sd_result(bool ok, const char *filename);
void gamepi_ui_sd_error(const char *message);
```

- [ ] **Step 2: Implementar en `src/gamepi13/ui.cpp`**

Agregar al final del archivo (después de `gamepi_ui_overlay_param`):

```cpp
static void sd_panel_title(const char *title, UWORD color) {
  overlay_show_panel();
  Paint_DrawString_EN(centered_x(title, 11), (uint16_t)(kOverlay.y + 12),
                      title, &Font16, color, COL_DARK);
}

// Truncate long filenames to what the overlay's 200px width can show at
// Font12 (7px/char) with some margin: ~26 chars.
static void draw_truncated(const char *text, uint16_t y, UWORD color) {
  char buf[27];
  size_t len = strlen(text);
  if (len > sizeof(buf) - 1) len = sizeof(buf) - 1;
  memcpy(buf, text, len);
  buf[len] = '\0';
  Paint_DrawString_EN(centered_x(buf, 7), y, buf, &Font12, color, COL_DARK);
}

void gamepi_ui_sd_listing() {
  if (!flush_allowed()) return;
  sd_panel_title("SD", COL_GRAY);
  draw_truncated("Leyendo tarjeta...", (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
}

void gamepi_ui_sd_browse(const char *filename, uint32_t index, uint32_t count) {
  if (!flush_allowed()) return;
  char pos[12];
  snprintf(pos, sizeof(pos), "%lu/%lu", (unsigned long)(index + 1),
           (unsigned long)count);
  sd_panel_title(pos, COL_GRAY);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50), COL_PINK);
  draw_truncated("Mantener R para cargar", (uint16_t)(kOverlay.y + 86),
                 COL_GRAY);
  flush(kOverlay);
}

void gamepi_ui_sd_confirm_progress(const char *filename, uint8_t percent) {
  if (!flush_allowed()) return;
  sd_panel_title("Cargando...", COL_CYAN);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50), COL_WHITE);
  uint16_t bx = (uint16_t)(kOverlay.x + (kOverlay.w - 170) / 2);
  uint16_t by = (uint16_t)(kOverlay.y + 86);
  Paint_DrawRectangle(bx, by, (uint16_t)(bx + 170), (uint16_t)(by + 10),
                      COL_BG, DOT_PIXEL_1X1, DRAW_FILL_FULL);
  uint16_t w = (uint16_t)((uint32_t)percent * 170u / 100u);
  if (w > 0) {
    Paint_DrawRectangle(bx, by, (uint16_t)(bx + w), (uint16_t)(by + 10),
                        COL_CYAN, DOT_PIXEL_1X1, DRAW_FILL_FULL);
  }
  flush(kOverlay);
}

void gamepi_ui_sd_loading(const char *filename) {
  // Flushed once, unthrottled: this is the LAST LCD write before core0 stops
  // touching spi1 for the duration of the actual SD-read+flash-write (see
  // main.cpp's mode-8 handler) -- deliberately bypasses flush_allowed() so
  // the message is guaranteed on screen before that quiet window starts.
  sd_panel_title("Cargando...", COL_CYAN);
  draw_truncated(filename, (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
}

void gamepi_ui_sd_result(bool ok, const char *filename) {
  if (!flush_allowed()) return;
  sd_panel_title(ok ? "Listo" : "Error", ok ? COL_GREEN : COL_PINK);
  draw_truncated(ok ? filename : "No se pudo cargar",
                 (uint16_t)(kOverlay.y + 50), COL_WHITE);
  flush(kOverlay);
}

void gamepi_ui_sd_error(const char *message) {
  if (!flush_allowed()) return;
  sd_panel_title("SD", COL_GRAY);
  draw_truncated(message, (uint16_t)(kOverlay.y + 50), COL_PINK);
  flush(kOverlay);
}
```

Nota: `gamepi_ui_sd_loading()` es la única que NO respeta `flush_allowed()` a propósito (comentario incluido) — todas las demás sí, igual que el resto del overlay.

- [ ] **Step 3: Build de ambas variantes**

Expected: `MAKE_OK` ×2 (estas funciones compilan pero aún no las llama nadie — se conectan en el Task 5).

- [ ] **Step 4: Commit**

```bash
git add src/gamepi13/ui.h src/gamepi13/ui.cpp
git commit -m "feat: pantallas del modo Browse SD (listado, navegacion, progreso, resultado)"
```

---

### Task 5: Modo 8 en el selector + manejo de botones

**Files:**
- Modify: `src/main.cpp` (extender el selector a 9 modos, agregar el estado y el manejo de botones del modo 8)

- [ ] **Step 1: Incluir el header de SD**

Buscar (ya existe):

```cpp
#include "gamepi13/ui.h"
```

Agregar justo después:

```cpp
#include "PikoSampleManager.h"
```

- [ ] **Step 2: Agregar el estado del modo 8**

Buscar (Fase 1, declaraciones globales bajo `#if PIKO_GAMEPI13`):

```cpp
bool gamepi_start_used_as_modifier = false;
#else
```

Reemplazar por:

```cpp
bool gamepi_start_used_as_modifier = false;

// Modo 8 (Browse SD) state machine.
enum GamepiSdState {
  GAMEPI_SD_IDLE,      // not in mode 8, or entered but nothing requested yet
  GAMEPI_SD_LISTING,   // waiting for gamepi_sd_list_done
  GAMEPI_SD_BROWSE,    // list ready, user navigating with L/R
  GAMEPI_SD_LOADING,   // waiting for gamepi_sd_load_done
  GAMEPI_SD_RESULT,    // showing success/fail briefly
};
GamepiSdState gamepi_sd_state = GAMEPI_SD_IDLE;
uint32_t gamepi_sd_index = 0;
uint16_t gamepi_sd_result_ticks = 0;
#define GAMEPI_SD_RESULT_TICKS 100  // brief pause before returning to browse
#else
```

- [ ] **Step 3: Extender el selector a 9 modos**

Buscar (Fase 1, handler de Select):

```cpp
      if (btn_select.ChangedHigh(true) && btn_select.On()) {
        gamepi_selector = (gamepi_selector + 1) % 8;
        input_knob[0].SetBucket(gamepi_selector, 8);
        gamepi_ui_overlay_mode(gamepi_selector);
      }
```

Reemplazar por:

```cpp
      if (btn_select.ChangedHigh(true) && btn_select.On()) {
        const uint8_t was = gamepi_selector;
        gamepi_selector = (gamepi_selector + 1) % 9;
        if (gamepi_selector < 8) {
          input_knob[0].SetBucket(gamepi_selector, 8);
          gamepi_ui_overlay_mode(gamepi_selector);
        }
        if (gamepi_selector == 8) {
          // Entering Browse SD: kick off the async directory listing.
          // Reset the repeat counters too -- Step 4 gates Function A/B's L/R
          // block out of this mode, so whatever gamepi_repeat_r held from
          // before Select was pressed would otherwise leak into the
          // hold-to-confirm countdown's own use of the same variable.
          gamepi_sd_state = GAMEPI_SD_LISTING;
          gamepi_sd_index = 0;
          gamepi_repeat_l = 0;
          gamepi_repeat_r = 0;
          gamepi_sd_list_done = false;
          __asm volatile("dmb" ::: "memory");
          gamepi_sd_list_requested = true;
          gamepi_ui_sd_listing();
        } else if (was == 8) {
          // Leaving Browse SD: unmount, don't leave the card open.
          gamepi_sd_unmount_requested = true;
          gamepi_sd_state = GAMEPI_SD_IDLE;
        }
      }
```

- [ ] **Step 4: Acotar el bloque de L/R de Fase 1 a los modos 0–7**

El bloque de Function A/B de Fase 1 (`{ const uint8_t active_knob = ...`) no está condicionado por `gamepi_selector` — corre siempre, y usa `gamepi_repeat_r` con una semántica (cuenta regresiva de "delay antes de repetir", 25→0) incompatible con el contador de confirmación del modo 8 que se agrega en el Step 5 (cuenta ascendente 0→250). Sin acotarlo, ambos bloques pisarían la misma variable en el mismo tick mientras el usuario mantiene R en el modo 8, y de paso se dispararía un overlay de Function A/B espurio (`gamepi_ui_overlay_param` con `mode=8`, que su propio `mode &= 7` interpretaría como modo 0).

Buscar (Fase 1, bloque completo sin cambios):

```cpp
      {
        const uint8_t active_knob = btn_start.On() ? 2 : 1;
        if (btn_l.On()) {
          if (gamepi_repeat_l == 0) {
            input_knob[active_knob].Adjust(-GAMEPI_KNOB_STEP);
            if (active_knob == 2) gamepi_start_used_as_modifier = true;
            gamepi_ui_overlay_param(gamepi_selector, active_knob == 2,
                                    input_knob[active_knob].Value());
            gamepi_repeat_l = GAMEPI_REPEAT_TICKS;
          } else {
            gamepi_repeat_l--;
          }
        } else {
          gamepi_repeat_l = 0;
        }
        if (btn_r.On()) {
          if (gamepi_repeat_r == 0) {
            input_knob[active_knob].Adjust(GAMEPI_KNOB_STEP);
            if (active_knob == 2) gamepi_start_used_as_modifier = true;
            gamepi_ui_overlay_param(gamepi_selector, active_knob == 2,
                                    input_knob[active_knob].Value());
            gamepi_repeat_r = GAMEPI_REPEAT_TICKS;
          } else {
            gamepi_repeat_r--;
          }
        } else {
          gamepi_repeat_r = 0;
        }
      }
```

Reemplazar por el mismo bloque envuelto en `if (gamepi_selector < 8) { ... }` (cuerpo interior sin ningún otro cambio):

```cpp
      if (gamepi_selector < 8) {
        const uint8_t active_knob = btn_start.On() ? 2 : 1;
        if (btn_l.On()) {
          if (gamepi_repeat_l == 0) {
            input_knob[active_knob].Adjust(-GAMEPI_KNOB_STEP);
            if (active_knob == 2) gamepi_start_used_as_modifier = true;
            gamepi_ui_overlay_param(gamepi_selector, active_knob == 2,
                                    input_knob[active_knob].Value());
            gamepi_repeat_l = GAMEPI_REPEAT_TICKS;
          } else {
            gamepi_repeat_l--;
          }
        } else {
          gamepi_repeat_l = 0;
        }
        if (btn_r.On()) {
          if (gamepi_repeat_r == 0) {
            input_knob[active_knob].Adjust(GAMEPI_KNOB_STEP);
            if (active_knob == 2) gamepi_start_used_as_modifier = true;
            gamepi_ui_overlay_param(gamepi_selector, active_knob == 2,
                                    input_knob[active_knob].Value());
            gamepi_repeat_r = GAMEPI_REPEAT_TICKS;
          } else {
            gamepi_repeat_r--;
          }
        } else {
          gamepi_repeat_r = 0;
        }
      }
```

Con `gamepi_selector == 8`, este bloque queda sin ejecutar — `gamepi_repeat_l`/`gamepi_repeat_r` quedan congelados en lo que valían al entrar al modo (se re-arrancan limpio en el Step 6, abajo, apenas se detecta `gamepi_selector==8` por primera vez tras el cambio de Select).

- [ ] **Step 5: Manejo del estado del modo 8**

Insertar el manejo del modo 8 **inmediatamente después** del bloque recién acotado, todavía dentro del mismo `#if PIKO_GAMEPI13`:

```cpp
      if (gamepi_selector == 8) {
        switch (gamepi_sd_state) {
          case GAMEPI_SD_IDLE:
            break;
          case GAMEPI_SD_LISTING:
            if (gamepi_sd_list_done) {
              if (gamepi_sd_file_count() == 0) {
                gamepi_ui_sd_error("Sin tarjeta o sin archivos");
                gamepi_sd_state = GAMEPI_SD_IDLE;
              } else {
                gamepi_sd_index = 0;
                gamepi_sd_state = GAMEPI_SD_BROWSE;
                gamepi_ui_sd_browse(gamepi_sd_file_name(0), 0,
                                    gamepi_sd_file_count());
              }
            }
            break;
          case GAMEPI_SD_BROWSE: {
            const uint32_t count = gamepi_sd_file_count();
            bool moved = false;
            if (btn_l.ChangedHigh(true) && btn_l.On() && count > 0) {
              gamepi_sd_index = (gamepi_sd_index + count - 1) % count;
              moved = true;
            }
            if (btn_r.ChangedHigh(true) && btn_r.On() && count > 0) {
              gamepi_sd_index = (gamepi_sd_index + 1) % count;
              moved = true;
            }
            if (moved) {
              // Same tick's rising edge already navigated; don't also let it
              // seed the confirm countdown below (that starts from the NEXT
              // tick if R is still held).
              gamepi_repeat_r = 0;
              gamepi_ui_sd_browse(gamepi_sd_file_name(gamepi_sd_index),
                                  gamepi_sd_index, count);
            }
            if (btn_r.On() && !moved) {
              if (gamepi_repeat_r == 0) {
                // Held past the repeat threshold without triggering a new
                // navigation step: start the confirm countdown.
                gamepi_repeat_r = 1;  // reuse as a hold-progress counter now
              } else if (gamepi_repeat_r < GAMEPI_REPEAT_TICKS * 10) {
                gamepi_repeat_r++;
                const uint8_t pct = (uint8_t)(
                    (gamepi_repeat_r * 100u) / (GAMEPI_REPEAT_TICKS * 10u));
                gamepi_ui_sd_confirm_progress(
                    gamepi_sd_file_name(gamepi_sd_index), pct);
                if (gamepi_repeat_r >= GAMEPI_REPEAT_TICKS * 10) {
                  gamepi_ui_sd_loading(gamepi_sd_file_name(gamepi_sd_index));
                  gamepi_sd_load_index = gamepi_sd_index;
                  gamepi_sd_load_done = false;
                  __asm volatile("dmb" ::: "memory");
                  gamepi_sd_load_requested = true;
                  gamepi_sd_state = GAMEPI_SD_LOADING;
                }
              }
            } else if (!btn_r.On()) {
              gamepi_repeat_r = 0;
            }
            break;
          }
          case GAMEPI_SD_LOADING:
            if (gamepi_sd_load_done) {
              gamepi_ui_sd_result(gamepi_sd_load_ok,
                                  gamepi_sd_file_name(gamepi_sd_load_index));
              gamepi_sd_result_ticks = GAMEPI_SD_RESULT_TICKS;
              gamepi_sd_state = GAMEPI_SD_RESULT;
            }
            break;
          case GAMEPI_SD_RESULT:
            if (gamepi_sd_result_ticks > 0) {
              gamepi_sd_result_ticks--;
            } else {
              gamepi_sd_state = GAMEPI_SD_BROWSE;
              gamepi_ui_sd_browse(gamepi_sd_file_name(gamepi_sd_index),
                                  gamepi_sd_index, gamepi_sd_file_count());
            }
            break;
        }
      }
```

Nota de diseño: `gamepi_repeat_r` se reusa deliberadamente como contador de "mantenido" dentro del modo 8 (en vez de declarar una variable nueva) — el Step 4 ya garantiza que el bloque de Function A/B (el otro dueño de esa variable) no corre mientras `gamepi_selector == 8`, así que no hay conflicto. El umbral de confirmación es `GAMEPI_REPEAT_TICKS * 10` ticks (~1s si `GAMEPI_REPEAT_TICKS` sigue calibrado a "~100ms" como dice su comentario original — ver la advertencia sobre el tick real del lazo en `GAMEPI13-INTERFACE.md` sección 5; si en hardware el tiempo de hold se siente distinto a 1 segundo, es la MISMA causa ya documentada, no un bug nuevo de esta fase).

- [ ] **Step 6: Build de ambas variantes**

Expected: `MAKE_OK` ×2. `build/` no cambia.

- [ ] **Step 7: Commit**

```bash
git add src/main.cpp
git commit -m "feat: modo 8 (Browse SD) - navegar con L/R, confirmar manteniendo R"
```

---

### Task 6: Botón de descarga en la web app

**Files:**
- Modify: `web/src/App.tsx`

- [ ] **Step 1: Agregar la función de descarga de banco**

Confirmado en el código actual: `buildBankBlob` ya está importado (línea 26), el ícono `Download` ya está importado y en uso por `downloadFirmware` (línea 15/793), y `uploadBank()` (línea 481) ya usa `device.capacityBytes` como segundo argumento de `buildBankBlob`. Agregar la función nueva justo antes de `function uploadBank()`:

```tsx
  function downloadBankFile() {
    if (samples.length === 0) return;
    const blob = buildBankBlob(samples, device?.capacityBytes ?? 0);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'bank.pikobank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
```

- [ ] **Step 2: Agregar el botón junto a Upload en el JSX**

Buscar el botón de Upload (líneas 777-786 actuales):

```tsx
          <button
            data-tour="upload"
            onClick={uploadBank}
            disabled={uploadDisabled}
            className={uploadNeedsSync ? 'needs-sync' : undefined}
            title={uploadNeedsSync ? 'Upload changes to sync pikocore' : 'Upload the current sample bank to the device'}
          >
            <Upload size={18} />
            Upload
          </button>
```

Agregar un botón hermano justo después (mismo estilo, sin `data-tour` ni `className` porque no es parte del tour guiado ni tiene estado condicional):

```tsx
          <button
            onClick={downloadBankFile}
            disabled={samples.length === 0}
            title="Download the current bank as a .pikobank file to copy to an SD card"
          >
            <Download size={18} />
            Download bank
          </button>
```

- [ ] **Step 3: Verificar en el navegador**

```bash
cd web && npm run dev
```

Abrir la app, agregar al menos una muestra (Add), confirmar que el botón "Download bank" se habilita y que al hacer click se descarga un archivo `bank.pikobank`. No hace falta un dispositivo conectado para esta prueba.

- [ ] **Step 4: Commit**

```bash
git add web/src/App.tsx
git commit -m "feat: boton para descargar el banco actual como .pikobank"
```

---

### Task 7: Verificación en hardware (requiere al usuario con la placa + una SD)

**Files:** ninguno

- [ ] **Step 1: Preparar la tarjeta**

Formatear una microSD como FAT32. Con la web app (`npm run dev` en `web/`), armar 2-3 bancos distintos (Add + Upload normal para probarlos, o directamente Download) y copiar los `.pikobank` resultantes al directorio raíz de la tarjeta.

- [ ] **Step 2: Grabar** `build-gamepi/pikocore.uf2` con la tarjeta puesta en el socket del RP2350-PiZero.

- [ ] **Step 3: Checklist** (si algo falla → `superpowers:systematic-debugging`, no parchar a ciegas — este es el código con más riesgo nuevo de toda la fase, el mutex de `spi1` en particular):

1. Arranca normal (dashboard, audio) — regresión básica.
2. Presionar Select hasta llegar al modo 8 (9no, después de Volumen): aparece "Leyendo tarjeta..." y después la lista con el primer archivo.
3. L/R navegan la lista, el nombre y la posición cambian en pantalla, **el audio no se corta**.
4. Mantener R: aparece la barra de progreso, sube durante ~1s, y dispara "Cargando...".
5. Soltar el nuevo banco: el LCD muestra "Listo" con el nombre, y el audio pasa a reproducir ese banco.
6. Volver a Select (salir del modo 8) y volver a entrar: la lista se relee (nueva llamada a `sd_list_files`), confirma que el desmontaje/remontaje no cuelga nada.
7. **Sin tarjeta puesta**: entrar al modo 8, ver "Sin tarjeta o sin archivos", salir sin crash.
8. **Soltar R antes de completar el segundo** (cancelar): el banco actual no cambia, no hubo escritura a flash.
9. **Estrés**: retirar la tarjeta a mitad de una carga (mantenida hasta pasar el umbral). El dispositivo no debe colgarse; en el peor caso, "Error" en pantalla y el banco anterior debe seguir sonando (no corrompido).
10. Con el dashboard normal refrescándose (LEDs moviéndose con el beat) antes de entrar al modo 8, confirmar que no hay parpadeos ni artefactos extraños en el LCD durante una carga — validación indirecta del mutex de `spi1`.

- [ ] **Step 4: Si algo falla de forma difícil de diagnosticar**

```bash
git reset --hard fase2-completa-verificada
```

vuelve al estado anterior, verificado. Documentar qué se intentó y por qué se abortó antes de reintentar.

---

### Task 8: Documentación

**Files:**
- Modify: `README-GAMEPI13.md`
- Modify: `GAMEPI13-INTERFACE.md`

- [ ] **Step 1: `README-GAMEPI13.md`** — agregar a la tabla de controles:

```markdown
| Select (9 veces) | entra al modo Browse SD |
```

Y una sección nueva antes de "## más detalle":

```markdown
## microSD

Poné archivos `.pikobank` (generados con "Download bank" en la web app) en la
raíz de una microSD FAT32 y montala en el socket integrado del RP2350-PiZero.
En el instrumento, Select hasta el modo 9 (Browse SD): L/R navegan la lista,
mantener R ~1s carga el banco resaltado.
```

- [ ] **Step 2: `GAMEPI13-INTERFACE.md`** — agregar el modo 8 a la tabla de la sección 3, y una entrada nueva a la sección 2 (combos) o una sección 3-bis describiendo la mecánica de navegación/confirmación, con referencia a `src/main.cpp`'s `GamepiSdState`.

- [ ] **Step 3: Commit**

```bash
git add README-GAMEPI13.md GAMEPI13-INTERFACE.md
git commit -m "docs: documentar el modo Browse SD (Fase 3)"
```

---

## Fuera de alcance (posible Fase 3.1)

- Detección de inserción/extracción en caliente (`Card Detect`).
- Subcarpetas / navegación jerárquica (hoy solo lista el directorio raíz).
- Renombrar/borrar archivos desde el dispositivo.
- Indicador de "banco actualmente cargado" resaltado en la lista (hoy no se distingue visualmente cuál de los archivos listados es el que está sonando).
