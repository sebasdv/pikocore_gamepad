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
    # -------------------------------------------------------------- PANEL LCD
    # Panel desnudo DisplayModule DM-TFT13-377 variante 24 pines (LH133T-IF05,
    # ST7789VW), FPC de 24 posiciones a 0.5mm. Cotas del "Mechanical Drawing"
    # rev C (2017-12-12) del datasheet publico, sin calibre: cierran por
    # aritmetica (BL - AA = 2 x margen) y son cotas de diseno del fabricante.
    # Reemplaza al modulo de 7 pines pasantes (27.78 x 39.22): sin header, sin
    # agujeros de montaje, se pega al frente y el FPC baja a un conector ZIF.
    #
    # ORIENTACION EN LA PLACA: el FPC sale hacia ABAJO (+Y). El lado de 26.16
    # del BL queda horizontal (ancho) y el de 29.22 vertical (alto); la franja
    # del IC/FPC (4.26) queda abajo y el margen chico (1.56) arriba.
    "PANEL_BL_W": Param(
        26.16, True,
        "Ancho del backlight (BL), horizontal en la placa. Drawing: 26.16+-0.2.",
        "V-1"),
    "PANEL_BL_H": Param(
        29.22, True,
        "Alto del BL, vertical en la placa (lado por el que sale el FPC). "
        "Drawing: 29.22+-0.2.",
        "V-1"),
    "PANEL_AA": Param(
        23.40, True,
        "Area activa, cuadrada. Drawing: 23.40 LCD (AA); 240 px x 0.0975 mm.",
        "V-1"),
    "PANEL_AA_OFF_X": Param(
        1.38, True,
        "Margen del BL al area activa en los dos lados cortos: (26.16-23.40)/2 "
        "= 1.38 exacto. Drawing: 0.33 (BL->POL) + 1.05.",
        "V-1"),
    "PANEL_AA_OFF_TOP": Param(
        1.56, True,
        "Margen del BL al area activa en el lado opuesto al FPC: 0.23 + 1.33 "
        "del drawing. El otro lado es 29.22 - 23.40 - 1.56 = 4.26, la franja "
        "del driver y la salida del FPC.",
        "V-1"),
    "PANEL_FPC_W": Param(
        13.0, True,
        "Ancho de la cola del FPC. Drawing: 12.5+-0.1 de contactos mas 0.25 "
        "por lado; conector de 24P a 0.5mm.",
        "V-1"),
    "PANEL_FPC_LEN": Param(
        14.93, True,
        "Largo de la cola del FPC desde el borde del vidrio hasta su punta "
        "(contactos en los ultimos 2mm). Drawing: 14.93.",
        "V-1"),
    "PANEL_T": Param(
        1.5, True, "Espesor del panel, max. Drawing: 1.5mm MAX.", "V-1"),
    # --- LA QUE NO SE PUEDE VERIFICAR SIN LA PIEZA ---
    "LCD_FPC_PIN_ORDER": Param(
        1.0, False,
        "1 = el pin 1 del FPC cae del lado del pin 1 del conector con el FPC "
        "derecho (sin plegar) y los contactos hacia la placa, que es como lo "
        "dibuja el datasheet. 0 = espejado. NO se verifica con el datasheet: "
        "depende de que lado del FPC lleva los contactos, y el conector "
        "C2856831 acepta las dos caras. Confirmar con el panel en mano "
        "(continuidad entre LEDA del FPC y el pad 1 de J4) antes de fabricar; "
        "si sale 0, J4 va con rot 0 en vez de 180 en placements.py.",
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
