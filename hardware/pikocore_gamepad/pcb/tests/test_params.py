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

    def test_las_cotas_del_lcd_salen_del_modelo_del_modulo(self):
        # Las dos arrancaron sin verificar porque el drawing del vendedor no
        # las acota: LCD_PIN_ROW_Y salia de escalar el dibujo a ojo (erraba
        # 0.33mm) y LCD_HOLE_INSET tenia dos candidatos, 2.19 y 2.5.
        # Se cerraron midiendo el STEP del modulo, y ahi se vio que 2.19 era
        # el margen del AREA ACTIVA, no la posicion del agujero.
        self.assertTrue(params.ALL["LCD_PIN_ROW_Y"].verified)
        self.assertTrue(params.ALL["LCD_HOLE_INSET"].verified)
        self.assertAlmostEqual(params.v("LCD_PIN_ROW_Y"), 1.27, places=2)
        self.assertAlmostEqual(params.v("LCD_HOLE_INSET"), 2.50, places=2)

    def test_el_margen_del_area_activa_no_es_el_inset_del_agujero(self):
        # (27.78 - 23.40)/2 = 2.19 EXACTO. Ese numero existe y es correcto,
        # pero acota el area activa — confundirlo con el agujero fue el error
        # que arrastraba V1.
        margen = (params.v("LCD_BOARD_W") - params.v("LCD_ACTIVE_W")) / 2
        self.assertAlmostEqual(margen, 2.19, places=2)
        self.assertNotAlmostEqual(margen, params.v("LCD_HOLE_INSET"), places=2)

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
        # Con un Param falso, para no depender de que quede alguno sin
        # verificar en el proyecto real — hoy no queda ninguno.
        from params import Param
        falso = {"OK": Param(1.0, True, "medido", "V-0"),
                 "PENDIENTE": Param(2.0, False, "sin medir", "V-9")}
        pend = check_verified.pendientes(falso)
        self.assertEqual(pend, ["PENDIENTE"])

    def test_hoy_no_queda_ninguno_pendiente(self):
        # G-0 en verde: es lo que habilita a gen_fab.py a generar sin --force.
        self.assertEqual(check_verified.pendientes(params.ALL), [])

    def test_pasa_cuando_todo_esta_verificado(self):
        from params import Param
        todos_ok = {"X": Param(1.0, True, "medido", "V-0")}
        self.assertEqual(check_verified.pendientes(todos_ok), [])


if __name__ == "__main__":
    unittest.main()
