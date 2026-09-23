#include <windows.h>

#include <cstdio>
#include <string>
#include <vector>

#include "app/cli.h"
#include "app/windowed.h"
#include "core/file_io.h"
#include "core/press_script.h"
#include "core/st7789.h"
#include "runtime/headless.h"
#include "runtime/machine.h"

namespace {

int run_headless_cli(const Cli& cli) {
  sim::HeadlessOptions o;
  o.run_ms = cli.run_ms;
  o.flash_path = cli.flash;  // vacío = solo memoria
  std::string err;
  if (!check_flash_arg(cli, &err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }
  if (!cli.bank.empty() && !sim::read_file(cli.bank, &o.bank)) {
    std::fprintf(stderr, "no se pudo leer el banco\n");
    return 1;
  }
  if (!sim::parse_press_script(cli.press, &o.presses, &err)) {
    std::fprintf(stderr, "--press: %s\n", err.c_str());
    return 2;
  }
  sim::HeadlessResult r;
  if (!sim::run_headless(o, &r, &err)) {
    std::fprintf(stderr, "error: %s\n", err.c_str());
    return 1;
  }
  std::printf("pikocore-sim: %u ms virtuales en %.2f s (x%.2f)\n", o.run_ms, r.wall_seconds,
              o.run_ms / 1000.0 / r.wall_seconds);
  if (!cli.dump_lcd.empty()) {
    if (!sim::write_bmp_rgb565(cli.dump_lcd, r.lcd.data(), sim::St7789::kSize,
                               sim::St7789::kSize, 2)) {
      std::fprintf(stderr, "no se pudo escribir el BMP\n");
      return 1;
    }
    std::printf("LCD -> %s\n", narrow(cli.dump_lcd.wstring()).c_str());
  }
  if (!cli.dump_wav.empty()) {
    if (!sim::write_wav_mono16(cli.dump_wav, r.audio, sim::kAudioRate)) {
      std::fprintf(stderr, "no se pudo escribir el WAV\n");
      return 1;
    }
    std::printf("audio -> %s (%zu muestras)\n", narrow(cli.dump_wav.wstring()).c_str(),
                r.audio.size());
  }
  return 0;
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
  // Los mensajes en castellano salen en UTF-8 (/utf-8): que la consola no los
  // muestre como mojibake.
  SetConsoleOutputCP(CP_UTF8);
  Cli cli;
  std::string err;
  if (!parse_cli(argc, argv, &cli, &err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    print_usage();
    return 2;
  }
  if (cli.help) {
    print_usage();
    return 0;
  }
  if (cli.headless) return run_headless_cli(cli);
  return run_windowed(cli);
}
