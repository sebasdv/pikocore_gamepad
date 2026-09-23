#include "core/st7789.h"

namespace sim {

St7789::St7789() : gram_(static_cast<size_t>(kSize) * kSize, 0) {}

void St7789::set_dc(bool data) {
  std::lock_guard<std::mutex> lock(mutex_);
  dc_ = data;
}

void St7789::set_cs(bool level) {
  std::lock_guard<std::mutex> lock(mutex_);
  cs_low_ = !level;
}

void St7789::write(const uint8_t* bytes, size_t len) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!cs_low_) return;
  for (size_t i = 0; i < len; ++i) {
    if (dc_) {
      data(bytes[i]);
    } else {
      command(bytes[i]);
    }
  }
}

void St7789::command(uint8_t cmd) {
  cmd_ = cmd;
  param_ = 0;
  if (cmd == kRamWr) {
    x_ = xs_;
    y_ = ys_;
    have_high_ = false;
  }
}

void St7789::data(uint8_t value) {
  switch (cmd_) {
    case kCaSet:
      set_range(&xs_, &xe_, value);
      break;
    case kRaSet:
      set_range(&ys_, &ye_, value);
      break;
    case kRamWr:
      // RGB565 big-endian: primero el byte alto.
      if (!have_high_) {
        high_ = value;
        have_high_ = true;
        return;
      }
      have_high_ = false;
      store_pixel(static_cast<uint16_t>((high_ << 8) | value));
      break;
    default:
      break;
  }
}

void St7789::set_range(uint16_t* start, uint16_t* end, uint8_t value) {
  switch (param_++) {
    case 0: *start = static_cast<uint16_t>(value << 8); break;
    case 1: *start = static_cast<uint16_t>(*start | value); break;
    case 2: *end = static_cast<uint16_t>(value << 8); break;
    case 3: *end = static_cast<uint16_t>(*end | value); break;
    default: break;
  }
}

void St7789::store_pixel(uint16_t pixel) {
  // La GRAM real es de 240x320; lo que cae fuera del panel de 240x240 no se ve.
  if (x_ < kSize && y_ < kSize) gram_[static_cast<size_t>(y_) * kSize + x_] = pixel;
  ++pixels_written_;
  if (x_ >= xe_) {
    x_ = xs_;
    y_ = (y_ >= ye_) ? ys_ : static_cast<uint16_t>(y_ + 1);
  } else {
    ++x_;
  }
}

uint16_t St7789::raw(int col, int row) const {
  std::lock_guard<std::mutex> lock(mutex_);
  if (col < 0 || row < 0 || col >= kSize || row >= kSize) return 0;
  return gram_[static_cast<size_t>(row) * kSize + col];
}

void St7789::snapshot_view(uint16_t* out) const {
  std::lock_guard<std::mutex> lock(mutex_);
  for (int y = 0; y < kSize; ++y) {
    for (int x = 0; x < kSize; ++x) {
      out[static_cast<size_t>(y) * kSize + x] =
          gram_[static_cast<size_t>(kSize - 1 - x) * kSize + y];
    }
  }
}

uint32_t St7789::pixels_written() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return pixels_written_;
}

}  // namespace sim
