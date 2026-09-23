#pragma once
#include <cstdint>

namespace sim {

// Cómo decide el modo ventana cuándo correr 1 ms más de emulación.
struct PaceState {
  // true: WASAPI está consumiendo el ring; se pacea por su nivel real.
  // false: sin audio o audio perdido; se pacea por reloj de pared.
  bool audio_running = false;
  uint64_t ring_fill = 0;    // muestras en el ring (solo con audio_running)
  uint64_t produced = 0;     // muestras producidas (solo por reloj de pared)
  uint64_t wall_frames = 0;  // muestras que "deberían" haberse consumido según el reloj
};

// true = correr otro paso. Con audio, mantiene el ring en lead_frames: el
// silencio que WASAPI inserta en un underrun no se acumula como latencia.
bool should_step(const PaceState& s, uint64_t lead_frames);

}  // namespace sim
