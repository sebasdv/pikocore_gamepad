// Símbolos que src/main.cpp referencia y que en el RP2350 vienen de
// PikoSampleManager.cpp (core1: protocolo USB y modo SD). El simulador no
// compila ese archivo: carga bancos con runtime/bank_hotload.cpp, y el modo SD
// está aparcado (PIKO_GAMEPI13_SD=0, el selector nunca llega al modo 8).
#include "PikoSampleManager.h"

volatile bool gamepi_sd_list_requested = false;
volatile bool gamepi_sd_list_done = false;
volatile bool gamepi_sd_load_requested = false;
volatile uint32_t gamepi_sd_load_index = 0;
volatile bool gamepi_sd_load_done = false;
volatile bool gamepi_sd_load_ok = false;
volatile bool gamepi_sd_unmount_requested = false;

uint32_t gamepi_sd_file_count() { return 0; }
const char* gamepi_sd_file_name(uint32_t index) {
  (void)index;
  return "";
}

void piko_sample_manager_set_ready() {}
void piko_sample_manager_core() {}
