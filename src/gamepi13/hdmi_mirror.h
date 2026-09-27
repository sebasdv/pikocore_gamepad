#pragma once
// HDMI (DVI over PIO, PicoDVI) mirror of the GamePi13 LCD. Opt-in with
// -DPIKO_GAMEPI13_HDMI=ON. Takes over core 1 (see hdmi_mirror.cpp), so the USB
// sample manager does not run in this build.

// Bring up clocks + DVI and launch core 1 as the video encoder. Call once,
// in place of multicore_launch_core1(piko_sample_manager_core).
void gamepi_hdmi_start();
