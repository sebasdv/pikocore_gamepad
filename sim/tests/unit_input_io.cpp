#include <filesystem>
#include <string>
#include <vector>

#include "core/buttons.h"
#include "core/file_io.h"
#include "core/press_script.h"
#include "test.h"

using namespace sim;

TEST(buttons_pins_match_hw_header) {
  CHECK_EQ(kButtonPins[kUp], 15);
  CHECK_EQ(kButtonPins[kA], 21);
  CHECK_EQ(kButtonPins[kSelect], 19);
  CHECK_EQ(kButtonPins[kStart], 26);
  CHECK_EQ(kButtonPins[kR], 4);
}

TEST(buttons_xinput_face_by_position) {
  CHECK_EQ(map_xinput(0x8000), bit(kX));  // Xbox Y (arriba)
  CHECK_EQ(map_xinput(0x2000), bit(kA));  // Xbox B (derecha)
  CHECK_EQ(map_xinput(0x1000), bit(kB));  // Xbox A (abajo)
  CHECK_EQ(map_xinput(0x4000), bit(kY));  // Xbox X (izquierda)
}

TEST(buttons_xinput_rest) {
  CHECK_EQ(map_xinput(0x0001 | 0x0008), bit(kUp) | bit(kRight));
  CHECK_EQ(map_xinput(0x0100), bit(kL));
  CHECK_EQ(map_xinput(0x0200), bit(kR));
  CHECK_EQ(map_xinput(0x0020), bit(kSelect));
  CHECK_EQ(map_xinput(0x0010), bit(kStart));
}

TEST(buttons_keyboard) {
  CHECK_EQ(button_for_vk('W'), kX);
  CHECK_EQ(button_for_vk('S'), kB);
  CHECK_EQ(button_for_vk(0x0D), kStart);
  CHECK_EQ(button_for_vk(0x26), kUp);
  CHECK_EQ(button_for_vk('Z'), -1);
}

TEST(buttons_names) {
  CHECK_EQ(button_from_name("start"), kStart);
  CHECK_EQ(button_from_name("Up"), kUp);
  CHECK_EQ(button_from_name("foo"), -1);
  CHECK(std::string(button_name(kSelect)) == "SELECT");
}

TEST(press_parses_press_and_release) {
  std::vector<PressEvent> ev;
  std::string err;
  CHECK(parse_press_script("1500:-A,1000:A+b", &ev, &err));
  CHECK_EQ(ev.size(), 2);
  CHECK_EQ(ev[0].at_ms, 1000);
  CHECK_EQ(ev[0].press, bit(kA) | bit(kB));
  CHECK_EQ(ev[1].release, bit(kA));
}

TEST(press_rejects_garbage) {
  std::vector<PressEvent> ev;
  std::string err;
  CHECK(!parse_press_script("abc", &ev, &err));
  CHECK(!parse_press_script("100:FOO", &ev, &err));
  CHECK(!parse_press_script("x:A", &ev, &err));
  CHECK(!parse_press_script("100:", &ev, &err));
  CHECK(!parse_press_script("99999999999:A", &ev, &err));
}

TEST(press_empty_script_is_ok) {
  std::vector<PressEvent> ev;
  std::string err;
  CHECK(parse_press_script("", &ev, &err));
  CHECK(ev.empty());
}

TEST(press_apply_in_time_order) {
  std::vector<PressEvent> ev;
  std::string err;
  CHECK(parse_press_script("1000:A+B,1500:-A", &ev, &err));
  size_t next = 0;
  uint16_t m = 0;
  m = apply_press_events(ev, &next, 999, m);
  CHECK_EQ(m, 0);
  m = apply_press_events(ev, &next, 1000, m);
  CHECK_EQ(m, bit(kA) | bit(kB));
  m = apply_press_events(ev, &next, 2000, m);
  CHECK_EQ(m, bit(kB));
}

TEST(file_io_rgb565) {
  CHECK_EQ(rgb565_to_rgb888(0xFFFF), 0xFFFFFF);
  CHECK_EQ(rgb565_to_rgb888(0xF800), 0xFF0000);
  CHECK_EQ(rgb565_to_rgb888(0x0000), 0);
}

TEST(file_io_bmp_layout) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test.bmp";
  const uint16_t px[4] = {0xF800, 0x07E0, 0x001F, 0xFFFF};
  CHECK(write_bmp_rgb565(path, px, 2, 2, 1));
  std::vector<uint8_t> d;
  CHECK(read_file(path, &d));
  CHECK_EQ(d.size(), 70);  // 54 de header + 2 filas de 8 bytes (6 + padding)
  CHECK(d[0] == 'B' && d[1] == 'M');
  // BMP arranca por la fila de abajo: primer píxel = (0, 1) = azul -> B, G, R.
  CHECK_EQ(d[54], 0xff);
  CHECK_EQ(d[55], 0);
  CHECK_EQ(d[56], 0);
  std::filesystem::remove(path);
}

TEST(file_io_wav_layout) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test.wav";
  CHECK(write_wav_mono16(path, {0.0f, 1.0f, -1.0f}, 48000));
  std::vector<uint8_t> d;
  CHECK(read_file(path, &d));
  CHECK_EQ(d.size(), 50);
  CHECK(d[0] == 'R' && d[1] == 'I' && d[2] == 'F' && d[3] == 'F');
  CHECK_EQ(d[46], 0xff);  // 32767 little-endian
  CHECK_EQ(d[47], 0x7f);
  std::filesystem::remove(path);
}
