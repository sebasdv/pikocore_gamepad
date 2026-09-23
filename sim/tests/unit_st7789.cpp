#include <initializer_list>
#include <vector>

#include "core/st7789.h"
#include "test.h"

using sim::St7789;

namespace {
// Igual que LCD_1IN3_SendCommand/SendData: DC en bajo = comando, CS en bajo.
void cmd(St7789& lcd, uint8_t c, std::initializer_list<uint8_t> params) {
  lcd.set_cs(false);
  lcd.set_dc(false);
  lcd.write(&c, 1);
  lcd.set_dc(true);
  for (uint8_t p : params) lcd.write(&p, 1);
  lcd.set_cs(true);
}

void window(St7789& lcd, uint16_t x0, uint16_t x1, uint16_t y0, uint16_t y1) {
  cmd(lcd, 0x2A, {uint8_t(x0 >> 8), uint8_t(x0), uint8_t(x1 >> 8), uint8_t(x1)});
  cmd(lcd, 0x2B, {uint8_t(y0 >> 8), uint8_t(y0), uint8_t(y1 >> 8), uint8_t(y1)});
}

void pixels(St7789& lcd, std::initializer_list<uint16_t> px) {
  const uint8_t ramwr = 0x2C;
  lcd.set_cs(false);
  lcd.set_dc(false);
  lcd.write(&ramwr, 1);
  lcd.set_dc(true);
  for (uint16_t p : px) {
    const uint8_t b[2] = {uint8_t(p >> 8), uint8_t(p)};
    lcd.write(b, 2);
  }
  lcd.set_cs(true);
}
}  // namespace

TEST(st7789_writes_window_row_major) {
  St7789 lcd;
  window(lcd, 10, 11, 20, 21);
  pixels(lcd, {0x1234, 0x5678, 0x9abc, 0xdef0});
  CHECK_EQ(lcd.raw(10, 20), 0x1234);
  CHECK_EQ(lcd.raw(11, 20), 0x5678);
  CHECK_EQ(lcd.raw(10, 21), 0x9abc);
  CHECK_EQ(lcd.raw(11, 21), 0xdef0);
  CHECK_EQ(lcd.pixels_written(), 4);
}

TEST(st7789_wraps_to_window_start) {
  St7789 lcd;
  window(lcd, 10, 11, 20, 21);
  pixels(lcd, {1, 2, 3, 4, 0x1111});
  CHECK_EQ(lcd.raw(10, 20), 0x1111);
  CHECK_EQ(lcd.raw(11, 20), 2);
}

TEST(st7789_ignores_bytes_with_cs_high) {
  St7789 lcd;
  window(lcd, 0, 0, 0, 0);
  lcd.set_cs(true);
  lcd.set_dc(false);
  const uint8_t ramwr = 0x2C;
  lcd.write(&ramwr, 1);
  lcd.set_dc(true);
  const uint8_t b[2] = {0xff, 0xff};
  lcd.write(b, 2);
  CHECK_EQ(lcd.raw(0, 0), 0);
  CHECK_EQ(lcd.pixels_written(), 0);
}

TEST(st7789_other_commands_keep_window) {
  St7789 lcd;
  window(lcd, 5, 5, 6, 6);
  cmd(lcd, 0x36, {0x70});
  cmd(lcd, 0x3A, {0x05});
  pixels(lcd, {0xabcd});
  CHECK_EQ(lcd.raw(5, 6), 0xabcd);
}

TEST(st7789_view_undoes_rotate_270) {
  St7789 lcd;
  // Píxel lógico (x=7, y=5) -> memoria/direcciones (col=5, fila=239-7=232).
  window(lcd, 5, 5, 232, 232);
  pixels(lcd, {0x0f0f});
  std::vector<uint16_t> view(St7789::kSize * St7789::kSize);
  lcd.snapshot_view(view.data());
  CHECK_EQ(view[5 * St7789::kSize + 7], 0x0f0f);
}
