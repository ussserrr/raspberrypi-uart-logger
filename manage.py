#!/usr/bin/env python3

import argparse, os, sys, subprocess

parser = argparse.ArgumentParser(description="Autonomous Python app that logging UART messages to USB drive. "\
                                             "Please run this managing utility as root. After installtion the "\
                                             "program will be located in '/opt/raspberrypi-uart-logger' directory")

subparsers = parser.add_subparsers(dest='subcommand', title='subcommands',
                                   description='valid subcommands', help='modes of operation')

parser_install = subparsers.add_parser('install', help='install dependencies, copy necessary files, register in the system')
# parser_new.add_argument('-d', '--directory', dest='path', help='path to project', required=True)
# parser_new.add_argument('-b', '--board', dest='board', help='pio name of the board', required=True)
# parser_new.add_argument('--start-editor', dest='editor', help="use specidied editor to open pio project",
#                         choices=['atom', 'vscode'], required=False)

parser_generate = subparsers.add_parser('uninstall', help='remove all files, registrations')
# parser_generate.add_argument('-d', '--directory', dest='path', help='path to project', required=True)

args = parser.parse_args()


if os.geteuid() != 0:
    sys.exit("Please run this managing utility as root")


# print help if no arguments were given
if not len(sys.argv) > 1:
    parser.print_help()
    sys.exit()

# main routine
else:
    import shutil

    here = os.path.abspath(os.path.dirname(__file__))
    name = 'raspberrypi-uart-logger'
    service_name = 'logger.service'
    mountpoint = '/mnt'
    drive_name = 'LOGS'


    if args.subcommand == 'install':
        print("Installation starts...")
        # TODO: add check for all files existence

        # enable /dev/ttyAMA0 for incoming UART connections
        print("Enable /dev/ttyAMA0 for incoming UART connections...")
        subprocess.run(['sudo', 'raspi-config', 'nonint', 'do_serial', '2'])

        # install dependencies (bypassing pip)
        print("Install dependencies...")
        subprocess.run(['sudo', 'apt', 'install', 'python3-termcolor', 'python3-serial', 'python3-rpi.gpio'])

        # copy files
        print("Copy files...")
        shutil.copytree(str(os.path.join(here, name)), '/opt/'+name)
        shutil.copy(str(os.path.join(here, service_name)), '/etc/systemd/system')

        # create mountpoint directory
        os.mkdir(os.path.join(mountpoint, drive_name))

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

        print("Installation completed. Please reboot now to apply changes in system "\
              "and start the logger. You can control the logger via 'sudo systemctl "\
              "start|stop|enable|disable logger.service' commands. The program is "\
              "located in '/opt/raspberrypi-uart-logger' directory. To remove the app "\
              "run 'sudo python3 manage.py uninstall' so don't delete this folder.")


    elif args.subcommand == 'uninstall':
        print("Uninstallation starts...")

        subprocess.run(['sudo', 'systemctl', 'stop', 'logger.service'])
        subprocess.run(['sudo', 'systemctl', 'disable', 'logger.service'])

        try:
            shutil.rmtree('/opt/'+name)
            print('rm', '/opt/'+name)
        except:
            pass

        try:
            shutil.rmtree(mountpoint+'/'+drive_name)
            print('rm', mountpoint+'/'+drive_name)
        except:
            pass

        try:
            os.remove('/etc/systemd/system/'+service_name)
            print('rm', '/etc/systemd/system/'+service_name)
        except:
            pass

        subprocess.run(['sudo', 'systemctl', 'daemon-reload'])

        print("Uninstallation completed. Note, that all dependencies are still there.")
