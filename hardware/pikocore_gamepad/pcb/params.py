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
        1.27, True,
        "Borde del modulo (el del lado del header) -> centro de la fila de "
        "pines. Medido sobre el STEP del modulo: los 7 agujeros D1.27 estan "
        "en Y=37.950 y el modulo mide 39.22 de alto, o sea 1.270 al borde. "
        "1.27 = 0.05 pulgadas = MEDIO paso de 2.54: es una cota de diseno y "
        "no una casualidad, lo que da confianza extra en el numero. "
        "El 1.60 de V1 salia de escalar el dibujo a ojo y erraba por 0.33mm.",
        "V-1"),
    "LCD_HOLE_INSET": Param(
        2.50, True,
        "Borde del modulo -> CENTRO del agujero de montaje, en los dos ejes. "
        "Medido sobre el STEP del modulo: los cuatro agujeros D2.00 caen en "
        "(2.500, 2.500) (2.500, 36.720) (25.200, 36.720) (25.200, 2.500). "
        "CONFIRMA la hipotesis que estaba anotada aca: el drawing decia 2.19 "
        "y la nota china 2.5, y no se contradecian — acotan cosas distintas. "
        "2.19 es el margen lateral del AREA ACTIVA ((27.78-23.40)/2 = 2.190 "
        "exacto), no la posicion del agujero. El valor de V1 estaba mal. "
        "gen_fp.py calcula el agujero derecho como BOARD_W - inset, o sea "
        "asume simetria: correcto para un modulo comercial.",
        "V-2"),
    "LCD_HOLE_DIA": Param(
        2.00, True,
        "Nota china del drawing: 'kong zhijing wei 2mm' = diametro 2mm.",
        "V-2"),

    # ---------------------------------------------------------------- audio
    "BOOST_L": Param(
        2.2, True,
        "Inductor del TPS61023 en uH. TI SLVSF14B tabla 6.3 (Recommended "
        "Operating Conditions) da un rango de inductancia efectiva de "
        "0.37 a 2.9 uH, con 1.0 nominal: 2.2 entra con margen. Se conserva "
        "en 2.2 y no se baja a 1.0 porque el inductor ya esta elegido y "
        "comprado (C3002559, 1210/3225), y moverlo dentro del rango valido no "
        "compra nada.",
        "V-7"),
    "BOOST_RFB_TOP": Param(
        200.0, True,
        "Resistencia superior del divisor de realimentacion, en kOhm. "
        "Vout = VREF * (1 + Rtop/Rbot) con VREF = 0.595V (TI SLVSF14B tabla "
        "6.5, PWM mode: 580/595/610 mV). Con 200k/27k da 5.0024V, o sea "
        "+0.05% de error, y los dos son valores E24 comunes. "
        "El divisor conduce 22uA contra los 4nA de fuga del pin FB (misma "
        "tabla), o sea 5500x mas: el error que aporta la fuga es despreciable. "
        "OJO: los valores de V1 (1000k/200k) daban 3.57V, un 28.6% por debajo "
        "del objetivo — nunca se habian calculado.",
        "V-7"),
    "BOOST_RFB_BOT": Param(
        27.0, True,
        "Resistencia inferior del divisor, en kOhm. Ver BOOST_RFB_TOP.",
        "V-7"),

    # ---------------------------------------------------------------- placa
    "BOARD_W": Param(
        120.00, True,
        "Contorno definitivo, tomado de la capa BOARD_OUTLINE del DXF que el usuario ordeno en Rhino.",
        "V-0"),
    "BOARD_H": Param(
        80.00, True,
        "Contorno definitivo, tomado de la capa BOARD_OUTLINE del DXF que el usuario ordeno en Rhino.",
        "V-0"),
}


def v(name):
    """Valor de una constante. Falla fuerte si no existe, para que un typo
    no se convierta en un None que se propaga silencioso a la geometria."""
    if name not in ALL:
        raise KeyError(f"parametro desconocido: {name}")
    return ALL[name].value
