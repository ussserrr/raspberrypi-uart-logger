"""
Module that generally controls operations with the drive. Almost all print() statements in this and another modules is
just for debug purposes because on the end device there will be no sense in them (but you can try to transfer them on
the logging platform if you sure that the drive is in a presence at the moment of a logging event).
"""

import os, shutil, subprocess, time, logging
from termcolor import cprint
from util import *



class CustomFileHandler(logging.FileHandler):
    """
    Subclass of logging.FileHandler with the overridden flush() method and a couple new properties. The main idea is to
    have and control a single "exit" of logging data into the output file.
    """

    def __init__(self, drive_arg, filename):
        # We need to know the current drive (/dev/sdXN) to check its presence
        self.drive = drive_arg
        # This flag is used to stop flushes when the drive is no more plugged and shutdown routines are performed
        self.active = True
        # Initialize a superclass in a usual way
        super(CustomFileHandler, self).__init__(filename)

    def flush(self):
        """
        Overridden method. It's automatically invoked on every logging event
        when FileHadler is connected to the current Logger.
        """
        if self.active:
            # Linux with its buffering mechanism doesn't immediately detect drive ejects so we need to perform manual
            # checks
            if not os.path.exists(self.drive):
                print('Drive has been lost')
                self.active = False
                # Wait for a new drive and reboot to start logging again
                replace_drive(possible_drives)
                sudo_reboot()
            else:
                super(CustomFileHandler, self).flush()
                if self.stream:
                    os.fsync(self.stream)



def unmount_drive(drive):
    cprint('UNMOUNT THE DRIVE', 'red')
    rslt = subprocess.run(['sudo', 'umount', drive], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Suppress command output while there is no error
    if rslt.returncode != 0:
        print(rslt.stderr.decode('utf-8'))



def mount_drive(drive, drive_mountpoint, drive_name):
    cprint('MOUNT THE DRIVE', 'red')
    # Make a directory for a drive to mount
    try:
        os.mkdir(os.path.join(drive_mountpoint, drive_name))
    except:
        pass
    rslt = subprocess.run(['sudo', 'mount', '-t', 'vfat', '-ouser,umask=0000', drive,
                           '{}/{}'.format(drive_mountpoint, drive_name)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Suppress command output while there is no error
    if rslt.returncode != 0:
        print(rslt.stderr.decode('utf-8'))



def check_drive(possible_drives, drive_mountpoint, drive_name, log_filename):
    """
    Full check: drive existence/name, log file existence/name, ability to write, so on

    returns:
        result,drive
    """

    mount_tries_cnt = mount_tries
    while True:
        if mount_tries_cnt == 0:
            return NEED_FORMAT,drive
        time.sleep(check_drive_retry_time)

        lsblk = subprocess.run(['lsblk', '-o', 'name,mountpoint', '-n', '-l'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if lsblk.returncode == 0:
            lsblk_output = lsblk.stdout.decode('utf-8')
        else:
            print(lsblk.stderr.decode('utf-8'))
            return CRITICAL_ERROR,''

        # Search for one of sdX1
        drives_cnt = 0
        for drv in possible_drives:
            if drv in lsblk_output:
                drives_cnt += 1
                drive = '/dev/{}'.format(drv)
                print('{} is plugged'.format(drive))
        if drives_cnt == 0:
            print('No plugged drives')
            return CRITICAL_ERROR,''
        elif drives_cnt > 1:
            print("Multiple drives were found! Using the last one")

        # Define whether sdX1 is mounted or not
        if drive_mountpoint in lsblk_output:
            print('{} is mounted'.format(drive))
        else:
            print('drive {} is not mounted'.format(drive))
            mount_drive(drive, drive_mountpoint, drive_name)
            mount_tries_cnt -= 1
            continue

        # Whether mounted drive is 'nameN' drive or not
        if drive_name in lsblk_output:
            # If 'nameN' then remount drive
            if lsblk_output[lsblk_output.find(drive_name)+len(drive_name)].isdigit():
                print('The drive is {}n, remount...'.format(drive_name))
                unmount_drive(drive)
                mount_drive(drive, drive_mountpoint, drive_name)
                mount_tries_cnt -= 1
                continue
            else:
                print('{} drive is mounted'.format(drive_name))
                break
        else:
            print('The drive is not {}, format...'.format(drive_name))
            return NEED_FORMAT,drive


    # Look for an already existed logfile on the drive
    if os.path.exists('{}/{}/{}'.format(drive_mountpoint, drive_name, log_filename)):
        print('{} is here'.format(log_filename))
    else:
        print('No log file, format...')
        return NEED_FORMAT,drive

    # First check for a logfile corruption (trying to get file properties)
    stat_info = 0
    try:
        stat_info = os.stat('{}/{}/{}'.format(drive_mountpoint, drive_name, log_filename))
    except Exception as e:
        print(e, ', format...')
        return NEED_FORMAT,drive
    if stat_info == 0:
        print('Log file is incorrect, format...')
        return NEED_FORMAT,drive

    # Whether logfile is empty or not. If it is, then we can safely format the drive
    if stat_info.st_size > 0:
        print('Log file size: {} bytes'.format(stat_info.st_size))
    else:
        print('Log file is empty, format')
        return NEED_FORMAT,drive

    # Second check for logfile corruption (trying to open the file for writing)
    try:
        log = open('{}/{}/{}'.format(drive_mountpoint, drive_name, log_filename), 'r+')
        log.close()
    except Exception as e:
        print(e, ', format...')
        return NEED_FORMAT,drive
    else:
        print('Log file is correct')
        return STATUS_OK,drive



def replace_drive(possible_drives):
    """
    Detect a new drive.

    returns:
        status
    """

    cprint('WAIT FOR A NEW DRIVE', 'red')
    wait_for_drive_cnt = 0
    while True:
        time.sleep(wait_for_drive_time)
        for drv in possible_drives:
            if os.path.exists('/dev/{}'.format(drv)):
                drive = '/dev/{}'.format(drv)
                print("We've waited for a new drive {} for approximately {} seconds"
                      .format(drive, wait_for_drive_time + wait_for_drive_cnt * wait_for_drive_time))
                time.sleep(wait_for_drive_time)
                return STATUS_OK
        print('Drive was not found yet')
        wait_for_drive_cnt += 1
        if wait_for_drive_cnt == wait_for_drive_tries:
            print("Wait for a drive timeout has expired")
            return CRITICAL_ERROR



def format_drive(drive, drive_name):
    cprint('FORMAT IN FAT32', 'red')
    rslt = subprocess.run(['sudo', 'mkdosfs', '-F', '32', '-I', drive, '-n', drive_name],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if rslt.returncode != 0:
        print(rslt.stderr.decode('utf-8'))



def activate_drive_and_logger(possible_drives, drive_mountpoint, drive_name, logger, formatter, log_filename):
    """
    Wrapper for check_driver() function with an extended functionality. Important thing is that this function also
    creates and returns a new CustomFileHandler instance. The current guide is to let the caller decide what to do in
    different cases instead of performing reboots "on the spot".

    returns:
        result,logging_file_handler,drive
    """

    activation_tries_cnt = activation_tries
    while True:

        drive_check_rslt,drive = check_drive(possible_drives, drive_mountpoint, drive_name, log_filename)
        if drive_check_rslt == NEED_FORMAT:
            print('Drive is need to be formatted')
            unmount_drive(drive)
            format_drive(drive, drive_name)
            mount_drive(drive, drive_mountpoint, drive_name)
        elif drive_check_rslt == CRITICAL_ERROR:
            print('¯\_(ツ)_/¯ sudo reboot')
            return CRITICAL_ERROR,None,''
        elif drive_check_rslt == STATUS_OK:
            print("All checks are passed")

        # Try to perform a test log writing
        try:
            logging_file_handler = CustomFileHandler(drive, '{}/{}/{}'.format(drive_mountpoint, drive_name,
                                                                              log_filename))
            logging_file_handler.setLevel(logging.DEBUG)
            logging_file_handler.setFormatter(formatter)
            logger.addHandler(logging_file_handler)
            logger.info("SUCCESSFUL USB DRIVE {} ACTIVATION".format(drive))
            logging_file_handler.flush()
        except Exception as e:
            print(e)
            activation_tries_cnt -= 1
            if activation_tries_cnt == 0:
                print('¯\_(ツ)_/¯ sudo reboot')
                return CRITICAL_ERROR,None,''
            print("Can't logging on drive. Retry after {} seconds".format(activation_tries_time))
            time.sleep(activation_tries_time)
        else:
            print('Logging activation success')
            return STATUS_OK,logging_file_handler,drive
            break
