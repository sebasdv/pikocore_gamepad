#!/usr/bin/env python3
"""G-F: ningun artefacto puede ser mas viejo que las fuentes de las que sale.

Es la puerta que faltaba, y la que mas barato evita el peor error posible.
Un DRC en verde fechado ANTES de la ultima corrida de gen_pcb.py no dice que
la placa este bien: dice que estuvo bien una placa que ya no existe. Ese modo
de fallo es peor que un error, porque se lee como exito y nadie lo mira dos
veces.

El caso real que motivo el script: el 2026-08-31 se regeneraron el
esquematico y el netlist, pero la .kicad_pcb quedo del 2026-08-28 — y el zip
de fabricacion salio de esa placa vieja. Ninguna de las puertas existentes se
da cuenta, porque cada una mira su archivo y lo encuentra internamente
consistente.

Corre con cualquier python 3: solo compara mtimes, no importa pcbnew. Por eso
va primero, antes de gastar un minuto en el DRC.

Uso:  python .claude/skills/pcb-verify/scripts/check_freshness.py [pcb_dir]

Sale 0 si todo esta al dia, 1 si hay algo desactualizado.

LIMITE HONESTO: mtime detecta "se toco despues", no "cambio el contenido".
Un `touch` o un checkout de git puede dar un falso positivo. Cuando eso pase,
la respuesta correcta es regenerar igual (es barato) o confirmar a mano que el
contenido no cambio — no es ignorar la puerta.
"""
import os
import sys
import time

# El grafo del pipeline: cada artefacto con las fuentes de las que se deriva y
# el comando que lo reconstruye. El orden es el de la cadena, para que el
# reporte se lea de arriba hacia abajo como el ciclo de trabajo.
#
# Un artefacto solo se compara contra las fuentes que REALMENTE lo afectan.
# Meter de mas genera ruido y entrena a ignorar la puerta.
PIPELINE = [
    (
        "pikocore_gamepad.kicad_sch",
        ["gen_sch.py", "netlist.py", "params.py", "pinmap.py"],
        "python gen_sch.py",
    ),
    (
        "pikocore_gamepad.net",
        ["pikocore_gamepad.kicad_sch"],
        '"$KICLI" sch export netlist --format kicadsexpr '
        "-o pikocore_gamepad.net pikocore_gamepad.kicad_sch",
    ),
    (
        "logs/erc.rpt",
        ["pikocore_gamepad.kicad_sch"],
        '"$KICLI" sch erc --severity-all --exit-code-violations '
        "-o logs/erc.rpt pikocore_gamepad.kicad_sch",
    ),
    (
        "pikocore_gamepad.kicad_pcb",
        [
            "pikocore_gamepad.net",
            "gen_pcb.py",
            "placements.py",
            "params.py",
            "manual_tracks.py",
            "plane_vias.py",
            "route_io.py",
            "finish_pcb.py",
            "pikocore_gamepad.kicad_dru",
            "lib/",
        ],
        "ciclo completo de ruteo (ver referencias/gates.md, G-3)",
    ),
    (
        "logs/drc.json",
        ["pikocore_gamepad.kicad_pcb", "pikocore_gamepad.kicad_dru"],
        '"$KICLI" pcb drc --severity-all --schematic-parity '
        "--exit-code-violations --format json "
        "-o logs/drc.json pikocore_gamepad.kicad_pcb",
    ),
    (
        "fab/pikocore_gamepad_fab.zip",
        ["pikocore_gamepad.kicad_pcb", "netlist.py", "gen_fab.py"],
        '"$KIPY" gen_fab.py',
    ),
]


def mtime(path):
    """mtime del archivo, o del descendiente mas nuevo si es un directorio.

    Los directorios se resuelven asi porque `lib/` importa como fuente de la
    placa: tocar un .kicad_mod cambia el footprint que gen_pcb.py levanta,
    aunque el mtime del directorio no siempre lo refleje.
    """
    if not os.path.exists(path):
        return None
    if os.path.isfile(path):
        return os.path.getmtime(path)
    ultimo = 0.0
    for raiz, dirs, archivos in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for a in archivos:
            try:
                ultimo = max(ultimo, os.path.getmtime(os.path.join(raiz, a)))
            except OSError:
                pass
    return ultimo or None


def fecha(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    base = os.path.abspath(base)

    if not os.path.exists(os.path.join(base, "gen_pcb.py")):
        print(f"No parece un directorio de PCB (no hay gen_pcb.py): {base}")
        return 2

    desactualizados = []
    faltantes = []

    for artefacto, fuentes, comando in PIPELINE:
        t_art = mtime(os.path.join(base, artefacto))
        if t_art is None:
            faltantes.append((artefacto, comando))
            continue

        nuevas = []
        for fuente in fuentes:
            t_src = mtime(os.path.join(base, fuente))
            if t_src is not None and t_src > t_art:
                nuevas.append((fuente, t_src))

        if nuevas:
            desactualizados.append((artefacto, t_art, sorted(nuevas), comando))

    print("=" * 68)
    print("G-F  frescura del pipeline")
    print("=" * 68)

    if not desactualizados and not faltantes:
        print("\nTodo al dia: ningun artefacto es mas viejo que sus fuentes.")
        return 0

    for artefacto, comando in faltantes:
        print(f"\nFALTA  {artefacto}")
        print(f"       generar con: {comando}")

    for artefacto, t_art, nuevas, comando in desactualizados:
        atraso = (nuevas[-1][1] - t_art) / 3600.0
        print(f"\nVIEJO  {artefacto}  ({fecha(t_art)}, {atraso:.1f}h de atraso)")
        for fuente, t_src in nuevas:
            print(f"       fuente mas nueva: {fuente}  ({fecha(t_src)})")
        print(f"       regenerar con: {comando}")

    total = len(desactualizados) + len(faltantes)
    print(f"\n{total} artefacto(s) fuera de fecha.")
    print(
        "Mientras esto no cierre, cualquier resultado en verde de las puertas\n"
        "de abajo describe un archivo que ya no es el que se va a fabricar."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
