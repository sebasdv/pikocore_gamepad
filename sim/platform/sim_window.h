#pragma once
#include <cstdint>
#include <filesystem>
#include <functional>
#include <string>

namespace sim {

struct WindowHooks {
  std::function<void(uint16_t* out)> snapshot_lcd;  // 240x240 RGB565, vista
  std::function<uint16_t()> button_mask;            // bits = sim::Button
  std::function<bool()> beat_led;
  std::function<uint16_t()> backlight;               // 0-65535
  std::function<std::wstring()> status;
  std::function<void(uint16_t)> keyboard_mask;
  std::function<void(const std::filesystem::path&)> file_dropped;
};

// Abre la ventana y corre el message loop hasta que se cierre. Con
// exit_after_ms > 0 se cierra sola, y si capture no está vacío guarda la
// ventana como BMP antes: sirve para verificarla sin intervención.
int run_window(const WindowHooks& hooks, const std::filesystem::path& capture,
               uint32_t exit_after_ms);

}  // namespace sim
