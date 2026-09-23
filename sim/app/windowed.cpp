#include "app/windowed.h"

#include <windows.h>
#include <timeapi.h>

#include <atomic>
#include <chrono>
#include <cstdio>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include "PikoAudioBank.h"
#include "core/audio_ring.h"
#include "core/bank_file.h"
#include "core/file_io.h"
#include "core/flash_store.h"
#include "core/pacing.h"
#include "platform/audio_out.h"
#include "platform/pad_input.h"
#include "platform/sim_window.h"
#include "runtime/bank_hotload.h"
#include "runtime/firmware_entry.h"
#include "runtime/machine.h"
#include "runtime/sim_io.h"

namespace {

struct Shared {
  std::mutex mutex;
  std::optional<std::vector<uint8_t>> pending_bank;  // protegido por mutex
  std::wstring pending_name;                          // protegido por mutex
  std::wstring bank_status;                           // protegido por mutex; "" = sin cargar
  std::atomic<uint32_t> sample_count{0};
  std::atomic<float> speed{0.0f};
  std::atomic<bool> quit{false};
};

std::wstring utf8_to_wide(const std::string& s) {
  if (s.empty()) return {};
  const int n = MultiByteToWideChar(CP_UTF8, 0, s.data(), static_cast<int>(s.size()), nullptr, 0);
  std::wstring w(static_cast<size_t>(n), L'\0');
  MultiByteToWideChar(CP_UTF8, 0, s.data(), static_cast<int>(s.size()), w.data(), n);
  return w;
}

std::filesystem::path default_flash_path() {
  wchar_t exe[MAX_PATH];
  GetModuleFileNameW(nullptr, exe, MAX_PATH);
  return std::filesystem::path(exe).parent_path() / L"pikocore_sim_flash.bin";
}

std::wstring loaded_status(const sim::BankCheck& check, const std::wstring& name) {
  std::wstring s = L"Banco: " + std::to_wstring(check.sample_count) + L" samples (" + name + L")";
  if (check.capacity_patched) s += L", capacidad corregida";
  return s;
}

// Corre en el hilo de emulación, entre dos run_until(): atómico respecto del firmware.
void apply_pending_bank(Shared* sh) {
  std::vector<uint8_t> blob;
  std::wstring name;
  {
    std::lock_guard<std::mutex> lock(sh->mutex);
    if (!sh->pending_bank) return;
    blob = std::move(*sh->pending_bank);
    name = sh->pending_name;
    sh->pending_bank.reset();
  }
  const sim::BankCheck check = sim::check_and_patch_bank(blob);
  if (check.ok) sim::hot_load_bank(blob);
  std::lock_guard<std::mutex> lock(sh->mutex);
  sh->bank_status = check.ok ? loaded_status(check, name)
                             : L"Banco rechazado (" + name + L"): " + utf8_to_wide(check.error);
}

void emulation_thread(Shared* sh, sim::AudioRing* ring, const sim::AudioOut* audio, bool audio_ok) {
  using clock = std::chrono::steady_clock;
  sim::Machine& m = sim::Machine::get();
  uint64_t produced = 0;
  m.dac().set_sink([&](float s) {
    ring->push(s);
    ++produced;
  });
  m.boot(&piko_firmware_main);

  // ~20 ms de emulación por delante de lo que suena (spec, "Pacing").
  constexpr uint64_t kLeadFrames = sim::kAudioRate * 20 / 1000;
  const clock::time_point wall0 = clock::now();
  clock::time_point speed_mark = wall0;
  uint64_t speed_cycles = 0;

  // Si WASAPI falla a mitad de sesión (dispositivo desconectado, etc.), el
  // ring deja de vaciarse; a partir de ese instante repacear por reloj de
  // pared para que la emulación siga corriendo a x1 en vez de congelarse
  // esperando un consumo que ya no llega.
  bool audio_lost = false;
  uint64_t produced_at_loss = 0;
  clock::time_point loss_mark{};

  while (!sh->quit) {
    apply_pending_bank(sh);
    const clock::time_point now = clock::now();
    if (audio_ok && !audio_lost && audio->failed()) {
      audio_lost = true;
      produced_at_loss = produced;
      loss_mark = now;
    }
    // Con audio se pacea por el nivel real del ring, no por frames_consumed():
    // este cuenta también el silencio que WASAPI mete en cada underrun
    // (arranque, carga en caliente), y pacear contra él dejaría esa latencia
    // acumulada para siempre, hasta el tope del ring.
    sim::PaceState pace;
    pace.audio_running = audio_ok && !audio_lost;
    pace.ring_fill = ring->size();
    pace.produced = produced;
    const auto frames_since = [now](clock::time_point t) {
      return static_cast<uint64_t>(std::chrono::duration<double>(now - t).count() *
                                   sim::kAudioRate);
    };
    if (audio_lost) {
      pace.wall_frames = produced_at_loss + frames_since(loss_mark);
    } else if (!audio_ok) {
      pace.wall_frames = frames_since(wall0);
    }
    if (sim::should_step(pace, kLeadFrames)) {
      m.run_until(m.now_cycles() + sim::kCpuHz / 1000);
    } else {
      Sleep(1);
    }
    sh->sample_count = piko_audio_sample_count();
    const double elapsed = std::chrono::duration<double>(now - speed_mark).count();
    if (elapsed >= 0.5) {
      sh->speed = static_cast<float>((m.now_cycles() - speed_cycles) /
                                     static_cast<double>(sim::kCpuHz) / elapsed);
      speed_cycles = m.now_cycles();
      speed_mark = now;
    }
  }
  // El sink captura `produced` (local de este hilo) por referencia: soltarlo
  // antes de volver, para no dejar al Dac apuntando a un hilo que ya murió.
  m.dac().set_sink({});
}

}  // namespace

int run_windowed(const Cli& cli) {
  // Si nos lanzaron con doble click, la consola es nuestra: se oculta.
  DWORD pids[2];
  if (GetConsoleProcessList(pids, 2) <= 1) FreeConsole();
  timeBeginPeriod(1);  // Sleep(1) de verdad ~1 ms, para el pacing

  Shared sh;
  std::string err;
  const std::filesystem::path flash_path = cli.flash_given ? cli.flash : default_flash_path();
  if (!sim::flash().open(flash_path, &err)) {
    MessageBoxW(nullptr, utf8_to_wide(err).c_str(), L"pikocore-sim", MB_ICONERROR);
    timeEndPeriod(1);
    return 1;
  }
  if (!cli.bank.empty()) {
    std::vector<uint8_t> blob;
    const std::wstring name = cli.bank.filename().wstring();
    if (!sim::read_file(cli.bank, &blob)) {
      sh.bank_status = L"Banco: no se pudo leer " + name;
    } else {
      const sim::BankCheck check = sim::check_and_patch_bank(blob);
      if (check.ok) {
        sim::write_bank_to_flash(blob);  // antes del boot: el firmware lo lee al arrancar
        sh.bank_status = loaded_status(check, name);
      } else {
        sh.bank_status = L"Banco rechazado (" + name + L"): " + utf8_to_wide(check.error);
      }
    }
  }

  sim::AudioRing ring(sim::kAudioRate / 2);  // 500 ms de margen
  sim::AudioOut audio;
  std::string audio_err;
  const bool audio_ok = audio.start(&ring, &audio_err);
  const std::wstring audio_err_wide = utf8_to_wide(audio_err);
  sim::PadInput pad;
  pad.start([](uint16_t mask) { sim::set_button_mask(mask); });
  std::thread emu(emulation_thread, &sh, &ring, &audio, audio_ok);

  sim::WindowHooks hooks;
  hooks.snapshot_lcd = [](uint16_t* out) { sim::Machine::get().lcd().snapshot_view(out); };
  hooks.button_mask = [] { return sim::button_mask(); };
  hooks.beat_led = [] { return sim::beat_led(); };
  hooks.backlight = [] { return sim::backlight_level(); };
  hooks.keyboard_mask = [&pad](uint16_t mask) { pad.set_keyboard_mask(mask); };
  hooks.file_dropped = [&sh](const std::filesystem::path& path) {
    std::vector<uint8_t> blob;
    const bool ok = sim::read_file(path, &blob);
    std::lock_guard<std::mutex> lock(sh.mutex);
    if (!ok) {
      sh.bank_status = L"Banco: no se pudo leer " + path.filename().wstring();
      return;
    }
    sh.pending_bank = std::move(blob);
    sh.pending_name = path.filename().wstring();
  };
  hooks.status = [&sh, &pad, &audio, audio_ok, &audio_err_wide] {
    std::wstring s = pad.connected()
                         ? L"Control XInput conectado"
                         : L"Sin control: flechas, W/A/S/D, Q/E, Enter, Backspace";
    std::wstring bank;
    {
      std::lock_guard<std::mutex> lock(sh.mutex);
      bank = sh.bank_status;
    }
    if (bank.empty()) {
      bank = sh.sample_count > 0
                 ? L"Banco: " + std::to_wstring(sh.sample_count.load()) + L" samples (en la flash)"
                 : L"Banco: ninguno (arrastrá un .pikobank)";
    }
    s += L"  ·  " + bank;
    if (audio_ok && audio.failed()) {
      s += L"  ·  Audio perdido";
    } else if (!audio_ok) {
      s += L"  ·  Sin audio (" + audio_err_wide + L")";
    } else {
      s += L"  ·  Audio WASAPI";
    }
    wchar_t speed[32];
    swprintf(speed, 32, L"  ·  x%.2f", sh.speed.load());
    return s + speed;
  };

  const int rc = sim::run_window(hooks, cli.capture, cli.exit_after_ms);
  sh.quit = true;
  emu.join();
  pad.stop();
  audio.stop();
  timeEndPeriod(1);
  return rc;
}
