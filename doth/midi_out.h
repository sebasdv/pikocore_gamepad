#ifdef __cplusplus
extern "C" {
#endif

#ifndef MIDIOUT_LIB
#define MIDIOUT_LIB 1

typedef struct MidiOut {
  uint8_t channel : 7;
  uint8_t monophonic : 1;
  int8_t last;
} MidiOut;

MidiOut *MidiOut_malloc(uint8_t channel, bool monophonic) {
  MidiOut *self = (MidiOut *)malloc(sizeof(MidiOut));
  self->channel = channel;
  self->monophonic = monophonic;
  self->last = -1;
  return self;
}

void MidiOut_free(MidiOut *self) { free(self); }

// One 3-byte channel message to every MIDI OUT this build has.
static inline void MidiOut_send(const uint8_t msg[3]) {
#if CFG_TUD_MIDI
  tud_midi_n_stream_write(0, 0, msg, 3);
#endif
#if PIKO_GAMEPAD
  // DIN MIDI OUT: UART0 -> LVC1G17 -> jack (main.cpp sets it up). Called
  // from the audio ISR, so it never blocks. ponytail: a byte is dropped only
  // with 32 already queued (10 messages, ~10 ms); this traffic never gets
  // there -- add a ring buffer drained from the main loop if retrigs do.
  for (int i = 0; i < 3; i++) {
    if (uart_is_writable(uart0)) uart_get_hw(uart0)->dr = msg[i];
  }
#endif
  (void)msg;
}

void MidiOut_on(MidiOut *self, uint8_t note, uint8_t velocity) {
  uint8_t msg[3];
  if (self->monophonic && self->last != -1) {
    msg[0] = 0x80 | (self->channel & 0x0F);
    msg[1] = self->last;
    msg[2] = 0;
    MidiOut_send(msg);
  }
  msg[0] = 0x90 | (self->channel & 0x0F);
  msg[1] = note;
  msg[2] = velocity;
  MidiOut_send(msg);
  self->last = note;
}

void MidiOut_off(MidiOut *self, uint8_t note) {
  uint8_t msg[3];
  msg[0] = 0x80 | (self->channel & 0x0F);
  msg[1] = note;
  msg[2] = 0;
  MidiOut_send(msg);
  if (self->last == note) {
    self->last = -1;
  }
}

#endif
#ifdef __cplusplus
}
#endif
