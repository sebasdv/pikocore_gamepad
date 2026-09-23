#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace sim {

struct PressEvent {
  uint32_t at_ms = 0;
  uint16_t press = 0;    // máscara de Button a apretar
  uint16_t release = 0;  // máscara de Button a soltar
};

// "1000:A+B,1500:-A": a los 1000 ms se aprietan A y B; a los 1500 se suelta A.
// Nombres de botones: los de button_name(). Queda ordenado por tiempo.
bool parse_press_script(const std::string& text, std::vector<PressEvent>* out, std::string* err);

// Aplica a `mask` los eventos con at_ms <= now_ms a partir de *next y avanza *next.
uint16_t apply_press_events(const std::vector<PressEvent>& events, size_t* next,
                            uint32_t now_ms, uint16_t mask);

}  // namespace sim
