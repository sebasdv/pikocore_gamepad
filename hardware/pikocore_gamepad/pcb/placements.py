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
    # NAV5 (reemplaza el D-pad de 4 tacts): espejado con el diamante X/Y/A/B,
    # mismo eje Y=83. Ver spec 2026-08-11-pikocore-gamepad-nav5-speaker-reloc-design.md.
    ("SW13", "gamesetup_lcsc:SW-TH_WS-1004-ARL10026",      30.00,   55.00, 0, False),
    # X/Y/A/B en diamante, abajo a la derecha.
    ("SW5", "Button_Switch_THT:SW_PUSH_6mm",   90.00,   42.50, 0, False),  # X
    ("SW6", "Button_Switch_THT:SW_PUSH_6mm",   77.50,   55.00, 0, False),  # Y
    ("SW7", "Button_Switch_THT:SW_PUSH_6mm",  102.50,   55.00, 0, False),  # A
    ("SW8", "Button_Switch_THT:SW_PUSH_6mm",   90.00,   67.50, 0, False),  # B
    # L / R: tact ANGULADO en el borde SUPERIOR, que es donde caen los indices
    # con la placa apaisada. La rotacion NO viaja por el DXF (una cruz no tiene
    # orientacion), asi que se fija aca:
    #    rot   0 -> actuador hacia -Y (borde superior)  <-- el caso de hoy
    #    rot  90 -> actuador hacia -X (borde izquierdo)
    #    rot 270 -> actuador hacia +X (borde derecho)
    #
    # SIMETRIA: el origen del footprint es el PAD 1 y NO esta en el centro de
    # la pieza — el cuerpo va de -1.55 a +6.05 en X local, o sea 2.25mm hacia
    # +X del origen. Con los DOS a rot 0 ese desbalance cae del mismo lado en
    # ambos, asi que no hay nada que compensar en Y (que es lo que si hacia
    # falta cuando estaban en los laterales con rot 90/270).
    # Las X de abajo ya vienen compensadas desde el DXF: 20.25 y 95.25 ponen
    # los CUERPOS centrados en 22.50 y 97.50, o sea a 22.50 de cada borde de
    # la placa de 120mm, simetricos respecto del centro X=60.
    # Y=1.87 y no 0.88: con 0.88 los PADS quedaban a 0.01mm del borde, o sea
    # cobre practicamente sobre la linea de corte (la regla del proyecto pide
    # 1.0mm y el min_copper_edge_clearance de KiCad, 0.5). Corridos a 1.87 los
    # pads respetan el milimetro y el actuador igual asoma ~2mm por fuera
    # del borde, que es lo que hace falta para poder apretarlo.
    ("SW9",  "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
       20.25,    1.89, 0,  False),  # L -> cuerpo x 18.70..26.30
    ("SW10", "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
      95.25,    1.89, 0, False),  # R -> cuerpo x 93.70..101.30
    # START / SELECT al centro.
    ("SW11", "Button_Switch_THT:SW_PUSH_6mm",   30.00,   27.39, 0, False),
    ("SW12", "Button_Switch_THT:SW_PUSH_6mm",   90.00,   27.39, 0, False),
    # Slide de encendido en el borde INFERIOR (la placa es apaisada; el borde
    # izquierdo de la version vertical ya no existe como tal).
    # rot 0 -> actuador hacia +Y, o sea asomando por el borde de abajo. Con la
    # rot 270 que traia se salia 3.15mm de la placa: el DXF no lleva rotacion,
    # asi que al mover la cruz quedo la orientacion vieja.
    # Y=77.70 lo lleva lo mas abajo que permite el cobre: el pad mas bajo
    # (los de anclaje, que sobresalen 1.30 del origen) queda en y=79.00, o sea
    # a 1.00mm del borde — el margen del proyecto. El ACTUADOR asoma 3.16mm
    # por fuera de la placa, que es justo lo que se quiere de un slide de
    # encendido: se acciona desde el canto del enclosure.
    # No se puede bajar mas sin violar el clearance a borde de cobre.
    ("SW15", "gamesetup_lcsc:SW-TH_SK12D07VG3",             30.00,    77.70, 0, False),

    # ================================================ DORSO: MCU
    # Huella real de pads: 19.48 x 49.96 (la bbox general de 21.55 x 56.70
    # incluye serigrafia y no sirve para decidir si entra). Va vertical en la
    # franja que el display deja libre a la izquierda; rot 180 pone el USB-C
    # contra el borde SUPERIOR, que es el unico que quedo despejado.
    # HORIZONTAL (rot 90) desde que la placa es apaisada: vertical medía
    # 21.6 x 51.5 y se comia la franja donde van Start (SW11) y el D-pad
    # (SW13), con 3 pads solapados. Rotado mide 51.5 x 21.6.
    #
    # Que no haya solape NO es que el modulo no comparta area con los
    # controles —en una placa de 120x80 con controles en los cuatro bordes eso
    # es imposible— sino que sus PADS no chocan: horizontal, los pines quedan
    # en dos filas separadas 17.8mm (y ~17.7 y ~37.3) y entre ellas hay una
    # franja libre donde SW11 cae comodo. El bbox de U1 tambien pisa el del
    # LCD en x 46..51.6, pero los pads de J4 estan todos en y 8.75..10.45, o
    # sea muy por encima de la primera fila de U1.
    #
    # X=26.50 lo deja practicamente donde estaba (24.98): el modulo sigue a la
    # izquierda, que es lo que pedia el placement de Rhino.
    # rot 270 y no 90: las dos dejan el modulo horizontal, pero 90 pone el
    # USB-C en x=49, o sea en mitad de la placa, donde no se puede enchufar
    # nada. Con 270 el conector queda contra el borde IZQUIERDO (x~4), que es
    # el unico borde largo que no tiene controles.
    ("U1",  "gamesetup_fp:RP2350-Plus_Socket",           26.50,   27.50, 270, True),

    # ================================================ DORSO: audio
    # Agrupado a la derecha del display, lejos del MCU y de los controles. El
    # lazo de conmutacion del boost queda arriba de todo, sin cruzar por
    # debajo del DAC ni del op-amp (spec 5.2.1).
    # SOT-563, NO SOT-23-6: el DRL de TI es SOT-5X3 (2.10x1.35 a paso 0.50,
    # contra 3.60x2.50 a paso 0.95 del SOT-23-6). Estuvo mal aca hasta que el
    # test de divergencia netlist<->placements lo encontro; el netlist siempre
    # dijo SOT-563.
    ("U2",  "Package_TO_SOT_SMD:SOT-563",                65.00,   6.00, 0, True),
    ("U5",  "gamesetup_lcsc:TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL", 65.00, 20.00, 0, True),
    ("U3",  "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",              66.00, 38.00, 0, True),
    ("U4",  "gamesetup_lcsc:MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL",   81.00, 38.00, 0, True),

    # ================================================ BORDES: conectores
    # Jack de audifonos, AL DORSO como el resto del audio (op-amp, DAC,
    # class-D): es una pieza de la cadena analogica, no un control del panel.
    #
    # Footprint OFICIAL de KiCad 9 (Connector_Audio), no uno propio — ver la
    # nota en netlist.py sobre por que se descarto el que se habia dibujado.
    # Sus pads se identifican por funcion (S/T/R/TN/RN), no por numero.
    #
    # Con flip=True KiCad espeja en Y, asi que el barril —que sin flip apunta
    # a -Y— sale hacia +Y. Con rot=0 y Y=77.00 el barril cruza el borde
    # INFERIOR y el cuerpo queda dentro de la placa; los pads quedan a 3.00mm
    # del borde. Verificado en el render, no deducido:
    #   "$KICLI" pcb render --side bottom -o /tmp/j.png pikocore_gamepad.kicad_pcb
    ("J1",  "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal",
      61.70,   77.00, 0, True),   # phones -> barril por el borde inferior
    # Bleeders de acoplo y filtro de deteccion. Se anclan porque la grilla
    # automatica los mandaba a (85.5, 11..17), o sea a ~60mm del jack: son
    # tres piezas que cuelgan de JACK_L / JACK_R / JACK_DET, y ahi arriba
    # convertian esas tres nets en stubs largos que hay que rutear igual.
    # A 20kHz la distancia da lo mismo electricamente; lo que se ahorra es
    # ~180mm de pista y el trabajo del ruteador.
    #
    # R19/R20 van en la franja vacia entre el jack y la fila de SW6: J1
    # termina en x=65.10, asi que x=68.00 deja 1.67mm de aire.
    ("R19", "Resistor_SMD:R_0603_1608Metric",              68.00,   62.00, 0, True),
    ("R20", "Resistor_SMD:R_0603_1608Metric",              68.00,   65.00, 0, True),
    # C29 al lado de R18, en el hueco a la izquierda de su fila.
    ("C29", "Capacitor_SMD:C_0603_1608Metric",             67.53,   53.77, 0, True),
    # Parlante: header en el dorso, al lado de U4 (el class-D que lo maneja),
    # NO debajo del modulo RP2350-Plus.
    #
    # ANTES estaba en (18, 30), o sea dentro de la huella de U1, apoyandose en
    # que el modulo deja libre la franja central entre sus dos filas de pines.
    # En COBRE eso es cierto (los pads de U1 estan en X=9.11 y X=26.89, y la
    # separacion minima a los pads de J5 era de 5.44mm), pero en ALTURA no
    # cierra: el JST PH vertical mide 8.0mm y el socket 2x20 levanta el modulo
    # ~8.5mm, o sea 0.5mm de luz — y eso sin contar el conector HEMBRA del
    # cable, que se enchufa por arriba y suma varios mm mas. El cable del
    # parlante no se podria conectar con el modulo puesto.
    # El DRC lo venia reportando como courtyards_overlap J5<->U1 y se estaba
    # leyendo como ruido; era el sintoma correcto de un choque mecanico real.
    #
    # La posicion nueva queda a 6.5mm de U4, fuera de la huella del LCD (que
    # esta en el frente, x 31..59), asi que el cable sale sin pelear con nada.
    # El parlante fisico se atornilla al enclosure y no a la PCB.
    ("J5",  "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
     103.50,   13.00, 0, True),
    # ============================================ DORSO: lazo del boost
    # Estos ocho iban a la grilla automatica de gen_pcb.py, que ordena por
    # tamano y busca hueco: no sabe que pertenecen al mismo circuito. El
    # resultado medido era el inductor a 26.8mm de su chip, C5/C7 a ~40mm y
    # R4/R5 a ~45mm, con BOOST_SW —el nodo que conmuta a ~1MHz— midiendo
    # 30.7mm de pista. En un boost eso es una antena, y esta placa tiene audio
    # analogico al lado.
    #
    # Se anclan como un cluster siguiendo la topologia del circuito, no la
    # geometria: U2 tiene VIN en sus pines 1-3 (lado -X) y SW/VOUT/FB en los
    # 4-6 (lado +X), asi que la entrada va a la izquierda y la salida a la
    # derecha, y las pistas no se cruzan.
    #
    #   C4 -- L2 --> [U2] --> L1 (BOOST_SW: 3.7mm)
    #                  |
    #             R5 - R4 (divisor FB)   C5 - C7 (bulk de salida)
    #
    # Toda la fila de abajo va en y=2.50 y el eje del chip en y=6.00: la
    # franja util es y < 8.0 porque en y=9.60 estan los pads THT del LCD, que
    # perforan la placa aunque el modulo este en el frente.
    ("L2",  "Inductor_SMD:L_1210_3225Metric",              59.80,    6.00, 0, True),
    ("C4",  "Capacitor_SMD:C_0603_1608Metric",             54.20,    6.00, 0, True),
    # rot 180 para que el pin de BOOST_SW quede del lado de U2. El inductor
    # va entre VIN y SW, y con el pinout real de TI esos dos pines estan en
    # columnas OPUESTAS del chip (3=VIN a la izq, 5=SW a la der). Con L1 sin
    # rotar, su pad de SW quedaba en el extremo lejano y el nodo conmutado
    # —el que hay que mantener corto— era el que daba la vuelta.
    # Asi: U2.5 (SW) -> L1 son 2.3mm. VSYS_F sale por el otro extremo y da un
    # rodeo mas largo, pero es un riel de entrada: la longitud no le duele.
    ("L1",  "Inductor_SMD:L_1210_3225Metric",              69.40,    6.00, 180, True),
    # C5 es 0805 y no 0603: es el bulk de salida del boost, y a 5V un X5R
    # de 0603/6.3V deja ~5uF de los 22. Ver LCSC_PASIVOS en netlist.py.
    ("C5",  "Capacitor_SMD:C_0805_2012Metric",             69.50,    2.50, 0, True),
    ("C7",  "Capacitor_SMD:C_0603_1608Metric",             73.20,    2.50, 0, True),
    # Divisor de realimentacion, corrido a la IZQUIERDA: con el pinout real
    # FB es el pin 1, arriba de la columna izquierda. Antes estaban centrados
    # bajo el chip, que era lo correcto para el pinout equivocado de V1.
    # TI (SLVAES4 seccion 5) pide la red de FB cerca del pin y la traza corta,
    # y sobre todo NO paralela al nodo SW — que aca queda del otro lado.
    ("R4",  "Resistor_SMD:R_0603_1608Metric",              64.00,    2.50, 0, True),
    ("R5",  "Resistor_SMD:R_0603_1608Metric",              60.20,    2.50, 0, True),
]

# Regiones del DORSO donde gen_pcb.py empaqueta los ~58 pasivos, en este
# orden. Son las zonas que el layout del frente deja libres: el hueco bajo el
# display (entre sus agujeros de montaje, que es donde no hay cobre), la
# franja central por debajo de los expansores, y el borde inferior.
#
# Se declaran aca y no en gen_pcb.py porque son consecuencia del layout, y el
# layout es lo que el usuario ordena en Rhino: si mueve los controles, estas
# regiones son lo primero que hay que revisar.
#
# STALE a proposito tras la Task 5 del plan de fork (remocion de los
# expansores PCF8574): las menciones a "los expansores" de abajo describen un
# layout que ya no tiene ningun expansor en esa zona. No se recalculo porque
# este bloque entero lo reescribe parse_dxf.py en el proximo ciclo de Rhino —
# tocar las coordenadas a mano aca se perderia igual. Ver docs/superpowers/
# plans/2026-08-11-pikocore-gamepad-pcb-fork.md Task 5.
#
# Y maximo recortado a 101 (antes 128) al bajar BOARD_H de 130 a 105 (ver
# docs/superpowers/plans/2026-08-11-pikocore-gamepad-nav5-speaker-reloc.md
# Task 4): sin este recorte, gen_pcb.py podia empaquetar pasivos fuera del
# contorno de la placa. La region "abajo a la derecha" (que arrancaba en
# Y=115, ya fuera de la placa nueva) se elimino entera en vez de recortarse.
FREE_REGIONS = [
    (31.0,  12.0, 59.0,  45.0),   # bajo el display, entre sus agujeros
    (31.0,  47.0, 88.0,  55.0),   # franja entre el display y la fila SW9..SW10
    (60.0,   2.0, 88.0,  45.0),   # derecha, alrededor de la etapa de audio
    (36.0,  64.0, 58.0,  78.0),   # columna central (antes con los expansores, ver nota arriba)
    (60.0,  62.0, 88.0,  78.0),   # derecha media
    (2.0,   62.0, 10.0,  78.0),   # borde izquierdo

]
