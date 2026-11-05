"""Referencias impresas de las piezas que suelda el usuario (2026-11-05).

Las piezas sin codigo LCSC las compra y suelda el usuario: llevan su
referencia en la serigrafia de su cara, para ubicarlas al armar. El resto lo
coloca JLCPCB con el CPL y su referencia sigue en Fab, que no se imprime.
La serigrafia que se pisa con otra la caza el DRC (silk_overlap).
"""
import unittest

import pcbnew

import netlist
from checks import check_placement as cp

A_MANO = [i[1] for i in netlist.INSTANCES if not i[6].get("LCSC")]


class TestReferenciasAMano(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = pcbnew.LoadBoard(cp.PCB)

    def test_son_las_18_piezas_sin_lcsc(self):
        self.assertEqual(len(A_MANO), 18, A_MANO)

    def test_la_referencia_esta_en_la_serigrafia_de_su_cara(self):
        for ref in A_MANO:
            fp = self.board.FindFootprintByReference(ref)
            f = fp.Reference()
            capa = pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS
            self.assertEqual(f.GetLayer(), capa, ref)
            self.assertTrue(f.IsVisible(), ref)
            # En el dorso va espejada: se lee al dar vuelta la placa.
            self.assertEqual(f.IsMirrored(), fp.IsFlipped(), ref)
            self.assertAlmostEqual(pcbnew.ToMM(f.GetTextHeight()), 1.0, places=2, msg=ref)
            bb = f.GetBoundingBox()
            self.assertGreater(bb.GetWidth(), bb.GetHeight(), f"{ref} no queda horizontal")

    def test_la_referencia_queda_dentro_de_la_placa(self):
        borde = self.board.GetBoardEdgesBoundingBox()
        borde.Inflate(-pcbnew.FromMM(0.5))
        for ref in A_MANO:
            bb = self.board.FindFootprintByReference(ref).Reference().GetBoundingBox()
            self.assertTrue(borde.Contains(bb), ref)

    def test_la_referencia_no_pisa_pads_de_su_cara(self):
        for ref in A_MANO:
            fp = self.board.FindFootprintByReference(ref)
            cu = pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu
            bb = fp.Reference().GetBoundingBox()
            pisa = [f"{o.GetReference()}.{p.GetNumber()}"
                    for o in self.board.GetFootprints() for p in o.Pads()
                    if p.IsOnLayer(cu) and bb.Intersects(p.GetBoundingBox())]
            self.assertEqual(pisa, [], ref)

    def test_las_demas_referencias_siguen_en_fab(self):
        for fp in self.board.GetFootprints():
            if fp.GetReference() not in A_MANO:
                self.assertIn(fp.Reference().GetLayer(), (pcbnew.F_Fab, pcbnew.B_Fab),
                              fp.GetReference())


if __name__ == "__main__":
    unittest.main()
