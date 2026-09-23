#pragma once
#include <cstdint>
#include <filesystem>
#include <string>

namespace sim {

// Entero decimal de 1 a 9 dígitos, sin signo ni espacios, en [1, max].
bool parse_uint_ms(const std::string& text, uint32_t max, uint32_t* out);

// Para un --flash explícito: false (con *err) si el archivo ya existe y su
// tamaño no es flash_size, porque FlashStore::open lo recrearía en blanco y se
// perdería lo que hubiera. Si no existe, o es una flash del tamaño justo, true.
bool check_explicit_flash_file(const std::filesystem::path& path, uint64_t flash_size,
                               std::string* err);

}  // namespace sim
