# Pantalla de 7 pines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Reemplazar el panel DM-TFT13-377 de 24 pines (FPC) por el modulo IPS 1.3" ST7789 de 7 pines, y dejar la placa ruteada, con DRC limpio y G-0 sin el pendiente del flex.

**Architecture:** Mismo pipeline Python de KiCad (pinmap -> netlist -> gen_sch -> gen_fp/gen_pcb + placements -> manual_tracks -> plane_vias -> route_cycle.sh). Se quita el bloque FPC/backlight y se agrega una huella pasante de 7 pines recuperada del historial.

**Tech Stack:** KiCad 9 scripting, freerouting 2.4.1, unittest.

**Spec:** `docs/superpowers/specs/2026-10-17-pantalla-7-pines-design.md` (autoridad; leerla primero).

## Global Constraints

- Placa 100 x 60 mm; modulo RP2350-Plus soldado plano al dorso, caja `MODULE_BOX = (38.9, 7.5, 61.1, 58.5)`: ninguna pata pasante ni SMD bajo ella.
- Pines del modulo, 1 a 7: GND, 3V3, `LCD_SCK`, `LCD_MOSI`, `LCD_RES`, `LCD_DC`, `LCD_BLK`.
- Geometria de la huella (origen = pin 1): placa x -6.27..21.51, y -1.27..37.95; pines en y=0, x = 0..15.24 paso 2.54, pad 1.7, taladro 1.0; area activa x -4.08..19.32, y 5.06..28.46; agujeros de 2.0 mm en (-3.77,1.23), (19.01,1.23), (-3.77,35.45), (19.01,35.45) **solo como dibujo, sin taladrar**.
- Centro del area activa en (50.0, 22.5): pin 1 en (42.38, 5.74).
- Pads a >= 1.0 mm del borde de la placa. Nunca ajustar reglas de DRC para esconder un error.
- Commits en espanol sin acentos, trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. No hacer push.

## Review Focus

- El orden de los pines de la huella contra las nets (pin 1 = GND ... pin 7 = BLK) y contra las etiquetas del dibujo.
- Que no quede ninguna referencia al panel de 24 pines, a R21/Q1/R22/C30/C31, a `LCD_TE` ni a `LCD_FPC_PIN_ORDER` (codigo, esquema, firmware, docs).
- Que ninguna pata pasante del modulo de pantalla caiga dentro de `MODULE_BOX` (margen esperado 0.9 mm).
- Que `config.h` y `pinmap.py` coincidan (G-4) y que el firmware no use GP26 como TE.
- Que los docs no afirmen "fabricable" mientras queden parametros sin verificar.

---

### Task 1: Pines, netlist, esquema, parametros y firmware

**Files:**
- Modify: `pcb/pinmap.py`, `pcb/params.py`, `pcb/netlist.py`, `pcb/gen_sch.py`, `src/boards/pikocore_gamepad/config.h`, `pcb/tests/test_pinmap.py`, `pcb/tests/test_params.py`, `pcb/tests/test_netlist.py`, `pcb/tests/test_fp_geometry.py`, `pcb/PARTES.md`
- Delete: simbolos y huellas del conector FPC y del panel si quedan huerfanos (`lib/gamesetup_lcsc.pretty/FPC-SMD_24P-P0.50_FPC-05FB-24PH20.*`).

**Interfaces:**
- Produces: instancia `J4` de tipo `LCD_ST7789` con footprint `gamesetup_fp:LCD_ST7789_240x240_7P` (nets pin 1..7 como en Global Constraints, `"MANUAL": True`), sin `LCD1`, `R21`, `Q1`, `R22`, `C30`, `C31`, ni el simbolo `LCD_FPC24`/`LCD_PANEL`; `pinmap.GPIO` sin 26 y `FREE == (26,)`; parametros `LCD7_*` (placa, pines, area activa, agujeros) con `verified=True` salvo `LCD7_PIN_ROW_TO_EDGE` (1.27) y `LCD7_PIN_DRILL` (1.0), `verified=False`; `LCD_FPC_PIN_ORDER` y `PANEL_*` eliminados.

- [ ] **Step 1: Tests que fallan.** En test_pinmap: GP26 ya no esta asignado y `FREE == (26,)`. En test_netlist: `nets_of("J4")` igual a `{"1":"GND","2":"3V3","3":"LCD_SCK","4":"LCD_MOSI","5":"LCD_RES","6":"LCD_DC","7":"LCD_BLK"}`; ninguna instancia con ref en {LCD1,R21,Q1,R22,C30,C31}; test_params: `LCD_FPC_PIN_ORDER` no existe y los dos `LCD7_*` no verificados son exactamente los esperados. Correrlos: deben fallar.
- [ ] **Step 2: Implementar** los cambios de los archivos listados: instancias, simbolo del modulo de 7 pines, nota de la hoja 02 (CS a GND lo hace el modulo; backlight directo en `LCD_BLK`), `config.h` sin `PIN_LCD_TE`, tests de geometria de la huella adaptados a los `LCD7_*`. Regenerar esquema y netlist (`gen_sch.py`, `kicad-cli sch export netlist`); ERC debe dar 0/0.
- [ ] **Step 3: Verificar.** Suite en verde salvo los tests de colocacion que Task 2 corrige; `checks/check_pinmap.py` OK (G-4); ERC 0/0.
- [ ] **Step 4: Commit** `hw: pantalla de 7 pines en el esquema (sin FPC, backlight ni TE)`.

### Task 2: Huella, colocacion y comprobaciones

**Files:**
- Modify: `pcb/gen_fp.py`, `pcb/placements.py`, `pcb/gen_pcb.py` (si hace falta), `pcb/checks/check_placement.py`, `pcb/tests/test_netlist.py`
- Create: `pcb/lib/gamesetup_fp.pretty/LCD_ST7789_240x240_7P.kicad_mod` (generada por gen_fp.py desde los `LCD7_*`; la forma se recupera de `git show 4d66184~1:hardware/pikocore_gamepad/pcb/lib/gamesetup_fp.pretty/LCD_ST7789_240x240_7P.kicad_mod`, sin pads NPTH: los agujeros van solo como dibujo en `Cmts.User`/`F.Fab`).

**Interfaces:**
- Produces: `placements.PLACEMENTS` con `J4` en (42.38, 5.74) rot 0 y sin `LCD1`; huella con pines 1..7, el contorno de la placa en `F.Fab`/`F.CrtYd` y el area activa en `Cmts.User`.

- [ ] **Step 1: Tests que fallan.** Pad por pad de la huella (posiciones y nombres pinfunction), ninguna pad NPTH, y un test que `J4` esta en (42.38, 5.74) y que ninguna pad pasante de J4 cae dentro de `MODULE_BOX` (margen >= 0.9 mm). Fallan.
- [ ] **Step 2: Implementar** el generador de la huella en gen_fp.py (parametrizado por `LCD7_*`), colocar J4, quitar el frente del panel (LCD1, J4 FPC) de placements, revisar que el empaquetador de pasivos no deje partes sin sitio (`gen_pcb.py` sin "AVISO ... sin lugar"), y que `check_placement.py` siga marcando patas bajo el modulo RP2350. Si alguna pieza del frente cae bajo el cuerpo del modulo de pantalla (x 36.11..63.89, y 4.47..43.69) o una pata de J4 choca con las bandas de los jacks, reubicar la pieza y registrar el cambio.
- [ ] **Step 3: Verificar.** `gen_pcb.py`, `manual_tracks.py`, `plane_vias.py` sin ERROR; `check_placement.py` OK; DRC previo al ruteo solo con los avisos esperados de zonas internas; render del frente (`kicad-cli pcb render --side top`) leido y descrito: el cuerpo del modulo cabe entre cruz y rombo.
- [ ] **Step 4: Commit** `hw: huella del modulo de 7 pines y colocacion arriba, entre los jacks`.

### Task 3: Rutear hasta DRC limpio

**Files:**
- Modify: `pcb/placements.py`, `pcb/manual_tracks.py` solo si una net no se puede rutear.

- [ ] **Step 1: Un ciclo.** `bash route_cycle.sh > logs/cycle.log 2>&1 &` desde `pcb/`, esperar `CICLO DONE` sin sondeo corto.
- [ ] **Step 2: Leer.** Condicion de exito: DRC 0 errores, `unconnected_items` 0, `schematic_parity` 0.
- [ ] **Step 3: Si quedan nets abiertas**, mover la pieza mas chica a un hueco o rutear a mano el par de pines finos relativo a su huella; nunca tocar reglas. Tras cuatro ciclos con nets abiertas, detenerse e informar con un grafico.
- [ ] **Step 4: Commit** `hw: ruteo con la pantalla de 7 pines (DRC 0 errores, 0 sin conectar)`.

### Task 4: Puertas, paquete de fab y documentos

**Files:**
- Modify: `hardware/pikocore_gamepad/README.md`, `docs/hardware/pikocore_gamepad-pinout.md`, `docs/hardware/pikocore_gamepad-jlcpcb-checklist.md`, el spec de la pantalla (estado), memoria `chipdown-descartado.md` si corresponde.

- [ ] **Step 1: Todas las puertas.** Suite; `checks/run_all.py`; ERC; DRC con paridad leido con `read_drc.py`; `gen_fab.py --force`; `gen_template_dxf.py` (contorno 100 x 60); `check_freshness.py`. Pegar conteos reales. G-0 debe quedar en rojo solo por `LCD7_PIN_ROW_TO_EDGE` y `LCD7_PIN_DRILL` (los dos por medir); el paquete se llama `NO-FABRICABLE` mientras eso siga.
- [ ] **Step 2: Render de ambos lados** a `logs/` y leerlos.
- [ ] **Step 3: Docs.** README: parrafo de estado de la rama; quitar toda mencion vigente al panel de 24 pines; pinout y checklist al dia (la lista de LCSC faltantes baja: ya no estan R21 ni el panel FPC). Aclarar que los 2 parametros por medir se miden con el modulo en mano.
- [ ] **Step 4: Commit** `hw: puertas, paquete de fab y docs de la pantalla de 7 pines`.
