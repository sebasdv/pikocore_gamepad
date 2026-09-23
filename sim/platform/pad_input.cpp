#include "platform/pad_input.h"

#include <windows.h>
#include <Xinput.h>

#include <chrono>

#include "core/buttons.h"

namespace sim {

PadInput::~PadInput() { stop(); }

void PadInput::start(std::function<void(uint16_t)> on_mask) {
  on_mask_ = std::move(on_mask);
  quit_ = false;
  thread_ = std::thread([this] { run(); });
}

void PadInput::stop() {
  quit_ = true;
  if (thread_.joinable()) thread_.join();
}

void PadInput::run() {
  using clock = std::chrono::steady_clock;
  int slot = -1;
  clock::time_point next_scan = clock::now();
  while (!quit_) {
    uint16_t pad = 0;
    const clock::time_point now = clock::now();
    if (slot < 0 && now >= next_scan) {
      // XInputGetState es caro sobre un slot vacío: buscar una vez por segundo.
      for (DWORD i = 0; i < XUSER_MAX_COUNT && slot < 0; ++i) {
        XINPUT_STATE state = {};
        if (XInputGetState(i, &state) == ERROR_SUCCESS) slot = static_cast<int>(i);
      }
      next_scan = now + std::chrono::seconds(1);
    }
    if (slot >= 0) {
      XINPUT_STATE state = {};
      if (XInputGetState(static_cast<DWORD>(slot), &state) == ERROR_SUCCESS) {
        pad = map_xinput(state.Gamepad.wButtons);
      } else {
        slot = -1;
        next_scan = now + std::chrono::seconds(1);
      }
    }
    connected_ = slot >= 0;
    on_mask_(static_cast<uint16_t>(pad | keyboard_.load()));
    Sleep(2);
  }
}

}  // namespace sim
