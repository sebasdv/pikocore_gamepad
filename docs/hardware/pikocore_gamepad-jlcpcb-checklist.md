# pikocore_gamepad — qué falta antes de mandar a JLCPCB

Estado al **2026-08-12**, rama `pikocore-gamepad-hardware`. Generado a partir de
`checks/check_verified.py` (gate G-0, corrido en vivo) más lo que ese gate **no**
cubre. Nada acá es de la lista heredada de GAMESETUP que ya no aplica (MIDI, microSD,
PCF8574, opto) — filtrado para que sea el checklist real de este proyecto.

## 0. El bloqueante más grande: la placa no está ruteada

```
tracks: 0   vias: 0
```

Todo lo de abajo (footprints, medidas, valores de componentes) puede cerrarse y la
placa **seguiría sin poder fabricarse** hasta correr el ciclo de ruteo:

```bash
"$KIPY" gen_pcb.py
"$KIPY" route_io.py export
java -jar freerouting.jar -de pikocore_gamepad.dsn -do pikocore_gamepad.ses -mp 50
"$KIPY" route_io.py import
"$KIPY" finish_pcb.py
"$KICLI" pcb drc --severity-all --format json pikocore_gamepad.kicad_pcb -o logs/drc.json
```

(mismo flujo que documentó GAMESETUP en su día — ver `PENDIENTES.md` §5, con los
nombres de archivo ya actualizados a `pikocore_gamepad.*`). Conviene hacerlo
**después** de cerrar la sección 1 y 2: el contorno definitivo y los footprints
reales cambian la geometría, y el ruteo habría que rehacerlo igual si se hace antes.

## 1. Contorno de la placa (gate V-0)

| Constante | Valor actual | Estado |
|---|---|---|
| `BOARD_W` | 90.0mm | **PROVISIONAL** |
| `BOARD_H` | 105.0mm | **PROVISIONAL** (bajado de 130 al mover el D-pad→NAV5 y el parlante — ver `2026-08-11-pikocore-gamepad-nav5-speaker-reloc-design.md`) |

Es un rectángulo de partida para que el pipeline genere algo válido, no la forma
real del enclosure. Falta: dibujar el contorno definitivo en Rhino y traerlo con
`parse_dxf.py` (`gen_template_dxf.py` → editar en Rhino → `parse_dxf.py --write` →
`gen_pcb.py`).

## 2. Partes sin elegir todavía (bloquean G-0 mientras el footprint sea provisional)

### 2.1 Jack de audífonos (`JACK_FP`) — el más delicado

Hoy usa un header de 4 pines como stand-in; la geometría **no** es la de un jack
real. Requisitos, en orden: **THT · 3.5mm estéreo · contacto NC aislado · datasheet
público descargable**. Candidato primario: **CUI SJ1-3535NG**. Alternativa: familia
**PJ-313D**. (El `PJ-320A` que usaba GAMESETUP quedó descartado: LCSC bloquea su
datasheet con un 403, nunca se pudo verificar pin→función — no reintroducirlo.)

Falta: código LCSC + mapeo tip/ring/sleeve/detección confirmado contra datasheet.

### 2.2 Tact vertical 6×6 THT (`BTN_FP`) — **6 unidades** (X/Y/A/B, Start, Select)

Hoy usa el footprint 4.5×4.5mm de respaldo. Buscar **100–160 gf** de fuerza de
actuación (no 260gf — cansa en patrones rápidos). Atajo: si la parte elegida
coincide con `Button_Switch_THT:SW_PUSH_6mm` (pads 4.5×6.5mm, ya viene con KiCad),
`BTN_FP` deja de ser provisional sin tocar nada más.

### 2.3 Tact angulado L/R (`BTN_RA_FP`) — **2 unidades**

Footprint ya resuelto: `SW_Tactile_SPST_Angled_PTS645Vx39-2LFS` (viene con KiCad).
Falta el número de parte concreto — el largo del actuador (variantes
Vx31/39/58/83) se decide con el enclosure, no ahora, porque comparten exactamente la
misma geometría de pads.

⚠️ Tiene **2 pines eléctricos**, no 4 — los otros dos contactos del footprint son
anclaje mecánico. Un angulado de 4 pines cambiaría el símbolo.

### 2.4 Op-amp SOIC-8 (`OPAMP_FP`) — **1 unidad**

El LCSC `C2838125` que está cargado es el NJM4556AD en **DIP-8**; para SMD hace
falta la versión **SOIC-8** (`NJM4556AM` o equivalente) — es otra parte, con su
propio código LCSC.

## 3. Medidas físicas pendientes (necesitan el módulo LCD en mano, con calibre)

| Constante | Valor provisional | Qué medir |
|---|---|---|
| `LCD_PIN_ROW_Y` | 1.60mm | Borde superior del módulo → centro de la fila de pines |
| `LCD_HOLE_INSET` | 2.19mm | Borde del módulo → centro del agujero de montaje, en los dos ejes (el drawing dice 2.19, la nota china dice 2.5 — hipótesis: son cotas distintas, ver nota en `params.py`) |

## 4. Valores del lazo del boost (gate V-7) — calcular, no comprar

| Constante | Valor provisional | Qué es |
|---|---|---|
| `BOOST_L` | 2.2µH | Inductor del TPS61023 (encapsulado ya confirmado por el part number: 1210/3225 métrico) |
| `BOOST_RFB_TOP` | 1000kΩ | Divisor de realimentación, arriba |
| `BOOST_RFB_BOT` | 200kΩ | Divisor, abajo |

Calcular desde la hoja de datos del TPS61023 para 5V de salida con el consumo del
NJM4556AD, con margen. El encapsulado del inductor no cambia — solo el valor.

## 5. Piezas del BOM que no viven en el netlist (no las bloquea G-0, pero hacen falta para el ensamble)

| Pieza | Spec | Nota |
|---|---|---|
| Batería LiPo | 3.7V, 2000mAh, conector MX1.25 | Va directo al header de la RP2350-Plus (carga integrada, sin TP4056 aparte) |
| Parlante | 8Ω, 1W, mono | Se monta al enclosure, no a la PCB — J5 es solo el header de 2 pines |
| Insertos térmicos M2 | Cantidad TBD por el diseño final del case | Depende del enclosure, que todavía no existe |

## 6. Falta el script que genera los archivos de fabricación

`gen_fab.py` (gerbers de las 4 capas + drill + BOM + CPL para JLCPCB, con G-0 como
puerta previa) **no existe todavía** — es el único componente del pipeline que hay
que escribir desde cero, no adaptar. Sin él no hay forma de producir el paquete que
JLCPCB necesita, incluso con todo lo de arriba resuelto.

## Orden sugerido

1. Rutear con el contorno provisional (sección 0) para tener una placa DRC-limpia
   de referencia — no fabricable todavía, pero destraba iterar sin cambiar de fase
2. Cerrar sección 2 (partes) — cada una es una compra + una edición de
   `netlist.py`/`params.py`
3. Medir el LCD (sección 3) — 10 minutos con calibre, dos números
4. Calcular el boost (sección 4) — sin comprar nada nuevo, solo aritmética contra
   la hoja de datos
5. Dibujar el contorno real en Rhino y re-rutear (sección 1) con las partes ya
   reales — la geometría real cambia el ruteo, así que conviene que sea lo último
6. Escribir `gen_fab.py` (sección 6) y correr `checks/run_all.py` — debería pasar
   las 5 puertas limpio recién ahí
7. Conseguir batería/parlante/insertos (sección 5) — en paralelo, no bloquea la PCB
