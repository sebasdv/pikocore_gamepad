#pragma once
// Shim único del pico-sdk para el simulador de PC. Cada header pico/... y
// hardware/... de este directorio solo incluye este. Implementa lo mínimo que
// usa el firmware; lo que toca "hardware" delega en las funciones sim_* de
// sim/runtime/sim_hal.cpp.
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef unsigned int uint;
typedef uint64_t absolute_time_t;

// ---- implementado en sim/runtime/sim_hal.cpp ----
extern uint8_t sim_flash_mem[];
uint64_t sim_time_us(void);
void sim_sleep_until_us(uint64_t t_us);
void sim_wfi(void);
bool sim_gpio_get(uint pin);
void sim_gpio_put(uint pin, bool value);
void sim_pwm_set_level(uint pin, uint16_t level);
void sim_pwm_irq_enable(bool enabled);
void sim_irq_set_handler(void (*handler)(void));
void sim_irq_enable(bool enabled);
void sim_spi_write(const uint8_t *src, size_t len);
void sim_flash_erase(uint32_t offset, size_t count);
void sim_flash_program(uint32_t offset, const uint8_t *data, size_t count);

// La flash XIP apunta al buffer simulado: flash_header() de PikoAudioBank.cpp y
// flash_target_contents de main.cpp leen de ahí.
#define XIP_BASE ((uintptr_t)sim_flash_mem)
#define FLASH_PAGE_SIZE (1u << 8)
#define FLASH_SECTOR_SIZE (1u << 12)
#define PICO_NO_HARDWARE 0
#define PICO_PIO_VERSION 0

// ---- tiempo ----
static inline uint64_t time_us_64(void) { return sim_time_us(); }
static inline uint32_t time_us_32(void) { return (uint32_t)sim_time_us(); }
static inline absolute_time_t get_absolute_time(void) { return sim_time_us(); }
static inline uint32_t to_ms_since_boot(absolute_time_t t) { return (uint32_t)(t / 1000u); }
static inline absolute_time_t make_timeout_time_ms(uint32_t ms) { return sim_time_us() + (uint64_t)ms * 1000u; }
static inline bool time_reached(absolute_time_t t) { return sim_time_us() >= t; }
static inline void sleep_us(uint64_t us) { sim_sleep_until_us(sim_time_us() + us); }
static inline void sleep_ms(uint32_t ms) { sleep_us((uint64_t)ms * 1000u); }
static inline void __wfi(void) { sim_wfi(); }
static inline uint32_t save_and_disable_interrupts(void) { return 0; }
static inline void restore_interrupts(uint32_t status) { (void)status; }
static inline bool set_sys_clock_khz(uint32_t khz, bool required) { (void)khz; (void)required; return true; }
enum clock_index { clk_sys = 5 };
static inline uint32_t clock_get_hz(enum clock_index clk) { (void)clk; return 248000000u; }
static inline bool stdio_init_all(void) { return true; }

// ---- gpio ----
enum gpio_function { GPIO_FUNC_SPI = 1, GPIO_FUNC_PWM = 4, GPIO_FUNC_SIO = 5, GPIO_FUNC_PIO0 = 6, GPIO_FUNC_PIO1 = 7 };
#define GPIO_OUT 1
#define GPIO_IN 0
static inline void gpio_init(uint pin) { (void)pin; }
static inline void gpio_set_dir(uint pin, bool out) { (void)pin; (void)out; }
static inline void gpio_pull_up(uint pin) { (void)pin; }
static inline void gpio_pull_down(uint pin) { (void)pin; }
static inline void gpio_set_function(uint pin, enum gpio_function fn) { (void)pin; (void)fn; }
static inline bool gpio_get(uint pin) { return sim_gpio_get(pin); }
static inline void gpio_put(uint pin, bool value) { sim_gpio_put(pin, value); }

// ---- irq (solo existe la del wrap del PWM de audio) ----
#define PWM_IRQ_WRAP 8
#define USBCTRL_IRQ 14
typedef void (*irq_handler_t)(void);
static inline void irq_set_priority(uint num, uint8_t p) { (void)num; (void)p; }
static inline void irq_set_exclusive_handler(uint num, irq_handler_t h) { if (num == PWM_IRQ_WRAP) sim_irq_set_handler(h); }
static inline void irq_set_enabled(uint num, bool en) { if (num == PWM_IRQ_WRAP) sim_irq_enable(en); }

// ---- pwm ----
typedef struct { uint32_t csr, div, top; } pwm_config;
static inline uint pwm_gpio_to_slice_num(uint pin) { return (pin >> 1u) & 7u; }
static inline void pwm_clear_irq(uint slice) { (void)slice; }
static inline void pwm_set_irq_enabled(uint slice, bool en) { (void)slice; sim_pwm_irq_enable(en); }
static inline pwm_config pwm_get_default_config(void) { pwm_config c = {0, 16, 0xffff}; return c; }
static inline void pwm_config_set_clkdiv(pwm_config *c, float div) { (void)c; (void)div; }
static inline void pwm_config_set_wrap(pwm_config *c, uint16_t wrap) { c->top = wrap; }
static inline void pwm_init(uint slice, pwm_config *c, bool start) { (void)slice; (void)c; (void)start; }
static inline void pwm_set_gpio_level(uint pin, uint16_t level) { sim_pwm_set_level(pin, level); }

// ---- spi ----
typedef struct spi_inst spi_inst_t;
#define spi0 ((spi_inst_t *)0)
#define spi1 ((spi_inst_t *)1)
static inline uint spi_init(spi_inst_t *spi, uint baud) { (void)spi; return baud; }
static inline uint spi_set_baudrate(spi_inst_t *spi, uint baud) { (void)spi; return baud; }
static inline int spi_write_blocking(spi_inst_t *spi, const uint8_t *src, size_t len) { (void)spi; sim_spi_write(src, len); return (int)len; }

// ---- flash ----
static inline void flash_range_erase(uint32_t off, size_t count) { sim_flash_erase(off, count); }
static inline void flash_range_program(uint32_t off, const uint8_t *data, size_t count) { sim_flash_program(off, data, count); }
static inline void flash_do_cmd(const uint8_t *tx, uint8_t *rx, size_t count) {
  // JEDEC ID de un chip de 16 MB: fabricante 0xEF, código de capacidad 24.
  (void)tx;
  memset(rx, 0, count);
  if (count >= 4) { rx[1] = 0xef; rx[2] = 0x40; rx[3] = 24; }
}

// ---- adc (el GamePi13 usa knobs virtuales) ----
static inline void adc_init(void) {}
static inline void adc_gpio_init(uint pin) { (void)pin; }
static inline void adc_select_input(uint input) { (void)input; }
static inline uint16_t adc_read(void) { return 0; }

// ---- sync / multicore: el firmware entero corre en un solo hilo ----
typedef struct { int unused; } mutex_t;
static inline void mutex_init(mutex_t *m) { (void)m; }
static inline void mutex_enter_blocking(mutex_t *m) { (void)m; }
static inline void mutex_exit(mutex_t *m) { (void)m; }
static inline void multicore_launch_core1(void (*entry)(void)) { (void)entry; }
static inline void multicore_lockout_victim_init(void) {}
static inline void multicore_lockout_start_blocking(void) {}
static inline void multicore_lockout_end_blocking(void) {}

// ---- pio (solo lo usa el receptor MIDI de un cable, que nunca recibe) ----
typedef struct pio_hw pio_hw_t;
typedef pio_hw_t *PIO;
#define pio0 ((PIO)0)
#define pio1 ((PIO)1)
typedef struct { uint32_t clkdiv, execctrl, shiftctrl, pinctrl; } pio_sm_config;
struct pio_program { const uint16_t *instructions; uint8_t length; int8_t origin; uint8_t pio_version; };
static inline uint pio_add_program(PIO pio, const struct pio_program *p) { (void)pio; (void)p; return 0; }
static inline pio_sm_config pio_get_default_sm_config(void) { pio_sm_config c = {0, 0, 0, 0}; return c; }
static inline void sm_config_set_wrap(pio_sm_config *c, uint t, uint w) { (void)c; (void)t; (void)w; }
static inline void sm_config_set_in_pins(pio_sm_config *c, uint p) { (void)c; (void)p; }
static inline void sm_config_set_set_pins(pio_sm_config *c, uint p, uint n) { (void)c; (void)p; (void)n; }
static inline void sm_config_set_in_shift(pio_sm_config *c, bool r, bool a, uint t) { (void)c; (void)r; (void)a; (void)t; }
static inline void pio_sm_set_consecutive_pindirs(PIO pio, uint sm, uint p, uint n, bool out) { (void)pio; (void)sm; (void)p; (void)n; (void)out; }
static inline void pio_sm_init(PIO pio, uint sm, uint off, const pio_sm_config *c) { (void)pio; (void)sm; (void)off; (void)c; }
static inline void pio_sm_set_clkdiv(PIO pio, uint sm, float div) { (void)pio; (void)sm; (void)div; }
static inline void pio_sm_set_enabled(PIO pio, uint sm, bool en) { (void)pio; (void)sm; (void)en; }
static inline bool pio_sm_is_rx_fifo_empty(PIO pio, uint sm) { (void)pio; (void)sm; return true; }
static inline uint32_t pio_sm_get(PIO pio, uint sm) { (void)pio; (void)sm; return 0; }

// ---- tinyusb (nunca hay host USB) ----
static inline bool tusb_init(void) { return true; }
static inline void tud_task(void) {}
static inline bool tud_mounted(void) { return false; }
static inline uint32_t tud_midi_n_stream_write(uint8_t itf, uint8_t cable, const uint8_t *buf, uint32_t n) { (void)itf; (void)cable; (void)buf; return n; }

#define bi_decl(x)

#ifdef __cplusplus
}
#endif
