# Jacks MIDI fuera de la placa (etapa 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Every task that touches `hardware/pikocore_gamepad/pcb/` also runs under the project skill `pcb-verify`.

**Goal:** sacar de la placa el bloque MIDI por jacks (J6, J7, U9, U10, R40-R43, D3, C56), dejar GP27 y GP28 libres en placa y firmware, re-rutear, y dejar el paquete de fabricacion listo para pedirle a JLCPCB las 5 placas armadas.

**Architecture:** el cambio electrico se hace en las fuentes del pipeline (`pinmap.py`, `netlist.py`, `gen_sch.py`, `placements.py`) con sus tests primero; el firmware pierde los pines y el codigo DIN con la puerta G-4 como prueba; despues se regenera todo con `route_cycle.sh` (gen_sch, netlist, gen_pcb, pistas manuales, vias de plano, freerouting, finish, DRC) y se cierra con el reporte de pcb-verify y `gen_fab.py`.

**Tech Stack:** KiCad 9.0.1 (`/c/Program Files/KiCad/9.0/bin/python.exe` y `kicad-cli.exe`), freerouting 2.5.0 (Java), Pico SDK 2.1.1 con la receta `C:\pkb\build.bat`.

**Spec:** `docs/superpowers/specs/2026-11-05-usb-midi-audio-design.md`, seccion "Etapa 2".

## Global Constraints

- Rama `hw/sin-jacks-midi` cortada de `fw/usb-midi-in` (PR #6, abierto): las dos tocan el mismo bloque de `src/main.cpp`. El PR va contra `main` cuando #6 este mergeado; si no, contra `fw/usb-midi-in`.
- El placement de las 66 piezas que quedan no se mueve. Ninguna posicion ni rotacion cambia.
- Nada se edita a mano en la GUI de KiCad: `gen_pcb.py` reconstruye la placa desde cero.
- Orden del ciclo, sin saltear: `manual_tracks.py` y `plane_vias.py` van antes del export a freerouting (ya costo 12 cortocircuitos hacerlo al reves). `route_cycle.sh` ya lo respeta.
- Los 22 µF de C5, C6 y C28 pasan de C45783 (Samsung CL21A226MAQNNNE, Basic, stock 0 en LCSC el 2026-11-05) a **C602037** (Samsung CL21A226MAYNNNE, misma serie, 22 µF 25 V X5R ±20 % 0805, 408 460 en stock, extendida o extendida preferida, US$0.108 a 10). Cuesta hasta US$3.07 de carga por pedido; si C45783 vuelve a tener stock antes de pedir, volver a C45783 ahorra eso.
- `clock_input_ittybittymidi` sigue fijo en MIDI en el gamepad: la unica sincronia externa es MIDI por USB, y el icono de la pantalla queda en MIDI, que es lo cierto.
- Los comentarios historicos que nombran MIDI (`params.py:128`, `gen_pcb.py:538`) quedan como estan.
- El README raiz no cambia: sus menciones de MIDI son creditos del receptor de un hilo, que el GamePi13 sigue usando.
- `pikocore_gamepad_template_MOD.dxf` no se toca ni se pasa por `parse_dxf.py --write`: esta viejo (contorno 120 × 80, trae SW13 del NAV5) y aplicarlo romperia el placement. Se reporta aparte.
- En los comandos, `KIPY="/c/Program Files/KiCad/9.0/bin/python.exe"` y `KICLI="/c/Program Files/KiCad/9.0/bin/kicad-cli.exe"`; los de la placa corren desde `hardware/pikocore_gamepad/pcb`.
- Commits terminan con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- **freerouting 2.5.0 en lugar de 2.4.1:** los flags `-de -do -mp -mt -l` pueden haber cambiado y el ruteo puede dejar nets abiertas. Se espera 0 sin conectar despues de la segunda pasada; si no, se repite el ciclo, que es estocastico, y nunca se rutea a mano. Paso 3 de la Tarea 3.
- **Cobre nuevo en las bandas del borde superior:** los planos rellenan donde estaban los jacks; no tienen que aparecer islas ni avisos nuevos en el DRC. La lista de avisos solo puede bajar respecto de los 15 de hoy. Paso 4 de la Tarea 3.
- **GP27 y GP28 del modulo sin conexion:** en el esquematico tienen que quedar con marca de no conexion, sin avisos de ERC nuevos; el firmware no los toca. Test `test_los_gpio_libres_quedan_sin_conectar` (ya existe, recorre `pinmap.FREE`) en la Tarea 1 y paso 4 de la Tarea 3.
- **El DXF del gabinete:** `parse_dxf.py` agrega a la tabla toda cruz que no conoce, asi que el template regenerado no puede traer J6 ni J7, ni cruces de piezas que no existen. Paso 5 de la Tarea 3.
- **El reemplazo del 22 µF:** mismo 0805, misma serie y misma tension; el BOM tiene que mostrar C602037 en la linea de C5, C6 y C28 y ningun C45783. Test en la Tarea 1 y paso 6 de la Tarea 3.

---

### Task 1: el bloque MIDI fuera de las fuentes de la placa

**Files:**
- Modify: `hardware/pikocore_gamepad/pcb/pinmap.py:10-13, 68-75`
- Modify: `hardware/pikocore_gamepad/pcb/netlist.py:243-279` (simbolos `D_1N4148`, `H11L1`, `LVC1G17`), `:668-708` (bloque MIDI), `:736-739` (LCSC de 10R, 33R, 220R), y la entrada `("22uF", C0805_FP)`
- Modify: `hardware/pikocore_gamepad/pcb/gen_sch.py:119-122` (hoja), `:265-267` (nota raiz), `:365-381` (`NOTA_MIDI`)
- Modify: `hardware/pikocore_gamepad/pcb/placements.py:42, 81-110`
- Test: `hardware/pikocore_gamepad/pcb/tests/test_pinmap.py:36-47, 147`, `hardware/pikocore_gamepad/pcb/tests/test_netlist.py:455-470, 1213-1300`
- Delete: `hardware/pikocore_gamepad/pcb/07_midi.kicad_sch`

**Interfaces:**
- Produces: `pinmap.FREE == (26, 27, 28)`; `pinmap.GPIO` sin las claves 27 y 28; ninguna instancia de `netlist.INSTANCES` con referencia J6, J7, U9, U10, R40, R41, R42, R43, D3 o C56, ni con nets `MIDI_*`; `netlist.LCSC_PASIVOS[("22uF", C0805_FP)] == "C602037"`.

- [ ] **Step 1: crear la rama**

```bash
git switch -c hw/sin-jacks-midi fw/usb-midi-in
```

- [ ] **Step 2: escribir los tests que fallan**

En `tests/test_pinmap.py`, reemplazar `test_midi_usa_gp27_y_gp28` y `test_midi_tx_es_un_pin_tx_de_uart0` por:

```python
def test_gp26_a_gp28_quedan_libres(self):
    # Sin jacks MIDI (spec 2026-11-05, etapa 2): el MIDI va por USB.
    self.assertEqual(pinmap.FREE, (26, 27, 28))
    for g in (27, 28):
        self.assertNotIn(g, pinmap.GPIO)
```

y corregir la aserción vieja `pinmap.FREE == (26,)` y el comentario de la linea 147.

En `tests/test_netlist.py`, borrar `class TestMidi` entera, sacar J6 y J7 de `test_los_jacks_estan_donde_dice_el_spec` (queda J1, comentario al dia) y agregar:

```python
class TestSinMidi(unittest.TestCase):
    """Etapa 2 de la spec 2026-11-05: el MIDI va por el USB-C del modulo."""
    MIDI = {"J6", "J7", "U9", "U10", "R40", "R41", "R42", "R43", "D3", "C56"}

    def test_no_queda_ninguna_pieza_del_midi(self):
        refs = {i[1] for i in netlist.INSTANCES}
        self.assertFalse(refs & self.MIDI, sorted(refs & self.MIDI))

    def test_no_queda_ninguna_net_midi(self):
        nets = {n for i in netlist.INSTANCES for n in i[5].values()}
        self.assertFalse({n for n in nets if n.startswith("MIDI_")})

    def test_el_22uF_es_el_que_tiene_stock(self):
        self.assertEqual(netlist.LCSC_PASIVOS[("22uF", netlist.C0805_FP)], "C602037")
```

(si `C0805_FP` no se exporta con ese nombre en `netlist`, usar el que use la tabla.)

- [ ] **Step 3: correr y ver que fallan**

Run: `cd hardware/pikocore_gamepad/pcb && "$KIPY" -m unittest tests.test_pinmap tests.test_netlist 2>&1 | tail -5`
Expected: FAIL en `test_gp26_a_gp28_quedan_libres` y en los tres de `TestSinMidi`.

- [ ] **Step 4: editar las fuentes**

- `pinmap.py`: sacar `27: "MIDI_RX"` y `28: "MIDI_TX"`, `FREE = (26, 27, 28)`, docstring y comentario de `FREE` al dia (GP26 libre desde el modulo de 7 pines, GP27/28 desde 2026-11-05).
- `netlist.py`: sacar el bloque `# MIDI` de `INSTANCES` con su diagrama, los simbolos `D_1N4148`, `H11L1` y `LVC1G17` (solo los usaba el MIDI), y las tres entradas de LCSC del MIDI; cambiar la entrada del 22 µF a `"C602037"` con un comentario: misma serie que C45783, que estaba sin stock el 2026-11-05.
- `gen_sch.py`: sacar la hoja `07_midi` de `HOJAS`, la linea `MIDI IN/OUT en TRS tipo A (hoja 7).` de la nota raiz, "seis hojas" pasa a "cinco hojas", y `NOTA_MIDI`.
- `placements.py`: sacar las diez filas y sus comentarios; el comentario de la linea 42 deja de nombrar los jacks MIDI.
- `git rm 07_midi.kicad_sch`.

- [ ] **Step 5: correr y ver que pasan**

Run: `"$KIPY" -m unittest tests.test_pinmap tests.test_netlist 2>&1 | tail -3`
Expected: `OK`.

- [ ] **Step 6: regenerar el esquematico y su netlist**

Run:
```bash
"$KIPY" gen_sch.py | tail -8
"$KICLI" sch export netlist -o pikocore_gamepad.net pikocore_gamepad.kicad_sch
"$KICLI" sch erc --severity-all --exit-code-violations -o logs/erc.rpt pikocore_gamepad.kicad_sch; echo "erc exit=$?"
```
Expected: `gen_sch.py` lista cinco hojas mas el indice y no levanta `REPARTO DE HOJAS MAL`; ERC exit 0 (0 errores, 0 avisos).

- [ ] **Step 7: commit**

```bash
git add -A pinmap.py netlist.py gen_sch.py placements.py tests/test_pinmap.py tests/test_netlist.py *.kicad_sch pikocore_gamepad.kicad_sym pikocore_gamepad.net
git commit -m "hw: el bloque MIDI por jacks fuera de las fuentes de la placa"
```

### Task 2: el firmware pierde los pines y el codigo DIN

**Files:**
- Modify: `src/boards/pikocore_gamepad/config.h:13, 40-41`
- Modify: `src/hw_gamepi13.h:19-22`
- Modify: `src/main.cpp:525, 1871, 1889-1906, 2045-2049`, y el comentario del setter `piko_set_clock_input_ittybittymidi`
- Modify: `doth/midi_out.h` (rama `#if PIKO_GAMEPAD`)

**Interfaces:**
- Consumes: `pinmap.FREE == (26, 27, 28)` de la Tarea 1.
- Produces: ningun `PIN_MIDI_*` en el firmware; en el gamepad `onewiremidi` queda `NULL` (`CLOCK_PIN` es -1) y `MidiOut_send` solo escribe al USB.

- [ ] **Step 1: ver fallar la puerta G-4**

Run: `cd hardware/pikocore_gamepad/pcb && "$KIPY" checks/check_pinmap.py; echo "exit=$?"`
Expected: exit distinto de 0, nombrando `PIN_MIDI_TX` y `PIN_MIDI_RX` como pines que la PCB no conoce.

- [ ] **Step 2: editar el firmware**

- `config.h`: sacar las dos lineas `PIN_MIDI_*`; el comentario de la linea 13 dice que GP26-GP28 quedan libres.
- `hw_gamepi13.h`: el comentario de `GAMEPI_CLOCK_PIN`/`GAMEPI_TRIGO_PIN` dice que la placa no tiene jacks de reloj, disparo ni MIDI; GP26-GP28 libres.
- `main.cpp`: sacar el bloque `#if PIKO_GAMEPAD` del jack MIDI IN y OUT en la configuracion de GPIO (inversion de GP27, `uart_init`, funcion UART en GP28); en la creacion del receptor queda solo `const int midi_in_pin = CLOCK_PIN;` (sin el `#if`); los comentarios de la linea 525, la linea 1871 y el setter dicen que la sincronia externa es MIDI por USB.
- `midi_out.h`: sacar la rama `#if PIKO_GAMEPAD` de la UART; `MidiOut_send` queda con el USB.

- [ ] **Step 3: G-4 en verde**

Run: `"$KIPY" checks/check_pinmap.py; echo "exit=$?"`
Expected: `OK: 23 pines coinciden entre PCB y firmware.` y exit 0 (hoy dice 25).

- [ ] **Step 4: compilar los dos targets y el chequeo de host**

Run (desde la raiz del repo):
```bash
cmd //c "C:\pkb\build.bat C:\pkb\g13b g13 C:/pikocore_gamepad"
cmd //c "C:\pkb\build.bat C:\pkb\gp4 gp C:/pikocore_gamepad"
cmd //c 'C:\pikocore_gamepad\tests\firmware\run_checks.bat'
grep -n "PIN_MIDI\|uart0" src doth -r
```
Expected: `BUILD OK` dos veces, `check_usb_midi_in OK`, y el grep vacio.

- [ ] **Step 5: commit**

```bash
git add src/boards/pikocore_gamepad/config.h src/hw_gamepi13.h src/main.cpp doth/midi_out.h
git commit -m "fw: sin jacks MIDI en el gamepad, GP27 y GP28 libres"
```

### Task 3: re-rutear, verificar y generar fabricacion

**Files:**
- Modify: `hardware/pikocore_gamepad/pcb/route_cycle.sh:9`
- Regenerated: `pikocore_gamepad.kicad_pcb`, `*.kicad_sch`, `pikocore_gamepad.net`, `pikocore_gamepad_template.dxf`, `logs/erc.log`, y `fab/` (no versionado)

**Interfaces:**
- Consumes: las fuentes de la Tarea 1.

- [ ] **Step 1: el jar de freerouting**

En `route_cycle.sh`, `JAR` apunta a `freerouting-2.5.0.jar` en el mismo directorio.
Run: `java -jar "$HOME/Documents/KiCad/10.0/3rdparty/plugins/app_freerouting_kicad-plugin/jar/freerouting-2.5.0.jar" --help 2>&1 | grep -E -- "-de|-do|-mp|-mt" | head`
Expected: los cuatro flags siguen existiendo. Si alguno cambio, el script se ajusta a la ayuda de la 2.5.0 y se anota como ruling.

- [ ] **Step 2: correr el ciclo completo**

Run (en segundo plano, tarda minutos): `bash route_cycle.sh > logs/ciclo.log 2>&1`
Expected: termina con `== CICLO DONE` y `read_drc.py` con 0 errores y 0 sin conectar. Si quedan nets abiertas despues de la segunda pasada, correr el ciclo otra vez; si tres corridas no cierran, parar y reportar.

- [ ] **Step 3: leer los logs de freerouting**

Run: `tail -5 logs/freerouting.log; grep -a "SES import" logs/import.log`
Expected: freerouting termino sin error de argumentos y el import trae pistas.

- [ ] **Step 4: pcb-verify completo**

Correr las puertas en el orden de la skill: G-F, T, `checks/run_all.py`, ERC, DRC con `--schematic-parity` y `read_drc.py`.
Expected: todo en verde; `run_all.py` con 66 piezas; G-4 con 23 pines; DRC 0 errores, 0 sin conectar, 0 paridad, y a lo sumo los 15 avisos de hoy, sin tipos nuevos.

- [ ] **Step 5: el DXF del gabinete**

Run:
```bash
"$KIPY" gen_template_dxf.py | tail -2
grep -c "J6\|J7" pikocore_gamepad_template.dxf
"$KIPY" parse_dxf.py pikocore_gamepad_template.dxf | grep -v -i swig | tail -5
```
Expected: el template no nombra J6 ni J7 (cuenta 0), y el dry run sobre el template recien generado dice `0 movidos, 17 sin cambio, 0 nuevos en la tabla` (hoy: 19 sin cambio, con J6 y J7), con contorno 100.00 x 60.00. Nunca `--write`.

- [ ] **Step 6: paquete de fabricacion**

Run: `"$KIPY" gen_fab.py | tail -6; grep -c "C45783" fab/pikocore_gamepad_BOM.csv; grep "C602037" fab/pikocore_gamepad_BOM.csv; tail -n +2 fab/pikocore_gamepad_CPL.csv | wc -l`
Expected: zip sin sufijo `NO-FABRICABLE`; 38 lineas de BOM, 17 sin LCSC; C45783 0 veces; la linea de C5, C6, C28 con C602037; 47 piezas en el CPL. G-F despues: todo al dia.

- [ ] **Step 7: commit**

```bash
git add route_cycle.sh pikocore_gamepad.kicad_pcb *.kicad_sch pikocore_gamepad.net pikocore_gamepad_template.dxf logs/erc.log
git commit -m "hw: placa re-ruteada sin los jacks MIDI"
```

### Task 4: documentacion

**Files:**
- Modify: `hardware/pikocore_gamepad/README.md` (estado en main, numeros de las puertas, parrafo del MIDI, puntos abiertos)
- Modify: `docs/hardware/pikocore_gamepad-pinout.md:41-42` y la lista de pines libres
- Modify: `docs/hardware/pikocore_gamepad-jlcpcb-checklist.md` (encabezado, lista de piezas a mano, notas de MIDI)
- Modify: `docs/superpowers/specs/2026-11-05-usb-midi-audio-design.md` (linea de estado: etapa 1 en PR #6, etapa 2 hecha)

- [ ] **Step 1: actualizar los cuatro documentos**

Con los numeros reales de la Tarea 3, no los esperados: piezas, tests, conexiones de G-2, pines de G-4, avisos de DRC, lineas de BOM y piezas de CPL. El README de hardware deja de describir J6/J7 y dice que el MIDI va por el USB-C del modulo; el checklist de JLCPCB pide armar las 5 placas, nombra el cambio a C602037 y la vuelta a C45783 si recupera stock.

- [ ] **Step 2: no quedan menciones vivas**

Run: `grep -n -i "J6\|J7\|H11L1\|LVC1G17\|MIDI IN jack\|MIDI OUT jack" hardware/pikocore_gamepad/README.md docs/hardware/pikocore_gamepad-pinout.md docs/hardware/pikocore_gamepad-jlcpcb-checklist.md`
Expected: solo lineas que hablan del pasado ("hasta el 2026-11-05", "en la historia").

- [ ] **Step 3: commit y PR**

```bash
git add hardware/pikocore_gamepad/README.md docs/hardware/pikocore_gamepad-pinout.md docs/hardware/pikocore_gamepad-jlcpcb-checklist.md docs/superpowers/specs/2026-11-05-usb-midi-audio-design.md docs/superpowers/plans/2026-11-05-sin-jacks-midi.md
git commit -m "docs: la placa sin jacks MIDI"
```

Con el visto bueno del usuario: push de `hw/sin-jacks-midi` y PR (base segun Global Constraints), con el reporte de pcb-verify en el cuerpo, incluida la seccion "Lo que NINGUNA puerta verifico". El cuerpo termina con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
