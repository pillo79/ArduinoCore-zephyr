# SPDX-License-Identifier: Apache-2.0

cmake_minimum_required(VERSION 3.20.0)

cmake_path(SET ZephyrBase $ENV{ZEPHYR_BASE})
set(NORMALIZED_BOARD_TARGET "${BOARD}${BOARD_QUALIFIERS}")
string(REPLACE "/" "_" NORMALIZED_BOARD_TARGET "${NORMALIZED_BOARD_TARGET}")
string(REPLACE "__" "_" NORMALIZED_BOARD_TARGET "${NORMALIZED_BOARD_TARGET}")
set(DTC_OVERLAY_FILE ${ZephyrBase}/../modules/lib/ArduinoCore-zephyr/loader/boards/${NORMALIZED_BOARD_TARGET}.overlay)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(analog_input)

target_sources(app PRIVATE src/main.cpp)
zephyr_compile_options(-Wno-unused-variable -Wno-comment)
