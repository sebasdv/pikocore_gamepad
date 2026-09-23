#include "core/flash_store.h"

#include <cstring>
#include <system_error>

namespace sim {

FlashStore::~FlashStore() {
  if (file_ != nullptr) std::fclose(file_);
}

bool FlashStore::open(const std::filesystem::path& path, std::string* err) {
  if (file_ != nullptr) {
    std::fclose(file_);
    file_ = nullptr;
  }
  std::memset(mem_, 0xff, size_);
  if (path.empty()) return true;

  std::error_code ec;
  const bool reuse = std::filesystem::exists(path, ec) &&
                     std::filesystem::file_size(path, ec) == size_;
  file_ = _wfopen(path.c_str(), reuse ? L"r+b" : L"w+b");
  if (file_ == nullptr) {
    if (err != nullptr) *err = "no se pudo abrir el archivo de flash";
    return false;
  }
  if (reuse) {
    if (std::fread(mem_, 1, size_, file_) != size_) {
      if (err != nullptr) *err = "no se pudo leer el archivo de flash";
      return false;
    }
  } else {
    persist(0, size_);
  }
  return true;
}

bool FlashStore::clamp(uint32_t offset, size_t* count) const {
  if (offset >= size_) return false;
  if (*count > size_ - offset) *count = size_ - offset;
  return *count > 0;
}

void FlashStore::erase(uint32_t offset, size_t count) {
  if (!clamp(offset, &count)) return;
  std::memset(mem_ + offset, 0xff, count);
  persist(offset, count);
}

void FlashStore::program(uint32_t offset, const uint8_t* data, size_t count) {
  if (!clamp(offset, &count)) return;
  for (size_t i = 0; i < count; ++i) mem_[offset + i] &= data[i];
  persist(offset, count);
}

void FlashStore::persist(uint32_t offset, size_t count) {
  if (file_ == nullptr) return;
  _fseeki64(file_, offset, SEEK_SET);
  std::fwrite(mem_ + offset, 1, count, file_);
  std::fflush(file_);
}

}  // namespace sim
