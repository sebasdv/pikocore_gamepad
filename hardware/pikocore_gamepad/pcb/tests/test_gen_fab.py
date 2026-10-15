"""CPL para JLCPCB: rotacion espejada en el dorso y correcciones por footprint.

Los valores esperados salen de ajustar los pads EasyEDA de cada parte LCSC
contra los pads reales de la placa (2026-10-15), no de la formula misma.
"""
import unittest

from gen_fab import jlc_pos


class TestJlcPos(unittest.TestCase):
    def test_dorso_sin_correccion_espeja(self):
        # D1, SOD-123F en el dorso a 0: JLC lo quiere a 180.
        self.assertEqual(jlc_pos("D_SOD-123F", 11.0, -26.5, 0.0, True),
                         (11.0, -26.5, 180.0))

    def test_soic_easyeda_suma_270(self):
        # U6 en el dorso a -90: el ajuste geometrico dio 180.
        _, _, rot = jlc_pos("generic_soic127p790x195-8", 0, 0, -90.0, True)
        self.assertEqual(rot, 180.0)
        # En la cara de arriba la misma pieza iria a rot + 270.
        _, _, rot = jlc_pos("generic_soic127p790x195-8", 0, 0, 0.0, False)
        self.assertEqual(rot, 270.0)

    def test_usb_c_centro_corrido(self):
        # J2 en el dorso a 90: el centro de JLC queda 1.335mm a la derecha.
        x, y, rot = jlc_pos("USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A",
                            4.6, -19.4, 90.0, True)
        self.assertAlmostEqual(x, 5.935)
        self.assertAlmostEqual(y, -19.4)
        self.assertEqual(rot, 90.0)


if __name__ == "__main__":
    unittest.main()
