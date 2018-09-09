from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
from os import path
import subprocess


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        # subprocess.run(['sudo', 'systemctl', 'enable', 'logger.service'])
        develop.run(self)

class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        # subprocess.run(['sudo', 'systemctl', 'enable', 'logger.service'])
        install.run(self)


setup(
    name="raspberrypi-uart-logger",
    version="0.1.0",
    author="Andrey Chufyrev",
    author_email="andrei4.2008@gmail.com",
    description="Autonomous Python app that logging UART messages to USB drive",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ussserrr/raspberrypi-uart-logger",
    packages=find_packages('raspberrypi-uart-logger'),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
    ],
    install_requires=['termcolor', 'pyserial'],
    data_files=[('/etc/systemd/system', ['logger.service'])],
    package_data={'raspberrypi-uart-logger': ['startup_script.sh']},
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    },
)


print("MESSAGE AFTER INSTALLATION")
