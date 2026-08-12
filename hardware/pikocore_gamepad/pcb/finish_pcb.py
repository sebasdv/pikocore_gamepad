#!/usr/bin/env python3
"""Post-proceso del board ya ruteado: relleno final de zonas.

Correr con el python de KiCad, despues de route_io.py import.

POR QUE NO HAY VIAS DE STITCHING, que es lo que hacia este script en V1:

En V1 tenian sentido porque los planos GND estaban en las capas EXTERNAS y
quedaban fragmentados por los taladros THT; las vias los cosian entre si.

Aca la arquitectura es otra: GND es un plano macizo en In1.Cu y NO hay vertido
de GND en F.Cu ni en B.Cu. Una via de stitching, entonces, no conecta nada —
toca el plano interno y nada mas. Se probo: de 24 vias agregadas, el DRC
reporto 21 como via_dangling, y ademas produjeron 2 cortocircuitos (GND contra
BTN_A y BTN_Y) y 5 violaciones de margen, porque la deteccion de obstaculos
aproximaba cada pista por tres puntos y una via puede caer entre ellos.

Cada pad de GND llega al plano por su propia via, puesta por freerouting. Eso
es lo que corresponde y es suficiente.

MANTENER SIMPLE. En V1 la tentacion fue agregar maquinaria para coser islas de
GND, y no funciona: ZONE_FILLER().Fill() via scripting no elimina islas y
kicad-cli pcb drc re-rellena las zonas ignorando cualquier edicion del relleno.
Si el DRC marca GND sin conectar, la respuesta es re-rutear, no "arreglar" el
relleno.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "pikocore_gamepad.kicad_pcb")


def main():
    if not os.path.isfile(PCB):
        print(f"FALTA: {PCB}")
        return 1
    board = pcbnew.LoadBoard(PCB)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)

    pistas = len([t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"])
    vias = len([t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"])
    zonas = len([z for z in board.Zones() if not z.GetIsRuleArea()])
    print(f"zonas rellenadas: {zonas}")
    print(f"guardado: {PCB}  ({pistas} pistas, {vias} vias)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
