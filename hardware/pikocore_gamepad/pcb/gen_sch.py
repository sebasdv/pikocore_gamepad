#!/usr/bin/env python3
"""Genera pikocore_gamepad.kicad_sch + .kicad_sym + .kicad_pro desde netlist.py.

Python puro, sin pcbnew: escribe los archivos como texto.

A diferencia de V1, este script es SUFICIENTE POR SI SOLO. V1 obligaba a
correr add_nav2_sch.py a continuacion, y olvidarlo dejaba el esquematico sin
el subsistema nav2 —cinco componentes y sus nets— sin ningun error visible.
Aca todo sale de netlist.py.

Las conexiones se hacen por GLOBAL LABELS en el extremo de cada pin, no por
cables. Es lo que permite generar un esquematico legible sin resolver ruteo
de wires, y lo que hace que el netlist dependa solo de la tabla.

pikocore_gamepad.kicad_pro NO se sobrescribe si ya existe: KiCad lo enriquece con
los ajustes de diseno de la placa (anchos de pista, clearances, reglas de
DRC) que no estan en este generador, y regenerarlo los borra en silencio.
Para forzar el reset, borrar el archivo a mano.

sym-lib-table NO lo escribe este script: es un archivo estatico versionado
(lo crea el Task 8). Tener dos fuentes del mismo archivo es como se
desincronizan las cosas.
"""
import json
import os

from netlist import SYMS, INSTANCES, NC

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = "pikocore_gamepad"

# UUID de la hoja raiz: FIJO, no aleatorio. Hace la regeneracion reproducible:
# sin esto cada corrida cambia todos los uuid y el diff de git queda
# inservible para revisar un cambio de netlist.
ROOT_UUID = "b1e7c2a4-9f31-4d6e-8a52-3c0f7d418e6b"

FECHA = "2026-08-28"
GRID = 1.27
EFFECTS = "(effects (font (size 1.27 1.27)))"
EFFECTS_H = "(effects (font (size 1.27 1.27)) (hide yes))"

_uuid_seq = 0


def u():
    """UUID deterministico. A diferencia de V1 (que usaba uuid4) esto hace que
    dos corridas sin cambios produzcan un archivo IDENTICO, asi que el diff de
    git muestra solo lo que cambio de verdad."""
    global _uuid_seq
    _uuid_seq += 1
    return f"{ROOT_UUID[:24]}{_uuid_seq:012x}"


def F(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def _snap(v):
    return round(v / GRID) * GRID


# ------------------------------------------------------------------- hojas
# El esquematico va repartido en hojas jerarquicas, una por bloque funcional.
# El motivo es de REVISION, no estetico: con los 63 componentes en una sola
# hoja, quien verifica la etapa de audio tiene que leer alrededor de los doce
# botones, y quien verifica la alimentacion tiene que encontrar el boost entre
# medio del DAC. Cada hoja se puede firmar por separado.
#
# NO HACEN FALTA PINES DE HOJA. Todo el diseno conecta por GLOBAL LABELS, que
# en KiCad valen para el proyecto ENTERO sin importar la jerarquia. La hoja
# raiz no lleva una sola senal cableada: solo los simbolos de hoja y las notas
# generales. Por eso repartir no cambia ni una conexion — lo verifica G-2,
# que compara el netlist del esquematico contra el de la placa.
#
# El reparto es explicito y se verifica (ver verificar_reparto): si se agrega
# una pieza a netlist.py y no se la asigna, el generador FALLA. Sin esa
# comprobacion la pieza quedaria fuera del esquematico en silencio, que es
# exactamente el tipo de error que una revision por hojas deberia evitar.
HOJAS = [
    ("01_alimentacion", "Alimentacion - boost 5V y encendido", [
        "SW15",                                    # corta 3V3_EN del modulo
        "U2", "L2", "C4", "L1", "R4", "R5",        # TPS61023 y su lazo
        "C5", "C6", "C7",                          # bulk de salida
    ], ["NOTA_ALIM"]),

    ("02_mcu_controles", "MCU, pantalla y controles", [
        "U1",                                      # modulo RP2350-Plus
        "J4",                                      # LCD ST7789
        "SW13",                                    # NAV5 (D-pad)
        "SW5", "SW6", "SW7", "SW8",                # X Y A B
        "SW11", "SW12",                            # START SELECT
        "SW9", "SW10",                             # gatillos L y R
    ], ["NOTA_ENTRADA"]),

    ("03_dac", "Audio digital - DAC PCM5102A", [
        "U5",
        "C8", "C9",                                # bomba de carga
        "C10",                                     # LDOO
        "C11", "C12", "C13", "C14", "C15", "C16",  # desacoplo de 3V3
        "R6",                                      # pulldown de XSMT
        "R7", "C17", "R8", "C18",                  # filtro RC de salida
    ], ["NOTA_DAC"]),

    ("04_opamp", "Audio analogico - buffer y masa virtual", [
        "U3",
        "R9", "R10", "C19", "C20",                 # VREF25
        "C21", "R11", "R12",                       # canal izquierdo
        "C22", "R13", "R14",                       # canal derecho
        "C23", "C24",                              # acoplo hacia el jack
    ], ["NOTA_OPAMP"]),

    ("05_salidas", "Salidas - jack, deteccion y parlante", [
        "J1", "R15", "R18", "C29", "R19", "R20",   # jack y deteccion
        "R16", "R17", "C25", "C26",                # suma mono
        "U4", "C27", "C28", "J5",                  # class-D y parlante
    ], ["NOTA_JACK", "NOTA_SPK"]),
]


def verificar_reparto():
    """Cada instancia en exactamente una hoja.

    Si falta, el componente no aparece en NINGUN esquematico pero si en la
    placa: G-2 lo encontraria, pero recien al comparar netlists, y el mensaje
    no diria que el problema es el reparto.
    """
    todos = [i[1] for i in INSTANCES]
    asignados = [r for _, _, refs, _ in HOJAS for r in refs]
    faltan = sorted(set(todos) - set(asignados))
    sobran = sorted(set(asignados) - set(todos))
    dobles = sorted({r for r in asignados if asignados.count(r) > 1})
    problemas = []
    if faltan:
        problemas.append("sin hoja asignada: " + ", ".join(faltan))
    if sobran:
        problemas.append("en HOJAS pero no en INSTANCES: " + ", ".join(sobran))
    if dobles:
        problemas.append("repetidos en dos hojas: " + ", ".join(dobles))
    if problemas:
        raise SystemExit("REPARTO DE HOJAS MAL:\n  " + "\n  ".join(problemas))


def uuid_hoja(i):
    """UUID fijo por hoja.

    Tiene que ser ESTABLE entre corridas: forma parte del path de cada
    instancia (/raiz/hoja) y de los ajustes del .kicad_pro. Si cambiara,
    KiCad veria todos los componentes como nuevos y perderia sus campos.
    El prefijo 'f' lo mantiene fuera del rango que consume u().
    """
    return f"{ROOT_UUID[:24]}f{i:011x}"


PASIVOS = ("R", "C", "CP", "L", "D")

MARGEN = 20.0        # aire contra el marco de la hoja
ETIQUETA = 46.0      # aire lateral por celda para que entren las global labels
AIRE_Y = 15.0        # aire vertical por celda
ANCHO_UTIL = 380.0   # ancho de grilla que todavia entra en A3

PAPELES = (("A4", 297.0, 210.0), ("A3", 420.0, 297.0), ("A2", 594.0, 420.0))


def _papel(w, h):
    for nombre, pw, ph in PAPELES:
        if w <= pw and h <= ph:
            return nombre
    return "A1"


def _orden(inst):
    """Chips primero y pasivos despues; dentro de los chips, el de mas pines
    arriba de todo.

    El criterio del pin count no es cosmetico: la hoja se lee de arriba a la
    izquierda, y ahi tiene que estar la pieza que define el bloque —el MCU, el
    DAC, el op-amp— no el primer componente que caiga por orden alfabetico.
    Entre pasivos manda la referencia, con el numero ordenado COMO NUMERO:
    R10 va despues de R9, no entre R1 y R2."""
    ref = inst[1]
    pre = "".join(c for c in ref if c.isalpha())
    num = "".join(c for c in ref if c.isdigit())
    es_pasivo = inst[0] in PASIVOS
    pines = 0 if es_pasivo else -len(SYMS[inst[0]]["pins"])
    return (es_pasivo, pines, pre, int(num) if num else 0)


def _layout_hoja(instancias):
    """Grilla uniforme, con la celda dimensionada por el simbolo mas grande
    de ESTA hoja.

    Uniforme y no ajustada pieza por pieza a proposito: lo que hace legible a
    un esquematico generado es que la posicion sea PREDECIBLE. Quien revisa
    encuentra R11 donde espera —bloque de pasivos, ordenados por referencia—
    y no donde haya caido. Las coordenadas que trae netlist.py se ignoran:
    eran indicativas y servian para agrupar por subsistema, que ahora lo hace
    el reparto en hojas.

    La celda mide el DOBLE del simbolo mas ancho porque w y h son semiejes.
    De ahi sale tambien que ningun par de pines pueda coincidir, que es lo que
    verifica verificar_colisiones.
    """
    if not instancias:
        return [], 0.0, 0.0
    w = max(SYMS[i[0]]["w"] for i in instancias)
    h = max(SYMS[i[0]]["h"] for i in instancias)
    cw = _snap(2 * w + ETIQUETA)
    ch = _snap(2 * h + AIRE_Y)
    cols = max(1, int((ANCHO_UTIL - 2 * MARGEN) // cw))
    out = []
    for n, (sym, ref, val, _x, _y, nets, props) in enumerate(
            sorted(instancias, key=_orden)):
        x = MARGEN + (n % cols) * cw + cw / 2
        y = MARGEN + (n // cols) * ch + ch / 2
        out.append((sym, ref, val, _snap(x), _snap(y), nets, props))
    filas = (len(out) + cols - 1) // cols
    return out, 2 * MARGEN + cols * cw, 2 * MARGEN + filas * ch


def verificar_colisiones(instancias):
    """Ningun punto puede tener dos pines de nets distintas.

    Dos pines que coinciden quedan electricamente unidos, asi que sus nets se
    fusionan. KiCad no lo llama error —solo avisa "multiple net names"— pero
    es un cortocircuito, y la netlist que sale hacia la PCB ya viene mal.

    Se corre por hoja: dos pines en hojas distintas no se tocan aunque
    compartan coordenada.
    """
    from collections import defaultdict
    puntos = defaultdict(list)
    for sym, ref, val, x, y, nets, props in instancias:
        for num, _, px, py, _ in SYMS[sym]["pins"]:
            puntos[(round(x + px, 3), round(y - py, 3))].append(
                (f"{ref}.{num}", nets[num]))
    malos = []
    for (px, py), pines in sorted(puntos.items()):
        if len({n for _, n in pines if n != NC}) > 1:
            malos.append(f"({px:.2f}, {py:.2f}): " +
                         " + ".join(f"{p}={n}" for p, n in pines))
    if malos:
        raise SystemExit("PINES SUPERPUESTOS CON NETS DISTINTAS "
                         "(cortocircuito):\n  " + "\n  ".join(malos))


# Notas por hoja. Cada una explica lo que el esquematico NO puede mostrar: por
# que el circuito es asi y no de otra forma. Es lo que necesita leer alguien
# que viene a verificar el diseno sin haberlo hecho.
NOTAS = {
    "NOTA_RAIZ":
        "pikocore_gamepad - PCB de 4 capas (F.Cu / GND / PWR / B.Cu), 120x80mm, panel unico.\n"
        "MCU: modulo Waveshare RP2350-Plus 16MB sobre socket 2x20.\n"
        "\n"
        "La bateria LiPo va al PH1.25 DEL PROPIO MODULO, que trae cargador ETA6096 a bordo:\n"
        "esta placa NO lleva circuito de carga. SW15 no corta la bateria, corta 3V3_EN del\n"
        "modulo, que tiene pull-up interno de 100K a VSYS.\n"
        "\n"
        "TODAS las conexiones son por GLOBAL LABEL, validas en las cinco hojas. La hoja raiz\n"
        "no tiene ninguna senal cableada: solo los simbolos de hoja y esta nota.",
    "NOTA_ALIM":
        "El riel de 5V alimenta SOLO al op-amp U3 (hoja 4). Es a proposito: el riel analogico\n"
        "tiene que ser FIJO y no seguir a la bateria, porque la masa virtual del op-amp se\n"
        "deriva de el. El class-D U4 (hoja 5) NO cuelga de aca sino de VSYS directo, porque a\n"
        "todo volumen pide cientos de mA y hacerlo pasar por el boost obligaria a dimensionarlo\n"
        "para el pico del parlante.\n"
        "\n"
        "Divisor de realimentacion: Vout = 0.595 * (1 + R4/R5) = 0.595 * (1 + 200k/27k) = 5.00V.\n"
        "\n"
        "C5 y C6 son 22uF/25V y NO de 6.3V: a 5V de polarizacion continua un X5R de 6.3V pierde\n"
        "cerca del 70% de su capacidad. Con los de 25V quedan ~13uF efectivos cada uno, o sea\n"
        "los ~22uF de salida que pide TI.\n"
        "\n"
        "BOOST_SW (U2.5 a L1.2) va ruteado A MANO en la placa, recto y de 2.29mm: es el nodo\n"
        "que conmuta a ~1MHz al lado de la cadena analogica, y no se deja librado al autoruteo.",
    "NOTA_ENTRADA":
        "Los 12 controles van DIRECTO a GPIO del modulo, sin expansor I2C. La asignacion esta\n"
        "en pinmap.py y la verifica la puerta G-4 contra el firmware.\n"
        "\n"
        "Los tacts de 6mm (SW5-SW8, SW11, SW12) tienen cuatro patas que son DOS PARES unidos\n"
        "dentro del switch; el simbolo declara 2 pines porque el footprint oficial de KiCad\n"
        "numera sus cuatro pads 1,1,2,2. Cablear 1 contra 2 ya cruza el contacto.\n"
        "\n"
        "SW9 y SW10 (gatillos) son angulados y tienen SOLO DOS patas electricas: las otras dos\n"
        "son soportes mecanicos, y en la placa son agujeros NO metalizados.\n"
        "\n"
        "SW13 es un NAV5 de 5 vias (arriba/abajo/izq/der/centro) y reemplaza a los cuatro tacts\n"
        "del D-pad de la version anterior. CONSECUENCIA PARA EL FIRMWARE: no se pueden pulsar\n"
        "arriba y abajo a la vez, asi que las combinaciones que lo pedian estan remapeadas.",
    "NOTA_DAC":
        "PCM5102A en modo chip-down, I2S generado por PIO. SCK (pin 12) A MASA: eso activa el\n"
        "PLL interno a partir de BCK y evita tener que generar MCLK. FMT/FLT/DEMP a masa.\n"
        "\n"
        "XSMT lleva pulldown de 100k (R6): el DAC arranca MUTEADO y lo libera el firmware, que\n"
        "es lo que evita el golpe en el parlante al encender.\n"
        "\n"
        "C8/C9 son la bomba de carga que genera VNEG. Es lo que centra la salida en MASA\n"
        "(+-2.8V, 2.0 Vrms) en vez de en medio riel, y de ahi sale el requisito de la hoja 4.\n"
        "\n"
        "Cada riel de 3V3 lleva 100nF Y 10uF: con un solo valor por riel no se cubre el rango\n"
        "de frecuencias que pide la hoja de datos (TI SLAS859C).",
    "NOTA_OPAMP":
        "U3 es INVERSOR, con ganancia 0.5 y entrada acoplada, y las tres cosas hacen falta: la\n"
        "salida del DAC son 2.0 Vrms centrados en MASA, y no entran en un riel simple de 5V con\n"
        "masa virtual en 2.5V. La ganancia 0.5 (R12/R11 = 10k/20k) los baja a 1.0 Vrms.\n"
        "\n"
        "C21/C22 bloquean la continua en la ENTRADA: sin ellos circularia continua por la\n"
        "resistencia de realimentacion y la salida se iria a 3.75V, comiendose el headroom.\n"
        "\n"
        "VREF25 = 5V/2 por R9/R10, con C19 (100uF) de reservorio. Contra el equivalente Thevenin\n"
        "de 5k eso pone el corte en 0.32Hz, muy por debajo del audio.\n"
        "\n"
        "C23/C24 (470uF) bloquean la continua hacia el jack. Son los UNICOS electroliticos de\n"
        "la placa y van SOLDADOS A MANO (marcados DNP, fuera del CPL). A 32 ohm de auricular\n"
        "dan el corte en 10.6Hz. Su terminal POSITIVO es el del lado de AUDIO_L / AUDIO_R.",
    "NOTA_JACK":
        "DETECCION DE AURICULARES - leer antes de tocar estos valores.\n"
        "\n"
        "Los switches del SJ1-3535NG NO son contactos libres: el pin 4 cierra contra el 2 (tip)\n"
        "y el 5 contra el 3 (ring), y ambos ABREN al insertar el plug. No hay ningun contacto\n"
        "que cierre contra masa, asi que el sensado convive con el audio por fuerza.\n"
        "\n"
        "El divisor se cierra por R20, el bleeder del canal derecho. SIN R20 el nodo JACK_R\n"
        "queda aislado por C24 —que bloquea continua— y NO SE FORMA NINGUN DIVISOR: DET se\n"
        "queda en 3V3 con y sin plug, o sea la deteccion no funciona en ningun estado.\n"
        "   sin plug: 3V3 -[R15 47k]- DET -[R18 4k7]- JACK_R -[R20 4k7]- GND = 0.55V -> BAJO\n"
        "   con plug: el contacto abre, DET sube a 3V3                              -> ALTO\n"
        "Hace falta R18+R20 << R15; por eso R18 es 4k7 y no 100k.\n"
        "\n"
        "C29 filtra el audio que R18 acopla al GPIO. Sin el, el pin leeria ALTO en cada pico de\n"
        "senal y el jack parpadearia. Cuesta ~480ms de latencia al enchufar.\n"
        "\n"
        "R19/R20 le dan ademas a C23/C24 la referencia de continua que no tenian: son\n"
        "electroliticos POLARIZADOS y su terminal negativo quedaba flotando sin auriculares.",
    "NOTA_SPK":
        "La suma mono se toma de AUDIO_L/AUDIO_R, o sea ANTES del bloqueo de continua. Si se\n"
        "tomara despues, el parlante se quedaria sin senal cuando no hay auriculares puestos.\n"
        "\n"
        "C25 acopla la entrada del class-D porque SPK_SUM reposa en VREF25 (2.5V) mientras el\n"
        "PAM8302A polariza sus entradas respecto de SU alimentacion, que es VSYS. Sin acoplo\n"
        "los dos puntos de reposo pelean.\n"
        "\n"
        "La salida es BTL: NINGUN terminal del parlante va a masa. Conectar SPK_N a masa rompe\n"
        "el amplificador.\n"
        "\n"
        "El apagado del parlante al enchufar auriculares es POR FIRMWARE (JACK_DET -> SPK_SHDN),\n"
        "no por hardware. Es deliberado: permite politicas como oir el parlante con los\n"
        "auriculares puestos, que un corte mecanico prohibe.",
}


def emit_lib_symbol(name, d, prefixed=True):
    w, h = d["w"], d["h"]
    sym_name = f"{PROJECT}:{name}" if prefixed else name
    out = [f'    (symbol "{sym_name}"',
           '      (exclude_from_sim no) (in_bom yes) (on_board yes)',
           f'      (property "Reference" "{d["ref"]}" (at 0 {F(h + 2.54)} 0) {EFFECTS})',
           f'      (property "Value" "{name}" (at 0 {F(-(h + 2.54))} 0) {EFFECTS})',
           f'      (property "Footprint" "" (at 0 0 0) {EFFECTS_H})',
           f'      (property "Datasheet" "{d["ds"]}" (at 0 0 0) {EFFECTS_H})',
           f'      (property "Description" "{d["desc"]}" (at 0 0 0) {EFFECTS_H})',
           f'      (symbol "{name}_0_1"',
           f'        (rectangle (start {F(-w)} {F(h)}) (end {F(w)} {F(-h)})'
           ' (stroke (width 0.254) (type default)) (fill (type background)))',
           '      )',
           f'      (symbol "{name}_1_1"']
    for num, pname, px, py, ang in d["pins"]:
        out += [f'        (pin passive line (at {F(px)} {F(py)} {ang}) (length 2.54)',
                f'          (name "{pname}" {EFFECTS})',
                f'          (number "{num}" {EFFECTS})',
                '        )']
    out += ['      )', '    )']
    return "\n".join(out)


def emit_instance(lib, ref, value, x, y, nets, props, hoja_uuid):
    d = SYMS[lib]
    h = d["h"]
    props = dict(props)
    fp = props.pop("FP", "")
    out = ['  (symbol',
           f'    (lib_id "{PROJECT}:{lib}")',
           f'    (at {F(x)} {F(y)} 0)',
           '    (unit 1)',
           '    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)',
           f'    (uuid "{u()}")',
           f'    (property "Reference" "{ref}" (at {F(x)} {F(y - h - 3.81)} 0) {EFFECTS})',
           f'    (property "Value" "{value}" (at {F(x)} {F(y + h + 3.81)} 0) {EFFECTS})',
           f'    (property "Footprint" "{fp}" (at {F(x)} {F(y)} 0) {EFFECTS_H})',
           f'    (property "Datasheet" "{d["ds"]}" (at {F(x)} {F(y)} 0) {EFFECTS_H})',
           f'    (property "Description" "{d["desc"]}" (at {F(x)} {F(y)} 0) {EFFECTS_H})']
    for k, v in props.items():
        out.append(f'    (property "{k}" "{v}" (at {F(x)} {F(y)} 0) {EFFECTS_H})')
    for num, _, _, _, _ in d["pins"]:
        out.append(f'    (pin "{num}" (uuid "{u()}"))')
    out += ['    (instances',
            f'      (project "{PROJECT}"',
            f'        (path "/{ROOT_UUID}/{hoja_uuid}" (reference "{ref}") (unit 1))',
            '      )',
            '    )',
            '  )']
    return "\n".join(out)


def emit_labels_and_ncs(lib, x, y, nets):
    """Una global label por pin conectado, un no_connect por pin NC.

    El pin declara su punto de conexion en (px, py) y el cuerpo queda del otro
    lado, asi que la etiqueta va exactamente ahi. Los NC explicitos son lo que
    evita que el ERC reporte cada pin sin usar como error."""
    d = SYMS[lib]
    out = []
    for num, _, px, py, ang in d["pins"]:
        sx, sy = x + px, y - py
        net = nets[num]
        if net == NC:
            out.append(f'  (no_connect (at {F(sx)} {F(sy)}) (uuid "{u()}"))')
            continue
        lang, just = (180, "right") if ang == 0 else (0, "left")
        out += [f'  (global_label "{net}" (shape passive) (at {F(sx)} {F(sy)} {lang})',
                f'    (effects (font (size 1.27 1.27)) (justify {just}))',
                f'    (uuid "{u()}")',
                f'    (property "Intersheetrefs" "${{INTERSHEET_REFS}}" '
                f'(at {F(sx)} {F(sy)} 0) {EFFECTS_H})',
                '  )']
    return "\n".join(out)


def _emit_nota(x, y, txt):
    esc = txt.replace("\n", "\\n")
    return "\n".join([
        f'  (text "{esc}" (exclude_from_sim no) (at {F(x)} {F(y)} 0)',
        '    (effects (font (size 1.27 1.27)) (justify left top))',
        f'    (uuid "{u()}")',
        '  )'])


def build_hoja(idx, nombre, titulo, refs, claves_nota):
    """Una hoja hija: sus componentes, sus global labels y sus notas."""
    porRef = {i[1]: i for i in INSTANCES}
    instancias = [porRef[r] for r in refs]
    colocadas, w, h = _layout_hoja(instancias)
    verificar_colisiones(colocadas)
    huuid = uuid_hoja(idx)

    parts = ['(kicad_sch',
             '  (version 20250114)',
             '  (generator "eeschema")',
             '  (generator_version "9.0")',
             f'  (uuid "{huuid}")',
             f'  (paper "{_papel(w, h + 90.0)}")',
             '  (title_block',
             f'    (title "{titulo}")',
             f'    (date "{FECHA}")',
             '    (rev "A")',
             f'    (comment 1 "pikocore_gamepad - hoja {idx + 2} de {len(HOJAS) + 1}")',
             '    (comment 2 "Todas las conexiones son por GLOBAL LABEL: valen en todas las hojas")',
             '  )',
             '  (lib_symbols']
    # Solo los simbolos que ESTA hoja usa: abrir una hoja del jack no tiene
    # por que cargar la biblioteca entera.
    for name in sorted({i[0] for i in colocadas}):
        parts.append(emit_lib_symbol(name, SYMS[name]))
    parts.append('  )')
    for lib, ref, value, x, y, nets, props in colocadas:
        parts.append(emit_instance(lib, ref, value, x, y, nets, props, huuid))
    for lib, ref, value, x, y, nets, props in colocadas:
        parts.append(emit_labels_and_ncs(lib, x, y, nets))
    ny = h + 8.0
    for clave in claves_nota:
        parts.append(_emit_nota(MARGEN, ny, NOTAS[clave]))
        ny += 6.0 + 1.9 * (NOTAS[clave].count("\n") + 1)
    parts += ['  (embedded_fonts no)', ')']
    return "\n".join(parts) + "\n"


def build_root():
    """Hoja raiz: los simbolos de hoja y la nota general.

    NO lleva ninguna senal. Con conexiones por global label no hacen falta
    pines de hoja, asi que la raiz es puro indice — y eso es deliberado: un
    indice sin cableado no puede contradecir a las hojas hijas.
    """
    parts = ['(kicad_sch',
             '  (version 20250114)',
             '  (generator "eeschema")',
             '  (generator_version "9.0")',
             f'  (uuid "{ROOT_UUID}")',
             '  (paper "A3")',
             '  (title_block',
             '    (title "pikocore_gamepad - indice")',
             f'    (date "{FECHA}")',
             '    (rev "A")',
             '    (comment 1 "MCU: Waveshare RP2350-Plus 16MB en socket | LiPo al PH1.25 del modulo")',
             '    (comment 2 "Pinout: pinmap.py, verificado contra el firmware por la puerta G-4")',
             '  )',
             '  (lib_symbols',
             '  )']
    y = 25.0
    for i, (nombre, titulo, refs, _n) in enumerate(HOJAS):
        parts += [f'  (sheet (at {F(30.0)} {F(y)}) (size {F(165.0)} {F(17.78)})',
                  '    (stroke (width 0.1524) (type solid))',
                  '    (fill (color 0 0 0 0.0))',
                  f'    (uuid "{uuid_hoja(i)}")',
                  f'    (property "Sheetname" "{titulo}" (at {F(30.0)} {F(y - 1.27)} 0)',
                  '      (effects (font (size 1.27 1.27)) (justify left bottom))',
                  '    )',
                  f'    (property "Sheetfile" "{nombre}.kicad_sch" '
                  f'(at {F(30.0)} {F(y + 19.05)} 0)',
                  '      (effects (font (size 1.27 1.27)) (justify left top))',
                  '    )',
                  '    (instances',
                  f'      (project "{PROJECT}"',
                  f'        (path "/{ROOT_UUID}" (page "{i + 2}"))',
                  '      )',
                  '    )',
                  '  )',
                  f'  (text "{len(refs)} componentes" (exclude_from_sim no) '
                  f'(at {F(205.0)} {F(y + 6.0)} 0)',
                  '    (effects (font (size 1.27 1.27)) (justify left top))',
                  f'    (uuid "{u()}")',
                  '  )']
        y += 30.0
    parts.append(_emit_nota(30.0, y + 6.0, NOTAS["NOTA_RAIZ"]))
    parts += ['  (sheet_instances',
              '    (path "/" (page "1"))',
              '  )',
              '  (embedded_fonts no)',
              ')']
    return "\n".join(parts) + "\n"


def build_lib():
    parts = ['(kicad_symbol_lib',
             '  (version 20241209)',
             '  (generator "kicad_symbol_editor")',
             '  (generator_version "9.0")']
    for name, d in SYMS.items():
        parts.append(emit_lib_symbol(name, d, prefixed=False))
    parts.append(')')
    return "\n".join(parts) + "\n"


def build_pro():
    return json.dumps({
        "board": {
            "3dviewports": [],
            "design_settings": {
                # Un solo radio termico alcanza para las corrientes de este
                # diseno; decision consciente, no descuido.
                "rule_severities": {"starved_thermal": "warning"},
            },
            "layer_presets": [], "viewports": [],
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 3},
        "net_settings": {
            "classes": [{
                "name": "Default",
                "clearance": 0.2, "track_width": 0.25,
                "via_diameter": 0.6, "via_drill": 0.3,
                "uvia_diameter": 0.3, "uvia_drill": 0.1,
                "diff_pair_width": 0.2, "diff_pair_gap": 0.25,
                "diff_pair_via_gap": 0.25,
                "wire_width": 6, "bus_width": 12, "line_style": 0,
                "pcb_color": "rgba(0, 0, 0, 0.000)",
                "schematic_color": "rgba(0, 0, 0, 0.000)",
            }],
            "meta": {"version": 4},
        },
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "project": {"files": []},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": ([[ROOT_UUID, "Root"]]
                   + [[uuid_hoja(i), t] for i, (_n, t, _r, _x)
                      in enumerate(HOJAS)]),
        "text_variables": {},
    }, indent=2)


def main():
    verificar_reparto()
    outputs = {f"{PROJECT}.kicad_sch": build_root()}
    for i, (nombre, titulo, refs, notas) in enumerate(HOJAS):
        outputs[f"{nombre}.kicad_sch"] = build_hoja(i, nombre, titulo, refs,
                                                    notas)
    outputs[f"{PROJECT}.kicad_sym"] = build_lib()
    outputs[f"{PROJECT}.kicad_pro"] = build_pro()
    preservar = {f"{PROJECT}.kicad_pro"}
    for fname, content in outputs.items():
        path = os.path.join(HERE, fname)
        if fname in preservar and os.path.exists(path):
            print(f"SKIP -> {path} (ya existe; se preservan los ajustes de KiCad)")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"OK   -> {path}")
    print()
    print(f"{len(SYMS)} simbolos, {len(INSTANCES)} instancias "
          f"repartidas en {len(HOJAS)} hojas + indice:")
    for i, (nombre, titulo, refs, _n) in enumerate(HOJAS):
        print(f"   {i + 2}. {titulo:<44} {len(refs):>2} componentes")


if __name__ == "__main__":
    main()
