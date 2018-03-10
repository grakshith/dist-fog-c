import numpy as np
import cv2
import time
import requests


bytes = ''
stream = requests.get('http://192.168.1.1:8080', stream=True)
i=0
while True:
    i+=1
    bytes+=stream.raw.read(1024)
    a=bytes.find('\xff\xd8')
    b=bytes.find('\xff\xd9')
    if a!=-1 and b!=-1:
        jpg = bytes[a:b+2]
        bytes = bytes[b+2:]
        img = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
        cv2.imwrite('capture-{}.jpg'.format(i), img)

