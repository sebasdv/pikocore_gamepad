# Web simulator demo — design

## Goal

Embed a lightweight, real-firmware demo of pikocore into the web loader
(`web/`), so a visitor can try the device in the browser without installing
or downloading anything. This sidesteps the Windows Defender/SmartScreen
false-positive issue on the native `pikocore_sim.exe` by giving people a
zero-install way to try the device — it does not replace the native
simulator, which stays the tool for real firmware testing (headless mode,
CLI scripting, `.pikobank` iteration).

Non-goals: full feature parity with the native simulator (no headless mode,
no CLI flags, no bank upload/drag-drop, no persisted flash state, no mobile
touch controls, no automated browser test suite).

## Architecture

The same firmware sources (`src/main.cpp`, `src/gamepi13/ui.cpp`,
`PikoAudioBank.cpp`, the LCD driver) that the native simulator compiles
against a pico-sdk shim get compiled again, this time with Emscripten, and
paired with a new web platform layer instead of `sim/platform/*.cpp`
(which is Win32-only: XInput, WASAPI, a Win32 window).

```
sim/web/                      new platform layer for the WASM target
  main.cpp                    entry point: exported functions for JS
  fiber_shim.cpp/h             Machine's scheduler, ported to emscripten/fiber.h
  build.sh                    emcc/em++ build script (separate from the MSVC CMake build)
web/public/sim/                compiled artifacts: pikocore_sim.wasm/.js, amen_pad_bank.pikobank
web/src/sim/                   TS glue: module loader, AudioWorklet, input mapping, React component
```

### Fiber scheduler → Asyncify

`sim/runtime/machine.cpp` drives the firmware's `main()` on a Win32 Fiber
(`CreateFiber`/`SwitchToFiber`/`ConvertThreadToFiber`), so it can suspend at
`__wfi()`, `sleep_*()`, and every timer read, while the deterministic
virtual-clock scheduler advances around it. The rest of `Machine` (the
248 MHz virtual clock, `run_until()`, the PWM ISR) is portable C++ and does
not change.

Emscripten's `emscripten/fiber.h` (`emscripten_fiber_init`,
`emscripten_fiber_swap`), built on Asyncify, is the direct replacement for
this exact pattern — it exists specifically for porting native fiber-based
control flow to WASM. Only the fiber primitives in `machine.cpp` are
swapped; `Machine`'s public interface (`boot`, `run_until`, `now_cycles`,
`dac()`, `lcd()`) is unchanged.

### Threading model

No pthreads, no SharedArrayBuffer, no COOP/COEP headers. Everything runs on
the browser main thread except audio, which runs on its own thread inside
an `AudioWorklet` (a browser primitive, not something we manage). This
keeps the demo deployable on any static host, including wherever `web/`
already gets served.

### Build

A standalone script (`sim/web/build.sh`, invoked via
`npm run build:sim-wasm` from `web/`) compiles `piko_fw` + `sim_core` +
`sim/runtime/*` (with the fiber-shimmed `machine.cpp`) + `sim/web/*.cpp`
into `web/public/sim/`. This is separate from `sim/CMakeLists.txt`, which
stays MSVC-only for the native simulator — the two build systems don't
interact.

## Data flow

### Simulation loop

JS drives the simulation from `requestAnimationFrame` (~16 ms), calling an
exported `piko_step(target_wall_ms)`. That function reuses the existing
portable pacing logic (`sim::should_step` / `PaceState` in
`sim/core/pacing.cpp`) to decide how many `run_until()` calls to make —
same ~20 ms look-ahead the native simulator uses ahead of the audio buffer.

### LCD

`St7789::snapshot_view()` already produces a 240×240 RGB565 `uint16_t`
buffer. An exported `piko_get_lcd_ptr()` returns a pointer into WASM linear
memory; JS reads it directly via `HEAPU16.subarray(...)` and blits it to a
`<canvas>` through `ImageData` — no extra copy, same pixel format the
native window already uses.

### Audio

`PwmDac::set_sink` pushes floats into the existing portable
`sim::AudioRing`. An exported `piko_pull_audio(ptr, max_frames)` is called
from the `AudioWorklet`'s `process()` callback to copy samples into the
output buffer — the same role WASAPI's callback plays natively.

### Input

Keyboard and Gamepad API events both converge on the existing
`sim::set_button_mask(mask)` (`sim/runtime/sim_io.h`, already
thread-agnostic). The keyboard mapping mirrors `sim/README.md`'s table
(arrows/WASD, Q/E, Enter/Backspace); gamepad polling happens once per rAF
via `navigator.getGamepads()`, mirroring the XInput mapping in
`sim/platform/pad_input.cpp`.

### Bank

`build-sim/bin/amen_pad_bank.pikobank` is copied to `web/public/sim/` and
fetched before boot. It's written into the simulated flash with the same
`check_and_patch_bank` + `write_bank_to_flash` sequence `windowed.cpp`
already uses, before `Machine::boot()` runs. Fixed for v1 — no upload UI,
no drag-drop.

## UI integration

A new collapsed section in `web/src/App.tsx` ("Try it in your browser")
with a single "Load simulator" button. Nothing downloads (WASM, bank,
worklet) until the visitor opts in, so the default "just export a bank"
path stays as light as it is today.

`web/src/sim/SimDemo.tsx`:
- On the button click: instantiate the Emscripten module, fetch the bank,
  run the boot sequence, register canvas-scoped keyboard listeners (so
  typing elsewhere on the page doesn't leak into button state), start the
  `AudioWorklet` and the rAF loop.
- Renders a `<canvas width=240 height=240>`, a status line (audio state,
  speed, gamepad detected — same shape as the native status bar), and the
  keyboard-mapping legend from `sim/README.md`.
- On unmount: stop the rAF loop, disconnect the `AudioWorklet` node, drop
  the module reference. No state persists across reloads.

## Testing

Manual verification in the browser: load the demo, confirm the LCD
renders, confirm audio plays, confirm keyboard and gamepad both move
through the UI. No automated browser test suite for v1 — the existing
native `sim_core`/`sim_runtime` unit and integration tests already cover
the shared firmware logic; the WASM build only needs to prove the platform
glue (fiber shim, audio pull, LCD blit, input mapping) works end to end.

## Out of scope for v1

- File drop / bank upload (fixed demo bank only)
- Headless mode, CLI flags, `--dump-lcd`/`--dump-wav`
- Persisted flash state across page reloads
- Mobile touch controls
- Chasing WASM-vs-native behavioral parity beyond what's needed for the
  demo to look and sound right
