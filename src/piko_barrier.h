#pragma once
// Barrera de memoria completa. En el RP2350 es la instrucción "dmb" de ARM; en
// el simulador de PC (sim/, PIKO_SIM=1) es un fence de C++, porque MSVC x64 no
// acepta asm inline. El código generado para ARM no cambia.
#if defined(PIKO_SIM)
#include <atomic>
#define PIKO_DMB() std::atomic_thread_fence(std::memory_order_seq_cst)
#else
#define PIKO_DMB() __asm volatile("dmb" ::: "memory")
#endif
