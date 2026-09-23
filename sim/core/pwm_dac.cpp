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
