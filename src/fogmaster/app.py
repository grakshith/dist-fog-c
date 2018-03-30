from flask import Flask
from flask import request
app = Flask(__name__)

# Imports
import psutil
from flask import jsonify
import redis
import json
from os import urandom
import hashlib
import docker
import requests
from celery import Celery
from celery.utils.log import get_task_logger

# docker config
client = docker.from_env()

# redis config
redis_cli = redis.StrictRedis(host='localhost', port=6380, db=0)

# Celery config
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6380/0'
app.config['CELERY_TIMEZONE'] = 'UTC'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
logger = get_task_logger(__name__)

fognodes = []


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/utilization')
def get_util():
    cpu_count = psutil.cpu_count()
    cpu_freq = {
        'current': psutil.cpu_freq().current,
        'max': psutil.cpu_freq().max,
        'min': psutil.cpu_freq().min
    }
    cpu_percent = psutil.cpu_percent()
    disk_util = {
        'total': psutil.disk_usage('/').total,
        'used': psutil.disk_usage('/').used,
        'free': psutil.disk_usage('/').free,
        'percent': psutil.disk_usage('/').percent
    }
    temperatures = psutil.sensors_temperatures()
    swap_mem = {
        'total': psutil.swap_memory().total,
        'used': psutil.swap_memory().used,
        'free': psutil.swap_memory().free,
        'percent': psutil.swap_memory().percent
    }
    memory = {
        'total': psutil.virtual_memory().total,
        'available': psutil.virtual_memory().available,
        'percent': psutil.virtual_memory().percent,
        'used': psutil.virtual_memory().used,
        'free': psutil.virtual_memory().free
    }
    utilization = {
        'cpu_count': cpu_count,
        'cpu_freq': cpu_freq,
        'cpu_percent': cpu_percent,
        'disk_util': disk_util,
        'temperatures': temperatures,
        'swap_memory': swap_mem,
        'memory': memory
    }
    return jsonify(utilization)


@app.route('/register/fognode/', methods=['GET','POST'])
def register_node():
    node = request.remote_addr
    if node not in fognodes:
        fognodes.append(node)
    return json.dumps(fognodes)



@app.route('/register/service', methods=['POST'])
def register_service():
    print request.data
    # body = json.loads(request.data)
    # print body
    service_id = hashlib.md5(urandom(128)).hexdigest()[:6]
    redis_cli.set(service_id, request.data)
    return service_id


@app.route('/deploy/<service_id>')
def deploy(service_id):
    dockerfile = redis_cli.get(service_id)
    print type(dockerfile)
    dockerfile = json.loads(dockerfile)['dockerfile']
    dockerfile = open(dockerfile, 'r')
    print "Building"
    a,b=client.images.build(fileobj=dockerfile)
    print a.id
    print client.containers.run(a)
    return "OK"


@app.route('/heartbeat')
def heartbeat():
    return "OK"

def get_heartbeat():
    for node in fognodes:
        request_uri = "http://{}:8080/heartbeat/".format(node)
        requests.get(request_uri)

@celery.task(name="test")
def celery_task():
    print "ASASD"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
    celery_task.delay()
