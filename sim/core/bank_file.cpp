#include "core/bank_file.h"

#include <cstddef>
#include <cstring>

#include "PikoAudioBank.h"

// piko_fw se compila con PIKO_FIRMWARE_RESERVE=524288u (sim/CMakeLists.txt),
// pero este TU no: toma el default de PikoAudioBank.h. Tienen que coincidir o
// el simulador y el firmware verían el banco en offsets distintos.
static_assert(PIKO_AUDIO_FLASH_OFFSET == 524288u,
              "PIKO_AUDIO_FLASH_OFFSET no coincide con el PIKO_FIRMWARE_RESERVE de piko_fw");

namespace sim {

uint32_t device_audio_capacity() {
  return PIKO_COMPILED_FLASH_TOTAL_BYTES - PIKO_AUDIO_FLASH_OFFSET - PIKO_BANK_HEADER_SIZE;
}

BankCheck check_and_patch_bank(std::vector<uint8_t>& blob) {
  BankCheck r;
  if (blob.size() < PIKO_BANK_HEADER_SIZE) {
    r.error = "el archivo es demasiado chico para ser un .pikobank";
    return r;
  }
  PikoBankHeader h;
  std::memcpy(&h, blob.data(), sizeof(h));
  const uint32_t cap = device_audio_capacity();
  const uint64_t audio_bytes = blob.size() - PIKO_BANK_HEADER_SIZE;

  if (h.magic != PIKO_BANK_MAGIC) {
    r.error = "no es un .pikobank (magic incorrecto)";
    return r;
  }
  if (h.version != PIKO_BANK_VERSION) {
    r.error = "versión de banco no soportada: " + std::to_string(h.version);
    return r;
  }
  if (h.header_size != PIKO_BANK_HEADER_SIZE || h.sample_rate != PIKO_BANK_SAMPLE_RATE) {
    r.error = "header de banco inválido";
    return r;
  }
  if (h.sample_count > PIKO_BANK_MAX_SAMPLES) {
    r.error = "el banco tiene más de 128 samples";
    return r;
  }
  if (h.audio_bytes != audio_bytes) {
    r.error = "el tamaño del archivo no coincide con el header";
    return r;
  }
  if (h.audio_bytes > cap) {
    r.error = "el banco no entra en la flash";
    return r;
  }
  for (uint32_t i = 0; i < h.sample_count; ++i) {
    const PikoBankSampleRecord& s = h.samples[i];
    if (s.frame_count == 0 || s.source_bpm == 0 || s.beat_count == 0 ||
        s.offset > h.audio_bytes || s.frame_count > h.audio_bytes - s.offset) {
      r.error = "el sample " + std::to_string(i + 1) + " del banco es inválido";
      return r;
    }
  }
  if (h.capacity_bytes > cap) {
    std::memcpy(blob.data() + offsetof(PikoBankHeader, capacity_bytes), &cap, sizeof(cap));
    r.capacity_patched = true;
  }
  r.ok = true;
  r.sample_count = h.sample_count;
  return r;
}

}  // namespace sim
