#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace sim {

struct BankCheck {
  bool ok = false;
  std::string error;
  uint32_t sample_count = 0;
  bool capacity_patched = false;
};

// Capacidad de audio de la flash de 16 MB del GamePi13. Es la misma cuenta que
// capacity_from_flash_size() en src/PikoAudioBank.cpp.
uint32_t device_audio_capacity();

// Valida un .pikobank con las mismas reglas que validate_header()
// (src/PikoSampleManager.cpp). Si capacity_bytes supera la capacidad del
// equipo, lo corrige en el blob: el loader web escribe 16 MB en ese campo al
// exportar (web/src/App.tsx, SD_BANK_CAPACITY_BYTES), y con ese valor
// piko_audio_bank_rescan() rechazaría el banco.
BankCheck check_and_patch_bank(std::vector<uint8_t>& blob);

}  // namespace sim
