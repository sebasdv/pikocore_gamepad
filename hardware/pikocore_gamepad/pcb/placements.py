#!/usr/bin/env python3
"""Posiciones de los footprints. LA REESCRIBE parse_dxf.py.

Vive en su propio archivo justamente para que parse_dxf.py pueda regenerarlo
entero sin riesgo. En V1 esta tabla estaba dentro de gen_pcb.py y parse_dxf.py
solo imprimia un diff que habia que transcribir a mano.

Formato: (ref, footprint "lib:nombre", x, y, rotacion, flip_al_dorso)

OJO con el flip: pcbnew.Flip(LEFT_RIGHT) espeja X y deja rot=180. La rotacion
de esta tabla es la FINAL, post-flip.

ESTE PLACEMENT ES PROVISIONAL. Existe para que gen_template_dxf.py tenga algo
que exportar y para que el board sea valido; NO pretende estar libre de
solapamientos ni ser ruteable. El layout real lo ordena el usuario en Rhino
sobre el DXF, y recien despues tiene sentido rutear y exigir DRC limpio.

Los pasivos NO estan aca: son ~58 y gen_pcb.py los coloca en una grilla
automatica del dorso. Escribirles coordenadas a mano seria inventar 58
numeros que el usuario va a mover igual en la primera pasada.
"""
from params import v

BOARD_W = v("BOARD_W")
BOARD_H = v("BOARD_H")

# Disposicion estilo Game Boy Micro (spec 2026-10-15): el panel al CENTRO,
# la cruceta a la izquierda y el rombo a la derecha, todos centrados en
# y=24. El origen del panel es el centro del area activa.
_LCD_X = BOARD_W / 2
_LCD_Y = 24.0

PLACEMENTS = [
    # ================================================ FRENTE: display
    ("LCD1", "gamesetup_fp:LCD_LH133T_24P",             _LCD_X, _LCD_Y, 0, False),
    # Conector del FPC debajo del panel, en el frente. El vidrio termina en
    # y = 24 - 11.7 - 1.56 + 29.22 = 39.96 y el flex llega desplegado
    # 14.93 mas abajo; con rot 180 los contactos del conector caen 1.62 por
    # debajo de su origen, asi que el origen va 12.4 bajo el vidrio, igual
    # que en la placa de 80 (44.60 = 32.22 + 12.4). Cuerpo x 41.7..58.3.
    # rot 180 asume contactos del FPC hacia la placa: LCD_FPC_PIN_ORDER.
    ("J4",  "gamesetup_lcsc:FPC-SMD_24P-P0.50_FPC-05FB-24PH20",
      _LCD_X,   52.40, 180, False),

    # ================================================ FRENTE: controles
    # Cruceta: cuatro tacts 6x6 con paso 8.5mm (era 12.5: no entra al lado
    # de un panel centrado en 100mm). El origen del SW_PUSH_6mm es el pad 1
    # y el cuerpo queda en (x+3.25, y+2.25). Centro de la cruz (18, 24).
    # Reemplaza al NAV5 de 5 vias (2026-10-14): un solo actuador no permite
    # diagonales ni Up+Down+B+A / Down+Left+X+B.
    ("SW1", "Button_Switch_THT:SW_PUSH_6mm",   14.75,   13.25, 0, False),  # UP    cuerpo (18.0, 15.5)
    ("SW3", "Button_Switch_THT:SW_PUSH_6mm",    6.25,   21.75, 0, False),  # LEFT  cuerpo ( 9.5, 24.0)
    ("SW4", "Button_Switch_THT:SW_PUSH_6mm",   23.25,   21.75, 0, False),  # RIGHT cuerpo (26.5, 24.0)
    ("SW2", "Button_Switch_THT:SW_PUSH_6mm",   14.75,   30.25, 0, False),  # DOWN  cuerpo (18.0, 32.5)
    # Rombo X/Y/A/B, espejo de la cruceta: centro (82, 24).
    ("SW5", "Button_Switch_THT:SW_PUSH_6mm",   78.75,   13.25, 0, False),  # X     cuerpo (82.0, 15.5)
    ("SW6", "Button_Switch_THT:SW_PUSH_6mm",   70.25,   21.75, 0, False),  # Y     cuerpo (73.5, 24.0)
    ("SW7", "Button_Switch_THT:SW_PUSH_6mm",   87.25,   21.75, 0, False),  # A     cuerpo (90.5, 24.0)
    ("SW8", "Button_Switch_THT:SW_PUSH_6mm",   78.75,   30.25, 0, False),  # B     cuerpo (82.0, 32.5)
    # L / R: tact ANGULADO en el borde SUPERIOR, en las esquinas, que es
    # donde caen los indices con la placa apaisada. La rotacion NO viaja por
    # el DXF, asi que se fija aca: rot 0 -> actuador hacia -Y.
    # El origen es el PAD 1 y el cuerpo esta 2.25 hacia +X: 9.75 y 85.75
    # dejan los cuerpos en 12 y 88, simetricos respecto de x=50 (el test lo
    # verifica). y=1.89: pads a 1mm del borde, actuador asomando ~2mm.
    ("SW9",  "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
       9.75,    1.89, 0,  False),  # L -> cuerpo x 8.2..15.8
    ("SW10", "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
      85.75,    1.89, 0, False),  # R -> cuerpo x 84.2..91.8
    # SELECT y START bajo el rombo, como en la Micro: cuerpos en (76, 46) y
    # (88, 46), 7.5mm por debajo de B. Select a la izquierda porque es el
    # que cambia de modo mirando la pantalla.
    ("SW12", "Button_Switch_THT:SW_PUSH_6mm",   72.75,   43.75, 0, False),  # SELECT
    ("SW11", "Button_Switch_THT:SW_PUSH_6mm",   84.75,   43.75, 0, False),  # START
    # Slide de encendido en el borde INFERIOR, a la izquierda del conector
    # del flex (J4 empieza en x=41.7; el slide ocupa 19.85..30.15). rot 0 ->
    # actuador hacia +Y, asomando por el borde de abajo. y=57.70: los pads
    # de anclaje quedan a 1mm del borde y el actuador asoma 3.16mm, igual
    # que el 77.70 de la placa de 80.
    ("SW15", "gamesetup_lcsc:SW-TH_SK12D07VG3",             25.00,    57.70, 0, False),

    # ================================================ DORSO: jacks (arriba)
    # Los tres jacks salen por el borde SUPERIOR, entre los gatillos (cuerpos
    # x 8..18 y 84..94): los cables apuntan lejos de las manos. Con flip y
    # rot 180 el barril cruza el borde de arriba; y=3.0 deja los pads a 3mm
    # del canto (espejo del 77.0 de la placa de 80). El cuerpo entra 14.5mm
    # en la placa. Orden: MIDI IN, auriculares, MIDI OUT; el opto queda a la
    # izquierda de J6 y el buffer a la derecha de J7, cada uno con su jack.
    ("J6",  "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal",
      36.00,    3.00, 180, True),   # MIDI IN   cuerpo x 31.4..40.6
    ("J1",  "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal",
      50.00,    3.00, 180, True),   # phones    cuerpo x 45.4..54.6
    ("J7",  "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal",
      64.00,    3.00, 180, True),   # MIDI OUT  cuerpo x 59.4..68.6
    # Opto a rot 0 (patas gull-wing en Y, 10.2mm): x 19.2..26.8, y 1.4..11.6,
    # entre las patas del gatillo L (hasta x 17.8) y las de UP (desde y 12.25).
    # A rot 90 pisaba el pad (21.25, 13.25) de SW1: lo vio check_placement.
    ("U10", "Package_DIP:SMDIP-6_W7.62mm",                 23.00,    6.50, 0, True),
    ("R42", "Resistor_SMD:R_0603_1608Metric",              29.50,    4.00, 90, True),
    ("D3",  "Diode_SMD:D_SOD-123",                         29.50,    9.00, 90, True),
    ("R43", "Resistor_SMD:R_0603_1608Metric",              29.50,   14.00, 90, True),
    ("C56", "Capacitor_SMD:C_0603_1608Metric",             30.50,   18.00, 90, True),
    ("U9",  "Package_TO_SOT_SMD:SOT-353_SC-70-5",          72.50,    6.00, 0, True),
    ("R40", "Resistor_SMD:R_0603_1608Metric",              72.50,    9.50, 0, True),
    ("R41", "Resistor_SMD:R_0603_1608Metric",              72.50,   12.50, 0, True),
    # Deteccion de auriculares, bajo el pad TN de J1 (y 14.6, hasta 15.5) y
    # sobre el nucleo (empieza en y 21).
    ("R15", "Resistor_SMD:R_0603_1608Metric",              44.00,   17.20, 0, True),
    ("R18", "Resistor_SMD:R_0603_1608Metric",              50.00,   17.20, 0, True),
    ("C29", "Capacitor_SMD:C_0603_1608Metric",             56.00,   17.20, 0, True),

    # ================================================ DORSO: USB, carga (abajo-izq)
    # USB-C en el borde INFERIOR con la boca hacia +Y. rot 180 con flip es la
    # hipotesis; check_placement.py avisa si la boca mira adentro, y entonces
    # va rot 0. y=55.4: boca a 0.4mm del canto (la boca esta a 4.22 del
    # origen). Cuerpo x 6.65..17.35; el slide empieza en 19.85.
    ("J2",  "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A",
      12.00,   55.40, 180, True),
    ("R29", "Resistor_SMD:R_0603_1608Metric",               5.00,   51.00, 0, True),
    ("R30", "Resistor_SMD:R_0603_1608Metric",              22.00,   51.00, 0, True),
    # Cargador ETA6096 y su lazo, encima del USB; misma geometria interna que
    # en la placa de 80 (SW al inductor por el camino corto), corrida
    # (+2, +11).
    ("D1",  "Diode_SMD:D_SOD-123F",                        13.00,   37.50, 0, True),
    ("U8",  "gamesetup_lcsc:DFN-10_L3.0-W3.0-P0.50-BL-EP2.4-1",
       8.00,   42.00, 0, True),
    ("C48", "Capacitor_SMD:C_0603_1608Metric",              4.00,   41.00, 90, True),
    ("C49", "Capacitor_SMD:C_0805_2012Metric",             12.20,   41.50, 90, True),
    ("R31", "Resistor_SMD:R_0603_1608Metric",               4.00,   44.40, 90, True),
    ("L4",  "Inductor_SMD:L_1210_3225Metric",               8.00,   46.60, 0, True),
    ("C50", "Capacitor_SMD:C_0603_1608Metric",             12.20,   46.60, 90, True),
    ("D2",  "Diode_SMD:D_SOD-123F",                        16.50,   46.60, 0, True),
    # Bateria: PicoBlade vertical en el margen izquierdo, bajo las patas de
    # LEFT (hasta y 27.25). x=4.0: el courtyard arranca en x 1.0 y los pads
    # de anclaje a 1.45 del canto (a 3.5 el DRC los marcaba en el keepout).
    ("J3",  "Connector_Molex:Molex_PicoBlade_53398-0271_1x02-1MP_P1.25mm_Vertical",
       4.00,   33.00, 90, True),
    # RUN en la esquina superior izquierda y BOOTSEL debajo, los dos a rot 90
    # (x 0.7..6.3): a rot 0 RUN medía 7.6 de ancho y su pad caía a 0.9mm del
    # agujero NPTH del gatillo L (8.5, 4.4). Paso 8.5 en Y: con 7 se pisaban
    # los courtyards. y=5.5: con 4.5 el pad superior caia en el keepout del
    # radio de la esquina (R3). Quedan sobre las patas de LEFT (desde y 20.75).
    ("SW14", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",  3.50,    5.50, 90, True),
    ("SW13", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",  3.50,   14.00, 90, True),
    # Sensado de VBUS y VSYS, entre el cargador y el slide (patas de DOWN
    # hasta y 35.75; slide desde y 53.8).
    ("R35", "Resistor_SMD:R_0603_1608Metric",              22.00,   40.00, 90, True),
    ("R36", "Resistor_SMD:R_0603_1608Metric",              25.00,   40.00, 90, True),
    ("R37", "Resistor_SMD:R_0603_1608Metric",              28.00,   40.00, 90, True),
    ("R38", "Resistor_SMD:R_0603_1608Metric",              22.00,   45.00, 90, True),
    ("C55", "Capacitor_SMD:C_0603_1608Metric",             25.00,   45.00, 90, True),

    # ================================================ DORSO: 3V3 (banda inferior, izq)
    # TPS63001 a la izquierda de la banda inferior, entre el slide (hasta
    # x 30.15) y el DAC. Misma geometria interna que en la placa de 80 (U7 a
    # 180 con L1/L2 enfrentados a L5, dx 4.2: las pistas manuales U7_BB_L1/L2
    # dependen de ESA geometria relativa), corrida (+0, +20.5).
    ("U7",  "Package_SON:Texas_DRC0010J_ThermalVias",      36.00,   54.00, 180, True),
    ("L5",  "Inductor_SMD:L_1210_3225Metric",              40.20,   54.00, 90, True),
    ("C51", "Capacitor_SMD:C_0603_1608Metric",             37.70,   57.40, 0, True),
    ("C52", "Capacitor_SMD:C_0603_1608Metric",             37.70,   50.90, 0, True),
    ("C53", "Capacitor_SMD:C_0603_1608Metric",             41.00,   50.90, 0, True),
    ("R32", "Resistor_SMD:R_0603_1608Metric",              32.80,   50.60, 90, True),
    ("C54", "Capacitor_SMD:C_0603_1608Metric",             35.00,   50.30, 90, True),
    ("R33", "Resistor_SMD:R_0603_1608Metric",              32.80,   53.80, 90, True),
    ("R34", "Resistor_SMD:R_0603_1608Metric",              32.80,   56.90, 90, True),
    # Parlante: header en la columna del borde derecho, bajo A (pads hasta
    # x 94.75, y 27.25). rot 90: x 94.25..99.75, y 29.5..36.5.
    ("J5",  "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
      97.00,   33.00, 90, True),

    # ================================================ DORSO: audio
    # DAC y op-amp en la banda inferior, a la derecha del TPS63001 y detras
    # de J4 (SMD del frente: no estorba). Los 470uF y sus bleeders en la
    # banda derecha, entre el rombo (pads hasta y 35.75) y Select/Start (pads
    # desde y 42.75): 7mm de luz para un cuerpo de 6.6, y lo que asoma cae
    # sobre el anillo de un pad, que es plano. check_placement y el DRC
    # miran pads y courtyards del MISMO lado, asi que esto no choca.
    ("U5",  "gamesetup_lcsc:TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL", 49.00, 53.50, 0, True),
    ("U3",  "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",              62.00, 53.00, 0, True),
    ("C23", "Capacitor_SMD:CP_Elec_6.3x5.4",               74.50,   39.40, 0, True),
    ("C24", "Capacitor_SMD:CP_Elec_6.3x5.4",               85.00,   39.40, 0, True),
    ("R19", "Resistor_SMD:R_0603_1608Metric",              91.50,   37.50, 0, True),
    ("R20", "Resistor_SMD:R_0603_1608Metric",              91.50,   41.50, 0, True),
    # Class-D bajo Select (patas hasta y 49.25), a la izquierda del boost.
    ("U4",  "gamesetup_lcsc:MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL",   74.00, 54.00, 0, True),
    # ================================================ DORSO: boost 5V
    # El lazo del TPS61023 se mueve ENTERO (+29, +50) desde la placa de 80:
    # manual_tracks.py tiene pistas entre U2, L1, C4 y C7 que dependen de la
    # geometria relativa del cluster. Queda en x 77.4..99, y 51.7..57.6.
    ("U2",  "Package_TO_SOT_SMD:SOT-563",                  89.00,   56.00, 0, True),
    ("L2",  "Inductor_SMD:L_1210_3225Metric",              83.80,   56.00, 0, True),
    ("C4",  "Capacitor_SMD:C_0603_1608Metric",             78.20,   56.00, 0, True),
    ("L1",  "Inductor_SMD:L_1210_3225Metric",              93.40,   56.00, 180, True),
    ("C5",  "Capacitor_SMD:C_0805_2012Metric",             93.50,   52.50, 0, True),
    ("C7",  "Capacitor_SMD:C_0603_1608Metric",             97.20,   52.50, 0, True),
    ("R4",  "Resistor_SMD:R_0603_1608Metric",              88.00,   52.50, 0, True),
    ("R5",  "Resistor_SMD:R_0603_1608Metric",              84.20,   52.50, 0, True),
]

# Regiones donde gen_pcb.py empaqueta los pasivos que no estan anclados
# (los del DAC, el op-amp, la suma mono y el class-D: ~40 piezas de 0603).
# Dorso 100x60: esquivan las patas pasantes del frente (con 1mm de radio de
# pad), la franja de jacks (y<19 en x 25..75), el nucleo (x 32..68,
# y 21..49) y los bloques anclados de arriba.
FREE_REGIONS = [
    # El empaquetador recorre las regiones EN ORDEN y pone primero las piezas
    # grandes: la banda del audio va primera para que los desacoplos del DAC
    # y los pasivos del op-amp caigan al lado de sus chips, no a 60mm.
    # Contra el borde las regiones arrancan en 1.5: con 0.5 los pads quedaban
    # a 0.8mm del canto (regla del proyecto: 1.0).
    (31.0, 49.0, 69.5, 58.5),    # banda del audio, bajo el nucleo
    (32.0, 46.3, 69.5, 48.9),    # franja bajo el nucleo: sus zonas terminan en y 40.9
    (69.5, 35.8, 94.5, 43.0),    # banda derecha, alrededor de los 470uF
    (31.0, 16.8, 69.5, 20.9),    # franja entre los jacks y el nucleo
    (40.9,  1.5, 45.1, 14.5),    # entre J6 y J1
    (54.9,  1.5, 59.1, 14.5),    # entre J1 y J7
    (94.5,  1.5, 98.5, 20.0),    # columna derecha, a la derecha del gatillo R
    (95.0, 20.5, 98.5, 29.0),    # columna derecha, a la derecha de A
    (94.5, 37.0, 98.5, 48.5),    # columna derecha, bajo J5
    (20.0, 36.0, 31.0, 39.0),    # bajo DOWN, sobre el sensado de VBUS
    (26.5, 41.0, 31.0, 53.0),    # entre el sensado y el nucleo, sobre el slide
    (6.0,  36.0, 10.5, 39.5),    # bajo DOWN, sobre el cargador
    (1.5,  48.0,  5.5, 58.5),    # margen izquierdo, al lado del USB
    (1.5,  21.0,  4.5, 29.0),    # margen izquierdo, entre BOOTSEL y la bateria
    (74.5,  1.5, 77.5, 13.0),    # entre el buffer MIDI y las patas de X
]

# Nucleo del RP2350A (rp_core.py): U1 en (x, y) del dorso, bloque a rot 90
# como en la placa de 80 (ruteo probado). A rot 90 el bloque ocupa
# x-21..x+15, y-16.5..y+11.5: con (53, 37.5) queda en x 32..68, y 21..49,
# detras del panel, la unica zona sin patas pasantes del frente.
NUCLEO = (53.0, 37.5, 90.0)
