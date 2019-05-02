# from bcd import *

# print(int_to_bcd_bytes(0))
# print(bcd_to_int(int_to_bcd(0)))

import subprocess, datetime

now = datetime.datetime.today()

rslt = subprocess.run(['sudo', 'date', '-s',
    '"$(date \%Y-\%m-\%d) {hour}:{minute}:{second}"'
    .format(hour=now.hour, minute=now.minute, second=now.second)])
if rslt.returncode == 0:
    print("Time was set from UART")
else:
    print("Error occured when setting time from UART")

rslt = subprocess.run(['sudo', 'date', '-s',
    '"{year}-{month}-{day} $(date +\%H:\%M:\%S)"'
    .format(year=now.year, month=now.month, day=now.day)])
if rslt.returncode == 0:
    print("Date was set from UART")
else:
    print("Error occured when setting date from UART")
