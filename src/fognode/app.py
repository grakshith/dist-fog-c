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


client = docker.from_env()
redis_cli = redis.StrictRedis(host='localhost', port=6380, db=0)
redis_shared = redis.StrictRedis(host='192.168.1.100', port=6381, db=0)

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


@app.route('/servicedata', methods=['POST'])
def propagate_data():
    print request.form
    redis_cli.set(request.form['service_id'],request.form['service_data'])
    parent_node = getParentNode()
    request_uri = "http://{}:8080/servicedata/".format(parent_node)
    requests.post(request_uri,data = request.form)
    return "OK"

def getParentNode():
    #get parent from shared redis
    parent = redis_shared.get(str(request.host.split((':')[0])))
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


if __name__ == '__main__':
    register_fog_master()
    app.run(debug=True, host='0.0.0.0', port=8080)
