#!/usr/bin/env python3
"""Revisa el placement antes de rutear: solapamientos y piezas fuera de placa.

No reemplaza al DRC — lo precede. El DRC necesita la placa ruteada y tarda;
esto corre en un segundo sobre el board recien generado y dice si el layout
es viable, que es lo que hace falta mientras se itera con el DXF de Rhino.

Compara PAD CONTRA PAD, no bounding box contra bounding box. La diferencia
importa: la bbox del modulo LCD abarca sus 27.78 x 39.22 enteros porque tiene
cuatro agujeros en las esquinas, pero su interior no tiene ni un poco de
cobre — y es justamente ahi donde conviene poner componentes del dorso. Con
comparacion por bbox, cada pieza colocada bajo el display aparece como choque.

Un par de pads se considera conflictivo si comparten capa de cobre, o si
alguno de los dos es pasante: un THT perfora las cuatro capas.

No mira courtyards: dos piezas cuyos courtyards se rozan suelen ser
aceptables, y aca lo que interesa es el cobre encimado.

Correr con el python de KiCad:
  "$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" checks/check_placement.py
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.dirname(HERE)
sys.path.insert(0, PCB_DIR)
PCB = os.path.join(PCB_DIR, "gamesetup.kicad_pcb")

MARGEN_BORDE = 1.0    # mm minimos entre cobre y borde de placa


def pads_de(fp):
    """[(ref.num, caja, pasante, cara)] de cada pad, en mm."""
    t = pcbnew.ToMM
    out = []
    for p in fp.Pads():
        b = p.GetBoundingBox()
        pasante = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,
                                       pcbnew.PAD_ATTRIB_NPTH)
        out.append((f"{fp.GetReference()}.{p.GetNumber() or '-'}",
                    (t(b.GetLeft()), t(b.GetTop()),
                     t(b.GetRight()), t(b.GetBottom())),
                    pasante, fp.IsFlipped()))
    return out


def footprint_bbox(fp):
    cajas = [c for _, c, _, _ in pads_de(fp)]
    if not cajas:
        return None
    return (min(c[0] for c in cajas), min(c[1] for c in cajas),
            max(c[2] for c in cajas), max(c[3] for c in cajas))


def solapan(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def main():
    if not os.path.isfile(PCB):
        print(f"FALTA: {PCB}")
        return 1
    board = pcbnew.LoadBoard(PCB)
    bb = board.GetBoardEdgesBoundingBox()
    anchos = [d.GetWidth() for d in board.GetDrawings()
              if d.GetLayer() == pcbnew.Edge_Cuts]
    bb.Inflate(-(max(anchos) if anchos else 0) // 2)
    bx0, by0 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
    bx1, by1 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())

    piezas, pads = [], []
    for fp in board.GetFootprints():
        caja = footprint_bbox(fp)
        if caja is None:
            continue
        piezas.append((fp.GetReference(), caja))
        pads.extend(pads_de(fp))
    piezas.sort()

    fuera = []
    for ref, c in piezas:
        if (c[0] < bx0 + MARGEN_BORDE or c[1] < by0 + MARGEN_BORDE or
                c[2] > bx1 - MARGEN_BORDE or c[3] > by1 - MARGEN_BORDE):
            fuera.append((ref, c))

    choques = []
    for i, (na, ca, pa, fa) in enumerate(pads):
        refa = na.split(".")[0]
        for nb, cb, pb, fb in pads[i + 1:]:
            if nb.split(".")[0] == refa:
                continue                      # pads del mismo componente
            if not solapan(ca, cb):
                continue
            if fa != fb and not (pa or pb):
                continue                      # caras opuestas, todo SMD
            cara = "misma cara" if fa == fb else "caras opuestas, hay pasante"
            choques.append((na, nb, cara))

    print(f"{len(piezas)} piezas, {len(pads)} pads. "
          f"Placa {bx1 - bx0:.2f} x {by1 - by0:.2f} mm.\n")

    if fuera:
        print(f"FUERA DE PLACA o a menos de {MARGEN_BORDE}mm del borde ({len(fuera)}):")
        for ref, c in fuera:
            print(f"  {ref:<5}  x {c[0]:7.2f}..{c[2]:7.2f}   y {c[1]:7.2f}..{c[3]:7.2f}")
        print()
    if choques:
        print(f"PADS SOLAPADOS ({len(choques)}):")
        for na, nb, cara in choques[:20]:
            print(f"  {na:<8} vs {nb:<8}  ({cara})")
        if len(choques) > 20:
            print(f"  ... y {len(choques) - 20} mas")
        print()

    if not fuera and not choques:
        print("OK: sin solapamientos de pads y todo dentro de la placa.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
