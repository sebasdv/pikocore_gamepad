import unittest

from checks import check_refs


class TestDuplicados(unittest.TestCase):

    def test_no_reporta_nada_sin_duplicados(self):
        self.assertEqual(check_refs.duplicados(["R1", "R2", "C1"]), [])

    def test_una_lista_vacia_no_tiene_duplicados(self):
        self.assertEqual(check_refs.duplicados([]), [])

    def test_detecta_un_duplicado(self):
        self.assertEqual(check_refs.duplicados(["R1", "C19", "R2", "C19"]), ["C19"])

    def test_detecta_varios_duplicados_ordenados(self):
        self.assertEqual(
            check_refs.duplicados(["C19", "R1", "C19", "R1", "U5"]),
            ["C19", "R1"])

    def test_no_confunde_prefijos_distintos_con_el_mismo_numero(self):
        self.assertEqual(check_refs.duplicados(["R1", "C1", "U1", "SW1"]), [])

    def test_reporta_una_sola_vez_una_referencia_repetida_tres_veces(self):
        self.assertEqual(check_refs.duplicados(["C19", "C19", "C19"]), ["C19"])


class TestHuecos(unittest.TestCase):

    def test_detecta_un_hueco_en_la_numeracion(self):
        # No es un error, pero un hueco suele significar un componente que se
        # dio de baja y dejo nets huerfanas: vale reportarlo.
        self.assertEqual(check_refs.huecos(["R1", "R2", "R4"]), ["R3"])

    def test_no_reporta_huecos_en_una_serie_completa(self):
        self.assertEqual(check_refs.huecos(["R1", "R2", "R3"]), [])

    def test_los_huecos_se_calculan_por_prefijo(self):
        self.assertEqual(check_refs.huecos(["R1", "R2", "C1", "C3"]), ["C2"])

    def test_una_serie_que_no_arranca_en_uno_no_es_un_hueco(self):
        # U10/U11/U12 son los expansores; que no exista U1..U9 en ese rango no
        # es un hueco, porque los huecos se miden entre el minimo y el maximo
        # de cada prefijo.
        self.assertEqual(check_refs.huecos(["U10", "U11", "U12"]), [])

    def test_detecta_varios_huecos_seguidos(self):
        self.assertEqual(check_refs.huecos(["C1", "C5"]), ["C2", "C3", "C4"])

    def test_ignora_referencias_sin_numero(self):
        # No debe romperse con una referencia que no siga el patron letra+digito.
        self.assertEqual(check_refs.huecos(["GND", "R1", "R2"]), [])

    def test_un_solo_componente_no_tiene_huecos(self):
        self.assertEqual(check_refs.huecos(["U1"]), [])


if __name__ == "__main__":
    unittest.main()
