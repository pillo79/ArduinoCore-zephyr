#!/usr/bin/env bash

arduino_zephyr_rules () {
cat <<EOF
# Arduino Zephyr rules

# Arduino UNO Q
# Operating mode
SUBSYSTEM=="usb", ATTR{idVendor}=="2341", ATTR{idProduct}=="0078", MODE="0666"
# EDL mode
SUBSYSTEM=="usb", ATTR{idVendor}=="05c6", ATTR{idProduct}=="9008", MODE="0666"

EOF
}

OS="$(uname -s)"
case "$OS" in
Linux*)
  if [ "$EUID" -ne 0 ]; then
    if [ -e "${PWD}/post_install.sh" ]; then
      if command -v pkexec > /dev/null 2>&1; then
        echo "Requesting root privileges..."
        pkexec "${PWD}/post_install.sh"
      else
        echo
        echo "You might need to configure permissions for uploading."
        echo "To do so, run the following command from the terminal:"
        echo "sudo \"${PWD}/post_install.sh\""
        echo
        exit
      fi
    else
      # Script was executed from another path. It is assumed this will only occur when user is executing script directly.
      # So it is not necessary to provide the command line.
      echo "Please run as root"
    fi

    exit
  fi

  arduino_zephyr_rules > /etc/udev/rules.d/60-arduino-zephyr.rules

  # reload udev rules
  echo "Reload rules..."
  udevadm trigger
  udevadm control --reload-rules

  ;;
esac
