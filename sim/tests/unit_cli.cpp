// Validación de la línea de comandos (core/cli_checks.h).
#include <cstdio>
#include <filesystem>
#include <string>
#include <vector>

#include "core/cli_checks.h"
#include "test.h"

using namespace sim;

namespace {
void write_bytes(const std::filesystem::path& path, size_t n) {
  FILE* f = std::fopen(path.string().c_str(), "wb");
  const std::vector<uint8_t> data(n, 0x42);
  if (n > 0) std::fwrite(data.data(), 1, n, f);
  std::fclose(f);
}
}  // namespace

TEST(parse_uint_ms_accepts_plain_numbers) {
  uint32_t v = 0;
  CHECK(parse_uint_ms("5000", 3600000, &v));
  CHECK_EQ(v, 5000);
  CHECK(parse_uint_ms("1", 3600000, &v));
  CHECK_EQ(v, 1);
  CHECK(parse_uint_ms("3600000", 3600000, &v));
  CHECK_EQ(v, 3600000);
  CHECK(parse_uint_ms("007", 3600000, &v));
  CHECK_EQ(v, 7);
}

TEST(parse_uint_ms_rejects_garbage) {
  uint32_t v = 123;
  CHECK(!parse_uint_ms("0", 3600000, &v));
  CHECK(!parse_uint_ms("-5", 3600000, &v));
  CHECK(!parse_uint_ms("+5", 3600000, &v));
  CHECK(!parse_uint_ms("5000abc", 3600000, &v));
  CHECK(!parse_uint_ms(" 5", 3600000, &v));
  CHECK(!parse_uint_ms("", 3600000, &v));
  CHECK(!parse_uint_ms("9999999999", 3600000, &v));
  CHECK(!parse_uint_ms("3600001", 3600000, &v));
  CHECK_EQ(v, 123);  // en error no se toca la salida
}

TEST(explicit_flash_missing_file_is_ok) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test_noflash.bin";
  std::filesystem::remove(path);
  std::string err;
  CHECK(check_explicit_flash_file(path, 4096, &err));
}

TEST(explicit_flash_right_size_is_ok) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test_okflash.bin";
  write_bytes(path, 4096);
  std::string err;
  CHECK(check_explicit_flash_file(path, 4096, &err));
  std::filesystem::remove(path);
}

TEST(explicit_flash_wrong_size_is_refused) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test_userfile.bin";
  write_bytes(path, 100);
  std::string err;
  CHECK(!check_explicit_flash_file(path, 4096, &err));
  CHECK(!err.empty());
  CHECK_EQ(std::filesystem::file_size(path), 100);  // intacto
  write_bytes(path, 0);
  CHECK(!check_explicit_flash_file(path, 4096, &err));
  std::filesystem::remove(path);
}
