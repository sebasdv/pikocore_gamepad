# Search for all source files in the current directory
# and save the names to the DIR_examples_SRCS variable
set(PICO_SDK_PATH "E:/pico/pico-sdk")
aux_source_directory(. DIR_examples_SRCS)

include_directories(../lib/Config)
include_directories(../lib/GUI)
include_directories(../lib/Infrared)
include_directories(../lib/LCD)
include_directories(../lib/Icm20948)


# Generate link library
add_library(examples ${DIR_examples_SRCS})
target_link_libraries(examples PUBLIC Config LCD Infrared  Icm20948)