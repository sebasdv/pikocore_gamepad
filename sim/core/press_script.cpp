#include "core/press_script.h"

#include <algorithm>
#include <sstream>

#include "core/buttons.h"

namespace sim {

namespace {
std::vector<std::string> split(const std::string& s, char sep) {
  std::vector<std::string> parts;
  std::string part;
  std::istringstream in(s);
  while (std::getline(in, part, sep)) parts.push_back(part);
  return parts;
}
}  // namespace

bool parse_press_script(const std::string& text, std::vector<PressEvent>* out, std::string* err) {
  out->clear();
  if (text.empty()) return true;
  for (const std::string& token : split(text, ',')) {
    const size_t colon = token.find(':');
    if (colon == std::string::npos || colon == 0) {
      *err = "falta 'ms:' en \"" + token + "\"";
      return false;
    }
    const std::string ms = token.substr(0, colon);
    if (ms.size() > 9 || ms.find_first_not_of("0123456789") != std::string::npos) {
      *err = "tiempo inválido en \"" + token + "\"";
      return false;
    }
    PressEvent ev;
    ev.at_ms = static_cast<uint32_t>(std::stoul(ms));
    for (std::string item : split(token.substr(colon + 1), '+')) {
      const bool release = !item.empty() && item[0] == '-';
      if (release) item.erase(0, 1);
      const int b = button_from_name(item);
      if (b < 0) {
        *err = "botón desconocido \"" + item + "\"";
        return false;
      }
      uint16_t& target = release ? ev.release : ev.press;
      target = static_cast<uint16_t>(target | bit(static_cast<Button>(b)));
    }
    if (ev.press == 0 && ev.release == 0) {
      *err = "no hay botones en \"" + token + "\"";
      return false;
    }
    out->push_back(ev);
  }
  std::stable_sort(out->begin(), out->end(),
                   [](const PressEvent& a, const PressEvent& b) { return a.at_ms < b.at_ms; });
  return true;
}

uint16_t apply_press_events(const std::vector<PressEvent>& events, size_t* next,
                            uint32_t now_ms, uint16_t mask) {
  while (*next < events.size() && events[*next].at_ms <= now_ms) {
    mask = static_cast<uint16_t>((mask | events[*next].press) & ~events[*next].release);
    ++*next;
  }
  return mask;
}

}  // namespace sim
