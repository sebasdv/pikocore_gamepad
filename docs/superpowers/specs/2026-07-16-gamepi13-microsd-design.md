# Fase 3: navegación y carga de bancos desde microSD — Diseño

**Fecha:** 2026-07-16
**Estado:** aprobado por el usuario (formato, modo 8, gesto de confirmación, cacheo, SPI, arquitectura core0/core1)
**Prerequisito:** Fase 1 + Fase 2 completas y verificadas en hardware (rama `port/rp2350-gamepi13`, tag `fase2-completa-verificada`).
**Punto de restauración:** `git reset --hard fase2-completa-verificada` deshace todo lo de esta fase si algo sale mal en hardware.

## Objetivo

Permitir cargar un banco de audio (`.pikobank`) desde la tarjeta microSD integrada del RP2350-PiZero, navegando entre varios archivos sin necesidad de una PC conectada por USB, usando la misma interfaz de botones + LCD que ya existe.

## No-objetivos (fuera de alcance de esta fase)

- Parsear WAV crudos en el dispositivo (se usa el mismo formato `.pikobank` validado que ya produce la web app).
- Streaming de audio directo desde la SD (el audio se sigue reproduciendo desde flash, igual que hoy — la SD es solo el origen de la carga).
- Escritura a la SD desde el dispositivo (solo lectura).
- Detección de inserción/extracción en caliente de la tarjeta (`Card Detect`) — se asume que la tarjeta está puesta antes de entrar al modo 8.
- Múltiples tarjetas o particiones.

## Hallazgo de hardware que condiciona el diseño

El socket de microSD integrado del RP2350-PiZero está cableado a GP30 (SCK), GP31 (MOSI), GP40 (MISO), GP43 (CS). Verificado contra los registros `IO_BANK0_GPIOxx_CTRL_FUNCSEL` del RP2350 (`pico-sdk/src/rp2350/hardware_regs/include/hardware/regs/io_bank0.h`): esos cuatro pines **solo** pueden mapearse a funciones de `spi1` — no existe alternativa `spi0` para ninguno de ellos. El LCD del GamePi13 ya usa `spi1` (GP10 SCK, GP11 MOSI). Es decir, Waveshare diseñó la placa para que el header de 40 pines y el socket de SD **compartan el mismo periférico SPI1**, diferenciados por su línea de Chip Select (GP8 el LCD, GP43 la SD) — un patrón de bus compartido estándar y soportado por la librería FatFS vendorizada (`RP2350-PiZero/C/03-MicroSD/`, "Supports multiple SD Cards per SPI").

Esto implica: como el LCD se refresca desde **core0** y la SD (por la razón de abajo) opera desde **core1**, ambos núcleos pueden intentar usar `spi1` al mismo tiempo — una contención real de periférico, no un descuido de software. Se resuelve con un mutex (`mutex_t`, pico-sdk `pico_sync`) que cualquier acceso a `spi1`, desde cualquier núcleo, debe tomar antes de tocar el bus y soltar al terminar.

## Formato: `.pikobank` prearmado

La SD contiene archivos `.pikobank` en el directorio raíz — el mismo formato binario (magic/version/header de 12 KB/PCM) que hoy sube la web app por USB. Se arman en la PC con la web app; este proyecto agrega ahí un botón "Download" (análogo al que ya existe para el firmware UF2) que llama a la función `buildBankBlob()` ya existente (`web/src/bank.ts`) y dispara la descarga del blob como archivo, sin tocar la lógica de construcción del banco.

En el dispositivo, un archivo leído de la SD se valida con la **misma** función `validate_header()` que ya usa `handle_write()` para las subidas por USB — cero lógica de validación nueva, cero superficie de bugs de parsing adicional.

## Interacción: modo 8 del selector

Se agrega un noveno valor al selector (`gamepi_selector % 9` en vez de `% 8`), dedicado a "Browse SD". No reemplaza ni modifica el modo 6 (Guardar/Cargar), que es configuración (volumen, BPM, etc.) y no tiene relación con esto.

- **Al entrar al modo** (Select llega a la posición 8): se pide a core1 que monte la SD y liste hasta 32 archivos `*.pikobank` del directorio raíz a un buffer compartido. La lista queda cacheada en RAM — no se relee mientras se está en el modo.
- **L / R**: navegan la lista un archivo por toque (paso discreto, sin repeat ni rampa — a diferencia de Function A/B en los otros modos). El LCD muestra el nombre del archivo resaltado y su posición ("3/12"). No tocan la SD ni la flash.
- **Mantener R ~1s** sobre el archivo elegido: dispara la carga. Se muestra una barra de progreso de la cuenta regresiva en el overlay; si se suelta antes de completarse, se cancela sin efecto.
- **Start** conserva su significado global (start/stop) sin importar el modo activo — no se sobrecarga dentro de este modo.
- El audio que esté sonando **no se interrumpe** por navegar la lista; solo se muta durante el instante real de la escritura a flash (mismo mecanismo que ya usa una subida por USB, vía `piko_audio_bank_set_mutating`).
- Al salir del modo 8 (Select avanza a 0), la SD se desmonta.

## Arquitectura

### Por qué la SD y la escritura a flash corren en core1

`multicore_lockout_victim_init()` (agregado en la Fase 2 al arreglar la corrupción de escrituras concurrentes) registra a **core0** como la "víctima" que se pausa durante `flash_range_erase/program`. Esa protección solo funciona si quien la dispara es **core1** — core0 no puede pedirse a sí mismo que se pause. Por lo tanto toda esta feature (montar SD, listar, leer el archivo, validar, escribir a flash) vive en `PikoSampleManager.cpp`, que ya es el dueño de esa responsabilidad y corre en core1.

### Comunicación entre núcleos

Se reutiliza el patrón ya existente en el código (banderas `volatile` + barrera `dmb`, el mismo que usa `piko_set_clock_input_ittybittymidi()` para su ida y vuelta entre núcleos) — no se introduce un mecanismo nuevo:

```
core0 (botones/LCD)                    core1 (piko_sample_manager_core)
──────────────────                     ─────────────────────────────────
sd_list_requested = true      ──────►  ve el flag, monta SD, lista archivos
                                        a sd_file_list[], sd_file_count
sd_list_done (poll)            ◄──────  sd_list_done = true

sd_load_requested = true
sd_load_index = N              ──────►  lee sd_file_list[N] completo, valida,
                                        safe_flash_erase/program (ya blindado)
sd_load_done (poll)             ◄──────  sd_load_done = true, sd_load_ok = true/false
```

`sd_file_list` es un array estático de hasta 32 entradas de 64 bytes (nombre truncado) — sin allocación dinámica, mismo estilo que el resto del firmware.

### Mutex de `spi1`

Un `mutex_t g_spi1_mutex` global, tomado por:
- `dev_shim.c` (LCD), alrededor de cada `LCD_1IN3_DisplayWindows`/`LCD_1IN3_Init`/comando individual — en la práctica, alrededor de todo el cuerpo de `flush()` en `ui.cpp` y de `gamepi_lcd_dev_init()`.
- El driver SD de la librería vendorizada, alrededor de cada transacción — se logra implementando los hooks de bajo nivel que la librería expone (`sd_spi_acquire`/`sd_spi_release`, o el punto equivalente en `sd_driver/SPI/my_spi.c`) en vez de envolver cada llamada dispersa a mano.

Dado que la SD solo se usa en el modo 8 (una acción deliberada y poco frecuente) y el LCD se refresca constantemente pero en ráfagas cortas (~ya acotadas a 25 Hz por el throttle de la Fase 2), la contención esperada es mínima — el mutex solo importa para **correctitud**, no rendimiento.

### CMake

Bajo `PIKO_GAMEPI13`, se agrega el target `no-OS-FatFS-SD-SDIO-SPI-RPi-Pico` (ya vendorizado en `RP2350-PiZero/C/03-MicroSD/src/`) más un `hw_config.c` propio (adaptado del `RP2350-PiZero/C/03-MicroSD/example/config/hw_config.c` ya presente, con un solo `sd_card_t` de tipo `SD_IF_SPI` apuntando a `spi1`, pines sck=30/mosi=31/miso=40/ss=43, `baud_rate = 12 * 1000 * 1000` (12 MHz — conservador; el propio ejemplo del repo usa 12.5 MHz como su primer valor no comentado) y `use_card_detect = false`.

## Cambios en la web app

Un botón "Download bank" junto al "Upload" existente: mismo `buildBankBlob()`, mismo helper de descarga de archivo que ya usa `downloadFirmware()` (`URL.createObjectURL` + `link.download`), destino distinto. Sin lógica nueva de construcción de banco.

## Manejo de errores

Todos no-fatales, no tocan flash ni interrumpen audio:

| Caso | Comportamiento |
|---|---|
| Sin tarjeta insertada | Overlay: "SD: no encontrada". Modo 8 queda vacío/navegable a "atrás". |
| Tarjeta sin archivos `.pikobank` | Overlay: "SD: sin archivos". |
| Archivo no pasa `validate_header()` | Overlay: "Archivo inválido", no se toca flash. |
| Falla de lectura a mitad de carga (tarjeta retirada, etc.) | Se aborta antes de tocar flash si la falla es durante la lectura del archivo completo a buffer; si ya se empezó a escribir, se completa con lo leído hasta el momento y se re-valida (mismo criterio que ya usa `handle_write()` con la fuente USB). |

## Pruebas

1. **Builds**: ambas variantes compilan; la original (flag OFF) no cambia — nada de esto se linkea sin `PIKO_GAMEPI13`.
2. **Hardware**:
   - Sin tarjeta: entrar al modo 8, ver el mensaje de error, salir sin crash.
   - Tarjeta con 1, con >1, y con 0 archivos `.pikobank`.
   - Navegar la lista con L/R, confirmar que el LCD se actualiza y el audio no se corta.
   - Mantener R hasta completar la carga; confirmar que el nuevo banco suena.
   - Soltar R antes de completar; confirmar que NO se tocó flash (el banco anterior sigue sonando igual).
   - Retirar la tarjeta a mitad de una carga (estrés): el dispositivo no debe colgarse ni corromper el banco existente.
   - Con el LCD refrescándose activamente (dashboard con LEDs cambiando), entrar al modo 8 y cargar un banco — confirmar que no hay artefactos visuales ni bloqueos (validación del mutex de `spi1`).
3. **Regresión**: audio y LCD se comportan igual que al final de la Fase 2 en todos los demás modos.

## Riesgos conocidos

- El mutex de `spi1` es la pieza más nueva y menos probada de este diseño — si algo falla en hardware de forma difícil de diagnosticar, el tag `fase2-completa-verificada` es el punto de retorno.
- La librería FatFS vendorizada es grande (~30 archivos fuente); se linkea completa bajo `PIKO_GAMEPI13` — impacto en flash a medir en la primera compilación (hay 16 MB de sobra, no se espera que sea un problema).
