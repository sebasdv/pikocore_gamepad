#include "hdmi_mirror.h"

#include <string.h>

#include "common_dvi_pin_configs.h"
#include "dvi.h"
#include "dvi_serialiser.h"
#include "hardware/clocks.h"
#include "hardware/vreg.h"
#include "pico/multicore.h"
#include "pico/stdlib.h"
#include "ui.h"

// The LCD UI is 240x240; DVI runs 320x240 pixel-doubled to 640x480, so the UI
// shows up 2x (480x480) centred, with 40 px black bars on each side.
static constexpr uint kUi = 240;
static constexpr uint kFrameW = 320;
static constexpr uint kPad = (kFrameW - kUi) / 2;

static struct dvi_inst dvi0;
// libdvi's timing is 252 MHz bit clock; the audio engine is tuned to a 248 MHz
// sys clock, so keep 248 and accept a ~24.8 MHz pixel clock (~59 Hz) instead of
// detuning every sample.
static struct dvi_timing timing;

// tmds encoder reads 32-bit words.
static uint16_t line_buf[kFrameW] __attribute__((aligned(4)));

// Source is the LCD framebuffer as ui.cpp draws it: ROTATE_270, so logical
// (x, y) lives at memory (x=y, y=kUi-1-x), stored RGB565 big-endian.
static uint32_t *next_line(uint y) {
#if PIKO_HDMI_ONLY || PIKO_HDMI_BARS
  {
    static const uint16_t bars[8] = {0xFFFF, 0xFFE0, 0x07FF, 0x07E0,
                                     0xF81F, 0xF800, 0x001F, 0x0000};
    for (uint x = 0; x < kFrameW; ++x) line_buf[x] = bars[x * 8 / kFrameW];
    return (uint32_t *)line_buf;
  }
#endif
  const uint16_t *fb = (const uint16_t *)gamepi_ui_framebuffer();
  uint16_t *out = line_buf + kPad;
  const uint16_t *src = fb + y + (kUi - 1) * kUi;
  for (uint x = 0; x < kUi; ++x) {
    out[x] = __builtin_bswap16(*src);
    src -= kUi;
  }
  return (uint32_t *)line_buf;
}

static void core1_main() {
  dvi_register_irqs_this_core(&dvi0, DMA_IRQ_0);
  dvi_scanbuf_main_16bpp_cb(&dvi0, next_line);
}

void gamepi_hdmi_start() {
  // Side bars stay black; only the centre is rewritten per line.
  memset(line_buf, 0, sizeof(line_buf));

  vreg_set_voltage(VREG_VOLTAGE_1_20);
  sleep_ms(10);

  // libdvi's PIO serialiser addresses pins 32-38 (HDMI socket).
  pio_set_gpio_base(DVI_DEFAULT_SERIAL_CONFIG.pio, 16);

  memcpy(&timing, &dvi_timing_640x480p_60hz, sizeof(timing));
  timing.bit_clk_khz = clock_get_hz(clk_sys) / 1000;
  dvi0.timing = &timing;
  dvi0.ser_cfg = DVI_DEFAULT_SERIAL_CONFIG;
  dvi_init(&dvi0, next_striped_spin_lock_num(), next_striped_spin_lock_num());

  multicore_launch_core1(core1_main);
}
