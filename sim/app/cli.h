#pragma once
#include <cstdint>
#include <filesystem>
#include <string>

struct Cli {
  std::filesystem::path bank;
  std::filesystem::path dump_lcd;
  std::filesystem::path dump_wav;
  std::filesystem::path flash;
  std::filesystem::path capture;
  bool headless = false;
  bool flash_given = false;
  bool help = false;
  uint32_t run_ms = 5000;
  uint32_t exit_after_ms = 0;
  std::string press;
};

bool parse_cli(int argc, wchar_t** argv, Cli* cli, std::string* err);
void print_usage();
// Solo para textos ASCII (flags, guion de --press); lo demás pasa a '?'.
std::string narrow(const std::wstring& text);
