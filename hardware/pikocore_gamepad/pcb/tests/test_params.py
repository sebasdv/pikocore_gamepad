import unittest

import params
from checks import check_verified


class TestParams(unittest.TestCase):

    def test_todo_param_tiene_los_cuatro_campos(self):
        for name, p in params.ALL.items():
            self.assertIsInstance(p.value, float, f"{name}: value debe ser float")
            self.assertIsInstance(p.verified, bool, f"{name}: verified debe ser bool")
            self.assertTrue(p.note, f"{name}: note no puede estar vacia")
            self.assertTrue(p.gate, f"{name}: gate no puede estar vacia")

    def test_las_constantes_del_lcd_estan_declaradas(self):
        for name in ("LCD_PIN_ROW_Y", "LCD_HOLE_INSET", "LCD_BOARD_W",
                     "LCD_BOARD_H", "LCD_PIN1_X", "LCD_ACTIVE_W",
                     "LCD_ACTIVE_TOP"):
            self.assertIn(name, params.ALL)

    def test_las_cotas_leidas_del_drawing_estan_marcadas_verificadas(self):
        # Estas salen del drawing y ademas cierran por aritmetica exacta,
        # asi que no dependen de un calibre.
        self.assertTrue(params.ALL["LCD_BOARD_W"].verified)
        self.assertTrue(params.ALL["LCD_PIN1_X"].verified)

    def test_las_cotas_ambiguas_arrancan_sin_verificar(self):
        self.assertFalse(params.ALL["LCD_PIN_ROW_Y"].verified)
        self.assertFalse(params.ALL["LCD_HOLE_INSET"].verified)

    def test_la_geometria_del_header_cierra_con_el_ancho_de_la_placa(self):
        # 6.27 + 6*2.54 + 6.27 == 27.78 exacto. Si alguien toca un valor
        # sin tocar el otro, este test lo agarra.
        w = params.ALL["LCD_BOARD_W"].value
        x1 = params.ALL["LCD_PIN1_X"].value
        pitch = params.ALL["LCD_PIN_PITCH"].value
        self.assertAlmostEqual(x1 + 6 * pitch + x1, w, places=4)

    def test_los_margenes_verticales_del_vidrio_son_simetricos(self):
        h = params.ALL["LCD_BOARD_H"].value
        top = params.ALL["LCD_GLASS_TOP"].value
        gh = params.ALL["LCD_GLASS_H"].value
        self.assertAlmostEqual(h - top - gh, top, places=4)


class TestAccesorV(unittest.TestCase):
    """params.v() lo consumen gen_fp.py y placements.py. Su unico motivo de
    existir es fallar fuerte ante un typo, asi que ese es el comportamiento
    que hay que fijar."""

    def test_devuelve_el_valor_de_la_constante(self):
        self.assertAlmostEqual(params.v("LCD_BOARD_W"), 27.78, places=4)

    def test_falla_fuerte_con_un_nombre_desconocido(self):
        # Sin esto, un typo devolveria None y se propagaria silencioso a la
        # geometria del footprint.
        with self.assertRaises(KeyError):
            params.v("LCD_BOARD_WIDTH")


class TestCheckVerified(unittest.TestCase):

    def test_reporta_los_no_verificados(self):
        pend = check_verified.pendientes(params.ALL)
        self.assertIn("LCD_PIN_ROW_Y", pend)

    def test_pasa_cuando_todo_esta_verificado(self):
        from params import Param
        todos_ok = {"X": Param(1.0, True, "medido", "V-0")}
        self.assertEqual(check_verified.pendientes(todos_ok), [])


if __name__ == "__main__":
    unittest.main()
