# Version for lxterminal (i.e. when we use DE on our Pi)
# lxterminal --geometry=225x60 --command='sudo /usr/bin/python3 /opt/raspberrypi-uart-logger/logger.py'

sudo /usr/bin/python3 /opt/raspberrypi-uart-logger/logger.py
result=$?

# LED OFF
LED_GPIO=18
echo $LED_GPIO > /sys/class/gpio/export
echo out > "/sys/class/gpio/gpio$LED_GPIO/direction"
echo 1 > "/sys/class/gpio/gpio$LED_GPIO/value"
echo $LED_GPIO > /sys/class/gpio/unexport

if [ $result -ne 0 ]; then
    sudo reboot
fi
