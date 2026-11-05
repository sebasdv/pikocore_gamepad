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


def vias_sueltas(board):
    """Vias que tocan menos de dos capas de cobre.

    Quedan cuando se borra el stub que llegaba a ellas, o cuando freerouting
    deja una via con pista de un solo lado. El DRC las marca como
    via_dangling y no conectan nada. Cuenta como capa: una pista que termina
    en la via o que le pasa por encima, un pad que la contiene, o una zona
    de la misma net que la contiene (el plano GND/3V3, o las zonas que
    vienen dentro de una huella, como las del nucleo RP2350A del chip-down,
    que no llevan pista).
    """
    tramos = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    zonas = [z for z in list(board.Zones())
             + [z for fp in board.GetFootprints() for z in fp.Zones()]
             if not z.GetIsRuleArea()]
    out = []
    for v in board.GetTracks():
        if v.GetClass() != "PCB_VIA":
            continue
        c, r = v.GetPosition(), v.GetWidth(pcbnew.F_Cu) // 2
        capas = set()
        for t in tramos:
            # HitTest con tolerancia r: la pista que termina en la via y
            # tambien la que le pasa por encima sin terminar ahi. Mirando
            # solo los extremos, una via en medio de una pista se borraba y
            # la pista caia en la vuelta siguiente.
            if t.GetNetCode() == v.GetNetCode() and t.HitTest(c, r):
                capas.add(t.GetLayer())
        for p in pads:
            if p.GetNetCode() == v.GetNetCode() and p.HitTest(c):
                capas.update(p.GetLayerSet().CuStack())
        for z in zonas:
            if z.GetNetCode() == v.GetNetCode() and z.Outline().Contains(c):
                capas.update(z.GetLayerSet().CuStack())
        if len(capas) < 2:
            out.append(v)
    return out


def main():
    if not os.path.isfile(PCB):
        print(f"FALTA: {PCB}")
        return 1
    board = pcbnew.LoadBoard(PCB)

    # Mismo paso que hace gen_pcb.py al colocar: FPID con libreria, Value y
    # marca de soldadura manual desde el netlist. Repetirlo aca es gratis
    # (idempotente) y deja la placa en paridad con el esquematico aunque
    # venga de un ciclo viejo.
    from gen_pcb import (identidad_desde_netlist, marcar_manuales,
                         reparar_capas_pth, rotular_a_mano)
    identidad_desde_netlist(board)
    marcar_manuales(board)
    sin_rotulo = rotular_a_mano(board)
    if sin_rotulo:
        print(f"AVISO: referencia sin lugar en la serigrafia: {', '.join(sin_rotulo)}")
    n_pth = reparar_capas_pth(board)
    if n_pth:
        print(f"pads PTH con capas internas restauradas: {n_pth}")

    # Stubs colgantes: freerouting parte y vuelve a unir las pistas manuales
    # (las de U2 sobre todo) y a veces deja un tramo de medio milimetro con
    # un extremo al aire. Electricamente no hace nada; el DRC lo reporta
    # como track_dangling una vez por cada pista que lo toca (21 avisos por
    # un stub de 0.6mm). Se borran iterando, porque quitar uno puede dejar
    # colgando al anterior.
    # BuildConnectivity() en cada vuelta y las pistas sacadas vivas en una
    # lista hasta guardar: sin eso KiCad 9.0.1 se cae con un access violation
    # (la conectividad queda apuntando a pistas ya removidas; paso con la
    # placa del chip-down, que tiene cientos de pistas mas).
    sacadas = []
    while True:
        board.BuildConnectivity()
        conn = board.GetConnectivity()
        colgantes = [t for t in board.GetTracks()
                     if t.GetClass() == "PCB_TRACK"
                     and conn.TestTrackEndpointDangling(t, False)]
        colgantes += vias_sueltas(board)
        if not colgantes:
            break
        for t in colgantes:
            board.Remove(t)
        sacadas += colgantes
    board.BuildConnectivity()
    if sacadas:
        print(f"stubs colgantes borrados: {len(sacadas)}")

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
