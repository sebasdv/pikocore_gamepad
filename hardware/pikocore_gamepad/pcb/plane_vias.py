#!/usr/bin/env python3
"""Vias de conexion a plano para los pads SMD de GND y 3V3.

Correr con el python de KiCad, DESPUES de gen_pcb.py y ANTES de
route_io.py export.

EL ORDEN IMPORTA Y NO ES EL INTUITIVO. La primera version de este script
corria despues del ruteo, que parecia lo natural: primero las senales, despues
"rellenar" las conexiones a plano que faltaban. Sale mal. Con el ruteo ya
hecho, poner una via en el centro de cada pad la mete encima de pistas de
otras nets que ya pasan por ahi: 12 cortocircuitos y 22 violaciones de margen
en la corrida donde se probo.

Puestas ANTES, las vias entran al DSN como parte del board y freerouting las
esquiva igual que a cualquier otro obstaculo.

POR QUE HACE FALTA UN SCRIPT Y NO LO HACE FREEROUTING:

Los planos viven en las capas internas (GND en In1, 3V3 en In2) y route_io.py
las exporta al DSN como (type power) para que freerouting NO rutee senales
encima y las parta. El efecto colateral es que freerouting deja de verlas como
destino: no pone ni una via hacia ellas. Los pads THT no lo necesitan —el
taladro ya atraviesa todas las capas— pero los 42 pads SMD de GND/3V3 quedan
"unconnected" aunque el plano este relleno justo debajo.

Se probo antes meter GND en la netclass Power (que en el DSN es lo que declara
la via a usar). No alcanza: freerouting sigue sin bajar a una capa (type
power), sin importar la clase. Por eso las vias se colocan aca, que ademas es
determinista y no depende de lo que el autorouter decida en cada corrida.

POR QUE ESTO NO CONTRADICE EL "NO STITCHING" DE finish_pcb.py:

Ahi se descarto agregar vias de stitching, que son vias de GND puestas en
lugares arbitrarios para coser islas del plano. Aquellas no conectaban nada
—tocaban el plano interno y nada mas— y el DRC las reportaba como
via_dangling. Estas son otra cosa: cada una nace EN un pad y termina en el
plano de SU MISMA net, o sea que es la conexion que al pad le falta. Sin ella
el pad no tiene forma de llegar al plano.

VIAS PASANTES Y NO CIEGAS: una via F.Cu->B.Cu atraviesa los dos planos, pero
solo se conecta al que comparte su net; para el otro el relleno de zona abre
un despeje alrededor. Es lo mismo que ya hacen las 38 vias que pone
freerouting para las senales. Las vias ciegas/enterradas encarecerian la
placa sin ganar nada.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "pikocore_gamepad.kicad_pcb")

# net -> capa donde vive su plano. Si se agrega un plano nuevo, va aca.
PLANOS = {"GND": "GND", "3V3": "PWR"}

# Misma via que declara la netclass Power en el DSN (600um / 300um), asi que
# la placa no estrena una geometria de taladro solo por estas vias.
VIA_D = 0.6
VIA_DRILL = 0.3

# Via chica para pads apretados. 0.50/0.30 deja un anillo de 0.100mm, que es
# exactamente el min_via_annular_width del proyecto, y el taladro sigue siendo
# el mismo 0.30 — no agrega una medida de broca nueva al fabricante.
VIA_D_MIN = 0.5

# Margen a respetar contra el cobre vecino (el clearance general del proyecto).
CLEARANCE = 0.2

# Hueco libre que necesita cada tamano de via alrededor del centro del pad.
HUECO_NORMAL = VIA_D / 2 + CLEARANCE      # 0.50mm
HUECO_MIN = VIA_D_MIN / 2 + CLEARANCE     # 0.45mm


def mm(v):
    return pcbnew.FromMM(v)


def pads_sin_plano(board):
    """Pads SMD cuya net tiene plano y que por lo tanto necesitan via."""
    out = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNumber():
                continue
            if pad.GetNetname() not in PLANOS:
                continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                continue          # el taladro ya cruza todas las capas
            out.append((fp.GetReference(), pad))
    return out


def ya_tiene_via(board, pad, tol=0.05):
    """True si ya hay una via de la misma net encima del pad.

    Evita duplicar cuando el script se corre dos veces sobre el mismo board, o
    cuando freerouting si llego a poner la via.
    """
    px, py = pad.GetPosition().x, pad.GetPosition().y
    for t in board.GetTracks():
        if t.GetClass() != "PCB_VIA":
            continue
        if t.GetNetname() != pad.GetNetname():
            continue
        d = ((t.GetPosition().x - px) ** 2 + (t.GetPosition().y - py) ** 2) ** 0.5
        if d <= mm(tol):
            return True
    return False


def hueco_libre(board, pad):
    """Distancia del CENTRO del pad al cobre ajeno mas cercano, en mm.

    Solo mira pads de otra net: es lo que limita el diametro de la via. Las
    pistas no se consideran porque este script corre ANTES del ruteo.
    """
    px = pcbnew.ToMM(pad.GetPosition().x)
    py = pcbnew.ToMM(pad.GetPosition().y)
    best = float("inf")
    for fp in board.GetFootprints():
        for q in fp.Pads():
            if not q.GetNumber() or q is pad:
                continue
            if q.GetNetname() == pad.GetNetname():
                continue
            bb = q.GetBoundingBox()
            dx = max(0.0, max(pcbnew.ToMM(bb.GetLeft()) - px,
                              px - pcbnew.ToMM(bb.GetRight())))
            dy = max(0.0, max(pcbnew.ToMM(bb.GetTop()) - py,
                              py - pcbnew.ToMM(bb.GetBottom())))
            best = min(best, (dx * dx + dy * dy) ** 0.5)
    return best


def poner_via(board, pad, diam):
    """Via pasante en el centro del pad, en la net del pad."""
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pad.GetPosition())
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(mm(diam))
    v.SetDrill(mm(VIA_DRILL))
    v.SetNet(pad.GetNet())
    board.Add(v)
    return v


def main():
    if not os.path.isfile(PCB):
        print(f"FALTA: {PCB}")
        return 1
    board = pcbnew.LoadBoard(PCB)

    pend = pads_sin_plano(board)
    puestas = chicas = saltadas = 0
    sin_lugar = []
    for ref, pad in pend:
        if ya_tiene_via(board, pad):
            saltadas += 1
            continue
        h = hueco_libre(board, pad)
        if h >= HUECO_NORMAL:
            poner_via(board, pad, VIA_D)
            puestas += 1
        elif h >= HUECO_MIN:
            poner_via(board, pad, VIA_D_MIN)
            chicas += 1
        else:
            # No entra ni la chica. No se fuerza: una via que viola el
            # clearance es peor que un pad que llega al plano por pista, que
            # es lo que hace freerouting cuando el pad se queda sin via.
            sin_lugar.append(f"{ref}.{pad.GetNumber()} "
                             f"[{pad.GetNetname()}] hueco={h:.3f}mm")

    pcbnew.SaveBoard(PCB, board)
    vias = len([t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"])
    print(f"pads SMD sobre plano: {len(pend)}")
    print(f"vias {VIA_D}mm: {puestas}   vias {VIA_D_MIN}mm: {chicas}   "
          f"ya tenian: {saltadas}")
    if sin_lugar:
        print(f"SIN VIA por falta de espacio ({len(sin_lugar)}) — tienen que "
              f"llegar al plano por pista:")
        for s in sin_lugar:
            print(f"  {s}")
    print(f"guardado: {PCB}  ({vias} vias en total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
