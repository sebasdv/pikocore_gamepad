#include <cmath>
#include <cstdint>
#include <vector>

#include "core/audio_ring.h"
#include "core/pwm_dac.h"
#include "test.h"

using sim::AudioRing;
using sim::PwmDac;

namespace {
constexpr uint64_t kCpuHz = 248000000;
constexpr uint32_t kPeriod = 251;
constexpr uint32_t kTicksPerSecond = 988047;  // 248 MHz / 251
}  // namespace

TEST(dac_emits_out_rate_samples_per_second) {
  PwmDac dac(kCpuHz, kPeriod, 48000);
  uint32_t n = 0;
  dac.set_sink([&](float) { ++n; });
  for (uint32_t i = 0; i < kTicksPerSecond; ++i) dac.tick(125);
  CHECK(n >= 47999 && n <= 48000);
}

TEST(dac_blocks_dc) {
  PwmDac dac(kCpuHz, kPeriod, 48000);
  std::vector<float> out;
  dac.set_sink([&](float s) { out.push_back(s); });
  for (uint32_t i = 0; i < kTicksPerSecond; ++i) dac.tick(200);
  CHECK(!out.empty());
  CHECK(std::fabs(out.front()) < 1e-6f);
  CHECK(std::fabs(out.back()) < 1e-3f);
}

TEST(dac_step_up_gives_positive_transient) {
  PwmDac dac(kCpuHz, kPeriod, 48000);
  std::vector<float> out;
  dac.set_sink([&](float s) { out.push_back(s); });
  for (uint32_t i = 0; i < kTicksPerSecond / 2; ++i) dac.tick(125);
  const size_t mark = out.size();
  for (uint32_t i = 0; i < 100; ++i) dac.tick(250);
  CHECK(out.size() > mark + 1);
  CHECK(out[mark + 1] > 0.4f);
}

TEST(ring_keeps_order) {
  AudioRing ring(8);
  CHECK(ring.push(1.0f));
  CHECK(ring.push(2.0f));
  CHECK(ring.push(3.0f));
  float out[3] = {};
  CHECK_EQ(ring.pop(out, 3), 3);
  CHECK(out[0] == 1.0f && out[1] == 2.0f && out[2] == 3.0f);
  CHECK_EQ(ring.size(), 0);
}

TEST(ring_rejects_when_full) {
  AudioRing ring(4);
  for (int i = 0; i < 4; ++i) CHECK(ring.push(float(i)));
  CHECK(!ring.push(9.0f));
  float out[10] = {};
  CHECK_EQ(ring.pop(out, 10), 4);
  CHECK(ring.push(9.0f));
}
