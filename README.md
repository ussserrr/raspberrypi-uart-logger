TODO: write about /dev/tty device and correct raspi-config settings
TODO: only one drive can be attached at a time (and other rules)

# Raspberry Pi serial UART logger

## Overview
The application takes log data (with the special formatting) from the serial port, parses it and writes to the USB flash drive. By default, the program uses the built-in UART port of the Raspberry Pi as the input but you can retransmit it to another device (external UART-USB converter for example) for sure. It was designed to be fully autonomous in terms of the external control of any kind and to deliver following functionality. The device as a whole sits as a plugin besides some primary device and plays the role of a "black box" that log all useful information from this main device. From time to time some support man takes the old full flash drive and swaps it with another one (new empty drive). During any mode, Black Box is staying powered and worked, can diagnose itself and reboot if some error or drive replacement has occurred. Keep these reboots in mind if you plan to run another stuff in parallel.

The current version had been developed and tested only for UNIX systems (Raspberry Pi 1 and 3 with official Raspbian, more stability with Pi 3).

## Dependencies and requirements
 - Python3 and its standard library
 - Linux-based system
 - `pyserial`
 - `termcolor` – for colorful printing of some useful debugging information to `stdout`
 - `RPi` – used in Raspberry Pi systems to control the indication LED
 - Root permissions / administrative privileges

## Usage
 1. Clone the repo to the one folder
 2. Edit settings in `miscs.py` and other sources according to your system:
  - UART parameters
  - log string format
  - timeouts (some default values are relatively small for debug purposes)
  - drive and log file names
  - working directory
  - LED
 3. Format your USB drive(s) and assign it `drive_name` name

As it is was designed as a fully autonomous service, some intermediate layer is used to start up and turn off the program. **systemd** is used to run the application at every system start. To register the program, place `logger.service` file to the `/etc/systemd/system` folder and enable the service: `sudo systemctl enable logger.service`. Once systemd did his work, Bash script `startup_script.sh` will be going on. His job is basically to run the Python with the main `.py`-file and to detect incidents of some kind of unpredicted behavior. If the Python is crashed, the script will trigger the system reboot, so it works as an additional safety wrapper around the main app.

Now reboot Raspberry in a non-DE mode to see both log messages and some debug information in your terminal. LED indicates that logger is now active – if it doesn't light then logger app is shutdown. So you can judge about the status of the system by briefly taking the look on the LED.

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

## Example UART device usage
Find STM32-F0 example of how to use this logger in your embedded app in `example` folder. Sample library is also available.

## Notes
Due to the specific purpose of the app, `logging` module is used as the main feature and not as an accessory one. So for actual indication of any debug information to `stdout` `print()`s and `cprint()`s statements are used. So in production final version, you can remove them from the app entirely to optimize performance. Of course, another instance of `logging.Logger` class with easy activation/deactivation method can be applied for this task but this wasn't implemented yet.

The program also creates and manages `workdir/reboots_cnt_filename` file that stores a number of reboots.

You can find the rough app scheme in `uml` folder (made with draw.io).

See TODOs for more information about current weaknesses and what would be great to do.
