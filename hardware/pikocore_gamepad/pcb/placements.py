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

# Panel desnudo (ver gen_fp.py): el origen del footprint es el CENTRO del
# area activa. Centrado en X; el borde superior del vidrio (BL) a 3.0mm del
# borde de la placa, que es lo que pide el estudio ergonomico (2026-10-14):
# cuanto mas arriba la imagen, mas lejos quedan los pulgares del vidrio.
_PANEL_TOP = 3.0
_LCD_X = BOARD_W / 2
_LCD_Y = _PANEL_TOP + v("PANEL_AA_OFF_TOP") + v("PANEL_AA") / 2   # 16.26

PLACEMENTS = [
    # ================================================ FRENTE: display
    ("LCD1", "gamesetup_fp:LCD_LH133T_24P",             _LCD_X, _LCD_Y, 0, False),
    # Conector del FPC, en el FRENTE, debajo del panel. El flex sale por el
    # borde inferior del vidrio (y=32.22) y llega desplegado hasta 47.15
    # (PANEL_FPC_LEN), con los contactos en los ultimos 2mm: con rot 180 los
    # pads del conector quedan en y = 44.6 + 1.62 = 46.2, o sea justo donde
    # caen los contactos del flex sin plegarlo. La entrada del conector mira
    # hacia el panel (-Y). Cuerpo x 42.25..57.75: entre Up (termina en 30) y
    # X (empieza en 70), y por encima de Select (empieza en 49).
    # rot 180 asume contactos del FPC hacia la placa: LCD_FPC_PIN_ORDER.
    ("J4",  "gamesetup_lcsc:FPC-SMD_24P-P0.50_FPC-05FB-24PH20",
      _LCD_X,   44.60, 180, False),

    # ================================================ FRENTE: controles
    # D-pad: cuatro tacts 6x6 en cruz, con el cuerpo centrado en X=30 y el
    # mismo paso de 12.5mm que el rombo X/Y/A/B (espejo exacto respecto del
    # centro de la placa, X=50). Reemplaza al NAV5 de 5 vias (2026-10-14):
    # un solo actuador no permite diagonales ni Up+Down+B+A / Down+Left+X+B.
    ("SW1", "Button_Switch_THT:SW_PUSH_6mm",   23.75,   38.45, 0, False),  # UP    cuerpo (27.0, 40.7)
    ("SW3", "Button_Switch_THT:SW_PUSH_6mm",   11.25,   50.95, 0, False),  # LEFT  cuerpo (14.5, 53.2)
    ("SW4", "Button_Switch_THT:SW_PUSH_6mm",   36.25,   50.95, 0, False),  # RIGHT cuerpo (39.5, 53.2)
    ("SW2", "Button_Switch_THT:SW_PUSH_6mm",   23.75,   63.45, 0, False),  # DOWN  cuerpo (27.0, 65.7)
    # X/Y/A/B en diamante, abajo a la derecha. El origen del SW_PUSH_6mm es
    # el pad 1 y el cuerpo esta centrado en (x+3.25, y+2.25): con x=66.75 el
    # cuerpo queda en X=70, espejo del NAV5 (X=30) respecto del centro de la
    # placa de 100mm. Antes (placa de 120) el rombo estaba en x=90.
    ("SW5", "Button_Switch_THT:SW_PUSH_6mm",   69.75,   38.45, 0, False),  # X     cuerpo (73.0, 40.7)
    ("SW6", "Button_Switch_THT:SW_PUSH_6mm",   57.25,   50.95, 0, False),  # Y     cuerpo (60.5, 53.2)
    ("SW7", "Button_Switch_THT:SW_PUSH_6mm",   82.25,   50.95, 0, False),  # A     cuerpo (85.5, 53.2)
    ("SW8", "Button_Switch_THT:SW_PUSH_6mm",   69.75,   63.45, 0, False),  # B     cuerpo (73.0, 65.7)
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
    # Las X de abajo ya vienen compensadas: 20.25 y 75.25 ponen los CUERPOS
    # centrados en 22.50 y 77.50, o sea a 22.50 de cada borde de la placa de
    # 100mm, simetricos respecto del centro X=50 (el test lo verifica).
    # Y=1.87 y no 0.88: con 0.88 los PADS quedaban a 0.01mm del borde, o sea
    # cobre practicamente sobre la linea de corte (la regla del proyecto pide
    # 1.0mm y el min_copper_edge_clearance de KiCad, 0.5). Corridos a 1.87 los
    # pads respetan el milimetro y el actuador igual asoma ~2mm por fuera
    # del borde, que es lo que hace falta para poder apretarlo.
    ("SW9",  "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
       20.25,    1.89, 0,  False),  # L -> cuerpo x 18.70..26.30
    ("SW10", "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
      75.25,    1.89, 0, False),  # R -> cuerpo x 73.70..81.30
    # SELECT y START apilados en la columna central, debajo del panel y del
    # conector del FPC: cualquiera de los dos pulgares llega sin tapar la
    # imagen (estudio ergonomico 2026-10-14). Select arriba porque es el que
    # cambia de modo mirando la pantalla.
    ("SW12", "Button_Switch_THT:SW_PUSH_6mm",   46.75,   48.75, 0, False),  # SELECT cuerpo (50, 51)
    ("SW11", "Button_Switch_THT:SW_PUSH_6mm",   46.75,   60.75, 0, False),  # START  cuerpo (50, 63)
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

    # ================================================ DORSO: USB, carga, 3V3
    # El nucleo del RP2350A NO esta en esta tabla: lo coloca rp_core.py como
    # un bloque rigido copiado de la placa minima oficial (ver NUCLEO abajo).
    # Aca van las piezas de alimentacion, que son de esta placa.
    #
    # USB-C en el canto IZQUIERDO, enfrente de R25/R26 (las 27R del nucleo,
    # en y 18.9-19.9). La boca del footprint esta en y=+4.22 locales; en el
    # dorso con rot 90 ese lado queda hacia -X (con 270 quedaba al reves: los
    # pads de senal contra el canto y la boca mirando adentro, lo detecto
    # check_placement). x=4.6 deja la boca a 0.4mm del canto y los pads THT
    # del blindaje a 3mm.
    ("J2",  "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A",
       4.60,   19.40, 90, True),
    ("R29", "Resistor_SMD:R_0603_1608Metric",               3.00,   12.80, 0, True),
    ("R30", "Resistor_SMD:R_0603_1608Metric",               3.00,   26.00, 0, True),
    # Cargador ETA6096 y su lazo, en la franja izquierda bajo el USB. El nodo
    # SW (pin 5) va al inductor por el camino mas corto, como pide el
    # datasheet en su PCB GUIDELINES.
    ("D1",  "Diode_SMD:D_SOD-123F",                        11.00,   26.50, 0, True),
    ("U8",  "gamesetup_lcsc:DFN-10_L3.0-W3.0-P0.50-BL-EP2.4-1",
       6.00,   31.00, 0, True),
    ("C48", "Capacitor_SMD:C_0603_1608Metric",              2.00,   30.00, 90, True),
    ("C49", "Capacitor_SMD:C_0805_2012Metric",             10.20,   30.50, 90, True),
    ("R31", "Resistor_SMD:R_0603_1608Metric",               2.00,   33.40, 90, True),
    ("L4",  "Inductor_SMD:L_1210_3225Metric",               6.00,   35.60, 0, True),
    ("C50", "Capacitor_SMD:C_0603_1608Metric",             10.20,   35.60, 90, True),
    ("D2",  "Diode_SMD:D_SOD-123F",                        14.50,   35.60, 0, True),
    # Bateria: PicoBlade vertical, en el dorso, al costado de la LiPo.
    ("J3",  "Connector_Molex:Molex_PicoBlade_53398-0271_1x02-1MP_P1.25mm_Vertical",
       6.00,   45.00, 0, True),
    # 3V3: TPS63001 y su lazo, bajo el cristal y a la derecha del D-pad.
    # y >= 30: el nucleo baja hasta y 26.7 en x 32 (C42, desacoplo de 3V3).
    # U7 a 180: en el dorso el footprint queda espejado y a 0 los pines
    # 1-5 (VOUT, L2, PGND, L1, VIN) miraban a la izquierda, lejos de L5; los
    # dos nodos de conmutacion tenian que cruzar bajo el chip y freerouting
    # no los cerraba. A 180 quedan enfrentados a L5, como en el layout de TI:
    # VOUT arriba (C52/C53 encima), VIN abajo (C51 debajo), EN/PS a la
    # izquierda (R33/R34).
    ("U7",  "Package_SON:Texas_DRC0010J_ThermalVias",      36.00,   33.50, 180, True),
    ("L5",  "Inductor_SMD:L_1210_3225Metric",              40.20,   33.50, 90, True),
    ("C51", "Capacitor_SMD:C_0603_1608Metric",             37.70,   36.90, 0, True),
    ("C52", "Capacitor_SMD:C_0603_1608Metric",             37.70,   30.40, 0, True),
    ("C53", "Capacitor_SMD:C_0603_1608Metric",             41.00,   30.40, 0, True),
    ("R32", "Resistor_SMD:R_0603_1608Metric",              32.80,   30.10, 90, True),
    ("C54", "Capacitor_SMD:C_0603_1608Metric",             35.00,   29.80, 90, True),
    ("R33", "Resistor_SMD:R_0603_1608Metric",              32.80,   33.30, 90, True),
    ("R34", "Resistor_SMD:R_0603_1608Metric",              32.80,   36.40, 90, True),
    # BOOTSEL y RUN abajo a la izquierda, en el dorso: son de desarrollo y
    # se alcanzan con un clip o por un agujero del enclosure.
    ("SW13", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",  5.50,   54.00, 90, True),
    ("SW14", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",  5.50,   63.00, 90, True),

    # ================================================ DORSO: audio
    # Agrupado a la derecha del display, lejos del MCU y de los controles. El
    # lazo de conmutacion del boost queda arriba de todo, sin cruzar por
    # debajo del DAC ni del op-amp (spec 5.2.1).
    # SOT-563, NO SOT-23-6: el DRL de TI es SOT-5X3 (2.10x1.35 a paso 0.50,
    # contra 3.60x2.50 a paso 0.95 del SOT-23-6). Estuvo mal aca hasta que el
    # test de divergencia netlist<->placements lo encontro; el netlist siempre
    # dijo SOT-563.
    # Todo el lazo del boost (U2 y sus ocho pasivos, mas abajo) esta 5mm mas
    # a la izquierda que en la placa de 120: el gatillo R paso de x=95 a
    # x=75 y sus patas de anclaje (NPTH D1.30 en x=74.0 y 81.0, y=4.38)
    # caian a <1mm de C7. manual_tracks.py toma la posicion de U2 de aca,
    # asi que mover el chip no desalinea sus pistas manuales.
    ("U2",  "Package_TO_SOT_SMD:SOT-563",                60.00,   6.00, 0, True),
    ("U5",  "gamesetup_lcsc:TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL", 65.00, 20.00, 0, True),
    # U3 en (58,35) y no en (66,38): con el rombo en X=70, los pines de X
    # (SW5) caen en (66.75, 42.5) y quedaban a 0.8mm de los pads 4/5 del
    # SOIC. Aca queda entre la ultima columna de pads del modulo (x=50.6) y
    # el DAC, lejos de todo pasante.
    ("U3",  "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",              58.00, 35.00, 0, True),
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
    # Bajados a y=72.5/75.5: con el rombo en X=73 los pines de B (SW8) caen
    # en (69.75/76.25, 63.45/67.95) y pisaban las R en y=62/65.
    ("R19", "Resistor_SMD:R_0603_1608Metric",              68.00,   72.50, 0, True),
    ("R20", "Resistor_SMD:R_0603_1608Metric",              68.00,   75.50, 0, True),
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
    # x=91 (era 103.5 en la placa de 120): los pads quedan en 91 y 93, a 7mm
    # del borde derecho, y a 10mm de U4.
    ("J5",  "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
      91.00,   13.00, 0, True),
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
    ("L2",  "Inductor_SMD:L_1210_3225Metric",              54.80,    6.00, 0, True),
    ("C4",  "Capacitor_SMD:C_0603_1608Metric",             49.20,    6.00, 0, True),
    # rot 180 para que el pin de BOOST_SW quede del lado de U2. El inductor
    # va entre VIN y SW, y con el pinout real de TI esos dos pines estan en
    # columnas OPUESTAS del chip (3=VIN a la izq, 5=SW a la der). Con L1 sin
    # rotar, su pad de SW quedaba en el extremo lejano y el nodo conmutado
    # —el que hay que mantener corto— era el que daba la vuelta.
    # Asi: U2.5 (SW) -> L1 son 2.3mm. VSYS_F sale por el otro extremo y da un
    # rodeo mas largo, pero es un riel de entrada: la longitud no le duele.
    ("L1",  "Inductor_SMD:L_1210_3225Metric",              64.40,    6.00, 180, True),
    # C5 es 0805 y no 0603: es el bulk de salida del boost, y a 5V un X5R
    # de 0603/6.3V deja ~5uF de los 22. Ver LCSC_PASIVOS en netlist.py.
    ("C5",  "Capacitor_SMD:C_0805_2012Metric",             64.50,    2.50, 0, True),
    ("C7",  "Capacitor_SMD:C_0603_1608Metric",             68.20,    2.50, 0, True),
    # Divisor de realimentacion, corrido a la IZQUIERDA: con el pinout real
    # FB es el pin 1, arriba de la columna izquierda. Antes estaban centrados
    # bajo el chip, que era lo correcto para el pinout equivocado de V1.
    # TI (SLVAES4 seccion 5) pide la red de FB cerca del pin y la traza corta,
    # y sobre todo NO paralela al nodo SW — que aca queda del otro lado.
    ("R4",  "Resistor_SMD:R_0603_1608Metric",              59.00,    2.50, 0, True),
    ("R5",  "Resistor_SMD:R_0603_1608Metric",              55.20,    2.50, 0, True),
]

# Nucleo del RP2350A copiado de la placa minima oficial (rp_core.py): U1 en
# (x, y) del dorso y el bloque rotado `rot` grados despues de voltearlo. Con
# 90 el lado de USB y del regulador de la placa oficial queda hacia el canto
# izquierdo (donde va J2) y el cristal hacia el centro. Ocupa x 7-43, y 4-32:
# el lugar que dejo libre el modulo RP2350-Plus.
NUCLEO = (28.0, 20.5, 90.0)

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
#
# Recalculadas para la placa de 100x80 (2026-10-14). El empaquetador esquiva
# lo ya colocado, asi que las regiones pueden pisar pasantes: solo dicen por
# donde buscar hueco. Las X de los pines del rombo (66.75/73.25, 54.25/60.75,
# 79.25/85.75) y de Select (66.75/73.25) atraviesan al dorso.
FREE_REGIONS = [
    # Dorso, 100x80. Esquivan los pines pasantes del frente, el nucleo del
    # RP2350A (x 5-41, y 4-32) y el bloque de alimentacion de la izquierda.
    (53.0, 10.0, 61.0,  32.0),   # columna entre el nucleo y el DAC
    (70.0,  9.0, 88.0,  35.0),   # derecha del DAC, hasta U4
    (32.0, 38.0, 45.0,  48.0),   # entre Up y Select
    (55.0, 39.0, 68.0,  48.0),   # entre U3 y X, sobre Y
    (32.0, 57.0, 45.0,  76.0),   # entre Down y Start
    (55.0, 57.0, 66.0,  64.0),   # entre Y y el jack
    (78.0, 57.0, 88.0,  76.0),   # derecha de B
    (89.0, 20.0, 97.0,  76.0),   # franja del borde derecho, bajo J5
    (1.0,  67.5, 10.0,  76.0),   # borde izquierdo, bajo RUN
    (13.0, 69.0, 22.0,  76.0),   # bajo el D-pad, a la izquierda del slide
]
