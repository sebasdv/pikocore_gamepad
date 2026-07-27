#include "PikoUsbDebug.h"

#include <array>
#include <atomic>

#include "PikoAudioBank.h"
#include "pico/stdlib.h"

namespace {

constexpr uint32_t kTelemetryPublishInterval = 64u;
constexpr uint32_t kAudioSampleRateHz = PIKO_BANK_SAMPLE_RATE;
constexpr uint32_t kAudioBudgetUsX1000 =
    (1000000000u + kAudioSampleRateHz / 2u) / kAudioSampleRateHz;
constexpr uint32_t kAudioBudgetUs =
    (1000000u + kAudioSampleRateHz - 1u) / kAudioSampleRateHz;
constexpr size_t kEventCount =
    static_cast<size_t>(PikoDebugEvent::kCount);

#if PICO_RP2350
static_assert(std::atomic<uint32_t>::is_always_lock_free,
              "RP2350 debug telemetry requires lock-free 32-bit atomics");
#endif

struct AudioTelemetry {
  std::atomic<uint32_t> frames{0};
  std::atomic<uint32_t> render_total_us{0};
  std::atomic<uint32_t> render_last_us{0};
  std::atomic<uint32_t> render_max_us{0};
  std::atomic<uint32_t> render_over_budget{0};
  std::atomic<uint32_t> interval_last_us{0};
  std::atomic<uint32_t> interval_max_us{0};
  std::atomic<uint32_t> reset_generation{0};
};

struct LocalAudioTelemetry {
  uint32_t frames = 0;
  uint32_t render_total_us = 0;
  uint32_t render_last_us = 0;
  uint32_t render_max_us = 0;
  uint32_t render_over_budget = 0;
  uint32_t interval_last_us = 0;
  uint32_t interval_max_us = 0;
  uint32_t previous_render_start_us = 0;
  uint32_t reset_generation = 0;
};

struct RuntimeTelemetry {
  std::atomic<uint32_t> current_sample{0};
  std::atomic<uint32_t> sample_count{0};
  std::atomic<uint32_t> bpm{0};
  std::atomic<uint32_t> beat_number{0};
  std::atomic<uint32_t> selected_beat{0};
  std::atomic<uint32_t> mode{0};
  std::atomic<uint32_t> audio_clock_threshold{0};
  std::atomic<uint32_t> sample_source_bpm{0};
  std::atomic<uint32_t> stretch_q8{0};
  std::atomic<uint32_t> knob_0{0};
  std::atomic<uint32_t> knob_1{0};
  std::atomic<uint32_t> knob_2{0};
  std::atomic<uint32_t> buttons_mask{0};
  std::atomic<uint32_t> external_clock_last_ticks{0};
  std::atomic<uint32_t> external_clock_bpm{0};
  std::atomic<uint32_t> audio_value{0};
  std::atomic<uint32_t> volume_reduce{0};
  std::atomic<uint32_t> distortion{0};
  std::atomic<uint32_t> filter_fc{0};
  std::atomic<uint32_t> noise_gate_threshold{0};
  std::atomic<uint32_t> probability_direction{0};
  std::atomic<uint32_t> probability_jump{0};
  std::atomic<uint32_t> probability_retrigger{0};
  std::atomic<uint32_t> probability_gate{0};
  std::atomic<uint32_t> probability_tunnel{0};
  std::atomic<uint32_t> retrigger_selection{0};
  std::atomic<uint32_t> retrigger_count{0};
  std::atomic<uint32_t> retrigger_max{0};
  std::atomic<uint32_t> sequencer_length{0};
  std::atomic<uint32_t> sequencer_step{0};
  std::atomic<uint32_t> timestretch_active{0};
  std::atomic<uint32_t> retrigger_active{0};
  std::atomic<uint32_t> muted{0};
  std::atomic<uint32_t> syncing{0};
  std::atomic<uint32_t> clock_input_midi{0};
  std::atomic<uint32_t> clock_locked{0};
  std::atomic<uint32_t> sequencer_playing{0};
  std::atomic<uint32_t> sequencer_recording{0};
};

AudioTelemetry g_audio;
LocalAudioTelemetry g_audio_local;
RuntimeTelemetry g_runtime;
std::array<std::atomic<uint32_t>, kEventCount> g_events{};

void publish_audio_telemetry() {
  g_audio.frames.store(g_audio_local.frames, std::memory_order_relaxed);
  g_audio.render_total_us.store(g_audio_local.render_total_us,
                                std::memory_order_relaxed);
  g_audio.render_last_us.store(g_audio_local.render_last_us,
                               std::memory_order_relaxed);
  g_audio.render_max_us.store(g_audio_local.render_max_us,
                              std::memory_order_relaxed);
  g_audio.render_over_budget.store(g_audio_local.render_over_budget,
                                   std::memory_order_relaxed);
  g_audio.interval_last_us.store(g_audio_local.interval_last_us,
                                 std::memory_order_relaxed);
  g_audio.interval_max_us.store(g_audio_local.interval_max_us,
                                std::memory_order_relaxed);
}

void append_field(PikoUsbResponse& response, const char* name, uint32_t value) {
  response.append(' ');
  response.append(name);
  response.append('=');
  response.append_uint(value);
}

uint32_t event_count(PikoDebugEvent event) {
  return g_events[static_cast<size_t>(event)].load(std::memory_order_relaxed);
}

}  // namespace

uint32_t piko_debug_audio_begin() {
  const uint32_t reset_generation =
      g_audio.reset_generation.load(std::memory_order_relaxed);
  if (g_audio_local.reset_generation != reset_generation) {
    g_audio_local = {};
    g_audio_local.reset_generation = reset_generation;
    publish_audio_telemetry();
  }

  const uint32_t now_us = time_us_32();
  if (g_audio_local.previous_render_start_us != 0u) {
    const uint32_t interval_us =
        now_us - g_audio_local.previous_render_start_us;
    g_audio_local.interval_last_us = interval_us;
    if (interval_us > g_audio_local.interval_max_us) {
      g_audio_local.interval_max_us = interval_us;
    }
  }
  g_audio_local.previous_render_start_us = now_us;
  return now_us;
}

void piko_debug_audio_end(uint32_t render_start_us) {
  const uint32_t elapsed_us = time_us_32() - render_start_us;
  ++g_audio_local.frames;
  g_audio_local.render_total_us += elapsed_us;
  g_audio_local.render_last_us = elapsed_us;
  if (elapsed_us > g_audio_local.render_max_us) {
    g_audio_local.render_max_us = elapsed_us;
  }
  if (elapsed_us >= kAudioBudgetUs) {
    ++g_audio_local.render_over_budget;
  }
  if ((g_audio_local.frames % kTelemetryPublishInterval) == 0u) {
    publish_audio_telemetry();
  }
}

void piko_debug_publish_runtime(const PikoDebugRuntimeState& state) {
  g_runtime.current_sample.store(state.current_sample,
                                 std::memory_order_relaxed);
  g_runtime.sample_count.store(state.sample_count, std::memory_order_relaxed);
  g_runtime.bpm.store(state.bpm, std::memory_order_relaxed);
  g_runtime.beat_number.store(state.beat_number, std::memory_order_relaxed);
  g_runtime.selected_beat.store(state.selected_beat,
                                std::memory_order_relaxed);
  g_runtime.mode.store(state.mode, std::memory_order_relaxed);
  g_runtime.audio_clock_threshold.store(state.audio_clock_threshold,
                                        std::memory_order_relaxed);
  g_runtime.sample_source_bpm.store(state.sample_source_bpm,
                                    std::memory_order_relaxed);
  g_runtime.stretch_q8.store(state.stretch_q8, std::memory_order_relaxed);
  g_runtime.knob_0.store(state.knob_0, std::memory_order_relaxed);
  g_runtime.knob_1.store(state.knob_1, std::memory_order_relaxed);
  g_runtime.knob_2.store(state.knob_2, std::memory_order_relaxed);
  g_runtime.buttons_mask.store(state.buttons_mask, std::memory_order_relaxed);
  g_runtime.external_clock_last_ticks.store(
      state.external_clock_last_ticks, std::memory_order_relaxed);
  g_runtime.external_clock_bpm.store(state.external_clock_bpm,
                                     std::memory_order_relaxed);
  g_runtime.audio_value.store(state.audio_value, std::memory_order_relaxed);
  g_runtime.volume_reduce.store(state.volume_reduce,
                                std::memory_order_relaxed);
  g_runtime.distortion.store(state.distortion, std::memory_order_relaxed);
  g_runtime.filter_fc.store(state.filter_fc, std::memory_order_relaxed);
  g_runtime.noise_gate_threshold.store(state.noise_gate_threshold,
                                       std::memory_order_relaxed);
  g_runtime.probability_direction.store(state.probability_direction,
                                        std::memory_order_relaxed);
  g_runtime.probability_jump.store(state.probability_jump,
                                   std::memory_order_relaxed);
  g_runtime.probability_retrigger.store(state.probability_retrigger,
                                        std::memory_order_relaxed);
  g_runtime.probability_gate.store(state.probability_gate,
                                   std::memory_order_relaxed);
  g_runtime.probability_tunnel.store(state.probability_tunnel,
                                     std::memory_order_relaxed);
  g_runtime.retrigger_selection.store(state.retrigger_selection,
                                      std::memory_order_relaxed);
  g_runtime.retrigger_count.store(state.retrigger_count,
                                  std::memory_order_relaxed);
  g_runtime.retrigger_max.store(state.retrigger_max,
                                std::memory_order_relaxed);
  g_runtime.sequencer_length.store(state.sequencer_length,
                                   std::memory_order_relaxed);
  g_runtime.sequencer_step.store(state.sequencer_step,
                                 std::memory_order_relaxed);
  g_runtime.timestretch_active.store(state.timestretch_active ? 1u : 0u,
                                     std::memory_order_relaxed);
  g_runtime.retrigger_active.store(state.retrigger_active ? 1u : 0u,
                                   std::memory_order_relaxed);
  g_runtime.muted.store(state.muted ? 1u : 0u, std::memory_order_relaxed);
  g_runtime.syncing.store(state.syncing ? 1u : 0u,
                          std::memory_order_relaxed);
  g_runtime.clock_input_midi.store(state.clock_input_midi ? 1u : 0u,
                                   std::memory_order_relaxed);
  g_runtime.clock_locked.store(state.clock_locked ? 1u : 0u,
                               std::memory_order_relaxed);
  g_runtime.sequencer_playing.store(state.sequencer_playing ? 1u : 0u,
                                    std::memory_order_relaxed);
  g_runtime.sequencer_recording.store(state.sequencer_recording ? 1u : 0u,
                                      std::memory_order_relaxed);
}

void piko_debug_note_event(PikoDebugEvent event) {
  const size_t index = static_cast<size_t>(event);
  if (index < g_events.size()) {
    g_events[index].fetch_add(1u, std::memory_order_relaxed);
  }
}

void piko_debug_reset_stats() {
  g_audio.frames.store(0u, std::memory_order_relaxed);
  g_audio.render_total_us.store(0u, std::memory_order_relaxed);
  g_audio.render_last_us.store(0u, std::memory_order_relaxed);
  g_audio.render_max_us.store(0u, std::memory_order_relaxed);
  g_audio.render_over_budget.store(0u, std::memory_order_relaxed);
  g_audio.interval_last_us.store(0u, std::memory_order_relaxed);
  g_audio.interval_max_us.store(0u, std::memory_order_relaxed);
  for (auto& counter : g_events) {
    counter.store(0u, std::memory_order_relaxed);
  }
  g_audio.reset_generation.fetch_add(1u, std::memory_order_release);
}

void piko_debug_append_status(PikoUsbResponse& response) {
  response.append("OK status");
  append_field(response, "uptime_ms", to_ms_since_boot(get_absolute_time()));
  append_field(response, "bank_valid", piko_audio_bank_valid() ? 1u : 0u);
  append_field(response, "bank_mutating",
               piko_audio_bank_mutating() ? 1u : 0u);
  append_field(response, "audio_bytes", piko_audio_audio_bytes());
  append_field(response, "frames",
               g_audio.frames.load(std::memory_order_relaxed));
  append_field(response, "render_total_us",
               g_audio.render_total_us.load(std::memory_order_relaxed));
  append_field(response, "render_last_us",
               g_audio.render_last_us.load(std::memory_order_relaxed));
  append_field(response, "render_max_us",
               g_audio.render_max_us.load(std::memory_order_relaxed));
  append_field(response, "render_over_budget",
               g_audio.render_over_budget.load(std::memory_order_relaxed));
  append_field(response, "interval_last_us",
               g_audio.interval_last_us.load(std::memory_order_relaxed));
  append_field(response, "interval_max_us",
               g_audio.interval_max_us.load(std::memory_order_relaxed));
  append_field(response, "sample_rate_hz", kAudioSampleRateHz);
  append_field(response, "budget_us_x1000", kAudioBudgetUsX1000);
  append_field(response, "sample",
               g_runtime.current_sample.load(std::memory_order_relaxed));
  append_field(response, "sample_count",
               g_runtime.sample_count.load(std::memory_order_relaxed));
  append_field(response, "bpm",
               g_runtime.bpm.load(std::memory_order_relaxed));
  append_field(response, "beat",
               g_runtime.beat_number.load(std::memory_order_relaxed));
  append_field(response, "selected_beat",
               g_runtime.selected_beat.load(std::memory_order_relaxed));
  append_field(response, "mode",
               g_runtime.mode.load(std::memory_order_relaxed));
  append_field(response, "audio_clk_thresh",
               g_runtime.audio_clock_threshold.load(std::memory_order_relaxed));
  append_field(response, "source_bpm",
               g_runtime.sample_source_bpm.load(std::memory_order_relaxed));
  append_field(response, "stretch_q8",
               g_runtime.stretch_q8.load(std::memory_order_relaxed));
  append_field(response, "knob_0",
               g_runtime.knob_0.load(std::memory_order_relaxed));
  append_field(response, "knob_1",
               g_runtime.knob_1.load(std::memory_order_relaxed));
  append_field(response, "knob_2",
               g_runtime.knob_2.load(std::memory_order_relaxed));
  append_field(response, "buttons",
               g_runtime.buttons_mask.load(std::memory_order_relaxed));
  append_field(response, "clock_last_ticks",
               g_runtime.external_clock_last_ticks.load(
                   std::memory_order_relaxed));
  append_field(response, "clock_bpm",
               g_runtime.external_clock_bpm.load(std::memory_order_relaxed));
  append_field(response, "audio_value",
               g_runtime.audio_value.load(std::memory_order_relaxed));
  append_field(response, "volume_reduce",
               g_runtime.volume_reduce.load(std::memory_order_relaxed));
  append_field(response, "distortion",
               g_runtime.distortion.load(std::memory_order_relaxed));
  append_field(response, "filter_fc",
               g_runtime.filter_fc.load(std::memory_order_relaxed));
  append_field(response, "gate_threshold",
               g_runtime.noise_gate_threshold.load(std::memory_order_relaxed));
  append_field(response, "prob_direction",
               g_runtime.probability_direction.load(
                   std::memory_order_relaxed));
  append_field(response, "prob_jump",
               g_runtime.probability_jump.load(std::memory_order_relaxed));
  append_field(response, "prob_retrig",
               g_runtime.probability_retrigger.load(
                   std::memory_order_relaxed));
  append_field(response, "prob_gate",
               g_runtime.probability_gate.load(std::memory_order_relaxed));
  append_field(response, "prob_tunnel",
               g_runtime.probability_tunnel.load(std::memory_order_relaxed));
  append_field(response, "retrig_selection",
               g_runtime.retrigger_selection.load(std::memory_order_relaxed));
  append_field(response, "retrig_count",
               g_runtime.retrigger_count.load(std::memory_order_relaxed));
  append_field(response, "retrig_max",
               g_runtime.retrigger_max.load(std::memory_order_relaxed));
  append_field(response, "sequencer_length",
               g_runtime.sequencer_length.load(std::memory_order_relaxed));
  append_field(response, "sequencer_step",
               g_runtime.sequencer_step.load(std::memory_order_relaxed));
  append_field(response, "timestretch",
               g_runtime.timestretch_active.load(std::memory_order_relaxed));
  append_field(response, "retrigger",
               g_runtime.retrigger_active.load(std::memory_order_relaxed));
  append_field(response, "muted",
               g_runtime.muted.load(std::memory_order_relaxed));
  append_field(response, "syncing",
               g_runtime.syncing.load(std::memory_order_relaxed));
  append_field(response, "clock_midi",
               g_runtime.clock_input_midi.load(std::memory_order_relaxed));
  append_field(response, "clock_locked",
               g_runtime.clock_locked.load(std::memory_order_relaxed));
  append_field(response, "sequencer_playing",
               g_runtime.sequencer_playing.load(std::memory_order_relaxed));
  append_field(response, "sequencer_recording",
               g_runtime.sequencer_recording.load(std::memory_order_relaxed));
  append_field(response, "beats", event_count(PikoDebugEvent::kBeat));
  append_field(response, "soft_syncs",
               event_count(PikoDebugEvent::kSoftSync));
  append_field(response, "retrig_starts",
               event_count(PikoDebugEvent::kRetriggerStart));
  append_field(response, "retrig_cycles",
               event_count(PikoDebugEvent::kRetriggerCycle));
  append_field(response, "button_changes",
               event_count(PikoDebugEvent::kButtonChange));
  append_field(response, "knob_changes",
               event_count(PikoDebugEvent::kKnobChange));
  append_field(response, "midi_note_on",
               event_count(PikoDebugEvent::kMidiNoteOn));
  append_field(response, "midi_note_off",
               event_count(PikoDebugEvent::kMidiNoteOff));
  append_field(response, "midi_start",
               event_count(PikoDebugEvent::kMidiStart));
  append_field(response, "midi_continue",
               event_count(PikoDebugEvent::kMidiContinue));
  append_field(response, "midi_stop",
               event_count(PikoDebugEvent::kMidiStop));
  append_field(response, "midi_clock",
               event_count(PikoDebugEvent::kMidiClock));
  append_field(response, "clock_edges",
               event_count(PikoDebugEvent::kExternalClock));
  append_field(response, "settings_saves",
               event_count(PikoDebugEvent::kSettingsSave));
  append_field(response, "settings_loads",
               event_count(PikoDebugEvent::kSettingsLoad));
  append_field(response, "lcd_bounds_errors",
               event_count(PikoDebugEvent::kLcdBoundsError));
  append_field(response, "sd_errors",
               event_count(PikoDebugEvent::kSdError));
  response.append('\n');
}

extern "C" void piko_debug_note_lcd_bounds_error(void) {
  piko_debug_note_event(PikoDebugEvent::kLcdBoundsError);
}

// The vendored FatFS driver deliberately exposes weak output callbacks. Keep
// them silent and retain only a count that can be requested over USB.
extern "C" void put_out_error_message(const char* message) {
  (void)message;
  piko_debug_note_event(PikoDebugEvent::kSdError);
}

extern "C" void put_out_info_message(const char* message) { (void)message; }

extern "C" void put_out_debug_message(const char* message) { (void)message; }

extern "C" int error_message_printf(const char* function, int line,
                                    const char* format, ...) {
  (void)function;
  (void)line;
  (void)format;
  piko_debug_note_event(PikoDebugEvent::kSdError);
  return 0;
}

extern "C" int error_message_printf_plain(const char* format, ...) {
  (void)format;
  piko_debug_note_event(PikoDebugEvent::kSdError);
  return 0;
}

extern "C" int info_message_printf(const char* format, ...) {
  (void)format;
  return 0;
}

extern "C" int debug_message_printf(const char* function, int line,
                                    const char* format, ...) {
  (void)function;
  (void)line;
  (void)format;
  return 0;
}
