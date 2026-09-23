#pragma once
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <vector>

namespace sim {

// Emulador mínimo del controlador ST7789 del LCD 1.3" del GamePi13. Recibe los
// bytes de SPI tal como los manda src/gamepi13/lcd/LCD_1in3.c (DC en bajo =
// comando, en alto = dato; solo con CS en bajo) y arma la GRAM en espacio de
// direcciones: columna = CASET, fila = RASET. Solo modela CASET, RASET y
// RAMWR; el resto de los comandos se ignora.
// Thread-safe: la emulación escribe y la ventana lee desde otro hilo.
class St7789 {
 public:
  static constexpr int kSize = 240;

  St7789();
  void set_dc(bool data);
  void set_cs(bool level);  // nivel del pin; activo en bajo
  void write(const uint8_t* bytes, size_t len);

  // Píxel RGB565 en espacio de direcciones del controlador.
  uint16_t raw(int col, int row) const;
  // Imagen tal como se ve en el GamePi13: 240x240, fila por fila. ui.cpp
  // dibuja en ROTATE_270 y flush() copia su memoria al espacio de direcciones,
  // así que vista(x, y) = raw(col = y, fila = 239 - x).
  void snapshot_view(uint16_t* out) const;
  uint32_t pixels_written() const;

 private:
  static constexpr uint8_t kCaSet = 0x2A;
  static constexpr uint8_t kRaSet = 0x2B;
  static constexpr uint8_t kRamWr = 0x2C;

  void command(uint8_t cmd);
  void data(uint8_t value);
  void set_range(uint16_t* start, uint16_t* end, uint8_t value);
  void store_pixel(uint16_t pixel);

  mutable std::mutex mutex_;
  std::vector<uint16_t> gram_;
  bool dc_ = false;
  bool cs_low_ = false;
  uint8_t cmd_ = 0;
  int param_ = 0;
  uint16_t xs_ = 0, xe_ = kSize - 1, ys_ = 0, ye_ = kSize - 1;
  uint16_t x_ = 0, y_ = 0;
  bool have_high_ = false;
  uint8_t high_ = 0;
  uint32_t pixels_written_ = 0;
};

}  // namespace sim
