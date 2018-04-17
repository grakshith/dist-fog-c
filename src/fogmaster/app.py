from flask import Flask
from flask import request
app = Flask(__name__)

# Imports
import psutil
from flask import jsonify
import redis
import json
import os
from os import urandom
import hashlib
import docker
import requests
from celery import Celery
from celery.utils.log import get_task_logger
import time
from datetime import timedelta
from celery.schedules import crontab
from cStringIO import StringIO
from structures import *
from Queue import Queue
import heapq
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
    try:
        path='service-data/{}'.format(service_id)
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise
    # TODO: Store the dockerfile here
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
    build_and_deploy.delay(service_id)
    return "OK"


@celery.task(name="build_and_deploy")
def build_and_deploy(service_id):
    with open('service-data/{}/dockerfile'.format(service_id), 'r') as f:
        print "Building"
        a = client.images.build(fileobj=f)
        print a.id
        service_data = json.loads(redis_cli.get(service_id))
        service_data['docker_image_id'] = a.id
        redis_cli.set(service_id, json.dumps(service_data))
        print client.containers.run(a)


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


@celery.task(name="monitor_resource_utilization")
def monitor_resource_util():
    fognodes = json.loads(redis_cli.get('fognodes'))
    for node in fognodes:
        request_uri = "http://{}:8080/utilization".format(node)
        try:
            response = requests.get(request_uri)
        except:
            print "{} did not send heartbeat".format(node)
        else:
            util = json.loads(response.text)
            print util['cpu_percent']


@celery.on_after_configure.connect
def tasks_start(sender, **kwargs):
    """Contains all the celery start points"""
    sender.add_periodic_task(2.5, get_heartbeat.s())
    sender.add_periodic_task(5.0, monitor_resource_util.s())


def get_util_node(node):
    request_uri = "http://{}:8080/utilization".format(node)
    try:
        response = requests.get(request_uri)
    except:
        print "{} did not send utilization".format(node)
    else:
        util = json.loads(response.text)
    small_util = {}
    small_util['cpu_percent'] = util['cpu_percent']
    small_util['disk_util'] = util['disk_util']['percent']
    small_util['memory'] = util['memory']['percent']
    return small_util


@app.route('/provision/<service_id>')
def provision_resources(service_id):
    # fognodes = json.loads(redis_cli.get('fognodes'))
    requirements = {
        "cpu": 20,
        "memory": 50
    }
    utils = {
        "192.168.1.102": {
            "cpu_percent": 1.7,
            "disk_util": 500,
            "memory": 45,
            "memory_percentage":14,
            "containers": 2
        },
        "192.168.1.103": {
            "cpu_percent": 22.7,
            "disk_util": 500,
            "memory": 600,
            "memory_percentage":60,
            "containers": 3
        }
    }
    sorted_utils = sorted(utils.iteritems(),key=lambda (k,v): ((0.40*v['memory_percentage']/100+0.45*v['containers']/5+0.1*v['cpu_percent']/100),k))
    for node in sorted_utils:
        available_resources = node[1]
        if available_resources['memory'] >= requirements['memory'] and \
                available_resources['cpu_percent'] >= 100-requirements['cpu'] and \
                available_resources['containers']<5:
                return node[0]

    # for node in fognodes:
    #     utils[node] = get_util_node(node)


    return jsonify(utils)

root = Node(IP="192.168.1.100")
root.children=['192.168.1.102', '192.168.1.103']
nodes = 1
utils = {
        "192.168.1.102": {
            "cpu_percent": 1.7,
            "disk_util": 500,
            "memory": 45,
            "memory_percentage":14,
            "containers": 2
        },
        "192.168.1.103": {
            "cpu_percent": 22.7,
            "disk_util": 500,
            "memory": 600,
            "memory_percentage":60,
            "containers": 3
        },
        "192.168.1.104": {
            "cpu_percent": 30,
            "disk_util": 500,
            "memory": 400,
            "memory_percentage":40,
            "containers": 1
        },
        "192.168.1.105": {
            "cpu_percent": 50,
            "disk_util": 500,
            "memory": 600,
            "memory_percentage":60,
            "containers": 0
        }
    }
def build_topology():
    queue = Queue()
    queue.put(root)
    while(not queue.empty()):
        u = queue.get()
        uri = "http://{}:8080/get_children".format(u.IP)
        # get_util_node

        response = requests.get(uri)
        children = json.loads(response.text)
        u.children = children
        for child in children:
            child_node = Node(IP=child)
            queue.put(child_node)
            nodes += 1

# requests - structure
req1 = Request(service_id='12345', requirements={'cpu':20, 'memory':50})
req2 = Request(service_id='12346', requirements={'cpu':40, 'memory':120})
req3 = Request(service_id='12347', requirements={'cpu':45, 'memory':100})
req4 = Request(service_id='12348', requirements={'cpu':50, 'memory':50})
heap = []
requests = [req1, req2, req3, req4]
assigned_indices = []
allocated_nodes = []

def branch_and_bound_rp(requests):
    # build_topology()
    cost_matrix = {}
    # fognodes = json.loads(redis_cli.get('fognodes'))
    fognodes = ['192.168.1.102', '192.168.1.103', '192.168.1.104', '192.168.1.105']
    for node in fognodes:
        # TODO: get_utils
        cost_matrix[node]=[]
        for request in requests:
            node_utils = utils[node]
            reqs = request.requirements
            cost_matrix[node].append(2/5*(node_utils['containers'])+0.04*(node_utils['cpu_percent']+reqs['cpu']) + 0.01*(node_utils['memory_percentage']+reqs['memory']))



    print cost_matrix


def cal_min_promising_cost(cost_matrix, node, req_index, cost_incurred):
    selected = cost_matrix[node]
    cost = cost_incurred
    for nod in cost_matrix:
        costs = 
        if nod == node:
            continue
        if nod in allocated_nodes:
            continue
    



branch_and_bound_rp(requests)
exit(0)


if __name__ == '__main__':
    fognodes = redis_cli.get('fognodes')
    if fognodes is None:
        redis_cli.set('fognodes', json.dumps([]))
    app.run(debug=True, host='0.0.0.0', port=8080)
