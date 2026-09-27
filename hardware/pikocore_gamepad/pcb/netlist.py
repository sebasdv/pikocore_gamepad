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

# El orden de los 40 pines del socket sale de pinmap.py, que es la fuente de
# verdad del pinout y la que check_pinmap contrasta contra el firmware. Tener
# una segunda copia aca fue el primer instinto y es un error: dos tablas del
# mismo dato derivan, y la divergencia no la detecta nadie.
PICO_PINS = pinmap.HEADER_ORDER


def _mcu_pin_geometry():
    """Los 40 pines del socket: 20 bajando por la izquierda, 20 subiendo por
    la derecha, como el header fisico."""
    out = []
    for i in range(20):
        out.append((str(i + 1), PICO_PINS[i], -17.78, 24.13 - 2.54 * i, 0))
    for i in range(20):
        out.append((str(i + 21), PICO_PINS[20 + i], 17.78, -24.13 + 2.54 * i, 180))
    return out


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
    "RP2350-Plus": dict(
        ref="U", w=15.24, h=27.94,
        desc="Waveshare RP2350-Plus 16MB (RP2350A, cargador LiPo ETA6096, "
             "USB-C). Pin-compatible Raspberry Pi Pico, montado en socket 2x20. "
             "GP23/24/25 son internos del modulo y GP29 no sale al header.",
        ds="https://www.waveshare.com/wiki/RP2350-Plus",
        pins=_mcu_pin_geometry(),
    ),
    "LCD_ST7789": dict(
        ref="J", w=7.62, h=10.16,
        desc="Modulo IPS 1.3in 240x240 ST7789, 7 pines. NO tiene pin CS: esta "
             "siempre seleccionado, asi que su SPI no se puede compartir con "
             "ningun otro periferico.",
        ds="",
        pins=_left_pins(["GND", "VCC", "SCL", "SDA", "RES", "DC", "BLK"]),
    ),
    "NAV_WS1004": dict(
        ref="SW", w=7.62, h=12.7,
        desc="XUNPU WS-1004-ARL10026, nav switch de 5 vias THT 10.2x10.2mm. "
             "Pinout de datasheet: 1=COM 2=LEFT 3=CENTRO 4=UP 5=RIGHT 6=DOWN. "
             "Cada direccion cierra contra el comun (pin 1).",
        ds="https://www.lcsc.com/product-detail/C42377836.html",
        pins=_left_pins(["COM", "LEFT", "CENTER", "UP", "RIGHT", "DOWN"]),
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
PINOUT_SIN_VERIFICAR = ()

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
NAV_FP = "gamesetup_lcsc:SW-TH_WS-1004-ARL10026"
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


def _mcu_nets():
    """Nets del socket del MCU, DERIVADAS de pinmap.py.

    Se generan y no se escriben a mano a proposito: en V1 la tabla estaba
    duplicada entre el esquematico y config.h, y mantenerlas sincronizadas a
    ojo fue una fuente constante de error. Aca la unica fuente es pinmap, que
    ademas es la que check_pinmap contrasta contra el firmware.
    """
    nets = {}
    for i, name in enumerate(PICO_PINS):
        pin = str(i + 1)
        if name in ("GND", "AGND"):
            nets[pin] = "GND"
        elif name == "3V3":
            nets[pin] = "3V3"
        elif name == "VSYS":
            nets[pin] = "VSYS"
        elif name == "3V3_EN":
            nets[pin] = "PWR_EN"
        elif name.startswith("GP"):
            g = int(name[2:])
            if g in pinmap.GPIO:
                nets[pin] = pinmap.GPIO[g]
            elif g in pinmap.FREE:
                nets[pin] = f"EXP_GP{g}"
            else:
                nets[pin] = NC
        else:
            # RUN, ADC_VREF y VBUS no se usan: el modulo los resuelve solo.
            nets[pin] = NC
    return nets


# Los 6 tacts restantes (X/Y/A/B, Start/Select): (ref, net de senal). El
# orden sigue al enum GcButton del firmware (src/input/ControlsTypes.h). El
# D-pad se resuelve aparte, via el NAV5 (ver bloque "NAV5" mas abajo).
TACTS = [
    ("SW5", "BTN_X"), ("SW6", "BTN_Y"),
    ("SW7", "BTN_A"), ("SW8", "BTN_B"),
    ("SW11", "BTN_START"), ("SW12", "BTN_SELECT"),
]

INSTANCES = [
    # ---------------------------------------------------------------- MCU
    ("RP2350-Plus", "U1", "RP2350-Plus-16MB", 60.0, 60.0, _mcu_nets(),
     {"FP": "gamesetup_fp:RP2350-Plus_Socket"}),

    # ------------------------------------------------------------ display
    ("LCD_ST7789", "J4", "ST7789_240x240", 200.0, 40.0, {
        "1": "GND", "2": "3V3", "3": "LCD_SCK", "4": "LCD_MOSI",
        "5": "LCD_RES", "6": "LCD_DC", "7": "LCD_BLK"},
     {"FP": "gamesetup_fp:LCD_ST7789_240x240_7P"}),
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

# ------------------------------------------------------------------- NAV5
# Reemplaza el D-pad de 4 tacts. Cablea directo al MCU (sin expansor: a
# diferencia de GAMESETUP, aca sobran GPIO). El comun (pin 1) va a masa; cada
# direccion, incluido el centro, a su propio GPIO con pull-up de firmware.
INSTANCES += [
    ("NAV_WS1004", "SW13", "NAV5", 300.0, 40.0, {
        "1": "GND", "2": "DPAD_LEFT", "3": "BTN_OK",
        "4": "DPAD_UP", "5": "DPAD_RIGHT", "6": "DPAD_DOWN"},
     {"LCSC": "C42377836", "FP": NAV_FP}),
]

# --------------------------------------------------- alimentacion y EXP
INSTANCES += [
    # El pin 3V3_EN del header tiene pull-up interno de 100k a VSYS hacia el
    # EN del MP28164: cerrarlo contra GND apaga el rail de 3V3 del modulo.
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
