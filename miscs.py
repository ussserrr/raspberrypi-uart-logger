"""
Module with general global objects and support functions. It needs to be imported by
all other modules but not vice versa.
"""

import os, sys, time, serial, logging, subprocess
import RPi.GPIO as GPIO
from getpass import getuser



# Logger instance goes through whole program
log_formatter_string = '%(levelname)-8s [%(asctime)s] %(message)s'
formatter = logging.Formatter(log_formatter_string)
logging.basicConfig(format=log_formatter_string, level=logging.DEBUG)
logger = logging.getLogger('')

# Serial object is also global
ser = serial.Serial()
ser.port = '/dev/ttyAMA0'
ser.baudrate = 115200
ser.timeout = 60  # 1 min

# Drive descrption
possible_drives = ['sd{}1'.format(letter) for letter in 'abcdefghijklmnopqrstuvwxyz']
drive = '?'
whoami = getuser()
drive_mountpoint = '/media/{}'.format(whoami)
drive_name = 'LOGS'
log_filename = 'test.log'

# TODO: https://stackoverflow.com/questions/5137497/find-current-directory-and-files-directory
workdir = '/home/{}/Documents'.format(whoami)
reboots_cnt_filename = '{}/reboots_cnt.txt'.format(workdir)

# Return values of functions
CRITICAL_ERROR = 2
NEED_FORMAT = 1
STATUS_OK = 0

# LED
LED_GPIO = 18



def program_exit():
    """
    Correct closing of the program
    """
    print('program exit')
    logging.shutdown()
    ser.close()
    GPIO.output(LED_GPIO, False)



def ctrlc_handler(signal, frame):
    """
    Ctrl-C interrupt handler
    """
    logger.info("Program is terminated by user (Ctrl-C)")
    program_exit()
    sys.exit()



def sudo_reboot():
    """
    Single waypoint to reboot Linux. Before actually reboot it checks reboots counter in
    a special file and decides when restart system: now or at shedule instead. It allows to
    avoid continuous reboots when some serious error occured.
    """
    try:
        # If file exists and its size greater 0:
        if os.path.isfile(reboots_cnt_filename) and os.stat(reboots_cnt_filename).st_size>0:
            # TODO: Fix multiple file open
            reboots_cnt_file = open(reboots_cnt_filename)
            reboots_cnt = int(reboots_cnt_file.read()) + 1
            reboots_cnt_file.close()
            reboots_cnt_file = open(reboots_cnt_filename, 'w')
            reboots_cnt_file.write(str(reboots_cnt)+'\n')
            reboots_cnt_file.close()
            if reboots_cnt > 3:
                program_exit()
                subprocess.run(['sudo', 'shutdown', '-r', '+{}'.format(60)])  # 60 - 1h
                print('reboot has been sheduled')
                sys.exit()
        # Else create file and write '1' to it:
        else:
            reboots_cnt_file = open(reboots_cnt_filename, 'w')
            reboots_cnt_file.write('1\n')
            reboots_cnt_file.close()
    except Exception as e:
        print(e)

    program_exit()
    print('reboot now')
    subprocess.run(['sudo', 'reboot'])
    sys.exit()



def reset_reboots_cnt():
    """
    Reset reboots counter when there is a need in this
    """
    subprocess.run(['sudo', 'rm', reboots_cnt_filename])
