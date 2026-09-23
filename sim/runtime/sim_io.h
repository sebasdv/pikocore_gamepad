#pragma once
#include <cstdint>

namespace sim {

class FlashStore;

// La flash simulada de 16 MB (sim_flash_mem).
FlashStore& flash();
// Botones apretados; bits = sim::Button. Thread-safe.
void set_button_mask(uint16_t mask);
uint16_t button_mask();
// LED de beat (GP28).
bool beat_led();
// Nivel PWM del backlight del LCD (GP7), 0-65535.
uint16_t backlight_level();

}  // namespace sim
