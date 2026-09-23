#include "runtime/headless.h"

#include <chrono>

#include "core/bank_file.h"
#include "core/flash_store.h"
#include "runtime/bank_hotload.h"
#include "runtime/firmware_entry.h"
#include "runtime/machine.h"
#include "runtime/sim_io.h"

namespace sim {

bool run_headless(const HeadlessOptions& o, HeadlessResult* r, std::string* err) {
  if (!flash().open(o.flash_path, err)) return false;
  if (!o.bank.empty()) {
    std::vector<uint8_t> blob = o.bank;
    const BankCheck c = check_and_patch_bank(blob);
    if (!c.ok) {
      *err = c.error;
      return false;
    }
    write_bank_to_flash(blob);
  }
  std::vector<uint8_t> hot = o.hot_bank;
  if (o.hot_load_at_ms > 0) {
    const BankCheck c = check_and_patch_bank(hot);
    if (!c.ok) {
      *err = c.error;
      return false;
    }
  }

  Machine& m = Machine::get();
  r->audio.clear();
  r->audio.reserve(static_cast<size_t>(o.run_ms) * kAudioRate / 1000 + 16);
  m.dac().set_sink([r](float s) { r->audio.push_back(s); });

  const auto t0 = std::chrono::steady_clock::now();
  m.boot(&piko_firmware_main);
  uint16_t mask = 0;
  size_t next = 0;
  for (uint32_t ms = 0; ms < o.run_ms; ++ms) {
    mask = apply_press_events(o.presses, &next, ms, mask);
    set_button_mask(mask);
    if (o.hot_load_at_ms > 0 && ms == o.hot_load_at_ms) hot_load_bank(hot);
    m.run_until(static_cast<uint64_t>(ms + 1) * (kCpuHz / 1000));
  }
  r->wall_seconds =
      std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  r->lcd.assign(static_cast<size_t>(St7789::kSize) * St7789::kSize, 0);
  m.lcd().snapshot_view(r->lcd.data());
  return true;
}

}  // namespace sim
