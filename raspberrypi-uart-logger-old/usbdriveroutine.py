"""
Module that generally controls operations with the drive. Almost all print() statements in this and
another modules is just for debug purposes because at final target they will not have any sense
(but you can try to transfer them on logging platform if you sure that drive is in presence
at the moment of logging event).
"""

import os, subprocess, time, logging
from termcolor import cprint
from miscs import *



class CustomFileHandler(logging.FileHandler):
    """
    Subclass of logging.FileHandler with overridden flush() method and couple new properties.
    The main idea is to have and control the single way of logging data into the output file.
    """
    def __init__(self, drive, filename):
        # we need to know the current drive (/dev/sdX) to check its presence
        self.mydrive = drive
        # this flag is used to stop flushes when the drive is no more plugged and shutdown routines are performed
        self.active = True
        super(CustomFileHandler, self).__init__(filename)  # initialize a superclass in a usual way

    def flush(self):
        """
        Overridden method. It's automatically invoked on every logging event when
        FileHadler connected to current getLogger('').
        """
        if self.active:
            # Linux with its buffering mechanism doesn't immediately detect drive ejects
            # so we need to perform manual checks
            if not os.path.exists(self.mydrive):
                print('drive was lost')
                self.active = False
                replace_drive(possible_drives)  # wait for a new drive and reboot to start logging again
                sudo_reboot()
            else:
                super(CustomFileHandler, self).flush()
                if self.stream:
                    os.fsync(self.stream)



def unmount_drive(drive):
    cprint('UNMOUNT THE DRIVE', 'red')
    rslt = subprocess.run(['sudo', 'umount', drive], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if rslt.returncode != 0:
        print(rslt.stderr.decode('utf-8'))



def mount_drive(drive, drive_mountpoint, drive_name):
    cprint('MOUNT THE DRIVE', 'red')
    # re-make a directory for drive mount
    subprocess.run(['sudo', 'rm', '-rf', '{}/{}'.format(drive_mountpoint, drive_name)])
    subprocess.run(['sudo', 'mkdir', '{}/{}'.format(drive_mountpoint, drive_name)])
    rslt = subprocess.run(
        ['sudo', 'mount', '-t', 'vfat', '-ouser,umask=0000', drive, '{}/{}'.format(drive_mountpoint, drive_name)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if rslt.returncode != 0:
        print(rslt.stderr.decode('utf-8'))



def check_drive(possible_drives, drive_mountpoint, drive_name, log_filename):
    """
    Full check of drive (and its existence at all) on different levels.

    returns: result,drive
    """
    mount_tries = 3
    while True:
        time.sleep(5)
        if mount_tries == 0:
            return NEED_FORMAT,drive

        lsblk_rslt = subprocess.run(['lsblk', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if lsblk_rslt.returncode == 0:
            print("'lsblk' success")
            lsblk_output = lsblk_rslt.stdout.decode('utf-8')
        else:
            print(lsblk_rslt.stderr.decode('utf-8'))
            return CRITICAL_ERROR,''

        # Search for one of sdX1
        drives_cnt = 0
        for drv in possible_drives:
            if drv in lsblk_output:
                drives_cnt += 1
                drive = '/dev/{}'.format(drv)
                print('{} is plugged'.format(drive))
        if drives_cnt == 0:
            print('no plugged drives')
            return CRITICAL_ERROR,''

        # Define whether sdX1 is mounted or not
        if drive_mountpoint in lsblk_output:
            print('{} is mounted'.format(drive))
        else:
            print('drive {} is not mounted'.format(drive))
            mount_drive(drive, drive_mountpoint, drive_name)
            mount_tries -= 1
            continue

        # Whether mounted drive is LOGS drive or not
        if drive_name in lsblk_output:
            # If LOGSn then remount drive
            if lsblk_output[lsblk_output.find(drive_name)+len(drive_name)] in [str(x) for x in range(10)]:
                print('drive is {}n'.format(drive_name))
                unmount_drive(drive)
                mount_drive(drive, drive_mountpoint, drive_name)
                mount_tries -= 1
                continue
            else:
                print('{} drive is mounted'.format(drive_name))
                break
        else:
            print('drive is not {}'.format(drive_name))
            return NEED_FORMAT,drive


    # Look for existed logfile on the drive
    if os.path.exists('{}/{}/{}'.format(drive_mountpoint, drive_name, log_filename)):
        print('logfile is here')
    else:
        print('no logfile')
        return NEED_FORMAT,drive

    # First check for logfile corruption (try to get file properties)
    statinfo = 0
    try:
        statinfo = os.stat('{}/{}/{}'.format(drive_mountpoint, drive_name, log_filename))
    except Exception as e:
        print(e)
        return NEED_FORMAT,drive
    if statinfo == 0:
        print('logfile is incorrect')
        return NEED_FORMAT,drive

    # Whether logfile is empty or not. If it is then we can safely format the drive
    if statinfo.st_size > 0:
        print('logfile size: {} bytes'.format(statinfo.st_size))
    else:
        print('logfile is empty')
        return NEED_FORMAT,drive

    # Second check for logfile corruption (try to open file for writing)
    try:
        log = open('{}/{}/{}'.format(drive_mountpoint, drive_name, log_filename), 'r+')
        log.close()
    except Exception as e:
        print(e)
        return NEED_FORMAT,drive
    else:
        print('logfile is correct')
        return STATUS_OK,drive



def replace_drive(possible_drives):
    """
    Last version of this function (this) just waits for the appearance of a new drive.

    returns: status
    """
    cprint('WAIT FOR NEW DRIVE', 'red')
    wait_for_drive_cnt = 0
    while True:
        time.sleep(5)
        for drv in possible_drives:
            if os.path.exists('/dev/{}'.format(drv)):
                drive = '/dev/{}'.format(drv)
                print("we've waited for a new drive {} for approximately {} seconds"
                    .format(drive, 5+wait_for_drive_cnt*5))
                time.sleep(5)
                return STATUS_OK
        print('drive is not found yet')
        wait_for_drive_cnt += 1
        if wait_for_drive_cnt == 60:  # 60 - ~5min
            print("timeout expired")
            return CRITICAL_ERROR



def format_drive(drive, drive_name):
    cprint('FORMAT IN FAT32', 'red')
    rslt = subprocess.run(['sudo', 'mkdosfs', '-F', '32', '-I', drive, '-n', drive_name],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if rslt.returncode != 0:
        print(rslt.stderr.decode('utf-8'))



def activate_drive_and_logger(possible_drives, drive_mountpoint, drive_name, logger, formatter, log_filename):
    """
    Wrapper for check_driver() function with extended functionality. Important thing is that this function
    also creates and returns a new CustomFileHandler instance. The current guide is to let the caller decide
    what to do in different cases instead of performing reboots on the spot.

    returns: result,logging_file_handler,drive
    """
    activation_tries = 3
    while True:

        drive_check_rslt,drive = check_drive(possible_drives, drive_mountpoint, drive_name, log_filename)
        if drive_check_rslt == NEED_FORMAT:
            print('drive is needed to be formatted')
            unmount_drive(drive)
            format_drive(drive, drive_name)
            mount_drive(drive, drive_mountpoint, drive_name)
        elif drive_check_rslt == CRITICAL_ERROR:
            print('¯\_(ツ)_/¯ sudo reboot')
            return CRITICAL_ERROR,0,0
        elif drive_check_rslt == STATUS_OK:
            print('all checks are passed')

        # Try to perform a test log writing
        try:
            logging_file_handler = CustomFileHandler(drive,
                '{}/{}/{}'.format(drive_mountpoint, drive_name, log_filename))
            logging_file_handler.setLevel(logging.DEBUG)
            logging_file_handler.setFormatter(formatter)
            logger.addHandler(logging_file_handler)
            logger.info("SUCCESSFUL USB DRIVE {} ACTIVATION".format(drive))
            logging_file_handler.flush()
        except Exception as e:
            print(e)
            activation_tries -= 1
            if activation_tries == 0:
                print('¯\_(ツ)_/¯ sudo reboot')
                return CRITICAL_ERROR,0,0
            print("can't logging on drive. Retry after 10 seconds")
            time.sleep(10)
        else:
            print('logging activation success')
            return STATUS_OK,logging_file_handler,drive
            break
