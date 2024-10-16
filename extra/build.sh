if [ x$ZEPHYR_SDK_INSTALL_DIR == x"" ]; then
export ZEPHYR_SDK_INSTALL_DIR=/ssd/zephyr-sdk-0.16.8/
fi

set -e

board=$1
variant=$2

if [[ $# -eq 0 ]]; then
board=arduino_giga_r1//m7
variant=arduino_giga_r1_m7
fi

source venv/bin/activate

(west build loader -b $board -p && west build -t llext-edk)
(tar xvfp build/zephyr/llext-edk.tar.xz --directory variants/$variant/)

(cp build/zephyr/zephyr.elf firmwares/zephyr-$variant.elf)
if [ -f build/zephyr/zephyr.bin ]; then
    cp build/zephyr/zephyr.bin firmwares/zephyr-$variant.bin
elif [ -f build/zephyr/zephyr.hex ]; then
    cp build/zephyr/zephyr.hex firmwares/zephyr-$variant.hex
fi

