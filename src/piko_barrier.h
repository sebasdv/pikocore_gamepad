#pragma once
// Full memory barrier: the ARM "dmb" instruction on the RP2350.
#define PIKO_DMB() __asm volatile("dmb" ::: "memory")
