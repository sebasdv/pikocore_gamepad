#pragma once
#include <cstdint>
#include <vector>

namespace sim {

// Escribe un .pikobank ya validado (check_and_patch_bank) en la flash simulada,
// sin avisarle al firmware. Sirve antes del boot: piko_audio_bank_init() lo lee.
void write_bank_to_flash(const std::vector<uint8_t>& blob);

// Carga en caliente con la misma secuencia que el core1 real
// (src/PikoSampleManager.cpp): mutating -> escribir flash -> rescan ->
// !mutating. Llamar solo entre dos run_until(), desde el hilo de emulación.
void hot_load_bank(const std::vector<uint8_t>& blob);

}  // namespace sim
