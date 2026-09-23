# Web Simulator Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed a lightweight, real-firmware demo of pikocore (LCD + real audio + keyboard/gamepad input) into the web loader (`web/`), running the same firmware sources as the native simulator, compiled to WebAssembly with Emscripten.

**Architecture:** Compile `piko_fw` (the real firmware) + `sim_core` + `sim/runtime/*` — with `machine.cpp`'s Win32 Fibers replaced by Emscripten's `emscripten/fiber.h` — plus a new `sim/web/` platform layer, into a WASM module. A React component drives it from `requestAnimationFrame`, blits the LCD framebuffer to a `<canvas>`, feeds audio through an `AudioWorklet`, and maps keyboard/Gamepad API input to the firmware's button mask.

**Tech Stack:** Emscripten (emcc/em++, Asyncify), C++20, TypeScript/React (existing `web/` Vite app), Web Audio API (`AudioWorklet`), Gamepad API.

## Global Constraints

- Firmware defines (must match `target_compile_definitions.cmake` and `sim/CMakeLists.txt` exactly): `PIKO_GAMEPI13=1`, `PIKO_GAMEPI13_SD=0`, `PIKO_SIM=1`, `PIKO_FIRMWARE_RESERVE=524288u`, `WS2812_ENABLED=1`, `MIDI_IN_ENABLED=0`, `MIDI_RESET_EVERY_BEAT=16`, `MIDI_CLOCK_MULTIPLIER=2`, `MIDI_NOTE_KEY=0`, `PCB_V2_LAYOUT=0`.
- `src/main.cpp` must be compiled with `main` renamed to `piko_firmware_main` (same trick `sim/CMakeLists.txt` uses via `COMPILE_DEFINITIONS "main=piko_firmware_main"` — for emcc this is a `-Dmain=piko_firmware_main` flag scoped to that one file).
- No pthreads, no SharedArrayBuffer, no COOP/COEP headers — single browser main thread + one `AudioWorklet` thread only (per spec's threading-model decision).
- No filesystem access in the WASM build — `sim::flash().open("", &err)` (empty path = memory-only, per `sim/core/flash_store.h`), bank bytes come from `fetch()` in JS, not `sim::read_file`.
- Demo bank is fixed for v1: `build-sim/bin/amen_pad_bank.pikobank`, copied into `web/public/sim/`. No upload/drag-drop UI.
- No headless mode, no CLI flags, no `--dump-lcd`/`--dump-wav` — those stay native-only.
- Spec: [docs/superpowers/specs/2026-09-23-web-sim-demo-design.md](../specs/2026-09-23-web-sim-demo-design.md)

---

## File Structure

```
sim/web/
  fiber_shim.h / fiber_shim.cpp   Machine, ported: emscripten_fiber_* instead of Win32 Fibers
  main.cpp                        exported C API consumed by JS (init/step/lcd/audio/buttons)
  build.sh                        emcc build script → web/public/sim/pikocore_sim.{wasm,js}
web/public/sim/
  amen_pad_bank.pikobank          copied from build-sim/bin/, fixed demo bank
  sim-audio-worklet.js            AudioWorkletProcessor, pulls PCM from the WASM module
web/src/sim/
  simModule.ts                    loads the WASM module, owns init/step/buttons/lcd/audio glue
  keyboard.ts                     KeyboardEvent.code -> Button bit mapping
  gamepad.ts                      Gamepad API poll -> XInput-shaped mask -> piko_map_xinput()
  SimDemo.tsx                     React component: canvas, status line, controls legend
web/src/App.tsx                   modified: adds a collapsed "Try it in your browser" section
```

`sim/web/fiber_shim.cpp` is a fork of `sim/runtime/machine.cpp`, not an edit of it — the native
simulator keeps using Win32 Fibers unchanged. The two files must stay behaviorally identical
outside of the fiber primitives; any future change to `Machine`'s virtual-clock logic has to be
applied to both.

---

### Task 1: Emscripten toolchain + minimal build pipeline

**Files:**
- Create: `sim/web/build.sh`
- Create: `sim/web/hello.cpp` (deleted again in Task 2 once a real entry point exists)

**Interfaces:**
- Produces: a working `emcc`/`em++` invocation pattern that later tasks extend — the exact flag set (`-sASYNCIFY`, `-sMODULARIZE`, `-sEXPORT_ES6=1`, `-sEXPORTED_FUNCTIONS`, `-sEXPORTED_RUNTIME_METHODS`) that Task 4 finalizes.

- [ ] **Step 1: Install the Emscripten SDK**

```bash
git clone https://github.com/emscripten-core/emsdk.git ~/emsdk
cd ~/emsdk
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh
```

On Windows, run the equivalent `emsdk.bat install latest` / `emsdk.bat activate latest` /
`emsdk_env.bat` from a Git Bash or PowerShell prompt. Confirm the toolchain is on `PATH`:

Run: `emcc -v`
Expected: prints an `emcc (Emscripten gcc/clang-like replacement)` version banner, no error.

- [ ] **Step 2: Write a trivial smoke-test program**

```cpp
// sim/web/hello.cpp
#include <cstdio>
#include <emscripten/emscripten.h>

extern "C" EMSCRIPTEN_KEEPALIVE int piko_hello(int x) {
  return x + 1;
}

int main() {
  std::printf("pikocore-sim-web toolchain OK\n");
  return 0;
}
```

- [ ] **Step 3: Write the build script**

```bash
#!/usr/bin/env bash
# sim/web/build.sh
set -euo pipefail
cd "$(dirname "$0")"
OUT_DIR=../../web/public/sim
mkdir -p "$OUT_DIR"

em++ -std=c++20 -O2 \
  hello.cpp \
  -sMODULARIZE=1 -sEXPORT_ES6=1 -sEXPORT_NAME=createPikoSimModule \
  -sEXPORTED_FUNCTIONS=_piko_hello,_main \
  -sEXPORTED_RUNTIME_METHODS=ccall,cwrap \
  -o "$OUT_DIR/pikocore_sim.js"

echo "Built $OUT_DIR/pikocore_sim.js"
```

- [ ] **Step 4: Run the build and verify with Node**

```bash
chmod +x sim/web/build.sh
sim/web/build.sh
node -e "
import('./web/public/sim/pikocore_sim.js').then(async ({ default: createModule }) => {
  const mod = await createModule();
  console.log('piko_hello(41) =', mod.ccall('piko_hello', 'number', ['number'], [41]));
});
"
```

Expected: prints `pikocore-sim-web toolchain OK` (from `main()`, run automatically at module init)
and `piko_hello(41) = 42`.

- [ ] **Step 5: Commit**

```bash
git add sim/web/build.sh sim/web/hello.cpp
git commit -m "build: emscripten smoke-test pipeline for the web sim demo"
```

---

### Task 2: Fiber shim — port Machine off Win32 Fibers

**Files:**
- Create: `sim/web/fiber_shim.h`
- Create: `sim/web/fiber_shim.cpp` (forked from `sim/runtime/machine.cpp` and `machine.h`)
- Delete: `sim/web/hello.cpp` (superseded)

**Interfaces:**
- Consumes: `sim::PwmDac`, `sim::St7789` (unchanged, from `sim/core/pwm_dac.h` / `sim/core/st7789.h`).
- Produces: `namespace sim { class Machine }` with the exact same public interface as
  `sim/runtime/machine.h` (`get()`, `boot(int(*)())`, `run_until(uint64_t)`, `now_cycles()`,
  `now_us()`, `in_main()`, `main_sleep_until(uint64_t)`, `main_wfi()`, `set_irq_handler`,
  `set_irq_enabled`, `set_pwm_irq_enabled`, `set_audio_level`, `dac()`, `lcd()`) — every later
  task that touches `Machine` (Task 4) can be written identically to how `windowed.cpp` uses it
  natively.

`sim/runtime/machine.cpp`'s fiber calls are `ConvertThreadToFiber`, `CreateFiber`,
`SwitchToFiber`, and the `__stdcall fiber_entry(void*)` signature. Emscripten's
`emscripten/fiber.h` replaces them with `emscripten_fiber_init_from_current_context`,
`emscripten_fiber_init`, and `emscripten_fiber_swap`, backed by Asyncify. Read
`emscripten/fiber.h` from the installed SDK (`find ~/emsdk -name fiber.h`) before writing this
file — the exact struct/field names below are Emscripten's documented API as of the 3.x series;
confirm they match the installed version and adjust if the SDK has since changed the signature.

- [ ] **Step 1: Write `fiber_shim.h`** (copy of `sim/runtime/machine.h`, only the private section changes)

```cpp
#pragma once
#include <cstdint>
#include <emscripten/fiber.h>

#include "core/pwm_dac.h"
#include "core/st7789.h"

namespace sim {

constexpr uint64_t kCpuHz = 248000000ull;
constexpr uint64_t kCyclesPerUs = kCpuHz / 1000000ull;
constexpr uint64_t kPwmPeriodCycles = 251;
constexpr uint32_t kAudioRate = 48000;
constexpr uint64_t kTimeReadCycles = 32;

class Machine {
 public:
  static Machine& get();

  void boot(int (*firmware_main)());
  void run_until(uint64_t cycles);
  uint64_t now_cycles() const { return now_; }
  uint64_t now_us() const { return now_ / kCyclesPerUs; }

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
  static void fiber_entry(void* arg);

  static constexpr size_t kStackSize = 1u << 20;       // matches CreateFiber's 1 MB native stack
  static constexpr size_t kAsyncifyStackSize = 1u << 16;

  emscripten_fiber_t scheduler_fiber_{};
  emscripten_fiber_t main_fiber_{};
  char scheduler_asyncify_stack_[kAsyncifyStackSize]{};
  char main_c_stack_[kStackSize]{};
  char main_asyncify_stack_[kAsyncifyStackSize]{};

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

- [ ] **Step 2: Write `fiber_shim.cpp`**, keeping the scheduler logic byte-for-byte identical to
`sim/runtime/machine.cpp` (`boot`, `run_until`, `in_main`, `main_sleep_until`, `main_wfi`,
constructor) and swapping only the four fiber calls:

```cpp
#include "web/fiber_shim.h"

namespace sim {

Machine& Machine::get() {
  static Machine instance;
  return instance;
}

Machine::Machine() : dac_(kCpuHz, kPwmPeriodCycles, kAudioRate) {}

void Machine::fiber_entry(void* arg) {
  Machine* m = static_cast<Machine*>(arg);
  m->firmware_main_();
  // El firmware nunca vuelve; si algún día lo hace, no hay a dónde saltar.
  for (;;) emscripten_fiber_swap(&m->main_fiber_, &m->scheduler_fiber_);
}

void Machine::boot(int (*firmware_main)()) {
  firmware_main_ = firmware_main;
  emscripten_fiber_init_from_current_context(
      &scheduler_fiber_, scheduler_asyncify_stack_, sizeof(scheduler_asyncify_stack_));
  emscripten_fiber_init(&main_fiber_, &Machine::fiber_entry, this, main_c_stack_,
                        sizeof(main_c_stack_), main_asyncify_stack_,
                        sizeof(main_asyncify_stack_));
}

void Machine::run_until(uint64_t cycles) {
  while (now_ < cycles) {
    uint64_t next = cycles;
    if (irq_enabled_ && pwm_irq_enabled_) next = next_pwm_ < next ? next_pwm_ : next;
    if (main_wake_ > now_) next = main_wake_ < next ? main_wake_ : next;
    now_ = next;
    if (irq_enabled_ && pwm_irq_enabled_ && now_ >= next_pwm_) {
      dac_.tick(audio_level_);
      if (isr_ != nullptr) isr_();
      next_pwm_ += kPwmPeriodCycles;
    }
    if (main_wake_ != 0 && now_ >= main_wake_) {
      main_wake_ = 0;
      emscripten_fiber_swap(&scheduler_fiber_, &main_fiber_);
    }
  }
}

bool Machine::in_main() const { return main_wake_ == 0 && now_ > 0; }

void Machine::main_sleep_until(uint64_t cycles) {
  main_wake_ = cycles;
  emscripten_fiber_swap(&main_fiber_, &scheduler_fiber_);
}

void Machine::main_wfi() { main_sleep_until(now_ + kTimeReadCycles); }

}  // namespace sim
```

The `run_until` body above is a placeholder skeleton matching the documented scheduling rules in
`sim/runtime/machine.h`'s comments (ISR every `kPwmPeriodCycles`, main woken at `main_wake_`) —
**before writing it for real, open `sim/runtime/machine.cpp` side by side and copy its exact
`run_until`/`in_main`/`main_sleep_until`/`main_wfi` bodies verbatim**, only substituting
`SwitchToFiber(main_fiber_)` → `emscripten_fiber_swap(&scheduler_fiber_, &main_fiber_)` and
`SwitchToFiber(scheduler_fiber_)` → `emscripten_fiber_swap(&main_fiber_, &scheduler_fiber_)`
(mind the swap direction: `emscripten_fiber_swap(from, to)` takes the *currently running* fiber
first, opposite of `SwitchToFiber`'s implicit-current-fiber convention).

- [ ] **Step 3: Compile-check in isolation with a synthetic firmware**

```cpp
// sim/web/fiber_shim_smoke.cpp — deleted after this step passes, not committed
#include <cstdio>
#include "web/fiber_shim.h"

int counter = 0;
int synthetic_main() {
  for (int i = 0; i < 5; ++i) {
    ++counter;
    sim::Machine::get().main_sleep_until(sim::Machine::get().now_cycles() + 1000);
  }
  return 0;
}

int main() {
  sim::Machine& m = sim::Machine::get();
  m.boot(&synthetic_main);
  m.run_until(10000);
  std::printf("counter=%d (expect 5)\n", counter);
  return counter == 5 ? 0 : 1;
}
```

```bash
em++ -std=c++20 -O0 -g -sASYNCIFY -I sim \
  sim/web/fiber_shim.cpp sim/core/pwm_dac.cpp sim/core/st7789.cpp sim/web/fiber_shim_smoke.cpp \
  -o /tmp/fiber_smoke.js
node /tmp/fiber_smoke.js
```

Expected: `counter=5 (expect 5)`, exit code 0. If it hangs or asserts, the fiber swap direction
or stack sizing is wrong — re-check against `emscripten/fiber.h`'s doc comments before proceeding.

- [ ] **Step 4: Remove the smoke files, commit the shim**

```bash
rm sim/web/hello.cpp sim/web/fiber_shim_smoke.cpp
git add sim/web/fiber_shim.h sim/web/fiber_shim.cpp
git rm sim/web/hello.cpp
git commit -m "sim: port Machine's fiber scheduler to emscripten/fiber.h"
```

---

### Task 3: Web platform entry point (C++ exported API)

**Files:**
- Create: `sim/web/main.cpp`

**Interfaces:**
- Consumes: `sim::Machine` (Task 2), `sim::flash()` / `sim::FlashStore` (`sim/runtime/sim_io.h`,
  `sim/core/flash_store.h`), `sim::check_and_patch_bank` (`sim/core/bank_file.h`),
  `sim::write_bank_to_flash` (`sim/runtime/bank_hotload.h`), `sim::set_button_mask` /
  `sim::button_mask` (`sim/runtime/sim_io.h`), `sim::map_xinput` (`sim/core/buttons.h`),
  `sim::AudioRing` (`sim/core/audio_ring.h`), `piko_firmware_main` (`sim/runtime/firmware_entry.h`).
- Produces (exported to JS via `EXPORTED_FUNCTIONS`):
  - `int piko_init(const uint8_t* bank_ptr, int bank_len)` — returns `1` on a valid bank, `0` if
    `check_and_patch_bank` rejected it (boots either way; an empty/rejected bank just means no
    samples play).
  - `void piko_step(double budget_ms)` — advances the virtual clock by up to `budget_ms` of
    wall-clock-equivalent audio-paced emulation (reuses `sim::should_step`/`PaceState`).
  - `void piko_snapshot_lcd()` — copies the current 240×240 RGB565 framebuffer into a static
    buffer.
  - `const uint16_t* piko_lcd_ptr()` — pointer to that static buffer (call `piko_snapshot_lcd`
    first).
  - `void piko_set_buttons(uint16_t mask)` — `sim::Button` bitmask, same bit order as
    `sim/core/buttons.h`.
  - `uint16_t piko_map_xinput(uint16_t xinput_buttons)` — thin wrapper around
    `sim::map_xinput`, exported so `gamepad.ts` (Task 6) doesn't duplicate the button table.
  - `int piko_pull_audio(float* out, int max_frames)` — pops up to `max_frames` samples from the
    internal `AudioRing` into `out` (caller-owned WASM memory), returns frames written.
  - `float piko_speed()` — emulation speed as a multiple of real time (same meaning as the
    native status bar's `x%.2f`).

```cpp
// sim/web/main.cpp
#include <cstdint>
#include <vector>

#include <emscripten/emscripten.h>

#include "core/audio_ring.h"
#include "core/bank_file.h"
#include "core/pacing.h"
#include "runtime/bank_hotload.h"
#include "runtime/firmware_entry.h"
#include "runtime/sim_io.h"
#include "web/fiber_shim.h"

namespace {

sim::AudioRing g_ring(sim::kAudioRate / 2);  // 500 ms margin, same as windowed.cpp
uint64_t g_produced = 0;
uint16_t g_lcd_snapshot[sim::St7789::kSize * sim::St7789::kSize];
bool g_booted = false;

}  // namespace

extern "C" {

EMSCRIPTEN_KEEPALIVE
int piko_init(const uint8_t* bank_ptr, int bank_len) {
  std::string err;
  sim::flash().open("", &err);  // memory-only, no persisted flash for the web demo

  std::vector<uint8_t> blob(bank_ptr, bank_ptr + bank_len);
  const sim::BankCheck check = sim::check_and_patch_bank(blob);
  if (check.ok) sim::write_bank_to_flash(blob);  // before boot: piko_audio_bank_init() reads it

  sim::Machine& m = sim::Machine::get();
  m.dac().set_sink([](float s) {
    g_ring.push(s);
    ++g_produced;
  });
  m.boot(&piko_firmware_main);
  g_booted = true;
  return check.ok ? 1 : 0;
}

EMSCRIPTEN_KEEPALIVE
void piko_step(double budget_ms) {
  if (!g_booted) return;
  sim::Machine& m = sim::Machine::get();
  constexpr uint64_t kLeadFrames = sim::kAudioRate * 20 / 1000;  // ~20 ms lead, same as native
  sim::PaceState pace;
  pace.audio_running = true;
  pace.ring_fill = g_ring.size();
  pace.produced = g_produced;
  double spent_ms = 0.0;
  // 1 ms of virtual CPU time per should_step() == true, matching windowed.cpp's granularity.
  while (spent_ms < budget_ms && sim::should_step(pace, kLeadFrames)) {
    m.run_until(m.now_cycles() + sim::kCpuHz / 1000);
    spent_ms += 1.0;
    pace.ring_fill = g_ring.size();
    pace.produced = g_produced;
  }
}

EMSCRIPTEN_KEEPALIVE
void piko_snapshot_lcd() {
  if (g_booted) sim::Machine::get().lcd().snapshot_view(g_lcd_snapshot);
}

EMSCRIPTEN_KEEPALIVE
const uint16_t* piko_lcd_ptr() { return g_lcd_snapshot; }

EMSCRIPTEN_KEEPALIVE
void piko_set_buttons(uint16_t mask) { sim::set_button_mask(mask); }

EMSCRIPTEN_KEEPALIVE
uint16_t piko_map_xinput(uint16_t xinput_buttons) { return sim::map_xinput(xinput_buttons); }

EMSCRIPTEN_KEEPALIVE
int piko_pull_audio(float* out, int max_frames) {
  return static_cast<int>(g_ring.pop(out, static_cast<size_t>(max_frames)));
}

EMSCRIPTEN_KEEPALIVE
float piko_speed() {
  if (!g_booted) return 0.0f;
  return static_cast<float>(sim::Machine::get().now_cycles()) / sim::kCpuHz;
}

}  // extern "C"
```

`piko_speed()` here returns elapsed virtual seconds, not instantaneous speed (the native version
tracks a 0.5 s rolling window — out of scope for a demo status line; `SimDemo.tsx` in Task 7 can
derive a simple ratio from wall-clock deltas between calls if it wants one, without needing new
C++).

- [ ] **Step 1: Write `sim/web/main.cpp` as above.**

- [ ] **Step 2: Compile it standalone against the portable libraries (no firmware yet — link
error on `piko_firmware_main` is expected and checked for) to catch header/signature mistakes early**

```bash
em++ -std=c++20 -O0 -sASYNCIFY -I sim -I . -DPIKO_SIM=1 \
  -c sim/web/main.cpp -o /tmp/main.o
```

Expected: compiles with no errors (a `.o` file with an unresolved `piko_firmware_main` symbol is
fine at this stage — Task 4 links the real firmware in).

- [ ] **Step 3: Commit**

```bash
git add sim/web/main.cpp
git commit -m "sim: web platform entry point exporting init/step/lcd/audio/button API"
```

---

### Task 4: Full build script — link the real firmware

**Files:**
- Modify: `sim/web/build.sh` (replace the Task 1 smoke-test invocation entirely)
- Modify: `web/package.json` (add `build:sim-wasm` script)

**Interfaces:**
- Consumes: every file from Tasks 2–3, plus `piko_fw`'s sources (same list as
  `sim/CMakeLists.txt`'s `add_library(piko_fw ...)`) and `sim_core`'s sources (same list as
  `add_library(sim_core ...)`, **excluding** `core/file_io.cpp` and `core/cli_checks.cpp` — both
  are native-CLI-only and `file_io.cpp` calls `_wfopen`, which doesn't exist under emcc).
- Produces: `web/public/sim/pikocore_sim.js` + `.wasm`, loadable as an ES module — the artifact
  Task 6 (`simModule.ts`) imports.

- [ ] **Step 1: Flatten `doth/easing.h`** — the same MSVC-nesting-depth workaround
`sim/cmake/flatten_easing.cmake` applies is worth reusing here too, since Clang's default
`-fbracket-depth` (256) can also choke on hundreds of chained `else if`. Add this to the top of
`build.sh`:

```bash
GEN_DIR="$(mktemp -d)"
mkdir -p "$GEN_DIR/doth"
python3 - "$PIKO_ROOT/doth/easing.h" "$GEN_DIR/doth/easing.h" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
content = open(src, encoding="utf-8").read()
content = content.replace("} else if (", "}\n  if (")
assert "else" not in content, f"{src} has a bare 'else': flattening is unsafe"
open(dst, "w", encoding="utf-8").write(content)
PY
```

- [ ] **Step 2: Write the full `sim/web/build.sh`**

```bash
#!/usr/bin/env bash
# sim/web/build.sh
set -euo pipefail
cd "$(dirname "$0")"
SIM_ROOT="$(pwd)"
PIKO_ROOT="$SIM_ROOT/.."
OUT_DIR="$PIKO_ROOT/web/public/sim"
mkdir -p "$OUT_DIR"

GEN_DIR="$(mktemp -d)"
mkdir -p "$GEN_DIR/doth"
python3 - "$PIKO_ROOT/doth/easing.h" "$GEN_DIR/doth/easing.h" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
content = open(src, encoding="utf-8").read()
content = content.replace("} else if (", "}\n  if (")
assert "else" not in content, f"{src} has a bare 'else': flattening is unsafe"
open(dst, "w", encoding="utf-8").write(content)
PY

FW_SOURCES=(
  "$PIKO_ROOT/src/main.cpp"
  "$PIKO_ROOT/src/PikoAudioBank.cpp"
  "$PIKO_ROOT/src/gamepi13/ui.cpp"
  "$PIKO_ROOT/src/gamepi13/dev_shim.c"
  "$PIKO_ROOT/src/gamepi13/lcd/LCD_1in3.c"
  "$PIKO_ROOT/src/gamepi13/lcd/GUI_Paint.c"
  "$PIKO_ROOT/src/gamepi13/lcd/font12.c"
  "$PIKO_ROOT/src/gamepi13/lcd/font16.c"
  "$PIKO_ROOT/src/gamepi13/lcd/font20.c"
  "$PIKO_ROOT/src/gamepi13/lcd/font24.c"
)
CORE_SOURCES=(
  "$SIM_ROOT/core/st7789.cpp"
  "$SIM_ROOT/core/pwm_dac.cpp"
  "$SIM_ROOT/core/flash_store.cpp"
  "$SIM_ROOT/core/bank_file.cpp"
  "$SIM_ROOT/core/buttons.cpp"
  "$SIM_ROOT/core/press_script.cpp"
  "$SIM_ROOT/core/pacing.cpp"
)
RUNTIME_SOURCES=(
  "$SIM_ROOT/web/fiber_shim.cpp"
  "$SIM_ROOT/runtime/sim_hal.cpp"
  "$SIM_ROOT/runtime/firmware_glue.cpp"
  "$SIM_ROOT/runtime/bank_hotload.cpp"
  "$SIM_ROOT/web/main.cpp"
)

FW_DEFINES=(
  -DPIKO_GAMEPI13=1 -DPIKO_GAMEPI13_SD=0 -DPIKO_SIM=1 -DPIKO_FIRMWARE_RESERVE=524288u
  -DWS2812_ENABLED=1 -DMIDI_IN_ENABLED=0 -DMIDI_RESET_EVERY_BEAT=16 -DMIDI_CLOCK_MULTIPLIER=2
  -DMIDI_NOTE_KEY=0 -DPCB_V2_LAYOUT=0
)
INCLUDES=(
  -I "$SIM_ROOT/shim" -I "$GEN_DIR" -I "$PIKO_ROOT" -I "$PIKO_ROOT/src"
  -I "$PIKO_ROOT/src/gamepi13" -I "$PIKO_ROOT/src/gamepi13/lcd" -I "$SIM_ROOT"
)

em++ -std=c++20 -O2 -sASYNCIFY -sASYNCIFY_STACK_SIZE=131072 \
  "${INCLUDES[@]}" "${FW_DEFINES[@]}" \
  -Dmain=piko_firmware_main "${FW_SOURCES[0]}" \
  "${FW_SOURCES[@]:1}" "${CORE_SOURCES[@]}" "${RUNTIME_SOURCES[@]}" \
  -sMODULARIZE=1 -sEXPORT_ES6=1 -sEXPORT_NAME=createPikoSimModule \
  -sEXPORTED_FUNCTIONS=_piko_init,_piko_step,_piko_snapshot_lcd,_piko_lcd_ptr,_piko_set_buttons,_piko_map_xinput,_piko_pull_audio,_piko_speed,_malloc,_free \
  -sEXPORTED_RUNTIME_METHODS=ccall,cwrap,HEAPU8,HEAPU16,HEAPF32 \
  -sALLOW_MEMORY_GROWTH=1 \
  -o "$OUT_DIR/pikocore_sim.js"

cp "$PIKO_ROOT/build-sim/bin/amen_pad_bank.pikobank" "$OUT_DIR/amen_pad_bank.pikobank"
echo "Built $OUT_DIR/pikocore_sim.js + amen_pad_bank.pikobank"
```

`-Dmain=piko_firmware_main` on the compile line (rather than scoped to just `main.cpp` via a
per-file property, the way CMake does it) works here because every other source file in the
build has no function named `main`, so the blanket define is safe — double check that stays true
if a future `piko_fw` source is added.

- [ ] **Step 3: Add the npm script**

Modify `web/package.json`'s `"scripts"` block:

```json
    "build:sim-wasm": "bash ../sim/web/build.sh",
```

- [ ] **Step 4: Build and smoke-test from Node**

```bash
chmod +x sim/web/build.sh
cd web && npm run build:sim-wasm && cd ..
node -e "
import('./web/public/sim/pikocore_sim.js').then(async ({ default: createModule }) => {
  const fs = await import('node:fs');
  const mod = await createModule();
  const bank = fs.readFileSync('./web/public/sim/amen_pad_bank.pikobank');
  const bankPtr = mod._malloc(bank.length);
  mod.HEAPU8.set(bank, bankPtr);
  const ok = mod.ccall('piko_init', 'number', ['number', 'number'], [bankPtr, bank.length]);
  console.log('piko_init ok =', ok);
  mod.ccall('piko_step', null, ['number'], [50]);
  mod.ccall('piko_snapshot_lcd', null, [], []);
  const lcdPtr = mod.ccall('piko_lcd_ptr', 'number', [], []);
  const pixel0 = mod.HEAPU16[lcdPtr / 2];
  console.log('speed =', mod.ccall('piko_speed', 'number', [], []), 'pixel0 =', pixel0.toString(16));
});
"
```

Expected: `piko_init ok = 1`, `speed` is a small positive number (the emulation ran ~50 virtual
ms), `pixel0` prints a hex value (proves the LCD framebuffer has non-garbage, initialized data —
the firmware's splash/boot screen has drawn something by 50 ms in).

- [ ] **Step 5: Commit**

```bash
git add sim/web/build.sh web/package.json web/public/sim/.gitignore
git commit -m "build: link the real firmware into the web sim WASM build"
```

Add a `web/public/sim/.gitignore` ignoring `pikocore_sim.js`/`pikocore_sim.wasm` (build output,
regenerated by `npm run build:sim-wasm`) but not `amen_pad_bank.pikobank` (checked-in fixture,
copied by the script but small enough to also commit directly so `npm install && npm run dev`
works without a working Emscripten install):

```
pikocore_sim.js
pikocore_sim.wasm
```

Also copy the bank file into git directly so the dev server works without Emscripten installed:

```bash
cp build-sim/bin/amen_pad_bank.pikobank web/public/sim/amen_pad_bank.pikobank
git add web/public/sim/amen_pad_bank.pikobank
git commit -m "assets: bundle the fixed demo bank for the web sim"
```

---

### Task 5: AudioWorklet processor

**Files:**
- Create: `web/public/sim/sim-audio-worklet.js`

**Interfaces:**
- Consumes: a `SharedArrayBuffer`-free message-passing handshake from `simModule.ts` (Task 6) —
  the worklet cannot call into the WASM module directly (it runs on the audio thread, in a
  separate JS realm), so `simModule.ts` pumps audio samples to it via `port.postMessage`.
- Produces: `class SimAudioProcessor extends AudioWorkletProcessor`, registered as
  `"sim-audio-processor"`.

```js
// web/public/sim/sim-audio-worklet.js
class SimAudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.queue = [];
    this.port.onmessage = (event) => {
      // event.data is a Float32Array of PCM samples at sampleRate (48000, matches
      // sim::kAudioRate; the AudioContext must be created with { sampleRate: 48000 }).
      this.queue.push(event.data);
    };
  }

  process(_inputs, outputs) {
    const output = outputs[0][0];
    let i = 0;
    while (i < output.length) {
      if (this.queue.length === 0) {
        output.fill(0, i);  // underrun: silence, same fallback the native WASAPI path has
        break;
      }
      const chunk = this.queue[0];
      const take = Math.min(chunk.length, output.length - i);
      output.set(chunk.subarray(0, take), i);
      i += take;
      if (take === chunk.length) {
        this.queue.shift();
      } else {
        this.queue[0] = chunk.subarray(take);
      }
    }
    return true;
  }
}

registerProcessor('sim-audio-processor', SimAudioProcessor);
```

- [ ] **Step 1: Write the file above.**

- [ ] **Step 2: Verify it loads without a syntax error**

```bash
node --check web/public/sim/sim-audio-worklet.js
```

Expected: no output, exit code 0 (Task 7's browser test is what actually exercises audio output
— `AudioWorkletProcessor` doesn't exist outside a real `AudioContext`, so this step only checks
syntax).

- [ ] **Step 3: Commit**

```bash
git add web/public/sim/sim-audio-worklet.js
git commit -m "sim: AudioWorklet processor for the web sim demo"
```

---

### Task 6: TypeScript glue — module loader, keyboard, gamepad

**Files:**
- Create: `web/src/sim/simModule.ts`
- Create: `web/src/sim/keyboard.ts`
- Create: `web/src/sim/gamepad.ts`
- Test: `web/src/sim/keyboard.test.ts`

**Interfaces:**
- Consumes: `web/public/sim/pikocore_sim.js` (Task 4's build output, an ES module default
  exporting `createPikoSimModule(): Promise<PikoSimModule>`), `web/public/sim/amen_pad_bank.pikobank`.
- Produces:
  - `keyToButtonBit(code: string): number | null` (Task 7 wires this to `keydown`/`keyup`).
  - `BUTTON_BITS` — the `sim::Button` enum's bit values, named, for reuse by `gamepad.ts` and
    `SimDemo.tsx`'s legend.
  - `pollGamepadMask(pad: Gamepad, piko: PikoSim): number` (Task 7 calls this once per rAF).
  - `class PikoSim` with `static async create(): Promise<PikoSim>`, `step(budgetMs: number): void`,
    `getLcdFrame(): Uint16Array` (a *view*, valid only until the next `step()`),
    `setButtons(mask: number): void`, `mapXinput(xinputButtons: number): number`,
    `pullAudio(maxFrames: number): Float32Array`, `speed(): number`.

```typescript
// web/src/sim/keyboard.ts

// Mirrors sim/core/buttons.h's Button enum order exactly — a bit index here must match that
// enum's declaration order, since piko_set_buttons() interprets the mask with the same bits.
export const BUTTON_BITS = {
  UP: 1 << 0,
  DOWN: 1 << 1,
  LEFT: 1 << 2,
  RIGHT: 1 << 3,
  Y: 1 << 4,
  X: 1 << 5,
  B: 1 << 6,
  A: 1 << 7,
  SELECT: 1 << 8,
  START: 1 << 9,
  L: 1 << 10,
  R: 1 << 11,
} as const;

// Same mapping as sim/README.md's table (face buttons by position, not letter).
const KEY_MAP: Record<string, number> = {
  ArrowUp: BUTTON_BITS.UP,
  ArrowDown: BUTTON_BITS.DOWN,
  ArrowLeft: BUTTON_BITS.LEFT,
  ArrowRight: BUTTON_BITS.RIGHT,
  KeyW: BUTTON_BITS.X,
  KeyD: BUTTON_BITS.A,
  KeyS: BUTTON_BITS.B,
  KeyA: BUTTON_BITS.Y,
  KeyQ: BUTTON_BITS.L,
  KeyE: BUTTON_BITS.R,
  Backspace: BUTTON_BITS.SELECT,
  Enter: BUTTON_BITS.START,
};

export function keyToButtonBit(code: string): number | null {
  return KEY_MAP[code] ?? null;
}
```

```typescript
// web/src/sim/gamepad.ts
import type { PikoSim } from './simModule';

// XINPUT_GAMEPAD_* bit values from sim/core/buttons.cpp's kXMap — piko_map_xinput() expects a
// mask built from these, not from sim::Button bits.
const X_DPAD_UP = 0x0001;
const X_DPAD_DOWN = 0x0002;
const X_DPAD_LEFT = 0x0004;
const X_DPAD_RIGHT = 0x0008;
const X_START = 0x0010;
const X_BACK = 0x0020;
const X_LEFT_SHOULDER = 0x0100;
const X_RIGHT_SHOULDER = 0x0200;
const X_A = 0x1000;
const X_B = 0x2000;
const X_X = 0x4000;
const X_Y = 0x8000;

// Standard Gamepad API button indices (https://www.w3.org/TR/gamepad/#remapping) line up with
// an Xbox-style pad's physical layout, same as XInput's wButtons.
const GAMEPAD_INDEX_TO_XINPUT: Array<[number, number]> = [
  [0, X_A],
  [1, X_B],
  [2, X_X],
  [3, X_Y],
  [4, X_LEFT_SHOULDER],
  [5, X_RIGHT_SHOULDER],
  [8, X_BACK],
  [9, X_START],
  [12, X_DPAD_UP],
  [13, X_DPAD_DOWN],
  [14, X_DPAD_LEFT],
  [15, X_DPAD_RIGHT],
];

export function pollGamepadMask(pad: Gamepad, piko: PikoSim): number {
  let xinputMask = 0;
  for (const [index, bit] of GAMEPAD_INDEX_TO_XINPUT) {
    const button = pad.buttons[index];
    if (button && button.pressed) xinputMask |= bit;
  }
  return piko.mapXinput(xinputMask);
}
```

```typescript
// web/src/sim/simModule.ts
export interface PikoSimModule {
  ccall: (name: string, ret: string | null, argTypes: string[], args: unknown[]) => unknown;
  _malloc: (size: number) => number;
  _free: (ptr: number) => void;
  HEAPU8: Uint8Array;
  HEAPU16: Uint16Array;
  HEAPF32: Float32Array;
}

const LCD_SIZE = 240;
const LCD_PIXELS = LCD_SIZE * LCD_SIZE;
const AUDIO_SCRATCH_FRAMES = 4096;

export class PikoSim {
  private constructor(
    private readonly mod: PikoSimModule,
    private readonly audioScratchPtr: number,
  ) {}

  static async create(): Promise<PikoSim> {
    const { default: createPikoSimModule } = await import(
      /* @vite-ignore */ `${import.meta.env.BASE_URL}sim/pikocore_sim.js`
    );
    const mod = (await createPikoSimModule()) as PikoSimModule;
    const bankResponse = await fetch(`${import.meta.env.BASE_URL}sim/amen_pad_bank.pikobank`);
    const bankBytes = new Uint8Array(await bankResponse.arrayBuffer());
    const bankPtr = mod._malloc(bankBytes.length);
    mod.HEAPU8.set(bankBytes, bankPtr);
    const ok = mod.ccall('piko_init', 'number', ['number', 'number'], [bankPtr, bankBytes.length]);
    mod._free(bankPtr);
    if (!ok) throw new Error('Bundled demo bank was rejected by the firmware');
    const audioScratchPtr = mod._malloc(AUDIO_SCRATCH_FRAMES * 4);
    return new PikoSim(mod, audioScratchPtr);
  }

  step(budgetMs: number): void {
    this.mod.ccall('piko_step', null, ['number'], [budgetMs]);
  }

  getLcdFrame(): Uint16Array {
    this.mod.ccall('piko_snapshot_lcd', null, [], []);
    const ptr = this.mod.ccall('piko_lcd_ptr', 'number', [], []) as number;
    return this.mod.HEAPU16.subarray(ptr / 2, ptr / 2 + LCD_PIXELS);
  }

  setButtons(mask: number): void {
    this.mod.ccall('piko_set_buttons', null, ['number'], [mask]);
  }

  mapXinput(xinputButtons: number): number {
    return this.mod.ccall('piko_map_xinput', 'number', ['number'], [xinputButtons]) as number;
  }

  pullAudio(maxFrames: number): Float32Array {
    const frames = Math.min(maxFrames, AUDIO_SCRATCH_FRAMES);
    const written = this.mod.ccall(
      'piko_pull_audio',
      'number',
      ['number', 'number'],
      [this.audioScratchPtr, frames],
    ) as number;
    return this.mod.HEAPF32.slice(this.audioScratchPtr / 4, this.audioScratchPtr / 4 + written);
  }

  speed(): number {
    return this.mod.ccall('piko_speed', 'number', [], []) as number;
  }
}
```

- [ ] **Step 1: Write `keyboard.ts` as above.**

- [ ] **Step 2: Write the test**

```typescript
// web/src/sim/keyboard.test.ts
import { describe, expect, it } from 'vitest';
import { BUTTON_BITS, keyToButtonBit } from './keyboard';

describe('keyToButtonBit', () => {
  it('maps arrow keys to D-pad bits', () => {
    expect(keyToButtonBit('ArrowUp')).toBe(BUTTON_BITS.UP);
    expect(keyToButtonBit('ArrowLeft')).toBe(BUTTON_BITS.LEFT);
  });

  it('maps face buttons by position, not letter (W is the top face button)', () => {
    expect(keyToButtonBit('KeyW')).toBe(BUTTON_BITS.X);
  });

  it('returns null for unmapped keys', () => {
    expect(keyToButtonBit('KeyZ')).toBeNull();
  });
});
```

- [ ] **Step 3: Run the test**

```bash
cd web && npx vitest run src/sim/keyboard.test.ts
```

Expected: 3 passing tests.

- [ ] **Step 4: Write `gamepad.ts` and `simModule.ts` as above (no unit test — both need a real
WASM module / Gamepad object to exercise meaningfully; Task 7's manual browser pass covers them).**

- [ ] **Step 5: Typecheck**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/sim/simModule.ts web/src/sim/keyboard.ts web/src/sim/keyboard.test.ts web/src/sim/gamepad.ts
git commit -m "web: TS glue for the sim demo (module loader, keyboard, gamepad mapping)"
```

---

### Task 7: React component + App integration

**Files:**
- Create: `web/src/sim/SimDemo.tsx`
- Modify: `web/src/App.tsx`
- Modify: `web/src/styles.css`

**Interfaces:**
- Consumes: `PikoSim` (Task 6), `keyToButtonBit`/`BUTTON_BITS` (Task 6), `pollGamepadMask`
  (Task 6).
- Produces: `export function SimDemo(): JSX.Element`, mounted from `App.tsx`.

```tsx
// web/src/sim/SimDemo.tsx
import { useEffect, useRef, useState } from 'react';
import { keyToButtonBit } from './keyboard';
import { pollGamepadMask } from './gamepad';
import { PikoSim } from './simModule';

const LCD_SIZE = 240;

export function SimDemo() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const simRef = useRef<PikoSim | null>(null);
  const keyMaskRef = useRef(0);
  const gamepadIndexRef = useRef<number | null>(null);
  const rafRef = useRef(0);
  const [status, setStatus] = useState('Loading simulator...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let audioContext: AudioContext | null = null;
    let workletNode: AudioWorkletNode | null = null;

    async function boot() {
      try {
        const sim = await PikoSim.create();
        if (cancelled) return;
        simRef.current = sim;

        audioContext = new AudioContext({ sampleRate: 48000 });
        await audioContext.audioWorklet.addModule(`${import.meta.env.BASE_URL}sim/sim-audio-worklet.js`);
        if (cancelled) return;
        workletNode = new AudioWorkletNode(audioContext, 'sim-audio-processor');
        workletNode.connect(audioContext.destination);

        const onKeyDown = (event: KeyboardEvent) => {
          const bit = keyToButtonBit(event.code);
          if (bit != null) {
            keyMaskRef.current |= bit;
            event.preventDefault();
          }
        };
        const onKeyUp = (event: KeyboardEvent) => {
          const bit = keyToButtonBit(event.code);
          if (bit != null) {
            keyMaskRef.current &= ~bit;
            event.preventDefault();
          }
        };
        const canvas = canvasRef.current;
        canvas?.setAttribute('tabindex', '0');
        canvas?.addEventListener('keydown', onKeyDown);
        canvas?.addEventListener('keyup', onKeyUp);

        const onGamepadConnected = (event: GamepadEvent) => {
          gamepadIndexRef.current = event.gamepad.index;
        };
        const onGamepadDisconnected = (event: GamepadEvent) => {
          if (gamepadIndexRef.current === event.gamepad.index) gamepadIndexRef.current = null;
        };
        window.addEventListener('gamepadconnected', onGamepadConnected);
        window.addEventListener('gamepaddisconnected', onGamepadDisconnected);

        setStatus('Ready');

        let lastFrameTime = performance.now();
        const tick = () => {
          const now = performance.now();
          const budgetMs = Math.min(50, now - lastFrameTime);
          lastFrameTime = now;

          let mask = keyMaskRef.current;
          const gamepadIndex = gamepadIndexRef.current;
          if (gamepadIndex != null) {
            const pad = navigator.getGamepads()[gamepadIndex];
            if (pad) mask |= pollGamepadMask(pad, sim);
          }
          sim.setButtons(mask);
          sim.step(budgetMs);

          const frame = sim.getLcdFrame();
          const canvas = canvasRef.current;
          const ctx = canvas?.getContext('2d');
          if (ctx) {
            const imageData = ctx.getImageData(0, 0, LCD_SIZE, LCD_SIZE);
            for (let i = 0; i < frame.length; i++) {
              const px = frame[i];
              const r = ((px >> 11) & 0x1f) * 255 / 31;
              const g = ((px >> 5) & 0x3f) * 255 / 63;
              const b = (px & 0x1f) * 255 / 31;
              imageData.data[i * 4] = r;
              imageData.data[i * 4 + 1] = g;
              imageData.data[i * 4 + 2] = b;
              imageData.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(imageData, 0, 0);
          }

          const audio = sim.pullAudio(4096);
          if (audio.length > 0 && workletNode) workletNode.port.postMessage(audio);

          rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);

        return () => {
          canvas?.removeEventListener('keydown', onKeyDown);
          canvas?.removeEventListener('keyup', onKeyUp);
          window.removeEventListener('gamepadconnected', onGamepadConnected);
          window.removeEventListener('gamepaddisconnected', onGamepadDisconnected);
        };
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    }

    const cleanupPromise = boot();

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafRef.current);
      void cleanupPromise.then((cleanup) => cleanup?.());
      workletNode?.disconnect();
      void audioContext?.close();
    };
  }, []);

  return (
    <div className="sim-demo">
      {error ? (
        <div className="sim-demo-error">Simulator failed to load: {error}</div>
      ) : (
        <>
          <canvas ref={canvasRef} width={LCD_SIZE} height={LCD_SIZE} className="sim-demo-canvas" />
          <div className="sim-demo-status">{status}</div>
          <div className="sim-demo-legend">
            <span>Arrows / WASD: D-pad + face buttons</span>
            <span>Q / E: L / R</span>
            <span>Backspace / Enter: Select / Start</span>
            <span>Xbox-compatible gamepad also works</span>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 1: Write `SimDemo.tsx` as above.**

- [ ] **Step 2: Add a collapsible section to `App.tsx`.** Add state near the other `useState`
calls (around `web/src/App.tsx:92`, next to `controlsInfoOpen`):

```tsx
  const [simDemoOpen, setSimDemoOpen] = useState(false);
```

Add the import at the top of the file:

```tsx
import { SimDemo } from './sim/SimDemo';
```

Add a toggle button next to the existing `Gamepad2` controls-info button (around
`web/src/App.tsx:879-886`, right after the `controlsInfoOpen` button):

```tsx
          <button
            className="icon-button"
            onClick={() => setSimDemoOpen((open) => !open)}
            title={simDemoOpen ? 'Hide the in-browser simulator' : 'Try pikocore in your browser'}
            aria-label={simDemoOpen ? 'Hide the in-browser simulator' : 'Try pikocore in your browser'}
            aria-pressed={simDemoOpen}
          >
            <Monitor size={18} />
          </button>
```

Add `Monitor` to the `lucide-react` import list at the top of the file (alongside the existing
`Gamepad2`, `HelpCircle`, etc.).

Add the section itself, right after the `debug-log` section (around `web/src/App.tsx:1056`,
before the `sample-list` section):

```tsx
      {simDemoOpen ? (
        <section className="sim-demo-section">
          <div className="sim-demo-title">Try it in your browser</div>
          <SimDemo />
        </section>
      ) : null}
```

- [ ] **Step 3: Add minimal styling to `web/src/styles.css`** (match the existing section/canvas
conventions already used for `.debug-log`/`.waveform` — read those rules first and follow the
same spacing/border variables):

```css
.sim-demo-section {
  border: 1px solid var(--border, #333);
  border-radius: 8px;
  padding: 12px;
  margin: 12px 0;
}

.sim-demo-title {
  font-weight: 600;
  margin-bottom: 8px;
}

.sim-demo {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.sim-demo-canvas {
  image-rendering: pixelated;
  width: 240px;
  height: 240px;
  outline: none;
  background: #000;
}

.sim-demo-legend {
  display: flex;
  flex-direction: column;
  font-size: 0.85em;
  opacity: 0.8;
}

.sim-demo-error {
  color: var(--danger, #c33);
}
```

(`var(--border, ...)`/`var(--danger, ...)` fall back to hardcoded colors if `styles.css` doesn't
already define those custom properties — check the top of the file for the actual variable names
in use and swap these to match rather than introducing new ones.)

- [ ] **Step 4: Typecheck and build**

```bash
cd web && npx tsc --noEmit && npm run build
```

Expected: no type errors, Vite build succeeds.

- [ ] **Step 5: Commit**

```bash
git add web/src/sim/SimDemo.tsx web/src/App.tsx web/src/styles.css
git commit -m "web: embed the in-browser pikocore simulator demo in the loader"
```

---

### Task 8: Manual browser verification

**Files:** none (verification only — no code changes expected unless this step surfaces a bug,
in which case fix it in the relevant task's file and re-run this checklist).

- [ ] **Step 1: Build everything and start the dev server**

```bash
cd web
npm run build:sim-wasm
npm run dev
```

- [ ] **Step 2: Open the loader in a browser, click the "Try pikocore in your browser" button
(the `Monitor` icon added in Task 7), and confirm:**
  - The status line goes from "Loading simulator..." to "Ready" within a few seconds.
  - The canvas shows the pikocore boot splash, then the running UI (not a blank/black square).
  - Clicking the canvas and pressing arrow keys / W-A-S-D / Q-E / Enter / Backspace changes what's
    on screen, matching the legend and `sim/README.md`'s button table.
  - Audio is audible and changes as buttons are pressed (the amen_pad_bank samples playing).
  - If an Xbox-compatible gamepad is connected and a button is pressed on it once (Gamepad API
    requires a user gesture before `navigator.getGamepads()` reports it), gamepad input also
    moves the UI.
  - Closing the section (clicking the `Monitor` icon again) stops audio and the canvas stops
    updating — no console errors about a dangling `AudioContext` or a runaway `requestAnimationFrame`
    loop (check the browser console).
  - Reopening the section boots a fresh instance correctly (no stale state from the previous
    session causing a crash).

- [ ] **Step 3: Run the full existing test suites to confirm nothing else broke**

```bash
cd web && npm test
```

Expected: all existing tests plus `keyboard.test.ts` (Task 6) pass.

- [ ] **Step 4: If everything above checks out, this plan is complete — no commit needed for this
task unless Step 2 surfaced a fix.**

---

## Self-Review Notes

- **Spec coverage:** architecture/build (Tasks 1, 4), fiber→Asyncify (Task 2), LCD/audio/input/bank
  data flow (Tasks 3, 5, 6), UI integration + scope boundaries (Task 7), manual verification
  (Task 8) — every spec section maps to at least one task.
- **Type/name consistency checked:** `PikoSim` methods (`step`, `getLcdFrame`, `setButtons`,
  `mapXinput`, `pullAudio`, `speed`) match the exported C symbols 1:1 across Tasks 3, 6, 7;
  `BUTTON_BITS` bit values in `keyboard.ts` match `sim/core/buttons.h`'s `Button` enum declaration
  order; `gamepad.ts`'s XInput constants match `sim/core/buttons.cpp`'s `kXMap` values verbatim.
- **Known risk flagged explicitly, not hidden:** Task 2's exact `emscripten_fiber_*` call
  signatures depend on the installed Emscripten SDK version — Step 2 tells the implementer to
  verify against the real header before trusting the code block, rather than presenting it as
  guaranteed-correct.
