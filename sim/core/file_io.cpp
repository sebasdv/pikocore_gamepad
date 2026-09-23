#include "core/file_io.h"

#include <algorithm>
#include <cstdio>

namespace sim {

namespace {
struct File {
  FILE* f = nullptr;
  ~File() {
    if (f != nullptr) std::fclose(f);
  }
};

void put16(std::vector<uint8_t>& b, uint16_t v) {
  b.push_back(static_cast<uint8_t>(v));
  b.push_back(static_cast<uint8_t>(v >> 8));
}

void put32(std::vector<uint8_t>& b, uint32_t v) {
  put16(b, static_cast<uint16_t>(v));
  put16(b, static_cast<uint16_t>(v >> 16));
}

void put_tag(std::vector<uint8_t>& b, const char* tag) {
  for (int i = 0; i < 4; ++i) b.push_back(static_cast<uint8_t>(tag[i]));
}

bool write_all(const std::filesystem::path& path, const std::vector<uint8_t>& data) {
  File file;
  file.f = _wfopen(path.c_str(), L"wb");
  if (file.f == nullptr) return false;
  return std::fwrite(data.data(), 1, data.size(), file.f) == data.size();
}
}  // namespace

bool read_file(const std::filesystem::path& path, std::vector<uint8_t>* out) {
  File file;
  file.f = _wfopen(path.c_str(), L"rb");
  if (file.f == nullptr) return false;
  _fseeki64(file.f, 0, SEEK_END);
  const long long n = _ftelli64(file.f);
  _fseeki64(file.f, 0, SEEK_SET);
  if (n < 0) return false;
  out->resize(static_cast<size_t>(n));
  return n == 0 || std::fread(out->data(), 1, out->size(), file.f) == out->size();
}

uint32_t rgb565_to_rgb888(uint16_t p) {
  const uint32_t r = ((p >> 11) & 31u) * 255u / 31u;
  const uint32_t g = ((p >> 5) & 63u) * 255u / 63u;
  const uint32_t b = (p & 31u) * 255u / 31u;
  return (r << 16) | (g << 8) | b;
}

bool write_bmp(const std::filesystem::path& path, int w, int h,
               const std::function<uint32_t(int x, int y)>& rgb) {
  const uint32_t row = (static_cast<uint32_t>(w) * 3u + 3u) & ~3u;
  const uint32_t data_size = row * static_cast<uint32_t>(h);
  std::vector<uint8_t> b;
  b.reserve(54 + data_size);
  b.push_back('B');
  b.push_back('M');
  put32(b, 54 + data_size);
  put32(b, 0);
  put32(b, 54);
  put32(b, 40);
  put32(b, static_cast<uint32_t>(w));
  put32(b, static_cast<uint32_t>(h));
  put16(b, 1);
  put16(b, 24);
  put32(b, 0);
  put32(b, data_size);
  put32(b, 2835);
  put32(b, 2835);
  put32(b, 0);
  put32(b, 0);
  for (int y = h - 1; y >= 0; --y) {  // BMP va de abajo hacia arriba
    for (int x = 0; x < w; ++x) {
      const uint32_t c = rgb(x, y);
      b.push_back(static_cast<uint8_t>(c));
      b.push_back(static_cast<uint8_t>(c >> 8));
      b.push_back(static_cast<uint8_t>(c >> 16));
    }
    for (uint32_t pad = static_cast<uint32_t>(w) * 3u; pad < row; ++pad) b.push_back(0);
  }
  return write_all(path, b);
}

bool write_bmp_rgb565(const std::filesystem::path& path, const uint16_t* px, int w, int h,
                      int scale) {
  return write_bmp(path, w * scale, h * scale, [&](int x, int y) {
    return rgb565_to_rgb888(px[static_cast<size_t>(y / scale) * w + x / scale]);
  });
}

bool write_wav_mono16(const std::filesystem::path& path, const std::vector<float>& samples,
                      uint32_t rate) {
  const uint32_t data_size = static_cast<uint32_t>(samples.size() * 2);
  std::vector<uint8_t> b;
  b.reserve(44 + data_size);
  put_tag(b, "RIFF");
  put32(b, 36 + data_size);
  put_tag(b, "WAVE");
  put_tag(b, "fmt ");
  put32(b, 16);
  put16(b, 1);  // PCM
  put16(b, 1);  // mono
  put32(b, rate);
  put32(b, rate * 2);
  put16(b, 2);
  put16(b, 16);
  put_tag(b, "data");
  put32(b, data_size);
  for (float s : samples) {
    const float c = std::clamp(s, -1.0f, 1.0f);
    put16(b, static_cast<uint16_t>(static_cast<int16_t>(c * 32767.0f)));
  }
  return write_all(path, b);
}

}  // namespace sim
