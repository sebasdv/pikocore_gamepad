#pragma once
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "core/press_script.h"

namespace sim {

struct HeadlessOptions {
  std::vector<uint8_t> bank;          // vacío = lo que ya haya en la flash
  std::filesystem::path flash_path;   // vacío = flash solo en memoria
  uint32_t run_ms = 5000;
  std::vector<PressEvent> presses;
  uint32_t hot_load_at_ms = 0;        // 0 = no cargar nada en caliente
  std::vector<uint8_t> hot_bank;
};

struct HeadlessResult {
  std::vector<float> audio;     // mono, kAudioRate
  std::vector<uint16_t> lcd;    // 240x240 RGB565, como se ve en el GamePi13
  double wall_seconds = 0.0;
};

// Arranca el firmware y lo corre run_ms de tiempo virtual, sin pacing. Solo se
// puede llamar una vez por proceso: el firmware tiene estado global.
bool run_headless(const HeadlessOptions& options, HeadlessResult* result, std::string* err);

}  // namespace sim
