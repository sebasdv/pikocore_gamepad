import math
import unittest

import gen_fp
import params


class TestLcdFootprint(unittest.TestCase):

    def setUp(self):
        self.pads = gen_fp.lcd_pads()
        self.holes = gen_fp.lcd_holes()

    # ------------------------------------------------------------ header
    def test_tiene_siete_pads_de_senal(self):
        self.assertEqual(len(self.pads), 7)

    def test_los_pads_estan_numerados_del_uno_al_siete(self):
        self.assertEqual(sorted(p["num"] for p in self.pads), list(range(1, 8)))

    def test_el_orden_de_los_pines_es_el_del_modulo(self):
        nombres = [p["name"] for p in sorted(self.pads, key=lambda p: p["num"])]
        self.assertEqual(nombres,
                         ["GND", "VCC", "SCL", "SDA", "RES", "DC", "BLK"])

    def test_el_paso_entre_pads_es_el_declarado(self):
        xs = sorted(p["x"] for p in self.pads)
        for a, b in zip(xs, xs[1:]):
            self.assertAlmostEqual(b - a, params.v("LCD_PIN_PITCH"), places=4)

    def test_los_pads_estan_todos_a_la_misma_altura(self):
        self.assertEqual(len({round(p["y"], 4) for p in self.pads}), 1)

    def test_el_origen_del_footprint_es_el_pad_1(self):
        p1 = next(p for p in self.pads if p["num"] == 1)
        self.assertAlmostEqual(p1["x"], 0.0, places=4)
        self.assertAlmostEqual(p1["y"], 0.0, places=4)

    def test_el_taladro_de_los_pads_deja_pasar_un_header_de_2_54(self):
        # Un header macho estandar tiene poste de 0.64mm de lado (diagonal
        # 0.9mm). Menos de 0.9 de taladro y no entra.
        for p in self.pads:
            self.assertGreaterEqual(p["drill"], 0.9, f"pad {p['num']}")
            self.assertGreater(p["size"], p["drill"], f"pad {p['num']}: sin anillo")

    # ------------------------------------------------- agujeros de montaje
    def test_tiene_cuatro_agujeros_de_montaje(self):
        self.assertEqual(len(self.holes), 4)

    def test_los_agujeros_son_de_dos_milimetros(self):
        for h in self.holes:
            self.assertAlmostEqual(h["drill"], params.v("LCD_HOLE_DIA"), places=4)

    def test_los_agujeros_forman_un_rectangulo(self):
        xs = sorted(set(round(h["x"], 3) for h in self.holes))
        ys = sorted(set(round(h["y"], 3) for h in self.holes))
        self.assertEqual(len(xs), 2)
        self.assertEqual(len(ys), 2)

    def test_la_separacion_de_agujeros_deriva_del_ancho_del_modulo(self):
        inset = params.v("LCD_HOLE_INSET")
        esperado = params.v("LCD_BOARD_W") - 2 * inset
        xs = sorted(set(round(h["x"], 3) for h in self.holes))
        self.assertAlmostEqual(xs[1] - xs[0], esperado, places=3)

    def test_la_separacion_vertical_de_agujeros_deriva_del_alto(self):
        inset = params.v("LCD_HOLE_INSET")
        esperado = params.v("LCD_BOARD_H") - 2 * inset
        ys = sorted(set(round(h["y"], 3) for h in self.holes))
        self.assertAlmostEqual(ys[1] - ys[0], esperado, places=3)

    def test_los_agujeros_caen_dentro_del_contorno(self):
        c = gen_fp.lcd_outline()
        for h in self.holes:
            r = h["drill"] / 2
            self.assertGreaterEqual(h["x"] - r, c["x0"])
            self.assertLessEqual(h["x"] + r, c["x1"])
            self.assertGreaterEqual(h["y"] - r, c["y0"])
            self.assertLessEqual(h["y"] + r, c["y1"])

    def test_los_agujeros_no_pisan_los_pads(self):
        # Si se tocan, el taladro se come el anillo de cobre y el pad queda
        # sin conexion. Es el tipo de error que solo se ve con la placa hecha.
        for h in self.holes:
            for p in self.pads:
                d = math.hypot(h["x"] - p["x"], h["y"] - p["y"])
                minimo = h["drill"] / 2 + p["size"] / 2
                self.assertGreater(d, minimo,
                                   f"agujero en ({h['x']:.2f},{h['y']:.2f}) "
                                   f"pisa el pad {p['num']}")

    # ------------------------------------------------- ventana del panel
    def test_la_ventana_del_panel_es_cuadrada(self):
        w = gen_fp.lcd_window()
        self.assertAlmostEqual(w["x1"] - w["x0"], w["y1"] - w["y0"], places=3)

    def test_la_ventana_mide_lo_que_el_area_activa(self):
        w = gen_fp.lcd_window()
        self.assertAlmostEqual(w["x1"] - w["x0"],
                               params.v("LCD_ACTIVE_W"), places=3)

    def test_la_ventana_cae_dentro_del_contorno_del_modulo(self):
        w = gen_fp.lcd_window()
        c = gen_fp.lcd_outline()
        self.assertGreaterEqual(w["x0"], c["x0"])
        self.assertLessEqual(w["x1"], c["x1"])
        self.assertGreaterEqual(w["y0"], c["y0"])
        self.assertLessEqual(w["y1"], c["y1"])

    def test_la_ventana_esta_centrada_en_el_ancho_del_modulo(self):
        w = gen_fp.lcd_window()
        c = gen_fp.lcd_outline()
        izq = w["x0"] - c["x0"]
        der = c["x1"] - w["x1"]
        self.assertAlmostEqual(izq, der, places=3)

    def test_la_ventana_no_pisa_la_fila_de_pines(self):
        # El header queda arriba del vidrio. Si se solapan, el recorte del
        # panel dejaria los pines a la vista.
        w = gen_fp.lcd_window()
        self.assertGreater(w["y0"], max(p["y"] for p in self.pads))

    # ------------------------------------------------------------ contorno
    def test_el_contorno_mide_lo_que_el_modulo(self):
        c = gen_fp.lcd_outline()
        self.assertAlmostEqual(c["x1"] - c["x0"], params.v("LCD_BOARD_W"), places=3)
        self.assertAlmostEqual(c["y1"] - c["y0"], params.v("LCD_BOARD_H"), places=3)

    def test_todos_los_pads_caen_dentro_del_contorno(self):
        c = gen_fp.lcd_outline()
        for p in self.pads:
            self.assertGreaterEqual(p["x"], c["x0"], f"pad {p['num']}")
            self.assertLessEqual(p["x"], c["x1"], f"pad {p['num']}")


class TestGeneracionDelArchivo(unittest.TestCase):

    def test_el_kicad_mod_declara_los_once_pads(self):
        # 7 de senal + 4 NPTH de montaje.
        s = gen_fp.build_lcd()
        self.assertEqual(s.count("(pad "), 11)

    def test_los_agujeros_de_montaje_son_no_pasantes(self):
        # np_thru_hole: sin cobre. Si fueran thru_hole normales, el DRC los
        # trataria como pads sin net.
        s = gen_fp.build_lcd()
        self.assertEqual(s.count("np_thru_hole"), 4)

    def test_el_pad_1_es_rectangular(self):
        # Convencion universal: el pad 1 se marca cuadrado para que la
        # orientacion sea evidente al soldar.
        s = gen_fp.build_lcd()
        self.assertIn('(pad "1" thru_hole rect', s)

    def test_el_archivo_abre_y_cierra_parentesis(self):
        s = gen_fp.build_lcd()
        self.assertEqual(s.count("("), s.count(")"))


if __name__ == "__main__":
    unittest.main()
