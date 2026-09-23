#!/usr/bin/env python3
"""Lee el DXF modificado en Rhino y REESCRIBE placements.py.

Esta es la mejora sobre V1, donde el script solo imprimia un diff que habia
que transcribir a mano a la tabla PLACEMENTS. Ademas lee BOARD_OUTLINE, asi
que el usuario puede cambiar el tamano de la placa y no solo mover
componentes.

Tres cosas que hace y conviene tener presentes:

1. Actualiza las coordenadas de los componentes que ya estan en la tabla.
2. AGREGA los que estan en el DXF pero no en la tabla. Son los ~58 pasivos,
   que gen_pcb.py coloca en grilla automatica: en cuanto el usuario los mueve
   en Rhino, pasan a tener posicion propia y la grilla deja de aplicarles.
3. Si el contorno cambio, actualiza BOARD_W/BOARD_H en params.py y los marca
   verificados: definir el contorno en Rhino ES el cierre de la tarea V-0.

LIMITACION: la ROTACION no viaja por el DXF —una cruz no tiene orientacion—
asi que girar algo en Rhino no tiene efecto. Se edita a mano en placements.py.
Los componentes que se agregan por (2) entran con rotacion 0 y al dorso, que
es lo que hace la grilla automatica.

No necesita pcbnew: trabaja sobre placements.py, params.py y el DXF, todo
texto.

Uso:
  python parse_dxf.py gamesetup_template_MOD.dxf            # solo muestra
  python parse_dxf.py gamesetup_template_MOD.dxf --write    # aplica
"""
import os
import re
import sys

import dxf_io
import netlist
from placements import PLACEMENTS

HERE = os.path.dirname(os.path.abspath(__file__))
PLACEMENTS_PY = os.path.join(HERE, "placements.py")
PARAMS_PY = os.path.join(HERE, "params.py")
TOL = 0.05   # mm: por debajo de esto se considera que no se movio


def footprint_de(ref):
    """Footprint declarado en netlist.py para una referencia."""
    for inst in netlist.INSTANCES:
        if inst[1] == ref:
            return inst[6].get("FP", "")
    return ""


def aplicar_posiciones(src, posiciones):
    """Reescribe las coordenadas de las filas que ya existen en la tabla."""
    for ref, (x, y) in posiciones.items():
        pat = re.compile(
            r'(\(\s*"' + re.escape(ref) + r'"\s*,\s*"[^"]+"\s*,\s*)'
            r'(-?[\d.]+)(\s*,\s*)(-?[\d.]+)')
        src, n = pat.subn(
            lambda m: f"{m.group(1)}{x:>6.2f}{m.group(3)}{y:>6.2f}",
            src, count=1)
        if n == 0:
            print(f"  AVISO: {ref} esta en el DXF pero no se pudo reescribir")
    return src


def agregar_filas(src, nuevos):
    """Agrega al final de PLACEMENTS los componentes que no estaban.

    Entran con rotacion 0 y al dorso, que es exactamente lo que hacia la
    grilla automatica de gen_pcb.py para ellos.
    """
    if not nuevos:
        return src
    filas = ["\n    # --- agregados por parse_dxf.py desde el DXF del usuario ---\n"]
    for ref, (x, y) in sorted(nuevos.items()):
        fp = footprint_de(ref)
        filas.append(f'    ("{ref}", "{fp}", {x:>6.2f}, {y:>6.2f}, 0, True),\n')
    # Se insertan antes del corchete de cierre de la lista, que es la ultima
    # linea del archivo que consiste solo en "]".
    return re.sub(r"\n\]\s*$", "\n" + "".join(filas) + "]\n", src)


def aplicar_contorno(src_params, outline, cambios):
    """Actualiza BOARD_W/BOARD_H en params.py y los marca verificados.

    Que el usuario REDIBUJE el contorno en Rhino es el cierre de V-0: deja de
    ser un valor de partida y pasa a ser el contorno real de la placa.

    Solo se tocan los que efectivamente cambiaron. Marcar verificado un valor
    que nadie movio seria una verificacion falsa — exactamente lo que la
    puerta G-0 existe para impedir — y bastaria un round-trip del template sin
    editar para cerrar V-0 sin que nadie haya decidido nada.
    """
    w = outline[2] - outline[0]
    h = outline[3] - outline[1]
    nota = ("Contorno definitivo, tomado de la capa BOARD_OUTLINE del DXF que "
            "el usuario ordeno en Rhino.")
    for nombre, valor in cambios:
        # La nota puede estar partida en VARIAS cadenas adyacentes (Python las
        # concatena solo). Hay que consumirlas todas hasta la coma que precede
        # al id de la tarea: reemplazar solo la primera deja pegados los restos
        # de la nota vieja, y el archivo sigue siendo Python valido, asi que el
        # destrozo pasa desapercibido.
        pat = re.compile(
            r'("' + nombre + r'":\s*Param\(\s*)'
            r'[\d.]+\s*,\s*(?:True|False)\s*,\s*'
            r'(?:"[^"]*"\s*)+'
            r',',
            re.S)
        src_params, n = pat.subn(
            lambda m: f'{m.group(1)}{valor:.2f}, True,\n        "{nota}",',
            src_params, count=1)
        if n == 0:
            print(f"  AVISO: no se pudo reescribir {nombre} en params.py")
    return src_params, w, h


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    dxf_path = sys.argv[1]
    write = "--write" in sys.argv

    if not os.path.isfile(dxf_path):
        print(f"FALTA: {dxf_path}")
        return 1

    with open(dxf_path, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    posiciones = dxf_io.read_positions(txt)
    outline = dxf_io.read_outline(txt)

    actual = {p[0]: (p[2], p[3]) for p in PLACEMENTS}
    movidos, nuevos, sin_cambio = {}, {}, 0
    for ref, (x, y) in sorted(posiciones.items()):
        if ref not in actual:
            nuevos[ref] = (x, y)
        elif abs(x - actual[ref][0]) > TOL or abs(y - actual[ref][1]) > TOL:
            movidos[ref] = (x, y)
        else:
            sin_cambio += 1

    if movidos:
        print(f"{'Ref':<6} {'antes X':>9} {'antes Y':>9} "
              f"{'ahora X':>9} {'ahora Y':>9}")
        print("-" * 48)
        for ref, (x, y) in movidos.items():
            ax, ay = actual[ref]
            print(f"{ref:<6} {ax:>9.2f} {ay:>9.2f} {x:>9.2f} {y:>9.2f}")
        print()

    print(f"{len(movidos)} movidos, {sin_cambio} sin cambio, "
          f"{len(nuevos)} nuevos en la tabla")
    if nuevos:
        print(f"  se agregan: {', '.join(sorted(nuevos))}")

    faltan = sorted(set(actual) - set(posiciones))
    if faltan:
        print(f"AVISO: sin cruz en el DXF (se conservan): {', '.join(faltan)}")

    w, h = outline[2] - outline[0], outline[3] - outline[1]
    print(f"contorno del DXF: {w:.2f} x {h:.2f} mm")

    if not write:
        print("\n(dry run — agregar --write para aplicar)")
        return 0

    with open(PLACEMENTS_PY, encoding="utf-8") as f:
        src = f.read()
    src = aplicar_posiciones(src, movidos)
    src = agregar_filas(src, nuevos)
    with open(PLACEMENTS_PY, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"\nESCRITO: {PLACEMENTS_PY} "
          f"({len(movidos)} movidos, {len(nuevos)} agregados)")

    import params
    cambios = [(n, v) for n, v in (("BOARD_W", w), ("BOARD_H", h))
               if abs(v - params.v(n)) > TOL]
    if cambios:
        with open(PARAMS_PY, encoding="utf-8") as f:
            srcp = f.read()
        srcp, w, h = aplicar_contorno(srcp, outline, cambios)
        with open(PARAMS_PY, "w", encoding="utf-8") as f:
            f.write(srcp)
        print(f"ESCRITO: {PARAMS_PY} — contorno {w:.2f} x {h:.2f}, "
              f"{', '.join(n for n, _ in cambios)} pasan a verificados (V-0)")
    else:
        print(f"{PARAMS_PY} sin cambios: el contorno es el mismo, asi que "
              f"BOARD_W/BOARD_H siguen SIN verificar (nadie los redibujo)")

    print("\nRegenerar la placa:  \"$KIPY\" gen_pcb.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
