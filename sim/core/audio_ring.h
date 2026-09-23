#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace sim {

// Cola sin locks de un productor (hilo de emulación) y un consumidor (WASAPI).
class AudioRing {
 public:
  explicit AudioRing(size_t capacity) : buf_(capacity) {}

  bool push(float value) {
    const uint64_t w = write_.load(std::memory_order_relaxed);
    if (w - read_.load(std::memory_order_acquire) >= buf_.size()) return false;
    buf_[w % buf_.size()] = value;
    write_.store(w + 1, std::memory_order_release);
    return true;
  }

  size_t pop(float* out, size_t n) {
    const uint64_t r = read_.load(std::memory_order_relaxed);
    const uint64_t avail = write_.load(std::memory_order_acquire) - r;
    const size_t k = static_cast<size_t>(avail < n ? avail : n);
    for (size_t i = 0; i < k; ++i) out[i] = buf_[(r + i) % buf_.size()];
    read_.store(r + k, std::memory_order_release);
    return k;
  }

  size_t size() const { return static_cast<size_t>(write_.load() - read_.load()); }

 private:
  std::vector<float> buf_;
  std::atomic<uint64_t> write_{0};
  std::atomic<uint64_t> read_{0};
};

}  // namespace sim
