// Hardware shim for the vendored Waveshare LCD driver (GamePi13 build).
#include "lcd/DEV_Config.h"

#include "hardware/pwm.h"

#include "../hw_gamepi13.h"

#define GAMEPI_SPI spi1

int EPD_RST_PIN = GAMEPI_LCD_RST_PIN;
int EPD_DC_PIN = GAMEPI_LCD_DC_PIN;
int EPD_CS_PIN = GAMEPI_LCD_CS_PIN;
int EPD_BL_PIN = GAMEPI_LCD_BL_PIN;

mutex_t gamepi_spi1_mutex;

void gamepi_spi1_mutex_init(void) { mutex_init(&gamepi_spi1_mutex); }

void DEV_Digital_Write(UWORD Pin, UBYTE Value) { gpio_put(Pin, Value); }
UBYTE DEV_Digital_Read(UWORD Pin) { return gpio_get(Pin); }

void DEV_SPI_WriteByte(UBYTE Value) {
  spi_write_blocking(GAMEPI_SPI, &Value, 1);
}
void DEV_SPI_Write_nByte(uint8_t *pData, uint32_t Len) {
  spi_write_blocking(GAMEPI_SPI, pData, Len);
}

void DEV_Delay_ms(UDOUBLE xms) { sleep_ms(xms); }
void DEV_Delay_us(UDOUBLE xus) { sleep_us(xus); }

void gamepi_lcd_dev_init(void) {
  gpio_init(GAMEPI_LCD_RST_PIN);
  gpio_set_dir(GAMEPI_LCD_RST_PIN, GPIO_OUT);
  gpio_init(GAMEPI_LCD_DC_PIN);
  gpio_set_dir(GAMEPI_LCD_DC_PIN, GPIO_OUT);
  gpio_init(GAMEPI_LCD_CS_PIN);
  gpio_set_dir(GAMEPI_LCD_CS_PIN, GPIO_OUT);
  gpio_put(GAMEPI_LCD_CS_PIN, 1);
  gpio_put(GAMEPI_LCD_DC_PIN, 0);

  // Confirmado en hardware 2026-07-15: 31.25 MHz y 15.625 MHz seguian con
  // lineas verticales persistentes en pantalla (presentes incluso en
  // widgets de ancho completo, en reposo -- no es especifico del overlay).
  // Bajado al valor exacto que usa Gamepi13-RP2040-Demo/C/lib/Config/
  // DEV_Config.c para este mismo panel/cableado, validado por Waveshare.
  mutex_enter_blocking(&gamepi_spi1_mutex);
  spi_init(GAMEPI_SPI, 10000 * 1000);
  gpio_set_function(GAMEPI_LCD_CLK_PIN, GPIO_FUNC_SPI);
  gpio_set_function(GAMEPI_LCD_MOSI_PIN, GPIO_FUNC_SPI);
  mutex_exit(&gamepi_spi1_mutex);

  // Backlight PWM (slice de GP7 = 3; no colisiona con el audio en GP18 = slice 1)
  gpio_set_function(GAMEPI_LCD_BL_PIN, GPIO_FUNC_PWM);
  uint slice = pwm_gpio_to_slice_num(GAMEPI_LCD_BL_PIN);
  pwm_config cfg = pwm_get_default_config();
  pwm_config_set_clkdiv(&cfg, 4.f);
  pwm_init(slice, &cfg, true);
  gamepi_lcd_backlight(0);  // apagado hasta después del splash
}

void gamepi_lcd_backlight(uint8_t percent) {
  if (percent > 100) percent = 100;
  pwm_set_gpio_level(GAMEPI_LCD_BL_PIN,
                     (uint16_t)((uint32_t)percent * 65535u / 100u));
}
