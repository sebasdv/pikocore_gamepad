// sd_hw_config.c
// Hardware config for the RP2350-PiZero's onboard microSD socket.
// Adapted from RP2350-PiZero/C/03-MicroSD/example/config/hw_config.c,
// trimmed to the single SPI-attached card this board actually has.
// Pins verified against RP2350 IO_BANK0 FUNCSEL registers: GP30/31/40 only
// route to spi1 (no spi0 alternative), same peripheral the LCD uses on
// GP10/GP11 -- shared bus, see the spi1 mutex in dev_shim.c (Task 2).
#include <assert.h>

#include "hw_config.h"

static spi_t spi = {
    .hw_inst = spi1,
    .sck_gpio = 30,
    .mosi_gpio = 31,
    .miso_gpio = 40,
    .set_drive_strength = true,
    .mosi_gpio_drive_strength = GPIO_DRIVE_STRENGTH_2MA,
    .sck_gpio_drive_strength = GPIO_DRIVE_STRENGTH_12MA,
    .no_miso_gpio_pull_up = true,
    .baud_rate = 12 * 1000 * 1000,  // 12 MHz, conservative to start
};

static sd_spi_if_t spi_if = {
    .spi = &spi,
    .ss_gpio = 43,
    .set_drive_strength = true,
    .ss_gpio_drive_strength = GPIO_DRIVE_STRENGTH_2MA,
};

static sd_card_t sd_card = {
    .type = SD_IF_SPI,
    .spi_if_p = &spi_if,
    .use_card_detect = false,
};

size_t sd_get_num() { return 1; }

sd_card_t *sd_get_by_num(size_t num) {
  assert(num == 0);
  return num == 0 ? &sd_card : NULL;
}
