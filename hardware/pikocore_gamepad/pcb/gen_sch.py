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


# Los pasivos de 2 pines se re-acomodan en una grilla propia. Las coordenadas
# que traen en netlist.py son indicativas —agrupan por subsistema— pero no
# respetan el ancho del simbolo: una resistencia mide 10.16mm entre pines, asi
# que dos a 10mm de distancia SE TOCAN. Eso no es un problema visual: fusiona
# las dos nets en una sola, y el resultado es un cortocircuito que el ERC
# reporta como un simple aviso de "multiple net names".
PASIVOS = ("R", "C", "CP", "L", "D")
GRILLA_X0, GRILLA_Y0 = 340.0, 30.0
GRILLA_DX, GRILLA_DY = 30.48, 20.32
GRILLA_FILAS = 16


def _layout(instances):
    """Posiciones finales: los pasivos van a su grilla, el resto queda donde
    lo puso netlist.py."""
    out, n = [], 0
    for (sym, ref, val, x, y, nets, props) in instances:
        if sym in PASIVOS:
            x = GRILLA_X0 + (n // GRILLA_FILAS) * GRILLA_DX
            y = GRILLA_Y0 + (n % GRILLA_FILAS) * GRILLA_DY
            n += 1
        out.append((sym, ref, val, _snap(x), _snap(y), nets, props))
    return out


def verificar_colisiones(instances):
    """Ningun punto puede tener dos pines de nets distintas.

    Dos pines que coinciden quedan electricamente unidos, asi que sus nets se
    fusionan. KiCad no lo llama error —solo avisa "multiple net names"— pero
    es un cortocircuito, y la netlist que sale hacia la PCB ya viene mal.
    """
    from collections import defaultdict
    puntos = defaultdict(list)
    for sym, ref, val, x, y, nets, props in instances:
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


PLACED = _layout(INSTANCES)
verificar_colisiones(PLACED)

NOTES = [
    (20.32, 300.0,
     "GAMESETUP V2 - PCB panel unico, 4 capas. MCU Waveshare RP2350-Plus 16MB en socket 2x20.\n"
     "La bateria LiPo va al PH1.25 del propio modulo (cargador ETA6096 a bordo): la placa no\n"
     "lleva circuito de carga. SW15 apaga el rail 3V3 del modulo via 3V3_EN, que tiene\n"
     "pull-up interno de 100K a VSYS."),
    (20.32, 315.0,
     "ENTRADA: los 22 contactos de switch (12 tacts + 2 nav de 5 vias) NO entran en los 26\n"
     "GPIO que expone el modulo, asi que van por 3 expansores PCF8574 en I2C1 (0x20/0x21/0x22).\n"
     "Cada nav queda ENTERO en un solo chip: repartido entre dos, dos lecturas distintas\n"
     "podrian mostrar una diagonal que el usuario nunca hizo. Los 3 /INT van en wired-OR a GP4."),
    (20.32, 335.0,
     "AUDIO: DAC PCM5102A (U5) chip-down, I2S por PIO. SCK (pin 12) a GND = PLL interno desde\n"
     "BCK, no hace falta MCLK. FMT/FLT/DEMP a GND. XSMT con pulldown de 100k: el DAC arranca\n"
     "MUTEADO y el firmware lo libera (anti-pop).\n"
     "La salida del DAC esta centrada en MASA (charge pump, +-2.8V / 2.0 Vrms), por eso el\n"
     "buffer U3 es INVERSOR con ganancia 0.5 y entrada acoplada: 2.0 Vrms no entran en un\n"
     "riel de 5V con masa virtual a 2.5V.\n"
     "El riel de 5V lo genera el boost U2 (TPS61023) y alimenta SOLO al op-amp: el riel\n"
     "analogico tiene que ser FIJO y no seguir a la bateria. El class-D U4 cuelga de VSYS\n"
     "directo, porque a todo volumen pide cientos de mA."),
    (20.32, 360.0,
     "VERIFICAR ANTES DE FABRICAR (correr checks/check_verified.py):\n"
     "- Cotas del modulo LCD que el drawing no acota: vertical de la fila de pines, y el\n"
     "  offset de los agujeros (la cota dice 2.19 y la nota china 2.5).\n"
     "- Pinout de TPS61023, H11L1, los dos jacks TRS, el jack de audio y el socket microSD:\n"
     "  ninguno viene verificado de V1 y sus simbolos lo dicen.\n"
     "- Valores del lazo del boost (inductor y divisor de realimentacion).\n"
     "Los pinouts de PCM5102A, NJM4556AD, PAM8302A y el nav WS-1004 SI vienen verificados\n"
     "de V1, donde llegaron a una placa ruteada con DRC limpio."),
]


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


def emit_instance(lib, ref, value, x, y, nets, props):
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
            f'        (path "/{ROOT_UUID}" (reference "{ref}") (unit 1))',
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


def build_sch():
    parts = ['(kicad_sch',
             '  (version 20250114)',
             '  (generator "eeschema")',
             '  (generator_version "9.0")',
             f'  (uuid "{ROOT_UUID}")',
             '  (paper "A2")',
             '  (title_block',
             '    (title "GAMESETUP V2 - panel principal")',
             '    (date "2026-07-31")',
             '    (rev "A")',
             '    (comment 1 "MCU: Waveshare RP2350-Plus 16MB en socket | LiPo al PH1.25 del modulo")',
             '    (comment 2 "Pinout: GAMESETUP/pcb/pinmap.py, verificado contra boards/rp2350plus_v2/config.h")',
             '  )',
             '  (lib_symbols']
    for name, d in SYMS.items():
        parts.append(emit_lib_symbol(name, d))
    parts.append('  )')
    for lib, ref, value, x, y, nets, props in PLACED:
        parts.append(emit_instance(lib, ref, value, x, y, nets, props))
    for lib, ref, value, x, y, nets, props in PLACED:
        parts.append(emit_labels_and_ncs(lib, x, y, nets))
    for tx, ty, txt in NOTES:
        esc = txt.replace("\n", "\\n")
        parts += [f'  (text "{esc}" (exclude_from_sim no) (at {F(tx)} {F(ty)} 0)',
                  '    (effects (font (size 1.27 1.27)) (justify left bottom))',
                  f'    (uuid "{u()}")',
                  '  )']
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
        "sheets": [[ROOT_UUID, "Root"]],
        "text_variables": {},
    }, indent=2)


def main():
    outputs = {
        f"{PROJECT}.kicad_sch": build_sch(),
        f"{PROJECT}.kicad_sym": build_lib(),
        f"{PROJECT}.kicad_pro": build_pro(),
    }
    preservar = {f"{PROJECT}.kicad_pro"}
    for fname, content in outputs.items():
        path = os.path.join(HERE, fname)
        if fname in preservar and os.path.exists(path):
            print(f"SKIP -> {path} (ya existe; se preservan los ajustes de KiCad)")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"OK   -> {path}")
    print(f"\n{len(SYMS)} simbolos, {len(PLACED)} instancias.")


if __name__ == "__main__":
    main()
