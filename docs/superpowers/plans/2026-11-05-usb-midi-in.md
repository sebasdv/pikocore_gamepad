# MIDI IN por USB (etapa 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que el reloj y el transporte MIDI que manda un computador o un celular por el USB-C muevan el secuenciador, en los dos targets, sin tocar la placa.

**Architecture:** un header nuevo en `doth/` con una cola de 64 paquetes USB-MIDI de un productor (core 1, `tud_midi_rx_cb` dentro de `tud_task()`) y un consumidor (core 0, lazo de control), mas un despacho puro que llama a los mismos callbacks que hoy usa el receptor de un hilo. El despacho y la cola se prueban en el host con `cl`; el cableado se prueba compilando los dos targets y en el banco con el GamePi13.

**Tech Stack:** C11/C++17, Pico SDK 2.1.1 (`C:/pico-sdk`), TinyUSB 0.18 del SDK, MSVC `cl` de VS 2022 para el chequeo de host, Python 3.13 + `mido`/`python-rtmidi` para el banco.

**Spec:** `docs/superpowers/specs/2026-11-05-usb-midi-audio-design.md`, seccion "Etapa 1".

## Global Constraints

- Rama `fw/usb-midi-in` cortada de `main` (8f86b52, que trae la spec y no esta pusheada).
- Sin dependencias nuevas; header-only en `doth/`, como `midi_out.h` y `onewiremidi.h`.
- El despacho USB corre siempre, en los dos targets, sin mirar `clock_input_ittybittymidi`.
- Cola: 64 paquetes de 4 bytes. Cola llena: se pierde el paquete mas nuevo y se cuenta.
- Despacho por el byte de estado `packet[1]`: 0xF8 timing, 0xFA start, 0xFB continue, 0xFC stop, 0x9n con velocidad > 0 note_on(nota, vel), 0x9n con velocidad 0 y 0x8n note_off(nota); todo lo demas se descarta. `packet[0]` (cable y CIN) se ignora.
- `MIDI_NOTE_KEY` sigue en 0; las notas se despachan aunque no tengan efecto.
- No se toca nada de `hardware/`, ni GP27/GP28, ni el receptor DIN: eso es la etapa 2.
- Los dos targets compilan: `PIKO_GAMEPI13=ON` y `PIKO_GAMEPAD=ON`.
- Commits terminan con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- **Cola llena con reloj rapido:** el paquete 65 se descarta y se cuenta, y los 64 primeros salen en orden. Test `test_full_queue_drops_newest` en la Tarea 1.
- **Indices que dan la vuelta:** contadores `uint8_t` sobre 64 lugares; 300 empujes y sacadas alternados no pierden ni duplican. Test `test_indices_wrap` en la Tarea 1.
- **Callbacks en NULL:** el struct puede traer notas en NULL; despachar una nota no debe colgar. Test `test_null_callbacks_are_skipped` en la Tarea 1.
- **Mensajes que no son reloj ni notas** (sysex, CC, pitch bend, active sensing, cable distinto de 0): no disparan nada, y una nota en cable 1 igual se despacha. Test `test_ignored_messages` en la Tarea 1.
- **Desenchufar y volver a enchufar con el reloj corriendo:** el promedio de `midi_timing()` arrastra un delta enorme una ventana de 32 pulsos y despues se corrige solo. Paso 6 de la Tarea 3.

---

### Task 1: cola y despacho de MIDI USB, con chequeo de host

**Files:**
- Create: `doth/usb_midi_in.h`
- Create: `tests/firmware/check_usb_midi_in.c`
- Create: `tests/firmware/run_checks.bat`

**Interfaces:**
- Consumes: `PIKO_DMB()` de `src/piko_barrier.h` (el chequeo de host la define vacia antes del include).
- Produces, todo `static inline` en `doth/usb_midi_in.h`, dentro de `extern "C"` como `midi_out.h`:
  - `#define USB_MIDI_IN_QUEUE_LEN 64`
  - `typedef struct UsbMidiInCallbacks { void (*note_on)(uint8_t note, uint8_t velocity); void (*note_off)(uint8_t note); void (*start)(void); void (*cont)(void); void (*stop)(void); void (*timing)(void); } UsbMidiInCallbacks;` (mismo orden que los argumentos de `Onewiremidi_new`)
  - `static volatile uint32_t usb_midi_in_dropped;`
  - `bool usb_midi_in_push(const uint8_t packet[4])` — core 1; `false` = cola llena, descartado y contado.
  - `bool usb_midi_in_pop(uint8_t packet[4])` — core 0; `false` = vacia.
  - `void usb_midi_in_dispatch(const uint8_t packet[4], const UsbMidiInCallbacks *cb)` — puro.
  - `void usb_midi_in_service(const UsbMidiInCallbacks *cb)` — saca todo lo que haya y despacha cada uno; bajo `DEBUG_MIDI` imprime `usb midi dropped\t%lu` cuando el contador cambio desde la ultima vez.

- [ ] **Step 1: crear la rama**

```bash
git switch -c fw/usb-midi-in main
```

- [ ] **Step 2: escribir el runner de chequeos de host**

`tests/firmware/run_checks.bat`, con fin de linea CRLF: llama a `vcvars64.bat` de VS 2022 Community (`C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat`, salida a nul), hace `cd /d %~dp0`, y para cada `check_*.c` compila con `cl /nologo /W4 /WX /std:c11 /I..\..\doth %%f /Fe:"%TEMP%\%%~nf.exe"` (sin redirigir la salida de `cl`, para ver los errores), lo corre, sale con `exit /b 1` si algo falla e imprime `%%~nf OK` si pasa. El bucle `for %%f in (check_*.c) do ( ... || exit /b 1 ...)` ya se probo en esta maquina y propaga el codigo de salida.

- [ ] **Step 3: escribir el chequeo que falla**

`tests/firmware/check_usb_midi_in.c`. Antes del include: `#define PIKO_DMB() ((void)0)`. Callbacks de registro que guardan el ultimo evento en un struct global (`kind`, `note`, `vel`, `count`). Un `reset()` que vacia la cola con `usb_midi_in_pop` y pone `usb_midi_in_dropped = 0`.

```c
static void test_realtime(void) {
  uint8_t p[4] = {0x0F, 0xF8, 0, 0};      dispatch_one(p); assert(ev.kind == EV_TIMING);
  p[1] = 0xFA;                            dispatch_one(p); assert(ev.kind == EV_START);
  p[1] = 0xFB;                            dispatch_one(p); assert(ev.kind == EV_CONT);
  p[1] = 0xFC;                            dispatch_one(p); assert(ev.kind == EV_STOP);
}
static void test_notes(void) {
  uint8_t on[4]  = {0x09, 0x93, 60, 100}; dispatch_one(on);
  assert(ev.kind == EV_NOTE_ON && ev.note == 60 && ev.vel == 100);
  uint8_t on0[4] = {0x09, 0x90, 61, 0};   dispatch_one(on0);
  assert(ev.kind == EV_NOTE_OFF && ev.note == 61);
  uint8_t off[4] = {0x08, 0x8F, 62, 64};  dispatch_one(off);
  assert(ev.kind == EV_NOTE_OFF && ev.note == 62);
}
static void test_ignored_messages(void) {
  const uint8_t ignored[][4] = {
    {0x04, 0xF0, 0x7D, 0x01}, {0x07, 0x02, 0x03, 0xF7},   // sysex
    {0x0B, 0xB0, 7, 100}, {0x0E, 0xE0, 0, 64},            // CC, pitch bend
    {0x0F, 0xFE, 0, 0}, {0x0C, 0xC0, 5, 0},               // active sensing, program
  };
  ev.count = 0;
  for (size_t i = 0; i < sizeof ignored / sizeof ignored[0]; i++) dispatch_one(ignored[i]);
  assert(ev.count == 0);
  uint8_t cable1[4] = {0x19, 0x90, 64, 1}; dispatch_one(cable1);   // cable 1: igual vale
  assert(ev.kind == EV_NOTE_ON && ev.note == 64);
}
static void test_null_callbacks_are_skipped(void) {
  UsbMidiInCallbacks only_clock = {0}; only_clock.timing = rec_timing;
  uint8_t on[4] = {0x09, 0x90, 60, 100};
  ev.count = 0; usb_midi_in_dispatch(on, &only_clock); assert(ev.count == 0);
}
static void test_queue_order_and_service(void) {
  reset();
  uint8_t a[4] = {0x0F, 0xFA, 0, 0}, b[4] = {0x0F, 0xF8, 0, 0};
  assert(usb_midi_in_push(a) && usb_midi_in_push(b));
  ev.count = 0; usb_midi_in_service(&cb);
  assert(ev.count == 2 && ev.kind == EV_TIMING);          // a primero, b ultimo
  uint8_t out[4]; assert(!usb_midi_in_pop(out));          // vacia
}
static void test_full_queue_drops_newest(void) {
  reset();
  uint8_t p[4] = {0x09, 0x90, 0, 1};
  for (int i = 0; i < USB_MIDI_IN_QUEUE_LEN; i++) { p[2] = (uint8_t)i; assert(usb_midi_in_push(p)); }
  p[2] = 99; assert(!usb_midi_in_push(p)); assert(usb_midi_in_dropped == 1);
  uint8_t out[4];
  for (int i = 0; i < USB_MIDI_IN_QUEUE_LEN; i++) { assert(usb_midi_in_pop(out)); assert(out[2] == i); }
  assert(!usb_midi_in_pop(out));
}
static void test_indices_wrap(void) {
  reset();
  uint8_t p[4] = {0x09, 0x90, 0, 1}, out[4];
  for (int i = 0; i < 300; i++) {
    p[2] = (uint8_t)(i & 0x7F); assert(usb_midi_in_push(p));
    assert(usb_midi_in_pop(out)); assert(out[2] == (uint8_t)(i & 0x7F));
    assert(!usb_midi_in_pop(out));
  }
  assert(usb_midi_in_dropped == 0);
}
```

`dispatch_one(p)` es `usb_midi_in_dispatch(p, &cb)` con `cb` apuntando a los seis callbacks de registro. `main` corre los siete tests y devuelve 0.

- [ ] **Step 4: correr y ver que falla**

Run: `cmd //c "$(cygpath -w tests/firmware/run_checks.bat)"`
Expected: error de compilacion de `cl` por `usb_midi_in.h` inexistente, y codigo de salida distinto de 0.

- [ ] **Step 5: escribir `doth/usb_midi_in.h`**

Las firmas del bloque Interfaces. Estado de la cola: `static uint8_t usb_midi_in_buf[USB_MIDI_IN_QUEUE_LEN][4]` y dos contadores `static volatile uint8_t usb_midi_in_head, usb_midi_in_tail` que corren libres; el lugar es `contador & (USB_MIDI_IN_QUEUE_LEN - 1)` y el llenado es `(uint8_t)(head - tail)` (256 es multiplo de 64). Push: si llena, cuenta y devuelve `false`; si no, copia al lugar de `head`, `PIKO_DMB()`, incrementa `head`. Pop: si `head == tail`, `false`; si no, `PIKO_DMB()`, copia el lugar de `tail`, `PIKO_DMB()`, incrementa `tail`. Si `PIKO_DMB` no esta definida, `#include "../src/piko_barrier.h"` (main.cpp ya la incluye antes, el chequeo de host la define vacia). Un comentario arriba dice quien es productor y quien consumidor, y por que la cola existe (la pila USB corre en el core 1 y los callbacks tocan estado del core 0).

- [ ] **Step 6: correr y ver que pasa**

Run: `cmd //c "$(cygpath -w tests/firmware/run_checks.bat)"`
Expected: `check_usb_midi_in OK`, codigo de salida 0, sin warnings (`/W4 /WX`).

- [ ] **Step 7: commit**

```bash
git add doth/usb_midi_in.h tests/firmware/check_usb_midi_in.c tests/firmware/run_checks.bat docs/superpowers/plans/2026-11-05-usb-midi-in.md
git commit -m "fw: cola y despacho de MIDI IN por USB, con chequeo de host"
```

### Task 2: cablear MIDI IN por USB en el firmware

**Files:**
- Modify: `doth/usb_midi_in.h` (el callback de TinyUSB)
- Modify: `src/main.cpp:32-33` (include), `src/main.cpp:~2085` (callbacks antes del lazo), `src/main.cpp:2090-2092` (despacho en el lazo)
- Modify: `README.md:28-29` (una linea en la lista de diferencias)

**Interfaces:**
- Consumes: todo el bloque Produces de la Tarea 1; `tud_midi_n_packet_read(uint8_t itf, uint8_t packet[4])` de TinyUSB; los callbacks existentes de `main.cpp`: `midi_note_on(uint8_t, uint8_t)`, `midi_note_off(uint8_t)`, `midi_start()`, `midi_continue()`, `midi_stop()`, `midi_timing()`.
- Produces: `void tud_midi_rx_cb(uint8_t itf)` con enlace C, definido en `doth/usb_midi_in.h` bajo `#if CFG_TUD_MIDI`.

- [ ] **Step 1: agregar el callback de TinyUSB**

En `doth/usb_midi_in.h`, bajo `#if CFG_TUD_MIDI`: `void tud_midi_rx_cb(uint8_t itf)` vacia el endpoint con `while (tud_midi_n_packet_read(itf, p)) usb_midi_in_push(p);`. No `static`: tiene que pisar la declaracion debil de `midi_device.h:121`. TinyUSB 0.18 no trae una definicion por defecto (llama `if (tud_midi_rx_cb)` en `midi_device.c:538`), asi que la nuestra queda debil pero es la unica. Comentario de una linea que lo diga.

- [ ] **Step 2: incluir y despachar en `main.cpp`**

- Include `"doth/usb_midi_in.h"` junto a `midi_out.h` y `onewiremidi.h` (lineas 32-33), despues de `tusb.h` y `piko_barrier.h`, que ya estan antes.
- Antes del lazo de control, junto a la creacion de `onewiremidi`: `static const UsbMidiInCallbacks usb_midi_in_cb = {midi_note_on, midi_note_off, midi_start, midi_continue, midi_stop, midi_timing};` (inicializacion por posicion: C++17).
- En el lazo, justo despues del `if (clock_input_ittybittymidi && onewiremidi) { Onewiremidi_receive(onewiremidi); }`: `usb_midi_in_service(&usb_midi_in_cb);`, sin condicion, con un comentario de una linea: el USB no tiene jack, la bandera no aplica.

- [ ] **Step 3: compilar los dos targets**

Run:
```bash
cmd //c "C:\pkb\build.bat C:\pkb\g13b g13 C:/pikocore_gamepad"
cmd //c "C:\pkb\build.bat C:\pkb\gp4 gp C:/pikocore_gamepad"
```
(si se ejecuta en un worktree, el tercer argumento es la ruta del worktree con barras normales.)
Expected: `BUILD OK` dos veces; `pikocore.uf2` con fecha de hoy en los dos directorios.

- [ ] **Step 4: confirmar que el callback quedo enlazado**

Run:
```bash
for d in g13b gp4; do "/c/Program Files/DaisyToolchain/bin/arm-none-eabi-nm.exe" C:/pkb/$d/pikocore.elf | grep -w tud_midi_rx_cb; done
```
Expected: una linea por target, tipo `W` o `T`, con direccion distinta de cero. Sin linea, el `if (tud_midi_rx_cb)` de TinyUSB nunca llama y el MIDI se pierde en silencio.

- [ ] **Step 5: README**

En la lista "What's different from stock pikocore", despues del item del cargador USB: `- **MIDI clock and transport over USB** — start, stop, continue and clock from a computer or phone sync the sequencer, in either clock-input mode.`

- [ ] **Step 6: correr el chequeo de host otra vez**

Run: `cmd //c "$(cygpath -w tests/firmware/run_checks.bat)"`
Expected: `check_usb_midi_in OK` (el bloque nuevo esta bajo `CFG_TUD_MIDI`, que en el host no existe).

- [ ] **Step 7: commit**

```bash
git add doth/usb_midi_in.h src/main.cpp README.md
git commit -m "fw: el reloj y el transporte MIDI por USB mueven el secuenciador"
```

### Task 3: prueba en banco con el GamePi13 (necesita al usuario)

**Files:** ninguno; el resultado va al mensaje del PR.

**Interfaces:**
- Consumes: `C:\pkb\g13b\pikocore.uf2` de la Tarea 2.

- [ ] **Step 1: flashear**

El usuario mantiene BOOTSEL, enchufa el GamePi13 y copia `C:\pkb\g13b\pikocore.uf2` a la unidad RP2350. Con un banco ya cargado en flash.

- [ ] **Step 2: ver el puerto**

Run: `python -c "import mido; print(mido.get_output_names())"`
Expected: aparece un nombre que contiene `pikocore`. Hoy, sin el GamePi13, la lista solo trae el GS Wavetable y los dos puertos de Akai.

- [ ] **Step 3: mandar reloj y transporte**

Run (en el directorio de trabajo, no en la scratchpad de otra sesion):
```bash
python - <<'EOF'
import time, mido
name = next(n for n in mido.get_output_names() if "pikocore" in n.lower())
out = mido.open_output(name)
def clock(bpm, secs):
    dt = 60.0 / (24 * bpm); t = time.perf_counter(); end = t + secs
    while t < end:
        out.send(mido.Message("clock")); t += dt
        while time.perf_counter() < t: pass   # espera activa: time.sleep de Windows es grueso
out.send(mido.Message("start")); clock(120, 20)
clock(90, 20)
out.send(mido.Message("stop")); time.sleep(3)
out.send(mido.Message("continue")); clock(120, 10)
out.send(mido.Message("stop"))
EOF
```

- [ ] **Step 4: mirar la pantalla** (el usuario lo reporta)

Expected, en modo CLOCK (el que trae el GamePi13 por defecto):
- `start` arranca la reproduccion.
- En unos segundos el BPM de la barra superior queda en **113** (el firmware pone 7 menos que el reloj, `param_set_bpm(bpm_input - 7, ...)`), y en **83** durante el tramo a 90. Estable dentro de 1.
- `stop` detiene, `continue` vuelve a arrancar, el ultimo `stop` detiene.

- [ ] **Step 5: repetir en modo MIDI**

Cambiar la entrada de reloj a ittybittymidi desde el cargador web (`web/`, el selector que llama a `setClockInputMode`; el firmware lo atiende en `handle_clock_input_mode`), cerrar el cargador para soltar el puerto serie, y repetir los pasos 3 y 4. Expected: lo mismo. El icono de fuente de reloj sigue mostrando el modo elegido, no el USB: es comportamiento conocido, fuera de esta etapa.

- [ ] **Step 6: desenchufar con el reloj corriendo**

Correr el paso 3 con `clock(120, 60)`, desenchufar el USB a los 10 s y volver a enchufar a los 15 s (el script se cae; volver a lanzarlo). Expected: despues de reenchufar, el BPM puede saltar durante una ventana de 32 pulsos (unos 0.7 s) y vuelve a 113 sin tocar nada.

- [ ] **Step 7: abrir el PR**

Con el visto bueno del usuario: push de `fw/usb-midi-in` y PR contra `main`, con el resultado de los pasos 4 a 6 en el cuerpo. El cuerpo termina con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
