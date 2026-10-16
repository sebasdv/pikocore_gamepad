#!/usr/bin/env python3
"""Simbolos e instancias del esquematico V2. FUENTE DE VERDAD del netlist.

Python puro: gen_sch.py lo consume para escribir gamesetup.kicad_sch, y los
checkers de checks/ lo consumen para las puertas G-2 y G-5.

A diferencia de V1, aca NO hay un segundo script que agregue componentes
despues. V1 necesitaba correr add_nav2_sch.py despues de gen_sch.py, y
olvidarlo dejaba el esquematico sin el subsistema nav2 sin ningun error
visible. Todo vive en esta tabla.

Formato de SYMS:
  pins: (numero, nombre, px, py, angulo) en coords de editor de simbolos
        (Y hacia arriba). angulo 0 = pin del lado izquierdo, 180 = derecho.

Formato de INSTANCES:
  (simbolo, ref, value, x, y, {pin: net}, {props})
  props["FP"]   = footprint "lib:nombre"
  props["LCSC"] = codigo de parte para el BOM de JLCPCB
"""
import params
import pinmap

NC = "<NC>"

def _mcu_pin_geometry():
    """Los 61 pines del RP2350A (QFN-60 + pad expuesto), en dos columnas: 1-31
    bajando por la izquierda, 32-61 subiendo por la derecha. Los nombres salen
    de pinmap.RP2350A_PINS, que es donde esta la verificacion."""
    nums = sorted(pinmap.RP2350A_PINS)
    izq, der = nums[:31], nums[31:]
    out = [(str(n), pinmap.RP2350A_PINS[n], -17.78, 38.1 - 2.54 * k, 0)
           for k, n in enumerate(izq)]
    out += [(str(n), pinmap.RP2350A_PINS[n], 17.78, -38.1 + 2.54 * k, 180)
            for k, n in enumerate(der)]
    return out


def _usb_c_pins():
    """Contactos A a la izquierda, B y el blindaje a la derecha."""
    a = ["A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12"]
    b = ["B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12", "S1"]
    return ([(n, n, -10.16, 17.78 - 2.54 * k, 0) for k, n in enumerate(a)] +
            [(n, n, 10.16, 17.78 - 2.54 * k, 180) for k, n in enumerate(b)])


def _left_pins(names, x=-7.62, step=2.54):
    """Pines en una sola columna a la izquierda, numerados 1..n."""
    y0 = step * (len(names) - 1) / 2
    return [(str(i + 1), n, x, y0 - step * i, 0) for i, n in enumerate(names)]


def _dual_pins(left, right, x=7.62, step=2.54):
    """Encapsulado tipo DIP: `left` baja por la izquierda numerando 1..n,
    `right` sube por la derecha continuando la numeracion. Es el orden fisico
    de un DIP/SOIC/TSSOP, asi que los numeros de pin salen correctos solos."""
    y0 = step * (len(left) - 1) / 2
    out = [(str(i + 1), n, -x, y0 - step * i, 0) for i, n in enumerate(left)]
    out += [(str(len(left) + i + 1), n, x, -y0 + step * i, 180)
            for i, n in enumerate(right)]
    return out


SYMS = {
    "RP2350A": dict(
        ref="U", w=15.24, h=40.64,
        desc="Raspberry Pi RP2350A, QFN-60 7x7 paso 0.4mm + pad expuesto a GND. "
             "Pinout verificado contra el simbolo de KiCad 10 y la placa minima "
             "oficial (ver pinmap.RP2350A_PINS). Regulador interno de 1V1 con "
             "L 3.3uH Abracon AOTA y el layout copiado de la placa minima.",
        ds="https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf",
        pins=_mcu_pin_geometry(),
    ),
    "W25Q128": dict(
        ref="U", w=10.16, h=7.62,
        desc="Flash QSPI 16MB Winbond W25Q128JVSIQ, SOIC-8 208mil. Pinout de "
             "la placa minima oficial (U3): 1=CS 2=IO1 3=IO2 4=GND 5=IO0 "
             "6=CLK 7=IO3 8=VCC.",
        ds="https://www.winbond.com/",
        pins=_dual_pins(["CS", "IO1", "IO2", "GND"],
                        ["IO0", "CLK", "IO3", "VCC"]),
    ),
    "XTAL4": dict(
        ref="Y", w=7.62, h=5.08,
        desc="Cristal 12MHz Abracon ABM8-272-T3 (3.2x2.5, 4 pads). 1 y 3 son el "
             "cristal, 2 y 4 la tapa a GND. El recomendado por Raspberry Pi; "
             "15pF por lado y 1k en serie en XOUT, igual que la placa minima.",
        ds="https://abracon.com/",
        pins=[("1", "X1", -7.62, 2.54, 0), ("2", "GND", -7.62, -2.54, 0),
              ("3", "X2", 7.62, 2.54, 180), ("4", "GND", 7.62, -2.54, 180)],
    ),
    "TPS63001": dict(
        ref="U", w=10.16, h=10.16,
        desc="Buck-boost TI TPS63001DRCR, salida FIJA 3.3V hasta 1.2A, VIN "
             "1.8-5.5V, VSON-10 3x3. Pinout verificado contra SLVS520C: 1=VOUT "
             "2=L2 3=PGND 4=L1 5=VIN 6=EN 7=PS/SYNC 8=VINA 9=GND 10=FB (a VOUT "
             "en la version fija), pad expuesto (11) a PGND. Reemplaza al "
             "MP28164 del modulo, que no tiene huella en KiCad ni en EasyEDA.",
        ds="https://www.ti.com/lit/ds/symlink/tps63001.pdf",
        pins=_dual_pins(["VOUT", "L2", "PGND", "L1", "VIN"],
                        ["EN", "PS", "VINA", "GND", "FB"]) +
        [("11", "EP", 0.0, -10.16, 90)],
    ),
    "ETA6096": dict(
        ref="U", w=10.16, h=10.16,
        desc="Cargador LiPo conmutado ETA6096D3K, 4.2V, DFN3x3-10. Pinout "
             "verificado contra su datasheet: 1=VIN 2=PMID 3=PGND 4=NC 5=SW "
             "6=BATS 7=AGND 8=ISET 9=STAT 10=AGND, pad expuesto (11) AGND. "
             "El mismo que trae el modulo RP2350-Plus.",
        ds="https://www.lcsc.com/product-detail/C7465538.html",
        pins=_dual_pins(["VIN", "PMID", "PGND", "NC", "SW"],
                        ["BATS", "AGND", "ISET", "STAT", "AGND"]) +
        [("11", "EP", 0.0, -10.16, 90)],
    ),
    "USB_C16": dict(
        ref="J", w=10.16, h=20.32,
        desc="Receptaculo USB-C 16P HCTL HC-TYPE-C-16P-01A. Pads por nombre de "
             "contacto USB (A1..B12) como el footprint oficial de KiCad; S1 es "
             "el blindaje. Solo USB 2.0: SBU sin conectar.",
        ds="https://www.lcsc.com/product-detail/C2894897.html",
        pins=_usb_c_pins(),
    ),
    "D_Schottky": dict(
        ref="D", w=2.54, h=7.62,
        desc="Schottky MBR230LSFT1G (30V 2A, SOD-123FL). Pin 1 = CATODO, como "
             "todos los footprints de diodo de KiCad (D_SOD-123F); pin 2 = anodo.",
        ds="https://www.lcsc.com/product-detail/C126673.html",
        pins=[("1", "K", 5.08, 0.0, 180), ("2", "A", -5.08, 0.0, 0)],
    ),
    "D_1N4148": dict(
        ref="D", w=2.54, h=7.62,
        desc="Diodo de senal 1N4148W (SOD-123). Pin 1 = CATODO, como todos los "
             "footprints de diodo de KiCad; pin 2 = anodo. Antiparalelo al LED "
             "del opto de MIDI IN: protege contra un cable con polaridad al reves.",
        ds="",
        pins=[("1", "K", 5.08, 0.0, 180), ("2", "A", -5.08, 0.0, 0)],
    ),
    "H11L1": dict(
        ref="U", w=10.16, h=10.16,
        desc="Optoacoplador con salida Schmitt (onsemi H11L1M, SMDIP-6). Vcc "
             "minimo 3V: funciona a 3V3. PINOUT SIN VERIFICAR contra el "
             "datasheet (tomado de memoria): 1 anodo, 2 catodo, 3 NC, "
             "4 salida (colector abierto), 5 GND, 6 Vcc.",
        ds="",
        pins=[("1", "A", -10.16, 2.54, 0), ("2", "K", -10.16, 0.0, 0),
              ("3", "NC", -10.16, -2.54, 0), ("4", "VO", 10.16, 0.0, 180),
              ("5", "GND", 10.16, -2.54, 180), ("6", "VCC", 10.16, 2.54, 180)],
    ),
    "LVC1G17": dict(
        ref="U", w=7.62, h=7.62,
        desc="Buffer Schmitt de una compuerta SN74LVC1G17 (SC-70-5 / DCK). "
             "Toma los 5mA del lazo MIDI en vez del GPIO. PINOUT VERIFICADO "
             "contra el datasheet de TI SCES351Y (rev. octubre 2025, pagina 3, "
             "tabla Pin Functions, columna DBV/DCK/DRL/DPW): 1 NC, 2 A, 3 GND, "
             "4 Y, 5 VCC. VCC 1.65-5.5V; IOL/IOH 16mA a 3V (el lazo MIDI pide 5).",
        ds="https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf",
        pins=[("1", "NC", -7.62, 2.54, 0), ("2", "A", -7.62, 0.0, 0),
              ("3", "GND", -7.62, -2.54, 0), ("4", "Y", 7.62, 0.0, 180),
              ("5", "VCC", 7.62, 2.54, 180)],
    ),
    "SW_SMD": dict(
        ref="SW", w=7.62, h=5.08,
        desc="Pulsador SMD 5.1x5.1 XKB TS-1187A (BOOTSEL / RUN). Pads 1,1,2,2 "
             "en el footprint de KiCad: 1 contra 2 cruza el contacto.",
        ds="https://www.lcsc.com/product-detail/C318884.html",
        pins=[("1", "A", -7.62, 0.0, 0), ("2", "B", 7.62, 0.0, 180)],
    ),
    "TestPoint": dict(
        ref="TP", w=2.54, h=2.54,
        desc="Pad de prueba de 1mm (SWD).", ds="",
        pins=[("1", "TP", -5.08, 0.0, 0)],
    ),
    "Conn_Bat": dict(
        ref="J", w=5.08, h=5.08,
        desc="Conector de bateria Molex PicoBlade 1.25mm 2P vertical SMD "
             "(compatible MX1.25). 1 = +, 2 = -, MP = lenguetas de anclaje. "
             "OJO: las LiPo con este conector vienen en las dos polaridades.",
        ds="",
        pins=[("1", "BAT+", -7.62, 2.54, 0), ("2", "BAT-", -7.62, 0.0, 0),
              ("MP", "MP", -7.62, -2.54, 0)],
    ),
    "LCD_FPC24": dict(
        ref="J", w=12.7, h=35.56,
        desc="Conector FPC 24P a 0.5mm (XUNPU FPC-05FB-24PH20, flip-top, "
             "contactos de las dos caras) para el panel DM-TFT13-377 de 24 "
             "pines. Pinout del datasheet del panel (LH133T-IF05, rev C): "
             "1=LEDA 2=LEDK 3=GND 4=VDD 5=VDDIO 6=IM(1=4-SPI) 7=RESET 8=CS "
             "9=SCL 10=D/C 11=RD 12=SDA 13..20=DB0..DB7 21=TE 22=NC 23/24=GND. "
             "25/26 son las lenguetas de anclaje del conector. CS va A MASA: "
             "siempre seleccionado, como el modulo de 7 pines que reemplaza. "
             "ORDEN DE PINES SIN VERIFICAR contra la pieza (LCD_FPC_PIN_ORDER "
             "en params.py): si el FPC lleva los contactos hacia arriba, el "
             "orden se espeja y J4 va a rot 0 en vez de 180.",
        ds="https://cdn.shopify.com/s/files/1/0264/7629/files/DM-TFT13-377P24.pdf",
        pins=_dual_pins(["LEDA", "LEDK", "GND", "VDD", "VDDIO", "IM", "RESET",
                         "CS", "SCL", "D/C", "RD", "SDA", "DB0"],
                        ["DB1", "DB2", "DB3", "DB4", "DB5", "DB6", "DB7", "TE",
                         "NC", "GND", "GND", "MP", "MP"]),
    ),
    "LCD_PANEL": dict(
        ref="LCD", w=12.7, h=12.7,
        desc="Panel IPS 1.3in 240x240 ST7789VW desnudo, DisplayModule "
             "DM-TFT13-377 variante 24 pines (LH133T-IF05). Pieza MECANICA: "
             "sin pines, se pega al frente de la placa y se conecta por J4. "
             "Solo existe para que la placa tenga su contorno, el area activa "
             "y la cola del FPC (enclosure y Rhino). Se compra aparte, no la "
             "monta JLCPCB.",
        ds="https://displaymodule.com/products/1-3-inch-ips-display-240x240-with-spi",
        pins=[],
    ),
    "Q_NMOS": dict(
        ref="Q", w=7.62, h=7.62,
        desc="MOSFET canal N en SOT-23 (2N7002). Pinout SOT-23 estandar: "
             "1=G 2=S 3=D, igual que el footprint Package_TO_SOT_SMD:SOT-23 "
             "de KiCad. Interruptor del backlight del panel.",
        ds="https://www.lcsc.com/product-detail/C8545.html",
        pins=[("1", "G", -7.62, 0.0, 0), ("2", "S", 7.62, -2.54, 180),
              ("3", "D", 7.62, 2.54, 180)],
    ),
    "SW_Push": dict(
        ref="SW", w=7.62, h=5.08,
        desc="Tact switch 6x6mm THT. Fisicamente tiene 4 patas, pero son DOS "
             "PARES cortocircuitados internamente y el contacto une los pares "
             "— el datasheet del tact comprado lo dibuja como 1-2 y 3-4. "
             "El simbolo declara 2 pines y no 4 porque el footprint oficial de "
             "KiCad (SW_PUSH_6mm) numera sus cuatro pads como 1,1,2,2: cada "
             "numero aparece dos veces, uno por pata del mismo par. Asi el "
             "cableado diagonal —que es lo que garantiza cruzar el contacto— "
             "queda imposible de equivocar, porque cualquier pad 1 con "
             "cualquier pad 2 ya cruza.",
        ds="",
        pins=[("1", "A", -7.62, 0.0, 0), ("2", "B", 7.62, 0.0, 180)],
    ),
    "SW_Push_RA": dict(
        ref="SW", w=7.62, h=5.08,
        desc="Tact switch RIGHT ANGLE (C&K PTS645 o equivalente), para los "
             "gatillos L y R. A diferencia del vertical tiene SOLO DOS pines "
             "electricos: los otros dos contactos del footprint son patas de "
             "anclaje mecanico sin numerar, con taladro de 1.30mm (mas gordo "
             "que los 0.99 de senal). Esas patas son lo que aguanta el empuje "
             "lateral del dedo, que es la carga que recibe un gatillo.",
        ds="",
        pins=[("1", "A", -7.62, 0.0, 0), ("2", "B", 7.62, 0.0, 180)],
    ),
    "SK12D07": dict(
        ref="SW", w=7.62, h=7.62,
        desc="Slide SPDT THT SK12D07VG3. Pin 2 = comun (centro); 1/3 = throws; "
             "4/5 = patas de anclaje mecanico, que van a GND.",
        ds="https://www.lcsc.com/product-detail/C431547.html",
        pins=_left_pins(["A", "COM", "B", "MNT", "MNT"]),
    ),

    # ================================================================ audio
    # ATENCION: los tres pinouts de abajo se COPIAN de V1, donde ya se
    # verificaron contra datasheet y llegaron a una placa ruteada con DRC
    # limpio. No reescribirlos de memoria — un pinout de DAC equivocado es una
    # placa muerta, y la version "de memoria" de este archivo tenia el SCK y
    # el XSMT en pines que no existen.
    "PCM5102A": dict(
        ref="U", w=12.7, h=15.24,
        desc="DAC I2S estereo, TSSOP-20 paso 0.65mm. SCK a GND activa el PLL "
             "interno desde BCK: no hace falta MCLK. FMT/FLT/DEMP a GND = I2S "
             "normal, filtro normal, sin de-emphasis. Salida DirectPath "
             "centrada EN MASA por el charge pump (CAPP/CAPM/VNEG): +-2.8V sin "
             "offset DC, y por eso el buffer siguiente es inversor y con "
             "entrada acoplada. Pinout verificado en V1 contra el simbolo "
             "oficial de KiCad (PCM5100) y TI SLAS859C.",
        ds="https://www.ti.com/lit/ds/symlink/pcm5102a.pdf",
        pins=[("1", "CPVDD", -15.24, 12.7, 0), ("2", "CAPP", -15.24, 10.16, 0),
              ("3", "CPGND", -15.24, 7.62, 0), ("4", "CAPM", -15.24, 5.08, 0),
              ("5", "VNEG", -15.24, 2.54, 0), ("8", "AVDD", -15.24, 0.0, 0),
              ("9", "AGND", -15.24, -2.54, 0), ("20", "DVDD", -15.24, -5.08, 0),
              ("19", "DGND", -15.24, -7.62, 0), ("18", "LDOO", -15.24, -10.16, 0),
              ("12", "SCK", 15.24, 12.7, 180), ("13", "BCK", 15.24, 10.16, 180),
              ("14", "DIN", 15.24, 7.62, 180), ("15", "LRCK", 15.24, 5.08, 180),
              ("16", "FMT", 15.24, 2.54, 180), ("11", "FLT", 15.24, 0.0, 180),
              ("10", "DEMP", 15.24, -2.54, 180), ("17", "XSMT", 15.24, -5.08, 180),
              ("6", "OUTL", 15.24, -7.62, 180), ("7", "OUTR", 15.24, -10.16, 180)],
    ),
    "PT2308": dict(
        ref="U", w=10.16, h=12.7,
        desc="Driver de auriculares Class AB estereo, SOIC-8 (Princeton "
             "PT2308-S, compatible con el TDA1308). Vdd 3.0-7.0V de "
             "alimentacion SIMPLE y carga minima de 8 ohm, asi que los 32 ohm "
             "de unos auriculares entran con margen: ~60mW en 32 ohm a 5V, "
             "unos 61mA de pico. THD 0.001%, S/N 110dB. "
             "REEMPLAZA al NJM4556AD que traia V1: ese op-amp NO existe en "
             "SOIC-8 —toda su familia SMD viene en DMP8, de cuerpo 5.0mm "
             "contra 3.9mm— y habria obligado a dibujar un footprint propio. "
             "El pinout es el ESTANDAR de op-amp dual, identico al del "
             "NJM4556A pin por pin, asi que el cableado no cambia: "
             "1=OUT1 2=IN1- 3=IN1+ 4=VSS 5=IN2+ 6=IN2- 7=OUT2 8=VDD.",
        ds="https://www.princeton.com.tw/Portals/0/activeforums_Attach/PT2308-s.pdf",
        pins=[("1", "OUTA", -12.7, 6.35, 0), ("2", "INA-", -12.7, 3.81, 0),
              ("3", "INA+", -12.7, 1.27, 0), ("4", "V-", -12.7, -1.27, 0),
              ("5", "INB+", 12.7, 6.35, 180), ("6", "INB-", 12.7, 3.81, 180),
              ("7", "OUTB", 12.7, 1.27, 180), ("8", "V+", 12.7, -1.27, 180)],
    ),
    "PAM8302A": dict(
        ref="U", w=8.89, h=12.7,
        desc="Class-D mono 2.5W, MSOP-8. Corre directo de VSYS (2.0-5.5V), NO "
             "del riel de 5V: a todo volumen pide cientos de mA y cargaria el "
             "boost. Salida BTL: VO+ y VO- son las dos patas del puente y "
             "NINGUNA va a masa, asi que no se puede conectar a un jack con "
             "masa comun. Pinout verificado en V1 contra Diodes DS41333.",
        ds="https://www.diodes.com/assets/Datasheets/PAM8302A.pdf",
        pins=[("1", "SD", -11.43, 6.35, 0), ("2", "NC", -11.43, 3.81, 0),
              ("3", "IN+", -11.43, 1.27, 0), ("4", "IN-", -11.43, -1.27, 0),
              ("5", "VO+", 11.43, 6.35, 180), ("6", "VDD", 11.43, 3.81, 180),
              ("7", "GND", 11.43, 1.27, 180), ("8", "VO-", 11.43, -1.27, 180)],
    ),

    # ------------------------------------------------- partes nuevas de V2
    "TPS61023": dict(
        ref="U", w=10.16, h=10.16,
        desc="Boost sincronico, SOT-563 (encapsulado DRL de TI), conmuta 1MHz "
             "con Vin>1.5V (lejos de la banda de audio). Alimenta SOLO al "
             "PT2308: el riel analogico tiene que ser fijo y no seguir a la "
             "bateria. Vin 0.5-5.5V, Vout ajustable 2.2-5.5V. "
             "PINOUT VERIFICADO contra TI SLVSF14B (agosto 2020), seccion 5 "
             "Pin Configuration and Functions, Figura 5-1 DRL Package 6-Pin "
             "SOT563 Top View: 1=FB 2=EN 3=VIN 4=GND 5=SW 6=VOUT. "
             "El simbolo de V1 estaba MAL —declaraba VIN/GND/EN + FB/VOUT/SW, "
             "o sea 5 de los 6 pines corridos— y el cableado seguia ese error: "
             "EN habria quedado a masa, que deja el chip apagado para siempre, "
             "y GND en el pin de realimentacion.",
        ds="https://www.ti.com/lit/ds/symlink/tps61023.pdf",
        pins=_dual_pins(["FB", "EN", "VIN"], ["GND", "SW", "VOUT"]),
    ),
    # ---------------------------------------------------------- conectores
    "JACK_AUDIO": dict(
        ref="J", w=7.62, h=12.70,
        desc="Jack 3.5mm estereo THT, CUI/Same Sky SJ1-3535NG (horizontal, "
             "5 pines). Contacto de deteccion NC: el pin DET va a JACK_DET "
             "con pull-up y el firmware apaga el parlante al detectar plug. "
             "Se decide por firmware y no por hardware a proposito — permite "
             "politicas como 'auriculares puestos pero quiero oir el parlante "
             "igual', que un corte mecanico prohibe. "
             "PINOUT VERIFICADO contra el datasheet rev 1.06 (pagina 2, tabla "
             "del SJ1-3535NG): 1=sleeve, 2=tip, 3=ring, 4=tip switch, "
             "5=ring switch. OJO: los switches son NC contra SU PROPIA senal "
             "(4 cierra contra 2, 5 cierra contra 3) y se abren al insertar; "
             "NO son contactos libres contra masa. Por eso DET usa el switch "
             "de RING y el canal derecho se toma del pin 3: ver la nota en "
             "el bloque del jack mas abajo.",
        ds="https://www.sameskydevices.com/product/resource/sj1-353xng.pdf",
        # Los NUMEROS de pin son los nombres de pad del footprint oficial de
        # KiCad (S/T/R/TN/RN), no 1..5: el .net cruza simbolo y footprint por
        # ese identificador, asi que tienen que ser iguales de los dos lados.
        pins=[("S", "SLEEVE", -7.62, 5.08, 0),
              ("T", "TIP", -7.62, 2.54, 0),
              ("R", "RING", -7.62, 0.0, 0),
              ("TN", "TIPSW", -7.62, -2.54, 0),
              ("RN", "DET", -7.62, -5.08, 0)],
    ),
    "Conn_01x02": dict(
        ref="J", w=5.08, h=5.08,
        desc="Header JST PH 2.0 de 2 pines para el parlante de 8 ohm. El "
             "parlante se monta al enclosure y no a la PCB: evita acoplar "
             "vibracion al plano y a los pasivos de audio. Recibe la salida "
             "BTL del PAM8302A, asi que NINGUN terminal va a masa.",
        ds="",
        pins=_left_pins(["1", "2"]),
    ),

    # ------------------------------------------------------------- pasivos
    "R": dict(ref="R", w=2.54, h=7.62, desc="Resistencia SMD 0603", ds="",
              pins=[("1", "1", -5.08, 0.0, 0), ("2", "2", 5.08, 0.0, 180)]),
    "C": dict(ref="C", w=2.54, h=7.62, desc="Capacitor ceramico SMD 0603", ds="",
              pins=[("1", "1", -5.08, 0.0, 0), ("2", "2", 5.08, 0.0, 180)]),
    "CP": dict(ref="C", w=2.54, h=7.62,
               desc="Capacitor electrolitico. POLARIZADO: montado al reves "
                    "revienta, por eso tiene simbolo propio y no se mezcla con "
                    "los ceramicos.",
               ds="",
               pins=[("1", "+", -5.08, 0.0, 0), ("2", "-", 5.08, 0.0, 180)]),
    "L": dict(ref="L", w=2.54, h=7.62, desc="Inductor SMD", ds="",
              pins=[("1", "1", -5.08, 0.0, 0), ("2", "2", 5.08, 0.0, 180)]),
    "D": dict(ref="D", w=2.54, h=7.62, desc="Diodo de senal SMD", ds="",
              pins=[("1", "A", -5.08, 0.0, 0), ("2", "K", 5.08, 0.0, 180)]),
}

# Simbolos cuyo pinout NO viene verificado de V1. Su descripcion lo dice, asi
# que aparece en el PDF del esquematico — es el mismo mecanismo que V1 uso con
# el NJM4556AD de V1 antes de confirmarlo contra LCSC. Verificar antes de fabricar.
# Vacio: los dos simbolos que faltaban verificar (JACK_AUDIO y TPS61023)
# ya se confirmaron contra sus datasheets. En los dos casos la
# verificacion encontro errores reales, asi que el mecanismo se gano el
# lugar: no quitar esta tabla, usarla para lo que entre nuevo.
PINOUT_SIN_VERIFICAR = ("H11L1",)

# ---------------------------------------------------------------- footprints
# El tact de V2 es de 6x6 (spec 4.2) pero esa parte todavia no esta importada
# de LCSC (V-4). Se apunta al 4.5x4.5 de V1 —conservado en la libreria
# justamente como fallback— para que el flujo corra end-to-end. Cuando el 6x6
# este importado, cambiar SOLO esta constante: no hay otro lugar que tocar, y
# el test de footprints existentes avisa si el nombre no resuelve.
# CERRADO (V-4): el tact 6x6 comprado trae su "P.C.B. Land Pattern" acotado en
# 6.5 x 4.5, que es EXACTAMENTE el de este footprint oficial de KiCad. El que
# habia antes (SW-TH_4P-L4.5-W4.5, paso 5.50 x 3.00) era el 4.5x4.5 de V1 que
# se dejo de respaldo, y no le habria calzado.
# Cuerpo 6.0 x 6.0, boton D3.4 con 0.25 de travel, patas de 0.7.
# Las variantes _H*mm de KiCad comparten esta misma geometria de pads: el
# largo del vastago se elige con el enclosure, sin tocar la placa.
# Comprado en AliExpress, sin codigo LCSC: lo suelda el usuario.
BTN_FP = "Button_Switch_THT:SW_PUSH_6mm"
# Gatillos L y R: tact ANGULADO, para que el dedo los apriete de costado desde
# el borde y no contra la cara del panel. El footprint viene con KiCad y es el
# de C&K PTS645. Las variantes de largo de actuador (Vx31/39/58/83) comparten
# EXACTAMENTE la misma geometria de pads, asi que el largo se elige al definir
# el enclosure sin tocar la PCB: solo cambia el numero de parte.
# CERRADO (V-4): el tact comprado coincide con este footprint. Su dibujo da
# patas interiores a paso 4.5 (contacto) y exteriores a 7.2+-0.5 (anclaje
# mecanico), contra los 4.50 y 7.01 del PTS645 — dentro de la tolerancia que
# declara el propio dibujo. Los roles tambien coinciden: 2 electricas + 2 de
# anclaje, confirmado sobre la pieza.
# Cuerpo 7.5 x 6.0, alto total 10.7+-0.5, boton D3.40 que sobresale 6.8mm del
# cuerpo, travel 0.25. Comprado en AliExpress, sin codigo LCSC: lo suelda el
# usuario, no JLCPCB (es THT y el CPL excluye THT a proposito).
BTN_RA_FP = "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS"
R_FP = "Resistor_SMD:R_0603_1608Metric"
C_FP = "Capacitor_SMD:C_0603_1608Metric"
# Los rieles de 5V necesitan 0805/25V y no 0603: ver LCSC_PASIVOS.
C0805_FP = "Capacitor_SMD:C_0805_2012Metric"
C1206_FP = "Capacitor_SMD:C_1206_3216Metric"
# El op-amp pasa a SMD para que lo monte JLC. No es solo comodidad de armado:
# libera 95 mm2 del dorso (66% de su area de pads), que es donde la placa esta
# apretada.
# El header del parlante NO se convierte: medido, el JST en SMD ocupa 55 mm2
# contra 6 del THT — nueve veces mas, por las lenguetas de anclaje y los pads
# anchos. Ademas recibe la fuerza de insercion de un conector, donde THT es
# mejor, y soldar dos pines pasantes no es trabajo.
# SOIC-8 de verdad, con el PT2308-S (C115492). El NJM4556A de V1 se descarto
# para SMD: sus dos referencias en LCSC son DMP8 (cuerpo 5.0mm contra 3.9mm),
# asi que habria obligado a dibujar un footprint propio — y en este proyecto un
# footprint propio mal dibujado ya costo una vuelta entera (el jack). El
# PT2308 cuesta lo mismo (~$0.26), tiene mas stock y usa este footprint
# estandar sin tocar nada.
OPAMP_FP = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
# Jack de audio: CUI/Same Sky SJ1-3535NG (V-3 cerrado — se descarto el PJ-320A
# de V1 por no tener datasheet publico). Es HORIZONTAL y de 5 pines, no
# vertical de 4 como asumia el stand-in: el cuerpo sale por el borde de la
# placa, asi que la posicion de J1 la manda el enclosure.
#
# Se usa el footprint OFICIAL de KiCad 9 (el PR upstream que faltaba ya esta
# mergeado), no uno propio. El que se habia dibujado en gamesetup_fp estaba
# MAL: las cotas 1.20/3.60/7.30/9.10/12.80 del "Recommended PCB Layout" son
# VERTICALES —posiciones de cada pad a lo largo del cuerpo— y se leyeron como
# horizontales, con lo que salia un patron ancho y bajo (9.10 x 3.40) en vez
# del real, alto y angosto (2.00 x 11.60). El modelo 3D no calzaba sobre los
# pads y asi se detecto.
# El oficial ademas trae su propio STEP, asi que no hay que mantener el WRL.
#
# OJO: sus pads se llaman por FUNCION, no por numero: S=sleeve T=tip R=ring
# TN=tip switch RN=ring switch. El netlist tiene que usar esos nombres.
JACK_FP = "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal"

# Footprints que estan puestos para que el flujo corra, no porque sean los
# definitivos. La puerta G-0 los reporta y bloquea la generacion de gerbers
# mientras queden: un footprint provisional que llega a fabricacion es una
# placa donde la pieza no entra.
FOOTPRINTS_PROVISIONALES = {}


# Nets fijas del RP2350A (todo lo que no es GPIO). Copiadas de la placa
# minima oficial, con los nombres de esta placa.
_MCU_FIJAS = {
    "IOVDD": "3V3", "DVDD": "1V1", "XIN": "XIN", "XOUT": "XOUT",
    "SWCLK": "SWCLK", "SWDIO": "SWDIO", "RUN": "RUN", "ADC_AVDD": "3V3",
    "VREG_AVDD": "VREG_AVDD", "VREG_PGND": "GND", "VREG_LX": "VREG_LX",
    "VREG_VIN": "3V3", "VREG_FB": "1V1", "USB_DM": "USB_DM_IC",
    "USB_DP": "USB_DP_IC", "USB_OTP_VDD": "3V3", "QSPI_IOVDD": "3V3",
    "QSPI_SD3": "QSPI_SD3", "QSPI_SCLK": "QSPI_SCLK", "QSPI_SD0": "QSPI_SD0",
    "QSPI_SD2": "QSPI_SD2", "QSPI_SD1": "QSPI_SD1", "QSPI_SS": "QSPI_SS",
    "GND": "GND",
}


def _mcu_nets():
    """Nets del RP2350A: GPIO desde pinmap.py (la fuente que check_pinmap
    contrasta contra el firmware) y el resto desde _MCU_FIJAS."""
    nets = {}
    for n, nombre in pinmap.RP2350A_PINS.items():
        if nombre.startswith("GPIO"):
            nets[str(n)] = pinmap.GPIO.get(int(nombre[4:]), NC)
        else:
            nets[str(n)] = _MCU_FIJAS[nombre]
    return nets


# Los 10 tacts verticales (D-pad, X/Y/A/B, Start/Select): (ref, net de
# senal). El orden sigue al enum GcButton del firmware
# (src/input/ControlsTypes.h). El D-pad son cuatro tacts y no un NAV5 de 5
# vias: el NAV5 es un solo actuador y no deja pulsar dos direcciones a la vez,
# que es lo que piden Up+Down+B+A (reset de FX) y Down+Left+X+B (clock lock).
TACTS = [
    ("SW1", "DPAD_UP"), ("SW2", "DPAD_DOWN"),
    ("SW3", "DPAD_LEFT"), ("SW4", "DPAD_RIGHT"),
    ("SW5", "BTN_X"), ("SW6", "BTN_Y"),
    ("SW7", "BTN_A"), ("SW8", "BTN_B"),
    ("SW11", "BTN_START"), ("SW12", "BTN_SELECT"),
]

INSTANCES = [
    # ---------------------------------------------------------------- MCU
    ("RP2350A", "U1", "RP2350A", 60.0, 60.0, _mcu_nets(),
     {"LCSC": "C42411118", "FP": "rp_minimal:rpi_rp2350a_vias"}),

    # ------------------------------------------------------------ display
    # Panel desnudo por FPC. CS a masa: siempre seleccionado, igual que hacia
    # el modulo de 7 pines, asi que SPI0 sigue sin poder compartirse. RD y el
    # bus paralelo DB0-7 a masa (4-SPI, IM=1). TE a GP26, que quedo libre.
    ("LCD_FPC24", "J4", "LCD_FPC", 200.0, 40.0, {
        "1": "BL_A", "2": "BL_K", "3": "GND", "4": "3V3", "5": "3V3",
        "6": "3V3", "7": "LCD_RES", "8": "GND", "9": "LCD_SCK",
        "10": "LCD_DC", "11": "GND", "12": "LCD_MOSI",
        "13": "GND", "14": "GND", "15": "GND", "16": "GND",
        "17": "GND", "18": "GND", "19": "GND", "20": "GND",
        "21": "LCD_TE", "22": NC, "23": "GND", "24": "GND",
        "25": "GND", "26": "GND"},
     {"LCSC": "C2856831",
      "FP": "gamesetup_lcsc:FPC-SMD_24P-P0.50_FPC-05FB-24PH20"}),
    # El panel en si: pieza mecanica, sin pines. MANUAL = DNP para JLCPCB
    # (la pega el usuario), pero queda en el BOM para comprarla.
    ("LCD_PANEL", "LCD1", "DM-TFT13-377-24P", 200.0, 80.0, {},
     {"FP": "gamesetup_fp:LCD_LH133T_24P", "MANUAL": True}),
    # Backlight: 2 LED blancos en paralelo, 3.0V / 40mA segun el datasheet.
    # Desde VSYS (3.4-4.2V con LiPo) y no desde 3V3 (0.3V de margen sobre la
    # Vf: la corriente quedaria a merced de la dispersion del LED) ni desde
    # el riel de 5V (es el riel del op-amp y el PWM le meteria ruido).
    # R21 fija el brillo maximo: a 3.9V nominal, (3.9-3.0)/24 = 37mA.
    # ponytail: R21 es la perilla de calibracion; con la LiPo llena da ~50mA
    # y vacia ~17mA. Si molesta, driver de corriente constante en V2.
    ("R", "R21", "24R", 190.0, 20.0,
     {"1": "VSYS", "2": "BL_A"}, {"FP": C0805_FP}),
    ("Q_NMOS", "Q1", "2N7002", 190.0, 40.0,
     {"1": "LCD_BLK", "2": "GND", "3": "BL_K"},
     {"LCSC": "C8545", "FP": "Package_TO_SOT_SMD:SOT-23"}),
    # Pulldown de puerta: con el GPIO sin configurar (reset, bootsel) el
    # backlight queda apagado en vez de flotar.
    ("R", "R22", "100k", 180.0, 40.0,
     {"1": "LCD_BLK", "2": "GND"}, {"FP": R_FP}),
    # Desacoplo del panel, al lado del conector.
    ("C", "C30", "1uF", 210.0, 20.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("C", "C31", "100nF", 218.0, 20.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
]

# ------------------------------------------------------------------- tacts
INSTANCES += [
    # {1,2} y no el {1,4} de V1: el footprint oficial de KiCad numera sus
    # cuatro pads como 1,1,2,2 (un numero por par interno), asi que cablear 1
    # y 2 YA cruza el contacto — el diagonal queda garantizado por el
    # footprint, sin depender de elegir bien los numeros.
    ("SW_Push", ref, sig, 240.0, 20.0 + 12.0 * i,
     {"1": sig, "2": "GND"},
     {"FP": BTN_FP})
    for i, (ref, sig) in enumerate(TACTS)
]

# ------------------------------------------------- gatillos L y R (angulados)
# Solo dos pines: pin 1 a la senal, pin 2 a GND. El cableado diagonal del tact
# vertical no aplica — aca no hay dos pares internos que cruzar.
INSTANCES += [
    ("SW_Push_RA", "SW9", "BTN_L", 240.0, 160.0,
     {"1": "BTN_L", "2": "GND"}, {"FP": BTN_RA_FP}),
    ("SW_Push_RA", "SW10", "BTN_R", 240.0, 172.0,
     {"1": "BTN_R", "2": "GND"}, {"FP": BTN_RA_FP}),
]

# --------------------------------------------------- alimentacion y EXP
INSTANCES += [
    # PWR_EN tiene pull-up de 100k a VSYS (R33) hacia el EN del TPS63001:
    # cerrarlo contra GND apaga el riel de 3V3. Es el mismo esquema que tenia
    # el pin 3V3_EN del modulo, ahora en la placa.
    ("SK12D07", "SW15", "PWR", 20.0, 160.0,
     {"1": "GND", "2": "PWR_EN", "3": NC, "4": "GND", "5": "GND"},
     {"LCSC": "C431547", "FP": "gamesetup_lcsc:SW-TH_SK12D07VG3"}),
]

# =================================================================== AUDIO
#
#   VSYS -[L2]- VSYS_F -[L1]- TPS61023 -> 5V   (riel analogico FIJO)
#                                          |
#   PCM5102A -[470R+2n2]-> PT2308 -[470uF]-> JACK 3.5mm
#    (I2S/PIO)              (5V, Vgnd=2.5V)  |
#                                            +-[10k]-+-[1uF]-> PAM8302A -> J5
#                                (canal R) --[10k]---+   (VSYS directo)
#
# Toda la cadena, salvo el boost, se copia de V1, que llego a una placa
# ruteada con DRC limpio. Las notas de por que cada componente esta donde
# esta tambien vienen de ahi: son caras de re-derivar.

CP_FP = "Capacitor_SMD:CP_Elec_6.3x5.4"
L_FP = "Inductor_SMD:L_1210_3225Metric"
D_FP = "Diode_SMD:D_SOD-123"

INSTANCES += [
    # ------------------------------------------------------------ boost 5V
    # El riel analogico es FIJO y no sigue a la bateria: colgado de VSYS, la
    # excursion de salida caeria de ~1.4 Vrms con LiPo llena a ~1.0 Vrms con
    # bateria baja, y el nivel cambiaria a lo largo de una sesion.
    # EN atado a VIN: el audio no depende de que el firmware arranque.
    # SOT-563, NO SOT-23-6: el sufijo DRL de TI es SOT-5X3. La diferencia es
    # brutal —2.10x1.35mm a paso 0.50 contra 3.60x2.50 a paso 0.95— asi que
    # con el footprint equivocado el chip no entra ni cerca.
    # Pinout de TI: 1=FB 2=EN 3=VIN 4=GND 5=SW 6=VOUT.
    # EN atado a VIN: el audio no depende de que el firmware arranque.
    ("TPS61023", "U2", "TPS61023DRLR", 40.0, 220.0, {
        "1": "BOOST_FB", "2": "VSYS_F", "3": "VSYS_F",
        "4": "GND", "5": "BOOST_SW", "6": "5V"},
     {"LCSC": "C919459", "FP": "Package_TO_SOT_SMD:SOT-563"}),
    # Filtro LC de entrada (spec 5.2.1): que la conmutacion no vuelva por VSYS
    # hasta el regulador del modulo.
    ("L", "L2", "2.2uH", 25.0, 210.0,
     {"1": "VSYS", "2": "VSYS_F"}, {"LCSC": "C3002559", "FP": L_FP}),
    ("C", "C4", "10uF", 32.0, 215.0, {"1": "VSYS_F", "2": "GND"}, {"FP": C_FP}),
    ("L", "L1", "2.2uH", 50.0, 210.0,
     {"1": "VSYS_F", "2": "BOOST_SW"}, {"LCSC": "C3002559", "FP": L_FP}),
    # Divisor de realimentacion: Vout = VREF * (1 + R4/R5) con VREF=0.595V.
    # 200k/27k -> 5.0024V (+0.05%). Los valores salen de params.py, que es
    # donde esta el calculo y la referencia al datasheet.
    ("R", "R4", "%gk" % params.v("BOOST_RFB_TOP"), 58.0, 225.0,
     {"1": "5V", "2": "BOOST_FB"}, {"FP": R_FP}),
    ("R", "R5", "%gk" % params.v("BOOST_RFB_BOT"), 58.0, 235.0,
     {"1": "BOOST_FB", "2": "GND"}, {"FP": R_FP}),
    ("C", "C5", "22uF", 66.0, 215.0, {"1": "5V", "2": "GND"},
     {"FP": C0805_FP}),
    # Bulk local del riel de 5V, fisicamente junto a los pines del op-amp.
    ("C", "C6", "22uF", 74.0, 215.0, {"1": "5V", "2": "GND"},
     {"FP": C0805_FP}),
    ("C", "C7", "100nF", 82.0, 215.0, {"1": "5V", "2": "GND"}, {"FP": C_FP}),

    # ----------------------------------------------------------------- DAC
    # Pinout verificado en V1 contra el simbolo oficial de KiCad y TI
    # SLAS859C. SCK (pin 12) a GND activa el PLL interno desde BCK.
    ("PCM5102A", "U5", "PCM5102APWR", 140.0, 220.0, {
        "1": "3V3", "2": "CAPP", "3": "GND", "4": "CAPM", "5": "VNEG",
        "6": "DACOUT_L", "7": "DACOUT_R", "8": "3V3", "9": "GND",
        "10": "GND", "11": "GND", "12": "GND",
        "13": "I2S_BCK", "14": "I2S_DIN", "15": "I2S_LRCK",
        "16": "GND", "17": "DAC_XSMT", "18": "LDOO", "19": "GND", "20": "3V3"},
     {"LCSC": "C107671",
      "FP": "gamesetup_lcsc:TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL"}),
    # Charge pump: es lo que centra la salida en masa (DirectPath).
    ("C", "C8", "2.2uF", 128.0, 205.0, {"1": "CAPP", "2": "CAPM"},
     {"FP": C_FP}),
    ("C", "C9", "2.2uF", 136.0, 205.0, {"1": "VNEG", "2": "GND"},
     {"FP": C_FP}),
    ("C", "C10", "100nF", 144.0, 205.0, {"1": "LDOO", "2": "GND"}, {"FP": C_FP}),
    # Un 100n + un 10uF por riel (AVDD / CPVDD / DVDD), segun SLAS859C.
    ("C", "C11", "100nF", 152.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("C", "C12", "10uF", 160.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("C", "C13", "100nF", 168.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("C", "C14", "10uF", 176.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("C", "C15", "100nF", 184.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("C", "C16", "10uF", 192.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    # XSMT con pulldown: el DAC arranca MUTEADO y el firmware lo libera. El
    # modulo GY-PCM5102 lo traia a 3V3 de fabrica; chip-down hay que ponerlo,
    # si no hay un golpe audible en el arranque.
    ("R", "R6", "100k", 120.0, 205.0, {"1": "DAC_XSMT", "2": "GND"}, {"FP": R_FP}),
    # Filtro de salida del DAC (SLAS859C): 470R + 2n2 por canal.
    ("R", "R7", "470R", 120.0, 240.0,
     {"1": "DACOUT_L", "2": "AOUT_L"}, {"FP": R_FP}),
    ("C", "C17", "2.2nF", 128.0, 245.0, {"1": "AOUT_L", "2": "GND"}, {"FP": C_FP}),
    ("R", "R8", "470R", 136.0, 240.0,
     {"1": "DACOUT_R", "2": "AOUT_R"}, {"FP": R_FP}),
    ("C", "C18", "2.2nF", 144.0, 245.0, {"1": "AOUT_R", "2": "GND"}, {"FP": C_FP}),

    # -------------------------------------------------------------- op-amp
    ("PT2308", "U3", "PT2308-S", 240.0, 220.0, {
        "1": "AUDIO_L", "2": "OPL_N", "3": "VREF25", "4": "GND",
        "5": "VREF25", "6": "OPR_N", "7": "AUDIO_R", "8": "5V"},
     {"LCSC": "C115492", "FP": OPAMP_FP}),
    # Masa virtual a 2.5V: es lo que permite alimentacion simple de 5V.
    ("R", "R9", "10k", 224.0, 205.0, {"1": "5V", "2": "VREF25"}, {"FP": R_FP}),
    ("R", "R10", "10k", 232.0, 205.0, {"1": "VREF25", "2": "GND"}, {"FP": R_FP}),
    ("C", "C19", "100uF", 240.0, 205.0, {"1": "VREF25", "2": "GND"},
     {"FP": C1206_FP}),
    ("C", "C20", "100nF", 248.0, 205.0, {"1": "VREF25", "2": "GND"}, {"FP": C_FP}),
    # Buffer INVERSOR de ganancia 0.5 (Rf/Rin = 10k/20k), uno por canal.
    # Por que atenua: el PCM5102A entrega +-2.8V centrados en MASA (2.0 Vrms)
    # y el op-amp corre con 5V simples y masa virtual a 2.5V — +-2.8V no
    # entran. Con 0.5 quedan +-1.4V, comodos.
    # Por que el acoplo: la salida del DAC reposa en masa y la del op-amp en
    # VREF25. Sin capacitor circularia continua por Rf y la salida se iria a
    # 3.75V, comiendose el headroom.
    ("C", "C21", "1uF", 216.0, 235.0, {"1": "AOUT_L", "2": "INL"}, {"FP": C_FP}),
    ("R", "R11", "20k", 224.0, 235.0, {"1": "INL", "2": "OPL_N"}, {"FP": R_FP}),
    ("R", "R12", "10k", 232.0, 232.0, {"1": "OPL_N", "2": "AUDIO_L"}, {"FP": R_FP}),
    ("C", "C22", "1uF", 216.0, 245.0, {"1": "AOUT_R", "2": "INR"}, {"FP": C_FP}),
    ("R", "R13", "20k", 224.0, 245.0, {"1": "INR", "2": "OPR_N"}, {"FP": R_FP}),
    ("R", "R14", "10k", 232.0, 248.0, {"1": "OPR_N", "2": "AUDIO_R"}, {"FP": R_FP}),
    # Bloqueo de DC hacia el jack: la salida del op-amp reposa en VREF25.
    #
    # Los UNICOS electroliticos que quedan en la placa, y no por descuido: a
    # 32 ohm de auricular, 470uF dan el corte en 10.6Hz. No hay ceramico
    # practico de ese valor, y bajar a 220uF subiria el corte a 22Hz, o sea
    # comerse los graves.
    #
    # MANUAL: los suelda el usuario, no JLCPCB. Los 470uF SMD que ofrece su
    # biblioteca son "New Arrivals" sin stock real (el emparejador devolvia
    # "10 shortfall"), y atar la placa a esa disponibilidad no tiene sentido
    # cuando ya hay doce piezas en la lista de soldadura manual. Ademas deja
    # elegir el capacitor libremente, que en un acoplo de audio importa.
    # gen_pcb.py los marca DNP para que salgan del CPL.
    ("CP", "C23", "470uF", 256.0, 235.0,
     {"1": "AUDIO_L", "2": "JACK_L"}, {"FP": CP_FP, "MANUAL": True}),
    ("CP", "C24", "470uF", 256.0, 245.0,
     {"1": "AUDIO_R", "2": "JACK_R"}, {"FP": CP_FP, "MANUAL": True}),

    # ---------------------------------------------------------------- jack
    # SJ1-3535NG. El mapeo sale de la tabla del datasheet (rev 1.06 p.2):
    #   1=sleeve  2=tip  3=ring  4=tip switch  5=ring switch
    # El izquierdo va al TIP (pin 2) y el derecho al RING (pin 3), que es el
    # estandar TRS; sleeve (pin 1) es la masa del auricular.
    #
    # DETECCION — por que cuelga del switch de RING y no del de TIP:
    # los switches de esta familia NO son contactos libres. El pin 4 cierra
    # contra el pin 2 (tip) y el 5 contra el 3 (ring), y ambos se ABREN al
    # insertar el plug. NO hay ningun contacto que cierre contra masa, asi
    # que el sensado tiene que convivir con el audio si o si.
    #
    # El divisor se cierra por R20, el bleeder del canal derecho. Sin R20 el
    # nodo JACK_R queda aislado por C24 — que bloquea continua — y no se forma
    # ningun divisor: DET se queda en 3V3 con y sin plug y la deteccion NO
    # FUNCIONA NUNCA. Esa era la falla de la version anterior de este bloque.
    #
    #   sin plug: RN cierra contra R
    #             3V3 -[R15]- DET -[R18]- JACK_R -[R20]- GND
    #             DET = 3V3 * (4k7+4k7)/(47k+4k7+4k7) = 0.55V   -> BAJO
    #   con plug: RN abre, DET = 3V3 por R15                    -> ALTO
    #
    # Los tres valores estan atados entre si: para que DET caiga bajo el
    # umbral (0.3*3V3 = 0.99V) hace falta R18+R20 << R15. Por eso R18 es
    # 4k7 y no 100k; con 100k el divisor no baja de 3.1V. Peor caso con
    # resistencias al 5%: 0.60V, todavia con margen.
    ("JACK_AUDIO", "J1", "PHONES", 280.0, 240.0, {
        "S": "GND", "T": "JACK_L", "R": "JACK_R", "TN": NC, "RN": "JACK_DETSW"},
     {"FP": JACK_FP}),
    # Pull-up externo: antes de que el firmware configure el pin, el interno
    # no esta activo y DET quedaria flotante.
    ("R", "R15", "47k", 288.0, 225.0,
     {"1": "3V3", "2": "JACK_DET"}, {"FP": R_FP}),
    # Serie entre el contacto y el GPIO. Con el plug afuera el switch esta
    # cerrado y JACK_R sigue llevando audio, que excursiona por debajo de
    # masa; R18 limita esa corriente hacia el pin.
    ("R", "R18", "4.7k", 288.0, 235.0,
     {"1": "JACK_DET", "2": "JACK_DETSW"}, {"FP": R_FP}),
    # Filtro del nodo de deteccion. Sin el, el audio llega al GPIO atenuado
    # apenas por R15/R18 y el pin leeria ALTO en cada pico de senal: el jack
    # parpadeando. Con 10uF la ondulacion en el peor caso (20Hz, pico de
    # 1.5V en JACK_R) queda en +-0.21V sobre los 0.55V de reposo.
    # El precio es latencia: ~480ms para reconocer que se enchufo, ~130ms
    # para reconocer que se desenchufo.
    ("C", "C29", "10uF", 296.0, 225.0,
     {"1": "JACK_DET", "2": "GND"}, {"FP": C_FP}),
    # Bleeders de los capacitores de acoplo. Hacen dos cosas:
    #  1) le dan a JACK_L/JACK_R la referencia de continua que no tenian.
    #     C23 y C24 son ELECTROLITICOS POLARIZADOS de 470uF y su terminal
    #     negativo quedaba flotando cuando no habia auriculares puestos.
    #  2) R20 cierra el divisor de deteccion (ver arriba).
    # Tambien matan el "pop" al conectar, porque el capacitor ya esta
    # descargado del lado del jack. 4k7 contra los 32R del auricular es una
    # carga del 0.7%, despreciable.
    ("R", "R19", "4.7k", 264.0, 230.0,
     {"1": "JACK_L", "2": "GND"}, {"FP": R_FP}),
    ("R", "R20", "4.7k", 264.0, 250.0,
     {"1": "JACK_R", "2": "GND"}, {"FP": R_FP}),

    # ------------------------------------------------------ parlante class-D
    # Suma mono tomada ANTES del bloqueo de DC: de AUDIO_*, no de JACK_*. Si
    # se tomara despues, el parlante se quedaria sin senal cuando no hay
    # auriculares enchufados.
    ("R", "R16", "10k", 264.0, 260.0,
     {"1": "AUDIO_L", "2": "SPK_SUM"}, {"FP": R_FP}),
    ("R", "R17", "10k", 272.0, 260.0,
     {"1": "AUDIO_R", "2": "SPK_SUM"}, {"FP": R_FP}),
    # Acoplo de entrada al class-D: SPK_SUM reposa en VREF25 (2.5V) y el
    # PAM8302A polariza sus entradas respecto de SU alimentacion (VSYS). Sin
    # acoplo los dos puntos de reposo pelean.
    ("C", "C25", "1uF", 280.0, 260.0,
     {"1": "SPK_SUM", "2": "SPK_INP"}, {"FP": C_FP}),
    ("C", "C26", "1uF", 288.0, 260.0,
     {"1": "SPK_INN", "2": "GND"}, {"FP": C_FP}),
    ("PAM8302A", "U4", "PAM8302A", 300.0, 265.0, {
        "1": "SPK_SHDN", "2": NC, "3": "SPK_INP", "4": "SPK_INN",
        "5": "SPK_P", "6": "VSYS", "7": "GND", "8": "SPK_N"},
     {"LCSC": "C113367",
      "FP": "gamesetup_lcsc:MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL"}),
    ("C", "C27", "100nF", 312.0, 255.0, {"1": "VSYS", "2": "GND"}, {"FP": C_FP}),
    ("C", "C28", "22uF", 320.0, 255.0, {"1": "VSYS", "2": "GND"},
     {"FP": C0805_FP}),
    # Salida BTL: ningun terminal va a masa.
    ("Conn_01x02", "J5", "SPEAKER 8R", 330.0, 265.0,
     {"1": "SPK_P", "2": "SPK_N"},
     {"FP": "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"}),
]

# ==================================================================== MIDI
#
#   MIDI OUT (J7, TRS tipo A): Tip = DIN 5, Ring = DIN 4, Sleeve = DIN 2.
#       3V3 -[33R R40]- Ring        MIDI_TX -> U9 (74LVC1G17) -[10R R41]- Tip
#   Norma MIDI 1.0 electrica, variante 3.3V (CA-033). U9 pone los 5mA del
#   lazo; el GPIO solo ve la entrada CMOS del buffer.
#
#   MIDI IN (J6): el emisor pone corriente por DIN 4 (= Ring en tipo A) y la
#   recibe por DIN 5 (= Tip). Ring -[220R R42]- anodo del LED de U10 (H11L1);
#   Tip - catodo. D3 antiparalelo al LED, para un cable al reves. La salida Schmitt de U10 es colector abierto:
#   R43 4k7 a 3V3 -> MIDI_RX. La MALLA de J6 queda al aire: el receptor no
#   aterriza el blindaje (lazo de masa con el emisor).
INSTANCES += [
    ("JACK_AUDIO", "J7", "MIDI OUT", 280.0, 300.0, {
        "S": "GND", "T": "MIDI_OUT_T", "R": "MIDI_OUT_R", "TN": NC, "RN": NC},
     {"FP": JACK_FP}),
    ("R", "R40", "33R", 288.0, 290.0,
     {"1": "3V3", "2": "MIDI_OUT_R"}, {"FP": R_FP}),
    ("R", "R41", "10R", 288.0, 300.0,
     {"1": "MIDI_TX_BUF", "2": "MIDI_OUT_T"}, {"FP": R_FP}),
    ("LVC1G17", "U9", "74LVC1G17", 300.0, 300.0,
     {"1": NC, "2": "MIDI_TX", "3": "GND", "4": "MIDI_TX_BUF", "5": "3V3"},
     {"FP": "Package_TO_SOT_SMD:SOT-353_SC-70-5"}),
    ("JACK_AUDIO", "J6", "MIDI IN", 280.0, 330.0, {
        "S": NC, "T": "MIDI_IN_K", "R": "MIDI_IN_R", "TN": NC, "RN": NC},
     {"FP": JACK_FP}),
    ("R", "R42", "220R", 288.0, 325.0,
     {"1": "MIDI_IN_R", "2": "MIDI_IN_A"}, {"FP": R_FP}),
    ("D_1N4148", "D3", "1N4148W", 288.0, 335.0,
     {"1": "MIDI_IN_A", "2": "MIDI_IN_K"}, {"FP": D_FP}),
    ("H11L1", "U10", "H11L1M", 300.0, 330.0,
     {"1": "MIDI_IN_A", "2": "MIDI_IN_K", "3": NC, "4": "MIDI_RX",
      "5": "GND", "6": "3V3"},
     {"FP": "Package_DIP:SMDIP-6_W7.62mm"}),
    ("R", "R43", "4.7k", 312.0, 325.0,
     {"1": "3V3", "2": "MIDI_RX"}, {"FP": R_FP}),
    ("C", "C56", "100nF", 312.0, 335.0,
     {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
]

# =========================================================== NUCLEO RP2350A
# Copiado de la placa minima oficial de Raspberry Pi (RPI-RP2350A-MINIMAL_R4,
# MIT): mismas piezas, mismos valores, mismas huellas (lib/rp_minimal.pretty,
# importadas por import_rp_minimal.py) y la MISMA geometria, que rp_core.py
# lleva al dorso de esta placa. Ver la spec 2026-10-14-...-chipdown-design.md.
#
# ref de la placa oficial -> ref en esta placa. rp_core.py usa esta tabla
# para saber que huella va donde; no hay una segunda copia.
CORE_REF_MAP = {
    "U1": "U1", "L1": "L3", "C6": "C32", "C7": "C33", "C9": "C34", "R3": "R23",
    "C8": "C35", "C10": "C36", "C11": "C37",
    "C12": "C38", "C13": "C39", "C14": "C40", "C15": "C41", "C16": "C42",
    "C17": "C43", "C18": "C44",
    "X1": "Y1", "C3": "C45", "C4": "C46", "R2": "R24",
    "R7": "R25", "R8": "R26",
    "U3": "U6", "C2": "C47", "R6": "R27", "R10": "R28",
}
# net de la placa oficial -> net de esta placa (para el cobre copiado).
CORE_NET_MAP = {
    "+3V3": "3V3", "+1V1": "1V1", "GND": "GND", "/VREG_LX": "VREG_LX",
    "/VREG_AVDD": "VREG_AVDD", "/XIN": "XIN", "/XOUT": "XOUT",
    "Net-(C4-Pad1)": "XOUT_R", "/QSPI_SD0": "QSPI_SD0",
    "/QSPI_SD1": "QSPI_SD1", "/QSPI_SD2": "QSPI_SD2", "/QSPI_SD3": "QSPI_SD3",
    "/QSPI_SCLK": "QSPI_SCLK", "/QSPI_SS": "QSPI_SS", "/FLASH_SS": "FLASH_SS",
    "Net-(U1-USB_DP)": "USB_DP_IC", "Net-(U1-USB_DM)": "USB_DM_IC",
}

RPF = "rp_minimal:"
C0402 = RPF + "generic_capc1005x50"
C0402W = RPF + "generic_capc1005x50_wide"
R0402 = RPF + "generic_resc1005x35"


def _c(ref, val, net, fp=C0402, lcsc="C1525"):
    return ("C", ref, val, 0.0, 0.0, {"1": net, "2": "GND"},
            {"FP": fp, "LCSC": lcsc})


INSTANCES += [
    # Regulador interno de 1V1 (guia, seccion 2.1). L3 es el Abracon con
    # punto de polaridad: la orientacion importa y la fija la copia.
    ("L", "L3", "3.3uH", 0.0, 0.0, {"1": "1V1", "2": "VREG_LX"},
     {"FP": RPF + "abracon_aota-b201610s3r3-101-t", "LCSC": "C42411119"}),
    _c("C32", "4.7uF", "3V3", C0402W, "C23733"),     # VREG_VIN
    _c("C33", "4.7uF", "1V1", C0402W, "C23733"),     # salida del regulador
    _c("C34", "4.7uF", "VREG_AVDD", C0402, "C23733"),
    ("R", "R23", "33R", 0.0, 0.0, {"1": "3V3", "2": "VREG_AVDD"},
     {"FP": R0402, "LCSC": "C25105"}),
    _c("C35", "100nF", "1V1"), _c("C36", "100nF", "1V1"),
    _c("C37", "100nF", "1V1"),
    _c("C38", "100nF", "3V3"), _c("C39", "100nF", "3V3"),
    _c("C40", "100nF", "3V3"), _c("C41", "100nF", "3V3"),
    _c("C42", "100nF", "3V3"), _c("C43", "100nF", "3V3"),
    _c("C44", "100nF", "3V3"),
    # Cristal (guia, seccion 4): ABM8-272-T3, 15pF y 1k en serie en XOUT.
    ("XTAL4", "Y1", "12MHz", 0.0, 0.0,
     {"1": "XIN", "2": "GND", "3": "XOUT_R", "4": "GND"},
     {"FP": RPF + "generic_xtalcc320x250x80-4", "LCSC": "C20625731"}),
    _c("C45", "15pF", "XIN", C0402, "C1548"),
    _c("C46", "15pF", "XOUT_R", C0402, "C1548"),
    ("R", "R24", "1k", 0.0, 0.0, {"1": "XOUT", "2": "XOUT_R"},
     {"FP": R0402, "LCSC": "C11702"}),
    # USB: 27R en serie cerca del chip (guia, seccion 5.1).
    ("R", "R25", "27R", 0.0, 0.0, {"1": "USB_DP", "2": "USB_DP_IC"},
     {"FP": R0402, "LCSC": "C25100"}),
    ("R", "R26", "27R", 0.0, 0.0, {"1": "USB_DM", "2": "USB_DM_IC"},
     {"FP": R0402, "LCSC": "C25100"}),
    # Flash (guia, seccion 3). R28 es el 0R de la placa oficial entre QSPI_SS
    # y el CS de la flash: se conserva para que el cobre copiado cierre igual.
    ("W25Q128", "U6", "W25Q128JVSIQ", 0.0, 0.0, {
        "1": "FLASH_SS", "2": "QSPI_SD1", "3": "QSPI_SD2", "4": "GND",
        "5": "QSPI_SD0", "6": "QSPI_SCLK", "7": "QSPI_SD3", "8": "3V3"},
     {"FP": RPF + "generic_soic127p790x195-8", "LCSC": "C97521"}),
    _c("C47", "100nF", "3V3"),
    ("R", "R27", "1k", 0.0, 0.0, {"1": "QSPI_SS", "2": "USB_BOOT"},
     {"FP": R0402, "LCSC": "C11702"}),
    ("R", "R28", "0R", 0.0, 0.0, {"1": "QSPI_SS", "2": "FLASH_SS"},
     {"FP": R0402, "LCSC": "C17168"}),
    # BOOTSEL (a QSPI_SS por R27) y RUN, como la placa minima (seccion 5.4).
    # RUN va directo a masa: tiene pull-up interno, igual que en la Pico 2.
    ("SW_SMD", "SW13", "BOOTSEL", 0.0, 0.0, {"1": "USB_BOOT", "2": "GND"},
     {"FP": "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "LCSC": "C318884"}),
    ("SW_SMD", "SW14", "RUN", 0.0, 0.0, {"1": "RUN", "2": "GND"},
     {"FP": "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "LCSC": "C318884"}),
    # SWD: tres pads para la sonda de depuracion (guia, seccion 5.3).
    ("TestPoint", "TP1", "SWCLK", 0.0, 0.0, {"1": "SWCLK"},
     {"FP": "TestPoint:TestPoint_Pad_D1.0mm"}),
    ("TestPoint", "TP2", "SWDIO", 0.0, 0.0, {"1": "SWDIO"},
     {"FP": "TestPoint:TestPoint_Pad_D1.0mm"}),
    ("TestPoint", "TP3", "GND", 0.0, 0.0, {"1": "GND"},
     {"FP": "TestPoint:TestPoint_Pad_D1.0mm"}),
]

# ===================================================== USB, CARGA Y 3V3
#
#   USB-C VBUS -+-[D1]-+-> VSYS -> TPS63001 -> 3V3
#               |      |
#               +-> ETA6096 -> VBAT -[D2]-+       (y VSYS alimenta class-D,
#                                 |                boost de 5V y backlight)
#                                J3 (LiPo)
#
# Es el arbol de alimentacion del modulo RP2350-Plus (esquema de Waveshare)
# con un cambio: TPS63001 en lugar del MP28164 (ver la spec).
INSTANCES += [
    ("USB_C16", "J2", "USB-C", 0.0, 0.0, {
        "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
        "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
        "A5": "USB_CC1", "B5": "USB_CC2",
        "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DM", "B7": "USB_DM",
        "A8": NC, "B8": NC},
     {"FP": "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A",
      "LCSC": "C2894897"}),
    # 5.1k en CC1/CC2: el host ve un dispositivo y entrega 5V.
    ("R", "R29", "5.1k", 0.0, 0.0, {"1": "USB_CC1", "2": "GND"}, {"FP": R_FP}),
    ("R", "R30", "5.1k", 0.0, 0.0, {"1": "USB_CC2", "2": "GND"}, {"FP": R_FP}),
    # OR de alimentacion: VSYS es la mayor entre VBUS y VBAT, menos un diodo.
    ("D_Schottky", "D1", "MBR230LSFT1G", 0.0, 0.0, {"1": "VSYS", "2": "VBUS"},
     {"FP": "Diode_SMD:D_SOD-123F", "LCSC": "C126673"}),
    ("D_Schottky", "D2", "MBR230LSFT1G", 0.0, 0.0, {"1": "VSYS", "2": "VBAT"},
     {"FP": "Diode_SMD:D_SOD-123F", "LCSC": "C126673"}),
    # Cargador. ISET 150k = 1.2A segun el datasheet (el modulo usa 160k ~1A,
    # punto que no esta en el datasheet). 0.6C para la LiPo de 2000mAh.
    ("ETA6096", "U8", "ETA6096D3K", 0.0, 0.0, {
        "1": "VBUS", "2": "CHG_PMID", "3": "GND", "4": NC, "5": "CHG_SW",
        "6": "VBAT", "7": "GND", "8": "CHG_ISET", "9": NC, "10": "GND",
        "11": "GND"},
     {"FP": "gamesetup_lcsc:DFN-10_L3.0-W3.0-P0.50-BL-EP2.4-1",
      "LCSC": "C7465538"}),
    ("C", "C48", "1uF", 0.0, 0.0, {"1": "VBUS", "2": "GND"}, {"FP": C_FP}),
    ("C", "C49", "22uF", 0.0, 0.0, {"1": "CHG_PMID", "2": "GND"},
     {"FP": C0805_FP}),
    ("L", "L4", "2.2uH", 0.0, 0.0, {"1": "CHG_SW", "2": "VBAT"},
     {"LCSC": "C3002559", "FP": L_FP}),
    ("C", "C50", "10uF", 0.0, 0.0, {"1": "VBAT", "2": "GND"}, {"FP": C_FP}),
    ("R", "R31", "150k", 0.0, 0.0, {"1": "CHG_ISET", "2": "GND"},
     {"FP": R_FP}),
    ("Conn_Bat", "J3", "LiPo", 0.0, 0.0, {"1": "VBAT", "2": "GND", "MP": "GND"},
     {"FP": "Connector_Molex:Molex_PicoBlade_53398-0271_1x02-1MP_P1.25mm_Vertical"}),
    # 3V3: TPS63001, circuito de aplicacion de SLVS520C (2.2uH, 10uF de
    # entrada, 2x10uF de salida, VINA filtrado con 100R + 100nF).
    ("TPS63001", "U7", "TPS63001DRCR", 0.0, 0.0, {
        "1": "3V3", "2": "BB_L2", "3": "GND", "4": "BB_L1", "5": "VSYS",
        "6": "PWR_EN", "7": "BB_PS", "8": "BB_VINA", "9": "GND", "10": "3V3",
        "11": "GND"},
     {"FP": "Package_SON:Texas_DRC0010J_ThermalVias", "LCSC": "C28060"}),
    ("L", "L5", "2.2uH", 0.0, 0.0, {"1": "BB_L1", "2": "BB_L2"},
     {"LCSC": "C3002559", "FP": L_FP}),
    ("C", "C51", "10uF", 0.0, 0.0, {"1": "VSYS", "2": "GND"}, {"FP": C_FP}),
    ("C", "C52", "10uF", 0.0, 0.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("C", "C53", "10uF", 0.0, 0.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("R", "R32", "100R", 0.0, 0.0, {"1": "VSYS", "2": "BB_VINA"},
     {"FP": R_FP}),
    ("C", "C54", "100nF", 0.0, 0.0, {"1": "BB_VINA", "2": "GND"},
     {"FP": C_FP}),
    ("R", "R33", "100k", 0.0, 0.0, {"1": "VSYS", "2": "PWR_EN"},
     {"FP": R_FP}),
    # PS/SYNC con pulldown: arranca en power-save; el firmware lo sube por
    # GP23 si quiere PWM fijo (menos ondulacion en el audio).
    ("R", "R34", "10k", 0.0, 0.0, {"1": "BB_PS", "2": "GND"}, {"FP": R_FP}),
    # Sensado: VBUS (100k/200k -> 3.33V con 5V) y VSYS/3 en el ADC3.
    ("R", "R35", "100k", 0.0, 0.0, {"1": "VBUS", "2": "VBUS_SENSE"},
     {"FP": R_FP}),
    ("R", "R36", "200k", 0.0, 0.0, {"1": "VBUS_SENSE", "2": "GND"},
     {"FP": R_FP}),
    ("R", "R37", "200k", 0.0, 0.0, {"1": "VSYS", "2": "VSYS_ADC"},
     {"FP": R_FP}),
    ("R", "R38", "100k", 0.0, 0.0, {"1": "VSYS_ADC", "2": "GND"},
     {"FP": R_FP}),
    ("C", "C55", "100nF", 0.0, 0.0, {"1": "VSYS_ADC", "2": "GND"},
     {"FP": C_FP}),
]

# ---------------------------------------------------------------- codigos LCSC
# Partes concretas por (valor, footprint). Se aplican abajo a toda instancia
# que no traiga un LCSC propio en sus props.
#
# POR QUE UNA TABLA Y NO UN CAMPO POR INSTANCIA: hay 40 pasivos y siete
# valores distintos. Con el codigo repetido en cada linea, cambiar una parte
# obliga a cazar todas sus apariciones, y basta olvidar una para mandar dos
# partes distintas con el mismo valor. Aca el valor y el encapsulado eligen
# la parte, que es exactamente como decide el emparejador de JLCPCB.
#
# LA TENSION FORMA PARTE DE LA CLAVE, aunque no se vea: un X5R pierde
# capacidad por polarizacion continua, y cuanto mas cerca de su tension
# nominal trabaja, mas pierde. Por eso los rieles de 5V llevan 0805/25V y no
# 0603: JLCPCB habia emparejado C5 con un 22uF de 6.3V, que a 5V deja unos
# 5uF de los 22. Con el de 25V quedan ~13uF.
LCSC_PASIVOS = {
    # Resistencias UNI-ROYAL 0603, 1%, 100mW, 75V.
    ("100k", R_FP): "C25803",
    ("10k",  R_FP): "C25804",
    ("200k", R_FP): "C25811",
    ("20k",  R_FP): "C4184",
    ("27k",  R_FP): "C22967",
    ("470R", R_FP): "C23179",
    ("4.7k", R_FP): "C23162",
    ("47k",  R_FP): "C25819",
    ("5.1k", R_FP): "C23186",
    ("100R", R_FP): "C22775",
    ("150k", R_FP): "C22807",   # 0603WAF1503T5E (ISET del ETA6096)
    # Ceramicos.
    ("100nF", C_FP):     "C14663",   # 50V X7R
    ("1uF",   C_FP):     "C15849",   # 50V X5R
    ("2.2nF", C_FP):     "C1604",    # 50V X7R
    ("2.2uF", C_FP):     "C23630",   # 16V X5R  (bomba de carga del DAC)
    ("10uF",  C_FP):     "C19702",   # 10V X5R  (3V3, que es riel de 3.3V)
    ("22uF",  C0805_FP): "C45783",   # 25V X5R  (5V y VSYS: ver nota arriba)
    ("100uF", C1206_FP): "C15008",   # 6.3V X5R (VREF25, que reposa en 2.5V)
}

for _s, _r, _v, _x, _y, _n, _p in INSTANCES:
    if not _p.get("LCSC"):
        _codigo = LCSC_PASIVOS.get((_v, _p.get("FP")))
        if _codigo:
            _p["LCSC"] = _codigo
