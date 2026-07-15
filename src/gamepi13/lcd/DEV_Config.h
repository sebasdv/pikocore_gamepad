#pragma once
// Shim replacing Waveshare's DEV_Config for the pikocore GamePi13 build.
// Provides only what LCD_1in3.c / GUI_Paint.c actually use. No i2c, no
// stdio_init_all, no DEV_Module_Init — init lives in gamepi_lcd_dev_init().
#include <stdint.h>

#include "hardware/spi.h"
#include "pico/stdlib.h"

#ifdef __cplusplus
extern "C" {
#endif

#define UBYTE uint8_t
#define UWORD uint16_t
#define UDOUBLE uint32_t

extern int EPD_RST_PIN;
extern int EPD_DC_PIN;
extern int EPD_CS_PIN;
extern int EPD_BL_PIN;

void DEV_Digital_Write(UWORD Pin, UBYTE Value);
UBYTE DEV_Digital_Read(UWORD Pin);
void DEV_SPI_WriteByte(UBYTE Value);
void DEV_SPI_Write_nByte(uint8_t *pData, uint32_t Len);
void DEV_Delay_ms(UDOUBLE xms);
void DEV_Delay_us(UDOUBLE xus);

// pikocore-specific (called from ui.cpp, not from vendored code):
void gamepi_lcd_dev_init(void);
void gamepi_lcd_backlight(uint8_t percent);  // 0-100

#ifdef __cplusplus
}
#endif
