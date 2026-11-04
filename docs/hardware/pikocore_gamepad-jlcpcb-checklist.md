# pikocore_gamepad — qué falta antes de mandar a JLCPCB

> **Actualización 2026-10-17, rama `hw/pantalla-7pines` — pantalla de 7 pines.**
> Placa de 100 × 60 con el RP2350-Plus soldado plano al dorso y MIDI TRS
> (heredado de `hw/modulo-micro-midi`, PR #3), y la pantalla cambiada al
> **módulo IPS 1.3" 240×240 ST7789 de 7 pines** (J4, header a 2.54 mm,
> pasante, soldado a mano en el frente; ver §2.5). Sin conector FPC ni
> backlight en la placa: el módulo trae el suyo y `LCD_BLK` (GP7) va directo
> a su pin BLK; GP26 queda libre (el módulo no tiene TE). Puertas, corridas
> en vivo: 219 tests OK; `run_all.py` sale 0 con todas las puertas en verde,
> **G-0 incluida** (las dos cotas del módulo, `LCD7_PIN_DRILL` y
> `LCD7_PIN_ROW_TO_EDGE`, las midió y confirmó el usuario el 2026-10-17; ver
> §2.5); G-5, G-4 (25 pines), G-2 (248 conexiones) y placement OK; ERC 0/0;
> DRC 0 errores / 0 sin conectar / 0 paridad, 15 avisos (11 serigrafía al
> borde, 2 serigrafía sobre cobre, 2 `lib_footprint_mismatch` de SW9/SW10).
> `gen_fab.py` sin `--force` → `pikocore_gamepad_fab.zip` (165 KB, sin sufijo
> `_NO-FABRICABLE`), 46 líneas de BOM (**19 sin LCSC**: los 12 tacts, los 3
> jacks PHONES/MIDI IN/MIDI OUT, el parlante, los dos 470 µF, el módulo
> RP2350-Plus y la pantalla), 55 SMD en el CPL; G-F: "Todo al día". Que las
> puertas pasen no es lo mismo que placa construida: **no se construyó ninguna**
> y ninguna puerta cubre lo siguiente: que el dorso del RP2350-Plus sea plano y
> asiente en la placa (el usuario confirmó la huella idéntica a la de la Pico,
> o sea el patrón de pads, no el dorso); el conector de batería del módulo
> contra las celdas JST GH del usuario (el carrier no llega a la línea de
> batería del módulo: hace falta un pigtail GH a MX1.25 o recrimpar el plug); el
> receptor UART por PIO en GP27 (firmware); la polaridad y el pull de BLK en la
> pantalla (el firmware asume activo en alto); un 1 µF opcional en J4 pin 2; la
> caja.
>
> **Al pedir en JLCPCB:** excluir del ensamblaje el módulo RP2350-Plus (U1) y
> la pantalla (J4); los dos los compra y suelda el usuario, igual que los tacts,
> los jacks, el parlante y los 470 µF (U1 y J4 no salen en el CPL,
> pero sí en el BOM sin LCSC: marcarlos "do not place"). La huella de U1
> tiene aperturas **solo en B.Paste** (3.8 × 2.2, más grandes que su cobre) que
> un stencil del dorso imprimiría: **pedir que no se ponga pasta en U1**, y 12
> vías de señal tocan el borde de esas aperturas (van tapadas con máscara,
> `tenting front back`; solo importa si se imprime pasta ahí).

> **Actualización 2026-10-14.** Corrida completa de la skill `pcb-verify` sobre
> el clon en `C:\pikocore_gamepad` (KiCad 9.0.1 en `C:\Program Files\KiCad`):
> 201 tests OK, G-0/G-5/G-4/G-2/placement OK, ERC 0 errores (2 avisos: GP27 y
> GP28 reservados), DRC 0 errores / 0 nets sin rutear / **0 avisos de paridad**
> (antes 128: `gen_pcb.py` no ponía la librería en el FPID ni el Value del
> netlist; ahora lo hace, y `finish_pcb.py` lo repite al final del ciclo).
> C23/C24 van DNP también en el esquemático. **Bug grave encontrado en
> `gen_fab.py`:** pedía las capas internas por su nombre de usuario (`GND`,
> `PWR`); kicad-cli las rechazaba con un aviso y exit 0, y el zip salía con
> **dos capas de cobre para una placa de cuatro**. Corregido (nombres
> canónicos `In1.Cu`/`In2.Cu`) y con guarda que aborta si falta cualquier
> gerber obligatorio. El paquete en `fab/` ahora trae los 16 archivos.
> Avisos de DRC que quedan y no bloquean: 7 de serigrafía cruzando el borde
> (SW15 y J1 sobresalen a propósito), 1 stub de 0.3 mm de 5V junto a U2
> (resto de la pista manual que freerouting completó por otro punto) y 4
> `lib_footprint_mismatch` (SW9/SW10 con las patas de anclaje convertidas a
> NPTH por `gen_pcb.py`; U2/U3 por diferencia de versión de librería 9.0.4 →
> 9.0.1). Los 13 LCSC en blanco del BOM son todos THT de soldadura manual más
> los dos 470 µF. Sigue abierto §5 (batería, parlante, insertos), el DFM
> externo (G-7) y el **repin de firmware**: el código de este repo apunta al
> RP2350-PiZero + GamePi13, no a esta placa.
>
> **Misma fecha, segunda corrida — placa reducida a 100 × 80.** Rombo
> X/Y/A/B con cuerpo en X=70 (espejo del NAV5 en X=30), Select en el mismo
> eje, gatillo R en x=75.25, J5 en (91, 13), lazo del boost 5 mm a la
> izquierda y U3 en (58, 35). Re-ruteada con freerouting 2.4.1 (el jar del
> plugin de KiCad 10, Java 25): 534 pistas, 98 vías. Puertas: 201 tests, G-0/
> G-5/G-4/G-2/placement OK, ERC 0 errores, DRC 0 errores / 0 abiertas / 0
> paridad, 10 avisos (7 serigrafía al borde, 1 serigrafía del jack sobre
> máscara, 2 `lib_footprint_mismatch` por los NPTH de SW9/SW10). Tres bugs de
> KiCad 9.0.1 cazados en el camino y rodeados en el pipeline: `Flip()` deja los
> pads PTH sin capas internas (10 conexiones abiertas al plano hasta que
> `reparar_capas_pth` las restaura), `PCB_VIA.SetWidth(int)` cuelga el script
> en un assert modal, y el `(image ...)` del DSN ahora lleva prefijo de
> librería (filtro de `route_io.py` ajustado). `manual_tracks.py` ya no usa
> coordenadas absolutas: las pistas de U2 y los puentes de los tacts se derivan
> de `placements.py`. El template DXF se regeneró a 100 × 80; el `_MOD.dxf` de
> Rhino sigue siendo el de 120.
>
> **Tercera corrida, misma fecha — D-pad de cuatro tacts.** El NAV5 (SW13)
> vuelve a ser SW1–SW4 (`SW_PUSH_6mm`, cruz de 12.5 mm centrada en X=30,
> espejo del rombo); BTN_OK desaparece y GP26 queda libre; Start pasa a
> x=26.75 para centrar su cuerpo en X=30. Ruteo: freerouting 2.4.1 hay que
> lanzarlo con `-Djava.awt.headless=true -mt 1` (con ventana, un
> NullPointerException en el repintado interrumpe el fanout y el `.ses` sale
> con 60 nets abiertas y exit 0), y las pistas manuales solo a 0/45/90°.
> Todo el lazo del boost va ahora a mano (`U2_5V` hasta C5.1, `C7_5V`,
> `L1_VSYS_F`, `C4_VSYS_F`): freerouting los cerraba una corrida sí y otra
> no. `NPTH_KEEPOUT` sube a 0.75. Resultado: 196 tests, puertas OK, ERC 0
> errores (3 avisos GP26/27/28), DRC 0 errores / 0 abiertas / 0 paridad, fab
> 16 gerbers, 38 líneas de BOM (17 sin LCSC: THT manuales + 470 µF).
> Estudio ergonómico con propuesta de layout (LCD 5.3 mm arriba, grupos
> abajo, Start/Select al centro, boost trasladado): doc "Estudio ergonómico
> pikocore_gamepad" en claude.ai; pendiente de decisión antes de aplicar.
>
> **Cuarta corrida, misma fecha — pantalla por flex + propuesta aplicada.**
> La pantalla pasó a un panel desnudo de 24 pines por flex y se aplicó el
> layout del estudio ergonómico. Esa variante sigue en la rama
> `hw/modulo-micro-midi` (PR #3); en esta rama la reemplaza el módulo de 7
> pines (arriba).

Estado al **2026-08-25**, rama `pikocore-gamepad-hardware`. Generado corriendo en
vivo `tests/run_tests.py` (185 OK) y `checks/run_all.py` con el Python de KiCad
9.0, más lo que esas puertas **no** cubren. Filtrado de la lista heredada de
GAMESETUP que ya no aplica (MIDI, microSD, PCF8574, opto).

Novedades grandes desde el 2026-08-12:
- El **contorno ya no es provisional**: la placa pasó a **120 × 80mm apaisada**,
  dibujada por el usuario en Rhino. `BOARD_W`/`BOARD_H` están verificados.
- El jack quedó **elegido, verificado contra datasheet y con modelo 3D del
  fabricante**. Esa verificación destapó un error de circuito y dos footprints
  equivocados — ver §7.
- La placa **está ruteada**, con **0 conexiones abiertas**.
- Los dos componentes grandes tienen **modelo 3D del fabricante**: el jack
  (Same Sky) y el módulo RP2350-Plus (Waveshare), ambos en
  `lib/gamesetup_fp.3dshapes/` y asignados desde `gen_pcb.py`
  (tabla `MODELOS_PROPIOS`). Sus offsets/rotaciones están **ajustados a mano**
  en KiCad y NO hay que re-derivarlos por cálculo: son ensamblajes cuyos ejes
  no se leen bien muestreando coordenadas.

## 0. El ciclo de ruteo

La placa **ya está ruteada**: 490 pistas, 67 vías, planos internos limpios y
**0 conexiones abiertas**.
Este es el ciclo completo, que hay que rehacer cada vez que cambia el placement:

```bash
KIPY="$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe"
KICLI="$LOCALAPPDATA/Programs/KiCad/9.0/bin/kicad-cli.exe"

python gen_sch.py                     # Python normal: no necesita pcbnew
"$KICLI" sch export netlist --format kicadsexpr \
         -o pikocore_gamepad.net pikocore_gamepad.kicad_sch
"$KIPY" gen_pcb.py
"$KIPY" manual_tracks.py              # ANTES del export, ver abajo
"$KIPY" plane_vias.py                 # ANTES del export, ver abajo
"$KIPY" route_io.py export
java -jar freerouting-1.9.0.jar -de pikocore_gamepad.dsn -do pikocore_gamepad.ses -mp 50
"$KIPY" route_io.py import
"$KIPY" finish_pcb.py
"$KICLI" pcb drc --severity-all --format json pikocore_gamepad.kicad_pcb -o logs/drc.json
```

⚠️ **`plane_vias.py` va ANTES del export, no después del ruteo.** Coloca las
vías que conectan los pads SMD de GND/3V3 a sus planos internos. Puestas antes,
freerouting las esquiva como cualquier obstáculo; puestas después caen encima
de pistas ya ruteadas (se probó: 12 cortocircuitos y 22 violaciones de margen).

⚠️ **Freerouting tiene que ser de la rama 1.x** (v1.9.0 es la última). Las 2.x
piden Java 21/25 y en esta máquina hay Java 17. El `.jar` no está versionado en
el repo — se baja de github.com/freerouting/freerouting/releases.

⚠️ **`manual_tracks.py` también va ANTES del export**, por el mismo motivo que
`plane_vias.py`: puestas después del ruteo, chocan con lo que ya trazó
freerouting (se probó: 4 cortocircuitos VSYS_F contra VSYS). Puestas antes,
entran al DSN como wiring preexistente y el autorouter las esquiva.

⚠️ **Nada ruteado a mano en la GUI sobrevive.** `gen_pcb.py` hace
`pcbnew.NewBoard()`: la placa se reconstruye desde cero en cada corrida. El
ruteo normal vuelve por el `.ses`, pero una pista dibujada a mano se pierde sin
aviso. Todo lo manual va en `manual_tracks.py` para que sea reproducible — hoy
están ahí las 4 conexiones de U2 que el autorouter no puede hacer (ver §7).

⚠️ **El paso del `.net` no es opcional.** `gen_pcb.py` lee las nets del `.net`
exportado, que NO se regenera solo al correr `gen_sch.py`. Si se lo saltea, la
placa sale con el netlist viejo y los componentes nuevos aparecen con los pads
sin net — sin que nada falle a la vista.

Conviene rutear **después** de cerrar §1 y §2: el contorno definitivo y los
footprints reales cambian la geometría, y el ruteo habría que rehacerlo igual.

## 1. ~~Contorno de la placa~~ (gate V-0) — ✅ CERRADO

| Constante | Valor | Estado |
|---|---|---|
| `BOARD_W` | 120.0mm | **verificado** |
| `BOARD_H` | 80.0mm | **verificado** |

Placa **apaisada**, dibujada en Rhino y traída por `parse_dxf.py`. El flujo es
`gen_template_dxf.py` → editar en Rhino → `parse_dxf.py --write` → `gen_pcb.py`.

⚠️ **La ROTACIÓN no viaja por el DXF.** Una cruz no tiene orientación, así que
al mover una pieza en Rhino conserva la rotación vieja. Pasó con los tres
componentes de borde al cambiar a apaisado: los gatillos seguían apuntando a los
laterales y el slide de encendido se salía 3.15mm de la placa. Se edita a mano en
`placements.py`.

⚠️ **El DXF sale solo con los componentes MECÁNICOS** (botones, switches,
pantalla, jack, conectores, socket del MCU). Los pasivos y chips SMD se filtran a
propósito: `parse_dxf.py` **agrega a `PLACEMENTS` todo lo que encuentre**, así
que incluirlos los anclaría en la posición que les dio la grilla automática.

## 2. Partes sin elegir todavía (bloquean G-0)

Quedan **3** de las 4 originales (el jack ya salió de `FOOTPRINTS_PROVISIONALES`). Cada una es una compra más una edición de
`netlist.py`/`params.py`.

### 2.1 ~~Jack de audífonos~~ — ✅ CERRADO (fuera de G-0)

**CUI / Same Sky SJ1-3535NG**, THT, 3.5mm estéreo, datasheet público
([rev 1.06](https://www.sameskydevices.com/product/resource/sj1-353xng.pdf)).
LCSC `C4991610` / `C22359743`; en JLCPCB la variante GR es `C4992036`
(confirmar color/variante antes de comprar).

Pinout verificado contra la tabla de la página 2:

| Pin | Función | Va a |
|---|---|---|
| 1 | sleeve | GND |
| 2 | tip | JACK_L |
| 3 | ring | JACK_R |
| 4 | tip switch | sin conectar |
| 5 | ring switch | JACK_DETSW |

`JACK_AUDIO` salió de `PINOUT_SIN_VERIFICAR`.

**Footprint: el OFICIAL de KiCad 9**, `Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal`
(el PR upstream que faltaba ya está mergeado, viene con la instalación). Hay una
variante `_CircularHoles` por si el fabricante prefiere agujeros redondos a
ranurados.

Se había dibujado uno propio y **estaba mal**: las cotas 1.20/3.60/7.30/9.10/12.80
del "Recommended PCB Layout" son **verticales** —la posición de cada pad a lo
largo del cuerpo— y se leyeron como horizontales, con lo que salía un patrón
ancho y bajo (9.10 × 3.40) en vez del real, alto y angosto (2.00 × 11.60). Se
detectó porque el modelo 3D del fabricante no calzaba sobre los pads.

⚠️ Sus pads se identifican por **función** (`S`/`T`/`R`/`TN`/`RN`), no por número.
El símbolo del esquemático usa esos mismos identificadores: el `.net` cruza
símbolo y footprint por ahí, así que tienen que coincidir de los dos lados.

**Modelo 3D: resuelto.** El footprint referencia
`Connector_Audio.3dshapes/Jack_3.5mm_CUI_SJ1-3535NG_Horizontal.step`, que
**KiCad 9.0.4 no incluye** (están los del 3523N/3524N/3525N, no este). En su
lugar se usa el **STEP nativo de Same Sky**, en
`lib/gamesetup_fp.3dshapes/`, y `gen_pcb.py` lo sustituye al colocar el
footprint (tabla `MODELOS_PROPIOS`, con su offset y rotación).

Antes se intentó convertir el modelo OBJ del visor web y **no sirve**: es una
malla de preview, no un sólido. Trae dos volúmenes desconectados (el jack y los
terminales aparte), y recortar uno deja la malla abierta — el render muestra la
pieza incompleta. Para CAD hay que usar el STEP nativo, que requiere cuenta
gratuita en sameskydevices.com.

### 2.2 ~~Tact vertical 6×6 THT~~ — ✅ CERRADO

**Comprado en AliExpress** (sin código LCSC: lo suelda el usuario).

Pasó a `Button_Switch_THT:SW_PUSH_6mm`, el **oficial de KiCad**. El dibujo del
vendedor trae su "P.C.B. Land Pattern" acotado en **6.5 × 4.5**, que es
exactamente el de ese footprint.

El que había antes (`SW-TH_4P-L4.5-W4.5`, paso **5.50 × 3.00**) era el 4.5×4.5
de V1 que quedó de respaldo: **no le habría calzado**.

⚠️ **El símbolo pasó de 4 pines a 2, y el cableado de `{1,4}` a `{1,2}`.**
`SW_PUSH_6mm` numera sus cuatro pads como **1,1,2,2** — un número por par
interno cortocircuitado. Cablear 1 y 2 cruza el contacto por construcción, así
que el cableado diagonal que antes había que elegir a mano ahora lo garantiza el
footprint. El test correspondiente verifica eso y no los números viejos.

Cuerpo 6.0 × 6.0, botón Ø3.4 con 0.25 de travel, patas de 0.7. Las variantes
`_H*mm` comparten la misma geometría de pads: el largo del vástago se elige con
el enclosure.

### 2.3 ~~Tact angulado L/R~~ — ✅ CERRADO

**Comprado en AliExpress** (sin código LCSC: lo suelda el usuario, no JLCPCB —
es THT y el CPL excluye los THT a propósito).

El footprint que ya tenía el proyecto, `SW_Tactile_SPST_Angled_PTS645Vx39-2LFS`,
**es el correcto**. Verificado contra el dibujo del vendedor:

| | tact comprado | footprint PTS645 |
|---|---|---|
| contactos (interiores) | paso 4.5 | 4.50 |
| anclajes (exteriores) | paso 7.2 ±0.5 | 7.01 |
| roles | 2 eléctricos + 2 mecánicos | idéntico |

Los 7.01 contra 7.2 caen dentro de la tolerancia ±0.5 que declara el propio
dibujo. Cuerpo 7.5 × 6.0, alto total 10.7 ±0.5, botón Ø3.40 que sobresale 6.8mm,
travel 0.25.

El **largo del actuador** (el vendedor ofrece H de 4.3 a 10mm) no afecta los pads:
todas las variantes comparten la misma geometría. Se elige con el enclosure.

⚠️ La **fuerza de actuación** no viene en el dibujo. El spec pide 100–160 gf; si
resultan más duros se nota al probarlos, pero no bloquea la fabricación.

### 2.4 Op-amp SMD (`OPAMP_FP`) — **1 unidad**

El LCSC `C2838125` cargado es el NJM4556AD en **DIP-8**. Para SMD:

- **NJM4556AM-TE1** (`C3018893`, JRC, 1.705 en stock, $0.2629) — encapsulado
  **DMP8**: cuerpo 5.0mm × 6.8mm, pitch 1.27mm. **No es drop-in** sobre el
  `SOIC-8_3.9x4.9mm_P1.27mm` que tiene el netlist: mismo pitch y misma cuenta de
  pines, pero 1.1mm más ancho de cuerpo.
- `C4366085` (Nisshinbo) a $1.0682 — 4× más caro, **confirmar encapsulado**
  antes de comprar.

Dos salidas: dibujar el DMP8 en `gamesetup_fp`, o conseguir un SOIC-8 real. El
ahorro de 95mm² que justificaba pasar a SMD hay que **recalcularlo** con el área
del DMP8.

### 2.5 Pantalla (J4) — comprada, medidas confirmadas el 2026-10-17 (G-0 en verde)

**Comprada en AliExpress** (sin código LCSC: la suelda el usuario, no JLCPCB).
Módulo IPS 1.3" 240×240 ST7789 de 7 pines (GND, VCC, SCL, SDA, RES, DC, BLK),
huella `LCD_ST7789_240x240_7P` según el dibujo del fabricante (27.78 × 39.22,
pin 1 a 6.27 del borde izquierdo, paso 2.54). Los 4 agujeros de 2 mm del
módulo **no se taladran**: se sostiene por sus pines.

Las dos cotas que faltaban las midió el usuario **con el módulo en mano** y
confirmó el 2026-10-17 que los valores son correctos; ambas están en `params.py`
con `verified=True`:

| Constante | Valor confirmado | Qué es |
|---|---|---|
| `LCD7_PIN_ROW_TO_EDGE` | 1.27 | eje de la fila de pines → borde del módulo del lado de los pines; el dibujo no la acota y corre el contorno y el área activa respecto de los pines |
| `LCD7_PIN_DRILL` | 1.0 | taladro de los 7 pines en la placa; sale del diámetro real de los pines |

Y la comprobación de orientación, también con el módulo en mano: pantalla
hacia arriba y fila del header arriba, la etiqueta de más a la izquierda tiene
que decir GND y va en el pad cuadrado (la placa ya tiene las etiquetas GND/BLK
en serigrafía). Al revés se cruzan GND/BLK, 3V3/DC y SCK/RES.
La foto del módulo del usuario (2026-10-17) ya muestra ese orden: con la pantalla
arriba y el texto legible, la fila de pines queda arriba y se lee GND VCC SCL SDA
RES DC BLK de izquierda a derecha, con GND en el pad cuadrado. El usuario
confirmo el 2026-10-17 que la pieza que tiene es la de la foto: la orientacion
queda cerrada.

Con las dos medidas cargadas con `verified=True` y ningún otro rojo, G-0 pasa y
`gen_fab.py` ya no pide `--force`: el paquete sale sin sufijo.

## 3. ~~Medidas físicas pendientes~~ — ✅ CERRADO

> Nota histórica: el 1.27 salió de un STEP dibujado desde el plano del
> fabricante, no de un calibre. Hoy es `LCD7_PIN_ROW_TO_EDGE`, que el usuario
> midió con el módulo en mano y confirmó el 2026-10-17 (`verified=True`):
> cerrada, ver §2.5.

Las dos cotas del LCD que faltaban salieron del **STEP del módulo** que modeló
el usuario a partir del dibujo, no de un calibre:

| Constante | V1 (mal) | Real | De dónde |
|---|---|---|---|
| `LCD_PIN_ROW_Y` | 1.60 | **1.27** | los 7 agujeros Ø1.27 están en Y=37.950 sobre 39.22 de alto |
| `LCD_HOLE_INSET` | 2.19 | **2.50** | los 4 agujeros Ø2.00 caen a 2.500 de cada borde |

**La hipótesis que estaba anotada en `params.py` era correcta.** Decía que 2.19
y 2.5 no se contradecían sino que acotaban cosas distintas: 2.19 es el margen
lateral del **área activa** —(27.78−23.40)/2 = 2.190 exacto— y 2.5 el centro del
agujero. El modelo lo confirmó.

El 1.27 tiene una comprobación extra: es **medio paso de 2.54** (0.05 pulgadas),
o sea una cota de diseño y no una casualidad. El 1.60 de V1 salía de escalar el
dibujo a ojo y erraba por 0.33mm.

⚠️ El STEP tiene el ancho en 27.70 y el real es **27.78** — 0.08mm de menos. No
afecta el inset, que se mide desde el borde, pero sí explica que la separación
horizontal entre agujeros dé 22.70 en el modelo y 22.78 en el footprint.
`gen_fp.py` calcula el agujero derecho como `BOARD_W - inset`, o sea asume
simetría: correcto para un módulo comercial, y 0.08mm en un agujero Ø2.00 para
un tornillo M2 es despreciable.

## 4. Valores del lazo del boost (gate V-7) — calcular, no comprar

| Constante | Valor provisional | Qué es |
|---|---|---|
| `BOOST_L` | 2.2µH | Inductor del TPS61023 (encapsulado confirmado: 1210/3225 métrico) |
| `BOOST_RFB_TOP` | 1000kΩ | Divisor de realimentación, arriba |
| `BOOST_RFB_BOT` | 200kΩ | Divisor, abajo |

Calcular desde la hoja de datos del TPS61023 para 5V de salida con el consumo
del NJM4556A, con margen. El encapsulado del inductor no cambia — solo el valor.

Sigue pendiente aparte: **el pinout del TPS61023 no está verificado**
(`PINOUT_SIN_VERIFICAR`). Es el único símbolo que queda sin confirmar contra
datasheet, y el caso del jack mostró que eso no es un trámite.

## 5. Piezas del BOM que no viven en el netlist

| Pieza | Spec | Nota |
|---|---|---|
| Batería LiPo | 3.7V, 2000mAh, conector MX1.25 | Va al header de la RP2350-Plus (carga integrada, sin TP4056) |
| Parlante | 8Ω, 1W, mono | Se monta al enclosure, no a la PCB — J5 es solo el header |
| Insertos térmicos M2 | Cantidad TBD | Depende del enclosure, que todavía no existe |

## 6. ~~Falta el script de fabricación~~ — ✅ CERRADO

`gen_fab.py` **ya existe**. Produce todo el paquete en `fab/`:

```bash
"$KIPY" gen_fab.py            # G-0 bloquea si hay algo provisional
"$KIPY" gen_fab.py --force    # genera igual, para inspeccionar
```

| Salida | Qué es |
|---|---|
| `fab/gerber/*.g*` | 4 capas de cobre + máscaras, serigrafías, pasta y contorno |
| `fab/gerber/*.drl` | taladros Excellon, PTH y NPTH separados |
| `fab/*_BOM.csv` | Comment/Designator/Footprint/LCSC, agrupado por valor |
| `fab/*_CPL.csv` | Designator/Mid X/Mid Y/Layer/Rotation, solo SMD |
| `fab/*_fab.zip` | todo junto, listo para subir (~90 KB) |

**G-0 es una puerta, no un aviso**: sin `--force` el script se niega a generar
mientras queden constantes o footprints provisionales. Con `--force` el zip sale
con el sufijo `_NO-FABRICABLE` en el nombre, para que no se confunda con uno real
(el sufijo aparece solo mientras G-0 esté rojo; con G-0 verde sale sin sufijo).

Detalles verificados contra la salida real:
- Extensiones **Protel** (`.gtl`/`.g1`/`.g2`/`.gbl`...), que es lo que espera el
  parser de JLCPCB.
- Gerbers y drill comparten origen (`--use-drill-file-origin` + `--drill-origin
  plot`). Se contrastó un taladro concreto: J5.1 está en (103.500, 13.000) en la
  placa y sale como `X103.5Y-13.0`. Si los orígenes no coincidieran, los taladros
  saldrían corridos respecto del cobre **sin que nada avise**.
- El CPL trae solo SMD: los THT los suelda una persona, y listarlos haría que
  JLCPCB cotice una colocación automática que después no puede hacer.

⚠️ **Faltan 23 códigos LCSC** (resistencias, condensadores, botones). El script
los deja en blanco y los reporta al final — **no inventa códigos**. Hay que
completarlos en el portal de JLCPCB al subir el BOM, o cargarlos en `netlist.py`.

`fab/` está en `.gitignore`: es salida generada, se rehace en un comando.

## 7. Deuda abierta por la verificación del jack

Verificar el pinout del jack destapó tres cosas que ya están **arregladas**, y
dejó una **sin resolver**.

### Arreglado

1. **El circuito de detección inyectaba DC en el audio.** Los switches del
   SJ1-3535NG no son contactos libres: el pin 4 cierra contra el 2 (tip) y el 5
   contra el 3 (ring). R15 como pull-up de 10k a 3V3 sobre cualquiera de los dos
   metía continua en el canal mientras no hubiera plug. Se resolvió colgando la
   detección del switch de ring y aislándola con **R18 (100k)** en serie:
   sin plug `DET ≈ 0.30V`, con plug `DET = 3V3`.
2. **U2 (boost) tenía el footprint equivocado.** `placements.py` decía
   `SOT-23-6` mientras `netlist.py` decía `SOT-563` — y el comentario del
   netlist advertía explícitamente "con el footprint equivocado el chip no entra
   ni cerca" (2.10×1.35 a paso 0.50 contra 3.60×2.50 a paso 0.95).
3. **El footprint estaba declarado en dos lugares que podían divergir.**
   `netlist.py` alimenta el esquemático y `placements.py` es de donde
   `gen_pcb.py` carga de verdad. Cuando divergen, la placa sale con el footprint
   viejo y el pinout nuevo, y los pads sobrantes quedan como
   `unconnected-(...)` en vez de dar error. Ahora hay un test
   (`test_placements_usa_el_mismo_footprint_que_el_netlist`) que lo cubre — fue
   el que encontró el bug de U2.

### El SOT-563 de U2: por qué necesita ruteo manual

Sus pads miden **0.68 × 0.35mm a paso 0.50**, o sea 0.15mm de hueco entre pads
adyacentes cuando una pista de 0.20 necesita 0.60 con su clearance. Los pines
del **medio** de cada columna (2=GND y 5=VOUT) no tienen salida lateral: están
encerrados entre sus vecinos. Eran las 4 conexiones que el autorouter dejaba
sin resolver, y **mover el componente no lo arregla** — el problema viaja con
él a cualquier posición.

TI lo resuelve ruteando por debajo del chip. De su guía de layout del TPS61023
([SLVAES4](https://www.ti.com/lit/pdf/slvaes4), §4): *"the SW pin is in the
middle of the VOUT pin and GND pin, place the SW trace **underneath the
device**"*. Entre las dos columnas de pads quedan 0.74mm libres.

Hubo que quitar **dos** obstáculos para poder hacerlo:

1. KiCad exporta el contorno del footprint al DSN como `(outline ...)` y
   freerouting lo trata como obstáculo: las líneas en y=±0.94 **sellan el
   corredor**. Lo limpia `route_io.py` (ver `SIN_OUTLINE`), solo para el
   SOT-563 y solo el contorno — los pads no se tocan.
2. `5V`/`GND`/`VSYS_F` son de la netclass **Power (0.40mm)**: con clearance
   necesitan 0.80mm y el corredor tiene 0.74. Fallaban por **0.06mm**.
   `BOOST_FB` y `BOOST_SW`, que son clase default (0.20), sí se ruteaban solos.

Las 4 conexiones quedaron en `manual_tracks.py` con pista de 0.20mm en el tramo
corto, que es exactamente lo que dibuja TI en su figura 9. El pin de GND baja
al plano por vía, como TI recomienda para masa.

Efecto colateral bueno: con esas 4 pistas puestas antes del export, el ruteo
pasó de **1m30s a 16s**.

### Sin resolver: clearance del SOT-563

Con el footprint correcto, U2 genera **4 infracciones de DRC**: los pads
adyacentes del SOT-563 quedan a **0.150mm** y el clearance global del proyecto
es 0.200mm. No es un error de colocación — es intrínseco al encapsulado de paso
0.5mm, con el footprint oficial de KiCad.

**Fabricar no es el problema:** JLCPCB admite 0.127mm en 2 capas y ~0.0889mm
(3.5 mil) en multicapa, y esta placa es de 4 — o sea que los 0.150mm del
SOT-563 entran con margen. Lo que falla es la regla del proyecto, no el proceso.

Hace falta una **regla de excepción para U2** en las reglas de diseño (en KiCad
9: una custom rule por footprint, o una netclass propia). No se tocó el
clearance global a propósito: bajarlo de 0.2mm afectaría toda la placa, y 0.2mm
es un buen default para el resto.

### Estado de las puertas (2026-08-25, histórico)

```
G-0  constantes y footprints verificados ....... FALLA (correcto: §2, §3, §4)
G-5  referencias duplicadas .................... OK
G-4  pinout PCB <-> firmware ................... OK
G-2  netlist esquemático <-> PCB ............... OK
---  placement sin solapamientos ............... OK
tests/run_tests.py ............................. 183 OK
```

DRC: 173 infracciones, de las cuales 168 son **pad contra zona de plano**
(GND/3V3) y desaparecen al rutear, cuando las zonas se rellenan y los pads
reciben su thermal relief. De las 5 restantes, 4 son el SOT-563 de arriba y 1 es
un solape de courtyard J5↔U1 que ya venía de antes.

## Orden sugerido (2026-08-25, histórico)

1. Rutear con el contorno provisional (§0) para tener una placa DRC-limpia de
   referencia — no fabricable todavía, pero destraba iterar
2. Resolver el clearance del SOT-563 (§7) — es una regla, no una compra, y
   conviene tenerla antes de rutear
3. Cerrar §2 (las 3 partes que quedan) — cada una es compra + edición
4. Medir el LCD y contrastar el footprint del jack (§3)
5. Calcular el boost y **verificar el pinout del TPS61023** (§4)
6. Dibujar el contorno real en Rhino y re-rutear (§1) con las partes ya reales
7. Escribir `gen_fab.py` (§6) y correr `checks/run_all.py` — debería pasar las 5
   puertas limpio recién ahí
8. Conseguir batería/parlante/insertos (§5) — en paralelo, no bloquea la PCB
