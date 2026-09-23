#pragma once
// Sustituto del header que pioasm genera a partir de doth/onewiremidi.pio
// (build-gamepi/onewiremidi.pio.h). El simulador no emula la recepción MIDI de
// un cable: el programa se "carga" pero nunca corre.
#include "hardware/pio.h"

#define midi_rx_wrap_target 0
#define midi_rx_wrap 7

static const uint16_t midi_rx_program_instructions[] = {
    0x2020, 0x20a0, 0xed27, 0xbd42, 0x4001, 0x0043, 0x8000, 0x0000};

static const struct pio_program midi_rx_program = {midi_rx_program_instructions, 8, -1, 1};

static inline pio_sm_config midi_rx_program_get_default_config(uint offset) {
  pio_sm_config c = pio_get_default_sm_config();
  sm_config_set_wrap(&c, offset + midi_rx_wrap_target, offset + midi_rx_wrap);
  return c;
}
