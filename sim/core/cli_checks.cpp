#include "core/cli_checks.h"

#include <system_error>

namespace sim {

bool parse_uint_ms(const std::string& text, uint32_t max, uint32_t* out) {
  // Hasta 9 dígitos entra en uint32_t sin overflow (mismo criterio que --press).
  if (text.empty() || text.size() > 9 ||
      text.find_first_not_of("0123456789") != std::string::npos) {
    return false;
  }
  const unsigned long v = std::stoul(text);
  if (v == 0 || v > max) return false;
  *out = static_cast<uint32_t>(v);
  return true;
}

bool check_explicit_flash_file(const std::filesystem::path& path, uint64_t flash_size,
                               std::string* err) {
  std::error_code ec;
  if (!std::filesystem::exists(path, ec)) return true;
  const uint64_t size = std::filesystem::file_size(path, ec);
  if (!ec && size == flash_size) return true;
  *err = "--flash: el archivo existe y no es una flash de " +
         std::to_string(flash_size / (1024 * 1024)) + " MB; no lo piso";
  return false;
}

}  // namespace sim
