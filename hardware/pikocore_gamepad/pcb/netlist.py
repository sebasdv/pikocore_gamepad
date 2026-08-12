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
             "siempre seleccionado, asi que su SPI no se puede compartir — por "
             "eso la microSD va a SPI1.",
        ds="",
        pins=_left_pins(["GND", "VCC", "SCL", "SDA", "RES", "DC", "BLK"]),
    ),
    "PCF8574": dict(
        ref="U", w=10.16, h=20.32,
        desc="Expansor I2C de 8 bits, quasi-bidireccional con pull-up interno "
             "de 100uA. Variante SIN sufijo A: direcciones 0x20-0x27 (la "
             "PCF8574A responde en 0x38-0x3F y no sirve para este diseno).",
        ds="https://www.ti.com/lit/ds/symlink/pcf8574.pdf",
        pins=_dual_pins(
            ["A0", "A1", "A2", "P0", "P1", "P2", "P3", "VSS"],
            ["P4", "P5", "P6", "P7", "INT", "SCL", "SDA", "VDD"]),
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
        desc="Tact switch 6x6mm THT, 4 pines. Los 4 pines son DOS PARES "
             "cortocircuitados internamente (1-2 y 3-4) y el contacto une los "
             "pares. Por eso el cableado es DIAGONAL, tomando un pin de cada "
             "par: garantiza cruzar el contacto sin depender de que par toco.",
        ds="",
        pins=[("1", "A", -7.62, 1.27, 0), ("2", "A", -7.62, -1.27, 0),
              ("3", "B", 7.62, -1.27, 180), ("4", "B", 7.62, 1.27, 180)],
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
    "NJM4556AD": dict(
        ref="U", w=10.16, h=12.7,
        desc="Op-amp dual SOIC-8, 70mA de salida (maneja auriculares de 32 ohm). "
             "Un op-amp por canal hace el buffer del jack Y el drive. Pinout "
             "verificado en V1 contra el simbolo de LCSC C2838125: es el "
             "estandar de op-amp dual, identico al 4558/5532/TL072 y comun a DIP-8 y SOIC-8: el encapsulado no cambia la numeracion.",
        ds="https://www.mouser.com/datasheet/2/294/NJM4556A_E-1917507.pdf",
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
        desc="Boost sincronico 5V, SOT-563 (encapsulado DRL de TI), conmuta ~1MHz (lejos de la banda "
             "de audio). Alimenta SOLO al NJM4556AD: el riel analogico tiene "
             "que ser fijo y no seguir a la bateria. PINOUT SIN VERIFICAR — "
             "confirmar contra la hoja de datos de TI antes de fabricar.",
        ds="https://www.ti.com/lit/ds/symlink/tps61023.pdf",
        pins=_dual_pins(["VIN", "GND", "EN"], ["FB", "VOUT", "SW"]),
    ),
    # ---------------------------------------------------------- conectores
    "JACK_AUDIO": dict(
        ref="J", w=7.62, h=10.16,
        desc="Jack 3.5mm estereo THT con contacto de deteccion NC. El pin DET "
             "va a JACK_DET con pull-up: el firmware apaga el parlante al "
             "detectar plug. Se decide por firmware y no por hardware a "
             "proposito — permite politicas como 'auriculares puestos pero "
             "quiero oir el parlante igual', que un corte mecanico prohibe. "
             "PINOUT SIN VERIFICAR: la parte todavia no esta elegida (V-3).",
        ds="",
        pins=_left_pins(["TIP", "RING", "SLEEVE", "DET"]),
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
    "Conn_01x09": dict(
        ref="J", w=5.08, h=25.4,
        desc="Header de expansion: 3V3, GND, VSYS y los 6 GPIO libres. "
             "GP26/27/28 son los unicos con ADC del header y quedan "
             "disponibles para un potenciometro de volumen futuro.",
        ds="",
        pins=_left_pins(["3V3", "GND", "VSYS"] +
                        [f"GP{g}" for g in pinmap.FREE]),
    ),
    "TP": dict(
        ref="TP", w=2.54, h=2.54,
        desc="Testpoint. Los dos puertos libres de U12 salen aca en vez de "
             "quedar flotantes, que es lo que dispara un warning de ERC.",
        ds="",
        pins=[("1", "TP", -5.08, 0.0, 0)],
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
# el NJM4556AD antes de confirmarlo contra LCSC. Verificar antes de fabricar.
PINOUT_SIN_VERIFICAR = ("TPS61023", "JACK_AUDIO")

# Numeros de pin del PCF8574 para P0..P7. Sale del pinout del datasheet
# (P0-P3 = 4,5,6,7 y P4-P7 = 9,10,11,12).
PCF_P_PINS = ["4", "5", "6", "7", "9", "10", "11", "12"]

# ---------------------------------------------------------------- footprints
# El tact de V2 es de 6x6 (spec 4.2) pero esa parte todavia no esta importada
# de LCSC (V-4). Se apunta al 4.5x4.5 de V1 —conservado en la libreria
# justamente como fallback— para que el flujo corra end-to-end. Cuando el 6x6
# este importado, cambiar SOLO esta constante: no hay otro lugar que tocar, y
# el test de footprints existentes avisa si el nombre no resuelve.
BTN_FP = "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5"
# Gatillos L y R: tact ANGULADO, para que el dedo los apriete de costado desde
# el borde y no contra la cara del panel. El footprint viene con KiCad y es el
# de C&K PTS645. Las variantes de largo de actuador (Vx31/39/58/83) comparten
# EXACTAMENTE la misma geometria de pads, asi que el largo se elige al definir
# el enclosure sin tocar la PCB: solo cambia el numero de parte.
BTN_RA_FP = "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS"
NAV_FP = "gamesetup_lcsc:SW-TH_WS-1004-ARL10026"
PCF_FP = "Package_SO:TSSOP-16_4.4x5mm_P0.65mm"
R_FP = "Resistor_SMD:R_0603_1608Metric"
C_FP = "Capacitor_SMD:C_0603_1608Metric"
TP_FP = "TestPoint:TestPoint_Pad_D1.5mm"
# Op-amp y optoacoplador pasan a SMD para que los monte JLC. No es solo
# comodidad de armado: liberan 95 mm2 del dorso (66% y 57% de su area de pads
# respectivamente), que es donde la placa esta apretada.
# El header del parlante NO se convierte: medido, el JST en SMD ocupa 55 mm2
# contra 6 del THT — nueve veces mas, por las lenguetas de anclaje y los pads
# anchos. Ademas recibe la fuerza de insercion de un conector, donde THT es
# mejor, y soldar dos pines pasantes no es trabajo.
OPAMP_FP = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
# El jack de audio todavia no esta elegido (V-3: se descarto el PJ-320A de V1
# por no tener datasheet publico). Se usa un header de 4 pines como stand-in
# para que el flujo corra; la geometria NO es la del jack.
JACK_FP = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"

# Footprints que estan puestos para que el flujo corra, no porque sean los
# definitivos. La puerta G-0 los reporta y bloquea la generacion de gerbers
# mientras queden: un footprint provisional que llega a fabricacion es una
# placa donde la pieza no entra.
FOOTPRINTS_PROVISIONALES = {
    "OPAMP_FP": "el NJM4556AD que se eligio (C2838125) es DIP-8; la version "
                "SOIC es otra parte (NJM4556AM o equivalente) y falta su "
                "codigo LCSC (V-4)",
    "BTN_RA_FP": "tact angulado para L/R: el footprint es el de C&K PTS645 que "
                 "trae KiCad, pero falta elegir el numero de parte concreto y "
                 "el largo de actuador, que depende del enclosure (V-4)",
    "BTN_FP": "tact 6x6 sin importar de LCSC (V-4); se usa el 4.5x4.5 de V1",
    "JACK_FP": "jack de audio sin elegir (V-3); se usa un header de 4 pines "
               "como stand-in y la geometria NO es la correcta",
}


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


# Los 12 tacts: (ref, net de senal). El orden sigue al enum GcButton del
# firmware (src/input/ControlsTypes.h) precedido por el D-pad.
TACTS = [
    ("SW1", "DPAD_UP"), ("SW2", "DPAD_DOWN"),
    ("SW3", "DPAD_LEFT"), ("SW4", "DPAD_RIGHT"),
    ("SW5", "BTN_X"), ("SW6", "BTN_Y"),
    ("SW7", "BTN_A"), ("SW8", "BTN_B"),
    ("SW11", "BTN_START"), ("SW12", "BTN_SELECT"),
]

# Mapa P0..P7 de cada expansor (spec 3.2). Cada nav queda ENTERO en un chip
# para que una lectura I2C devuelva un estado coherente de sus 5 vias: si
# quedara repartido entre dos chips, dos lecturas distintas podrian mostrar
# una diagonal que el usuario nunca hizo.
PCF_MAP = {
    "U10": ["DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
            "BTN_X", "BTN_Y", "BTN_A", "BTN_B"],
    "U11": ["NAV1_UP", "NAV1_DOWN", "NAV1_LEFT", "NAV1_RIGHT", "NAV1_CENTER",
            "BTN_L", "BTN_R", "BTN_START"],
    "U12": ["NAV2_UP", "NAV2_DOWN", "NAV2_LEFT", "NAV2_RIGHT", "NAV2_CENTER",
            "BTN_SELECT", "TP_SPARE1", "TP_SPARE2"],
}
# A0/A1/A2 de cada expansor: 0x20 = 000, 0x21 = 001, 0x22 = 010.
PCF_ADDR_BITS = {"U10": (0, 0, 0), "U11": (1, 0, 0), "U12": (0, 1, 0)}

# Los expansores arrancan en U10 a proposito, reservando el bloque U1-U6 para
# los integrados de una sola pieza (MCU, boost, op-amp, class-D, DAC, opto).
# Eso deja U7-U9 sin usar y check_refs.py lo reporta como hueco: es esperado,
# no un componente perdido. Renumerarlos desincronizaria las referencias con
# boards/rp2350plus_v2/config.h y con el spec.


def _pcf_instances():
    out = []
    for i, (ref, sigs) in enumerate(PCF_MAP.items()):
        a0, a1, a2 = PCF_ADDR_BITS[ref]
        nets = {
            "1": "3V3" if a0 else "GND",   # A0
            "2": "3V3" if a1 else "GND",   # A1
            "3": "3V3" if a2 else "GND",   # A2
            "8": "GND", "16": "3V3",       # VSS / VDD
            "13": "PCF_INT", "14": "I2C_SCL", "15": "I2C_SDA",
        }
        for pin, sig in zip(PCF_P_PINS, sigs):
            nets[pin] = sig
        out.append(("PCF8574", ref, "PCF8574MT", 60.0, 40.0 + 60.0 * i,
                    nets, {"LCSC": "C22461594", "FP": PCF_FP}))
    return out


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

# ----------------------------------------------------------- expansores I2C
INSTANCES += _pcf_instances()

INSTANCES += [
    # Pull-ups del bus. El /INT de los tres chips va en wired-OR, asi que
    # lleva UN pull-up, no tres.
    ("R", "R1", "4.7k", 140.0, 30.0, {"1": "3V3", "2": "I2C_SDA"}, {"FP": R_FP}),
    ("R", "R2", "4.7k", 150.0, 30.0, {"1": "3V3", "2": "I2C_SCL"}, {"FP": R_FP}),
    ("R", "R3", "10k", 160.0, 30.0, {"1": "3V3", "2": "PCF_INT"}, {"FP": R_FP}),
    # Un desacople por expansor.
    ("C", "C1", "100nF", 80.0, 40.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("C", "C2", "100nF", 80.0, 100.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("C", "C3", "100nF", 80.0, 160.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    # Los dos puertos libres de U12 salen a testpoints en vez de quedar
    # flotantes, que es lo que dispara un warning de ERC.
    ("TP", "TP1", "SPARE1", 100.0, 170.0, {"1": "TP_SPARE1"}, {"FP": TP_FP}),
    ("TP", "TP2", "SPARE2", 105.0, 170.0, {"1": "TP_SPARE2"}, {"FP": TP_FP}),
]

# ------------------------------------------------------------------- tacts
INSTANCES += [
    ("SW_Push", ref, sig, 240.0, 20.0 + 12.0 * i,
     {"1": sig, "4": "GND", "2": NC, "3": NC},
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

# ------------------------------------------------------------ nav switches
INSTANCES += [
    ("NAV_WS1004", "SW13", "NAV1", 300.0, 40.0, {
        "1": "GND", "2": "NAV1_LEFT", "3": "NAV1_CENTER",
        "4": "NAV1_UP", "5": "NAV1_RIGHT", "6": "NAV1_DOWN"},
     {"LCSC": "C42377836", "FP": NAV_FP}),
    ("NAV_WS1004", "SW14", "NAV2", 300.0, 100.0, {
        "1": "GND", "2": "NAV2_LEFT", "3": "NAV2_CENTER",
        "4": "NAV2_UP", "5": "NAV2_RIGHT", "6": "NAV2_DOWN"},
     {"LCSC": "C42377836", "FP": NAV_FP}),
]

# --------------------------------------------------- alimentacion y EXP
INSTANCES += [
    # El pin 3V3_EN del header tiene pull-up interno de 100k a VSYS hacia el
    # EN del MP28164: cerrarlo contra GND apaga el rail de 3V3 del modulo.
    ("SK12D07", "SW15", "PWR", 20.0, 160.0,
     {"1": "GND", "2": "PWR_EN", "3": NC, "4": "GND", "5": "GND"},
     {"LCSC": "C431547", "FP": "gamesetup_lcsc:SW-TH_SK12D07VG3"}),
    ("Conn_01x09", "J7", "EXP", 20.0, 60.0, {
        "1": "3V3", "2": "GND", "3": "VSYS",
        "4": "EXP_GP9", "5": "EXP_GP14", "6": "EXP_GP15",
        "7": "EXP_GP26", "8": "EXP_GP27", "9": "EXP_GP28"},
     {"FP": "Connector_PinHeader_2.54mm:PinHeader_1x09_P2.54mm_Vertical"}),
]

# =================================================================== AUDIO
#
#   VSYS -[L2]- VSYS_F -[L1]- TPS61023 -> 5V   (riel analogico FIJO)
#                                          |
#   PCM5102A -[470R+2n2]-> NJM4556AD -[470uF]-> JACK 3.5mm
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
    ("TPS61023", "U2", "TPS61023DRLR", 40.0, 220.0, {
        "1": "VSYS_F", "2": "GND", "3": "VSYS_F",
        "4": "BOOST_FB", "5": "5V", "6": "BOOST_SW"},
     {"LCSC": "C919459", "FP": "Package_TO_SOT_SMD:SOT-563"}),
    # Filtro LC de entrada (spec 5.2.1): que la conmutacion no vuelva por VSYS
    # hasta el regulador del modulo.
    ("L", "L2", "2u2", 25.0, 210.0,
     {"1": "VSYS", "2": "VSYS_F"}, {"LCSC": "C3002559", "FP": L_FP}),
    ("C", "C4", "10uF", 32.0, 215.0, {"1": "VSYS_F", "2": "GND"}, {"FP": C_FP}),
    ("L", "L1", "2u2", 50.0, 210.0,
     {"1": "VSYS_F", "2": "BOOST_SW"}, {"LCSC": "C3002559", "FP": L_FP}),
    ("R", "R4", "1M", 58.0, 225.0, {"1": "5V", "2": "BOOST_FB"}, {"FP": R_FP}),
    ("R", "R5", "200k", 58.0, 235.0, {"1": "BOOST_FB", "2": "GND"}, {"FP": R_FP}),
    ("C", "C5", "22uF", 66.0, 215.0, {"1": "5V", "2": "GND"}, {"FP": C_FP}),
    # Bulk local del riel de 5V, fisicamente junto a los pines del op-amp.
    ("CP", "C6", "100uF", 74.0, 215.0, {"1": "5V", "2": "GND"}, {"FP": CP_FP}),
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
    ("C", "C8", "2u2", 128.0, 205.0, {"1": "CAPP", "2": "CAPM"}, {"FP": C_FP}),
    ("C", "C9", "2u2", 136.0, 205.0, {"1": "VNEG", "2": "GND"}, {"FP": C_FP}),
    ("C", "C10", "100nF", 144.0, 205.0, {"1": "LDOO", "2": "GND"}, {"FP": C_FP}),
    # Un 100n + un 10uF por riel (AVDD / CPVDD / DVDD), segun SLAS859C.
    ("C", "C11", "100nF", 152.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("CP", "C12", "10uF", 160.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": CP_FP}),
    ("C", "C13", "100nF", 168.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("CP", "C14", "10uF", 176.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": CP_FP}),
    ("C", "C15", "100nF", 184.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
    ("CP", "C16", "10uF", 192.0, 205.0, {"1": "3V3", "2": "GND"}, {"FP": CP_FP}),
    # XSMT con pulldown: el DAC arranca MUTEADO y el firmware lo libera. El
    # modulo GY-PCM5102 lo traia a 3V3 de fabrica; chip-down hay que ponerlo,
    # si no hay un golpe audible en el arranque.
    ("R", "R6", "100k", 120.0, 205.0, {"1": "DAC_XSMT", "2": "GND"}, {"FP": R_FP}),
    # Filtro de salida del DAC (SLAS859C): 470R + 2n2 por canal.
    ("R", "R7", "470R", 120.0, 240.0,
     {"1": "DACOUT_L", "2": "AOUT_L"}, {"FP": R_FP}),
    ("C", "C17", "2n2", 128.0, 245.0, {"1": "AOUT_L", "2": "GND"}, {"FP": C_FP}),
    ("R", "R8", "470R", 136.0, 240.0,
     {"1": "DACOUT_R", "2": "AOUT_R"}, {"FP": R_FP}),
    ("C", "C18", "2n2", 144.0, 245.0, {"1": "AOUT_R", "2": "GND"}, {"FP": C_FP}),

    # -------------------------------------------------------------- op-amp
    ("NJM4556AD", "U3", "NJM4556AD", 240.0, 220.0, {
        "1": "AUDIO_L", "2": "OPL_N", "3": "VREF25", "4": "GND",
        "5": "VREF25", "6": "OPR_N", "7": "AUDIO_R", "8": "5V"},
     {"FP": OPAMP_FP}),
    # Masa virtual a 2.5V: es lo que permite alimentacion simple de 5V.
    ("R", "R9", "10k", 224.0, 205.0, {"1": "5V", "2": "VREF25"}, {"FP": R_FP}),
    ("R", "R10", "10k", 232.0, 205.0, {"1": "VREF25", "2": "GND"}, {"FP": R_FP}),
    ("CP", "C19", "100uF", 240.0, 205.0, {"1": "VREF25", "2": "GND"}, {"FP": CP_FP}),
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
    ("CP", "C23", "470uF", 256.0, 235.0,
     {"1": "AUDIO_L", "2": "JACK_L"}, {"FP": CP_FP}),
    ("CP", "C24", "470uF", 256.0, 245.0,
     {"1": "AUDIO_R", "2": "JACK_R"}, {"FP": CP_FP}),

    # ---------------------------------------------------------------- jack
    ("JACK_AUDIO", "J1", "PHONES", 280.0, 240.0, {
        "1": "JACK_L", "2": "JACK_R", "3": "GND", "4": "JACK_DET"},
     {"FP": JACK_FP}),
    # Pull-up externo: antes de que el firmware configure el pin, el interno
    # no esta activo y DET quedaria flotante.
    ("R", "R15", "10k", 288.0, 225.0,
     {"1": "3V3", "2": "JACK_DET"}, {"FP": R_FP}),

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
    ("CP", "C28", "10uF", 320.0, 255.0, {"1": "VSYS", "2": "GND"}, {"FP": CP_FP}),
    # Salida BTL: ningun terminal va a masa.
    ("Conn_01x02", "J5", "SPEAKER 8R", 330.0, 265.0,
     {"1": "SPK_P", "2": "SPK_N"},
     {"FP": "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"}),
]
