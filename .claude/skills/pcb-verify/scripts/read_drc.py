#!/usr/bin/env python3
"""Lee logs/drc.json y lo resume por severidad y por tipo.

Existe porque el resumen en prosa del DRC engana. El JSON guarda TRES listas
distintas y las tres importan por motivos distintos:

  violations        reglas de diseno violadas (margenes, anillos, silk)
  unconnected_items nets que quedaron sin rutear
  schematic_parity  la placa y el esquematico no dicen lo mismo

Mirar solo una y declarar verde es el error tipico: una placa con
`unconnected_items = 0` se lee como "ruteada y lista", y puede tener cinco
errores de margen que la hacen infabricable. Paso exactamente eso en este
proyecto.

Corre con cualquier python 3.

Uso:  python read_drc.py [logs/drc.json]

Sale 0 si no hay errores, 1 si hay al menos uno.
"""
import json
import os
import sys
import time
from collections import Counter

# La consola de Windows suele venir en cp1252 y los mensajes del DRC estan en
# espanol con acentos: sin esto salen como interrogantes y un mensaje ilegible
# es un mensaje que no se lee.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LISTAS = ("violations", "unconnected_items", "schematic_parity")


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else "logs/drc.json"
    if not os.path.exists(ruta):
        print(f"No existe {ruta}. Corre el DRC primero (ver SKILL.md, G-3).")
        return 2

    with open(ruta, encoding="utf-8") as f:
        d = json.load(f)

    print("=" * 68)
    print(f"DRC  {ruta}")
    print(f"     generado {d.get('date', '?')}  |  KiCad {d.get('kicad_version', '?')}")
    edad = (time.time() - os.path.getmtime(ruta)) / 3600.0
    print(f"     el archivo tiene {edad:.1f}h  (G-F dice si eso es fresco)")
    print("=" * 68)

    errores = 0
    for nombre in LISTAS:
        items = d.get(nombre, [])
        sev = Counter(x.get("severity") for x in items)
        errores += sev.get("error", 0)
        print(f"\n{nombre}: {len(items)}  {dict(sev) if sev else ''}")

        # Agrupar por tipo: cinco violaciones del mismo tipo suelen ser una
        # sola causa, y verlas agrupadas evita perseguirlas de a una.
        por_tipo = Counter(
            (x.get("severity"), x.get("type")) for x in items
        )
        for (s, t), n in sorted(por_tipo.items(), key=lambda kv: -kv[1]):
            print(f"    {s:8} {n:3}  {t}")

        for x in items:
            if x.get("severity") == "error":
                desc = (x.get("description") or "").strip()
                print(f"    ERROR  {x.get('type')} | {desc[:100]}")

    print("\n" + "=" * 68)
    if errores:
        print(f"{errores} error(es). Veredicto: NO FABRICABLE.")
        return 1
    print("0 errores. Los avisos, si los hay, van listados pero no bloquean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
