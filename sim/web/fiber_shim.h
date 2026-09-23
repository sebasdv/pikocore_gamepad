#pragma once
#include <cstdint>
#include <emscripten/fiber.h>

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

// Planificador determinista del RP2350 simulado, portado de sim/runtime/machine.cpp
// (Machine) para correr sobre WebAssembly. El main() del firmware corre en una
// fiber de Emscripten (emscripten/fiber.h, sobre Asyncify) en vez de una Fiber de
// Win32, y cede el control en __wfi(), sleep_*() y cada lectura del timer; entre
// medio, run_until() corre los ticks de PWM (ISR de audio + DAC). Todo el firmware
// corre en el hilo que llamó a boot(). La lógica del planificador es la misma que
// sim/runtime/machine.cpp; sólo cambian las primitivas de fiber.
class Machine {
 public:
  static Machine& get();

  // Prepara las fibers y el main() del firmware. Llamar una vez, desde el hilo
  // que después llama a run_until().
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
  static void fiber_entry(void* arg);

  static constexpr size_t kStackSize = 1u << 20;        // matches CreateFiber's 1 MB native stack
  static constexpr size_t kAsyncifyStackSize = 1u << 16;

  emscripten_fiber_t scheduler_fiber_{};
  emscripten_fiber_t main_fiber_{};
  char scheduler_asyncify_stack_[kAsyncifyStackSize]{};
  char main_c_stack_[kStackSize]{};
  char main_asyncify_stack_[kAsyncifyStackSize]{};
  // GetCurrentFiber() no tiene equivalente en emscripten/fiber.h: in_main() se
  // reconstruye a mano, marcando este flag justo antes/después del swap hacia
  // main_fiber_ en run_until() (ver fiber_shim.cpp).
  bool in_main_ = false;

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
