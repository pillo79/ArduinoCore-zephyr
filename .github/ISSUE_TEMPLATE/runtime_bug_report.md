---
name: Runtime bug report
about: Sketch compile and uploads but doesn't run correctly (or doesn't run at all)
title: ''
labels: ''
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**Target board + cli verbose compilation output**
**Full verbose** compilation output, ideally with `arduino-cli` invocation or from IDE 2.3.3+
Issues without the full verbose output will be discarded as invalid.

**Output of debug UART**
Complete output of the console crash, starting from
```*** Booting Zephyr OS build v3.7...```
Runtime issues without the **full UART output** will be discarded as invalid.

**Output of readelf**
Paste (or attach) the output of `arm-none-eabi-readelf -a $your_sketch_elf_file`

**Optional: attach the elf file**

**Output: attach the sketch**

**Additional context**
Add any other context about the problem here.
