#!/usr/bin/env python3
"""Pistas ruteadas a mano que el autorouter no resuelve.

Correr con el python de KiCad DESPUES de gen_pcb.py y ANTES de
route_io.py export — el mismo lugar que plane_vias.py, y por el mismo motivo.

EL ORDEN IMPORTA. Puestas DESPUES del ruteo, freerouting ya ocupo el lugar y
las pistas manuales chocan con las suyas: se probo y aparecieron 4
cortocircuitos VSYS_F contra VSYS, porque el autorouter habia cruzado VSYS
justo por donde tenia que pasar VSYS_F. Puestas ANTES, entran al DSN como
wiring preexistente y freerouting las esquiva.

POR QUE EXISTE ESTE ARCHIVO:

gen_pcb.py hace pcbnew.NewBoard(), o sea que la placa se reconstruye DESDE
CERO en cada corrida del pipeline. El ruteo normal sobrevive porque vuelve a
entrar por el .ses, pero una pista dibujada a mano en la GUI de KiCad no tiene
de donde volver: se pierde en la siguiente regeneracion, sin aviso.

Todo lo que se rutee a mano tiene que quedar aca para ser reproducible.

COMO AGREGAR UNA: dibujarla en la GUI de KiCad, leer los segmentos con
pcbnew (GetTracks filtrando por net) y transcribirlos al dict, con el primer
extremo EXACTAMENTE sobre el centro de su pad. verificar_extremos() falla en
la proxima corrida si el layout se mueve y las coordenadas quedan viejas, que
es la unica forma de enterarse a tiempo.

Una entrada puede terminar en VIA en vez de en otro pad: es lo que hace falta
cuando el destino es un PLANO (GND, 3V3) y no una pieza.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "pikocore_gamepad.kicad_pcb")

# clave -> dict(net, capa, ancho_mm, puntos, via)
#
# `via`: si es True, el ultimo punto lleva una via al plano en vez de tener
# que caer sobre un pad. Se usa cuando el destino es el PLANO y no una pieza.
#
# POR QUE ESTAS CUATRO SON A MANO — el TPS61023 (U2) en SOT-563:
#
# Sus pads miden 0.68 x 0.35mm a paso 0.50: entre dos pads adyacentes quedan
# 0.15mm, cuando una pista de 0.20 necesita 0.60 con su clearance. La unica
# salida es el corredor de 0.74mm que hay ENTRE las dos columnas, por debajo
# del chip — que es exactamente lo que recomienda TI en su guia de layout
# (SLVAES4, seccion 4: "place the SW trace UNDERNEATH the device").
#
# Por ese corredor entra una pista de 0.20 (0.20 + 0.40 = 0.60 < 0.74) pero NO
# una de 0.40 (necesitaria 0.80). Y 5V/GND/VSYS_F son de la netclass Power,
# que va a 0.40. Fallan por 0.06mm.
#
# La evidencia de que el problema es el ANCHO y no el encapsulado: el pin 1
# (FB) es de la clase default (0.20) y el autorouter lo resuelve solo, en la
# misma corrida donde deja los de Power sin conectar. BOOST_SW tambien es
# default, pero esta aca por otro motivo: no por ancho sino por criticidad
# (ver su nota abajo).
#
# Por eso van a mano con 0.20 en el tramo corto que sale del chip. Es lo mismo
# que dibuja TI en su figura 9: pista fina bajo el IC, ancha al salir.
#
# route_io.py ademas tiene que quitar el contorno del footprint del DSN (ver
# SIN_OUTLINE ahi): KiCad lo exporta como (outline ...) y freerouting lo toma
# como obstaculo, sellando el corredor.
PISTAS = {
    # FB (pin 1) NO esta aca: es de la clase default (0.20mm) y el autorouter
    # lo resuelve solo, igual que SW. Se probo ponerlo a mano y sale peor —
    # cualquier ruta fija choca contra lo que el ruteo pone alrededor, y al
    # reves. Solo van a mano las que son IMPOSIBLES por el ancho de 0.40.
    # VSYS_F llega a los pines 2 (EN) y 3 (VIN). EN atado a VIN es lo que hace
    # que el riel analogico arranque sin depender del firmware.
    "U2_VSYS_F_2": dict(net="VSYS_F", capa="B.Cu", ancho=0.20, via=False,
                        puntos=[(64.287, 6.00), (63.40, 6.00),
                                (61.20, 6.00)]),
    # Termina en el punto de union con la ruta de arriba, no en un pad: por eso
    # lleva via=True (que saltea la verificacion del extremo final) mas
    # sin_via=True (que evita poner la via en si).
    "U2_VSYS_F_3": dict(net="VSYS_F", capa="B.Cu", ancho=0.20, via=True,
                        sin_via=True,
                        puntos=[(64.287, 5.50), (63.40, 5.50), (62.60, 6.00)]),
    # GND sale hacia +X y baja a una via al plano de In1, que es lo que TI
    # recomienda para masa en vez de una pista lateral.
    "U2_GND": dict(net="GND", capa="B.Cu", ancho=0.20, via=True,
                   # x=66.30 y no 66.60: con 66.60 la via de 0.5mm quedaba
                   # a 0.05mm de la pista de 5V que baja por x=67.00 —
                   # riesgo de corto 5V-GND en fabricacion. La revision de
                   # codigo lo encontro; verificar_extremos no compara las
                   # entradas de PISTAS entre si, solo contra pads.
                   puntos=[(65.713, 5.50), (66.30, 5.50), (66.30, 4.10)]),
    # VOUT sale del chip HACIA ABAJO y ahi lo toma el ruteador.
    #
    # Antes esta pista llegaba sola hasta C5.1, subiendo por x=67.00. Con eso
    # dibujaba una "L" alrededor de U2.5 —el tramo horizontal en y=6.50 y el
    # vertical en x=67.00— que TAPIABA las dos salidas del pin de
    # conmutacion: BOOST_SW no podia ir ni a la derecha ni hacia abajo, y
    # quedaba sin rutear. El DRC lo reporto como una conexion abierta entre
    # U2.5 y L1.2.
    #
    # QUIEN CEDE Y POR QUE: los dos tienen que cruzarse, porque 5V es el pad
    # de ABAJO de la columna y su destino (C5) esta ARRIBA, mientras SW va
    # derecho al inductor. En una capa no hay forma de evitarlo. Cede 5V
    # porque es continua: dar la vuelta no le cuesta nada. BOOST_SW conmuta
    # a ~1MHz y cada milimetro de mas es area de lazo radiando al lado de la
    # cadena analogica.
    #
    # Termina al aire a proposito (via=True + sin_via=True saltea la
    # verificacion del extremo sin poner via): sale del canal apretado del
    # SOT-563 con 0.20 y desde (66.60, 7.80) ya hay lugar para los 0.40 de
    # la netclass Power, asi que freerouting completa el resto.
    "U2_5V": dict(net="5V", capa="B.Cu", ancho=0.20, via=True, sin_via=True,
                  puntos=[(65.713, 6.50), (66.60, 6.50), (66.60, 7.80)]),
    # El nodo de conmutacion, en linea recta: 2.29mm, el minimo posible entre
    # los dos pads. Va a mano y no lo decide el ruteador porque es la pista
    # mas critica del boost — antes salia por donde encontraba hueco, y una
    # corrida daba 4.8mm y la siguiente nada.
    #
    # Pasa entre los pads 4 (GND) y 6 (5V) con 0.225mm de margen a cada uno,
    # sobre los 0.20 que pide la clase default. Ancho 0.20 en todo el tramo:
    # a 0.9A de pico son 5.6 miliohm y 4.5mW sobre 2.29mm, o sea nada, y mas
    # ancho no entra entre los pads vecinos.
    "U2_BOOST_SW": dict(net="BOOST_SW", capa="B.Cu", ancho=0.20, via=False,
                        puntos=[(65.713, 6.00), (68.000, 6.00)]),
}


# --------------------------------------------------------- puentes de tact
# Los tacts de 6mm tienen CUATRO patas que son DOS PARES cortocircuitados
# dentro del switch, y el footprint oficial de KiCad los numera 1,1,2,2.
#
# KiCad NO da por conectados dos pads solo porque compartan numero: si el
# ruteador llega a uno de los dos, el DRC reporta la net abierta. Y venia
# funcionando POR CASUALIDAD — en una corrida alcanzaba los dos pads en cinco
# de los seis tacts y en SW5 llegaba a uno solo. Nada lo garantizaba, y como
# el switch une las patas por dentro, la placa habria andado igual: el DRC
# estaba avisando de algo que no se ve en el banco. Con el puente explicito
# deja de depender de la suerte del ruteador.
#
# El cobre es redundante respecto del switch real, que es justamente por que
# es seguro ponerlo. Van en F.Cu, que es donde estan los tacts, y pasan por
# debajo del cuerpo: el par de senal esta a 4.5mm del par de masa, asi que la
# recta entre los dos pads no roza nada.
#
# El par de MASA no necesita puente: son pads THT y la zona de GND los une
# al plano por si misma.
PUENTES_TACT = {
    "SW5":  ("BTN_X",      (90.000, 42.500), (96.500, 42.500)),
    "SW6":  ("BTN_Y",      (77.500, 55.000), (84.000, 55.000)),
    "SW7":  ("BTN_A",     (102.500, 55.000), (109.000, 55.000)),
    "SW8":  ("BTN_B",      (90.000, 67.500), (96.500, 67.500)),
    "SW11": ("BTN_START",  (30.000, 27.390), (36.500, 27.390)),
    "SW12": ("BTN_SELECT", (90.000, 27.390), (96.500, 27.390)),
}
for _sw, (_net, _a, _b) in PUENTES_TACT.items():
    PISTAS["%s_PUENTE" % _sw] = dict(net=_net, capa="F.Cu", ancho=0.20,
                                     via=False, puntos=[_a, _b])


# Misma via que usa plane_vias.py: no estrena una medida de broca nueva.
VIA_D, VIA_DRILL = 0.5, 0.3


def mm(v):
    return pcbnew.FromMM(v)


def pads_de_la_net(board, net):
    out = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNumber() and p.GetNetname() == net:
                out.append((f"{fp.GetReference()}.{p.GetNumber()}",
                            pcbnew.ToMM(p.GetPosition().x),
                            pcbnew.ToMM(p.GetPosition().y)))
    return out


def verificar_extremos(board, net, pts, tol=0.01, solo_inicio=False):
    """Los dos extremos tienen que coincidir con pads de la net.

    Si el layout se mueve, esto avisa en vez de dejar una pista al aire que
    solo se descubre leyendo el DRC.
    """
    pads = pads_de_la_net(board, net)
    problemas = []
    extremos = (pts[0],) if solo_inicio else (pts[0], pts[-1])
    for extremo in extremos:
        hit = [n for n, x, y in pads
               if abs(x - extremo[0]) <= tol and abs(y - extremo[1]) <= tol]
        if not hit:
            cerca = min(pads, key=lambda p: (p[1] - extremo[0]) ** 2
                        + (p[2] - extremo[1]) ** 2) if pads else None
            problemas.append(
                f"{net}: el extremo {extremo} no cae sobre ningun pad"
                + (f" (el mas cercano es {cerca[0]} en ({cerca[1]:.3f}, "
                   f"{cerca[2]:.3f}))" if cerca else ""))
    return problemas


def ya_ruteada(board, clave, pts):
    """True si el PRIMER segmento de esta entrada ya existe en la placa.

    Se mira el segmento y no solo la net: el autorouter deja pistas de GND y
    5V por toda la placa, asi que preguntar "esta net tiene pistas?" daria
    siempre que si y no se pondria nunca lo que falta.
    """
    a, b = pts[0], pts[1]
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK":
            continue
        s, e = t.GetStart(), t.GetEnd()
        if (abs(pcbnew.ToMM(s.x) - a[0]) < 0.01
                and abs(pcbnew.ToMM(s.y) - a[1]) < 0.01
                and abs(pcbnew.ToMM(e.x) - b[0]) < 0.01
                and abs(pcbnew.ToMM(e.y) - b[1]) < 0.01):
            return True
    return False


def main():
    if not os.path.isfile(PCB):
        print(f"FALTA: {PCB}")
        return 1
    board = pcbnew.LoadBoard(PCB)

    puestas = saltadas = 0
    errores = []
    for clave, d in PISTAS.items():
        net, pts = d["net"], d["puntos"]
        errores += verificar_extremos(board, net, pts, solo_inicio=d["via"])
        nc = board.FindNet(net)
        if nc is None:
            errores.append(f"{clave}: la net {net} no existe en la placa")
            continue
        if ya_ruteada(board, clave, pts):
            print(f"{clave}: ya esta puesta, no se toca")
            saltadas += 1
            continue
        layer = board.GetLayerID(d["capa"])
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
            t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
            t.SetWidth(mm(d["ancho"]))
            t.SetLayer(layer)
            t.SetNet(nc)
            board.Add(t)
        if d["via"] and not d.get("sin_via"):
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(mm(pts[-1][0]), mm(pts[-1][1])))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(mm(VIA_D))
            v.SetDrill(mm(VIA_DRILL))
            v.SetNet(nc)
            board.Add(v)
        print(f"{clave}: {len(pts) - 1} segmento(s) en {d['capa']}"
              + (" + via al plano" if d["via"] and not d.get("sin_via")
                 else ""))
        puestas += 1

    if errores:
        print()
        for e in errores:
            print(f"ERROR: {e}")
        return 1

    pcbnew.SaveBoard(PCB, board)
    print(f"guardado: {PCB}  ({puestas} net(s) ruteada(s), {saltadas} ya estaban)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
