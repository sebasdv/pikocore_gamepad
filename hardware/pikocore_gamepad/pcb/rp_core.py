#!/usr/bin/env python3
"""Lleva el nucleo del RP2350A (rp_core_ref.py) a esta placa.

Lo usa gen_pcb.py: colocar() pone las huellas antes de asignar nets, y
cobre() agrega pistas, vias y zonas antes del relleno.

LA TRANSFORMACION se hace con las operaciones de pcbnew y no con aritmetica
propia: cada pieza, pista, via y zona se crea donde estaba en la placa
oficial (frente, U1 en el origen) y despues se la VOLTEA al dorso, se la ROTA
y se la MUEVE como un solo bloque rigido (placements.NUCLEO). Voltear todo
junto es lo mismo, fisicamente, que dar vuelta la placa oficial: el inductor
queda en la misma relacion con su capacitor de salida que en el diseno de
Raspberry Pi, que es lo que la guia exige.
"""
import re

import pcbnew

import rp_core_ref as R
from netlist import CORE_NET_MAP, CORE_REF_MAP
from pinmap import GPIO
from placements import NUCLEO

LIB = "rp_minimal"


def mm(v):
    return pcbnew.FromMM(v)


def _bloque(item):
    """Voltea al dorso, rota y traslada, en ese orden, alrededor del origen
    (donde esta U1 en el marco oficial)."""
    x0, y0, rot = NUCLEO
    c = pcbnew.VECTOR2I(0, 0)
    item.Flip(c, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    item.Rotate(c, pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
    item.Move(pcbnew.VECTOR2I(mm(x0), mm(y0)))


def colocar(board, find_fp):
    """Pone las huellas del nucleo. Devuelve las referencias colocadas."""
    refs = []
    for rp_ref, (nombre, dx, dy, rot, _valor) in R.PARTS.items():
        fp = find_fp(f"{LIB}:{nombre}")
        fp.SetReference(CORE_REF_MAP[rp_ref])
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I(mm(dx), mm(dy)))
        fp.SetOrientationDegrees(rot)
        _bloque(fp)
        refs.append(CORE_REF_MAP[rp_ref])
    return refs


# Salida copiada de la placa oficial SOLO para estas nets, las que freerouting
# dejaba abiertas corrida tras corrida. Las dos primeras, LCD_DC y LCD_MOSI
# (cinco corridas seguidas): son los
# pines 5 y 8 de la fila de arriba, encerrados entre la pista de 1V1 del pin 6
# y las vias que planta para los vecinos. Con el carril de la placa oficial
# (entre los capacitores de desacoplo, hasta pasar sus vias) solo le queda
# unir la punta con J4. Copiar el fanout de TODOS los GPIO se probo y fue peor
# (10 a 15 nets abiertas): fija salidas que en esta placa chocan con el
# cristal y el lazo del TPS63001.
FANOUT_NETS = {"LCD_DC", "LCD_MOSI", "BTN_START", "DPAD_UP", "DPAD_DOWN"}


def net_fanout(rp_net):
    """Net de la placa oficial -> net de esta placa, o None si el GPIO esta
    libre aca (GP25/27/28: su tramo no se copia)."""
    nombre = rp_net.lstrip("/")
    m = re.match(r"GPIO(\d+)", nombre)
    if m:
        return GPIO.get(int(m.group(1)))
    return {"RUN": "RUN", "SWD": "SWDIO", "SWCLK": "SWCLK"}[nombre]


def cobre(board, nets):
    """Pistas, vias y zonas del nucleo, con las nets de esta placa.
    Devuelve (pistas, vias, zonas)."""
    n_t = n_v = n_z = 0
    for net, capa, x0, y0, x1, y1, ancho in R.TRACKS:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
        t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        t.SetWidth(mm(ancho))
        t.SetLayer(board.GetLayerID(capa))
        t.SetNet(nets[CORE_NET_MAP[net]])
        board.Add(t)
        _bloque(t)
        n_t += 1
    for rp_net, capa, x0, y0, x1, y1, ancho in R.FANOUT:
        net = net_fanout(rp_net)
        if net not in FANOUT_NETS:
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
        t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        t.SetWidth(mm(ancho))
        t.SetLayer(board.GetLayerID(capa))
        t.SetNet(nets[net])
        board.Add(t)
        _bloque(t)
        n_t += 1
    for net, x, y, diam, taladro in R.VIAS:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        # Con capa: en KiCad 9.0.1 SetWidth(int) abre un assert modal.
        v.SetWidth(pcbnew.PADSTACK.ALL_LAYERS, mm(diam))
        v.SetDrill(mm(taladro))
        v.SetNet(nets[CORE_NET_MAP[net]])
        board.Add(v)
        _bloque(v)
        n_v += 1
    for zd in R.ZONES:
        z = pcbnew.ZONE(board)
        z.SetLayer(board.GetLayerID(zd["layer"]))
        z.SetNet(nets[CORE_NET_MAP[zd["net"]]])
        z.SetAssignedPriority(zd["priority"])
        z.SetLocalClearance(mm(zd["clearance"]))
        z.SetMinThickness(mm(zd["min_thickness"]))
        z.SetPadConnection(zd["connection"])
        z.SetThermalReliefGap(mm(zd["thermal_gap"]))
        z.SetThermalReliefSpokeWidth(mm(zd["spoke"]))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        o = z.Outline()
        o.NewOutline()
        for x, y in zd["pts"]:
            o.Append(mm(x), mm(y))
        board.Add(z)
        _bloque(z)
        n_z += 1
    return n_t, n_v, n_z
