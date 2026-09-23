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
