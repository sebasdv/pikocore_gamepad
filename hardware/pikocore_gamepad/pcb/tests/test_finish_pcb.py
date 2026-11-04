"""vias_sueltas() de finish_pcb sobre copias en memoria de la placa.

Necesita el python de KiCad (importa pcbnew), como el resto de la suite.
"""
import unittest

import pcbnew

import finish_pcb

mm = pcbnew.FromMM


def posiciones(vias):
    return {(v.GetPosition().x, v.GetPosition().y) for v in vias}


def via_de(board, net, x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetWidth(pcbnew.F_Cu, mm(0.5))   # KiCad 9: ancho por capa (sin capa, assert)
    v.SetDrill(mm(0.3))
    v.SetNetCode(board.GetNetcodeFromNetname(net))
    board.Add(v)
    return (v.GetPosition().x, v.GetPosition().y)


class TestViasSueltas(unittest.TestCase):
    def setUp(self):
        self.b = pcbnew.LoadBoard(finish_pcb.PCB)
        self.b.BuildConnectivity()

    def test_la_placa_commiteada_no_tiene_vias_sueltas(self):
        self.assertEqual(finish_pcb.vias_sueltas(self.b), [])

    def test_una_via_en_medio_de_una_pista_cuenta_esa_capa(self):
        # Una via de GND sobre el medio de una pista de GND exterior toca esa
        # capa aunque la pista no termine ahi, mas el plano GND: no es suelta.
        # Mirando solo extremos se borraba, y la pista caia despues.
        pistas = [t for t in self.b.GetTracks()
                  if t.GetClass() == "PCB_TRACK" and t.GetNetname() == "GND"
                  and t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu)
                  and t.GetLength() >= mm(2)]
        self.assertTrue(pistas, "la placa no tiene pistas de GND exteriores de 2 mm")
        t = pistas[0]
        c = (t.GetStart() + t.GetEnd()) / 2
        pos = via_de(self.b, "GND", pcbnew.ToMM(c.x), pcbnew.ToMM(c.y))
        self.assertNotIn(pos, posiciones(finish_pcb.vias_sueltas(self.b)))

    def test_una_via_sin_pista_ni_pad_es_suelta(self):
        # Solo el plano GND la contiene: una capa, suelta.
        pos = via_de(self.b, "GND", 50.0, 33.0)
        self.assertIn(pos, posiciones(finish_pcb.vias_sueltas(self.b)))


if __name__ == "__main__":
    unittest.main()
