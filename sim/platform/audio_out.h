#pragma once
#include <atomic>
#include <cstdint>
#include <future>
#include <string>
#include <thread>

#include "core/audio_ring.h"

namespace sim {

// Salida de audio por WASAPI en modo compartido, event-driven. Lee el ring
// (mono, 48 kHz, float) y duplica a estéreo; Windows convierte a la
// frecuencia del dispositivo (AUTOCONVERTPCM).
class AudioOut {
 public:
  ~AudioOut();
  bool start(AudioRing* ring, std::string* err);
  void stop();
  // Frames entregados al dispositivo (incluye silencio si el ring estaba vacío).
  uint64_t frames_consumed() const { return consumed_.load(); }

 private:
  void run(AudioRing* ring, std::promise<std::string>* ready);

  std::thread thread_;
  std::atomic<bool> quit_{false};
  std::atomic<uint64_t> consumed_{0};
};

}  // namespace sim
