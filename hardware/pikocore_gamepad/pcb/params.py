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
    # ---------------------------------------------------------- PANTALLA LCD
    # Modulo IPS 1.3in 240x240 ST7789 de 7 pines pasantes (EC-Buying,
    # AliExpress 32880670572), el que el usuario tiene en mano. Cotas del
    # dibujo del fabricante, confirmadas por el usuario el 2026-10-17; cierran
    # por aritmetica (pines y area activa centrados en el ancho). Las dos que
    # el dibujo no da quedan sin verificar y bloquean G-0 hasta medirlas.
    #
    # Huella: origen = pin 1 (GND), X a lo largo de la fila de pines, Y hacia
    # el cuerpo del modulo.
    "LCD7_BOARD_W": Param(
        27.78, True, "Ancho de la placa del modulo. Dibujo del fabricante.",
        "V-1"),
    "LCD7_BOARD_H": Param(
        39.22, True, "Alto de la placa del modulo. Dibujo del fabricante.",
        "V-1"),
    "LCD7_PIN1_X": Param(
        6.27, True,
        "Borde izquierdo -> eje del pin 1. Dibujo: 6.27 + 6 x 2.54 + 6.27 = "
        "27.78 exacto, los 7 pines quedan centrados en el ancho.",
        "V-1"),
    "LCD7_PIN_PITCH": Param(
        2.54, True, "Paso de los pines. Dibujo del fabricante.", "V-1"),
    "LCD7_PIN_PAD": Param(
        1.7, True,
        "Diametro del pad en la placa. Eleccion de diseno (no es cota del "
        "modulo): con el taladro de 1.0 deja 0.35 de anillo por lado.",
        "V-1"),
    "LCD7_AA": Param(
        23.40, True,
        "Area activa, cuadrada. Dibujo: 23.40 = 240 px x 0.0975 mm.", "V-1"),
    "LCD7_AA_OFF_X": Param(
        2.19, True,
        "Borde izquierdo -> area activa: (27.78 - 23.40) / 2 = 2.19, centrada "
        "en el ancho.",
        "V-1"),
    "LCD7_AA_OFF_TOP": Param(
        6.33, True,
        "Borde del lado de los pines -> area activa. Dibujo: 5.00 al vidrio "
        "+ 1.33 de marco del vidrio a la ventana.",
        "V-1"),
    "LCD7_HOLE_DIA": Param(
        2.0, True,
        "Diametro de los 4 agujeros de montaje del modulo. Dibujo del "
        "fabricante. En la placa son solo dibujo: no se taladran, el modulo "
        "se sostiene por sus pines.",
        "V-1"),
    "LCD7_HOLE_INSET": Param(
        2.5, True,
        "Borde del modulo -> centro de cada agujero, en los dos ejes. Dibujo "
        "del fabricante.",
        "V-1"),
    # --- LAS DOS QUE EL DIBUJO NO DA: verificadas por el usuario con el modulo ---
    "LCD7_PIN_ROW_TO_EDGE": Param(
        1.27, True,
        "Eje de la fila de pines -> borde del modulo del lado de los pines. "
        "El dibujo no la acota; 1.27 (medio paso) venia de la huella vieja "
        "(commit 4d66184~1). El usuario midio el modulo en mano y confirmo el "
        "valor el 2026-10-17 (corre el contorno y el area activa respecto de "
        "los pines).",
        "V-8"),
    "LCD7_PIN_DRILL": Param(
        1.0, True,
        "Taladro de los 7 pines en la placa. Parte de pines de header de 0.64 "
        "de lado (diagonal 0.9). El usuario midio los pines del modulo en mano "
        "y confirmo el valor el 2026-10-17.",
        "V-8"),

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
        100.00, True,
        "Reducido de 120 a 100 por pedido del usuario (2026-10-14): el ancho "
        "lo fijaban los dos grupos de controles y sobraban ~30mm de aire "
        "entre el display y el rombo y a la derecha del rombo. El DXF de "
        "Rhino (pikocore_gamepad_template*.dxf) sigue en 120 y hay que "
        "regenerarlo con gen_template_dxf.py si se vuelve a editar ahi.",
        "V-0"),
    "BOARD_H": Param(
        60.00, True,
        "Eleccion de diseno de la variante con modulo (Micro 100x60 + MIDI), "
        "no una medicion: el modulo RP2350-Plus va soldado plano al dorso "
        "por castellations y la placa baja de 80 a 60. El DXF de Rhino (80) quedo "
        "desactualizado.",
        "V-0"),
}


def v(name):
    """Valor de una constante. Falla fuerte si no existe, para que un typo
    no se convierta en un None que se propaga silencioso a la geometria."""
    if name not in ALL:
        raise KeyError(f"parametro desconocido: {name}")
    return ALL[name].value
