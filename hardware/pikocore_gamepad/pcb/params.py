#!/usr/bin/env python3
"""Constantes fisicas de la PCB V2 y su estado de verificacion.

Cada constante declara si su valor esta CONFIRMADO contra la pieza fisica o
si todavia es provisional. checks/check_verified.py falla mientras quede
alguna sin verificar, y esa puerta bloquea la generacion de gerbers.

El proposito es que un valor provisional no pueda llegar a fabricacion por
olvido: en V1 el mapeo de pines del jack PJ-320A quedo sin verificar durante
meses porque solo estaba anotado en un comentario.

Para marcar una constante como verificada: medir, poner el valor real y
cambiar verified a True citando en `note` COMO se midio.
"""
from collections import namedtuple

# value    : valor en mm (o adimensional donde corresponda)
# verified : True solo si se confirmo contra la pieza fisica o un datasheet
# note     : de donde sale el valor / como se confirmo
# gate     : id de la tarea de verificacion del spec (V-1..V-7)
Param = namedtuple("Param", "value verified note gate")

ALL = {
    # ---------------------------------------------------------------- LCD
    # Cotas leidas del drawing GAMESETUP/layout.png. Las que cierran por
    # aritmetica exacta se dan por verificadas: la consistencia interna del
    # dibujo es evidencia suficiente y no depende de un calibre.
    "LCD_BOARD_W": Param(
        27.78, True,
        "Drawing layout.png. Cierra exacto con LCD_PIN1_X y LCD_PIN_PITCH.",
        "V-1"),
    "LCD_BOARD_H": Param(
        39.22, True,
        "Drawing layout.png. Cierra exacto con LCD_GLASS_TOP y LCD_GLASS_H.",
        "V-1"),
    "LCD_PIN1_X": Param(
        6.27, True,
        "Drawing. 6.27 + 6*2.54 + 6.27 = 27.78 exacto -> los 7 pines quedan "
        "centrados en el ancho del modulo.",
        "V-1"),
    "LCD_PIN_PITCH": Param(
        2.54, True, "Paso estandar, acotado en el drawing.", "V-1"),
    "LCD_GLASS_TOP": Param(
        5.00, True,
        "Drawing. 39.22 - 5.00 - 29.22 = 5.00 -> margenes simetricos.",
        "V-1"),
    "LCD_GLASS_H": Param(
        29.22, True, "Drawing.", "V-1"),
    "LCD_ACTIVE_W": Param(
        23.40, True,
        "Drawing. 23.40 x 23.40 = 240x240 px; diagonal 33.1mm = 1.3 pulgadas.",
        "V-1"),
    "LCD_ACTIVE_TOP": Param(
        6.33, True,
        "Drawing: LCD_GLASS_TOP (5.00) + 1.33 de marco superior del vidrio.",
        "V-1"),

    # --- LAS DOS QUE EL DRAWING NO CIERRA ---
    "LCD_PIN_ROW_Y": Param(
        1.60, False,
        "PROVISIONAL. El drawing no acota la vertical del header: las cotas "
        "2.19/0.81/0.64/0.64 son todas horizontales. 1.60 sale de escalar el "
        "dibujo (11.09 px/mm, verificado contra dos cotas conocidas). MEDIR "
        "con calibre: borde superior del modulo -> centro de la fila de pines.",
        "V-1"),
    "LCD_HOLE_INSET": Param(
        2.19, False,
        "PROVISIONAL. La cota del drawing dice 2.19mm al borde y la nota china "
        "al pie dice 2.5mm. HIPOTESIS de que no se contradicen sino que acotan "
        "cosas distintas: (27.78 - 23.40)/2 = 2.19 EXACTO, o sea que 2.19 es "
        "el margen lateral del area activa, y 2.5 seria el centro del agujero. "
        "De ser asi el valor correcto aca es 2.5. MEDIR con calibre para "
        "confirmar: borde del modulo -> CENTRO del agujero, en los dos ejes.",
        "V-2"),
    "LCD_HOLE_DIA": Param(
        2.00, True,
        "Nota china del drawing: 'kong zhijing wei 2mm' = diametro 2mm.",
        "V-2"),

    # ---------------------------------------------------------------- audio
    "BOOST_L": Param(
        2.2, False,
        "PROVISIONAL. Inductor del TPS61023 en uH. Calcular desde la hoja de "
        "datos de TI para 5V de salida con la corriente del NJM4556AD, y "
        "confirmar stock del valor elegido en LCSC.",
        "V-7"),
    "BOOST_RFB_TOP": Param(
        1000.0, False,
        "PROVISIONAL. Resistencia superior del divisor de realimentacion en "
        "kOhm. Calcular para Vout = 5.0V con la Vref del TPS61023.",
        "V-7"),
    "BOOST_RFB_BOT": Param(
        200.0, False,
        "PROVISIONAL. Resistencia inferior del divisor, en kOhm.",
        "V-7"),

    # ---------------------------------------------------------------- placa
    "BOARD_W": Param(
        90.0, False,
        "PROVISIONAL: contorno de partida para poder generar el template DXF. "
        "El contorno definitivo lo dibuja el usuario en Rhino y entra por "
        "parse_dxf.py.",
        "V-0"),
    "BOARD_H": Param(
        130.0, False,
        "PROVISIONAL: ver BOARD_W.",
        "V-0"),
}


def v(name):
    """Valor de una constante. Falla fuerte si no existe, para que un typo
    no se convierta en un None que se propaga silencioso a la geometria."""
    if name not in ALL:
        raise KeyError(f"parametro desconocido: {name}")
    return ALL[name].value
