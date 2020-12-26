#!/usr/bin/python
#--------------------------------------
#    ___  ___  _ ____
#   / _ \/ _ \(_) __/__  __ __
#  / , _/ ___/ /\ \/ _ \/ // /
# /_/|_/_/  /_/___/ .__/\_, /
#                /_/   /___/
#
#           Temperature Logger
#  Read data from a BMP280 sensor and
#  send to Thingspeak.com account.
#
# Author : Matt Hawkins
# Date   : 20/06/2015
#
# http://www.raspberrypi-spy.co.uk/
#
# Updated to work with python3 by 
# Sebastian Morkisch - 26.12.2020
#
#--------------------------------------


import smbus
import time
import os
import sys
import requests          # URL requests
import bme280            # Sensor library
import RPi.GPIO as GPIO  # GPIO library

################# Default Constants #################
# These can be changed if required
DEVICE        = 0x76 # Default device I2C address
SMBUSID       = 1    # Rev 2 Pi uses 1, Rev 1 uses 0
LEDGPIO       = 17   # GPIO for LED
SWITCHGPIO    = 22   # GPIO for switch
INTERVAL      = 5    # Delay between each reading (mins)
AUTOSHUTDOWN  = 1    # Set to 1 to shutdown on switch
THINGSPEAKKEY = 'XXXXXXXXXXXXXXXX'
THINGSPEAKURL = 'https://api.thingspeak.com/update'
#####################################################

def currentHumidity(bus):
  bus.write_byte(0x40, 0xF5)
  time.sleep(0.3)
  data_0 = bus.read_byte(0x40)
  data_1 = bus.read_byte(0x40)
  humidity = ((data_0 * 256 + data_1) * 125 / 65536.0) - 6
  return humidity

def switchCallback(channel):

  global AUTOSHUTDOWN

  # Called if switch is pressed
  if AUTOSHUTDOWN==1:
    os.system('/sbin/shutdown -h now')
  sys.exit(0)

def sendData(url,key,field1,field2,field3,temp,pres,humid):
  """
  Send event to internet site
  """

  values = {'api_key' : key,'field1' : temp,'field2' : pres, 'field3': humid}

  log = time.strftime("%d-%m-%Y,%H:%M:%S") + ","
  log = log + "{:.1f} C".format(temp) + ","
  log = log + "{:.2f} mBar".format(pres) + ","
  log = log + "{:.2f} rh".format(humid) + ","

  try:
    # Send data to Thingspeak
    response = requests.post(url, values)
    log = log + 'Update ' + str(response.status_code)
  except Exception as e:
      log2 = log + 'Error:' + str(e)
      print(log2)

def main():

  global DEVICE
  global SMBUSID
  global LEDGPIO
  global SWITCHGPIO
  global INTERVAL
  global AUTOSHUTDOWN
  global THINGSPEAKKEY
  global THINGSPEAKURL

  # Check if config file exists and overwrite
  # default constants with new values
  if os.path.isfile('templogger.cfg')==True:
    print("Found templogger.cfg")
    f = open('templogger.cfg','r')
    data = f.read().splitlines()
    f.close()
    if data[0]=='Temp Logger':
      print("Using templogger.cfg")
      DEVICE        = int(data[1],16)
      SMBUSID       = int(data[2])
      LEDGPIO       = int(data[3])
      SWITCHGPIO    = int(data[4])
      INTERVAL      = int(data[5])
      AUTOSHUTDOWN  = int(data[6])
      THINGSPEAKKEY = data[7]
      THINGSPEAKURL = data[8]

  # Setup GPIO
  GPIO.setmode(GPIO.BCM)
  GPIO.setwarnings(True)
  # LED on GPIO17
  GPIO.setup(LEDGPIO , GPIO.OUT)
  # Switch on GPIO22 as input pulled LOW by default
  GPIO.setup(SWITCHGPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  # Define what function to call when switch pressed
  GPIO.add_event_detect(SWITCHGPIO, GPIO.RISING, callback=switchCallback)
  bus = smbus.SMBus(SMBUSID)

  try:
    while True:
      GPIO.output(LEDGPIO, True)
      (temperature, pressure)= bme280.readBME280All()
      sendData(THINGSPEAKURL,THINGSPEAKKEY,'field1','field2','field3',temperature,pressure,currentHumidity(bus))

      # Toggle LED while we wait for next reading
      for i in range(0,INTERVAL*60):
        GPIO.output(LEDGPIO, not GPIO.input(LEDGPIO))
        time.sleep(1)
  except Exception as e:
    # Reset GPIO settings
    crash=["Error on line {}".format(sys.exc_info()[-1].tb_lineno),"\n",e]
    print(crash)
    timeX=str(time.time())
    with open("CRASH-"+timeX+".txt","w") as crashLog:
        for i in crash:
            i=str(i)
            crashLog.write(i)
    GPIO.cleanup()
    sys.exit(0)

if __name__=="__main__":
   main()
