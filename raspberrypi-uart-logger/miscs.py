"""
Module with general global objects and support functions. It needs to be
imported by all other modules but not vice versa.
"""

import os, sys, serial, logging, subprocess
import RPi.GPIO as GPIO



# Serial object is global
ser = serial.Serial()
ser.port = '/dev/ttyAMA0'
ser.baudrate = 115200

# To get a full period multiply (usart_reconnect_retry_time * usart_reconnect_tries)
usart_reconnect_retry_time = 60  # seconds
usart_reconnect_tries = 1

# To get a full period multiply (ser.timeout * no_ping_tries)
ser.timeout = 60  # seconds
no_ping_tries = 10

# Number of bytes that we consider as a too long message without an EOL symbol
# (so some error happened)
too_long_message = 1000
too_long_message_sleep = 1800  # seconds


# Drive descrption
possible_drives = ['sd{}1'.format(letter) for letter in
                   'abcdefghijklmnopqrstuvwxyz']
drive = '?'  # initial name
drive_mountpoint = '/mnt'
drive_name = 'LOGS'  # we detect (and format) drives with such name
log_filename = 'uartlog.txt'

# Used in check_drive() function to provide several tries to initialize the drive
mount_tries = 3
check_drive_retry_time = 5  # seconds

# Used in replace_drive() function
wait_for_drive_tries = 60
wait_for_drive_time = 5  # seconds

# Wrap around check_drive() function adds additional tries
activation_tries = 3
activation_tries_time = 10  # seconds


workdir = '/opt/raspberrypi-uart-logger'
reboots_cnt_filename = '{}/reboots_cnt.txt'.format(workdir)


# Return codes of functions
CRITICAL_ERROR = 2
NEED_FORMAT = 1
STATUS_OK = 0

# LED
LED_GPIO = 18


# Logger instance goes through the whole program
log_formatter_string = '%(levelname)-8s [%(asctime)s] %(message)s'
formatter = logging.Formatter(log_formatter_string)
logging.basicConfig(format=log_formatter_string, level=logging.DEBUG)
logger = logging.getLogger('')



def program_exit():
    """
    Correct close of the program
    """
    print('Program exit')
    logging.shutdown()
    ser.close()
    GPIO.output(LED_GPIO, False)



def ctrlc_handler(signal, frame):
    """
    Ctrl-C interrupt handler
    """
    logger.info("Program is terminated by a user (Ctrl-C)")
    program_exit()
    sys.exit()



def sudo_reboot():
    """
    Single waypoint to reboot Linux. Before actually reboot, it checks reboots
    counter in a special file and decides when to restart a system: now or at a
    shedule instead. It allows to avoid continuous reboots when some serious
    error had occured.
    """
    try:
        # If the file exists and its size greater than 0:
        if os.path.isfile(reboots_cnt_filename) and os.stat(reboots_cnt_filename).st_size > 0:

            # Read current value and increment it by 1
            with open(reboots_cnt_filename) as reboots_cnt_file:
                reboots_cnt = int(reboots_cnt_file.read()) + 1

            # Replace the old value by new
            with open(reboots_cnt_filename, 'w') as reboots_cnt_file:
                reboots_cnt_file.write(str(reboots_cnt)+'\n')

            if reboots_cnt > 3:
                program_exit()
                subprocess.run(['sudo', 'shutdown', '-r', '+{}'.format(60)])  # 60 - 1h
                print('reboot has been sheduled')
                sys.exit()

        # Else create the file and write '1' to it:
        else:
            with open(reboots_cnt_filename, 'w') as reboots_cnt_file:
                reboots_cnt_file.write('1\n')

    # Can't manipulate the file
    except Exception as e:
        print(e)

    program_exit()
    print('Reboot now')
    subprocess.run(['sudo', 'reboot'])
    sys.exit()



def reset_reboots_cnt():
    """
    Reset reboots counter when there is a need in this
    """
    try:
        os.remove(reboots_cnt_filename)
    except:
        pass
