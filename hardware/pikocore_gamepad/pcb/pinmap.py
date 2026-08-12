#!/usr/bin/env python3
"""Asignacion GPIO -> funcion de la PCB V2. Fuente de verdad del pinout.

Es el mismo mapa que la seccion 3.1 del spec. gen_sch.py lo consume para
armar las nets del socket del MCU, y checks/check_pinmap.py lo contrasta
contra boards/rp2350plus_v2/config.h del firmware: si los dos se separan, la
placa y el firmware dejan de coincidir sin ningun error visible.

El RP2350-Plus es pin-compatible con la Raspberry Pi Pico y expone GP0-GP22
y GP26-GP28. GP23/24/25 son internos del modulo (MODE del MP28164, sensado
de VBUS, LED) y GP29 no sale al header.
"""

# --- pines validos por periferico, restringido a los que el modulo expone ---
#
# Las funciones alternativas del RP2350 siguen patrones periodicos, y estas
# listas se derivan de ahi:
#
#   SPI  — bloques de 8 GPIO alternando SPI0/SPI1, y dentro de cada grupo de
#          4: RX, CSn, SCK, TX. (GP0-7 SPI0, GP8-15 SPI1, GP16-23 SPI0,
#          GP24-31 SPI1.)
#   I2C  — alterna cada 2 GPIO, SDA en el par y SCL en el impar siguiente.
#          I2C1 cae en GP2/3, GP6/7, GP10/11, GP14/15, GP18/19, GP22/23, GP26/27.
#   UART — bloques de 4: TX, RX, CTS, RTS. UART0 en GP0-3, GP12-15, GP16-19
#          y GP28-29.
#
# Son una lista blanca: si falta una entrada, el checker da una alarma falsa
# que un humano verifica contra el datasheet. Nunca al reves. Por eso solo se
# agregan entradas de las que hay certeza.
SPI0_SCK_OK = (2, 6, 18, 22)
SPI0_TX_OK = (3, 7, 19)            # GP23 no esta expuesto
SPI0_RX_OK = (0, 4, 16, 20)
SPI1_SCK_OK = (10, 14, 26)
SPI1_TX_OK = (11, 15, 27)
SPI1_RX_OK = (8, 12, 28)
I2C1_SDA_OK = (2, 6, 10, 14, 18, 22, 26)
I2C1_SCL_OK = (3, 7, 11, 15, 19, 27)   # GP23 no esta expuesto
UART0_TX_OK = (0, 12, 16, 28)
UART0_RX_OK = (1, 13, 17)              # GP29 no sale al header

# --- asignacion definitiva ---
GPIO = {
    0:  "MIDI_TX",     # UART0 TX
    1:  "MIDI_RX",     # UART0 RX
    2:  "LCD_SCK",     # SPI0 SCK
    3:  "LCD_MOSI",    # SPI0 TX
    4:  "PCF_INT",     # wired-OR de los 3 /INT
    5:  "LCD_DC",
    6:  "LCD_RES",
    7:  "LCD_BLK",     # PWM de backlight
    8:  "I2S_DIN",     # PIO
    10: "SD_SCK",      # SPI1 SCK
    11: "SD_MOSI",     # SPI1 TX
    12: "SD_MISO",     # SPI1 RX
    13: "SD_CS",
    16: "I2S_BCK",     # PIO
    17: "I2S_LRCK",    # PIO — DEBE ser BCK+1
    18: "I2C_SDA",     # I2C1
    19: "I2C_SCL",     # I2C1
    20: "SPK_SHDN",    # salida: 1 = parlante encendido
    21: "JACK_DET",    # entrada con pull-up: 0 = plug insertado
    22: "DAC_XSMT",    # pulldown 100k: arranca muteado
}

# Van al header de expansion. GP26/27/28 son los unicos con ADC.
FREE = (9, 14, 15, 26, 27, 28)

# Orden fisico del header de 40 pines tipo Pico. El pin 38 es GND (no VSYS_EN).
HEADER_ORDER = [
    "GP0", "GP1", "GND", "GP2", "GP3", "GP4", "GP5", "GND", "GP6", "GP7",
    "GP8", "GP9", "GND", "GP10", "GP11", "GP12", "GP13", "GND", "GP14", "GP15",
    "GP16", "GP17", "GND", "GP18", "GP19", "GP20", "GP21", "GND", "GP22", "RUN",
    "GP26", "GP27", "AGND", "GP28", "ADC_VREF", "3V3", "3V3_EN", "GND", "VSYS", "VBUS",
]


def gpio_of(func):
    """Numero de GPIO de una funcion. Falla fuerte si no existe, para que un
    typo no se convierta en un None que se propaga silencioso a las nets."""
    for g, f in GPIO.items():
        if f == func:
            return g
    raise KeyError(f"funcion no asignada: {func}")


def header_pin(gpio):
    """Numero de pin fisico en el header de 40 pines tipo Pico."""
    return HEADER_ORDER.index(f"GP{gpio}") + 1
