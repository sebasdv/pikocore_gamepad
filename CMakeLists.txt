cmake_minimum_required(VERSION 3.18)

option(PIKO_GAMEPI13 "Build for Waveshare RP2350-PiZero + GamePi13" OFF)
# Modo 8 (Browse SD) APARCADO por defecto. La microSD comparte spi1 con el LCD,
# y ese conflicto de bus produjo tres bugs distintos y encadenados (inanicion
# del redibujo, el baudrate que la SD dejaba en 100-400 kHz, y un stall de ~20 s
# con tarjeta presente). Con el flag en OFF el selector cicla 0-7 y el modo 8 es
# inalcanzable: cero actividad de SD en runtime. El codigo queda intacto -- basta
# poner esto en ON para reactivarlo. Cargar samples por USB (.pikobank) no se ve
# afectado. Ver docs/superpowers/specs/2026-07-20-*-design.md.
# Espejo del LCD por HDMI (DVI/PicoDVI por PIO, pines 32-38 del socket de la
# RP2350-PiZero). OJO: ocupa el core 1 para codificar video, asi que en este
# build NO corre el sample manager (carga de bancos por USB / SD).
option(PIKO_HDMI_ONLY "Diagnostic: HDMI colour bars only, no pikocore" OFF)
option(PIKO_HDMI_BARS "Diagnostic: full firmware, but HDMI shows colour bars" OFF)
option(PIKO_HDMI_NOAUDIO "Diagnostic: never enable the audio PWM IRQ" OFF)
option(PIKO_HDMI_XIP "Diagnostic: run from flash (XIP) instead of copy_to_ram" OFF)
option(PIKO_HDMI_EARLY "Diagnostic: start HDMI right after the clock setup" OFF)
option(PIKO_GAMEPI13_HDMI "Mirror the GamePi13 LCD to the HDMI port (takes core 1)" OFF)
option(PIKO_GAMEPI13_SD "Enable the Browse SD mode (mode 8) on GamePi13" OFF)
if(PIKO_GAMEPI13)
	list(APPEND PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/boards)
	set(PICO_BOARD waveshare_rp2350_pizero CACHE STRING "Board type")
endif()

if(NOT PICO_SDK_PATH)
	if(DEFINED ENV{PICO_SDK_PATH})
		set(PICO_SDK_PATH "$ENV{PICO_SDK_PATH}")
	elseif(EXISTS "${CMAKE_CURRENT_LIST_DIR}/../pico-sdk/pico_sdk_init.cmake")
		set(PICO_SDK_PATH "${CMAKE_CURRENT_LIST_DIR}/../pico-sdk")
	elseif(EXISTS "${CMAKE_CURRENT_LIST_DIR}/pico-sdk/pico_sdk_init.cmake")
		set(PICO_SDK_PATH "${CMAKE_CURRENT_LIST_DIR}/pico-sdk")
	endif()
endif()

include(pico_sdk_import.cmake)

project(pikocore C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(${PROJECT_NAME} 
	${CMAKE_CURRENT_LIST_DIR}/src/main.cpp
	${CMAKE_CURRENT_LIST_DIR}/src/PikoAudioBank.cpp
	${CMAKE_CURRENT_LIST_DIR}/src/PikoSampleManager.cpp
	${CMAKE_CURRENT_LIST_DIR}/doth/WS2812.cpp 
	${CMAKE_CURRENT_LIST_DIR}/doth/usb_descriptors.c
)
pico_generate_pio_header(${PROJECT_NAME} ${CMAKE_CURRENT_LIST_DIR}/doth/WS2812.pio)
pico_generate_pio_header(${PROJECT_NAME} ${CMAKE_CURRENT_LIST_DIR}/doth/onewiremidi.pio)

target_link_libraries(${PROJECT_NAME} 
	pico_stdlib
	pico_multicore
	hardware_adc
	hardware_dma
	hardware_pio
	hardware_timer
	hardware_clocks
	hardware_pwm
	hardware_flash
	hardware_sync
    tinyusb_device
    tinyusb_board
)

set_property(TARGET ${PROJECT_NAME} APPEND_STRING PROPERTY LINK_FLAGS "-Wl,--print-memory-usage")

if(PIKO_HDMI_XIP)
	pico_set_binary_type(${PROJECT_NAME} default)
else()
	pico_set_binary_type(${PROJECT_NAME} copy_to_ram)
endif()
pico_enable_stdio_usb(${PROJECT_NAME} 0)
pico_enable_stdio_uart(${PROJECT_NAME} 0)

target_include_directories(${PROJECT_NAME} PRIVATE
	${CMAKE_CURRENT_LIST_DIR}
	${CMAKE_CURRENT_LIST_DIR}/src
)

include(target_compile_definitions.cmake)

if(PIKO_GAMEPI13)
	target_compile_definitions(${PROJECT_NAME} PRIVATE PIKO_GAMEPI13=1)
	if(PIKO_GAMEPI13_SD)
		target_compile_definitions(${PROJECT_NAME} PRIVATE PIKO_GAMEPI13_SD=1)
	else()
		target_compile_definitions(${PROJECT_NAME} PRIVATE PIKO_GAMEPI13_SD=0)
	endif()
	target_sources(${PROJECT_NAME} PRIVATE
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/LCD_1in3.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/GUI_Paint.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/font12.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/font16.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/font20.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd/font24.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/dev_shim.c
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/ui.cpp
	)
	target_include_directories(${PROJECT_NAME} PRIVATE
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/lcd
	)
	target_link_libraries(${PROJECT_NAME} hardware_spi)

	if(PIKO_GAMEPI13_HDMI)
		set(DVI_DIR ${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/01-DVI)
		target_compile_definitions(${PROJECT_NAME} PRIVATE
			PIKO_GAMEPI13_HDMI=1
			PIKO_HDMI_ONLY=$<BOOL:${PIKO_HDMI_ONLY}>
			PIKO_HDMI_BARS=$<BOOL:${PIKO_HDMI_BARS}>
			PIKO_HDMI_EARLY=$<BOOL:${PIKO_HDMI_EARLY}>
			PIKO_HDMI_NOAUDIO=$<BOOL:${PIKO_HDMI_NOAUDIO}>
			PICO_PIO_USE_GPIO_BASE=1
			DVI_DEFAULT_SERIAL_CONFIG=pico_sock_cfg)
		target_sources(${PROJECT_NAME} PRIVATE
			${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/hdmi_mirror.cpp
			${DVI_DIR}/libdvi/dvi.c
			${DVI_DIR}/libdvi/dvi_serialiser.c
			${DVI_DIR}/libdvi/dvi_timing.c
			${DVI_DIR}/libdvi/tmds_encode.S
			${DVI_DIR}/libdvi/tmds_encode.c)
		target_include_directories(${PROJECT_NAME} PRIVATE
			${DVI_DIR}/libdvi ${DVI_DIR}/include ${DVI_DIR}/assets)
		target_link_libraries(${PROJECT_NAME} hardware_interp pico_util)
		pico_generate_pio_header(${PROJECT_NAME} ${DVI_DIR}/libdvi/dvi_serialiser.pio)
		pico_generate_pio_header(${PROJECT_NAME} ${DVI_DIR}/libdvi/tmds_encode_1bpp.pio)
	endif()

	add_subdirectory(${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/03-MicroSD/src
		${CMAKE_CURRENT_BINARY_DIR}/no-OS-FatFS)
	target_sources(${PROJECT_NAME} PRIVATE
		${CMAKE_CURRENT_LIST_DIR}/src/gamepi13/sd_hw_config.c
	)
	target_include_directories(${PROJECT_NAME} PRIVATE
		${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/03-MicroSD/include
		${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/03-MicroSD/src/include
		${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/03-MicroSD/src/sd_driver
		${CMAKE_CURRENT_LIST_DIR}/RP2350-PiZero/C/03-MicroSD/src/ff15/source
	)
	target_link_libraries(${PROJECT_NAME} no-OS-FatFS-SD-SDIO-SPI-RPi-Pico pico_sync)
endif()

target_compile_definitions(${PROJECT_NAME} PRIVATE
	PIKO_FIRMWARE_RESERVE=524288u
	PICO_STDIO_USB_CONNECTION_WITHOUT_DTR=1
	USBD_MANUFACTURER="infinitedigits"
	USBD_PRODUCT="pikocore"
)

pico_add_extra_outputs(${PROJECT_NAME})

add_custom_command(
	TARGET ${PROJECT_NAME}
	POST_BUILD
	COMMAND ${CMAKE_COMMAND}
		-DBIN_FILE="$<TARGET_FILE_DIR:${PROJECT_NAME}>/${PROJECT_NAME}.bin"
		-DFIRMWARE_RESERVE=524288
		-P "${CMAKE_CURRENT_LIST_DIR}/cmake/check_firmware_reserve.cmake"
)
