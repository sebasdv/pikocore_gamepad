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

# El modulo LCD mide 27.78 de ancho y su origen de footprint es el pad 1, que
# esta a 6.27 del borde izquierdo del modulo. Para centrarlo en la placa:
#   borde izq del modulo = (90 - 27.78)/2 = 31.11  ->  pad 1 = 37.38
_LCD_X = (BOARD_W - 27.78) / 2 + 6.27
_LCD_Y = 8.0 + 1.60          # 8mm de margen superior + la fila de pines

PLACEMENTS = [
    # ================================================ FRENTE: display
    ("J4",  "gamesetup_fp:LCD_ST7789_240x240_7P",       _LCD_X, _LCD_Y, 0, False),

    # ================================================ FRENTE: controles
    # D-pad en diamante, abajo a la izquierda.
    ("SW1", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  22.50, 100.00, 0, False),  # UP
    ("SW2", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  22.50, 116.00, 0, False),  # DOWN
    ("SW3", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  14.50, 108.00, 0, False),  # LEFT
    ("SW4", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  30.50, 108.00, 0, False),  # RIGHT
    # X/Y/A/B en diamante, abajo a la derecha.
    ("SW5", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  67.50,  75.00, 0, False),  # X
    ("SW6", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  59.50,  83.00, 0, False),  # Y
    ("SW7", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  75.50,  83.00, 0, False),  # A
    ("SW8", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  67.50,  91.00, 0, False),  # B
    # L / R: tact ANGULADO contra el borde, el dedo los aprieta de costado.
    # La rotacion define hacia donde apunta el actuador y NO viaja por el DXF
    # (una cruz no tiene orientacion), asi que se fija aca:
    #    rot  90 -> actuador hacia -X (borde izquierdo)
    #    rot 270 -> actuador hacia +X (borde derecho)
    # Las X salen de que el cuerpo sobresale 3.90mm del origen hacia el
    # actuador: 0 + 3.90 y 90 - 3.90, para que la punta quede justo en el borde.
    ("SW9",  "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
      3.90,  59.00, 90,  False),  # L
    ("SW10", "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
     86.10,  59.00, 270, False),  # R
    # START / SELECT al centro.
    ("SW11", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  32.50,  59.00, 0, False),
    ("SW12", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  57.50,  59.00, 0, False),
    # Slide de encendido en el borde izquierdo, actuador accesible.
    ("SW15", "gamesetup_lcsc:SW-TH_SK12D07VG3",            3.50,   38.00, 270, False),

    # ================================================ DORSO: MCU
    # Huella real de pads: 19.48 x 49.96 (la bbox general de 21.55 x 56.70
    # incluye serigrafia y no sirve para decidir si entra). Va vertical en la
    # franja que el display deja libre a la izquierda; rot 180 pone el USB-C
    # contra el borde SUPERIOR, que es el unico que quedo despejado.
    ("U1",  "gamesetup_fp:RP2350-Plus_Socket",          18.00,  28.00, 180, True),

    # ================================================ DORSO: audio
    # Agrupado a la derecha del display, lejos del MCU y de los controles. El
    # lazo de conmutacion del boost queda arriba de todo, sin cruzar por
    # debajo del DAC ni del op-amp (spec 5.2.1).
    ("U2",  "Package_TO_SOT_SMD:SOT-23-6",              65.00,   6.00, 0, True),
    ("U5",  "gamesetup_lcsc:TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL", 65.00, 20.00, 0, True),
    ("U3",  "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",              66.00, 38.00, 0, True),
    ("U4",  "gamesetup_lcsc:MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL",   81.00, 38.00, 0, True),

    # ================================================ BORDES: conectores
    # OJO: los headers tienen su ORIGEN en el PAD 1, no en el centro, y un
    # footprint VOLTEADO extiende sus pads hacia -Y. O sea que la posicion de
    # aca es el extremo INFERIOR del conector y el cuerpo sube desde ahi. Con
    # la intuicion contraria (+Y) el jack se metia en la fila de SW9/SW10, y
    # el solapamiento no se ve mirando los numeros.
    ("J1",  "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
     86.00, 102.00, 0, True),   # phones    -> pads y 93.5..102.9
    # Parlante abajo a la izquierda.
    ("J5",  "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
     12.00, 124.00, 0, True),
]

# Regiones del DORSO donde gen_pcb.py empaqueta los ~58 pasivos, en este
# orden. Son las zonas que el layout del frente deja libres: el hueco bajo el
# display (entre sus agujeros de montaje, que es donde no hay cobre), la
# franja central por debajo de los expansores, y el borde inferior.
#
# Se declaran aca y no en gen_pcb.py porque son consecuencia del layout, y el
# layout es lo que el usuario ordena en Rhino: si mueve los controles, estas
# regiones son lo primero que hay que revisar.
FREE_REGIONS = [
    (31.0,  12.0, 59.0,  45.0),   # bajo el display, entre sus agujeros
    (31.0,  47.0, 88.0,  55.0),   # franja entre el display y la fila SW9..SW10
    (60.0,   2.0, 88.0,  45.0),   # derecha, alrededor de la etapa de audio
    (36.0,  64.0, 58.0, 128.0),   # columna central, con los expansores
    (60.0,  62.0, 88.0, 101.0),   # derecha media
    (60.0, 115.0, 88.0, 128.0),   # abajo a la derecha
    (2.0,   62.0, 10.0, 128.0),   # borde izquierdo
]
