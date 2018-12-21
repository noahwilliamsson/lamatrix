#!/usr/bin/python
#
# Watch board pin number 5 for level changes and initiate a power-off
# when this pin goes low.
#
from RPi import GPIO
from subprocess import call

# https://pinout.xyz/pinout/i2c
pin = 5  # a.k.a BCM 3 a.k.a SCL

GPIO.setmode(GPIO.BOARD)
GPIO.setup(pin, GPIO.IN)
GPIO.wait_for_edge(pin, GPIO.FALLING)
print('Board pin number 5 dropped to low, initiating poweroff')
call(["/bin/systemctl","poweroff","--force"])
