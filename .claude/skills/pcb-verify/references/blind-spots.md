# Lo que ninguna puerta ve

Esta lista alimenta la última sección del reporte, que es obligatoria incluso
—sobre todo— cuando todo está en verde.

## Por qué la sección es obligatoria

Hay un dato del estado del arte que conviene tener a mano: en un framework de
generación de circuitos con LLM medido en 2026, los esquemáticos generados
pasaban el ERC automático entre el **83% y el 88%** de las veces. Cuando a los
mismos esquemáticos se les preguntó si además **hacían lo que se les había
pedido**, la tasa cayó al **21–53%**. Las fallas típicas no eran violaciones de
regla: era TX conectado a TX, un PWM en un pin que no lo tiene, un periférico
de 5V colgado de un dominio de 3.3V.

Ninguna de esas tres cosas la ve un ERC. Todas son perfectamente legales
eléctricamente. Por eso un reporte que dice "todas las puertas pasan" y se
detiene ahí no es un reporte honesto: describe consistencia interna y se lee
como corrección.

## 1. Corrección funcional

El circuito puede estar íntegramente conectado y no hacer lo que tiene que
hacer. Ninguna puerta de este repo verifica:

- que la topología del regulador sea la adecuada para la carga;
- que el divisor de realimentación dé la tensión que se quiere;
- que falte o sobre un capacitor de bulk;
- que un periférico esté en el bus correcto;
- que los dominios de tensión cierren en cada interfaz.

Esto se resuelve con criterio de ingeniería, simulación y banco. No con checks.

## 2. Valores todavía no calculados

De la checklist de fabricación, lo que sigue abierto por cálculo y no por
compra:

- **§4 — valores del lazo del boost.** Hay que calcularlos, no comprarlos.
- **§2 — partes sin elegir.** Bloquean G-0 legítimamente.
- **§7 — deuda abierta por la verificación del jack.** La verificación contra
  datasheet destapó un error de circuito y dos footprints equivocados. Que la
  verificación de UNA pieza haya encontrado tres bugs es el mejor argumento
  disponible para verificar las demás igual.

Revisá el estado real de esas secciones en
`docs/hardware/pikocore_gamepad-jlcpcb-checklist.md` antes de darlas por
cerradas: la checklist se edita y las secciones tachadas cambian.

## 3. Footprint ↔ land pattern del datasheet

G-0 verifica que **alguien marcó** el footprint como verificado. No verifica
que la verificación haya sido correcta.

El único chequeo real es abrir el datasheet y comparar el dibujo de land
pattern con el `.kicad_mod`: separación de pads, tamaño, pin 1, courtyard,
altura. Un footprint provisional que llega a fabricación es una placa donde la
pieza no entra, y para cuando se descubre ya se pagó el pedido.

Las dos piezas grandes (el jack Same Sky y el módulo RP2350-Plus de Waveshare)
tienen modelo 3D del fabricante con offsets **ajustados a mano** en KiCad. No
los re-derives por cálculo: son ensamblajes cuyos ejes no se leen bien
muestreando coordenadas.

## 4. Polaridad y orientación

- **Pin 1 en la esquina correcta** de cada IC: el símbolo del esquemático y el
  footprint tienen que coincidir en cuál es el pin de polaridad.
- **Cátodo de diodos y LEDs**: en montaje profesional la orientación depende
  del tape-and-reel, no del footprint.
- **Rotación del CPL** contra la orientación del reel de la parte LCSC elegida.
  Ver G-6 en `gates.md` — es el error caro que ninguna herramienta detecta.
- **Serigrafía que marque la polaridad** fuera del courtyard (símbolo de diodo,
  `K` o `-` junto al pad de cátodo). Además de ayudar al armado a mano, es lo
  que le permite a JLCPCB corregir una rotación dudosa antes de montar.

## 5. Físico y mecánico

- que la placa entre en el gabinete;
- que el jack, los botones y el display queden alineados con sus aberturas;
- que ningún conector quede colgando del borde o pisando un tornillo;
- que las alturas no choquen con la tapa;
- que el contorno del `.kicad_pcb` siga coincidiendo con el DXF de Rhino.

## 6. Térmico, integridad de señal, impedancia

Nada del flujo mira disipación, caídas en los planos, ni impedancia controlada.
Para este diseño probablemente no haga falta, pero "no hace falta" es una
decisión de ingeniería que hay que tomar explícitamente, no un hecho que las
puertas verdes establezcan.

## 7. Manufactura en la línea

Acid traps, slivers, dams de máscara insuficientes: pasan el DRC limpio y
arruinan la placa en producción. Los caza el DFM externo (G-7), no KiCad.

## 8. Firmware sobre hardware real

G-4 compara el pinout de la PCB con el `config.h`. Que coincidan no dice que el
firmware funcione: dice que apuntan al mismo pin. Todo lo demás —niveles,
timing, pull-ups, comportamiento del periférico— es banco.

## Cómo escribir la sección

No pegues esta lista entera en cada reporte. Elegí lo que aplica a lo que se
cambió, y decilo en términos de riesgo concreto:

> **Lo que ninguna puerta verificó:** el footprint del jack se marcó como
> verificado en `params.py` pero no lo revisé contra el datasheet en esta
> corrida; los valores del lazo del boost (§4) siguen sin calcular; y nadie
> chequeó las rotaciones del CPL contra el reel de las partes LCSC, que es
> donde se pierden las placas que pasan todos los checks.
