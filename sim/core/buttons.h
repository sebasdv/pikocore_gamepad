#pragma once
#include <cstdint>
#include <string>

#include "hw_gamepi13.h"

namespace sim {

// Mismo orden que los 8 botones musicales de pikocore (GAMEPI_BUTTON_PINS) y
// después los 4 de control.
enum Button : uint8_t {
  kUp, kDown, kLeft, kRight, kY, kX, kB, kA,
  kSelect, kStart, kL, kR,
  kButtonCount
};

inline constexpr uint8_t kMusicPins[8] = GAMEPI_BUTTON_PINS;
inline constexpr uint8_t kButtonPins[kButtonCount] = {
    kMusicPins[0], kMusicPins[1], kMusicPins[2], kMusicPins[3],
    kMusicPins[4], kMusicPins[5], kMusicPins[6], kMusicPins[7],
    GAMEPI_BTN_SELECT, GAMEPI_BTN_START, GAMEPI_BTN_L, GAMEPI_BTN_R};

constexpr uint16_t bit(Button b) { return static_cast<uint16_t>(1u << b); }

const char* button_name(Button b);
// Sin distinguir mayúsculas; -1 si no existe.
int button_from_name(const std::string& name);
// wButtons de XINPUT_GAMEPAD -> máscara de Button. Botones de cara por
// posición: el de arriba del control Xbox (Y) es el de arriba del GamePi13 (X).
uint16_t map_xinput(uint16_t xinput_buttons);
// Tecla virtual de Windows -> Button, o -1.
int button_for_vk(unsigned vk);

}  // namespace sim
