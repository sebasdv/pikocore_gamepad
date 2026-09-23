#include "web/fiber_shim.h"

#include <algorithm>
#include <cstdint>

namespace sim {

Machine& Machine::get() {
  static Machine machine;
  return machine;
}

Machine::Machine() : dac_(kCpuHz, static_cast<uint32_t>(kPwmPeriodCycles), kAudioRate) {}

void Machine::boot(int (*firmware_main)()) {
  firmware_main_ = firmware_main;
  emscripten_fiber_init_from_current_context(&scheduler_fiber_, scheduler_asyncify_stack_,
                                              sizeof(scheduler_asyncify_stack_));
  emscripten_fiber_init(&main_fiber_, &Machine::fiber_entry, this, main_c_stack_,
                         sizeof(main_c_stack_), main_asyncify_stack_,
                         sizeof(main_asyncify_stack_));
  main_wake_ = now_;
}

void Machine::fiber_entry(void* arg) {
  Machine* m = static_cast<Machine*>(arg);
  m->firmware_main_();
  // El main() del firmware no vuelve nunca; si volviera, queda dormido.
  for (;;) m->main_sleep_until(UINT64_MAX);
}

bool Machine::in_main() const { return in_main_; }

void Machine::main_sleep_until(uint64_t cycles) {
  main_wake_ = std::max(cycles, now_);
  emscripten_fiber_swap(&main_fiber_, &scheduler_fiber_);
}

void Machine::main_wfi() { main_sleep_until(next_pwm_); }

void Machine::run_until(uint64_t target) {
  while (now_ < target) {
    if (main_wake_ <= now_) {
      in_main_ = true;
      emscripten_fiber_swap(&scheduler_fiber_, &main_fiber_);
      in_main_ = false;
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
