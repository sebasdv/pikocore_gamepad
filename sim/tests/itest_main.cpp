// Tests de integración: un escenario por proceso, porque el firmware tiene
// estado global y solo se puede arrancar una vez.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>

#include "PikoAudioBank.h"
#include "core/press_script.h"
#include "runtime/headless.h"
#include "runtime/machine.h"
#include "synth_bank.h"

extern uint8_t gamepi_selector;  // src/main.cpp

namespace {
constexpr uint16_t kWhite = 0xFFFF;  // COL_WHITE de src/gamepi13/ui.cpp
constexpr uint16_t kGray = 0x632C;   // COL_GRAY de src/gamepi13/ui.cpp
int g_failures = 0;

void expect(bool ok, const char* what) {
  std::printf("%s %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) ++g_failures;
}

double rms(const std::vector<float>& a, uint32_t from_ms, uint32_t to_ms) {
  const size_t per_ms = sim::kAudioRate / 1000;
  const size_t from = static_cast<size_t>(from_ms) * per_ms;
  const size_t to = std::min(a.size(), static_cast<size_t>(to_ms) * per_ms);
  if (to <= from) return 0.0;
  double acc = 0.0;
  for (size_t i = from; i < to; ++i) acc += static_cast<double>(a[i]) * a[i];
  return std::sqrt(acc / static_cast<double>(to - from));
}

// Centro del cuadrado del modo i en la fila de modos (draw_dots() en ui.cpp:
// 8 slots de 30 px, cuadrados de 20 px en y = 212..231).
uint16_t mode_square(const sim::HeadlessResult& r, int i) {
  return r.lcd[static_cast<size_t>(222) * 240 + i * 30 + 15];
}

bool run(const sim::HeadlessOptions& o, sim::HeadlessResult* r) {
  std::string err;
  if (!sim::run_headless(o, r, &err)) {
    std::printf("FAIL run_headless: %s\n", err.c_str());
    return false;
  }
  std::printf("     %u ms virtuales en %.2f s reales (x%.2f)\n", o.run_ms, r->wall_seconds,
              o.run_ms / 1000.0 / r->wall_seconds);
  return true;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    std::printf("uso: pikocore_sim_itest boot|mute|mode_jump|hotload|dump_bank ARCHIVO\n");
    return 2;
  }
  const std::string scenario = argv[1];

  if (scenario == "dump_bank") {
    if (argc < 3) {
      std::printf("uso: pikocore_sim_itest dump_bank ARCHIVO\n");
      return 2;
    }
    const std::vector<uint8_t> blob = make_synth_bank(4);
    FILE* f = std::fopen(argv[2], "wb");
    if (f == nullptr) return 1;
    const bool ok = std::fwrite(blob.data(), 1, blob.size(), f) == blob.size();
    std::fclose(f);
    std::printf("banco sintético -> %s\n", argv[2]);
    return ok ? 0 : 1;
  }

  sim::HeadlessOptions o;
  sim::HeadlessResult r;
  o.bank = make_synth_bank(2);

  std::string err;
  if (scenario == "boot") {
    o.run_ms = 6000;
    if (!run(o, &r)) return 1;
    expect(rms(r.audio, 5000, 6000) > 0.01, "hay audio después del arranque");
    size_t lit = 0;
    for (uint16_t p : r.lcd) lit += p != 0;
    expect(lit > 1000, "el LCD muestra el dashboard");
    expect(mode_square(r, 0) == kWhite, "modo 0 resaltado");
    expect(mode_square(r, 1) == kGray, "modo 1 en gris");
  } else if (scenario == "mute") {
    // Start con un toque simple alterna mute (GAMEPI13-INTERFACE.md §2).
    sim::parse_press_script("6000:START,6150:-START", &o.presses, &err);
    o.run_ms = 7500;
    if (!run(o, &r)) return 1;
    expect(rms(r.audio, 5000, 6000) > 0.01, "suena antes de tocar Start");
    expect(rms(r.audio, 7000, 7500) < 0.001, "silencio después de tocar Start");
  } else if (scenario == "mode_jump") {
    // Select sostenido + Right salta directo al modo 3 (GAMEPI13-INTERFACE.md §3).
    sim::parse_press_script("6000:SELECT,6100:RIGHT,6200:-RIGHT,6300:-SELECT", &o.presses, &err);
    o.run_ms = 7000;
    if (!run(o, &r)) return 1;
    expect(gamepi_selector == 3, "Select+Right salta al modo 3");
    expect(mode_square(r, 3) == kWhite, "modo 3 resaltado en el LCD");
    expect(mode_square(r, 0) == kGray, "modo 0 ya no está resaltado");
  } else if (scenario == "hotload") {
    o.hot_load_at_ms = 5000;
    o.hot_bank = make_synth_bank(5);
    o.run_ms = 6500;
    if (!run(o, &r)) return 1;
    expect(piko_audio_sample_count() == 5, "el banco cargado en caliente tiene 5 samples");
    expect(rms(r.audio, 6000, 6500) > 0.01, "sigue sonando después de la carga");
  } else {
    std::printf("escenario desconocido: %s\n", scenario.c_str());
    return 2;
  }
  return g_failures == 0 ? 0 : 1;
}
