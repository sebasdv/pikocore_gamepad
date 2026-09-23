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
