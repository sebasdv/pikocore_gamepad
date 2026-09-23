#!/usr/bin/env python3
"""Corre todas las puertas en orden y devuelve 1 si alguna falla.

Es lo que hay que correr antes de generar archivos de fabricacion, y lo que
gen_fab.py invoca antes de escribir nada.

El orden no es casual: va de lo barato a lo caro, y de lo que invalida todo
lo demas a lo que solo afecta un subsistema. Si el pinout no coincide con el
firmware no tiene sentido mirar el DRC.

G-1 (ERC) y G-3 (DRC) no estan aca: las corre kicad-cli, tardan, y necesitan
el esquematico y la placa ya generados. Se corren aparte.

Correr con el python de KiCad, porque check_netlist y check_placement
importan pcbnew:
  "$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" checks/run_all.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

PUERTAS = [
    ("G-0  constantes fisicas y footprints verificados", "check_verified.py"),
    ("G-5  referencias duplicadas", "check_refs.py"),
    ("G-4  pinout PCB <-> firmware", "check_pinmap.py"),
    ("G-2  netlist esquematico <-> PCB", "check_netlist.py"),
    ("---  placement sin solapamientos", "check_placement.py"),
]


def main():
    fallan = []
    for nombre, script in PUERTAS:
        print(f"\n{'=' * 60}\n=== {nombre}\n{'=' * 60}")
        r = subprocess.run([sys.executable, os.path.join(HERE, script)])
        if r.returncode != 0:
            fallan.append(nombre)

    print("\n" + "=" * 60)
    if not fallan:
        print("TODAS LAS PUERTAS PASAN.")
        return 0
    print(f"{len(fallan)} puerta(s) fallan:")
    for f in fallan:
        print("  " + f)
    return 1


if __name__ == "__main__":
    sys.exit(main())
