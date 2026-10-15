#!/usr/bin/env python3
"""Asignacion GPIO -> funcion de la PCB V2. Fuente de verdad del pinout.

gen_sch.py lo consume para armar las nets del socket del MCU, y
checks/check_pinmap.py lo contrasta contra el board config real del firmware
(src/boards/pikocore_gamepad/config.h, target PIKO_GAMEPAD de CMake): si los
dos se separan, la placa y el firmware dejan de coincidir sin ningun error
visible.

Desde la rama hw/chipdown-rp2350 el RP2350A va soldado en la placa (QFN-60),
no en el modulo RP2350-Plus: los 30 GPIO quedan disponibles. GP0-GP22 y GP26
conservan exactamente la funcion que tenian con el modulo (el firmware no
cambia); GP23/24/29 hacen lo mismo que hacian DENTRO del modulo (modo del
regulador, sensado de VBUS, VSYS/3) y GP25 (el LED del modulo) queda libre.
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
    0:  "DPAD_UP",
    1:  "DPAD_DOWN",
    2:  "LCD_SCK",     # SPI0 SCK
    3:  "LCD_MOSI",    # SPI0 TX
    4:  "DPAD_LEFT",
    5:  "LCD_DC",
    6:  "LCD_RES",
    7:  "LCD_BLK",     # PWM de backlight
    8:  "I2S_DIN",     # PIO
    9:  "DPAD_RIGHT",
    10: "BTN_X",
    11: "BTN_Y",
    12: "BTN_A",
    13: "BTN_B",
    14: "BTN_START",
    15: "BTN_SELECT",
    16: "I2S_BCK",     # PIO
    17: "I2S_LRCK",    # PIO — DEBE ser BCK+1
    18: "BTN_L",
    19: "BTN_R",
    20: "SPK_SHDN",    # salida: 1 = parlante encendido
    21: "JACK_DET",    # entrada con pull-up: 0 = plug insertado
    22: "DAC_XSMT",    # pulldown 100k: arranca muteado
    23: "BB_PS",       # TPS63001 PS/SYNC: 0 = power-save, 1 = PWM fijo
    24: "VBUS_SENSE",  # 1 = USB conectado (100k/200k desde VBUS)
    26: "LCD_TE",      # tearing effect del panel (entrada, opcional)
    29: "VSYS_ADC",    # ADC3, VSYS/3 (200k/100k): nivel de bateria
}

# Libres: GP27/GP28 (con ADC) y GP25 (era el LED del modulo; en la parte de
# atras de una consola de mano nadie lo ve). GP26 fue BTN_OK (centro del
# NAV5) hasta que el D-pad volvio a ser cuatro tacts, y despues LCD_TE.
FREE = (25, 27, 28)

# Pines del RP2350A en QFN-60: numero -> nombre. VERIFICADO contra dos
# fuentes independientes que coinciden en los 61 pads:
#   - simbolo MCU_RaspberryPi:RP2350A de la libreria de KiCad 10;
#   - netlist pad->net de la placa minima oficial RPI-RP2350A-MINIMAL_R4-S1.
# El 61 es el pad expuesto (GND).
RP2350A_PINS = {
    1: "IOVDD", 2: "GPIO0", 3: "GPIO1", 4: "GPIO2", 5: "GPIO3", 6: "DVDD",
    7: "GPIO4", 8: "GPIO5", 9: "GPIO6", 10: "GPIO7", 11: "IOVDD",
    12: "GPIO8", 13: "GPIO9", 14: "GPIO10", 15: "GPIO11", 16: "GPIO12",
    17: "GPIO13", 18: "GPIO14", 19: "GPIO15", 20: "IOVDD", 21: "XIN",
    22: "XOUT", 23: "DVDD", 24: "SWCLK", 25: "SWDIO", 26: "RUN",
    27: "GPIO16", 28: "GPIO17", 29: "GPIO18", 30: "IOVDD", 31: "GPIO19",
    32: "GPIO20", 33: "GPIO21", 34: "GPIO22", 35: "GPIO23", 36: "GPIO24",
    37: "GPIO25", 38: "IOVDD", 39: "DVDD", 40: "GPIO26", 41: "GPIO27",
    42: "GPIO28", 43: "GPIO29", 44: "ADC_AVDD", 45: "IOVDD",
    46: "VREG_AVDD", 47: "VREG_PGND", 48: "VREG_LX", 49: "VREG_VIN",
    50: "VREG_FB", 51: "USB_DM", 52: "USB_DP", 53: "USB_OTP_VDD",
    54: "QSPI_IOVDD", 55: "QSPI_SD3", 56: "QSPI_SCLK", 57: "QSPI_SD0",
    58: "QSPI_SD2", 59: "QSPI_SD1", 60: "QSPI_SS", 61: "GND",
}


def gpio_of(func):
    """Numero de GPIO de una funcion. Falla fuerte si no existe, para que un
    typo no se convierta en un None que se propaga silencioso a las nets."""
    for g, f in GPIO.items():
        if f == func:
            return g
    raise KeyError(f"funcion no asignada: {func}")


def qfn_pin(gpio):
    """Numero de pin del QFN-60 de un GPIO."""
    for n, nombre in RP2350A_PINS.items():
        if nombre == f"GPIO{gpio}":
            return n
    raise KeyError(f"GPIO{gpio} no existe en el RP2350A")
