# Port de pikocore a RP2350-PiZero + GamePi13 — Plan de Implementación (Fase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Firmware pikocore funcional en la placa Waveshare RP2350-PiZero con el HAT GamePi13: audio por el parlante/jack integrado (GP18), los 8 botones musicales mapeados al d-pad + ABXY, los 3 knobs emulados con Select/Start/L/R, y sin tocar ningún GPIO que entre en conflicto con el LCD o los botones.

**Architecture:** Se agrega un flag de compilación `PIKO_GAMEPI13` (opción CMake) que activa un nuevo header de pines (`src/hw_gamepi13.h`), sustituye la clase `Knob` (ADC) por una `VirtualKnob` controlada por botones, y desactiva las escrituras GPIO de los 8 LEDs (esos pines ahora son botones del GamePi13 — escribirlos podría causar cortocircuitos). El hardware original de pikocore sigue compilando sin el flag. La UI en el LCD ST7789 es la **Fase 2** (plan separado; los valores de LED quedan en memoria listos para leerse desde la UI).

**Tech Stack:** pico-sdk 2.1.1, CMake, C++17, board `waveshare_rp2350_pizero` (header incluido en el repo), tinyusb. Sin framework de tests en el firmware: la "prueba" de cada tarea es el build (compila/no compila) más verificación en hardware al final.

---

## Contexto para quien ejecuta (léelo antes de empezar)

### Hardware y pines (verificados contra los demos del repo, NO contra la tabla BCM del wiki)

Fuentes: `Gamepi13-RP2040-Demo/C/lib/Config/DEV_Config.c:162-171` (LCD/I2C), `Gamepi13-RP2040-Demo/C/examples/LCD_1in3_test.c:86-99` (botones), `Gamepi13-RP2040-Demo/Python/micropython_GamePi13/Pong/board.py` (buzzer=18, LED=28). La tabla "BCM coding" de `www-waveshare-com-wiki-GamePi13.md` difiere del código real en los botones X/Y/R/Up — confiar en el código.

**GPIO ocupados por el GamePi13:** 2,3 (I2C IMU), 4 (R), 5 (X), 6 (Down), 7 (BL LCD), 8 (CS), 9 (Y), 10 (SCK), 11 (MOSI), 13 (Right), 15 (Up), 16 (Left), 18 (AUDIO: parlante+jack), 19 (Select), 20 (B), 21 (A), 23 (L), 24 (IR TX), 25 (DC), 26 (Start), 27 (RST LCD), 28 (LED estado).
**GPIO libres:** 0,1 (UART), 12, 14, 17, 22, 29.

### Pines del pikocore original que hay que reubicar

| Función | Original | Nuevo (GamePi13) | Motivo |
|---|---|---|---|
| Audio PWM | GP20 | **GP18** | GP20 es botón B; GP18 va al parlante/jack del GamePi13 |
| LED de beat | `PICO_DEFAULT_LED_PIN` (no existe en esta placa) | **GP28** | LED de estado del GamePi13 |
| 8 botones | GP4–11 | **{15,6,16,13,9,5,20,21}** | GP4–11 chocan con LCD y otros botones |
| 8 LEDs | GP12–19 | **stub (sin GPIO)** | GP13/15/16/19 son botones: escribirlos como salida y presionar el botón = corto a GND |
| Knobs ADC | GP26–28 | **VirtualKnob (botones)** | GP26=Start, GP27=RST del LCD, GP28=LED |
| Trigger out | GP21 | **GP12** | GP21 es botón A |
| Clock in | GP22 | GP22 (sin cambio) | libre |
| GP23 salida-baja (ahorro energía del Pico) + WS2812 en GP23 | GP23 | **eliminado bajo el flag** | GP23 es el botón L |

### Esquema de controles (decisión de diseño ya acordada)

- **Up, Down, Left, Right, Y, X, B, A** = botones musicales 0–7 de pikocore (los combos de 4 botones del firmware siguen funcionando).
- **Select** = cicla el "selector" (knob 0) entre los 8 modos de parámetro.
- **L / R** = decrementa / incrementa el knob activo (Function A = knob 1). Mantener presionado repite (~100 ms).
- **Start (mantenido) + L/R** = ajusta Function B (knob 2).

### Advertencia de seguridad de hardware

**NO grabar el firmware en la placa con el GamePi13 conectado hasta completar la Tarea 5.** Antes de eso el firmware configura GPIO de botones como salidas (LEDs GP12–19, GP23 en bajo), y presionar un botón cortocircuitaría una salida en alto contra GND.

### Entorno de build (Windows)

El repo se compila con CMake + pico-sdk; los headers generados (`doth/easing.h`, `doth/filter.h`) ya están en el repo, así que **no** hace falta Go/Python/clang-format. Dos opciones:

- **WSL (recomendado):** `sudo apt install cmake gcc-arm-none-eabi build-essential`, luego los comandos de este plan tal cual.
- **Windows nativo:** instalar ARM GNU Toolchain + CMake + Ninja (o usar el toolchain de la extensión Pico de VS Code en `%USERPROFILE%\.pico-sdk\`), y agregar `-G Ninja` a los comandos `cmake`, reemplazando `make -j4` por `ninja`.

Los comandos de este plan asumen bash (WSL o Git Bash) desde la raíz del repo `C:\pikocore-main`.

---

### Task 0: Inicializar git

El directorio no es un repositorio git; el plan requiere commits frecuentes.

**Files:** ninguno (solo git)

- [ ] **Step 1: Init y commit del estado base**

```bash
cd /c/pikocore-main   # en WSL: /mnt/c/pikocore-main
git init
git add -A
git commit -m "chore: estado base del repo antes del port RP2350-PiZero + GamePi13"
```

Expected: commit creado sin errores. Nota: `.gitignore` ya excluye `build/`.

---

### Task 1: Toolchain + build base (hardware original, RP2040)

Verifica que el toolchain funciona ANTES de tocar código. Cualquier error aquí es de entorno, no del port.

**Files:**
- Create: `pico-sdk/` (clon, queda ignorado por git — verificar)

- [ ] **Step 1: Clonar pico-sdk 2.1.1**

```bash
git clone https://github.com/raspberrypi/pico-sdk
cd pico-sdk && git checkout 2.1.1 && git submodule update --init && cd ..
```

Expected: checkout en tag 2.1.1, submódulos (tinyusb, etc.) inicializados.

- [ ] **Step 2: Asegurar que pico-sdk no entre al repo**

Verificar que `.gitignore` contenga `pico-sdk` (el CMakeLists ya lo busca en `./pico-sdk`); si no está, agregar la línea `pico-sdk/` a `.gitignore` y hacer commit:

```bash
grep -q "pico-sdk" .gitignore || (echo "pico-sdk/" >> .gitignore && git add .gitignore && git commit -m "chore: ignorar pico-sdk local")
```

- [ ] **Step 3: Build del firmware original**

```bash
mkdir -p build && cd build
cmake -DPICO_SDK_PATH=../pico-sdk ..
make -j4
cd ..
```

Expected: termina con `[100%] ... pikocore.uf2` y el reporte `--print-memory-usage` sin overflow. Si falla aquí, arreglar el entorno antes de continuar.

---

### Task 2: Opción CMake `PIKO_GAMEPI13` + board RP2350-PiZero

**Files:**
- Modify: `CMakeLists.txt` (líneas 1–13 y después de la línea 58)

- [ ] **Step 1: Agregar la opción y la selección de placa ANTES de `include(pico_sdk_import.cmake)`**

En `CMakeLists.txt`, entre `cmake_minimum_required(...)` y el bloque `if(NOT PICO_SDK_PATH)`, insertar:

```cmake
option(PIKO_GAMEPI13 "Build for Waveshare RP2350-PiZero + GamePi13" OFF)
if(PIKO_GAMEPI13)
	list(APPEND PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/boards)
	set(PICO_BOARD waveshare_rp2350_pizero CACHE STRING "Board type")
endif()
```

(El header `RP2350-PiZero/C/boards/waveshare_rp2350_pizero.h` ya existe en el repo y declara `PICO_PLATFORM rp2350` y flash de 16 MB.)

- [ ] **Step 2: Propagar el flag al código, después de `include(target_compile_definitions.cmake)` (línea 58)**

```cmake
if(PIKO_GAMEPI13)
	target_compile_definitions(${PROJECT_NAME} PRIVATE PIKO_GAMEPI13=1)
endif()
```

- [ ] **Step 3: Verificar que el build original NO se rompió (flag OFF)**

```bash
cd build && cmake -DPICO_SDK_PATH=../pico-sdk .. && make -j4 && cd ..
```

Expected: PASS igual que en Task 1.

- [ ] **Step 4: Verificar que el build GamePi13 falla donde esperamos (este es el "test que falla")**

```bash
mkdir -p build-gamepi && cd build-gamepi
cmake -DPICO_SDK_PATH=../pico-sdk -DPIKO_GAMEPI13=ON ..
make -j4 2>&1 | tail -20
cd ..
```

Expected: la configuración CMake dice `Target board (PICO_BOARD) is 'waveshare_rp2350_pizero'` y la compilación **FALLA** en `src/main.cpp` con `error: 'LED_PIN' was not declared in this scope` (la placa no define `PICO_DEFAULT_LED_PIN`). Ese error lo resuelve la Task 3.

- [ ] **Step 5: Ignorar el nuevo dir de build y commit**

```bash
echo "build-gamepi/" >> .gitignore
git add CMakeLists.txt .gitignore
git commit -m "feat: opcion CMake PIKO_GAMEPI13 con board waveshare_rp2350_pizero"
```

---

### Task 3: Header de pines + remapeo en main.cpp

Al terminar esta tarea el build GamePi13 compila, pero **AÚN NO ES SEGURO GRABARLO** (LEDs y knobs todavía tocan GPIO del HAT — Tasks 4 y 5).

**Files:**
- Create: `src/hw_gamepi13.h`
- Modify: `src/main.cpp` (bloque de defines ~líneas 50–57, declaración de knobs ~102, inicialización en `main()` ~1385–1404)

- [ ] **Step 1: Crear `src/hw_gamepi13.h`**

```cpp
#pragma once
// Pin map: Waveshare RP2350-PiZero + GamePi13 HAT.
// Verified against Gamepi13-RP2040-Demo/C/lib/Config/DEV_Config.c (LCD/I2C),
// LCD_1in3_test.c (buttons) and Python demos (buzzer=GP18, status LED=GP28).
// Do NOT trust the BCM column of the Waveshare wiki table (X/Y/R/Up differ).

// GamePi13 onboard PWM audio (speaker + headphone jack)
#define GAMEPI_AUDIO_PIN 18
// GamePi13 status LED, used as pikocore's beat LED
#define GAMEPI_LED_PIN 28
// Free header pins
#define GAMEPI_CLOCK_PIN 22  // clock in (same as original pikocore)
#define GAMEPI_TRIGO_PIN 12  // trigger out (original GP21 is button A)

// The 8 pikocore music buttons, pikocore order 0..7:
//                            Up  Dn  Lt  Rt   Y   X   B   A
#define GAMEPI_BUTTON_PINS {15, 6, 16, 13, 9, 5, 20, 21}

// Virtual-knob control buttons
#define GAMEPI_BTN_SELECT 19  // cycles selector (knob 0) through 8 modes
#define GAMEPI_BTN_START 26   // hold = edit Function B (knob 2) instead of A
#define GAMEPI_BTN_L 23       // decrease active knob
#define GAMEPI_BTN_R 4        // increase active knob

#define GAMEPI_KNOB_STEP 164    // ~4% of 4095 per repeat (full sweep ~2.5 s held)
#define GAMEPI_REPEAT_TICKS 25  // repeat every 100 ms at the 250 Hz input scan
```

- [ ] **Step 2: Reemplazar el bloque de defines de pines en `src/main.cpp`**

Buscar (líneas ~50–57):

```cpp
#define AUDIO_PIN 20   // audio out
#ifdef PICO_DEFAULT_LED_PIN
#define LED_PIN PICO_DEFAULT_LED_PIN
#endif
#define CLOCK_PIN 22  // clock in pin
#define TRIGO_PIN 21  // trigger out pin
```

Reemplazar por:

```cpp
#if PIKO_GAMEPI13
#include "hw_gamepi13.h"
#define AUDIO_PIN GAMEPI_AUDIO_PIN
#define LED_PIN GAMEPI_LED_PIN
#define CLOCK_PIN GAMEPI_CLOCK_PIN
#define TRIGO_PIN GAMEPI_TRIGO_PIN
// GamePi13 has no WS2812 strip; GP23 (original strip pin) is the L button.
#undef WS2812_ENABLED
#define WS2812_ENABLED 0
#else
#define AUDIO_PIN 20   // audio out
#ifdef PICO_DEFAULT_LED_PIN
#define LED_PIN PICO_DEFAULT_LED_PIN
#endif
#define CLOCK_PIN 22  // clock in pin
#define TRIGO_PIN 21  // trigger out pin
#endif
```

Nota: este bloque debe quedar ANTES de `#if WS2812_ENABLED == 1 / #include "doth/WS2812.hpp"` (línea ~59), que es donde se consume el macro.

- [ ] **Step 3: Quitar la salida GP23 bajo el flag**

Buscar en `main()` (~línea 1390):

```cpp
  gpio_init(23);
  gpio_pull_up(23);
  gpio_set_dir(23, GPIO_OUT);
  gpio_put(23, 0);
```

Reemplazar por:

```cpp
#if !PIKO_GAMEPI13
  // Pico power-save pin; on the GamePi13, GP23 is the L button.
  gpio_init(23);
  gpio_pull_up(23);
  gpio_set_dir(23, GPIO_OUT);
  gpio_put(23, 0);
#endif
```

- [ ] **Step 4: Remapear los 8 botones**

Buscar (~línea 1396):

```cpp
  for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
    input_button[i].Init(i + 4, 10);  // GPIO 4 through 11 are buttons
  }
```

Reemplazar por:

```cpp
#if PIKO_GAMEPI13
  const uint8_t gamepi_button_pins[NUM_BUTTONS] = GAMEPI_BUTTON_PINS;
  for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
    input_button[i].Init(gamepi_button_pins[i], 10);
  }
#else
  for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
    input_button[i].Init(i + 4, 10);  // GPIO 4 through 11 are buttons
  }
#endif
```

- [ ] **Step 5: Build de ambas variantes**

```bash
cd build-gamepi && cmake -DPICO_SDK_PATH=../pico-sdk -DPIKO_GAMEPI13=ON .. && make -j4 && cd ..
cd build && make -j4 && cd ..
```

Expected: ambas PASS. El build gamepi genera `build-gamepi/pikocore.uf2` (⚠ no grabar aún).

- [ ] **Step 6: Commit**

```bash
git add src/hw_gamepi13.h src/main.cpp
git commit -m "feat: mapa de pines GamePi13 (audio GP18, LED GP28, botones dpad+ABXY)"
```

---

### Task 4: Neutralizar los GPIO de los LEDs

`LEDArray` inicializa GP12–19 como salidas (`doth/ledarray.h:9` → `led[i].Init(i + 12)`); GP13/15/16/19 son botones del GamePi13. Se conserva TODO el estado en memoria (`dim`, `vals`) para que la UI del LCD (Fase 2) lo lea.

**Files:**
- Modify: `doth/led.h`

- [ ] **Step 1: Proteger las llamadas GPIO en `doth/led.h`**

Reemplazar el contenido completo del archivo por:

```cpp
class LED {
  uint8_t gpio;
  uint8_t state;
  uint8_t dim;
  uint8_t dim_i;

 public:
  void Init(uint8_t gpio_) {
    gpio = gpio_;
#if !PIKO_GAMEPI13
    gpio_init(gpio);
    gpio_set_dir(gpio, GPIO_OUT);
    gpio_put(gpio, 0);
#endif
    state = 0;
    dim_i = 0;
  }

  uint8_t Val() { return dim; }

  void Update() {
    dim_i++;
#if !PIKO_GAMEPI13
    if (dim_i < dim) {
      gpio_put(gpio, 1);
    } else {
      gpio_put(gpio, 0);
    }
#endif
  }

  void Set(bool on) {
#if !PIKO_GAMEPI13
    if (on) {
      gpio_put(gpio, 1);
    } else {
      gpio_put(gpio, 0);
    }
#endif
    dim = on ? 255 : 0;
  }

  void SetDim(uint16_t dim_) {
    if (dim_ < 255) {
      dim = dim_;
    } else {
      dim = 255;
    }
  }
};
```

(Cambios respecto al original: los tres bloques `gpio_*` quedan tras `#if !PIKO_GAMEPI13`, y `Set()` ahora también refleja el estado en `dim` para que la Fase 2 pueda leerlo con `Val()`. En el build original `PIKO_GAMEPI13` no está definido → `!PIKO_GAMEPI13` evalúa 1 → comportamiento idéntico.)

- [ ] **Step 2: Build de ambas variantes**

```bash
cd build-gamepi && make -j4 && cd ..
cd build && make -j4 && cd ..
```

Expected: ambas PASS.

- [ ] **Step 3: Commit**

```bash
git add doth/led.h
git commit -m "feat: LEDs sin GPIO bajo PIKO_GAMEPI13 (pines compartidos con botones)"
```

---

### Task 5: Knobs virtuales controlados por botones

La clase `Knob` (`doth/knob.h`) lee ADC0–2 = GP26/27/28 (Start, RST del LCD, LED): en esta placa daría basura y movería parámetros solo. Se sustituye por `VirtualKnob` con la misma interfaz pública que consume `main.cpp` (`Init/Reset/Value/ValueMax/Read/Changed`).

**Files:**
- Create: `doth/virtualknob.h`
- Modify: `src/main.cpp` (include ~línea 26, declaración ~102, `adc_init()` ~1401, escaneo de entradas ~1632–1694)

- [ ] **Step 1: Crear `doth/virtualknob.h`**

```cpp
// Drop-in replacement for Knob when there is no ADC hardware.
// Value is driven by buttons via Adjust()/SetBucket() instead of adc_read().
class VirtualKnob {
  uint16_t val;
  bool pending;
  bool changed;

 public:
  void Init(uint8_t input_, uint16_t alpha_) {
    (void)input_;
    (void)alpha_;
    val = 2048;  // mid-scale; nothing is applied until the user adjusts
    pending = false;
    changed = false;
  }

  void Reset() {}

  uint16_t Value() { return val; }
  uint16_t ValueMax() { return 4095; }

  void Adjust(int32_t delta) {
    int32_t v = (int32_t)val + delta;
    if (v < 0) v = 0;
    if (v > 4095) v = 4095;
    if ((uint16_t)v != val) {
      val = (uint16_t)v;
      pending = true;
    }
  }

  // Set to the center of bucket k of `total`, so that
  // Value() * total / ValueMax() == k (used for the selector knob).
  void SetBucket(uint8_t k, uint8_t total) {
    uint32_t v = ((uint32_t)k * 4096u + 2048u) / total;
    if (v > 4095u) v = 4095u;
    if ((uint16_t)v != val) {
      val = (uint16_t)v;
      pending = true;
    }
  }

  // Same contract as Knob: Read() latches, Changed() reports one scan cycle.
  void Read() {
    changed = pending;
    pending = false;
  }

  bool Changed() { return changed; }
};
```

- [ ] **Step 2: Incluir y conmutar la clase en `src/main.cpp`**

Después de `#include "doth/knob.h"` (línea ~26) agregar:

```cpp
#include "doth/virtualknob.h"
```

Buscar (~línea 102):

```cpp
Knob input_knob[NUM_KNOBS];
```

Reemplazar por:

```cpp
#if PIKO_GAMEPI13
VirtualKnob input_knob[NUM_KNOBS];
Button btn_select, btn_start, btn_l, btn_r;
uint8_t gamepi_selector = 0;
uint16_t gamepi_repeat_l = 0;
uint16_t gamepi_repeat_r = 0;
#else
Knob input_knob[NUM_KNOBS];
#endif
```

- [ ] **Step 3: Inicialización en `main()`**

Buscar (~línea 1400):

```cpp
  // initialize knobs
  adc_init();
  for (uint8_t i = 0; i < NUM_KNOBS; i++) {
    input_knob[i].Init(i, 50);
  }
```

Reemplazar por:

```cpp
  // initialize knobs
#if PIKO_GAMEPI13
  for (uint8_t i = 0; i < NUM_KNOBS; i++) {
    input_knob[i].Init(i, 50);
  }
  btn_select.Init(GAMEPI_BTN_SELECT, 10);
  btn_start.Init(GAMEPI_BTN_START, 10);
  btn_l.Init(GAMEPI_BTN_L, 10);
  btn_r.Init(GAMEPI_BTN_R, 10);
#else
  adc_init();
  for (uint8_t i = 0; i < NUM_KNOBS; i++) {
    input_knob[i].Init(i, 50);
  }
#endif
```

- [ ] **Step 4: Manejo de los botones de knob en el escaneo a 250 Hz**

En el lazo de control, dentro de `if (clock_ms % 16 == 0) {` (~línea 1630), inmediatamente ANTES del comentario `// adc reading` (~línea 1691), insertar:

```cpp
#if PIKO_GAMEPI13
      // GamePi13: Select cycles the selector; L/R adjust Function A
      // (or Function B while Start is held), with hold-to-repeat.
      btn_select.Read();
      btn_start.Read();
      btn_l.Read();
      btn_r.Read();
      if (btn_select.ChangedHigh(true) && btn_select.On()) {
        gamepi_selector = (gamepi_selector + 1) % 8;
        input_knob[0].SetBucket(gamepi_selector, 8);
      }
      {
        const uint8_t active_knob = btn_start.On() ? 2 : 1;
        if (btn_l.On()) {
          if (gamepi_repeat_l == 0) {
            input_knob[active_knob].Adjust(-GAMEPI_KNOB_STEP);
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
            gamepi_repeat_r = GAMEPI_REPEAT_TICKS;
          } else {
            gamepi_repeat_r--;
          }
        } else {
          gamepi_repeat_r = 0;
        }
      }
#endif
```

(Queda fuera del gate `if (!btn_retrig)` a propósito: los ajustes solo marcan `pending`; el `Read()` de los knobs que los consume sigue dentro del gate, igual que el original.)

- [ ] **Step 5: Build de ambas variantes**

```bash
cd build-gamepi && make -j4 && cd ..
cd build && make -j4 && cd ..
```

Expected: ambas PASS. A partir de aquí `build-gamepi/pikocore.uf2` **ya es seguro para grabar**.

- [ ] **Step 6: Commit**

```bash
git add doth/virtualknob.h src/main.cpp
git commit -m "feat: knobs virtuales por botones Select/Start/L/R en GamePi13"
```

---

### Task 6: Grabar y verificar en hardware

**Files:** ninguno (verificación en dispositivo)

- [ ] **Step 1: Grabar el UF2**

Con el GamePi13 montado en el RP2350-PiZero: mantener BOOT, conectar USB, soltar BOOT. Copiar `build-gamepi/pikocore.uf2` a la unidad `RP2350` que aparece. La placa se reinicia sola.

- [ ] **Step 2: Cargar muestras de audio**

El firmware guarda las muestras en un banco de flash que se carga por USB con la web app del repo:

```bash
cd web && npm install && npm run dev
```

Abrir la URL que muestra vite (Chrome/Edge — usa WebUSB), conectar el dispositivo `pikocore` y subir los WAV de `audio2h/demo/`. Si la app no detecta el dispositivo, la página de firmware de https://pikocore.com es la alternativa.

- [ ] **Step 3: Checklist funcional en el dispositivo**

Verificar en orden; si algo falla, aplicar `superpowers:systematic-debugging` antes de seguir:

1. **Arranque**: el LED de estado (GP28) parpadea al ritmo del beat. Si la placa ni enumera USB, probar bajar `CLOCK_RATE` de 248000 a 240000 en `src/main.cpp:36` (overclock en RP2350) y recompilar.
2. **Audio**: se oye el sample por el parlante; al conectar audífonos al jack, suena por ahí.
3. **Botones musicales**: cada uno de Up/Down/Left/Right/Y/X/B/A salta a un slice distinto del sample (audible).
4. **Combo**: mantener Up+Down+B+A (botones 0,1,6,7) resetea los FX — comportamiento original del firmware.
5. **Knob selector**: presionar Select 1 vez (modo 1 = filtro, ver tabla de modos abajo) y mantener R: el filtro se abre progresivamente (audible). Mantener L: se cierra.
6. **Function B**: con el selector en modo 0, mantener Start y presionar R repetidamente: sube la intensidad del break FX (audible). En modo 1, Start+L/R cambia el timestretch.
7. **Persistencia**: ajustar volumen (Select hasta modo 7, luego L/R), apagar y encender: el volumen se conserva (se guarda en flash).

Tabla de modos del selector (de `src/main.cpp`, switches en ~1738 y ~1833):

| Modo | Function A (L/R) | Function B (Start+L/R) |
|---|---|---|
| 0 | selección de sample | break FX |
| 1 | filtro (LPF) | timestretch |
| 2 | noise gate | probabilidad de gate |
| 3 | probabilidad de jump | probabilidad de retrig |
| 4 | probabilidad de tunnel | probabilidad de reversa |
| 5 | grabar secuenciador | reproducir secuenciador |
| 6 | guardar (subir a tope) | cargar (subir a tope) |
| 7 | volumen/distorsión | — |

- [ ] **Step 4: Registrar resultados**

Anotar en el PR/commit final qué puntos del checklist pasaron. No declarar el port funcional sin evidencia de los 7 puntos (skill `superpowers:verification-before-completion`).

---

### Task 7: Documentación

**Files:**
- Create: `README-GAMEPI13.md`
- Modify: `README.md` (agregar un enlace en la sección `## diy`)

- [ ] **Step 1: Crear `README-GAMEPI13.md`**

```markdown
# pikocore en RP2350-PiZero + GamePi13

Port de pikocore a la Waveshare RP2350-PiZero con el HAT GamePi13
(LCD 1.3" ST7789, 12 botones, parlante + jack de audio en GP18).

## build

    mkdir -p build-gamepi && cd build-gamepi
    cmake -DPICO_SDK_PATH=../pico-sdk -DPIKO_GAMEPI13=ON ..
    make -j4

Grabar `build-gamepi/pikocore.uf2` (mantener BOOT al conectar USB).
Cargar muestras con la web app (`cd web && npm run dev`).

## controles

| Control | Función |
|---|---|
| Up Down Left Right Y X B A | botones musicales 1–8 de pikocore |
| Select | cicla el modo de parámetro 0–7 (equivale al knob selector) |
| L / R | baja / sube el parámetro activo (Function A); mantener repite |
| Start + L/R | ajusta Function B |

Modos: 0 sample/break · 1 filtro/stretch · 2 gate/prob-gate ·
3 prob-jump/prob-retrig · 4 prob-tunnel/prob-reversa ·
5 secuenciador rec/play · 6 save/load · 7 volumen
| Up+Down+B+A | reset de FX |
| Up+Right+Y+A | mute / start-stop |
| Down+Left+X+B | lock de clock |

## pines

Audio GP18 (parlante/jack del HAT) · LED de beat GP28 · clock in GP22 ·
trigger out GP12 · resto: ver `src/hw_gamepi13.h`.

La UI en el LCD (reemplazo de los 8 LEDs y visualización de knobs) es la
fase 2 del port; los valores ya quedan en memoria (`LED::Val()`).
```

- [ ] **Step 2: Enlazar desde `README.md`**

En la sección `## diy`, agregar al final de la lista:

```markdown
- [Port RP2350-PiZero + GamePi13](README-GAMEPI13.md)
```

- [ ] **Step 3: Commit**

```bash
git add README-GAMEPI13.md README.md
git commit -m "docs: guia de build y controles del port RP2350-PiZero + GamePi13"
```

---

## Fuera de alcance (Fase 2 — plan separado)

- Driver del LCD ST7789 (portar `lib/LCD` + `lib/Config` del demo GamePi13 al build de pikocore, SPI1 a 10 MHz+, backlight PWM en GP7).
- UI: barra de 8 "LEDs" desde `LEDArray`, nombre/valor del modo activo del selector, indicador de BPM/sample.
- Opcional: IMU ICM20948 (I2C GP2/3) como modulador de FX; IR; carga de muestras desde microSD del PiZero.
