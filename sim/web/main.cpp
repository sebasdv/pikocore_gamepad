// sim/web/main.cpp
#include <cstdint>
#include <vector>

#include <emscripten/emscripten.h>

#include "core/audio_ring.h"
#include "core/bank_file.h"
#include "core/buttons.h"
#include "core/flash_store.h"
#include "core/pacing.h"
#include "runtime/bank_hotload.h"
#include "runtime/firmware_entry.h"
#include "runtime/sim_io.h"
#include "web/fiber_shim.h"

namespace {

sim::AudioRing g_ring(sim::kAudioRate / 2);  // 500 ms margin, same as windowed.cpp
uint64_t g_produced = 0;
uint16_t g_lcd_snapshot[sim::St7789::kSize * sim::St7789::kSize];
bool g_booted = false;

}  // namespace

extern "C" {

EMSCRIPTEN_KEEPALIVE
int piko_init(const uint8_t* bank_ptr, int bank_len) {
  std::string err;
  sim::flash().open("", &err);  // memory-only, no persisted flash for the web demo

  std::vector<uint8_t> blob(bank_ptr, bank_ptr + bank_len);
  const sim::BankCheck check = sim::check_and_patch_bank(blob);
  if (check.ok) sim::write_bank_to_flash(blob);  // before boot: piko_audio_bank_init() reads it

  sim::Machine& m = sim::Machine::get();
  m.dac().set_sink([](float s) {
    g_ring.push(s);
    ++g_produced;
  });
  m.boot(&piko_firmware_main);
  g_booted = true;
  return check.ok ? 1 : 0;
}

EMSCRIPTEN_KEEPALIVE
void piko_step(double budget_ms) {
  if (!g_booted) return;
  sim::Machine& m = sim::Machine::get();
  constexpr uint64_t kLeadFrames = sim::kAudioRate * 20 / 1000;  // ~20 ms lead, same as native
  sim::PaceState pace;
  pace.audio_running = true;
  pace.ring_fill = g_ring.size();
  pace.produced = g_produced;
  double spent_ms = 0.0;
  // 1 ms of virtual CPU time per should_step() == true, matching windowed.cpp's granularity.
  while (spent_ms < budget_ms && sim::should_step(pace, kLeadFrames)) {
    m.run_until(m.now_cycles() + sim::kCpuHz / 1000);
    spent_ms += 1.0;
    pace.ring_fill = g_ring.size();
    pace.produced = g_produced;
  }
}

EMSCRIPTEN_KEEPALIVE
void piko_snapshot_lcd() {
  if (g_booted) sim::Machine::get().lcd().snapshot_view(g_lcd_snapshot);
}

EMSCRIPTEN_KEEPALIVE
const uint16_t* piko_lcd_ptr() { return g_lcd_snapshot; }

EMSCRIPTEN_KEEPALIVE
void piko_set_buttons(uint16_t mask) { sim::set_button_mask(mask); }

EMSCRIPTEN_KEEPALIVE
uint16_t piko_map_xinput(uint16_t xinput_buttons) { return sim::map_xinput(xinput_buttons); }

EMSCRIPTEN_KEEPALIVE
int piko_pull_audio(float* out, int max_frames) {
  return static_cast<int>(g_ring.pop(out, static_cast<size_t>(max_frames)));
}

EMSCRIPTEN_KEEPALIVE
float piko_speed() {
  if (!g_booted) return 0.0f;
  return static_cast<float>(sim::Machine::get().now_cycles()) / sim::kCpuHz;
}

}  // extern "C"
