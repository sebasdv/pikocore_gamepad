#pragma once
#include <cstdint>
#include <vector>

// Banco .pikobank sintético para los tests: `count` samples de 4 beats a 120
// BPM (48000 frames a 24 kHz). Cada beat es un golpe senoidal que decae, con
// una frecuencia distinta por sample. PCM de 8 bits sin signo, centro 128.
std::vector<uint8_t> make_synth_bank(uint32_t count);
