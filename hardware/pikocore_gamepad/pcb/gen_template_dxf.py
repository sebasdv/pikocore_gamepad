#!/usr/bin/env python3
"""Escribe gamesetup_template.dxf leyendo el board REAL.

Correr con el python de KiCad 9:
  "$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" gen_template_dxf.py

Es una cascara fina: extrae origenes y bboxes del board y delega el formato a
dxf_io.py, que se testea aparte sin levantar KiCad.

Que sale en el DXF, una capa por refdes:
  - cruz (+) en el ORIGEN del footprint = la posicion de placements.py.
    Mover la cruz = nueva posicion. Es lo unico que hay que mover.
  - rectangulo punteado con la extension real de los pads, para ver cuanto
    ocupa de verdad cada pieza.
  - capa BOARD_OUTLINE con el contorno. Moverla cambia el tamano de la placa.

El bbox sale del board, no de datos hardcodeados, asi que siempre refleja los
footprints vigentes.

LIMITACION: la ROTACION no viaja por el DXF. Una cruz no tiene orientacion,
asi que girar algo en Rhino no tiene efecto. La rotacion se edita a mano en
placements.py.

Flujo:
  1. "$KIPY" gen_template_dxf.py
  2. abrir gamesetup_template.dxf en Rhino (unidades mm)
  3. mover las cruces y, si hace falta, el contorno
  4. guardar como gamesetup_template_MOD.dxf
  5. python parse_dxf.py gamesetup_template_MOD.dxf --write
"""
import os

import pcbnew

import dxf_io

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "gamesetup.kicad_pcb")
OUT = os.path.join(HERE, "gamesetup_template.dxf")


def to_mm(v):
    return pcbnew.ToMM(v)


def pad_bbox_mm(fp):
    """BBox de los pads en mm.

    Se computa a mano acumulando: BOX2I.Merge no acumula bien a traves de
    SWIG y devuelve cajas incorrectas. Si el footprint no tiene pads (un
    testpoint mecanico, por ejemplo), cae al bbox general.
    """
    xs0, ys0, xs1, ys1 = [], [], [], []
    for p in fp.Pads():
        b = p.GetBoundingBox()
        xs0.append(b.GetLeft()); ys0.append(b.GetTop())
        xs1.append(b.GetRight()); ys1.append(b.GetBottom())
    if not xs0:
        b = fp.GetBoundingBox()
        return (to_mm(b.GetLeft()), to_mm(b.GetTop()),
                to_mm(b.GetRight()), to_mm(b.GetBottom()))
    return (to_mm(min(xs0)), to_mm(min(ys0)),
            to_mm(max(xs1)), to_mm(max(ys1)))


def contorno_geometrico(board):
    """(x0, y0, x1, y1) del contorno SIN el ancho de linea del Edge.Cuts.

    GetBoardEdgesBoundingBox() incluye el ancho del trazo: una placa dibujada
    de 0 a 90 con linea de 0.1 mide 90.10 en la bbox. Escribir ese numero
    como BOARD_W hace que la placa crezca 0.1mm en CADA ciclo de Rhino, y la
    deriva es silenciosa porque cada paso parece correcto.
    """
    bb = board.GetBoardEdgesBoundingBox()
    anchos = [d.GetWidth() for d in board.GetDrawings()
              if d.GetLayer() == pcbnew.Edge_Cuts]
    w = max(anchos) if anchos else 0
    bb.Inflate(-w // 2)
    return (to_mm(bb.GetLeft()), to_mm(bb.GetTop()),
            to_mm(bb.GetRight()), to_mm(bb.GetBottom()))


def main():
    board = pcbnew.LoadBoard(PCB)
    outline = contorno_geometrico(board)

    items = []
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        pos = fp.GetPosition()
        items.append(dxf_io.Item(
            ref=fp.GetReference(),
            x=to_mm(pos.x), y=to_mm(pos.y),
            bbox=pad_bbox_mm(fp),
            back=fp.IsFlipped(),
        ))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(dxf_io.build_document(outline, items))

    dorso = sum(1 for i in items if i.back)
    print(f"OK -> {OUT}")
    print(f"{len(items)} componentes leidos del board real "
          f"({len(items) - dorso} al frente, {dorso} al dorso)")
    print(f"contorno: {outline[2] - outline[0]:.2f} x "
          f"{outline[3] - outline[1]:.2f} mm")


if __name__ == "__main__":
    main()
