# Mejoras futuras: candidatos a portar desde zeptocore (_core)

**Fecha:** 2026-07-20
**Estado:** research / backlog (no comprometido a implementación)
**Fuente:** `github.com/schollz/_core` (README + árbol de `lib/` + lectura del reverb).
El lado zeptocore viene de su README/docs y un vistazo al DSP, NO de una lectura
completa de su código — profundizar por área antes de comprometer cualquier port.

## Encuadre

pikocore es el hermano **deliberadamente minimalista y barato** de zeptocore; ambos
salen del linaje `_core` de schollz. Las diferencias son simplificaciones para bajar
costo y caber en un RP2040 pelado, no bugs. El port a GamePi13 subió el piso de
hardware (RP2350 más rápido + más RAM/flash, + LCD color + SD), así que nuestra versión
hoy queda *entre* el pikocore original y zeptocore — de ahí el interés en re-agregar
cosas que se habían dejado afuera.

## Comparación (resumen)

| Eje | pikocore (nuestro, GamePi13) | zeptocore (_core) |
|---|---|---|
| MCU | RP2350 (port) / RP2040 orig. | RP2040 |
| Audio | **8-bit, 24 kHz**, salida **PWM** (GP18) | **16-bit, 44.1 kHz**, salida **I2S** (DAC) |
| Síntesis | Solo playback de samples | Sampler + synth wavetable (single-cycle) |
| Efectos activos | Filtro LPF, distorsión, noise gate, timestretch granular, FX por probabilidad (jump/túnel/gate/retrig/reversa) | ~16: reverb (Freeverb), tape delay, tape stop, comb, bitcrush, resonant filter, shapers, transfer function, saturation, fuzz, beat repeat… |
| Efectos latentes en NUESTRO repo | **bitcrush + delay presentes pero comentados** (`doth/delay.h` incluido; `delay.Update()` y bitcrush comentados en `main.cpp`) | — |
| Banco/samples | 1 banco de ≤128 samples desde flash (+ Browse SD) | 16 bancos × 16 tracks = 256 archivos en SD |
| Secuenciador | Grabar/reproducir | Real-time con cuantización |
| MIDI | Clock **in** (onewire/ittybitty) | **In + out por USB** + clock sync out; comparte `onewiremidi` con pikocore |
| Display | LCD color (nuestro aporte) | OLED SSD1306 (`ssd1306.h/.c`) |

## Hallazgos clave de factibilidad

1. **Los efectos son portables a nuestro pipeline pese al audio 8-bit.** El DSP de
   zeptocore está en headers C autocontenidos de **punto fijo** (`lib/*.h`,
   `fixedpoint.h`). Un efecto procesa el stream digital *antes* del PWM, así que su
   calidad es independiente de que la salida final sea 8-bit. Ejemplos directos:
   `freeverb_fp_mono.h`, `tapedelay.h`, `delay.h`, `bitcrush.h`, `comb.h`,
   `saturation.h`, `resonantfilter.h`, `beatrepeat.h`.

2. **El muro para 16-bit es el hardware de salida, no el software.** zeptocore usa
   I2S (`lib/my_pico_audio_i2s/`) → DAC de 16-bit; nosotros PWM en GP18. El GamePi13 no
   tiene DAC I2S, así que 16-bit real necesitaría hardware extra. **Separado** de los
   efectos — no los bloquea.

3. **Reverb concretamente factible.** `freeverb_fp_mono.h`:
   - Interfaz: `FV_Reverb_process(self, int32_t *buf, n)`, Q16.16, **punto fijo puro
     (sin float)**.
   - ~7 filtros/sample (4 comb + 3 allpass) → costo de CPU trivial en RP2350 @ 248 MHz.
   - ~20-36 KB de buffers de delay (tuneados a 44.1 kHz; a 24 kHz escalarían a ~19 KB).
     Affordable: RP2350 tiene 520 KB de RAM, el framebuffer usa 115 KB.
   - Adaptación: convertir `audio_now` (8-bit, centro 128) a int32 Q16.16, correr
     `process()`, volver a 8-bit para el PWM; retunear tamaños de buffer para 24 kHz.

## Candidatos, por riesgo/esfuerzo

**🟢 Bajos:**
- Reactivar **bitcrush** (código comentado en `main.cpp`, solo exponerlo).
- Reactivar **delay** (`doth/delay.h` ya vendorizado; `delay.Update()` comentado).
- **MIDI out** (`midi_out.h`; onewire compartido con pikocore).

**🟡 Medios:**
- **Reverb** (`freeverb_fp_mono`) — recomendado como primer port "insignia": es el
  efecto que más falta vs zeptocore, autocontenido (un `process()` en la ruta de
  audio), factible y ya escrito/probado.
- **Multi-banco** estilo 16×16 aprovechando la SD ya montada (hoy cargamos 1 banco).
- **Cuantización** en el secuenciador.
- **tape delay / resonant filter / beat repeat** (siguiente tanda de efectos).

**🔴 Altos (límite de hardware, no solo software):**
- **Audio 16-bit / 44.1 kHz**: requiere DAC I2S (o PWM de mayor resolución) — mayor
  impacto sonoro pero bloqueado por hardware.
- **Synth wavetable**: subsistema nuevo entero (`wavetableosc.h`/`wavetablesyn.h`).

## Próximo paso sugerido cuando se retome

Empezar por **reverb** (máximo impacto, riesgo acotado) o, si se quiere validar primero
el mecanismo de "insertar un efecto de zeptocore en la ISR" con algo mínimo, por
**bitcrush** (menor riesgo). Cada candidato va por su propio ciclo spec→plan, y conviene
profundizar en el código fuente de zeptocore para el área específica antes de
comprometerlo.
