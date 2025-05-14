## Sync Zephyr Artifacts tool

This tool fetches the pre-built files that are associated with the current
revision of the Arduino core for Zephyr. This makes it possible to use the
repository as a local core with the Arduino IDE without the need to have the
full Zephyr build system installed and configured.

Pre-built files are generated only for the most recent commits in each branch.
If in doubt, checkout the current version of the branch you are interested in
before running the tool.

### Getting the tool

If you have installed the Arduino IDE and the Arduino core for Zephyr, you can
find the pre-built files in the `.arduino15/packages/arduino/tools/` folder in
your home directory. You can directly use the tool from there.

### Building manually

To build the tool, you need to have the Go programming language installed; make
sure you have the `go` command available in your PATH. Then, use the `go build`
command to build the tool for your platform.

To build the full set of binaries for all platforms, run the `package_tool.sh`
script in the parent directory with `../package_tool.sh`, or provide the path
to this directory as an argument.
