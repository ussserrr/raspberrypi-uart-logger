#!/usr/bin/env python3

import argparse, os, shutil, tempfile, sys, subprocess


here = os.path.abspath(os.path.dirname(__file__))
package_name = 'raspberrypi-uart-logger'
service_name = 'logger.service'
mountpoint = '/mnt/LOGS'
installation_files = [ 'logger.py',
                       'miscs.py',
                       'startup_script.sh',
                       'usbdriveroutine.py' ]
dependencies = [ 'python3-termcolor',
                 'python3-serial',
                 'python3-rpi.gpio' ]


def check_files(path, given_files):
    if os.path.exists(path):
        current_files = os.listdir(path)
        files_intersection = list(set(current_files) & set(given_files))
        files_intersection.sort()
        given_files.sort()
        if files_intersection == given_files:
            return True
    return False


def replace_line(source_file_path, pattern, substring):
    fh, target_file_path = tempfile.mkstemp()
    with open(target_file_path, 'w') as target_file,\
         open(source_file_path, 'r') as source_file:
        for line in source_file:
            target_file.write(line.replace(pattern, substring))
    os.remove(source_file_path)
    shutil.move(target_file_path, source_file_path)



parser = argparse.ArgumentParser(
    description="Autonomous Python app that logging UART messages to USB drive. "
                "Please run this managing utility as root")

subparsers = parser.add_subparsers(dest='subcommand', title='subcommands',
    description='valid subcommands', help='modes of operation')

parser_install = subparsers.add_parser('install',
    help="Install dependencies, copy necessary files, register in the system. "
         "After installtion the program will be located in "
         "'/opt/raspberrypi-uart-logger' directory. Current installation will be "
         "overridden. Reboot is needed to take effects.")
parser_generate = subparsers.add_parser('uninstall',
    help="Remove all files, registrations. Note that all dependencies will still "
         "be there and some system configs will not be revert back")

args = parser.parse_args()


# check root permissions
if os.geteuid() != 0:
    sys.exit("Please run this managing utility as root")


# print help if no arguments were given
if not len(sys.argv) > 1:
    parser.print_help()
    sys.exit()

# main routine
else:
    if args.subcommand == 'install':
        print("Installation starts...")

        # check installation files to be present
        if not check_files(os.path.join(here, package_name), installation_files):
            print("Installation files not found")
            sys.exit("Please re-download the package")

        # enable /dev/ttyAMA0 for incoming UART connections
        print("Enable /dev/ttyAMA0 for incoming UART connections...")
        # no console on /dev/ttyAMA0, but keep UART functionality
        subprocess.run(['sudo', 'raspi-config', 'nonint', 'do_serial', '2'])
        # detach BT from /dev/ttyAMA0. Firstly, reset settings
        replace_line('/boot/config.txt', 'dtoverlay=pi3-miniuart-bt\n', '')
        replace_line('/boot/config.txt', 'dtoverlay=pi3-disable-bt\n', '')
        with open('/boot/config.txt', 'a') as config_txt:
            config_txt.write("dtoverlay=pi3-miniuart-bt\n")
            config_txt.write("dtoverlay=pi3-disable-bt\n")

        # install dependencies (bypassing pip)
        print("Install dependencies...")
        subprocess.run(['sudo', 'apt', 'install'] + dependencies)

        # copy files
        print("Copy files...")
        # remove already existed installation
        if os.path.exists('/opt/'+package_name):
            shutil.rmtree('/opt/'+package_name)
        if os.path.exists('/etc/systemd/system'+service_name):
            os.remove('/etc/systemd/system/'+service_name)
        shutil.copytree(str(os.path.join(here, package_name)), '/opt/'+package_name)
        shutil.copy(str(os.path.join(here, service_name)), '/etc/systemd/system')

        # create a mountpoint directory
        try:
            os.mkdir(mountpoint)
        except:
            pass

        print("Register the daemon via systemd...")
        # Always run the systemctl daemon-reload command after creating new unit
        # files or modifying existing unit files. Otherwise, the systemctl start
        # or systemctl enable commands could fail due to a mismatch between states
        # of systemd and actual service unit files on disk.
        #
        # (from RedHat documentation)
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
        # enable service in systemd
        subprocess.run(['sudo', 'systemctl', 'enable', service_name])

        print("\nInstallation completed. Please reboot now to apply changes in "
              "system and start the logger. You can control the logger via\n\n\t"
              "sudo systemctl start|stop|enable|disable logger.service\n\ncommands. "
              "The program is located in\n\n\t/opt/raspberrypi-uart-logger\n\n"
              "directory. To remove the app run\n\n\tsudo python3 manage.py "
              "uninstall\n\nso don't delete this folder.")


    elif args.subcommand == 'uninstall':
        print("Uninstallation starts...")

        subprocess.run(['sudo', 'systemctl', 'stop', 'logger.service'])
        subprocess.run(['sudo', 'systemctl', 'disable', 'logger.service'])

        shutil.rmtree('/opt/'+package_name, ignore_errors=True)
        print('rm', '/opt/'+package_name)

        shutil.rmtree(mountpoint, ignore_errors=True)
        print('rm', mountpoint)

        try:
            os.remove('/etc/systemd/system/'+service_name)
            print('rm', '/etc/systemd/system/'+service_name)
        except:
            pass

        subprocess.run(['sudo', 'systemctl', 'daemon-reload'])

        replace_line('/boot/config.txt', 'dtoverlay=pi3-miniuart-bt\n', '')
        replace_line('/boot/config.txt', 'dtoverlay=pi3-disable-bt\n', '')

        print("\nUninstallation completed. Note that all dependencies are still "
              "there and some system configs were have not been reverted back")
