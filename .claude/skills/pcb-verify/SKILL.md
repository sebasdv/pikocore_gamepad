---
name: pcb-verify
description: Verifica de punta a punta el diseño de PCB de pikocore_gamepad (KiCad 9 + las puertas Python del repo) y emite un veredicto de si se puede fabricar. Usala SIEMPRE que se toque cualquier cosa bajo hardware/pikocore_gamepad/pcb/ — params.py, netlist.py, placements.py, footprints, ruteo — y siempre que el usuario pregunte si la placa está bien, si se puede mandar a JLCPCB, si el DRC/ERC pasa, si el fab package está al día, o pida "rechequear", "verificar", "revisar la placa", "está lista para fabricar". Usala también antes de generar gerbers o de dar por cerrado cualquier cambio de hardware, aunque el pedido no mencione verificación explícitamente.
---

# Verificación del diseño PCB

## Por qué esta skill existe

El repo ya tiene puertas buenas (`checks/run_all.py`, un par de cientos de tests, ERC, DRC). El
problema no es que falten checks: es que **correrlos en el orden equivocado, o
sobre archivos desactualizados, produce verde falso**. Y un verde falso es peor
que un rojo, porque nadie lo mira dos veces.

La frase que conviene tener presente todo el tiempo, de la literatura de
revisión pre-fabricación:

> Un diseño puede estar perfectamente conectado, perfectamente ruteado,
> completamente limpio de DRC — y estar completamente equivocado.

Las puertas automáticas verifican **consistencia interna**, no **corrección**.
Esta skill corre las puertas, pero su trabajo real es decir con precisión qué
quedó verificado y qué no, para que nadie confunda una cosa con la otra.

## Alcance: verificar, no regenerar

Por defecto **verificá y reportá; no regeneres nada**. Regenerar el
esquemático o la placa borra trabajo (`gen_pcb.py` hace `pcbnew.NewBoard()`:
reconstruye desde cero) y cambia el objeto que se está evaluando en la mitad
de la evaluación. Cuando una puerta falle, decí **qué comando lo arregla** y
dejá que la persona decida.

Regenerá solo si te lo piden explícitamente ("regenerá y verificá"), y en ese
caso seguí el ciclo completo de `references/gates.md` sin saltear pasos: el
orden de `manual_tracks.py` y `plane_vias.py` **antes** del export no es
opcional, ya costó 12 cortocircuitos y 22 violaciones de margen la vez que se
hizo al revés.

## El orden de las puertas

De lo barato a lo caro, y de lo que invalida todo lo demás a lo que solo
afecta un subsistema. **Si G-F falla, todo lo de abajo es ruido** — pero
corrélas igual, porque saber qué más está roto ahorra un ciclo entero.

| # | Puerta | Qué caza | Costo |
|---|--------|----------|-------|
| **G-F** | frescura del pipeline | artefactos más viejos que sus fuentes | seg |
| **T** | tests unitarios | geometría, params, netlist, pinmap | seg |
| **G-0** | constantes y footprints verificados | valores provisionales que llegan a fab | seg |
| **G-5** | referencias duplicadas | dos C19, BOM equivocado | seg |
| **G-4** | pinout PCB ↔ firmware | placa correcta, firmware apuntando a otro pin | seg |
| **G-2** | netlist esquemático ↔ PCB | placa cableada distinto del esquemático | seg |
| **P** | placement | pads encimados, piezas fuera de placa | seg |
| **G-1** | ERC | pines flotantes, dos drivers, falta power flag | ~30s |
| **G-3** | DRC + paridad | márgenes, anillos, nets sin rutear | ~1min |
| **G-6** | paquete de fabricación | BOM sin LCSC, rotaciones del CPL | seg |
| **G-7** | DFM externo | acid traps, slivers, dams de máscara | humano |

G-2 y G-3 se superponen a propósito: `--schematic-parity` del DRC y
`check_netlist.py` miran lo mismo por caminos distintos. Que coincidan es
señal; que discrepen es un bug en uno de los dos y hay que perseguirlo.

## Cómo correr

```bash
cd hardware/pikocore_gamepad/pcb
KIPY="$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe"
KICLI="$LOCALAPPDATA/Programs/KiCad/9.0/bin/kicad-cli.exe"

# G-F — primero, con cualquier python, sin KiCad
python ../../../.claude/skills/pcb-verify/scripts/check_freshness.py .

# T + G-0/G-5/G-4/G-2/P — necesitan el python de KiCad (importan pcbnew)
"$KIPY" tests/run_tests.py
"$KIPY" checks/run_all.py

# G-1 y G-3 — kicad-cli. --exit-code-violations hace que el exit code sirva:
# 0 sin violaciones, 5 con violaciones. Sin ese flag siempre sale 0 y el
# resultado hay que leerlo a ojo, que es como se cuelan los errores.
"$KICLI" sch erc --severity-all --exit-code-violations \
         -o logs/erc.rpt pikocore_gamepad.kicad_sch
"$KICLI" pcb drc --severity-all --schematic-parity --exit-code-violations \
         --format json -o logs/drc.json pikocore_gamepad.kicad_pcb
```

Para leer el DRC no confíes en el resumen: contá por severidad y por tipo. El
script `scripts/read_drc.py` hace exactamente eso y ya separa `violations`,
`unconnected_items` y `schematic_parity`, que son tres cosas distintas que el
JSON guarda en tres listas distintas:

```bash
python ../../../.claude/skills/pcb-verify/scripts/read_drc.py logs/drc.json
```

G-6 y G-7 están en `references/gates.md`. Leelo cuando llegues a fabricación,
o cuando una puerta falle y no sepas interpretar el mensaje.

## Cómo clasificar un fallo

Cuando algo falla, decidí a cuál de estas dos familias pertenece antes de
proponer arreglo. La distinción viene de la literatura de evaluación de
circuitos asistidos por LLM y acá es directamente accionable, porque los dos
tipos se arreglan distinto:

- **Fallo de cumplimiento** — el diseño está bien, se violó el procedimiento.
  Ejemplos reales de este repo: `plane_vias.py` corrido después del ruteo en
  vez de antes; ruteo hecho a mano en la GUI que `gen_pcb.py` va a borrar en
  la próxima corrida; DRC leído de un log viejo. **Se arregla rehaciendo el
  paso en el orden correcto.** No toques el diseño.

- **Fallo de competencia** — el diseño está mal. Un margen que no entra, un
  pinout que no coincide con el firmware, un footprint que no es el de la
  pieza real. **Se arregla cambiando `params.py`, `netlist.py` o
  `placements.py`** y regenerando.

Confundirlas es caro en las dos direcciones: tocar el diseño para arreglar un
error de procedimiento mete un bug nuevo, y rehacer el procedimiento para
arreglar un error de diseño hace perder un ciclo y deja el bug.

## El veredicto

Una sola línea, binaria, sin suavizar. Un diseño **pasa** solo si no hay
ningún error ni ninguna puerta en rojo; los avisos se listan pero no
convierten un rojo en verde ni al revés.

Nunca reportes "prácticamente listo", "solo faltan detalles menores" ni
"pasa salvo por". Si algo está en rojo, el veredicto es **NO FABRICABLE** y
después venís con el detalle. La razón es concreta: el costo de un rojo mal
comunicado es una tanda de placas pagada e inservible, y el de un rojo bien
comunicado son veinte minutos.

## Plantilla del reporte

```markdown
## Veredicto: [FABRICABLE | NO FABRICABLE — N bloqueantes]

| Puerta | Estado | Detalle |
|--------|--------|---------|
| G-F frescura | ✅/❌ | ... |
| ... | | |

### Bloqueantes
1. **[puerta]** — qué está mal, en qué archivo/línea.
   *Tipo:* cumplimiento | competencia
   *Arreglo:* comando o cambio concreto.

### Avisos (no bloquean)
- ...

### Lo que NINGUNA puerta verificó
- ...
```

La última sección es obligatoria y va en **todos** los reportes, incluso
cuando todo esté en verde — sobre todo cuando todo esté en verde. Su contenido
sale de `references/blind-spots.md`. Sin ella el reporte se lee como "la placa
está bien", que es una afirmación que estas puertas no pueden sostener.

## Reglas de honestidad

- **No inventes lo que no medís.** Un código LCSC, una dimensión de footprint
  o un valor de componente que no salga de un datasheet o de una medición se
  marca como no verificado. Dejarlo en blanco es estrictamente mejor que
  llenarlo con algo plausible: el hueco se ve, el dato inventado no. Esta es
  exactamente la regla que ya aplica `gen_fab.py` con los LCSC, y la misma que
  usan los frameworks del estado del arte cuando levantan una bandera de
  "fuera de distribución" en vez de completar un pin que no conocen.
- **No reportes verde sin haber visto la salida.** Pegá los conteos reales.
  "los tests pasan" sin el número no es evidencia.
- **Un log no es una corrida.** Si vas a citar `logs/drc.json`, verificá antes
  que G-F lo dé por fresco.

## Referencias

- `references/gates.md` — cada puerta en detalle: qué caza, cómo se corre,
  cómo se lee el fallo, y el ciclo completo de regeneración con sus trampas.
- `references/blind-spots.md` — lo que ninguna puerta cubre. Leelo antes de
  escribir la última sección del reporte.
- `references/research.md` — de dónde salen los criterios de esta skill.
