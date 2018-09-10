#!/usr/bin/env python3

import argparse, os, sys, subprocess

parser = argparse.ArgumentParser(description="Autonomous Python app that logging UART messages to USB drive. Please run this managing utility as root")

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
    requirements_txt = 'requirements.txt'
    name = 'raspberrypi-uart-logger'
    service_name = 'logger.service'


    if args.subcommand == 'install':
        # add check for all files existence

        # install dependencies
        subprocess.run(['pip3', 'install', '-r', os.path.join(here, requirements_txt)])

        # copy files
        shutil.copytree(str(os.path.join(here, name)), '/opt/'+name)
        shutil.copy(str(os.path.join(here, service_name)), '/etc/systemd/system')

        # Always run the systemctl daemon-reload command after creating new unit
        # files or modifying existing unit files. Otherwise, the systemctl start
        # or systemctl enable commands could fail due to a mismatch between states
        # of systemd and actual service unit files on disk.
        #
        # (from RedHat documentation)
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
        # enable service in systemd
        subprocess.run(['sudo', 'systemctl', 'enable', service_name])


    elif args.subcommand == 'uninstall':
        subprocess.run(['sudo', 'systemctl', 'stop', 'logger.service'])
        subprocess.run(['sudo', 'systemctl', 'disable', 'logger.service'])
        shutil.rmtree('/opt/'+name)
        os.remove('/etc/systemd/system/'+service_name)
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
