import math
import unittest

import gen_fp
import params


class TestLcdFootprint(unittest.TestCase):
    """Modulo IPS 1.3in de 7 pines pasantes. Origen = pin 1 (GND), X a lo
    largo de la fila de pines, Y hacia el cuerpo. Las cotas esperadas son
    las del spec (dibujo del fabricante, 2026-10-17)."""

    def setUp(self):
        self.pads = gen_fp.lcd_pads()
        self.holes = gen_fp.lcd_holes()

    def caja(self, b, x0, y0, x1, y1):
        for k, esperado in zip(("x0", "y0", "x1", "y1"), (x0, y0, x1, y1)):
            self.assertAlmostEqual(b[k], esperado, places=3, msg=k)

    # ------------------------------------------------------------ pines
    def test_siete_pines_en_el_orden_del_modulo(self):
        nombres = [p["name"] for p in sorted(self.pads, key=lambda p: p["num"])]
        self.assertEqual(nombres,
                         ["GND", "VCC", "SCL", "SDA", "RES", "DC", "BLK"])

    def test_los_pines_van_de_0_a_15_24_en_y_0(self):
        for p in self.pads:
            self.assertAlmostEqual(p["x"], (p["num"] - 1) * 2.54, places=4)
            self.assertAlmostEqual(p["y"], 0.0, places=4)

    def test_el_pad_y_el_taladro_son_los_declarados(self):
        for p in self.pads:
            self.assertAlmostEqual(p["size"], params.v("LCD7_PIN_PAD"), places=4)
            self.assertAlmostEqual(p["drill"], params.v("LCD7_PIN_DRILL"), places=4)
            self.assertGreater(p["size"], p["drill"], f"pad {p['num']}: sin anillo")

    # ------------------------------------------------------------ contorno
    def test_el_contorno_es_el_del_spec(self):
        self.caja(gen_fp.lcd_outline(), -6.27, -1.27, 21.51, 37.95)

    def test_el_contorno_mide_lo_que_el_modulo(self):
        c = gen_fp.lcd_outline()
        self.assertAlmostEqual(c["x1"] - c["x0"], params.v("LCD7_BOARD_W"), places=3)
        self.assertAlmostEqual(c["y1"] - c["y0"], params.v("LCD7_BOARD_H"), places=3)

    # ------------------------------------------------------- area activa
    def test_el_area_activa_es_la_del_spec(self):
        self.caja(gen_fp.lcd_window(), -4.08, 5.06, 19.32, 28.46)

    def test_el_area_activa_no_pisa_la_fila_de_pines(self):
        w = gen_fp.lcd_window()
        self.assertGreater(w["y0"], max(p["y"] + p["size"] / 2 for p in self.pads))

    # ------------------------------------------------------- agujeros
    def test_los_agujeros_son_los_del_spec(self):
        pos = sorted((round(h["x"], 3), round(h["y"], 3)) for h in self.holes)
        self.assertEqual(pos, [(-3.77, 1.23), (-3.77, 35.45),
                               (19.01, 1.23), (19.01, 35.45)])
        for h in self.holes:
            self.assertAlmostEqual(h["drill"], params.v("LCD7_HOLE_DIA"), places=4)

    def test_los_agujeros_no_pisan_los_pads(self):
        for h in self.holes:
            for p in self.pads:
                d = math.hypot(h["x"] - p["x"], h["y"] - p["y"])
                self.assertGreater(d, h["drill"] / 2 + p["size"] / 2,
                                   f"agujero ({h['x']:.2f},{h['y']:.2f}) "
                                   f"pisa el pad {p['num']}")


if __name__ == "__main__":
    unittest.main()
