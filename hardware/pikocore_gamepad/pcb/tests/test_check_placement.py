"""check_placement sobre copias en memoria de la placa (la commiteada no se toca).

Necesita el python de KiCad (importa pcbnew), como el resto de la suite.
"""
import contextlib
import io
import unittest

import pcbnew

from checks import check_placement as cp

mm = pcbnew.FromMM


def correr(board):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = cp.main(board)
    return rc, out.getvalue()


def cargar():
    return pcbnew.LoadBoard(cp.PCB)


class TestBajoLaPantalla(unittest.TestCase):
    def test_la_placa_commiteada_pasa(self):
        rc, out = correr(cargar())
        self.assertEqual(rc, 0, out)

    def test_falla_si_falta_j4(self):
        b = cargar()
        b.Remove(b.FindFootprintByReference("J4"))
        rc, out = correr(b)
        self.assertEqual(rc, 1)
        self.assertIn("FALTA J4", out)

    def test_pata_pasante_bajo_la_pantalla(self):
        b = cargar()
        b.FindFootprintByReference("SW4").SetPosition(pcbnew.VECTOR2I(mm(50), mm(25)))
        rc, out = correr(b)
        self.assertEqual(rc, 1)
        self.assertIn("PATA BAJO LA PANTALLA: SW4.", out)

    def test_pad_smd_del_frente_bajo_la_pantalla(self):
        b = cargar()
        fp = pcbnew.FOOTPRINT(b)
        fp.SetReference("U99")
        pad = pcbnew.PAD(fp)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetLayerSet(pad.SMDMask())
        pad.SetSize(pcbnew.VECTOR2I(mm(1), mm(1)))
        pad.SetNumber("1")
        fp.Add(pad)
        b.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I(mm(50), mm(25)))
        rc, out = correr(b)
        self.assertEqual(rc, 1)
        self.assertIn("BAJO LA PANTALLA: U99", out)

    def test_courtyard_del_frente_bajo_la_pantalla(self):
        b = cargar()
        fp = pcbnew.FOOTPRINT(b)
        fp.SetReference("U98")
        r = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_RECT)
        r.SetStart(pcbnew.VECTOR2I(mm(34), mm(20)))
        r.SetEnd(pcbnew.VECTOR2I(mm(37), mm(23)))   # el cuerpo arranca en x 36.11
        r.SetLayer(pcbnew.F_CrtYd)
        fp.Add(r)
        b.Add(fp)
        rc, out = correr(b)
        self.assertEqual(rc, 1)
        self.assertIn("BAJO LA PANTALLA: U98", out)

    def test_courtyard_del_dorso_no_cuenta(self):
        b = cargar()
        fp = pcbnew.FOOTPRINT(b)
        fp.SetReference("U97")
        r = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_RECT)
        r.SetStart(pcbnew.VECTOR2I(mm(45), mm(20)))
        r.SetEnd(pcbnew.VECTOR2I(mm(48), mm(23)))
        r.SetLayer(pcbnew.B_CrtYd)
        fp.Add(r)
        b.Add(fp)
        rc, out = correr(b)
        self.assertNotIn("U97", out)
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
