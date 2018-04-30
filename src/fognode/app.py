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
from docker import APIClient
import requests
import zipfile
from celery import Celery
from celery.utils.log import get_task_logger
import os
import StringIO
import time

client = docker.from_env()
redis_cli = redis.StrictRedis(host='localhost', port=6380, db=0)
redis_shared = redis.StrictRedis(host='192.168.1.100', port=6381, db=0)
raw_cli = APIClient(base_url='unix://var/run/docker.sock')

# Celery config
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6380/0'
app.config['CELERY_TIMEZONE'] = 'UTC'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])

celery.conf.update(app.config)
logger = get_task_logger(__name__)
# app.config['CELERYBEAT_SCHEDULE'] = {
#     'get-heartbeat': {
#         'task': 'get_heartbeat_task',
#         'schedule': 5.0,
#     },
# }


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
        'memory': memory,
        'containers': len(client.containers.list())
    }
    return jsonify(utilization)


@app.route('/servicedata', methods=['POST'])
def propagate_data():
    print request.data
    form = json.loads(request.data)
    redis_cli.set(str(form['service_id']+"-service_data"), form['service_data'])
    parent_node = getParentNode(request)
    request_uri = "http://{}:8080/servicedata/".format(parent_node)
    # print request_uri
    requests.post(request_uri, data=request.data)
    return "OK"

def getParentNode(request):
    #get parent from shared redis
    parent = redis_shared.get('192.168.1.102')
    print parent
    return parent

def getChildren():
    #get parent from shared redis
    children = redis_cli.get('fognodes')
    return children

@app.route('/heartbeat/')
def heartbeat():
    return "OK"

def register_fog_master():
    requests.get("http://192.168.1.100:8080/register/fognode/")


@app.route('/build_trigger/<service_id>')
def trigger_build(service_id):
    get_service_data.delay(service_id)
    return "OK"

@celery.task(name="get_service_data")
def get_service_data(service_id):
    url = "http://192.168.1.100:8080/services/{}".format(service_id)
    req = requests.get(url, stream=True)
    try:
        path = 'service-data/{}'.format(service_id)
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise
    z = zipfile.ZipFile(StringIO.StringIO(req.content))
    z.extractall('service-data/{}'.format(service_id))
    build_and_deploy(service_id)


def build_and_deploy(service_id):
    service_data = redis_cli.get(service_id)
    if not service_data:
        command = "docker build -t rakshith/{} service-data/{}/".format(service_id, service_id)
        print "Building"
        os.system(command)
            # a = client.images.build(fileobj=f)
            # for line in raw_cli.build(fileobj=f, tag='rakshith/{}'.format(service_id), custom_context=True):
            #     print line
            # # service_data = {}
        service_data = 'rakshith/{}'.format(service_id)
        redis_cli.set(service_id, service_data)
    print "Time start"
    start = time.time()
    print client.containers.run(service_data)
    end = time.time()
    print "Time End - Total Time = {}".format(end-start)



if __name__ == '__main__':
    register_fog_master()
    app.run(debug=True, host='0.0.0.0', port=8080)
