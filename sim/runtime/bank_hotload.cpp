#include "runtime/bank_hotload.h"

#include "PikoAudioBank.h"
#include "core/flash_store.h"
#include "runtime/sim_io.h"

namespace sim {

void write_bank_to_flash(const std::vector<uint8_t>& blob) {
  const size_t erase_len = (blob.size() + PIKO_FLASH_SECTOR_SIZE - 1) &
                           ~static_cast<size_t>(PIKO_FLASH_SECTOR_SIZE - 1);
  flash().erase(PIKO_AUDIO_FLASH_OFFSET, erase_len);
  flash().program(PIKO_AUDIO_FLASH_OFFSET, blob.data(), blob.size());
}

void hot_load_bank(const std::vector<uint8_t>& blob) {
  piko_audio_bank_set_mutating(true);
  write_bank_to_flash(blob);
  piko_audio_bank_rescan();
  piko_audio_bank_set_mutating(false);
}

}  // namespace sim
