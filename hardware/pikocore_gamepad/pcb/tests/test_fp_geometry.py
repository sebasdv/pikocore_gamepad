import unittest

import gen_fp
import params


class TestPanelFootprint(unittest.TestCase):
    """Panel desnudo LCD_LH133T_24P: contorno, area activa y cola del FPC.
    Sin pads: lo electrico va por el conector J4, que se importa de LCSC."""

    def test_el_origen_es_el_centro_del_area_activa(self):
        w = gen_fp.panel_window()
        self.assertAlmostEqual(w["x0"], -w["x1"], places=4)
        self.assertAlmostEqual(w["y0"], -w["y1"], places=4)

    def test_la_ventana_es_cuadrada_y_mide_el_area_activa(self):
        w = gen_fp.panel_window()
        self.assertAlmostEqual(w["x1"] - w["x0"], params.v("PANEL_AA"), places=4)
        self.assertAlmostEqual(w["y1"] - w["y0"], params.v("PANEL_AA"), places=4)

    def test_el_contorno_mide_lo_que_el_backlight(self):
        c = gen_fp.panel_outline()
        self.assertAlmostEqual(c["x1"] - c["x0"], params.v("PANEL_BL_W"), places=3)
        self.assertAlmostEqual(c["y1"] - c["y0"], params.v("PANEL_BL_H"), places=3)

    def test_la_ventana_cae_dentro_del_contorno_con_sus_margenes(self):
        c, w = gen_fp.panel_outline(), gen_fp.panel_window()
        self.assertAlmostEqual(w["x0"] - c["x0"], params.v("PANEL_AA_OFF_X"), places=4)
        self.assertAlmostEqual(c["x1"] - w["x1"], params.v("PANEL_AA_OFF_X"), places=4)
        self.assertAlmostEqual(w["y0"] - c["y0"], params.v("PANEL_AA_OFF_TOP"), places=4)
        # La franja del driver (lado del FPC) es la ancha, y esta ABAJO (+Y).
        self.assertGreater(c["y1"] - w["y1"], params.v("PANEL_AA_OFF_TOP"))

    def test_el_fpc_sale_por_abajo_y_mide_lo_declarado(self):
        c, f = gen_fp.panel_outline(), gen_fp.panel_fpc()
        self.assertAlmostEqual(f["y0"], c["y1"], places=4)
        self.assertAlmostEqual(f["y1"] - f["y0"], params.v("PANEL_FPC_LEN"), places=4)
        self.assertAlmostEqual(f["x1"] - f["x0"], params.v("PANEL_FPC_W"), places=4)
        self.assertAlmostEqual(f["x0"], -f["x1"], places=4)


class TestGeneracionDelArchivo(unittest.TestCase):

    def test_el_kicad_mod_no_declara_pads(self):
        # Pieza pegada: un pad aca seria un pad sin net en el DRC.
        self.assertEqual(gen_fp.build_panel().count("(pad "), 0)

    def test_queda_fuera_del_cpl_pero_dentro_del_bom(self):
        # La pega el usuario (no va al pick-and-place) pero hay que comprarla.
        # exclude_from_bom ademas choca con el simbolo (in_bom yes) y el DRC
        # con --schematic-parity lo reporta.
        s = gen_fp.build_panel()
        self.assertIn("exclude_from_pos_files", s)
        self.assertNotIn("exclude_from_bom", s)

    def test_tiene_courtyard_y_ventana(self):
        s = gen_fp.build_panel()
        self.assertEqual(s.count('(layer "F.CrtYd")'), 4)
        # contorno + ventana + cola del FPC, 4 lineas cada uno
        self.assertEqual(s.count('(layer "Cmts.User")'), 12)

    def test_el_archivo_abre_y_cierra_parentesis(self):
        s = gen_fp.build_panel()
        self.assertEqual(s.count("("), s.count(")"))


if __name__ == "__main__":
    unittest.main()
