#!/usr/bin/env python3
"""Posiciones de los footprints. LA REESCRIBE parse_dxf.py.

Vive en su propio archivo justamente para que parse_dxf.py pueda regenerarlo
entero sin riesgo. En V1 esta tabla estaba dentro de gen_pcb.py y parse_dxf.py
solo imprimia un diff que habia que transcribir a mano.

Formato: (ref, footprint "lib:nombre", x, y, rotacion, flip_al_dorso)

OJO con el flip: pcbnew.Flip(LEFT_RIGHT) espeja X y deja rot=180. La rotacion
de esta tabla es la FINAL, post-flip.

Disposicion Game Boy Micro en 100x60 (spec 2026-10-16, variante con modulo):
el frente es el de la rama chip-down (verificado alli); al dorso va el modulo
RP2350-Plus soldado PLANO por sus castellations, vertical en la unica franja
sin patas pasantes del frente (x 31..69), y todo lo demas alrededor.

Los pasivos que no estan aca los coloca gen_pcb.py en FREE_REGIONS.
"""
from params import v

BOARD_W = v("BOARD_W")
BOARD_H = v("BOARD_H")

# El panel al CENTRO, la cruceta a la izquierda y el rombo a la derecha,
# todos centrados en y=24. El origen del panel es el centro del area activa.
_LCD_X = BOARD_W / 2
_LCD_Y = 24.0

# Modulo RP2350-Plus al dorso, eje largo en Y, USB-C hacia el borde inferior.
# MODULE_BOX es hasta donde llegan sus pads (+-11.1 x +-25.5 del centro): el
# modulo apoya plano, asi que adentro no puede haber ninguna pieza del dorso
# ni ninguna pata pasante del frente (check_placement.py lo verifica).
MODULE_POS = (50.0, 33.0)
MODULE_BOX = (38.9, 7.5, 61.1, 58.5)

PLACEMENTS = [
    # ================================================ FRENTE: display
    ("LCD1", "gamesetup_fp:LCD_LH133T_24P",             _LCD_X, _LCD_Y, 0, False),
    # Conector del FPC debajo del panel, en el frente. El vidrio termina en
    # y = 24 - 11.7 - 1.56 + 29.22 = 39.96 y el flex llega desplegado
    # 14.93 mas abajo; con rot 180 los contactos del conector caen 1.62 por
    # debajo de su origen, asi que el origen va 12.4 bajo el vidrio.
    # rot 180 asume contactos del FPC hacia la placa: LCD_FPC_PIN_ORDER.
    # Es SMD del frente: detras, al dorso, va el modulo (cobre en caras
    # opuestas, sin pasantes).
    ("J4",  "gamesetup_lcsc:FPC-SMD_24P-P0.50_FPC-05FB-24PH20",
      _LCD_X,   52.40, 180, False),

    # ================================================ FRENTE: controles
    # Cruceta: cuatro tacts 6x6 con paso 8.5mm. El origen del SW_PUSH_6mm es
    # el pad 1 y el cuerpo queda en (x+3.25, y+2.25). Centro de la cruz
    # (18, 24). Sus patas atraviesan al dorso: x 6..30, y 12..37.
    ("SW1", "Button_Switch_THT:SW_PUSH_6mm",   14.75,   13.25, 0, False),  # UP    cuerpo (18.0, 15.5)
    ("SW3", "Button_Switch_THT:SW_PUSH_6mm",    6.25,   21.75, 0, False),  # LEFT  cuerpo ( 9.5, 24.0)
    ("SW4", "Button_Switch_THT:SW_PUSH_6mm",   23.25,   21.75, 0, False),  # RIGHT cuerpo (26.5, 24.0)
    ("SW2", "Button_Switch_THT:SW_PUSH_6mm",   14.75,   30.25, 0, False),  # DOWN  cuerpo (18.0, 32.5)
    # Rombo X/Y/A/B, espejo de la cruceta: centro (82, 24). Patas x 69..94.
    ("SW5", "Button_Switch_THT:SW_PUSH_6mm",   78.75,   13.25, 0, False),  # X     cuerpo (82.0, 15.5)
    ("SW6", "Button_Switch_THT:SW_PUSH_6mm",   70.25,   21.75, 0, False),  # Y     cuerpo (73.5, 24.0)
    ("SW7", "Button_Switch_THT:SW_PUSH_6mm",   87.25,   21.75, 0, False),  # A     cuerpo (90.5, 24.0)
    ("SW8", "Button_Switch_THT:SW_PUSH_6mm",   78.75,   30.25, 0, False),  # B     cuerpo (82.0, 32.5)
    # L / R: tact ANGULADO en las esquinas superiores. rot 0 -> actuador
    # hacia -Y. El origen es el PAD 1 y el cuerpo esta 2.25 hacia +X: 9.75 y
    # 85.75 dejan los cuerpos en 12 y 88, simetricos respecto de x=50.
    # y=1.89: pads a 1mm del borde, actuador asomando ~2mm.
    ("SW9",  "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
       9.75,    1.89, 0,  False),  # L -> cuerpo x 8.2..15.8
    ("SW10", "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
      85.75,    1.89, 0, False),  # R -> cuerpo x 84.2..91.8
    # SELECT y START bajo el rombo, como en la Micro: cuerpos en (76, 46) y
    # (88, 46). Patas x 72..91, y 42.7..50.3.
    ("SW12", "Button_Switch_THT:SW_PUSH_6mm",   72.75,   43.75, 0, False),  # SELECT
    ("SW11", "Button_Switch_THT:SW_PUSH_6mm",   84.75,   43.75, 0, False),  # START
    # Slide de encendido en el borde INFERIOR, a la izquierda del flex.
    # rot 0 -> actuador hacia +Y. y=57.70: pads de anclaje a 1mm del borde.
    ("SW15", "gamesetup_lcsc:SW-TH_SK12D07VG3",             25.00,    57.70, 0, False),

    # ================================================ DORSO: modulo
    ("U1",  "gamesetup_fp:RP2350-Plus_Castellated",
      MODULE_POS[0], MODULE_POS[1], 0, True),

    # ================================================ DORSO: jacks
    # El extremo superior del modulo (y=7.5) tapa el centro del borde de
    # arriba: MIDI IN arriba a la izquierda y MIDI OUT arriba a la derecha,
    # simetricos, con flip y rot 180 (barril por el borde superior, pads a
    # 3mm del canto, cuerpo 14.5mm hacia adentro). x=33/67: el cuerpo (9.2 de
    # ancho) termina a ~1.3mm del modulo y no tapa las patas de UP ni de X.
    ("J6",  "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal",
      33.00,    3.00, 180, True),   # MIDI IN
    ("J7",  "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal",
      67.00,    3.00, 180, True),   # MIDI OUT
    # Auriculares por el borde IZQUIERDO, girado: bajo las patas de la
    # cruceta (hasta y 36) y a la izquierda del slide (desde x 19.9).
    ("J1",  "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal",
       3.00,   45.00, 270, True),   # phones

    # ================================================ DORSO: MIDI
    # Opto a rot 0 (patas gull-wing en Y, 10.2mm): x 19.2..26.8, y 1.4..11.6,
    # entre las patas del gatillo L y las de UP, al lado de J6. Sus pasivos
    # en la columna entre la cruceta (patas hasta x 30.75) y el modulo.
    ("U10", "Package_DIP:SMDIP-6_W7.62mm",                 23.00,    6.50, 0, True),
    ("R42", "Resistor_SMD:R_0603_1608Metric",              35.00,   19.50, 90, True),
    ("D3",  "Diode_SMD:D_SOD-123",                         35.00,   24.00, 90, True),
    ("R43", "Resistor_SMD:R_0603_1608Metric",              35.00,   28.50, 90, True),
    ("C56", "Capacitor_SMD:C_0603_1608Metric",             35.00,   32.00, 90, True),
    # Buffer del MIDI OUT entre J7 y las patas de X.
    ("U9",  "Package_TO_SOT_SMD:SOT-353_SC-70-5",          75.00,    4.00, 0, True),
    ("R40", "Resistor_SMD:R_0603_1608Metric",              75.00,    7.50, 0, True),
    ("R41", "Resistor_SMD:R_0603_1608Metric",              75.00,   10.50, 0, True),

    # ================================================ DORSO: audio
    # DAC y op-amp a la izquierda, entre J1 y el modulo, bajo la cruceta.
    ("U5",  "gamesetup_lcsc:TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL", 24.00, 42.00, 0, True),
    ("U3",  "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",              33.00, 42.00, 0, True),
    # Deteccion de auriculares, al lado de J1.
    ("R15", "Resistor_SMD:R_0603_1608Metric",              20.00,   48.00, 0, True),
    ("R18", "Resistor_SMD:R_0603_1608Metric",              20.00,   50.50, 0, True),
    ("C29", "Capacitor_SMD:C_0603_1608Metric",             24.00,   48.00, 0, True),
    # Los 470uF y sus bleeders en la banda de 7mm entre el rombo (pads hasta
    # y 35.75) y Select/Start (pads desde y 42.75).
    ("C23", "Capacitor_SMD:CP_Elec_6.3x5.4",               74.50,   39.40, 0, True),
    ("C24", "Capacitor_SMD:CP_Elec_6.3x5.4",               85.00,   39.40, 0, True),
    ("R19", "Resistor_SMD:R_0603_1608Metric",              91.50,   37.50, 0, True),
    ("R20", "Resistor_SMD:R_0603_1608Metric",              91.50,   41.50, 0, True),
    # Class-D bajo Select, a la izquierda del boost; parlante en la columna
    # del borde derecho, bajo A (pads hasta x 94.75, y 27.25).
    ("U4",  "gamesetup_lcsc:MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL",   74.00, 54.00, 0, True),
    ("J5",  "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
      97.00,   33.00, 90, True),

    # ================================================ DORSO: boost 5V
    # El lazo del TPS61023 se mueve ENTERO (+29, +50) desde la placa de 80:
    # manual_tracks.py tiene pistas entre U2, L1, C4 y C7 que dependen de la
    # geometria relativa del cluster. Queda en x 77.4..99, y 51.7..57.6,
    # bajo Select/Start.
    ("U2",  "Package_TO_SOT_SMD:SOT-563",                  89.00,   56.00, 0, True),
    ("L2",  "Inductor_SMD:L_1210_3225Metric",              83.80,   56.00, 0, True),
    ("C4",  "Capacitor_SMD:C_0603_1608Metric",             78.20,   56.00, 0, True),
    # rot 180 para que el pin de BOOST_SW quede del lado de U2.
    ("L1",  "Inductor_SMD:L_1210_3225Metric",              93.40,   56.00, 180, True),
    # C5 es 0805 y no 0603: a 5V un X5R de 0603/6.3V deja ~5uF de los 22.
    ("C5",  "Capacitor_SMD:C_0805_2012Metric",             93.50,   52.50, 0, True),
    ("C7",  "Capacitor_SMD:C_0603_1608Metric",             97.20,   52.50, 0, True),
    # Divisor de realimentacion del lado de FB (pin 1), lejos del nodo SW.
    ("R4",  "Resistor_SMD:R_0603_1608Metric",              88.00,   52.50, 0, True),
    ("R5",  "Resistor_SMD:R_0603_1608Metric",              84.20,   52.50, 0, True),
]

# Regiones del DORSO donde gen_pcb.py empaqueta los pasivos no anclados, EN
# ORDEN (las piezas grandes primero). Ninguna pisa MODULE_BOX. Esquivan las
# patas pasantes del frente; el empaquetador ademas esquiva solo todo lo ya
# colocado (courtyards del dorso y de cualquier pieza con pasantes). Contra
# el borde arrancan en 1.5: pads a >= 1.0mm del canto.
FREE_REGIONS = [
    (17.5, 36.5, 38.5, 53.3),    # izquierda: banda del audio, bajo la cruceta
    (31.0, 17.5, 38.5, 36.5),    # columna entre la cruceta y el modulo
    (30.7, 53.3, 38.5, 58.5),    # entre el slide y el modulo
    (1.5,  50.5, 19.4, 58.5),    # bajo J1
    (61.5, 17.5, 69.0, 51.0),    # columna entre el modulo y el rombo
    (61.5, 51.0, 98.5, 58.5),    # banda inferior derecha, bajo Select/Start
    (61.5, 35.8, 98.5, 43.0),    # banda de los 470uF
    (1.5,   7.0, 13.5, 20.0),    # arriba a la izquierda, bajo el gatillo L
    (86.5,  7.0, 98.5, 20.0),    # arriba a la derecha, bajo el gatillo R
    (14.0, 19.5, 22.0, 28.5),    # centro de la cruceta
    (78.5, 19.5, 85.5, 28.5),    # centro del rombo
]
