# TODO: in production: remove all print and cprint statements
# TODO: respond on errors of subprocess.run() (use subprocess.run(..., check=True))
# TODO: USB drive overflow/fat32 maximal file size (4 Gb) exceed

"""
Main program module.
"""

import sys, time, signal, serial, logging, subprocess
import RPi.GPIO as GPIO
from functools import partial

from miscs import *
from usbdriveroutine import *



def usart_connect(logger, ser):
    """
    Routine that perform several tries to connect to the serial port (UART).
    Usually on Raspberry the connection is established at the first attempt
    because of the permanently existing port. So this function just adds one
    more safety level and an ability to migrate the code to another platform.

    returns:
        result,reconnect_counter
    """
    usart_reconnect_counter = 0
    while not ser.is_open:
        try:
            ser.open()
        except Exception as e:
            usart_reconnect_counter += 1
            if usart_reconnect_counter > usart_reconnect_tries:
                return CRITICAL_ERROR,usart_reconnect_counter+1
            logger.error("{}. Reconnect after {} seconds, {} tries left".format(
                            e,
                            usart_reconnect_retry_time,
                            usart_reconnect_tries - usart_reconnect_counter
                         ))
            time.sleep(usart_reconnect_retry_time)
        else:
            logger.info("Host now listening to {} (established in {} tries)"
                        .format(ser.name, usart_reconnect_counter+1))

    return 0,usart_reconnect_counter+1



def main():
    """
    Main function is not an actual start point of the whole program because of
    routines in imported modules.
    """

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_GPIO, GPIO.OUT)
    GPIO.output(LED_GPIO, True)

    # Connect handler of Ctrl-C interrupt
    signal.signal(signal.SIGINT, ctrlc_handler)
    signal.signal(signal.SIGTERM, ctrlc_handler)

    # Many of such functions in the program does not actually use all these
    # arguments and return values as part of the isolation principle. The idea
    # is to make it easier to upgrade the code in future releases.
    activate_drive_and_logger_status,\
    logging_file_handler,\
    drive = activate_drive_and_logger(
        possible_drives,
        drive_mountpoint,
        drive_name,
        logger,
        formatter,
        log_filename
    )
    if activate_drive_and_logger_status == CRITICAL_ERROR:
        sudo_reboot()

    usart_connect_status, usart_reconnect_counter = usart_connect(logger, ser)
    if usart_connect_status == CRITICAL_ERROR:
        sudo_reboot()

    no_ping_counter = 0
    reset_reboots_cnt_flag = False

    # Read messages forever in a loop
    while True:

        # Read bytes from USART till we get whole message
        msg = ''; char = b'a';
        while True:
            try:
                char = ser.read(1)  # 1 byte
            # Rear or non-present exception on Raspberry
            except Exception as e:
                logger.error("{}. His last words were (raw): {}"
                             .format(e, "''" if msg=='' else msg))
                msg = ''
            else:
                # Send symbol back to see what we typing (for debugging)
                # ser.write(char)

                # read byte timeout expired
                if char == b'':
                    no_ping_counter += 1
                    if no_ping_counter > no_ping_tries:
                        sudo_reboot()

                    # Define whether disconnection has happened in "idle" mode
                    # (between two messages) or while transfer
                    if msg == '':
                        logger.error(
                            "Target is not present. Wait for {} seconds, {} tries left"
                            .format(
                                ser.timeout,
                                no_ping_tries - no_ping_counter
                            ))
                    else:
                        logger.error(
                            "Transmission failed. His last words were (raw): {}. "
                            "New waiting timeout: {} seconds"
                            .format(
                                "''" if msg=='' else msg,
                                ser.timeout
                            ))
                        msg = ''

                    # Go and wait again
                    continue

                # EOL symbol at the end of message or just alone?
                elif char == b'\r':
                    if msg == '':
                        logger.warning("Empty message: '{}'".format(repr(char)))
                        continue
                    break

                # Reset no_ping_counter if we get any symbol
                if no_ping_counter > 0:
                    msg = ''
                    no_ping_counter = 0

                # Append a symbol to the message and catch decode exceptions.
                # They usually appears due to transmit errors (bad electrical
                # contact, for example).
                try:
                    msg = msg + char.decode('utf-8')
                except Exception as e:
                    logger.warning("{}".format(e))

                # Case of the too long message without EOL symbol
                if len(msg) > too_long_message:
                    logger.warning("Message is too long")
                    msg = ''
                    time.sleep(too_long_message_sleep)
                    sudo_reboot()


        # Parse type of a log message and store it
        type = msg[0]; msg_for_log = msg[2:]
        if type == 'D':
            logger.debug(msg_for_log)
        elif type == 'I':
            logger.info(msg_for_log)
        elif type == 'W':
            logger.warning(msg_for_log)
        elif type == 'E':
            logger.error(msg_for_log)
        elif type == 'C':
            logger.critical(msg_for_log)

        # Ping-like message transmitted for us by the target to be sure that
        # it is alive
        elif msg == 'is_present':
            # We have dedicated resets counter in file. But we need to reset it
            # sometimes, right? We do it only once per program run, at condition
            # of a successful transmission.
            if not reset_reboots_cnt_flag:
                # Cancel reboot, if there was planned one
                subprocess.run(['sudo', 'shutdown', '-c'])
                reset_reboots_cnt()
                reset_reboots_cnt_flag = True
                print('Reboots counter was cleared')

        elif msg == 'end':
            logger.info("Program terminated by the target")
            program_exit()
            sys.exit()

        # If a message isn't of any recognizable type
        else:
            logger.warning("Undefined message: {}".format(repr(msg)))

        # Force flush after every message for certainty
        logging_file_handler.flush()



"""
This construction allows to have separate program environments and runs them
independentely. For example, we can write test() which deliver similar but
different functionality compared to main(), and run it instead of main().
"""
if __name__ == '__main__':
    main()
