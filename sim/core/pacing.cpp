#include "core/pacing.h"

namespace sim {

bool should_step(const PaceState& s, uint64_t lead_frames) {
  if (s.audio_running) return s.ring_fill < lead_frames;
  return s.produced < s.wall_frames + lead_frames;
}

}  // namespace sim
