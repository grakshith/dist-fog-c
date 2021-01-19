import requests, json, sys
import time

def test():
    data = {
        "temperature": 27,
        "humidity": 40,
        "light_intensity": 0
    }
    dumped = json.dumps(data)
    fog_url = "http://localhost:8000/update"
    resp = requests.post(fog_url, data=dumped)
    print resp.text

if __name__ == '__main__':
    while True:
        try:
            test()
        except KeyboardInterrupt:
            sys.exit(0)
        else:
            time.sleep(15)
