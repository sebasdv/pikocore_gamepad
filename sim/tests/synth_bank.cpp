#include "synth_bank.h"

#include <cmath>
#include <cstdio>
#include <cstring>

#include "PikoAudioBank.h"
#include "core/bank_file.h"

std::vector<uint8_t> make_synth_bank(uint32_t count) {
  constexpr uint32_t kFrames = 48000;
  constexpr uint32_t kBeatFrames = 12000;
  std::vector<uint8_t> blob(PIKO_BANK_HEADER_SIZE + count * kFrames, 0xff);

  PikoBankHeader h;
  std::memset(&h, 0xff, sizeof(h));
  h.magic = PIKO_BANK_MAGIC;
  h.version = PIKO_BANK_VERSION;
  h.header_size = PIKO_BANK_HEADER_SIZE;
  h.sample_rate = PIKO_BANK_SAMPLE_RATE;
  h.sample_count = count;
  h.audio_bytes = count * kFrames;
  h.capacity_bytes = sim::device_audio_capacity();
  h.reserved0 = 0;
  for (uint32_t i = 0; i < count; ++i) {
    PikoBankSampleRecord& s = h.samples[i];
    std::memset(&s, 0, sizeof(s));
    s.offset = i * kFrames;
    s.frame_count = kFrames;
    s.source_bpm = 120;
    s.beat_count = 4;
    s.peak = 228;
    std::snprintf(s.name, sizeof(s.name), "synth_%u", i + 1);
    const double freq = 110.0 * (i + 1);
    for (uint32_t f = 0; f < kFrames; ++f) {
      const double t = (f % kBeatFrames) / 24000.0;
      const double v = std::sin(2.0 * 3.14159265358979 * freq * t) * std::exp(-t * 6.0);
      blob[PIKO_BANK_HEADER_SIZE + s.offset + f] = static_cast<uint8_t>(128.0 + 100.0 * v);
    }
  }
  std::memcpy(blob.data(), &h, sizeof(h));
  return blob;
}
