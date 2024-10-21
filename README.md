> [!IMPORTANT]  
> This core is in **BETA**. 🧪  
> Features may change, and bugs may be present. Use for testing only and provide feedback to help us improve.

# 🚧 Arduino Core for Zephyr 

This repository contains the official implementation of **Arduino Core** for Zephyr RTOS based board.

## 🧐 What is Zephyr? 

[Zephyr RTOS](https://zephyrproject.org/) is an open-source, real-time operating system designed for low-power, resource-constrained devices. It's modular, scalable, and supports multiple architectures.

![Zephyr RTOS Logo](doc/zephyr_logo.jpg)

## ⚙️ Installation

Install the core and its toolchains via Board Manager:
* Download and install the latest [Arduino IDE](https://www.arduino.cc/en/software) (only versions `2.x.x` are supported)
* Open the *'Settings / Preferences'* window
* Open the *'Boards Manager'* from the side menu and search for *'Zephyr'*
  * If it doesn’t appear, add the following URL to the *'Additional Boards Manager URLs'* field: `https://downloads.arduino.cc/packages/package_zephyr_index.json` (if you have multiple URLs, separate them with a comma)
* Install the `Arduino Zephyr Boards` platform

Alternatively, to install the core using the command line, run the following command with the Arduino CLI:

```bash
arduino-cli core install arduino:zephyr --additional-urls https://downloads.arduino.cc/packages/package_zephyr_index.json
```

## 🧢 Under the hood

Unlike traditional Arduino implementations, where the final output is a standalone binary loaded by a bootloader, this core generates a freestanding `elf` file. This file can be dynamically loaded by a precompiled Zephyr firmware, referred to as the `loader`.

For the end user, installing the `loader` is easy. Simply run `Burn Bootloader` option from the IDE/CLI while the board is in bootloader mode (by double-clicking the RESET button). Note that due to limitations in the Arduino IDE, you may need to select any programmer from the `Programmers` menu.

To load the first sketch, the board must also be manually placed into bootloader mode. After this initial setup, the standard "autoload" method will take over for future sketches.

To ensure flexibility, the `loader` project is designed to be generic. Any necessary modifications for specific boards should be made in the corresponding `DTS overlay` or a special `fixup` file, using appropriate guards to maintain stability.

The behavior of the `loader` can be adjusted through the `Mode` menu:
- `Standard`: The sketch is loaded automatically.
- `Debug`: The user must type `sketch` in Zephyr's shell, which is accessible via the default Serial.

The most important components of this project are:

* [Zephyr based loader](/loader)
* [LLEXT](https://docs.zephyrproject.org/latest/services/llext/index.html)
* [Actual core](/cores/arduino) with [variants](/variants) and the usual `{platform,boards}.txt`
* [ArduinoCore-API](https://github.com/arduino/ArduinoCore-API)
* [post_build_tool](/extra/post_build_tool)

## 🛠️ Setup the environment

In this section, we’ll guide you through setting up your environment to work with the core, making it easy to compile and upload your sketches to compatible boards.

Shell scripts are available to simplify the installation process (Windows is not supported at the moment 😔).

### Clone the repository
```bash
mkdir my_new_zephyr_folder && cd my_new_zephyr_folder
git clone https://github.com/arduino/ArduinoCore-zephyr
```
### Pre-requirements
Before running the installation script, ensure that `python3` and `pip` are installed on your system. The script will automatically install `west` and manage the necessary dependencies.

### Run the ```bootstrap``` script
```bash
cd ArduinoCore-zephyr
./extra/bootstrap.sh
```
### Install the Zephyr SDK
Download and install the Zephyr SDK for your OS from [here](https://github.com/zephyrproject-rtos/sdk-ng/releases/tag/v0.16.8).

> [!NOTE]  
> This core is validated for version v0.16.8. Compatibility with later versions has not been tested yet.

### Build the Loader

To build a loader, run the following commands:
```bash
export ZEPHYR_SDK_INSTALL_DIR=$folder_where_you_installed_the_sdk
./extra/build.sh $zephyr_board_name $arduino_variant_board_name
```
Replace `$zephyr_board_name` and `$arduino_variant_board_name` with the appropriate names for your board.

Example for Arduino Portenta H7:
```bash
./extra/build.sh arduino_portenta_h7//m7 arduino_portenta_h7
```

The firmwares will be copied to [firmwares](/firmwares) folder.

### Flash the Loader

If the board is fully supported by Zephyr, you can flash the firmware directly onto the board using the following command:
```bash
west flash
```

## 🖥️ Using the Core in Arduino IDE/CLI

After running the `bootstrap` script, you can symlink the core to `$sketchbook/hardware/arduino-git/zephyr`. Once linked, it will appear in the IDE/CLI, and the board's Fully Qualified Board Name (FQBN) will be formatted as `arduino-git:zephyr:name_from_boards_txt`.

## 🔧 Troubleshooting

### Common Issues

#### **Q: My Sketch doesn't start (Serial doesn't appear)**
**A:** Connect a USB-to-UART adapter to the default UART (eg. TX0/RX0 on Giga, TX/RX on Nano) and read the error message (with the sketch compiled in `Default` mode). If you don't own a USB-to-UART adapter, compile the sketch in `Debug` mode; this will force the shell to wait until you open the Serial Monitor. Then, run `sketch` command and *probably* you'll be able to read the error (if generated by `llext`). For OS crashes, the USB-to-UART adapter is the only way to collect the crash.

---

#### **Q: I did it and I get the error: `<err> llext: Undefined symbol with no entry in symbol table ...`**
**A:** This means you are trying to use a Zephyr function which has not yet been exported. Open `llext_exports.c`, add the function you need and recompile/upload the loader.

---

#### **Q: I want to use a Zephyr subsystem which is not compiled in**
**A:** Open the `.conf` file for your board, add the required `CONFIG_`, recompile/upload the loader.

---

#### **Q: I get an OS crash, like `<err> os: ***** USAGE FAULT *****`**
**A:** This is usually due to a buffer overflow or coding error in the user's own code. However, since the project is still in beta 🧪, a [good bug report](#bug-reporting) could help identify any issues in our code.

---

#### **Q: I get an out of memory error**
**A:** Since collecting bug reports is very important at this time, we are keeping Zephyr's shell enabled to allow loading a full sketch (which requires a large stack). Adjust your board's `.conf` file to reduce the stack size if your platform doesn't have enough RAM.

## 📚 Libraries

### Included with the core: ###

### Separately supplied: ###
- **ArduinoBLE**: This library is enabled only for the Arduino Nano 33 BLE. Please use [this branch](https://github.com/facchinm/ArduinoBLE/tree/zephyr_hci) to test it.

## 🚀 Adding a new target

To add a new board that is already supported by mainline Zephyr, follow these steps:

* Create the `DTS overlay` and `.conf` files in the [loader](/loader/boards) directory.
  The overlay must include:
  * A flash partition called `user_sketch`, tipically located near the end of the flash.
  * A `zephyr,user` section containing the description for GPIOs, Analog, UART, SPI and I2C devices. Feel free to leave some fields empty in case Zephyr support is missing. This will result in some APIs not being available at runtime (eg. `analogWrite` if PWM section is empty).
* Build the Loader: run `./extra.build.sh $your_board $your_board` and start debugging the errors. :grin:
* Update the `boards.txt`: add an entry for your board, manually filling the required fields.
* Implement touch support: if your board supports the `1200bps touch` method, implement `_on_1200_bps` in a file located inside the `variant/your_board` folder.
* ⏳ Temporary steps
  * Create `includes.txt` based on `llext-edk/Makefile.cflags`, taking inspiration for other variants.
  * Amend `your_board.compiler.zephyr.*` with information from `llext-edk/Makefile.cflags`.

## 🐛 Bug Reporting

To report a bug, open the [issues](/../../issues) and follow the instructions. Any issue opened without the needed information will be discarded.

## 🙌 Contributions

Contributions are always welcome. The preferred way to receive code contribution is by submitting a [Pull request](/../../pulls).

> [!WARNING] 
> At this stage of development, we only accept Pull requests for bug fixes and features. We do **not** accept support for new targets.

## 📌 Upcoming features

- [ ] Unify overlay in [loader](/loader/boards) with the one provided in [variant](/variant) for interoperability with GSoC project
- [ ] Autogenerate `defines.txt`, `includes.txt`, `cflags.txt` from `llext-edk` output
- [ ] Network: support UDP and TLS
- [ ] USB: switch to USB_DEVICE_STACK_NEXT to support PluggableUSB
- [ ] Relocate RODATA in flash to accomodate sketches with large assets
- [ ] Provide better error reporting for failed llext operations
- [ ] Replace [llext_exports.c](/loader/llext_exports.c) with proper symbols generation (via includes)
- [ ] Provide better usability for `Debug` builds (eg. shell over USB)
- [ ] Fix corner cases with `std::` includes (like `<iterator>`)
- [ ] Get rid of all warnings

## 🌟 Acknowledgments

This effort would have been very hard without the [GSoC project](/README.gsoc.md) and the Zephyr community.
