class Node(object):
    """Tree Nodes"""
    def __init__(self, **kwargs):
        self.children = kwargs.get('children') or None
        self.IP = kwargs.get('IP') or None
        self.containers = kwargs.get('containers') or None
        self.cpu = kwargs.get('cpu') or None
        self.ram = kwargs.get('ram') or None


class Request(object):
    def __init__(self, **kwargs):
        self.service_id = kwargs.get('service_id')
        self.assigned_node_IP = None
        self.requirements = kwargs.get('requirements')
