#!/usr/bin/env python3
"""G-4: el pinout de la PCB coincide con el config.h del firmware V2.

En V1 esta verificacion se hacia leyendo las dos tablas a ojo. Automatizarla
importa porque el modo de fallo es silencioso: la placa se fabrica, el
firmware compila, y recien se descubre al enchufar.

Se compara en las DOS direcciones:
  - funciones de la PCB que el firmware no define, o define en otro pin;
  - #define PIN_* del firmware que la PCB no conoce. Esta segunda direccion
    existe porque el camino natural es partir del config.h de V1, que trae
    PIN_BTN_PLAY, PIN_ENC0_A y demas apuntando a hardware que V2 no tiene.

Uso:  python checks/check_pinmap.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.dirname(HERE)
sys.path.insert(0, PCB)

CONFIG_H = os.path.join(PCB, "firmware_pin_stub", "config.h")


def parse_defines(src):
    """{nombre: valor} de los #define PIN_* con valor entero decimal.

    Solo enteros decimales: un numero de pin nunca es 0x20 ni (62500000).
    """
    out = {}
    for m in re.finditer(r"^\s*#define\s+(PIN_\w+)\s+(\d+)\s*(?://.*)?$",
                         src, re.M):
        out[m.group(1)] = int(m.group(2))
    return out


def compare(gpio_by_func, defines):
    """Discrepancias PCB -> firmware. Lista vacia = todo coincide."""
    diffs = []
    for func, gpio in sorted(gpio_by_func.items()):
        key = f"PIN_{func}"
        if key not in defines:
            diffs.append(f"{func}: la PCB usa GP{gpio}, el firmware no define {key}")
        elif defines[key] != gpio:
            diffs.append(
                f"{func}: la PCB usa GP{gpio}, el firmware dice GP{defines[key]}")
    return diffs


def sobrantes(gpio_by_func, defines):
    """#define PIN_* del firmware que la PCB no conoce."""
    conocidos = {f"PIN_{f}" for f in gpio_by_func}
    return sorted(k for k in defines if k not in conocidos)


def main():
    import pinmap
    path = os.path.normpath(CONFIG_H)
    if not os.path.isfile(path):
        print(f"FALTA: {path}")
        return 1
    with open(path, encoding="utf-8") as f:
        defines = parse_defines(f.read())
    by_func = {func: g for g, func in pinmap.GPIO.items()}
    diffs = compare(by_func, defines)
    sobra = sobrantes(by_func, defines)
    if not diffs and not sobra:
        print(f"OK: {len(by_func)} pines coinciden entre PCB y firmware.")
        return 0
    print(f"G-4 FALLA: {len(diffs) + len(sobra)} discrepancia(s)\n")
    for d in diffs:
        print("  " + d)
    for s in sobra:
        print(f"  {s}: el firmware lo define, la PCB no lo conoce")
    return 1


if __name__ == "__main__":
    sys.exit(main())
