cmake_minimum_required(VERSION 3.20)
project(pikocore_sim C CXX)

if(NOT MSVC)
  message(FATAL_ERROR "pikocore-sim se compila con MSVC (Visual Studio 2022)")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)
# $<0:> evita el subdirectorio por configuración: todo queda en build-sim/bin.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin/$<0:>)

set(PIKO_ROOT ${CMAKE_CURRENT_LIST_DIR}/..)
set(SIM_ROOT ${CMAKE_CURRENT_LIST_DIR})

include(${SIM_ROOT}/cmake/flatten_easing.cmake)
piko_flatten_easing(${PIKO_ROOT}/doth/easing.h ${CMAKE_BINARY_DIR}/gen/doth/easing.h)

# ---- el firmware real, compilado contra el shim ----
add_library(piko_fw STATIC
  ${PIKO_ROOT}/src/main.cpp
  ${PIKO_ROOT}/src/PikoAudioBank.cpp
  ${PIKO_ROOT}/src/gamepi13/ui.cpp
  ${PIKO_ROOT}/src/gamepi13/dev_shim.c
  ${PIKO_ROOT}/src/gamepi13/lcd/LCD_1in3.c
  ${PIKO_ROOT}/src/gamepi13/lcd/GUI_Paint.c
  ${PIKO_ROOT}/src/gamepi13/lcd/font12.c
  ${PIKO_ROOT}/src/gamepi13/lcd/font16.c
  ${PIKO_ROOT}/src/gamepi13/lcd/font20.c
  ${PIKO_ROOT}/src/gamepi13/lcd/font24.c
)
target_include_directories(piko_fw PUBLIC ${SIM_ROOT}/shim)
# gen/ va antes que la raíz del repo: "doth/easing.h" resuelve a la copia aplanada.
target_include_directories(piko_fw PRIVATE
  ${CMAKE_BINARY_DIR}/gen
  ${PIKO_ROOT}
  ${PIKO_ROOT}/src
  ${PIKO_ROOT}/src/gamepi13
  ${PIKO_ROOT}/src/gamepi13/lcd
)
# Mismas defines que el build del RP2350 (target_compile_definitions.cmake usa
# ${PROJECT_NAME} como target).
set(PIKO_SIM_PROJECT_NAME ${PROJECT_NAME})
set(PROJECT_NAME piko_fw)
include(${PIKO_ROOT}/target_compile_definitions.cmake)
set(PROJECT_NAME ${PIKO_SIM_PROJECT_NAME})
target_compile_definitions(piko_fw PRIVATE
  PIKO_GAMEPI13=1
  PIKO_GAMEPI13_SD=0
  PIKO_SIM=1
  PIKO_FIRMWARE_RESERVE=524288u
  _CRT_SECURE_NO_WARNINGS
)
# El main() del firmware no puede llamarse main: lo arranca el simulador.
set_source_files_properties(${PIKO_ROOT}/src/main.cpp PROPERTIES
  COMPILE_DEFINITIONS "main=piko_firmware_main")
# /W1: el firmware no es nuestro para limpiar warnings de MSVC. C4828: fonts.h
# tiene bytes latin-1.
target_compile_options(piko_fw PRIVATE /W1 /wd4828)

# ---- núcleo del simulador (sin firmware ni Win32; testeable aislado) ----
add_library(sim_core STATIC
  core/st7789.cpp
  core/pwm_dac.cpp
  core/flash_store.cpp
  core/bank_file.cpp
)
target_include_directories(sim_core PUBLIC ${SIM_ROOT} ${PIKO_ROOT}/src)
target_compile_options(sim_core PRIVATE /W4 /utf-8)
# flash_store.cpp usa _wfopen (no _wfopen_s) para poder pasarle un modo
# ("r+b"/"w+b") elegido en tiempo de ejecución.
target_compile_definitions(sim_core PRIVATE _CRT_SECURE_NO_WARNINGS)

enable_testing()
add_executable(pikocore_sim_tests
  tests/unit_main.cpp
  tests/unit_st7789.cpp
  tests/unit_audio.cpp
  tests/unit_flash_bank.cpp
  tests/synth_bank.cpp
)
target_link_libraries(pikocore_sim_tests PRIVATE sim_core)
target_compile_options(pikocore_sim_tests PRIVATE /W4 /utf-8)
target_compile_definitions(pikocore_sim_tests PRIVATE _CRT_SECURE_NO_WARNINGS)
add_test(NAME unit COMMAND pikocore_sim_tests)
