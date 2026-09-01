# Las puertas, en detalle

Leé esto cuando una puerta falle y el mensaje no alcance, o cuando llegues a
G-6/G-7, que no están en `run_all.py`.

## Índice

- [G-F — frescura del pipeline](#g-f--frescura-del-pipeline)
- [T — tests unitarios](#t--tests-unitarios)
- [G-0 — constantes y footprints verificados](#g-0--constantes-y-footprints-verificados)
- [G-5 — referencias duplicadas](#g-5--referencias-duplicadas)
- [G-4 — pinout PCB ↔ firmware](#g-4--pinout-pcb--firmware)
- [G-2 — netlist esquemático ↔ PCB](#g-2--netlist-esquemático--pcb)
- [P — placement](#p--placement)
- [G-1 — ERC](#g-1--erc)
- [G-3 — DRC](#g-3--drc)
- [G-6 — paquete de fabricación](#g-6--paquete-de-fabricación)
- [G-7 — DFM externo](#g-7--dfm-externo)
- [El ciclo completo de regeneración](#el-ciclo-completo-de-regeneración)

---

## G-F — frescura del pipeline

`scripts/check_freshness.py` · cualquier python 3 · segundos

Compara el mtime de cada artefacto contra el de sus fuentes según el grafo del
pipeline. Es la única puerta que mira **relaciones entre archivos** en vez del
contenido de uno solo, y por eso es la única que puede detectar que todas las
demás están evaluando la cosa equivocada.

**Cómo se lee un fallo.** `VIEJO pikocore_gamepad.kicad_pcb (71.6h de atraso)`
significa que el `.net` se regeneró después de la última corrida de
`gen_pcb.py`. La placa que hay en disco corresponde a un esquemático anterior.
Todo lo que diga el DRC sobre ella es cierto y a la vez irrelevante.

**El fallo en cascada.** Un artefacto viejo contamina todo lo que sale de él.
Si la placa está desactualizada, el zip de fabricación puede aparecer "fresco"
respecto de la placa y estar igual de podrido, porque su fuente lo está. Leé
el reporte de arriba hacia abajo y arreglá desde el primer rojo.

**Límite honesto.** mtime detecta "se tocó después", no "cambió el contenido".
Un `git checkout` puede dar falso positivo. La respuesta correcta es regenerar
igual (es barato) o corroborar por contenido — nunca es ignorar la puerta.

**Cómo corroborar por contenido.** G-2 (`check_netlist.py`) compara la
conectividad real del `.net` contra la del `.kicad_pcb`. Si G-F marca la placa
como vieja pero **G-2 pasa**, la regeneración del esquemático no cambió la
conectividad: el desfase es cosmético y el riesgo es bajo. Reportá las dos
cosas juntas — "vieja por fecha, idéntica en conectividad" — porque decir solo
una de las dos desinforma en direcciones opuestas. Lo que G-2 **no** cubre son
cambios que no tocan nets: valores, footprints, huellas 3D. Si el `git diff`
del esquemático toca alguno de esos, la placa hay que regenerarla.

## T — tests unitarios

`"$KIPY" tests/run_tests.py` · segundos

Unos 200 tests sobre geometría de footprints, params, netlist, pinmap y
refs — el número crece, no lo cites de memoria: leelo de la salida.
Cubren los generadores, no el resultado: un test verde dice que `gen_pcb.py`
hace lo que su autor quiso, no que lo que quiso esté bien.

## G-0 — constantes y footprints verificados

`checks/check_verified.py`

Falla mientras queden constantes físicas sin verificar o footprints
provisionales. **Bloquea fabricación, no el diseño**: se puede iterar el
layout entero con valores provisionales, pero no mandarlo a fabricar.

`gen_fab.py` la invoca antes de escribir nada. Tiene `--force` para inspeccionar
el paquete sin cerrarla, y estampa un aviso en el nombre del zip. Un zip con
ese aviso en el nombre **no se sube a JLCPCB**.

## G-5 — referencias duplicadas

`checks/check_refs.py`

Una `C19` duplicada ya llegó al esquemático una vez (commit `aad25ba`). KiCad
no se queja: el segundo componente pisa las propiedades del primero y el
síntoma aparece mucho después, como un valor equivocado en el BOM.

Los huecos de numeración son **aviso**, no error.

## G-4 — pinout PCB ↔ firmware

`checks/check_pinmap.py`

Compara la PCB contra `firmware_pin_stub/config.h` en las dos direcciones. La
segunda dirección (defines del firmware que la PCB no conoce) existe porque el
camino natural es partir del `config.h` de V1, que trae pines de hardware que
V2 no tiene.

Modo de fallo si no se automatiza: silencioso. La placa se fabrica, el firmware
compila, y se descubre al enchufar.

## G-2 — netlist esquemático ↔ PCB

`checks/check_netlist.py` · necesita `pcbnew`

Compara pares `(referencia, pin) -> net` entre el `.net` y el `.kicad_pcb`. Una
divergencia significa que la placa está cableada distinto del esquemático, y
**no la detecta ni el ERC** (que solo mira el esquemático) **ni el DRC**, que
da por buena la net que tiene el pad.

Se solapa con `--schematic-parity` del DRC a propósito. Que coincidan es señal;
que discrepen es un bug en uno de los dos.

## P — placement

`checks/check_placement.py` · necesita `pcbnew`

Compara **pad contra pad**, no bounding box contra bounding box. La diferencia
importa: la bbox del módulo LCD abarca sus 27.78 × 39.22 enteros, pero su
interior no tiene cobre — y es justo ahí donde conviene poner componentes del
dorso. Con comparación por bbox toda pieza bajo el display aparecería como
choque.

No mira courtyards: dos courtyards que se rozan suelen ser aceptables.

## G-1 — ERC

```bash
"$KICLI" sch erc --severity-all --exit-code-violations \
         -o logs/erc.rpt pikocore_gamepad.kicad_sch
```

`--exit-code-violations` hace que el exit code signifique algo: 0 sin
violaciones, **5** con violaciones. Sin ese flag siempre sale 0.

Caza: pines de entrada flotantes, dos drivers en la misma net, falta de
power flag, partes sin alimentar, pines de enable al aire.

**Momento correcto:** antes del layout. Un error de ERC arreglado después de
rutear cuesta un ciclo completo de ruteo.

El reporte termina con una línea del tipo
`**Mensajes ERC: 2. Errores 0, Avisos 2`. Los avisos se listan en el reporte
pero no bloquean; leelos igual, porque "pin sin conectar" es aviso y a veces
es exactamente el bug.

## G-3 — DRC

```bash
"$KICLI" pcb drc --severity-all --schematic-parity --exit-code-violations \
         --format json -o logs/drc.json pikocore_gamepad.kicad_pcb
python <skill>/scripts/read_drc.py logs/drc.json
```

`--schematic-parity` no está en el ciclo documentado original y conviene
agregarlo: es gratis y cruza con G-2.

**El JSON tiene tres listas distintas** y las tres importan:

| lista | qué significa |
|---|---|
| `violations` | reglas de diseño violadas (márgenes, anillos, silk) |
| `unconnected_items` | nets sin rutear |
| `schematic_parity` | la placa y el esquemático no dicen lo mismo |

Mirar solo una es el error típico. Una placa con `unconnected_items: 0` se lee
como "ruteada y lista" y puede tener cinco errores de margen que la hacen
infabricable. Pasó exactamente eso acá.

**Las reglas tienen que ser las del fabricante, no las por defecto.** El
proyecto tiene `pikocore_gamepad.kicad_dru`; si el DRC corre sin él o con las
netclasses por defecto, el resultado no significa nada respecto de JLCPCB. Si
alguna vez se rutea con un servicio externo, hay que **volver a correr el DRC
localmente** con las reglas propias: el DRC del servicio usó las suyas.

**Errores de margen agrupados: agrupá, pero no asumas una sola causa.**
`read_drc.py` agrupa por tipo para no perseguirlos de a uno, y varios errores
idénticos suelen compartir causa — pero hay que confirmarlo mirando los `items`
de cada violación, no darlo por hecho. En la primera corrida de esta skill, 5
violaciones idénticas de `clearance` en la netclass `Power` resultaron ser
**dos causas distintas**: 3 eran pad-a-pad dentro de U2 y 2 eran vía-a-vía en
U5. Sacá siempre los items:

```bash
python -c "
import json,sys; sys.stdout.reconfigure(encoding='utf-8',errors='replace')
for v in json.load(open('logs/drc.json'))['violations']:
    if v['severity']!='error': continue
    print(v['type'], '|', v['description'])
    for it in v.get('items',[]):
        p=it.get('pos',{}); print('   ', it.get('description'), p.get('x'), p.get('y'))
"
```

**Trampa del `.kicad_dru`: `A.Reference` NO matchea pads.** Una regla escrita
como `(condition "A.Reference == 'U2' && B.Reference == 'U2'")` se parsea sin
error, se carga sin aviso y **no matchea nada** — el DRC sigue aplicando la
netclass y parece que la excepción no existiera. La forma que funciona para
alcanzar los pads de un footprint es:

```
(condition "A.memberOfFootprint('U2') && B.memberOfFootprint('U2')")
```

**Cómo verificar que una regla está viva**, en dos pasos, porque el modo de
fallo silencioso hace que "escribí la regla" no sea evidencia de nada:

1. ¿Se lee el archivo? Poné una regla trivialmente cierta
   (`A.Type == 'Pad'`) con `(min 5mm)` y corré el DRC. Si el conteo explota, se
   lee. Si no cambia, KiCad no está viendo el `.kicad_dru`.
2. ¿Matchea la condición? Dejá la condición real y subí el `min` a `5mm`. Si
   explotan solo los items que esperabas, la condición es correcta; bajá el
   `min` al valor definitivo. Si no cambia nada, la condición está mal.

Restaurá siempre el archivo original después (`cp` antes de tocarlo).

**Un DRC limpio no es reproducible: freerouting varía entre corridas.**
Sobre entradas identicas el autorouter da ruteos distintos, y con ellos
violaciones marginales que aparecen y desaparecen. Medido en este proyecto:
503 pistas una corrida y 477 la siguiente; y una violacion de `clearance` de
0.150mm presente en una corrida y ausente en la de al lado, con el mismo
codigo y los mismos archivos de entrada.

Consecuencias practicas, las dos importantes:

1. **Un verde no autoriza a re-rutear sin volver a chequear.** El DRC vale
   para la placa que hay en disco, no para "esta placa". Si se corre el ciclo
   otra vez, hay que correr el DRC otra vez — es exactamente lo que G-F ya
   exige por fecha, y esto es la misma idea por contenido.
2. **Un rojo marginal no siempre es un bug propio.** Antes de perseguir una
   violacion de margen, corré el ciclo de nuevo sin cambiar nada. Si vuelve
   igual, es estructural y hay causa que buscar; si cambia de lugar o
   desaparece, es varianza del autorouter. Este test separo señal de ruido dos
   veces acá: descarto una violacion contra un agujero NPTH de SW10, y
   confirmo que un pad sin rutear era geometrico y no suerte.

Cuando la varianza aparece siempre en la misma zona, lo que dice es que esa
zona esta congestionada — no que el autorouter este roto. Las salidas son
darle margen (declararle mas clearance del que se exige), acotar una excepcion
en el `.kicad_dru`, o descongestionar moviendo componentes.

## G-6 — paquete de fabricación

`"$KIPY" gen_fab.py` · genera `fab/`

No hay puerta automática para el contenido del paquete. Revisá a mano:

**BOM** (`pikocore_gamepad_BOM.csv`, columnas `Comment/Designator/Footprint/LCSC`)
- Celdas LCSC vacías: `gen_fab.py` las reporta al final. Hay que completarlas
  en el portal o en `netlist.py`. **Inventar un código es peor que dejarlo en
  blanco** — el hueco se ve, el código plausible no.
- Piezas del BOM que no viven en el netlist (§5 de la checklist): conectores,
  hardware mecánico. No aparecen acá y hay que pedirlas aparte.

**CPL** (`pikocore_gamepad_CPL.csv`, columnas `Designator/Mid X/Mid Y/Layer/Rotation`)
- **La rotación es el error más caro y el que ninguna herramienta detecta.** El
  0° de KiCad no es necesariamente el 0° de JLCPCB: la referencia de JLC es la
  orientación de la pieza en el tape-and-reel, no la del footprint. Un IC
  rotado 90° se suelda con el pin 1 en la esquina equivocada.
- Revisá una por una las **polarizadas y las de pin 1**: diodos, LEDs,
  electrolíticos, cada IC. Para las demás la rotación no importa.
- `Layer` va capitalizado, `Top`/`Bottom`.
- Si no hay certeza sobre una rotación, JLCPCB revisa y corrige según la
  serigrafía antes de montar — lo cual solo funciona **si la serigrafía marca
  la polaridad**. Poné el símbolo de diodo o una `K` fuera del courtyard.

**Gerbers**
- Extensión Protel (`.gtl/.gbl/...`), que es lo que espera el parser de JLC.
  Por eso NO se pasa `--no-protel-ext`.
- Drill en Excellon, mm, PTH y NPTH separados.
- **Gerbers y drill con el mismo origen** (`--use-drill-file-origin` +
  `--drill-origin plot`). Si no coinciden, los taladros salen corridos respecto
  del cobre y la placa se fabrica mal sin que nada avise.

## G-7 — DFM externo

Subir `fab/pikocore_gamepad_fab.zip` al DFM gratuito de JLCPCB (jlcdfm.com)
antes de pagar el pedido.

**Esto no es redundante con el DRC.** Hay una familia entera de defectos que
pasan un DRC limpio y arruinan la placa en la línea de producción, porque son
propiedades del proceso de fabricación y no de las reglas de diseño:

- **acid traps** — pistas que se encuentran en ángulo agudo (<90°) y atrapan
  químico de ataque, sobre-atacando el cobre hasta abrir el circuito;
- **slivers** — cuñas finas y aisladas de cobre o de máscara que se despegan
  durante la fabricación y flotan por la placa creando cortos intermitentes;
- **dams de máscara insuficientes** entre pads adyacentes, que producen puentes
  de soldadura.

El DFM revisa unos 30 puntos sobre pistas, máscara, taladros, serigrafía y
montaje, y localiza cada hallazgo visualmente. Es gratis y tarda segundos: no
hay razón para saltearlo.

---

## El ciclo completo de regeneración

Solo si te lo piden explícitamente. Hay que rehacerlo entero cada vez que
cambia el placement.

```bash
KIPY="$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe"
KICLI="$LOCALAPPDATA/Programs/KiCad/9.0/bin/kicad-cli.exe"

python gen_sch.py                     # python normal: no necesita pcbnew
"$KICLI" sch export netlist --format kicadsexpr \
         -o pikocore_gamepad.net pikocore_gamepad.kicad_sch
"$KIPY" gen_pcb.py
"$KIPY" manual_tracks.py              # ANTES del export
"$KIPY" plane_vias.py                 # ANTES del export
"$KIPY" route_io.py export
java -jar freerouting-1.9.0.jar -de pikocore_gamepad.dsn -do pikocore_gamepad.ses -mp 50
"$KIPY" route_io.py import
"$KIPY" finish_pcb.py
"$KICLI" pcb drc --severity-all --schematic-parity --exit-code-violations \
         --format json -o logs/drc.json pikocore_gamepad.kicad_pcb
```

Las tres trampas, todas verificadas empíricamente en este proyecto:

1. **`plane_vias.py` va ANTES del export.** Coloca las vías que conectan los
   pads SMD de GND/3V3 a los planos internos. Antes, freerouting las esquiva
   como cualquier obstáculo; después, caen encima de pistas ya ruteadas — se
   probó: 12 cortocircuitos y 22 violaciones de margen.
2. **`manual_tracks.py` también va ANTES**, por el mismo motivo — se probó: 4
   cortocircuitos de VSYS_F contra VSYS.
3. **Nada ruteado a mano en la GUI sobrevive.** `gen_pcb.py` hace
   `pcbnew.NewBoard()`: la placa se reconstruye desde cero en cada corrida.

Y una de entorno: **freerouting tiene que ser de la rama 1.x** (1.9.0 es la
última). Las 2.x piden Java 21/25 y en esta máquina hay Java 17. El `.jar` no
está versionado — se baja de github.com/freerouting/freerouting/releases.
