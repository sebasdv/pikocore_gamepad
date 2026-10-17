import math
import os
import re
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


class TestLcdFootprintArchivo(unittest.TestCase):
    """El .kicad_mod que carga gen_pcb.py, pad por pad. Es el archivo el que
    va a la placa: que lcd_pads() este bien no sirve si el archivo quedo
    viejo o lo escribio otra cosa."""

    PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "lib", "gamesetup_fp.pretty",
                        "LCD_ST7789_240x240_7P.kicad_mod")
    PAD = re.compile(r'\(pad\s+"([^"]*)"\s+(\S+)\s+(\S+)\s+\(at\s+([-\d.]+)\s+([-\d.]+)\)'
                     r'\s+\(size\s+([-\d.]+)\s+([-\d.]+)\)\s+\(drill\s+([-\d.]+)\)'
                     r'.*?\(pinfunction\s+"([^"]*)"\)')
    HOLES = [(-3.77, 1.23), (-3.77, 35.45), (19.01, 1.23), (19.01, 35.45)]

    def setUp(self):
        with open(self.PATH, encoding="utf-8") as f:
            self.txt = f.read()

    def test_esta_al_dia_con_gen_fp(self):
        self.assertEqual(self.txt, gen_fp.build_lcd(),
                         "correr gen_fp.py: el archivo no es el que sale de params.py")

    def test_siete_pads_pasantes_pin_por_pin(self):
        pads = self.PAD.findall(self.txt)
        self.assertEqual(len(pads), 7)
        nombres = ["GND", "VCC", "SCL", "SDA", "RES", "DC", "BLK"]
        for i, (num, tipo, forma, x, y, w, h, drill, fn) in enumerate(pads):
            self.assertEqual(num, str(i + 1))
            self.assertEqual(tipo, "thru_hole", f"pad {num}")
            self.assertEqual(forma, "rect" if i == 0 else "circle", f"pad {num}")
            self.assertAlmostEqual(float(x), i * 2.54, places=3, msg=f"pad {num}")
            self.assertAlmostEqual(float(y), 0.0, places=3, msg=f"pad {num}")
            self.assertEqual((float(w), float(h)), (1.7, 1.7), f"pad {num}")
            self.assertAlmostEqual(float(drill), 1.0, places=3, msg=f"pad {num}")
            self.assertEqual(fn, nombres[i], f"pad {num}")

    def test_no_hay_pads_npth_ni_otros_pads(self):
        # Los agujeros del modulo NO se taladran: el modulo se sostiene por
        # sus pines. Solo van dibujados.
        self.assertNotIn("np_thru_hole", self.txt)
        self.assertEqual(self.txt.count("(pad "), 7)

    def test_los_agujeros_van_solo_como_dibujo(self):
        circ = re.findall(r'\(fp_circle\s+\(center\s+([-\d.]+)\s+([-\d.]+)\)\s+'
                          r'\(end\s+([-\d.]+)\s+[-\d.]+\).*?\(layer\s+"([^"]+)"\)',
                          self.txt)
        for capa in ("Cmts.User", "F.Fab"):
            de_capa = [(float(x), float(y), float(ex)) for x, y, ex, c in circ
                       if c == capa]
            self.assertEqual(sorted((x, y) for x, y, _ in de_capa), self.HOLES, capa)
            for x, _, ex in de_capa:
                self.assertAlmostEqual(ex - x, 1.0, places=3, msg=capa)  # radio

    def _puntos(self, capa):
        out = []
        for m in re.finditer(r'\(fp_line\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+'
                             r'\(end\s+([-\d.]+)\s+([-\d.]+)\)[^\n]*\(layer\s+"'
                             + re.escape(capa) + r'"\)', self.txt):
            v = [float(g) for g in m.groups()]
            out += [(v[0], v[1]), (v[2], v[3])]
        return out

    def test_el_contorno_va_en_fab_y_courtyard(self):
        for capa in ("F.Fab", "F.CrtYd"):
            pts = self._puntos(capa)
            self.assertTrue(pts, capa)
            self.assertEqual((min(x for x, _ in pts), min(y for _, y in pts),
                              max(x for x, _ in pts), max(y for _, y in pts)),
                             (-6.27, -1.27, 21.51, 37.95), capa)

    def test_el_area_activa_va_en_cmts(self):
        pts = self._puntos("Cmts.User")
        self.assertIn((-4.08, 5.06), pts)
        self.assertIn((19.32, 28.46), pts)


if __name__ == "__main__":
    unittest.main()
