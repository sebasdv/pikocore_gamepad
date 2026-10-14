#pragma once
// I2S output to the PCM5102A on the pikocore_gamepad carrier PCB.
//
// The audio engine (pwm_interrupt_handler in main.cpp) was written for a PWM
// pin: it ticks at ~992 kHz off a PWM slice, and every time it has a new
// 8-bit sample it writes the level -- at a VARIABLE rate, because pitch is
// done by changing how many ticks go by between samples. The PWM pin simply
// holds the last level until the next write.
//
// This keeps that contract exactly. The engine still ticks off a PWM slice
// (one with no GPIO mapped to it, see GAMEPI_AUDIO_TICK_SLICE) and each new
// sample is stored in gamepad_i2s_word. A DMA channel in ENDLESS mode, paced
// by the PIO TX DREQ, copies that one word into the I2S FIFO once per frame
// at a fixed GAMEPI_I2S_HZ -- i.e. the DAC zero-order-holds the engine's
// output the same way the PWM pin did. No ring buffer, no underruns: the DMA
// keeps feeding the last sample even while interrupts are off (flash writes).
//
// ponytail: 8-bit engine output left-shifted into a 16-bit DAC. Add dither
// or a 16-bit engine path if the DAC ever makes the 8-bit floor audible.
#include <stdint.h>

#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "hardware/pio.h"
#include "hw_gamepi13.h"
#include "i2s.pio.h"

static volatile uint32_t gamepad_i2s_word = 0;  // {right:16, left:16}, mono

// 8-bit unsigned (128 = silence), same value the PWM path wrote.
static inline void gamepad_i2s_write(uint8_t v) {
  const uint16_t s = (uint16_t)(((int)v - 128) << 8);
  gamepad_i2s_word = ((uint32_t)s << 16) | s;
}

static inline void gamepad_i2s_init(void) {
  const PIO pio = GAMEPI_I2S_PIO;
  const uint sm = GAMEPI_I2S_SM;
  pio_gpio_init(pio, PIN_I2S_DIN);
  pio_gpio_init(pio, PIN_I2S_BCK);
  pio_gpio_init(pio, PIN_I2S_LRCK);
  const uint offset = pio_add_program(pio, &audio_i2s_program);
  audio_i2s_program_init(pio, sm, offset, PIN_I2S_DIN, PIN_I2S_BCK);
  // 64 PIO cycles per frame (see i2s.pio). Fractional divider: the DAC
  // re-locks its PLL to BCK, the jitter is far below audibility.
  pio_sm_set_clkdiv(pio, sm,
                    (float)clock_get_hz(clk_sys) / (64.0f * GAMEPI_I2S_HZ));

  const int ch = dma_claim_unused_channel(true);
  dma_channel_config c = dma_channel_get_default_config(ch);
  channel_config_set_transfer_data_size(&c, DMA_SIZE_32);
  channel_config_set_read_increment(&c, false);
  channel_config_set_write_increment(&c, false);
  channel_config_set_dreq(&c, pio_get_dreq(pio, sm, true));
  // RP2350 ENDLESS mode: the count never decrements, the channel runs until
  // aborted. (Would need two chained channels on an RP2040.)
  dma_channel_configure(
      ch, &c, &pio->txf[sm], &gamepad_i2s_word,
      (DMA_CH0_TRANS_COUNT_MODE_VALUE_ENDLESS << DMA_CH0_TRANS_COUNT_MODE_LSB) | 1u,
      true);
  pio_sm_set_enabled(pio, sm, true);
}
