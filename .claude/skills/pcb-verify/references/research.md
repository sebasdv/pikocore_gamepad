# De dónde salen los criterios de esta skill

Relevamiento hecho el 2026-09-01 sobre diseño de PCB asistido por IA. Está acá
para que las decisiones de la skill se puedan discutir contra su fuente en vez
de tomarse por autoridad, y para que se sepa qué revisar si el estado del arte
se mueve.

## El consenso de 2026, en una línea

No existe un botón creíble de "describilo y obtené una placa terminada". El
lugar donde los LLM ayudan más hoy es la captura de esquemático — y ahí la
**alucinación de conectividad es real**, así que ERC, DRC y verificación contra
datasheet son obligatorios, y cada etapa sigue necesitando revisión humana.
Las herramientas comerciales (Cadence AuraStack, Siemens Fuse) van hacia
arquitecturas multi-agente con orquestador, no hacia autonomía.

Esa es exactamente la forma de esta skill: no genera diseño, corre puertas
deterministas y le devuelve a una persona un veredicto con lo que quedó sin
verificar.

## Qué se tomó de cada fuente

### CircuitLM — ERC determinista y niveles de severidad
*Multi-Agent LLM-Aided Design Framework*, arXiv 2601.04505

Modelan el esquemático como grafo y corren un checker programático, con fallas
en cuatro niveles (Critical/Major/Minor/Warning). **Un esquemático pasa solo si
tiene cero Critical y cero Major.**

→ Aplicado como el **veredicto binario** de la skill: los avisos se listan pero
no convierten un rojo en verde. Sin un umbral declarado de antemano, la
tentación de reportar "prácticamente listo" siempre gana.

También aportan el dato más importante del relevamiento: **83–88% de ERC
aprobado contra 21–53% de corrección semántica** en los mismos circuitos, con
fallas del tipo TX↔TX, PWM en pin equivocado, mezcla de dominios 5V/3.3V.

→ Aplicado como la justificación de la sección **"lo que ninguna puerta ve"**,
que es obligatoria en todos los reportes. Ver `blind-spots.md`.

Su Retrieval Agent levanta una bandera **out-of-distribution** y detiene la
ejecución cuando una pieza pedida no existe en la base local, en vez de
inventarle un pinout.

→ Aplicado como la regla de honestidad **"no inventes lo que no medís"**, que
además ya era la política de `gen_fab.py` con los códigos LCSC.

### CircuChain — taxonomía de errores competencia vs cumplimiento
*Disentangling Competence and Compliance in LLM Circuit Analysis*, arXiv 2602.15037

Separan dos dimensiones independientes: **competencia** (saber modelar y
resolver el circuito) y **cumplimiento** (respetar las convenciones y el
procedimiento declarados). Encuentran que se comportan distinto y que conviene
atribuir cada falla a una de las dos antes de intentar arreglarla.

→ Aplicado tal cual en **"cómo clasificar un fallo"**, y encaja sospechosamente
bien con este repo: los errores conocidos de acá —`plane_vias.py` corrido
después del ruteo, ruteo a mano en la GUI que se borra, DRC leído de un log
viejo— son todos de cumplimiento, y su arreglo es rehacer el paso en orden, no
tocar el diseño. Confundirlos mete bugs nuevos.

### PCBSchemaGen — topología contra patrón de referencia
*Constraint-Guided Schematic Design via LLM for PCBs*, arXiv 2602.00510

Verifican por isomorfismo de subgrafos contra patrones de referencia expertos,
con una **tolerancia** que distingue el error real de la variación legítima: un
diseñador puede agregar un capacitor de desacople extra sin romper la topología.
Y comprimen datasheets a semántica de roles de pin para guiar la generación.

→ Aplicado en dos lugares: la regla de **no marcar como error una desviación
que preserva la topología** (evita reportes que gritan por cosas correctas), y
el criterio de que la verificación de footprints y pinouts tiene que **citar el
datasheet**, no una inspección plausible. Ver `blind-spots.md` §3.

### Agentic EDA — el momento del handoff
*Agentic Electronic Design Automation: A Handoff Perspective*, arXiv 2606.19795

El PDF no se pudo extraer a texto legible; se toma solo la tesis del título y
del abstract —dónde un agente debe ceder el control a una herramienta
determinista o a una persona— y no ningún detalle específico.

→ Aplicado como la decisión de **alcance**: la skill verifica y reporta, no
regenera salvo pedido explícito. Regenerar cambia el objeto evaluado en medio
de la evaluación, y la decisión de rehacer un ciclo de ruteo es de la persona.

### Revisión pre-fabricación — la frase que ordena todo
ProtoFlow, *Automated Schematic Review, ERC & DRC: What to Check Before Fabrication*

> "A design can be perfectly connected, perfectly routed, fully DRC-clean, and
> completely wrong."

De ahí salen además dos reglas operativas concretas: **ERC antes del layout,
DRC después de cada pasada de ruteo**, y **si el ruteo lo hizo un servicio
externo, volver a correr el DRC localmente con las reglas de capacidad del
fabricante propio, no las por defecto**. Esta última aplica directo acá, donde
el ruteo lo hace freerouting y existe `pikocore_gamepad.kicad_dru`.

### DFM de JLCPCB — la familia de defectos que el DRC no ve
jlcpcb.com/blog/pcb-design-verification-guide · jlcdfm.com

Acid traps, slivers y dams de máscara insuficientes **pasan los checks
estándar de EDA y causan problemas en la línea de producción**. El DFM gratuito
revisa ~30 puntos sobre gerbers en segundos.

→ Aplicado como **G-7**, puerta propia y no un apéndice del DRC, para que no se
lea como redundante y se saltee.

### Rotaciones del CPL y polaridad
Guía de orientación de componentes de JLCPCB · JLCPCB/JLCPCB-SMT-Assembly-Components-orientation-fix

El 0° del programa de diseño **no es necesariamente** el 0° de JLCPCB: su
referencia es la orientación en el tape-and-reel de la parte. Los errores
típicos son pin 1 en la esquina equivocada y diodos o LEDs al revés. JLCPCB
corrige rotaciones dudosas antes de montar **basándose en la serigrafía**.

→ Aplicado como **G-6**, con la instrucción de revisar rotaciones solo de las
piezas polarizadas y de pin 1 (para las demás da igual) y de exigir marca de
polaridad en la serigrafía fuera del courtyard.

### CLI de KiCad 9
docs.kicad.org/9.0/en/cli/cli.html

`--exit-code-violations` hace que el exit code signifique algo (0 sin
violaciones, 5 con violaciones); sin él siempre sale 0. `--schematic-parity`
cruza placa contra esquemático desde el DRC.

→ Los dos flags se agregaron a los comandos de la skill. El ciclo documentado
originalmente en el repo no usaba ninguno de los dos.

## Lo que no se tomó

- **Arquitecturas multi-agente con orquestador** (Cadence AuraStack, Siemens
  Fuse). Son para generar diseño; acá el diseño lo generan scripts
  deterministas que ya existen y funcionan. Meter agentes en el medio agregaría
  varianza sin agregar capacidad.
- **Verificación por isomorfismo de subgrafos contra patrones de referencia.**
  Es lo más prometedor de la lista para un uso futuro, pero necesita una
  biblioteca de patrones expertos que este proyecto no tiene. Si alguna vez se
  arma —para el boost, el buffer de audio, la sección de alimentación— sería la
  puerta que hoy más falta: es la única del relevamiento que ataca corrección
  funcional en vez de consistencia interna.
- **Cualquier cosa que requiera simulación SPICE.** No hay modelos para este
  diseño y armarlos es un proyecto propio.

## Fuentes

- [CircuitLM: A Multi-Agent LLM-Aided Design Framework](https://arxiv.org/html/2601.04505v2)
- [CircuChain: Disentangling Competence and Compliance in LLM Circuit Analysis](https://arxiv.org/html/2602.15037v1)
- [PCBSchemaGen: Constraint-Guided Schematic Design via LLM for PCBs](https://arxiv.org/html/2602.00510v1)
- [Agentic Electronic Design Automation: A Handoff Perspective](https://arxiv.org/pdf/2606.19795)
- [LLM-Aided Hardware Design in 2026: What Engineers Actually Trust AI With](https://promwad.com/news/llm-aided-hardware-design-2026)
- [AI PCB Design in 2026: What's Real and What's Hype](https://www.protoflow.ai/blog/ai-pcb-design-2026-guide)
- [Automated Schematic Review, ERC & DRC: What to Check Before Fabrication](https://www.protoflow.ai/compare/ai-pcb-design-rule-check)
- [JLCPCB — PCB Design Verification Guide](https://jlcpcb.com/blog/pcb-design-verification-guide)
- [JLCPCB — Component Polarity & Orientation Identification Guide](https://jlcpcb.com/help/article/component-polarity-and-orientation-identification-guide)
- [JLCPCB — SMT Assembly Components Orientation Fix](https://github.com/JLCPCB/JLCPCB-SMT-Assembly-Components-orientation-fix)
- [JLCDFM — DFM gratuito](https://jlcdfm.com/)
- [KiCad 9 Command-Line Interface](https://docs.kicad.org/9.0/en/cli/cli.html)
- [EDA AI Agents: Intelligent Automation in Semiconductors & PCBs — EE Times](https://www.eetimes.com/eda-ai-agents-intelligent-automation-in-semiconductor-pcb-design/)
