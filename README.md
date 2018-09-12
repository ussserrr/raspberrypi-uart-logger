# Raspberry Pi serial UART logger

## Overview
The application takes log data (with the special formatting, see "Log data format") from the serial port, parses it and writes to the USB flash drive. By default, the program uses the built-in UART port of the Raspberry Pi as the input but you can swap it to another device (external UART-USB converter for example (CH340, CP2102, etc.)) for sure. It was designed to be fully autonomous in terms of the external control of any kind and to deliver following functionality. The device as a whole sits as a plugin beside some primary device and plays the role of a "black box" recorder that logs all useful information from this main device. From time to time some *support man* takes out the flash drive and swaps it with another one (new empty drive). During any mode, Black Box is staying powered and worked, can diagnose itself and reboot if some error or drive replacement has occurred. Keep these reboots in mind if you plan to run another stuff in parallel.

The current version had been developed and tested only for Raspberry Pi 1 and 3 with official Raspbian system (more stability with Pi 3).

## Dependencies and requirements
 - Raspbian OS
 - Python3 and its standard library
 - `pyserial`
 - `termcolor` – for colorful printing of some useful debugging information to `stdout`. Can be safely removed from the app entirely
 - `RPi.GPIO` – used in Raspberry Pi systems to control the indication LED
 - Root permissions / administrative privileges

## Raspberry Pi UART
The Logger uses primary, full-functional `/dev/ttyAMA0` UART module so make sure that RX line GPIO15 (pin 10) is free. Further setup will be done by `manage.py` script during installation. Basically, it detaches console and Bluetooth from UART module via `raspi-config` utility and patches `/boot/config.txt` file with necessary parameters (reboot is required). You can preliminarily test your UART connection using any serial monitor program.

Solid electrical contact for both GND and RX is an important thing because otherwise there are real risk of bad data transmissions (some sort of garbage non-UTF8 symbols, etc.).

## Usage
  0. `sudo apt update && sudo apt upgrade && sudo apt install git`
  1. Clone the repo (you will also be needed in Internet connection during installation to satisfy dependencies)
  2. Edit settings in `manage.py`, `raspberrypi-uart-logger/miscs.py` according to your system:
    - UART parameters
    - log string format
    - timeouts (some default values are relatively small for debug purposes)
    - drive and log file names
    - working (installation) directory
    - optional LED, that indicates Logger ON/OFF status - if it doesn't light then logger app is shutdown'ed. So you can judge about the status of the system by briefly taking the look on the LED.
  3. Run
    ```sh
    cd raspberrypi-uart-logger/
    sudo python3 manage.py install
    ```
  4. You doesn't really have to prepare your USB drives because the app is able to remount/format improper drives (so do not store any important documents on drives intended for usage)
  5. Reboot the system. It will apply new preferences and also start the logger.

As it is was designed as a fully autonomous service, some intermediate layer is used to start up and turn off the program. **systemd** is used to run the application at every system start. Once systemd did his work, Bash script `startup_script.sh` will be going on. His job is basically to run the Python with the main `.py`-file and to detect incidents of some kind of unpredicted behavior. If the Python is crashed, the script will trigger the system reboot, so it works as an additional safety wrapper around the main app.

Alternative, you can test the app in "interactive" mode first. Disable the daemon (`sudo systemctl disable logger.service`) and place `/bin/bash /opt/raspberrypi-uart-logger/startup_script.sh` in the end of your `~/.bashrc`. So now, every time you log in into shell (during startup or manually) you will see entire logger output including service and log messages.

## Log data format
There are 5 levels of warning messages available. You can, of course, specify any format of the log string but default considerations are:
 - **D** – debug
 - **I** – info
 - **W** – warning
 - **E** – error
 - **C** – critical (error)

`[PREFIX LETTER] [MESSAGE] \r`

These prefix letters you should put at the start of your message and separate with a space from an actual payload. Output string will contain a type of the message, time & date and then actual payload:
```plain
DEBUG    [2018-08-24 03:50:00,844] Debug message from UART received
INFO     [2018-08-24 03:50:00,844] It's OK!
WARNING  [2018-08-24 03:50:00,845] Something happened
ERROR    [2018-08-24 03:50:00,845] You really need to repair this
CRITICAL [2018-08-24 03:50:00,845] PAN!C
```

There are also 2 service messages:
 - `is_present`: send this every `serial.Serial.timeout` seconds to notify the logger that your UART device is alive if there are no other messages to deliver. If it is not present for some time (see `no_ping_counter`) the logger will reboot itself. You, of course, can send any data over UART to reset the timeout but such message would not be recognized and be written to the USB drive with the `WARNING` prefix
 - `end`: this message terminates the logger program in a normal way (LED is turning off)

Always end every message with the CR `\r` symbol to notify the system about it.

## USB drive replacement
Assume the system is working in normal mode and some man unplug the flash drive. During the closest logging event the app will detect that no drive is present (that why the custom `logging.FileHandler` class is used for) and will go in the search mode to wait for a new drive. After successful detection the Raspberry will reboot itself and the program starts over. Such approach is a little bit clumsy but in the same time simpler. You can implement a non-reboot mode as well to improve the logger. Please avoid situations when more than one drive is plugged to the Raspberry simultaneously as it leads to an undefined behavior.

## Example UART device usage
Find STM32-F0 example (in C) of how to use this logger in your embedded app in `client-usage-example` folder. Sample library is also available.

## Project structure
Main files:
 - `/raspberrypi-uart-logger` - core app, will be copied in your system
 - `/manage.py` - installation/deinstallation utility. Keep it to manage your set-up in the future
 - `/logger.service` - description of systemd service, is used for autostart/start/stop functionality
 - `/client-usage-example` - sample C library and usage example. Runs on STM32 and continuously sends log messages via UART (115200, 8N1)

## Notes
Due to the specific purpose of the app, `logging` module is used as the main feature and not as an accessory one. So for actual indication of any debug information to `stdout` `print()`s and `cprint()`s statements are used. So in production final version, you can remove them from the app entirely to optimize performance. Of course, another instance of `logging.Logger` class with easy activation/deactivation method can be applied for this task but this wasn't implemented yet.

The program also creates and manages `workdir/reboots_cnt_filename` file that stores a number of reboots.

You can find the rough app scheme in `uml` folder (made with draw.io).

See TODOs for more information about current weaknesses and what would be great to do.
