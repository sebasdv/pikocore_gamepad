// Implementación de las funciones sim_* que declara sim/shim/sim_pico.h: acá el
// "hardware" del RP2350 se conecta con la Machine y el resto del simulador.
#include <atomic>

#include "PikoAudioBank.h"
#include "core/buttons.h"
#include "core/flash_store.h"
#include "hw_gamepi13.h"
#include "runtime/machine.h"
#include "runtime/sim_io.h"
#include "sim_pico.h"

// piko_fw se compila con PIKO_FIRMWARE_RESERVE=524288u (sim/CMakeLists.txt),
// pero este TU no: toma el default de PikoAudioBank.h. Tienen que coincidir o
// el simulador y el firmware verían el banco en offsets distintos.
static_assert(PIKO_AUDIO_FLASH_OFFSET == 524288u,
              "PIKO_AUDIO_FLASH_OFFSET no coincide con el PIKO_FIRMWARE_RESERVE de piko_fw");

uint8_t sim_flash_mem[PIKO_COMPILED_FLASH_TOTAL_BYTES];

namespace {
constexpr uint32_t kPinCount = 48;
std::atomic<bool> g_pin_low[kPinCount];  // salidas: true = el firmware escribió 0
std::atomic<uint16_t> g_buttons{0};
std::atomic<uint16_t> g_backlight{0};
std::atomic<bool> g_led{false};
sim::FlashStore g_flash(sim_flash_mem, sizeof(sim_flash_mem));

int button_for_pin(uint pin) {
  for (int b = 0; b < sim::kButtonCount; ++b) {
    if (sim::kButtonPins[b] == pin) return b;
  }
  return -1;
}
}  // namespace

namespace sim {
FlashStore& flash() { return g_flash; }
void set_button_mask(uint16_t mask) { g_buttons = mask; }
uint16_t button_mask() { return g_buttons; }
bool beat_led() { return g_led; }
uint16_t backlight_level() { return g_backlight; }
}  // namespace sim

extern "C" {

uint64_t sim_time_us(void) {
  sim::Machine& m = sim::Machine::get();
  if (m.in_main()) m.main_sleep_until(m.now_cycles() + sim::kTimeReadCycles);
  return m.now_us();
}

void sim_sleep_until_us(uint64_t t_us) {
  sim::Machine& m = sim::Machine::get();
  if (m.in_main()) m.main_sleep_until(t_us * sim::kCyclesPerUs);
}

void sim_wfi(void) {
  sim::Machine& m = sim::Machine::get();
  if (m.in_main()) m.main_wfi();
}

bool sim_gpio_get(uint pin) {
  const int b = button_for_pin(pin);
  // Botones con pull-up: apretado = 0.
  if (b >= 0) return (g_buttons.load() & sim::bit(static_cast<sim::Button>(b))) == 0;
  return pin < kPinCount ? !g_pin_low[pin].load() : true;
}

void sim_gpio_put(uint pin, bool value) {
  if (pin >= kPinCount) return;
  g_pin_low[pin] = !value;
  sim::Machine& m = sim::Machine::get();
  if (pin == GAMEPI_LCD_DC_PIN) {
    m.lcd().set_dc(value);
  } else if (pin == GAMEPI_LCD_CS_PIN) {
    m.lcd().set_cs(value);
  } else if (pin == GAMEPI_LED_PIN) {
    g_led = value;
  }
}

void sim_pwm_set_level(uint pin, uint16_t level) {
  if (pin == GAMEPI_AUDIO_PIN) {
    sim::Machine::get().set_audio_level(level);
  } else if (pin == GAMEPI_LCD_BL_PIN) {
    g_backlight = level;
  }
}

void sim_pwm_irq_enable(bool enabled) { sim::Machine::get().set_pwm_irq_enabled(enabled); }
void sim_irq_set_handler(void (*handler)(void)) { sim::Machine::get().set_irq_handler(handler); }
void sim_irq_enable(bool enabled) { sim::Machine::get().set_irq_enabled(enabled); }
void sim_spi_write(const uint8_t* src, size_t len) { sim::Machine::get().lcd().write(src, len); }
void sim_flash_erase(uint32_t offset, size_t count) { g_flash.erase(offset, count); }
void sim_flash_program(uint32_t offset, const uint8_t* data, size_t count) {
  g_flash.program(offset, data, count);
}

}  // extern "C"
