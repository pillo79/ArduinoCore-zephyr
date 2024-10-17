---
name: Runtime bug report
about: Sketch compiles and uploads but doesn't run correctly (or doesn't run at all)
title: ''
labels: ''
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**Target board + cli verbose compilation output**
**Full verbose** compilation output, ideally with `arduino-cli` invocation or from IDE 2.3.3+
Issues without the full verbose output will be discarded as invalid.

**Output of Serial Monitor**
1. If you have an USB-to-Serial adapter, paste the complete output of the console crash, starting from
```*** Booting Zephyr OS build v3.7...```
2. If you don't, compile the sketch in `Debug` mode (see *Troubleshooting section* in README) and paste the output after invoking `sketch` command
Runtime issues without the **full output** will be discarded as invalid.

**Output of readelf**
You can find the loaction of the elf file by compiling in Verbose mode and looking near the end of the compilation output (after `Linking everything together..`)
Paste (or attach) the output of `arm-none-eabi-readelf -a $your_sketch_elf_file`

**Optional: attach the elf file**

**Optional: attach the sketch**

**Additional context**
Add any other context about the problem here.
