#pragma once
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <string>

namespace sim {

// Flash NOR simulada sobre un buffer en memoria, opcionalmente respaldada en un
// archivo del mismo tamaño. Borrar pone 0xFF; programar hace AND bit a bit,
// como el chip real, que solo puede bajar bits a 0.
class FlashStore {
 public:
  FlashStore(uint8_t* mem, size_t size) : mem_(mem), size_(size) {}
  ~FlashStore();
  FlashStore(const FlashStore&) = delete;
  FlashStore& operator=(const FlashStore&) = delete;

  // path vacío = solo memoria. Si el archivo no existe o tiene otro tamaño se
  // recrea en blanco (0xFF).
  bool open(const std::filesystem::path& path, std::string* err);
  void erase(uint32_t offset, size_t count);
  void program(uint32_t offset, const uint8_t* data, size_t count);
  size_t size() const { return size_; }

 private:
  bool clamp(uint32_t offset, size_t* count) const;
  void persist(uint32_t offset, size_t count);

  uint8_t* mem_;
  size_t size_;
  FILE* file_ = nullptr;
};

}  // namespace sim
