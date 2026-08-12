#!/usr/bin/env python3
"""Export DSN / import SES para freerouting. Correr con el python de KiCad.

  "$KIPY" route_io.py export   -> pikocore_gamepad.dsn
  "$KIPY" route_io.py import   -> aplica pikocore_gamepad.ses, rellena zonas, guarda

DIFERENCIA CON V1: alli habia que QUITAR las zonas GND antes de exportar, para
que freerouting ruteara GND como pistas. Eso era un parche a la fragmentacion
del plano en 2 capas: con tanto THT el plano quedaba partido en islas y no
habia forma de garantizar conectividad de tierra por relleno.

Con 4 capas In1.Cu es un plano GND continuo, asi que las zonas se CONSERVAN en
el export y freerouting solo tiene que rutear las senales, conectando cada pad
GND al plano por via.

PITFALL heredado de V1: NO pasar este script ni kicad-cli por "2>&1 | grep".
El assert de "non-closed outline" mas el memory-leak de SWIG salen por stderr
y hacen deadlock del pipe — parece colgado. Redirigir a un log y grepear el
archivo.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "pikocore_gamepad.kicad_pcb")
DSN = os.path.join(HERE, "pikocore_gamepad.dsn")
SES = os.path.join(HERE, "pikocore_gamepad.ses")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("export", "import"):
        print(__doc__)
        return 2

    board = pcbnew.LoadBoard(PCB)

    if sys.argv[1] == "export":
        ok = pcbnew.ExportSpecctraDSN(board, DSN)
        zonas = len([z for z in board.Zones() if not z.GetIsRuleArea()])
        print(f"DSN export: {ok} -> {DSN}")
        print(f"{zonas} zonas conservadas (4 capas: el plano GND no se toca)")
        return 0 if ok else 1

    if not os.path.isfile(SES):
        print(f"FALTA: {SES} (correr freerouting primero)")
        return 1
    try:
        ok = pcbnew.ImportSpecctraSES(board, SES)
    except TypeError:
        ok = pcbnew.ImportSpecctraSES(SES)
    print("SES import:", ok)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    pistas = len([t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"])
    vias = len([t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"])
    print(f"guardado: {PCB}  ({pistas} pistas, {vias} vias)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
