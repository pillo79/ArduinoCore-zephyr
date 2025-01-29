# SPDX-License-Identifier: Apache-2.0
zephyr_include_directories(.)
zephyr_include_directories(../../variants)

if(NOT DEFINED ARDUINO_BUILD_PATH)

zephyr_sources(zephyrSerial.cpp)
zephyr_sources(zephyrCommon.cpp)
zephyr_sources(USB.cpp)
zephyr_sources(itoa.cpp)

zephyr_sources(api/CanMsg.cpp)
zephyr_sources(api/CanMsgRingbuffer.cpp)
zephyr_sources(api/Common.cpp)
zephyr_sources(api/IPAddress.cpp)
zephyr_sources(api/Print.cpp)
zephyr_sources(api/Stream.cpp)
zephyr_sources(api/String.cpp)

if(DEFINED CONFIG_ARDUINO_ENTRY)
zephyr_sources(main.cpp)
zephyr_sources(threads.cpp)
endif()

endif()

