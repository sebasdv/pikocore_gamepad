#!/usr/bin/env python3
"""G-5: no hay referencias duplicadas en la lista de instancias.

En V1 una C19 duplicada llego al esquematico y hubo que cazarla a mano
(commit aad25ba). KiCad no se queja al generar: el segundo componente
simplemente pisa las propiedades del primero, y el sintoma aparece mucho
despues como un valor equivocado en el BOM o una net que no cierra.

Los huecos de numeracion se reportan como AVISO y no hacen fallar la puerta:
saltear un numero es legitimo, pero suele indicar un componente que se dio de
baja dejando nets huerfanas, asi que conviene verlo.

Uso:  python checks/check_refs.py
"""
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

REF_RE = re.compile(r"^([A-Za-z_]+)(\d+)$")


def duplicados(refs):
    """Referencias que aparecen mas de una vez, ordenadas."""
    return sorted(r for r, n in Counter(refs).items() if n > 1)


def huecos(refs):
    """Numeros faltantes dentro de cada prefijo (R1, R2, R4 -> R3).

    Se miden entre el minimo y el maximo de cada prefijo, asi que una serie
    que no arranca en 1 (U10/U11/U12) no cuenta como hueco.
    """
    por_prefijo = defaultdict(list)
    for r in refs:
        m = REF_RE.match(r)
        if m:
            por_prefijo[m.group(1)].append(int(m.group(2)))
    out = []
    for pref, nums in por_prefijo.items():
        faltan = set(range(min(nums), max(nums))) - set(nums)
        out.extend(f"{pref}{n}" for n in faltan)
    return sorted(out, key=lambda r: (REF_RE.match(r).group(1),
                                      int(REF_RE.match(r).group(2))))


def main():
    try:
        import netlist
    except ModuleNotFoundError:
        print("netlist.py todavia no existe (se crea en el Task 10).")
        return 1
    refs = [inst[1] for inst in netlist.INSTANCES]
    dups = duplicados(refs)
    gaps = huecos(refs)
    print(f"{len(refs)} instancias.")
    if gaps:
        print(f"AVISO: huecos de numeracion: {', '.join(gaps)}")
    if not dups:
        print("OK: no hay referencias duplicadas.")
        return 0
    print(f"G-5 FALLA: referencia(s) duplicada(s): {', '.join(dups)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
