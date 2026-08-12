#!/usr/bin/env python3
"""G-2: el netlist del esquematico y el de la PCB son identicos.

Compara pares (referencia, pin) -> net entre gamesetup.net (exportado del
esquematico) y gamesetup.kicad_pcb. Una divergencia significa que la placa
esta cableada distinto del esquematico, y no la detecta ni el ERC —que solo
mira el esquematico— ni el DRC, que da por buena la net que tiene el pad.

Correr con el python de KiCad:
  "$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" checks/check_netlist.py
"""
import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.dirname(HERE)
NET = os.path.join(PCB_DIR, "gamesetup.net")
PCB = os.path.join(PCB_DIR, "gamesetup.kicad_pcb")


def from_netlist(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    seccion = src.split("(nets", 1)[1]
    out = {}
    for chunk in re.split(r"\(net ", seccion)[1:]:
        m = re.search(r'\(name "([^"]+)"\)', chunk)
        if not m:
            continue
        name = m.group(1)
        for ref, pin in re.findall(
                r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', chunk):
            out[(ref, pin)] = name
    return out


def from_board(path):
    board = pcbnew.LoadBoard(path)
    out = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num:
                out[(fp.GetReference(), num)] = pad.GetNetname()
    return out


def comparar(a, b):
    """(solo_en_sch, solo_en_pcb, distintos). Los tres vacios = identicos."""
    solo_sch = sorted(set(a) - set(b))
    solo_pcb = sorted(set(b) - set(a))
    distinto = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    return solo_sch, solo_pcb, distinto


def main():
    for p in (NET, PCB):
        if not os.path.isfile(p):
            print(f"FALTA: {p}")
            return 1
    a, b = from_netlist(NET), from_board(PCB)
    solo_sch, solo_pcb, distinto = comparar(a, b)

    if not (solo_sch or solo_pcb or distinto):
        print(f"OK: {len(a)} conexiones identicas entre esquematico y PCB.")
        return 0

    print("G-2 FALLA")
    for k in solo_sch:
        print(f"  solo en el esquematico: {k[0]}.{k[1]} = {a[k]}")
    for k in solo_pcb:
        print(f"  solo en la PCB:         {k[0]}.{k[1]} = {b[k]}")
    for k in distinto:
        print(f"  net distinta:           {k[0]}.{k[1]}: "
              f"sch={a[k]} pcb={b[k]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
