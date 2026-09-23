#include "core/buttons.h"

#include <cctype>

namespace sim {

namespace {
const char* const kNames[kButtonCount] = {"UP", "DOWN", "LEFT", "RIGHT", "Y", "X",
                                          "B", "A", "SELECT", "START", "L", "R"};

// Constantes de Xinput.h, repetidas acá para que el core no dependa de windows.h.
constexpr uint16_t kXDpadUp = 0x0001, kXDpadDown = 0x0002, kXDpadLeft = 0x0004,
                   kXDpadRight = 0x0008, kXStart = 0x0010, kXBack = 0x0020,
                   kXLeftShoulder = 0x0100, kXRightShoulder = 0x0200, kXA = 0x1000,
                   kXB = 0x2000, kXX = 0x4000, kXY = 0x8000;

struct XMap {
  uint16_t xinput;
  Button button;
};
constexpr XMap kXMap[] = {
    {kXDpadUp, kUp},       {kXDpadDown, kDown}, {kXDpadLeft, kLeft},
    {kXDpadRight, kRight}, {kXY, kX},           {kXB, kA},
    {kXA, kB},             {kXX, kY},           {kXLeftShoulder, kL},
    {kXRightShoulder, kR}, {kXBack, kSelect},   {kXStart, kStart}};

struct VkMap {
  unsigned vk;
  Button button;
};
constexpr VkMap kVkMap[] = {
    {0x26, kUp},  {0x28, kDown},  {0x25, kLeft},  {0x27, kRight},  // flechas
    {'W', kX},    {'D', kA},      {'S', kB},      {'A', kY},
    {'Q', kL},    {'E', kR},      {0x08, kSelect}, {0x0D, kStart}};  // Backspace, Enter
}  // namespace

const char* button_name(Button b) { return b < kButtonCount ? kNames[b] : "?"; }

int button_from_name(const std::string& name) {
  std::string upper;
  for (char c : name) upper.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(c))));
  for (int i = 0; i < kButtonCount; ++i) {
    if (upper == kNames[i]) return i;
  }
  return -1;
}

uint16_t map_xinput(uint16_t xinput_buttons) {
  uint16_t mask = 0;
  for (const XMap& e : kXMap) {
    if (xinput_buttons & e.xinput) mask = static_cast<uint16_t>(mask | bit(e.button));
  }
  return mask;
}

int button_for_vk(unsigned vk) {
  for (const VkMap& e : kVkMap) {
    if (e.vk == vk) return e.button;
  }
  return -1;
}

}  // namespace sim
