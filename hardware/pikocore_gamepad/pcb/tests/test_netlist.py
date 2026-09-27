import io
import math
import os
import re
import unittest

import gen_fp
import netlist
import pinmap

PCB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KICAD_FP = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs",
                        "KiCad", "9.0", "share", "kicad", "footprints")

# Librerias del proyecto -> su directorio .pretty
LIBS_PROPIAS = {
    "gamesetup_lcsc": os.path.join(PCB, "lib", "gamesetup_lcsc.pretty"),
    "gamesetup_fp": os.path.join(PCB, "lib", "gamesetup_fp.pretty"),
}


def footprint_path(fpid):
    """Ruta al .kicad_mod de un footprint 'lib:nombre', o None si la libreria
    es estandar de KiCad y KiCad no esta instalado."""
    lib, _, name = fpid.partition(":")
    if lib in LIBS_PROPIAS:
        return os.path.join(LIBS_PROPIAS[lib], name + ".kicad_mod")
    if not os.path.isdir(KICAD_FP):
        return None
    return os.path.join(KICAD_FP, lib + ".pretty", name + ".kicad_mod")


def pads_bbox(fpid):
    """Semiejes del rectangulo que cubre los pads de un footprint, medidos
    desde su origen y SIN rotar. None si el .kicad_mod no esta disponible."""
    path = footprint_path(fpid)
    if not path or not os.path.isfile(path):
        return None
    txt = io.open(path, encoding="utf-8").read()
    dx = dy = 0.0
    # [^(]* se come el tipo y la forma del pad, saltos de linea incluidos.
    pat = r'\(pad\s+"[^"]*"[^(]*\(at\s+([-\d.]+)\s+([-\d.]+)[^)]*\)\s*\(size\s+([-\d.]+)\s+([-\d.]+)\)'
    for m in re.finditer(pat, txt):
        x, y, w, h = (float(v) for v in m.groups())
        dx = max(dx, abs(x) + w / 2)
        dy = max(dy, abs(y) + h / 2)
    return (dx, dy) if dx else None


def nets_of(ref):
    for inst in netlist.INSTANCES:
        if inst[1] == ref:
            return inst[5]
    raise AssertionError(f"no existe la instancia {ref}")


def pin_names(sym):
    """Nombres de los pines de un simbolo, en orden de numero de pin.

    Algunos footprints identifican sus pads por FUNCION y no por numero (el
    jack oficial de KiCad usa S/T/R/TN/RN). Para esos se conserva el orden de
    declaracion, que es el que el simbolo dibuja.
    """
    pins = netlist.SYMS[sym]["pins"]
    if all(p[0].isdigit() for p in pins):
        pins = sorted(pins, key=lambda p: int(p[0]))
    return [p[1] for p in pins]


class TestSimbolos(unittest.TestCase):

    def test_estan_definidos_todos_los_simbolos_que_usan_las_instancias(self):
        for inst in netlist.INSTANCES:
            self.assertIn(inst[0], netlist.SYMS,
                          f"{inst[1]} usa el simbolo {inst[0]}, que no existe")

    def test_cada_simbolo_declara_prefijo_de_referencia(self):
        for name, s in netlist.SYMS.items():
            self.assertTrue(s["ref"], f"{name}: falta ref")

    def test_cada_simbolo_tiene_al_menos_un_pin(self):
        for name, s in netlist.SYMS.items():
            self.assertTrue(s["pins"], f"{name}: no tiene pines")

    def test_ningun_simbolo_repite_numero_de_pin(self):
        for name, s in netlist.SYMS.items():
            nums = [p[0] for p in s["pins"]]
            self.assertEqual(len(nums), len(set(nums)), f"{name}: pin repetido")

    def test_los_numeros_de_pin_son_correlativos_desde_uno(self):
        # Un hueco en la numeracion casi siempre es un pin olvidado, y el
        # sintoma es una net que no cierra en el ERC.
        for name, s in netlist.SYMS.items():
            if not all(p[0].isdigit() for p in s["pins"]):
                continue      # pads identificados por funcion (S/T/R/TN/RN)
            nums = sorted(int(p[0]) for p in s["pins"])
            self.assertEqual(nums, list(range(1, len(nums) + 1)),
                             f"{name}: numeracion con huecos")

    def test_cada_simbolo_declara_descripcion(self):
        for name, s in netlist.SYMS.items():
            self.assertTrue(s["desc"], f"{name}: falta desc")


class TestSimboloMcu(unittest.TestCase):

    def test_tiene_cuarenta_pines(self):
        self.assertEqual(len(netlist.SYMS["RP2350-Plus"]["pins"]), 40)

    def test_usa_el_orden_del_header_declarado_en_pinmap(self):
        # No debe haber una segunda copia del orden de 40 pines: pinmap.py es
        # la fuente de verdad y check_pinmap la contrasta contra el firmware.
        # Dos copias derivan y el error es invisible.
        self.assertEqual(pin_names("RP2350-Plus"), pinmap.HEADER_ORDER)

    def test_el_pin_38_es_gnd(self):
        # Trampa clasica del header tipo Pico: el pin 38 es GND, no VSYS_EN.
        # En V1 hubo que parchear la tabla a mano por esto.
        self.assertEqual(pin_names("RP2350-Plus")[37], "GND")

    def test_el_pin_40_es_vbus_y_el_39_vsys(self):
        nombres = pin_names("RP2350-Plus")
        self.assertEqual(nombres[38], "VSYS")
        self.assertEqual(nombres[39], "VBUS")

    def test_no_declara_los_gpio_internos_del_modulo(self):
        # GP23/24/25 son internos (MODE del MP28164, sensado de VBUS, LED) y
        # GP29 no sale al header: no deben aparecer como pines del socket.
        nombres = pin_names("RP2350-Plus")
        for g in (23, 24, 25, 29):
            self.assertNotIn(f"GP{g}", nombres)


class TestSimboloLcd(unittest.TestCase):

    def test_tiene_siete_pines_en_el_orden_del_modulo(self):
        self.assertEqual(pin_names("LCD_ST7789"),
                         ["GND", "VCC", "SCL", "SDA", "RES", "DC", "BLK"])

    def test_el_orden_coincide_con_el_footprint(self):
        # El simbolo y el footprint viven en archivos distintos. Si divergen,
        # el esquematico y la placa se cablean distinto y no lo agarra ni el
        # ERC ni el DRC: la netlist es coherente consigo misma en los dos.
        self.assertEqual(pin_names("LCD_ST7789"), gen_fp.LCD_PIN_NAMES)

    def test_no_tiene_pin_cs(self):
        # El modulo de 7 pines esta siempre seleccionado. Que no exista el pin
        # es lo que fuerza que la microSD vaya a otro SPI.
        self.assertNotIn("CS", pin_names("LCD_ST7789"))


class TestSimboloNav(unittest.TestCase):

    def test_tiene_seis_pines(self):
        self.assertEqual(len(netlist.SYMS["NAV_WS1004"]["pins"]), 6)

    def test_sigue_el_pinout_del_datasheet(self):
        # WS-1004-ARL10026: 1=COM 2=LEFT 3=CENTRO 4=UP 5=RIGHT 6=DOWN.
        self.assertEqual(pin_names("NAV_WS1004"),
                         ["COM", "LEFT", "CENTER", "UP", "RIGHT", "DOWN"])


class TestSimboloTact(unittest.TestCase):

    def test_declara_un_pin_por_par_interno(self):
        # El tact tiene 4 patas pero son DOS PARES cortocircuitados. El
        # simbolo declara 2 pines, uno por par, porque el footprint oficial de
        # KiCad (SW_PUSH_6mm) numera sus cuatro pads como 1,1,2,2 — cada
        # numero en las dos patas del mismo par. Cablear 1 y 2 cruza el
        # contacto por construccion.
        self.assertEqual(pin_names("SW_Push"), ["A", "B"])


class TestSimboloSlide(unittest.TestCase):

    def test_el_comun_es_el_pin_2(self):
        # SK12D07VG3: pin 2 = comun (centro), 1/3 = throws, 4/5 = anclaje.
        self.assertEqual(pin_names("SK12D07")[1], "COM")

    def test_las_patas_de_anclaje_son_la_4_y_la_5(self):
        nombres = pin_names("SK12D07")
        self.assertEqual(nombres[3], "MNT")
        self.assertEqual(nombres[4], "MNT")


class TestSimbolosVerificadosDeV1(unittest.TestCase):
    """Pinouts que V1 ya confirmo contra datasheet y que llegaron a una placa
    ruteada. Se copian tal cual; estos tests impiden que alguien los
    'mejore' de memoria."""

    def test_el_dac_sigue_el_pinout_verificado_en_v1(self):
        # Verificado en V1 contra el simbolo oficial de KiCad (PCM5100) y
        # contra TI SLAS859C. NO reescribir de memoria: un pinout de DAC
        # equivocado es una placa muerta.
        self.assertEqual(
            pin_names("PCM5102A"),
            ["CPVDD", "CAPP", "CPGND", "CAPM", "VNEG", "OUTL", "OUTR", "AVDD",
             "AGND", "DEMP", "FLT", "SCK", "BCK", "DIN", "LRCK", "FMT",
             "XSMT", "LDOO", "DGND", "DVDD"])

    def test_el_i2s_del_dac_cae_en_los_pines_12_a_16(self):
        # SCK=12, BCK=13, DIN=14, LRCK=15, FMT=16. Es el bloque que se cablea
        # al PIO y el que mas facil se corre un lugar.
        n = pin_names("PCM5102A")
        self.assertEqual(n[11], "SCK")
        self.assertEqual(n[12], "BCK")
        self.assertEqual(n[13], "DIN")
        self.assertEqual(n[14], "LRCK")
        self.assertEqual(n[15], "FMT")

    def test_el_opamp_sigue_el_estandar_dual_dip8(self):
        # El simbolo pasó de NJM4556AD (V1) a PT2308, pero el pinout es el
        # MISMO: ambos usan el estandar de op-amp dual, identico al
        # 4558/5532/TL072. Verificado contra el datasheet de Princeton
        # (PT2308-s.pdf, PIN CONFIGURATION) pin por pin.
        # Los nombres se conservan en la convencion del op-amp (OUTA/INA-...)
        # y no en la del PT2308 (OUT1/IN1-...) porque es lo que el resto del
        # netlist y el esquematico ya usan; la posicion es lo que importa.
        self.assertEqual(
            pin_names("PT2308"),
            ["OUTA", "INA-", "INA+", "V-", "INB+", "INB-", "OUTB", "V+"])

    def test_el_classd_sigue_el_datasheet_de_diodes(self):
        # Verificado en V1 contra Diodes DS41333.
        self.assertEqual(
            pin_names("PAM8302A"),
            ["SD", "NC", "IN+", "IN-", "VO+", "VDD", "GND", "VO-"])

    def test_la_salida_del_classd_es_btl(self):
        # VO+ y VO- son las dos patas del puente: NINGUNA va a masa. Si
        # alguien conecta VO- a GND pensando que es single-ended, se quema.
        n = pin_names("PAM8302A")
        self.assertIn("VO+", n)
        self.assertIn("VO-", n)
        self.assertIn("BTL", netlist.SYMS["PAM8302A"]["desc"])


class TestSimbolosNuevos(unittest.TestCase):

    def test_el_boost_tiene_seis_pines(self):
        self.assertEqual(len(netlist.SYMS["TPS61023"]["pins"]), 6)

    def test_los_pasivos_tienen_dos_pines(self):
        for name in ("R", "C", "CP", "L", "D"):
            self.assertEqual(len(netlist.SYMS[name]["pins"]), 2, name)

    def test_el_electrolitico_marca_la_polaridad(self):
        # Un CP montado al reves revienta. El simbolo tiene que distinguirse
        # de un ceramico a simple vista en el esquematico.
        self.assertEqual([p[1] for p in netlist.SYMS["CP"]["pins"]], ["+", "-"])

    def test_el_diodo_marca_anodo_y_catodo(self):
        self.assertEqual([p[1] for p in netlist.SYMS["D"]["pins"]], ["A", "K"])

    def test_el_jack_de_audio_declara_el_contacto_de_deteccion(self):
        self.assertIn("DET", pin_names("JACK_AUDIO"))

    def test_el_header_del_parlante_tiene_dos_pines(self):
        self.assertEqual(len(netlist.SYMS["Conn_01x02"]["pins"]), 2)


class TestPinoutsSinVerificar(unittest.TestCase):
    """Los simbolos nuevos no heredan la verificacion de V1. Mientras su
    pinout no se confirme contra datasheet, tiene que decirlo en la cara —
    el esquematico en PDF lo muestra, igual que V1 hizo con el NJM4556AD
    antes de verificarlo."""

    def test_la_tabla_existe_aunque_este_vacia(self):
        # Hoy esta vacia: los dos simbolos que faltaban (JACK_AUDIO y
        # TPS61023) ya se verificaron contra sus datasheets, y en LOS DOS la
        # verificacion encontro errores reales. Por eso la tabla se conserva
        # en vez de borrarla: lo que entre nuevo sin verificar va aca.
        self.assertIsInstance(netlist.PINOUT_SIN_VERIFICAR, tuple)

    def test_todos_existen_como_simbolo(self):
        for name in netlist.PINOUT_SIN_VERIFICAR:
            self.assertIn(name, netlist.SYMS)

    def test_cada_uno_lo_dice_en_su_descripcion(self):
        for name in netlist.PINOUT_SIN_VERIFICAR:
            self.assertIn("SIN VERIFICAR", netlist.SYMS[name]["desc"],
                          f"{name}: el desc no avisa")

    def test_ningun_simbolo_heredado_de_v1_esta_en_la_lista(self):
        # Si uno de estos aparece marcado sin verificar, es que alguien lo
        # reescribio y perdio la verificacion de V1.
        for name in ("PCM5102A", "NJM4556AD", "PAM8302A", "SK12D07"):
            self.assertNotIn(name, netlist.PINOUT_SIN_VERIFICAR)


class TestFootprints(unittest.TestCase):

    def test_toda_instancia_declara_footprint(self):
        for inst in netlist.INSTANCES:
            self.assertIn("FP", inst[6], f"{inst[1]}: sin footprint")

    def test_los_footprints_provisionales_nombran_constantes_reales(self):
        for nombre in netlist.FOOTPRINTS_PROVISIONALES:
            self.assertTrue(hasattr(netlist, nombre),
                            f"{nombre} no existe como constante")

    def test_cada_footprint_provisional_declara_su_motivo(self):
        for nombre, motivo in netlist.FOOTPRINTS_PROVISIONALES.items():
            self.assertTrue(len(motivo) > 20, f"{nombre}: motivo muy pobre")

    def test_los_footprints_provisionales_igual_tienen_que_existir(self):
        # Son stand-ins para que el flujo corra end-to-end; si el stand-in
        # tampoco existe, gen_pcb.py falla igual.
        for nombre in netlist.FOOTPRINTS_PROVISIONALES:
            fpid = getattr(netlist, nombre)
            p = footprint_path(fpid)
            if p is not None:
                self.assertTrue(os.path.isfile(p), f"{nombre}: {fpid}")

    def test_todos_los_footprints_referenciados_existen(self):
        # Un footprint inexistente no lo detecta nadie hasta que gen_pcb.py
        # falla al cargarlo, ya avanzado el flujo. Verificarlo aca cuesta nada.
        faltan = []
        for inst in netlist.INSTANCES:
            fpid = inst[6].get("FP", "")
            p = footprint_path(fpid)
            if p is not None and not os.path.isfile(p):
                faltan.append(f"{inst[1]}: {fpid}")
        self.assertEqual(faltan, [], f"footprints inexistentes: {faltan}")

    def test_placements_usa_el_mismo_footprint_que_el_netlist(self):
        # El footprint esta declarado en DOS lugares: netlist.py (que va al
        # esquematico y al .net) y placements.py (que es de donde gen_pcb.py
        # lo carga de verdad). Si divergen, la placa sale con el footprint
        # viejo y el pinout nuevo — y nada falla a la vista: los pads que
        # sobran quedan como "unconnected-(...)" en vez de dar error.
        # Paso exactamente eso al cambiar J1 de header de 4 pines al jack de
        # 5, asi que queda cubierto.
        import placements
        del_netlist = {i[1]: i[6].get("FP", "") for i in netlist.INSTANCES}
        divergen = []
        for ref, lib_id, *_ in placements.PLACEMENTS:
            esperado = del_netlist.get(ref)
            if esperado and esperado != lib_id:
                divergen.append(f"{ref}: netlist={esperado} placements={lib_id}")
        self.assertEqual(divergen, [], f"footprint divergente: {divergen}")

    def test_las_regiones_libres_caen_dentro_de_la_placa(self):
        # FREE_REGIONS le dice a gen_pcb.py donde empaquetar los pasivos, y
        # empaquetar_pasivos NO verifica el contorno: si una region se pasa
        # del borde, los componentes caen afuera sin que nada avise.
        # Ya paso DOS veces al cambiar BOARD_H (105 -> 80 la ultima), asi que
        # el test existe para que no haya una tercera.
        import placements
        malas = [r for r in placements.FREE_REGIONS
                 if r[2] > placements.BOARD_W or r[3] > placements.BOARD_H]
        self.assertEqual(malas, [],
                         f"regiones fuera de la placa "
                         f"{placements.BOARD_W}x{placements.BOARD_H}: {malas}")

    def test_los_gatillos_L_y_R_quedan_simetricos(self):
        # El origen del tact angulado es el PAD 1, que no esta en el centro de
        # la pieza: su cuerpo esta 2.25mm corrido en X local. Como L y R usan
        # rotaciones opuestas (90 y 270), ese desbalance se proyecta sobre Y
        # con signos contrarios — poniendo los dos en el mismo Y quedan
        # corridos 4.50mm uno respecto del otro, que se ve a simple vista en
        # la placa armada pero no mirando los numeros.
        # El invariante que importa es que los CUERPOS queden a la misma
        # altura, no que los origenes coincidan.
        import placements
        OFF = 2.25   # (x0+x1)/2 del F.Fab del PTS645Vx39-2LFS
        pos = {}
        for ref, lib_id, x, y, rot, flip in placements.PLACEMENTS:
            if ref in ("SW9", "SW10"):
                pos[ref] = (x, y, rot % 360)
        self.assertEqual(set(pos), {"SW9", "SW10"}, "faltan los gatillos")

        rots = {r for _, _, r in pos.values()}
        self.assertTrue(rots <= {0, 90, 180, 270},
                        f"rotacion inesperada: {rots}")

        if rots == {0} or rots == {180}:
            # Gatillos en un borde HORIZONTAL (arriba o abajo): el desbalance
            # del footprint cae del mismo lado en los dos, asi que lo que
            # tiene que coincidir es la Y, y los cuerpos tienen que quedar
            # simetricos respecto del centro de la placa.
            self.assertAlmostEqual(
                pos["SW9"][1], pos["SW10"][1], places=3,
                msg=f"gatillos a distinta altura: {pos}")
            cx = {ref: x + OFF for ref, (x, _, _) in pos.items()}
            centro = placements.BOARD_W / 2
            self.assertAlmostEqual(
                cx["SW9"] - 0, placements.BOARD_W - cx["SW10"], places=2,
                msg=f"gatillos no simetricos respecto de X={centro}: {cx}")
        else:
            # Gatillos en los bordes LATERALES con rotaciones opuestas: ahi el
            # desbalance se proyecta sobre Y con signos contrarios y hay que
            # compensarlo, o quedan corridos 4.50mm (paso en su momento).
            self.assertEqual(rots, {90, 270},
                             f"un gatillo en cada lateral requiere 90 y 270: {pos}")
            centros = {}
            for ref, (x, y, rot) in pos.items():
                centros[ref] = y - OFF if rot == 90 else y + OFF
            self.assertAlmostEqual(
                centros["SW9"], centros["SW10"], places=3,
                msg=f"gatillos a distinta altura: {centros}")


    def test_nada_alto_queda_bajo_el_modulo_rp2350(self):
        # El socket 2x20 levanta el modulo ~8.5mm sobre la placa. En COBRE la
        # franja central entre las dos filas de pines esta libre y tienta a
        # meter cosas ahi, pero en ALTURA no entra casi nada: un JST PH
        # vertical solo mide 8.0mm y ademas hay que poder ENCHUFARLE el cable,
        # que suma varios mm mas por arriba.
        # J5 estuvo en (18,30) —dentro de la huella de U1— hasta que se
        # detecto el choque; el DRC lo reportaba como courtyards_overlap y se
        # leia como ruido.
        import placements
        U1 = next((p for p in placements.PLACEMENTS if p[0] == "U1"), None)
        self.assertIsNotNone(U1, "no se encontro U1 en PLACEMENTS")
        _, fpid, ux, uy, rot, uflip = U1
        # La caja sale del .kicad_mod, NO de dos numeros escritos a mano: si
        # se cambia el socket o se gira el modulo, el guard se mueve con el.
        # Cableada, la caja se queda vieja justo cuando mas hace falta, y este
        # test es lo unico que separa a J5 de volver debajo del modulo.
        caja = pads_bbox(fpid)
        if caja is None:
            self.skipTest("no esta el .kicad_mod de %s" % fpid)
        HW, HH = caja
        if rot % 180 == 90:
            HW, HH = HH, HW      # 90 y 270 intercambian los ejes
        HW += 1.0                # holgura de colocacion
        HH += 1.0
        ALTOS = {"J5"}   # conectores que no pueden vivir debajo del modulo
        dentro = []
        for ref, lib_id, x, y, rot, flip in placements.PLACEMENTS:
            if ref not in ALTOS:
                continue
            if flip != uflip:
                # Lado opuesto de la placa: el modulo no le pasa por encima.
                # SW11 cae justo en el centro de la huella de U1 y es
                # correcto, porque el tact esta en el panel (F.Cu) y el
                # modulo en el dorso (B.Cu). Sin esta condicion el guard
                # dispararia contra colocaciones que estan bien.
                continue
            if abs(x - ux) < HW and abs(y - uy) < HH:
                dentro.append(f"{ref} en ({x}, {y}) cae bajo U1 en ({ux}, {uy})")
        self.assertEqual(dentro, [], f"choque mecanico con el modulo: {dentro}")


class TestPuentesDeTact(unittest.TestCase):
    """Los tacts de 6mm tienen cuatro patas numeradas 1,1,2,2 en el footprint
    oficial de KiCad. KiCad NO da por conectados dos pads solo porque
    compartan numero, asi que si el ruteador llega a uno de los dos, la net
    queda abierta — y como el switch une las patas por dentro, la placa
    funciona igual y el error solo se ve en el DRC.

    Venia pasando por casualidad: en una corrida el ruteador alcanzaba los
    dos pads de cinco de los seis tacts y en SW5 llegaba a uno solo."""

    def test_cada_tact_de_6mm_tiene_su_puente(self):
        import manual_tracks
        tacts = {i[1] for i in netlist.INSTANCES if i[0] == "SW_Push"}
        self.assertEqual(tacts - set(manual_tracks.PUENTES_TACT), set(),
                         "tact(s) sin puente en PUENTES_TACT")

    def test_no_hay_puentes_de_mas(self):
        import manual_tracks
        tacts = {i[1] for i in netlist.INSTANCES if i[0] == "SW_Push"}
        self.assertEqual(set(manual_tracks.PUENTES_TACT) - tacts, set(),
                         "PUENTES_TACT nombra piezas que ya no existen")

    def test_cada_puente_usa_la_net_de_su_tact(self):
        import manual_tracks
        for ref, (net, _a, _b) in manual_tracks.PUENTES_TACT.items():
            self.assertIn(net, nets_of(ref).values(),
                          "%s: el puente usa la net %s, que no es suya"
                          % (ref, net))


class TestInstanciasEntrada(unittest.TestCase):

    def test_hay_nueve_switches_fisicos(self):
        # 6 tacts verticales (X/Y/A/B + Start/Select) + 2 gatillos angulados
        # (L/R) + 1 NAV5 (reemplaza los 4 tacts del D-pad).
        vert = [i for i in netlist.INSTANCES if i[0] == "SW_Push"]
        ang = [i for i in netlist.INSTANCES if i[0] == "SW_Push_RA"]
        nav = [i for i in netlist.INSTANCES if i[0] == "NAV_WS1004"]
        self.assertEqual(len(vert), 6)
        self.assertEqual(len(ang), 2)
        self.assertEqual(len(nav), 1)
        self.assertEqual(len(vert) + len(ang) + len(nav), 9)

    def test_hay_trece_botones_logicos(self):
        # X/Y/A/B (4) + Start/Select (2) + L/R (2) + NAV5 (5: 4 direcciones +
        # BTN_OK) = 13, aunque solo sean 9 piezas fisicas.
        logicos = {sig for _, sig in netlist.TACTS}
        logicos |= {"BTN_L", "BTN_R"}
        logicos |= {"DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "BTN_OK"}
        self.assertEqual(len(logicos), 13)

    def test_los_gatillos_son_los_angulados(self):
        # L y R se aprietan de costado desde el borde: si quedaran verticales
        # habria que apretarlos contra la cara del panel.
        refs = {i[1] for i in netlist.INSTANCES if i[0] == "SW_Push_RA"}
        self.assertEqual(refs, {"SW9", "SW10"})

    def test_los_gatillos_usan_sus_dos_unicos_pines(self):
        # El angulado tiene SOLO 2 pines electricos; los otros dos contactos
        # del footprint son anclajes mecanicos sin numerar. Cablear un "pin 4"
        # como en el vertical dejaria la net sin aterrizar.
        for ref, sig in (("SW9", "BTN_L"), ("SW10", "BTN_R")):
            n = nets_of(ref)
            self.assertEqual(set(n), {"1", "2"})
            self.assertEqual(n["1"], sig)
            self.assertEqual(n["2"], "GND")

    def test_los_tacts_cruzan_el_contacto(self):
        # El tact tiene 4 patas en dos pares cortocircuitados. Para que apretar
        # el boton CIERRE algo, los dos extremos tienen que caer en pares
        # DISTINTOS: si los dos van al mismo par, la net queda cerrada siempre
        # y el boton no hace nada.
        # Con SW_PUSH_6mm eso queda garantizado por el footprint, que numera
        # sus pads 1,1,2,2 — un numero por par. Basta con que el netlist use
        # los dos numeros, que es lo que se verifica aca.
        for inst in netlist.INSTANCES:
            if inst[0] != "SW_Push":
                continue
            n = inst[5]
            self.assertEqual(set(n), {"1", "2"},
                             f"{inst[1]}: tiene que usar un pin de cada par")
            self.assertNotEqual(n["1"], "GND", f"{inst[1]}: pin 1 es la senal")
            self.assertEqual(n["2"], "GND", f"{inst[1]}: pin 2 va a masa")

    def test_el_comun_del_nav5_va_a_masa(self):
        self.assertEqual(nets_of("SW13")["1"], "GND")

    def test_el_nav5_cablea_las_5_direcciones_correctas(self):
        # Las 4 direcciones ya estaban en el pinmap desde el fork original
        # (heredadas del D-pad); BTN_OK es nuevo en este plan.
        n = nets_of("SW13")
        self.assertEqual(n["2"], "DPAD_LEFT")
        self.assertEqual(n["3"], "BTN_OK")
        self.assertEqual(n["4"], "DPAD_UP")
        self.assertEqual(n["5"], "DPAD_RIGHT")
        self.assertEqual(n["6"], "DPAD_DOWN")

    def test_las_5_nets_del_nav5_existen_en_el_pinmap(self):
        # gpio_of() falla fuerte (KeyError) si la funcion no esta asignada:
        # esto verifica que las 5 nets del NAV5 tengan un GPIO real detras,
        # no un nombre que quedo mal escrito.
        for func in ("DPAD_LEFT", "BTN_OK", "DPAD_UP", "DPAD_RIGHT", "DPAD_DOWN"):
            pinmap.gpio_of(func)  # no debe lanzar KeyError

class TestInstanciaMcu(unittest.TestCase):

    def test_usa_exactamente_el_pinmap(self):
        u1 = nets_of("U1")
        for gpio, func in pinmap.GPIO.items():
            pin = str(pinmap.header_pin(gpio))
            self.assertEqual(u1[pin], func,
                             f"GP{gpio} (pin {pin}) deberia ser {func}")

    def test_todos_los_gnd_del_header_van_a_masa(self):
        u1 = nets_of("U1")
        for i, nombre in enumerate(pinmap.HEADER_ORDER):
            if nombre in ("GND", "AGND"):
                self.assertEqual(u1[str(i + 1)], "GND", f"pin {i+1}")

    def test_el_3v3_en_va_al_slide_de_encendido(self):
        u1 = nets_of("U1")
        pin = str(pinmap.HEADER_ORDER.index("3V3_EN") + 1)
        self.assertEqual(u1[pin], "PWR_EN")
        self.assertEqual(nets_of("SW15")["2"], "PWR_EN")

    def test_el_slide_apaga_tirando_a_masa(self):
        # El 3V3_EN tiene pull-up interno a VSYS: cerrarlo contra GND apaga
        # el rail de 3V3 del modulo.
        n = nets_of("SW15")
        self.assertEqual(n["1"], "GND")

    def test_las_patas_de_anclaje_del_slide_van_a_masa(self):
        n = nets_of("SW15")
        self.assertEqual(n["4"], "GND")
        self.assertEqual(n["5"], "GND")


class TestInstanciaDisplay(unittest.TestCase):

    def test_se_alimenta_de_3v3(self):
        n = nets_of("J4")
        self.assertEqual(n["1"], "GND")
        self.assertEqual(n["2"], "3V3")

    def test_el_spi_y_el_control_llegan_del_mcu(self):
        n = nets_of("J4")
        self.assertEqual(n["3"], "LCD_SCK")
        self.assertEqual(n["4"], "LCD_MOSI")
        self.assertEqual(n["5"], "LCD_RES")
        self.assertEqual(n["6"], "LCD_DC")

    def test_el_backlight_va_al_gpio_y_no_a_3v3(self):
        # Fijarlo a 3V3 dejaria el mayor consumidor de la placa siempre al
        # maximo, sin forma de apagar la pantalla por firmware.
        self.assertEqual(nets_of("J4")["7"], "LCD_BLK")


def instancias_de(sym):
    return [i for i in netlist.INSTANCES if i[0] == sym]


def hay_pasivo(sym, nets, valor=None):
    """True si existe un pasivo de `sym` conectado exactamente a `nets`."""
    for i in netlist.INSTANCES:
        if i[0] == sym and set(i[5].values()) == set(nets):
            if valor is None or i[2] == valor:
                return True
    return False


def faradios(valor):
    """'2.2uF', '2u2' o '100nF' -> el valor en faradios.

    Acepta las dos notaciones a proposito: asi el test verifica el NUMERO y
    no como esta escrito. La cadena importa aparte — el emparejador de BOM de
    JLCPCB lee el campo Comment, y ahi '2u2' es ambiguo (se estaba usando
    para 2.2uF y para 2.2uH a la vez)."""
    v = valor.rstrip("F")
    for suf, mult in (("p", 1e-12), ("n", 1e-9), ("u", 1e-6), ("m", 1e-3)):
        if v.endswith(suf):          # "2.2u"
            return float(v[:-1]) * mult
        if suf in v:                 # "2u2", notacion europea
            ent, _, dec = v.partition(suf)
            return float(ent + "." + dec) * mult
    return float(v)


def valor_de(sym, nets):
    """Valor del unico pasivo de `sym` conectado exactamente a `nets`."""
    for i in netlist.INSTANCES:
        if i[0] == sym and set(i[5].values()) == set(nets):
            return i[2]
    raise AssertionError("no hay %s entre %s" % (sym, " y ".join(nets)))


def resistencia(nets):
    return valor_de("R", nets)


def capacitancia_total(nets):
    """Suma en faradios de todos los capacitores entre `nets`.

    Suma C y CP juntos a proposito: lo que le importa a un riel es la
    capacidad que ve, no con que simbolo esta dibujada. Varios electroliticos
    pasaron a ceramico al elegir las partes de JLCPCB y los tests no tienen
    por que romperse por eso — si el valor cambia, ahi si."""
    total = 0.0
    for i in netlist.INSTANCES:
        if i[0] in ("C", "CP") and set(i[5].values()) == set(nets):
            total += faradios(i[2])
    return total


def capacitor(nets):
    """Busca en C y en CP: si un electrolitico se cambia por ceramico o al
    reves el valor sigue siendo el mismo y el test no tiene por que romperse."""
    for sym in ("C", "CP"):
        try:
            return valor_de(sym, nets)
        except AssertionError:
            pass
    raise AssertionError("no hay capacitor entre %s" % " y ".join(nets))


def ohms(valor):
    """'4.7k' -> 4700.0. Sirve para verificar divisores por su NUMERO y no
    por la cadena, que es lo que permite cambiar valores sin romper el test
    mientras el circuito siga cumpliendo."""
    mult = {"R": 1, "k": 1e3, "M": 1e6}
    if valor[-1] in mult:
        return float(valor[:-1]) * mult[valor[-1]]
    return float(valor)


class TestAudioDac(unittest.TestCase):

    def test_el_sck_va_a_masa(self):
        # Activa el PLL interno desde BCK: sin esto hace falta MCLK, que el
        # PIO no genera. SCK es el pin 12 — el 13 es BCK.
        self.assertEqual(nets_of("U5")["12"], "GND")

    def test_el_i2s_llega_a_los_pines_13_14_15(self):
        n = nets_of("U5")
        self.assertEqual(n["13"], "I2S_BCK")
        self.assertEqual(n["14"], "I2S_DIN")
        self.assertEqual(n["15"], "I2S_LRCK")

    def test_fmt_flt_y_demp_van_a_masa(self):
        n = nets_of("U5")
        self.assertEqual(n["16"], "GND", "FMT")
        self.assertEqual(n["11"], "GND", "FLT")
        self.assertEqual(n["10"], "GND", "DEMP")

    def test_xsmt_va_al_gpio_y_no_a_masa(self):
        self.assertEqual(nets_of("U5")["17"], "DAC_XSMT")

    def test_xsmt_tiene_pulldown_de_100k(self):
        # El DAC debe arrancar MUTEADO: sin esto hay un golpe audible en el
        # arranque. El modulo GY-PCM5102 lo traia resuelto de fabrica; chip
        # down hay que ponerlo.
        self.assertTrue(hay_pasivo("R", ["DAC_XSMT", "GND"], "100k"))

    def test_los_tres_rieles_del_dac_estan_alimentados(self):
        n = nets_of("U5")
        for pin, nombre in (("1", "CPVDD"), ("8", "AVDD"), ("20", "DVDD")):
            self.assertEqual(n[pin], "3V3", nombre)

    def test_cada_riel_del_dac_tiene_100n_y_10u(self):
        # TI SLAS859C. Con un solo valor por riel no se cubre el rango de
        # frecuencias que pide la hoja de datos.
        cien_n = [i for i in netlist.INSTANCES
                  if i[0] == "C" and i[2] == "100nF"
                  and set(i[5].values()) == {"3V3", "GND"}]
        diez_u = [i for i in netlist.INSTANCES
                  # isclose y no ==: faradios("10uF") da 9.999...e-6, que
                  # con == no coincide con 10e-6. Comparar flotantes por
                  # igualdad exacta hacia fallar el test sin que el netlist
                  # tuviera nada malo.
                  if i[0] in ("C", "CP")
                  and math.isclose(faradios(i[2]), 10e-6, rel_tol=1e-9)
                  and set(i[5].values()) == {"3V3", "GND"}]
        self.assertGreaterEqual(len(cien_n), 3)
        self.assertGreaterEqual(len(diez_u), 3)

    def test_el_charge_pump_esta_completo(self):
        # CAPP-CAPM y VNEG a masa. Es lo que centra la salida en masa; sin
        # esto no hay DirectPath.
        self.assertAlmostEqual(faradios(capacitor(["CAPP", "CAPM"])), 2.2e-6)
        self.assertAlmostEqual(faradios(capacitor(["VNEG", "GND"])), 2.2e-6)
        self.assertTrue(hay_pasivo("C", ["LDOO", "GND"], "100nF"))

    def test_el_filtro_de_salida_es_470_ohm_y_2n2_por_canal(self):
        for dac, aout in (("DACOUT_L", "AOUT_L"), ("DACOUT_R", "AOUT_R")):
            self.assertAlmostEqual(ohms(resistencia([dac, aout])), 470.0,
                                   msg=dac)
            self.assertAlmostEqual(faradios(capacitor([aout, "GND"])), 2.2e-9,
                                   msg=aout)


class TestAudioBoost(unittest.TestCase):

    def test_toma_vsys_filtrado_y_entrega_cinco_volts(self):
        # Pinout de TI SLVSF14B, seccion 5: 1=FB 2=EN 3=VIN 4=GND 5=SW 6=VOUT.
        # El simbolo de V1 tenia 5 de los 6 pines corridos y el cableado
        # seguia ese error.
        n = nets_of("U2")
        self.assertEqual(n["3"], "VSYS_F", "pin 3 = VIN")
        self.assertEqual(n["6"], "5V", "pin 6 = VOUT")
        self.assertEqual(n["4"], "GND", "pin 4 = GND")
        self.assertEqual(n["5"], "BOOST_SW", "pin 5 = SW, va al inductor")
        self.assertEqual(n["1"], "BOOST_FB", "pin 1 = FB, va al divisor")

    def test_arranca_habilitado(self):
        # EN (pin 2) atado a VIN: el riel analogico no depende de ningun GPIO,
        # asi que el audio funciona aunque el firmware no arranque.
        self.assertEqual(nets_of("U2")["2"], "VSYS_F")

    def test_el_divisor_de_realimentacion_da_cinco_volts(self):
        # Vout = VREF * (1 + Rtop/Rbot), VREF = 0.595V (TI SLVSF14B tabla 6.5).
        # Los valores de V1 (1000k/200k) daban 3.57V: nunca se calcularon.
        import params
        VREF = 0.595
        top = params.v("BOOST_RFB_TOP")
        bot = params.v("BOOST_RFB_BOT")
        vout = VREF * (1 + top / bot)
        self.assertAlmostEqual(vout, 5.0, delta=0.05,
                               msg=f"el divisor {top}k/{bot}k da {vout:.3f}V")

    def test_el_inductor_esta_en_el_rango_de_ti(self):
        # TI SLVSF14B tabla 6.3: inductancia efectiva 0.37 .. 2.9 uH.
        import params
        L = params.v("BOOST_L")
        self.assertGreaterEqual(L, 0.37)
        self.assertLessEqual(L, 2.9)

    def test_tiene_filtro_lc_en_la_entrada(self):
        # Spec 5.2.1: que la conmutacion del boost no vuelva por VSYS hasta el
        # regulador del modulo.
        self.assertTrue(hay_pasivo("L", ["VSYS", "VSYS_F"]))
        self.assertTrue(hay_pasivo("C", ["VSYS_F", "GND"]))

    def test_el_inductor_del_boost_va_de_vsys_filtrado_a_sw(self):
        self.assertTrue(hay_pasivo("L", ["VSYS_F", "BOOST_SW"]))

    def test_tiene_divisor_de_realimentacion(self):
        self.assertTrue(hay_pasivo("R", ["5V", "BOOST_FB"]))
        self.assertTrue(hay_pasivo("R", ["BOOST_FB", "GND"]))

    def test_tiene_bulk_local_en_el_riel_de_cinco_volts(self):
        # Spec 5.2.1: fisicamente junto a los pines del op-amp.
        # Se mide la CAPACIDAD del riel, no el tipo de capacitor: el bulk
        # dejo de ser un electrolitico de 100uF y pasaron a ser dos ceramicos
        # de 22uF/25V, que a 1MHz sirven mucho mas (el electrolitico tiene
        # demasiado ESR ahi). TI pide ~22uF de salida para el TPS61023.
        self.assertGreaterEqual(capacitancia_total(["5V", "GND"]), 20e-6)
        self.assertTrue(hay_pasivo("C", ["5V", "GND"], "100nF"))


class TestAudioOpamp(unittest.TestCase):

    def test_se_alimenta_del_riel_de_cinco_volts(self):
        n = nets_of("U3")
        self.assertEqual(n["8"], "5V", "V+")
        self.assertEqual(n["4"], "GND", "V-")

    def test_las_entradas_no_inversoras_van_a_la_masa_virtual(self):
        n = nets_of("U3")
        self.assertEqual(n["3"], "VREF25", "INA+")
        self.assertEqual(n["5"], "VREF25", "INB+")

    def test_la_masa_virtual_esta_a_la_mitad_del_riel(self):
        # Divisor 10k/10k desde 5V, con bulk. Alimentacion simple obliga.
        self.assertTrue(hay_pasivo("R", ["5V", "VREF25"], "10k"))
        self.assertTrue(hay_pasivo("R", ["VREF25", "GND"], "10k"))
        # El reservorio de la masa virtual. Con R9/R10 el equivalente
        # Thevenin es 5k, asi que 100uF ponen el corte en 0.32Hz, muy
        # por debajo del audio. Bajar de ~47uF lo subiria a 0.7Hz y
        # empezaria a acortar la rampa de encendido (mas "pop").
        self.assertGreaterEqual(capacitancia_total(["VREF25", "GND"]),
                                47e-6)

    def test_la_entrada_esta_acoplada_por_capacitor(self):
        # La salida del DAC reposa en MASA y la del op-amp en VREF25. Sin
        # acoplo circularia continua por Rf y la salida se iria a 3.75V,
        # comiendose el headroom.
        for aout, inn in (("AOUT_L", "INL"), ("AOUT_R", "INR")):
            self.assertTrue(hay_pasivo("C", [aout, inn], "1uF"), aout)

    def test_la_ganancia_es_0_5_por_canal(self):
        # Rf/Rin = 10k/20k. El PCM5102A entrega +-2.8V centrados en masa y el
        # op-amp corre con 5V simples: +-2.8V no entran, +-1.4V si.
        for inn, sum_n, out in (("INL", "OPL_N", "AUDIO_L"),
                                ("INR", "OPR_N", "AUDIO_R")):
            self.assertTrue(hay_pasivo("R", [inn, sum_n], "20k"), inn)
            self.assertTrue(hay_pasivo("R", [sum_n, out], "10k"), out)

    def test_la_salida_al_jack_esta_bloqueada_en_continua(self):
        # La salida del op-amp reposa en VREF25 (2.5V): sin bloqueo, esos
        # 2.5V irian a los auriculares.
        for audio, jack in (("AUDIO_L", "JACK_L"), ("AUDIO_R", "JACK_R")):
            self.assertTrue(hay_pasivo("CP", [audio, jack], "470uF"), audio)


class TestAudioJackYParlante(unittest.TestCase):

    def test_el_jack_recibe_los_dos_canales_y_masa(self):
        # Orden del datasheet del SJ1-3535NG (rev 1.06 p.2), NO el del header
        # de 4 pines que se usaba como stand-in: 1=sleeve, 2=tip, 3=ring.
        n = nets_of("J1")
        self.assertEqual(n["S"], "GND", "SLEEVE")
        self.assertEqual(n["T"], "JACK_L", "TIP")
        self.assertEqual(n["R"], "JACK_R", "RING")

    def test_el_jack_lleva_su_contacto_de_deteccion_al_gpio(self):
        # El contacto usado es el de RING (pin 5). El de TIP (pin 4) queda al
        # aire: ver la nota en netlist.py sobre por que no se puede colgar un
        # pull-up de cualquiera de los dos.
        self.assertEqual(nets_of("J1")["RN"], "JACK_DETSW")

    def test_la_deteccion_tiene_pull_up_externo(self):
        # Antes de que el firmware configure el pin, el pull-up interno no
        # esta activo y DET quedaria flotante.
        self.assertTrue(hay_pasivo("R", ["3V3", "JACK_DET"]))

    def test_la_deteccion_esta_aislada_del_canal_de_audio(self):
        # Los switches del SJ1-3535NG cierran contra su propia senal, no
        # contra masa. Sin la serie el pull-up inyecta DC en el canal derecho
        # cada vez que no hay auriculares puestos.
        self.assertTrue(hay_pasivo("R", ["JACK_DET", "JACK_DETSW"]))

    def test_el_divisor_de_deteccion_se_cierra_contra_masa(self):
        # ESTA ES LA REGRESION. El circuito original ponia pull-up en
        # JACK_DET y serie hasta JACK_DETSW, y ahi se detenia: el switch
        # cierra contra JACK_R, que del otro lado solo tiene C24 — un
        # capacitor, que BLOQUEA CONTINUA. No se formaba ningun divisor y
        # JACK_DET se quedaba en 3V3 con y sin plug. La deteccion no
        # funcionaba en ningun estado, y nada lo detectaba.
        self.assertTrue(hay_pasivo("R", ["JACK_R", "GND"]),
                        "sin resistencia de JACK_R a masa el divisor de "
                        "deteccion no existe: C24 bloquea la continua")

    def test_la_deteccion_da_nivel_bajo_sin_plug(self):
        # Con el plug afuera el switch cierra y queda
        #   3V3 -[R15]- DET -[R18]- JACK_R -[R20]- GND
        # Para que el GPIO lea BAJO hace falta R18+R20 << R15. Con los 100k
        # que tenia R18 el divisor daba 3.1V aunque el camino existiera, o
        # sea seguia sin funcionar. Se verifica el numero, no el valor.
        pu = ohms(resistencia(["3V3", "JACK_DET"]))
        serie = ohms(resistencia(["JACK_DET", "JACK_DETSW"]))
        bleed = ohms(resistencia(["JACK_R", "GND"]))
        det = 3.3 * (serie + bleed) / (pu + serie + bleed)
        self.assertLess(det, 0.3 * 3.3,
                        "DET = %.2fV, el umbral bajo del RP2350 es 0.99V "
                        "(R15=%g R18=%g R20=%g)" % (det, pu, serie, bleed))

    def test_la_deteccion_esta_filtrada(self):
        # Con el plug afuera el switch esta cerrado y JACK_R sigue llevando
        # audio, atenuado solo por R15/R18. Sin capacitor el pin lee ALTO en
        # cada pico de senal: el jack parpadeando.
        self.assertTrue(hay_pasivo("C", ["JACK_DET", "GND"]))

    def test_los_capacitores_de_acoplo_tienen_referencia_de_continua(self):
        # C23 y C24 son electroliticos POLARIZADOS de 470uF. Sin bleeder su
        # terminal negativo flota cuando no hay auriculares puestos: no hay
        # nada que fije su polaridad. Los bleeders tambien matan el "pop" al
        # conectar, porque el capacitor ya esta descargado del lado del jack.
        for net in ("JACK_L", "JACK_R"):
            self.assertTrue(hay_pasivo("R", [net, "GND"]),
                            "%s no tiene bleeder a masa" % net)

    def test_los_dos_canales_tienen_el_mismo_bleeder(self):
        # Valores distintos serian un desbalance de canales.
        self.assertEqual(resistencia(["JACK_L", "GND"]),
                         resistencia(["JACK_R", "GND"]))

    def test_la_suma_mono_usa_dos_resistencias_iguales(self):
        sumas = [i for i in netlist.INSTANCES
                 if i[0] == "R" and "SPK_SUM" in i[5].values()]
        self.assertEqual(len(sumas), 2)
        self.assertEqual(sumas[0][2], sumas[1][2])

    def test_la_suma_se_toma_antes_del_bloqueo_de_dc(self):
        # De AUDIO_*, no de JACK_*: si se tomara despues, el parlante se
        # quedaria sin senal cuando no hay auriculares enchufados.
        sumas = [i for i in netlist.INSTANCES
                 if i[0] == "R" and "SPK_SUM" in i[5].values()]
        fuentes = {n for i in sumas for n in i[5].values() if n != "SPK_SUM"}
        self.assertEqual(fuentes, {"AUDIO_L", "AUDIO_R"})

    def test_el_classd_se_alimenta_de_vsys_y_no_del_boost(self):
        # Deliberado: a todo volumen pide cientos de mA y obligaria a
        # dimensionar el inductor del boost para esa punta.
        self.assertEqual(nets_of("U4")["6"], "VSYS")

    def test_el_shdn_del_classd_lo_gobierna_el_firmware(self):
        self.assertEqual(nets_of("U4")["1"], "SPK_SHDN")

    def test_las_entradas_del_classd_estan_acopladas(self):
        # SPK_SUM reposa en VREF25 (2.5V) y el PAM8302A polariza sus entradas
        # respecto de SU alimentacion (VSYS). Sin acoplo los dos puntos pelean.
        self.assertTrue(hay_pasivo("C", ["SPK_SUM", "SPK_INP"], "1uF"))
        self.assertTrue(hay_pasivo("C", ["SPK_INN", "GND"], "1uF"))

    def test_la_salida_btl_va_entera_al_header(self):
        # Ningun terminal a masa: es un puente.
        n = nets_of("J5")
        self.assertEqual(set(n.values()), {"SPK_P", "SPK_N"})
        u4 = nets_of("U4")
        self.assertEqual(u4["5"], "SPK_P")
        self.assertEqual(u4["8"], "SPK_N")
        self.assertNotIn("GND", (u4["5"], u4["8"]))


class TestCoberturaDeNets(unittest.TestCase):

    def test_ninguna_net_de_senal_tiene_un_solo_extremo(self):
        # Una net con un solo pin es casi siempre un typo, y el ERC la reporta
        # recien al generar el esquematico. Se exceptuan los rieles, los
        # testpoints y los GPIO libres del MCU (EXP_GP*, sin header ni otro
        # consumidor desde que se elimino el header de expansion), que
        # legitimamente pueden tener un solo consumidor.
        from collections import Counter
        cuenta = Counter()
        for inst in netlist.INSTANCES:
            for net in inst[5].values():
                if net != netlist.NC:
                    cuenta[net] += 1
        exentas = {"GND", "3V3", "5V", "VSYS", "VBUS"}
        huerfanas = sorted(n for n, c in cuenta.items()
                           if c < 2 and n not in exentas
                           and not n.startswith("TP_")
                           and not n.startswith("EXP_"))
        self.assertEqual(huerfanas, [], f"nets con un solo extremo: {huerfanas}")

    def test_toda_funcion_del_pinmap_llega_a_algun_componente(self):
        # Si un GPIO se asigna en pinmap pero nadie lo consume, es una funcion
        # que quedo sin cablear.
        consumidores = Counter_de_nets()
        for func in pinmap.GPIO.values():
            self.assertGreaterEqual(
                consumidores.get(func, 0), 2,
                f"{func}: solo llega al MCU, no lo consume nadie")


class TestGuardaDeColisiones(unittest.TestCase):
    """gen_sch conecta por global labels en el extremo de cada pin. Si dos
    pines de simbolos distintos caen en el mismo punto, quedan unidos y sus
    nets se fusionan. KiCad no lo llama error —solo avisa "multiple net
    names"— asi que la netlist que sale hacia la PCB ya viene con un
    cortocircuito y nada lo bloquea."""

    def test_acepta_el_netlist_real(self):
        # Se verifica HOJA POR HOJA, que es como lo corre el generador: dos
        # pines en hojas distintas no se tocan aunque compartan coordenada.
        import gen_sch
        porRef = {i[1]: i for i in netlist.INSTANCES}
        for idx, (_n, titulo, refs, _x) in enumerate(gen_sch.HOJAS):
            colocadas, _w, _h = gen_sch._layout_hoja(
                [porRef[r] for r in refs])
            gen_sch.verificar_colisiones(colocadas)   # no debe levantar

    def test_detecta_dos_resistencias_que_se_tocan(self):
        # Caso real que aparecio al generar: R1/R2/R3 estaban a 10mm y el
        # simbolo mide 10.16mm entre pines, asi que 3V3 se fusiono con
        # I2C_SDA y con I2C_SCL.
        import gen_sch
        fake = [
            ("R", "RX", "1k", 100.0, 50.0,
             {"1": "NET_A", "2": "NET_B"}, {"FP": netlist.R_FP}),
            ("R", "RY", "1k", 110.16, 50.0,
             {"1": "NET_C", "2": "NET_D"}, {"FP": netlist.R_FP}),
        ]
        with self.assertRaises(SystemExit):
            gen_sch.verificar_colisiones(fake)

    def test_no_se_queja_si_las_nets_coinciden(self):
        # Dos pines de la MISMA net superpuestos no son un cortocircuito.
        import gen_sch
        fake = [
            ("R", "RX", "1k", 100.0, 50.0,
             {"1": "NET_A", "2": "GND"}, {"FP": netlist.R_FP}),
            ("R", "RY", "1k", 110.16, 50.0,
             {"1": "GND", "2": "NET_D"}, {"FP": netlist.R_FP}),
        ]
        gen_sch.verificar_colisiones(fake)   # no debe levantar

    def test_la_celda_es_mas_ancha_que_el_simbolo_mas_grande(self):
        # La celda de la grilla tiene que dar mas luz que el simbolo que
        # contiene, o el cortocircuito vuelve en cuanto se agregue una pieza.
        # w y h del simbolo son SEMIEJES, de ahi el factor 2.
        import gen_sch
        porRef = {i[1]: i for i in netlist.INSTANCES}
        for _n, titulo, refs, _x in gen_sch.HOJAS:
            instancias = [porRef[r] for r in refs]
            w = max(netlist.SYMS[i[0]]["w"] for i in instancias)
            h = max(netlist.SYMS[i[0]]["h"] for i in instancias)
            colocadas, _cw, _ch = gen_sch._layout_hoja(instancias)
            xs = sorted({c[3] for c in colocadas})
            ys = sorted({c[4] for c in colocadas})
            if len(xs) > 1:
                self.assertGreater(min(b - a for a, b in zip(xs, xs[1:])),
                                   2 * w, titulo)
            if len(ys) > 1:
                self.assertGreater(min(b - a for a, b in zip(ys, ys[1:])),
                                   2 * h, titulo)


class TestRepartoEnHojas(unittest.TestCase):
    """El esquematico va en cinco hojas, una por bloque funcional, para que se
    pueda revisar de a partes. El reparto es una tabla escrita a mano, asi que
    agregar una pieza a netlist.py y olvidar asignarla la dejaria fuera del
    esquematico — presente en la placa y en ningun plano."""

    def test_cada_instancia_esta_en_exactamente_una_hoja(self):
        import gen_sch
        gen_sch.verificar_reparto()   # no debe levantar

    def test_detecta_una_pieza_sin_hoja(self):
        import gen_sch
        original = gen_sch.HOJAS
        try:
            gen_sch.HOJAS = [(n, t, r[1:] if i == 0 else r, x)
                             for i, (n, t, r, x) in enumerate(original)]
            with self.assertRaises(SystemExit):
                gen_sch.verificar_reparto()
        finally:
            gen_sch.HOJAS = original

    def test_las_notas_que_nombran_las_hojas_existen(self):
        import gen_sch
        for _n, titulo, _r, claves in gen_sch.HOJAS:
            for clave in claves:
                self.assertIn(clave, gen_sch.NOTAS, titulo)


def Counter_de_nets():
    from collections import Counter
    c = Counter()
    for inst in netlist.INSTANCES:
        for net in inst[5].values():
            if net != netlist.NC:
                c[net] += 1
    return c


if __name__ == "__main__":
    unittest.main()
