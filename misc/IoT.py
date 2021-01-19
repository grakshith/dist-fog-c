import sys
import Adafruit_DHT
import RPi.GPIO as GPIO
import time
import requests
import json

GPIO.setmode(GPIO.BOARD)
GPIO.setup(7, GPIO.IN)
green=11
red=13
blue=15
GPIO.setup(green, GPIO.OUT)
GPIO.setup(red, GPIO.OUT)
GPIO.setup(blue, GPIO.OUT)

def get_data_and_update():
    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 2)

    light_intensity = ~GPIO.input(7)+2

    print humidity, temperature, light_intensity
    url = "https://api.thingspeak.com/update?api_key=IFIQUAPHODE2WXHN&field1={}&field2={}&field3={}".format(temperature, humidity, light_intensity)

    requests.get(url)
    data = {
        "temperature": temperature,
        "humidity": humidity,
        "light_intensity": light_intensity
    }
    dumped = json.dumps(data)
    fog_url = "http://localhost:8000/update"
    res = requests.post(url, data=dumped)
    res = float(res.text)
    print "Prediction = ",res
    if(res == 1.0):
        GPIO.output(red, 0)
        GPIO.output(blue, 0)
        GPIO.output(green, 1)
    else:
        GPIO.output(red, 1)
        GPIO.output(green,0)
        GPIO.output(blue,0)

if __name__ == '__main__':
    while True:
        try:
            get_data_and_update()
            time.sleep(15)
        except KeyboardInterrupt:
            GPIO.cleanup()
            sys.exit(0)            
