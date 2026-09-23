#pragma once
#include <cstdint>
#include <filesystem>
#include <functional>
#include <vector>

namespace sim {

bool read_file(const std::filesystem::path& path, std::vector<uint8_t>* out);
// BMP de 24 bits; rgb(x, y) devuelve 0xRRGGBB, con y = 0 arriba.
bool write_bmp(const std::filesystem::path& path, int w, int h,
               const std::function<uint32_t(int x, int y)>& rgb);
// Imagen RGB565 (como la del LCD) ampliada `scale` veces.
bool write_bmp_rgb565(const std::filesystem::path& path, const uint16_t* px, int w, int h,
                      int scale);
uint32_t rgb565_to_rgb888(uint16_t p);
// WAV PCM mono de 16 bits.
bool write_wav_mono16(const std::filesystem::path& path, const std::vector<float>& samples,
                      uint32_t rate);

}  // namespace sim
