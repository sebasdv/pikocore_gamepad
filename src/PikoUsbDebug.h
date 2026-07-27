#pragma once

#include <stddef.h>
#include <stdint.h>

#include "PikoDebugC.h"

class PikoUsbResponse {
 public:
  PikoUsbResponse(char* buffer, size_t capacity)
      : buffer_(buffer), capacity_(capacity) {
    if (capacity_ != 0u) {
      buffer_[0] = '\0';
    }
  }

  void append(char value) {
    if (size_ + 1u >= capacity_) {
      truncated_ = true;
      return;
    }
    buffer_[size_++] = value;
    buffer_[size_] = '\0';
  }

  void append(const char* text) {
    while (*text != '\0') {
      append(*text++);
    }
  }

  void append_uint(uint32_t value) {
    char reversed[10];
    size_t digits = 0;
    do {
      reversed[digits++] = static_cast<char>('0' + (value % 10u));
      value /= 10u;
    } while (value != 0u);
    while (digits != 0u) {
      append(reversed[--digits]);
    }
  }

  const char* data() const { return buffer_; }
  size_t size() const { return size_; }
  bool truncated() const { return truncated_; }

 private:
  char* buffer_;
  size_t capacity_;
  size_t size_ = 0;
  bool truncated_ = false;
};

struct PikoDebugRuntimeState {
  uint32_t current_sample;
  uint32_t sample_count;
  uint32_t bpm;
  uint32_t beat_number;
  uint32_t selected_beat;
  uint32_t mode;
  uint32_t audio_clock_threshold;
  uint32_t sample_source_bpm;
  uint32_t stretch_q8;
  uint32_t knob_0;
  uint32_t knob_1;
  uint32_t knob_2;
  uint32_t buttons_mask;
  uint32_t external_clock_last_ticks;
  uint32_t external_clock_bpm;
  uint32_t audio_value;
  uint32_t volume_reduce;
  uint32_t distortion;
  uint32_t filter_fc;
  uint32_t noise_gate_threshold;
  uint32_t probability_direction;
  uint32_t probability_jump;
  uint32_t probability_retrigger;
  uint32_t probability_gate;
  uint32_t probability_tunnel;
  uint32_t retrigger_selection;
  uint32_t retrigger_count;
  uint32_t retrigger_max;
  uint32_t sequencer_length;
  uint32_t sequencer_step;
  bool timestretch_active;
  bool retrigger_active;
  bool muted;
  bool syncing;
  bool clock_input_midi;
  bool clock_locked;
  bool sequencer_playing;
  bool sequencer_recording;
};

enum class PikoDebugEvent : uint8_t {
  kBeat,
  kSoftSync,
  kRetriggerStart,
  kRetriggerCycle,
  kButtonChange,
  kKnobChange,
  kMidiNoteOn,
  kMidiNoteOff,
  kMidiStart,
  kMidiContinue,
  kMidiStop,
  kMidiClock,
  kExternalClock,
  kSettingsSave,
  kSettingsLoad,
  kLcdBoundsError,
  kSdError,
  kCount,
};

// Called only for rendered audio samples, not for every ~1 MHz PWM carrier
// interrupt. The returned timestamp must be passed to piko_debug_audio_end().
uint32_t piko_debug_audio_begin();
void piko_debug_audio_end(uint32_t render_start_us);

void piko_debug_publish_runtime(const PikoDebugRuntimeState& state);
void piko_debug_note_event(PikoDebugEvent event);
void piko_debug_reset_stats();
void piko_debug_append_status(PikoUsbResponse& response);
