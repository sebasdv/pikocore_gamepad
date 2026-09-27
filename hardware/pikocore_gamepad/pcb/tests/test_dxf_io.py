import unittest

import dxf_io


def group_values(dxf_text, code):
    """Valores del grupo DXF `code`.

    El formato DXF alterna lineas: el codigo de grupo en una, su valor en la
    siguiente. Se parsea de verdad en vez de buscar substrings, porque una
    asercion por substring sobre coordenadas no distingue " 20" (codigo de
    grupo) de "20.0000" (valor) y da falsos positivos.
    """
    lines = [l.rstrip() for l in dxf_text.splitlines()]
    out = []
    for i in range(len(lines) - 1):
        if lines[i].strip() == str(code):
            try:
                out.append(float(lines[i + 1]))
            except ValueError:
                pass
    return out


def shift_layer_x(dxf_text, layer, dx):
    """Simula que el usuario movio una capa entera en Rhino.

    Suma dx a cada coordenada X (grupos 10 y 11) de las entidades de esa capa.
    Mover SOLO una de las dos lineas de la cruz no sirve como simulacion: el
    lector exige que los dos brazos se crucen en su punto medio, asi que una
    cruz a medio mover no es una cruz y no se encuentra.

    DXF alterna estrictamente codigo/valor, asi que se camina de a dos.
    """
    lines = dxf_text.splitlines(keepends=True)
    out = list(lines)
    cur_layer = None
    for i in range(0, len(lines) - 1, 2):
        code = lines[i].strip()
        val = lines[i + 1].strip()
        if code == "8":
            cur_layer = val
        elif code in ("10", "11") and cur_layer == layer:
            out[i + 1] = f"{float(val) + dx:.4f}\n"
    return "".join(out)


class TestEscritura(unittest.TestCase):

    def test_una_cruz_produce_dos_lineas(self):
        s = dxf_io.cross("SW1", 10.0, 20.0, arm=3.0)
        self.assertEqual(s.count("LINE"), 2)

    def test_la_cruz_invierte_el_signo_de_y(self):
        # KiCad tiene Y hacia abajo y DXF hacia arriba: el writer debe negar Y
        # o el layout aparece espejado verticalmente en Rhino, y es facil no
        # notarlo hasta que la placa esta fabricada.
        s = dxf_io.cross("SW1", 10.0, 20.0, arm=3.0)
        ys = group_values(s, 20) + group_values(s, 21)
        self.assertTrue(ys, "no se emitio ninguna coordenada Y")
        self.assertTrue(all(y < 0 for y in ys), f"Y sin negar: {ys}")
        self.assertIn(-20.0, ys)

    def test_la_cruz_no_toca_el_signo_de_x(self):
        s = dxf_io.cross("SW1", 10.0, 20.0, arm=3.0)
        xs = group_values(s, 10) + group_values(s, 11)
        self.assertTrue(all(x > 0 for x in xs), f"X alterada: {xs}")
        self.assertIn(10.0, xs)

    def test_la_cruz_esta_centrada_en_el_punto_pedido(self):
        # El centro se recupera de la interseccion, asi que los brazos tienen
        # que ser simetricos o parse_dxf devuelve una posicion corrida.
        s = dxf_io.cross("SW1", 10.0, 20.0, arm=3.0)
        xs = group_values(s, 10) + group_values(s, 11)
        ys = group_values(s, 20) + group_values(s, 21)
        self.assertAlmostEqual((min(xs) + max(xs)) / 2, 10.0, places=4)
        self.assertAlmostEqual((min(ys) + max(ys)) / 2, -20.0, places=4)

    def test_un_rectangulo_produce_cuatro_lineas(self):
        s = dxf_io.rect("U1", 0.0, 0.0, 10.0, 5.0)
        self.assertEqual(s.count("LINE"), 4)

    def test_el_documento_completo_abre_y_cierra_secciones(self):
        doc = dxf_io.build_document(
            outline=(0.0, 0.0, 90.0, 130.0),
            items=[dxf_io.Item("SW1", 10.0, 20.0, (8.0, 18.0, 12.0, 22.0), False)],
        )
        self.assertTrue(doc.startswith("  0\nSECTION"))
        self.assertTrue(doc.rstrip().endswith("EOF"))
        self.assertIn("ENDSEC", doc)

    def test_el_documento_declara_una_capa_por_item_mas_el_contorno(self):
        doc = dxf_io.build_document(
            outline=(0.0, 0.0, 90.0, 130.0),
            items=[
                dxf_io.Item("SW1", 10.0, 20.0, (8.0, 18.0, 12.0, 22.0), False),
                dxf_io.Item("U1", 40.0, 60.0, (30.0, 50.0, 50.0, 70.0), True),
            ],
        )
        self.assertIn("\nBOARD_OUTLINE\n", doc)
        self.assertIn("\nSW1\n", doc)
        self.assertIn("\nU1\n", doc)

    def test_marca_los_componentes_del_dorso(self):
        doc = dxf_io.build_document(
            outline=(0.0, 0.0, 90.0, 130.0),
            items=[dxf_io.Item("U1", 40.0, 60.0, (30.0, 50.0, 50.0, 70.0), True)],
        )
        self.assertIn("DORSO", doc)

    def test_no_marca_como_dorso_los_del_frente(self):
        doc = dxf_io.build_document(
            outline=(0.0, 0.0, 90.0, 130.0),
            items=[dxf_io.Item("SW1", 10.0, 20.0, (8.0, 18.0, 12.0, 22.0), False)],
        )
        self.assertNotIn("DORSO", doc)

    def test_declara_milimetros_como_unidad(self):
        # $INSUNITS = 4 es milimetros. Si Rhino abre el DXF en pulgadas, el
        # layout entero entra 25.4x mas chico.
        doc = dxf_io.build_document(outline=(0.0, 0.0, 90.0, 130.0), items=[])
        self.assertIn("$INSUNITS", doc)
        self.assertIn("\n 70\n4\n", doc)


class TestLectura(unittest.TestCase):

    def _doc(self):
        return dxf_io.build_document(
            outline=(0.0, 0.0, 90.0, 130.0),
            items=[
                dxf_io.Item("SW1", 10.0, 20.0, (8.0, 18.0, 12.0, 22.0), False),
                dxf_io.Item("U1", 40.5, 60.25, (30.0, 50.0, 50.0, 70.0), True),
            ],
        )

    def test_recupera_los_centros_de_las_cruces(self):
        pos = dxf_io.read_positions(self._doc())
        self.assertAlmostEqual(pos["SW1"][0], 10.0, places=3)
        self.assertAlmostEqual(pos["SW1"][1], 20.0, places=3)

    def test_el_round_trip_conserva_decimales(self):
        pos = dxf_io.read_positions(self._doc())
        self.assertAlmostEqual(pos["U1"][0], 40.5, places=3)
        self.assertAlmostEqual(pos["U1"][1], 60.25, places=3)

    def test_el_round_trip_no_espeja_en_y(self):
        # Escritura y lectura tienen que ser inversas exactas. Si las dos
        # negaran Y, o ninguna, los tests de escritura y de lectura pasarian
        # igual por separado y el error solo aparece al comparar contra el
        # board real.
        pos = dxf_io.read_positions(self._doc())
        self.assertGreater(pos["SW1"][1], 0, "Y volvio negativa del round-trip")

    def test_recupera_el_contorno_de_la_placa(self):
        out = dxf_io.read_outline(self._doc())
        self.assertAlmostEqual(out[2] - out[0], 90.0, places=3)
        self.assertAlmostEqual(out[3] - out[1], 130.0, places=3)

    def test_ignora_capas_sin_cruz(self):
        # BOARD_OUTLINE tiene lineas pero no forma una cruz: no debe aparecer
        # como si fuera un componente.
        pos = dxf_io.read_positions(self._doc())
        self.assertNotIn("BOARD_OUTLINE", pos)

    def test_un_rectangulo_solo_no_se_confunde_con_una_cruz(self):
        # El bbox punteado vive en la MISMA capa que la cruz, asi que el
        # lector tiene que distinguirlos. Un rectangulo tiene horizontales y
        # verticales que se tocan en las esquinas; lo que las descarta es
        # exigir que el cruce sea el punto medio de ambos segmentos.
        solo_rect = dxf_io.rect("XX", 0.0, 0.0, 10.0, 5.0)
        self.assertEqual(dxf_io.read_positions(solo_rect), {})

    def test_tolera_que_rhino_reordene_las_entidades(self):
        # Rhino no garantiza el orden de las entidades al guardar. El lector
        # se apoya en la geometria (interseccion de las dos lineas), no en el
        # orden, asi que invertirlas no debe cambiar nada.
        doc = self._doc()
        bloques = doc.split("  0\nLINE")
        revuelto = bloques[0] + "  0\nLINE".join(reversed(bloques[1:]))
        pos = dxf_io.read_positions(revuelto)
        self.assertAlmostEqual(pos["SW1"][0], 10.0, places=3)

    def test_una_capa_movida_devuelve_la_posicion_nueva(self):
        doc = shift_layer_x(self._doc(), "SW1", 15.5)
        pos = dxf_io.read_positions(doc)
        self.assertAlmostEqual(pos["SW1"][0], 25.5, places=3)
        self.assertAlmostEqual(pos["SW1"][1], 20.0, places=3)

    def test_mover_una_capa_no_afecta_a_las_demas(self):
        doc = shift_layer_x(self._doc(), "SW1", 15.5)
        pos = dxf_io.read_positions(doc)
        self.assertAlmostEqual(pos["U1"][0], 40.5, places=3)

    def test_el_round_trip_es_exacto_para_una_placa_entera(self):
        # La propiedad de la que depende el Task 17: si escritura y lectura no
        # son inversas exactas, el ciclo Rhino corre TODO el layout un poco y
        # nadie lo nota. Se prueba a escala, con coordenadas negativas y
        # componentes de los dos lados, no con dos items de juguete.
        import random
        random.seed(7)
        items = []
        for i in range(60):
            x = round(random.uniform(-40, 140), 2)
            y = round(random.uniform(-40, 190), 2)
            w = round(random.uniform(0.6, 30), 2)
            h = round(random.uniform(0.6, 30), 2)
            items.append(dxf_io.Item(f"R{i}", x, y,
                                     (x - w, y - h, x + w, y + h), i % 3 == 0))
        outline = (-50.0, -50.0, 200.0, 250.0)
        pos = dxf_io.read_positions(dxf_io.build_document(outline, items))

        self.assertEqual(len(pos), len(items), "se perdieron cruces")
        for it in items:
            self.assertAlmostEqual(pos[it.ref][0], it.x, places=4, msg=it.ref)
            self.assertAlmostEqual(pos[it.ref][1], it.y, places=4, msg=it.ref)
        self.assertEqual(
            dxf_io.read_outline(dxf_io.build_document(outline, items)), outline)

    def test_un_dxf_sin_contorno_falla_fuerte(self):
        # Sin contorno no se puede saber el tamano de la placa. Devolver algo
        # por defecto seria peor que fallar.
        with self.assertRaises(ValueError):
            dxf_io.read_outline(dxf_io.rect("XX", 0.0, 0.0, 10.0, 5.0))


if __name__ == "__main__":
    unittest.main()
