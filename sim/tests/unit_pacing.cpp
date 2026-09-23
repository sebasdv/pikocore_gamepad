// Pacing del modo ventana (core/pacing.h).
#include "core/pacing.h"
#include "test.h"

using namespace sim;

namespace {
constexpr uint64_t kLead = 960;  // 20 ms a 48 kHz

PaceState ring(uint64_t fill) {
  PaceState s;
  s.audio_running = true;
  s.ring_fill = fill;
  return s;
}

PaceState wall(uint64_t produced, uint64_t wall_frames) {
  PaceState s;
  s.produced = produced;
  s.wall_frames = wall_frames;
  return s;
}
}  // namespace

TEST(pacing_ring_below_lead_steps) {
  CHECK(should_step(ring(0), kLead));
  CHECK(should_step(ring(kLead - 1), kLead));
}

TEST(pacing_ring_at_or_above_lead_waits) {
  CHECK(!should_step(ring(kLead), kLead));
  CHECK(!should_step(ring(kLead * 10), kLead));
}

TEST(pacing_ring_ignores_produced_counters) {
  // Con audio, lo que manda es el nivel del ring: aunque WASAPI haya
  // "consumido" mucho silencio (produced muy atrás del reloj), no se corre
  // de más si el ring ya tiene su lead.
  PaceState s = ring(kLead);
  s.produced = 0;
  s.wall_frames = 1000000;
  CHECK(!should_step(s, kLead));
}

TEST(pacing_wall_clock_keeps_lead_over_wall) {
  CHECK(should_step(wall(0, 0), kLead));
  CHECK(should_step(wall(1000 + kLead - 1, 1000), kLead));
  CHECK(!should_step(wall(1000 + kLead, 1000), kLead));
  CHECK(!should_step(wall(5000, 1000), kLead));
}
