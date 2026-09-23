#include <cstdio>
#include <cstring>
#include <filesystem>
#include <vector>

#include "core/bank_file.h"
#include "core/flash_store.h"
#include "synth_bank.h"
#include "test.h"

using sim::FlashStore;

namespace {
constexpr size_t kSize = 65536;
}

TEST(flash_memory_only_starts_erased) {
  std::vector<uint8_t> mem(kSize, 0);
  FlashStore f(mem.data(), mem.size());
  std::string err;
  CHECK(f.open({}, &err));
  CHECK_EQ(mem[0], 0xff);
  CHECK_EQ(mem[kSize - 1], 0xff);
}

TEST(flash_program_ands_and_erase_resets) {
  std::vector<uint8_t> mem(kSize, 0);
  FlashStore f(mem.data(), mem.size());
  std::string err;
  CHECK(f.open({}, &err));
  const uint8_t a = 0x0f, b = 0xf0;
  f.program(10, &a, 1);
  CHECK_EQ(mem[10], 0x0f);
  f.program(10, &b, 1);
  CHECK_EQ(mem[10], 0x00);
  f.erase(0, 4096);
  CHECK_EQ(mem[10], 0xff);
}

TEST(flash_out_of_range_is_clamped) {
  std::vector<uint8_t> mem(kSize, 0);
  FlashStore f(mem.data(), mem.size());
  std::string err;
  CHECK(f.open({}, &err));
  f.erase(kSize, 10);  // no debe romper nada
  const uint8_t zeros[4] = {0, 0, 0, 0};
  f.program(kSize - 2, zeros, 4);
  CHECK_EQ(mem[kSize - 2], 0);
  CHECK_EQ(mem[kSize - 1], 0);
}

TEST(flash_persists_to_file) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test_flash.bin";
  std::filesystem::remove(path);
  std::string err;
  {
    std::vector<uint8_t> mem(kSize);
    FlashStore f(mem.data(), mem.size());
    CHECK(f.open(path, &err));
    const uint8_t d[3] = {1, 2, 3};
    f.program(1000, d, 3);
  }
  {
    std::vector<uint8_t> mem(kSize, 0);
    FlashStore f(mem.data(), mem.size());
    CHECK(f.open(path, &err));
    CHECK_EQ(mem[1000], 1);
    CHECK_EQ(mem[1002], 3);
    CHECK_EQ(mem[999], 0xff);
  }
  std::filesystem::remove(path);
}

TEST(flash_replaces_file_of_wrong_size) {
  const auto path = std::filesystem::temp_directory_path() / "pikocore_sim_test_flash_bad.bin";
  {
    FILE* junk = _wfopen(path.c_str(), L"wb");
    const uint8_t zeros[10] = {};
    std::fwrite(zeros, 1, sizeof(zeros), junk);
    std::fclose(junk);
  }
  std::string err;
  {
    std::vector<uint8_t> mem(kSize, 0);
    FlashStore f(mem.data(), mem.size());
    CHECK(f.open(path, &err));
    CHECK_EQ(mem[0], 0xff);
  }
  CHECK_EQ(std::filesystem::file_size(path), kSize);
  std::filesystem::remove(path);
}

TEST(bank_accepts_synth_bank) {
  std::vector<uint8_t> b = make_synth_bank(3);
  const sim::BankCheck c = sim::check_and_patch_bank(b);
  CHECK(c.ok);
  CHECK_EQ(c.sample_count, 3);
  CHECK(!c.capacity_patched);
}

TEST(bank_rejects_bad_magic) {
  std::vector<uint8_t> b = make_synth_bank(1);
  b[0] ^= 0xff;
  const sim::BankCheck c = sim::check_and_patch_bank(b);
  CHECK(!c.ok);
  CHECK(!c.error.empty());
}

TEST(bank_rejects_truncated_file) {
  std::vector<uint8_t> b = make_synth_bank(1);
  b.pop_back();
  CHECK(!sim::check_and_patch_bank(b).ok);
}

TEST(bank_rejects_sample_past_end) {
  std::vector<uint8_t> b = make_synth_bank(1);
  const uint32_t too_long = 48001;  // frame_count del sample 0 (offset 32 + 4)
  std::memcpy(b.data() + 36, &too_long, sizeof(too_long));
  CHECK(!sim::check_and_patch_bank(b).ok);
}

TEST(bank_patches_sd_capacity) {
  std::vector<uint8_t> b = make_synth_bank(1);
  const uint32_t sd_capacity = 16u * 1024u * 1024u;  // lo que escribe el loader web
  std::memcpy(b.data() + 24, &sd_capacity, sizeof(sd_capacity));
  const sim::BankCheck c = sim::check_and_patch_bank(b);
  CHECK(c.ok);
  CHECK(c.capacity_patched);
  uint32_t patched = 0;
  std::memcpy(&patched, b.data() + 24, sizeof(patched));
  CHECK_EQ(patched, sim::device_audio_capacity());
}
