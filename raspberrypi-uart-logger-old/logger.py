# TODO: check dependencies (termcolor) at start
# TODO: in production: remove all print and cprint statements
# TODO: respond on errors of subprocess.run()
# TODO: centralized timeouts and counters control

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
    Routine that perform several tries to connect to serial port (USART). Usually on Raspberry connection
    is established at first attempt because of permanently existed port. So this function just adds one more
    safety level and also ability to migrate code to another platform.

    returns: result,reconnect_counter
    """
    usart_reconnect_counter = 0
    while not ser.is_open:
        try:
            ser.open()
        except Exception as e:
            usart_reconnect_counter += 1
            if usart_reconnect_counter>=5:  # 540 - 1h30min
                return CRITICAL_ERROR,usart_reconnect_counter+1
            logger.error("{}. Reconnect after 10 seconds".format(e))
            time.sleep(10)
        else:
            logger.info("Host now listening to {} (established in {} tries)".format(ser.name, usart_reconnect_counter+1))

    return 0,usart_reconnect_counter+1



def main():
    """
    Main function is not an actual start point of the whole program because of routines in imported modules.
    """

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_GPIO, GPIO.OUT)
    GPIO.output(LED_GPIO, True)

    # Connect handler of Ctrl-C interrupt
    signal.signal(signal.SIGINT, ctrlc_handler)
    signal.signal(signal.SIGTERM, ctrlc_handler)

    # Many of such functions in program does not actually use all these arguments and return values as part of
    # isolation principle. Idea is to make it easier to upgrade code in future releases.
    activate_drive_and_logger_status,\
    logging_file_handler,\
    drive = activate_drive_and_logger(possible_drives, drive_mountpoint, drive_name, logger, formatter, log_filename)
    if activate_drive_and_logger_status == CRITICAL_ERROR:
        sudo_reboot()

    usart_connect_status,usart_reconnect_counter = usart_connect(logger, ser)
    if usart_connect_status == CRITICAL_ERROR:
        sudo_reboot()

    no_ping_counter = 0
    reset_reboots_cnt_flag = False

    # Read messages forever
    while True:

        # Read bytes from USART till we get whole message
        msg = ''; char = b'a';
        while True:
            try:
                char = ser.read(1)  # 1 byte
            # Rear or non-present exception on Raspberry
            except Exception as e:
                logger.error("{}. His last words was (raw): {}".format(e, '' if msg=='' else msg))
                msg = ''
            else:
                # ser.write(char)  # Send symbol back to see what we typing (for debugging)

                # read byte timeout expired
                if char == b'':
                    no_ping_counter += 1
                    if no_ping_counter>=10:  # 90 - 1h30min
                        sudo_reboot()
                    else:
                        pass

                    # Define whether disconnection has happened in "idle" mode (between two messages) or while transfer
                    if msg == '':
                        logger.error("Target is not present. New waiting timeout: {} seconds".format(ser.timeout))
                    else:
                        logger.error("Transmitting failed. His last words was (raw): {}. New waiting timeout: {} seconds"
                            .format('' if msg=='' else msg, ser.timeout))
                        msg = ''

                    # Go and wait again
                    continue

                # EOL symbol at the end of message or just alone?
                elif char == b'\r':
                    if msg == '':
                        logger.warning("Empty message {}".format(repr(char)))
                        continue
                    break
                else:
                    pass

                # Reset no_ping_counter if we get any symbol
                if no_ping_counter>0:
                    msg = ''
                    no_ping_counter = 0

                # Append symbol to message and catch decode exceptions. They usually appears because of transmit errors
                # (bad electrical contact for example).
                try:
                    msg = msg+char.decode('utf-8')
                except Exception as e:
                    logger.warning("{}".format(e))

                # Case of too long message without EOL symbol
                if len(msg)>1000:
                    logger.warning("Message is too long")
                    msg = ''
                    time.sleep(1800)  # 1800 - 30min
                    sudo_reboot()


        # Parse type of log message and store it
        if msg[0] == 'D':
            logger.debug(msg[2:])
        elif msg[0] == 'I':
            logger.info(msg[2:])
        elif msg[0] == 'W':
            logger.warning(msg[2:])
        elif msg[0] == 'E':
            logger.error(msg[2:])
        elif msg[0] == 'C':
            logger.critical(msg[2:])

        # Ping-like message transmitted for us by timer to be sure that target is alive
        elif msg == 'is_present':
            # We have dedicated resets counter in file. But we need to reset it sometimes, right?
            # We do it only once per program run at condition of successful transmit.
            if not reset_reboots_cnt_flag:
                subprocess.run('sudo shutdown -c', shell=True)
                reset_reboots_cnt()
                reset_reboots_cnt_flag = True
                print('reboot counter cleared')
        elif msg == 'end':
            logger.info("Program terminated by target")
            program_exit()
            sys.exit()

        # If message isn't of any recognizable type
        else:
            logger.warning("Undefined message: {}".format(repr(msg)))

        # Forced flush after every message for certainty
        logging_file_handler.flush()



"""
This construction allows to define different program environments and run them independentely.
For example, we can write test() which has similar but different functionality compared to
main() and run it instead of main().
"""
if __name__ == '__main__':
    main()
