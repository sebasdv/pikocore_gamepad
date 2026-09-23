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
