#include "app/cli.h"

#include <cstdio>

#include "core/cli_checks.h"
#include "core/flash_store.h"
#include "runtime/sim_io.h"

namespace {
// Tope de --run-ms y --exit-after-ms: una hora.
constexpr uint32_t kMaxMs = 3600000;
}  // namespace

std::string narrow(const std::wstring& text) {
  std::string out;
  for (wchar_t c : text) out.push_back(c < 128 ? static_cast<char>(c) : '?');
  return out;
}

void print_usage() {
  std::fprintf(stderr,
               "uso: pikocore_sim [banco.pikobank] [opciones]\n"
               "  --bank ARCHIVO        banco .pikobank a cargar al arrancar\n"
               "  --flash ARCHIVO       flash persistente (default: pikocore_sim_flash.bin\n"
               "                        junto al .exe; con --headless, solo en memoria)\n"
               "  --headless            sin ventana ni audio, lo más rápido posible\n"
               "  --run-ms N            (headless) ms virtuales a correr (default 5000)\n"
               "  --press GUION         (headless) botones, ej. \"6000:A+B,6200:-A\"\n"
               "  --dump-lcd ARCHIVO    (headless) guarda la pantalla final como BMP\n"
               "  --dump-wav ARCHIVO    (headless) guarda el audio como WAV\n"
               "  --capture ARCHIVO     (ventana) guarda la ventana como BMP al salir\n"
               "  --exit-after-ms N     (ventana) se cierra sola después de N ms\n"
               "botones: UP DOWN LEFT RIGHT A B X Y L R SELECT START\n");
}

bool parse_cli(int argc, wchar_t** argv, Cli* cli, std::string* err) {
  for (int i = 1; i < argc; ++i) {
    const std::wstring arg = argv[i];
    const bool takes_value = arg == L"--bank" || arg == L"--flash" || arg == L"--run-ms" ||
                             arg == L"--press" || arg == L"--dump-lcd" ||
                             arg == L"--dump-wav" || arg == L"--capture" ||
                             arg == L"--exit-after-ms";
    if (takes_value && i + 1 >= argc) {
      *err = "falta el valor de " + narrow(arg);
      return false;
    }
    if (arg == L"--help" || arg == L"-h") {
      cli->help = true;
    } else if (arg == L"--headless") {
      cli->headless = true;
    } else if (arg == L"--bank") {
      cli->bank = argv[++i];
    } else if (arg == L"--flash") {
      cli->flash = argv[++i];
      cli->flash_given = true;
    } else if (arg == L"--run-ms") {
      if (!sim::parse_uint_ms(narrow(argv[++i]), kMaxMs, &cli->run_ms)) {
        *err = "--run-ms tiene que ser un entero entre 1 y 3600000 (ms)";
        return false;
      }
    } else if (arg == L"--press") {
      cli->press = narrow(argv[++i]);
    } else if (arg == L"--dump-lcd") {
      cli->dump_lcd = argv[++i];
    } else if (arg == L"--dump-wav") {
      cli->dump_wav = argv[++i];
    } else if (arg == L"--capture") {
      cli->capture = argv[++i];
    } else if (arg == L"--exit-after-ms") {
      if (!sim::parse_uint_ms(narrow(argv[++i]), kMaxMs, &cli->exit_after_ms)) {
        *err = "--exit-after-ms tiene que ser un entero entre 1 y 3600000 (ms)";
        return false;
      }
    } else if (!arg.empty() && arg[0] == L'-') {
      *err = "opción desconocida: " + narrow(arg);
      return false;
    } else {
      cli->bank = arg;
    }
  }
  return true;
}

bool check_flash_arg(const Cli& cli, std::string* err) {
  // El default (junto al .exe) conserva el comportamiento de siempre: si no
  // tiene el tamaño justo se recrea. Un --flash explícito podría ser cualquier
  // archivo del usuario, y FlashStore::open lo pisaría.
  if (!cli.flash_given) return true;
  return sim::check_explicit_flash_file(cli.flash, sim::flash().size(), err);
}
