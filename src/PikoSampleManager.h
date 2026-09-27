#pragma once

#include <stdint.h>

void piko_sample_manager_set_ready();
void piko_sample_manager_core();

#if PIKO_GAMEPI13
// Async request/response API for core0 -> core1 SD operations. Same
// volatile-flag + dmb pattern already used by piko_set_clock_input_ittybittymidi
// (main.cpp), mirrored in the other direction. Core0 must never busy-wait on
// the *_done flags -- poll them once per UI tick instead, so audio (core0's
// ISR) and the rest of the button/LCD loop are never blocked.
extern volatile bool gamepi_sd_list_requested;
extern volatile bool gamepi_sd_list_done;
extern volatile bool gamepi_sd_load_requested;
extern volatile uint32_t gamepi_sd_load_index;
extern volatile bool gamepi_sd_load_done;
extern volatile bool gamepi_sd_load_ok;
extern volatile bool gamepi_sd_unmount_requested;

uint32_t gamepi_sd_file_count();
const char *gamepi_sd_file_name(uint32_t index);
#endif
