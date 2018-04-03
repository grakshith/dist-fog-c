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
import time
from datetime import timedelta
from celery.schedules import crontab

# docker config
client = docker.from_env()

# redis config
redis_cli = redis.StrictRedis(host='localhost', port=6380, db=0)
redis_shared = redis.StrictRedis(host='192.168.1.100', port=6381, db=0)

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
        'memory': memory
    }
    return jsonify(utilization)


@app.route('/register/fognode/', methods=['GET','POST'])
def register_node():
    node = request.remote_addr
    fognodes = json.loads(redis_cli.get('fognodes'))
    if node not in fognodes:
        print "New node - {} joining the topology!".format(node)
        fognodes.append(node)
        redis_cli.set('fognodes',json.dumps(fognodes))
        redis_shared.set(str(node),str(request.host.split(':')[0]))
    return json.dumps(fognodes)



@app.route('/register/service', methods=['POST'])
def register_service():
    print request.data
    # body = json.loads(request.data)
    # print body
    service_id = hashlib.md5(urandom(128)).hexdigest()[:6]
    redis_cli.set(service_id, request.data)
    return service_id


@app.route('/servicedata', methods=['POST'])
def propagate_data():
    print request.data
    form = json.loads(request.data)
    redis_cli.set(str(form['service_id']+"-service_data"),form['service_data'])
    parent_node = getParentNode()
    if parent_node is not None:
        request_uri = "http://{}:8080/servicedata/".format(parent_node)
        requests.post(request_uri, data=request.data)
    return "OK"


def getParentNode():
    #get parent from shared redis
    parent = redis_shared.get(str(request.host.split(':')[0]))
    return parent


def getChildren():
    children = redis_cli.get('fognodes')
    return children


@app.route('/deploy/<service_id>')
def deploy(service_id):
    dockerfile = redis_cli.get(service_id)
    print type(dockerfile)
    dockerfile = json.loads(dockerfile)['dockerfile']
    dockerfile = open(dockerfile, 'r')
    print "Building"
    a, b = client.images.build(fileobj=dockerfile)
    print a.id
    print client.containers.run(a)
    return "OK"


@app.route('/heartbeat')
def heartbeat():
    return "OK"


@celery.task(name="get_heartbeat_task")
def get_heartbeat():
    fognodes = json.loads(redis_cli.get('fognodes'))
    print "In heartbeat - {}".format([x for x in fognodes])
    for node in fognodes:
        request_uri = "http://{}:8080/heartbeat/".format(node)
        try:
            response = requests.get(request_uri)
        except:
            print "{} did not send heartbeat".format(node)
            fognodes.remove(node)
            redis_cli.set('fognodes', json.dumps(fognodes))
        else:
            print "{} - {}".format(node, response.text)


@celery.on_after_configure.connect
def tasks_start(sender, **kwargs):
    """Contains all the celery start points"""
    sender.add_periodic_task(5.0, get_heartbeat.s())

if __name__ == '__main__':
    fognodes = redis_cli.get('fognodes')
    if fognodes is None:
        redis_cli.set('fognodes', json.dumps([]))
    app.run(debug=True, host='0.0.0.0', port=8080)
