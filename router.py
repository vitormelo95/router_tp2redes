#!/usr/bin/env python3
import sys
import socket
import json
import random
from threading import *

PORT = 55151
MAX = 4096

class Message:
    type = '' #o tipo deve ser: 'data' | 'update' | 'trace'
    source = '' #endereço de origem da mensagem
    destination = '' #endereço de destino da mensagem
    payload = '' #resposta final de uma mensagem de trace 
    distances = '' #dicionário de distâncias para o vizinho: { 'addr': dist , ...} 
    hops = [] #vetor de endereços de roteadores pelo qual uma mensagem de trace passou: ['addr1','addr2', ...] 
    def __init__(self,type,source,destination, payload = None, distances = None, hops = None):
        self.type = type
        self.source = source
        self.destination = destination
        if( self.type == 'data'):
            self.payload = payload
        elif (self.type == 'update'):
            self.distances = distances
        elif (self.type == 'trace'):
            self.hops = hops
        else:
            raise Exception("Wrong mode of initialization: if type = 'data' should define payload, if update: distances, if trace: hops ")
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)


class Router:
     #endereço do roteador 
     #endereços de rotas para o roteador acima [ {addr:'1.1.1.1', dist: 10, last_update: 0 }, ...]  
    def __init__(self, address, route_addr, dist, learn_from):
        self._address = address
        self._routes = []
        self.add_route(route_addr,dist, learn_from)
    
    def add_route(self, route_addr, dist, learn_from):
        route = { 'addr' : route_addr , 'dist': dist, 'last_update': 0, 'learn_from': learn_from  }
        self._routes.append(route) 

    def update_route(self, route_addr, dist, learn_from):
        find = False
        for route in self._routes:
            if(route['addr'] == route_addr):
                route['dist'] = dist
                route['last_update'] = 0
                route['learn_from'] = learn_from
                find = True
        if(not find):
            self.add_route(route_addr,dist, learn_from)
        
    def remove_route(self,route_addr):
        for route in self._routes:
            if(route['addr'] == route_addr):
                self._routes.remove(route)

    def exist_routes(self):
        if(len(self._routes) > 0):
            return True
        return False
    
    def is_neigh(self):
        for route in self._routes:
            if(route['addr'] == self._address):
                return True
        return False

    def get_route_addr(self):
        min_dist = 0
        first = True
        routes = []
        for route in self._routes:
            if(first):
                min_dist = route['dist']
                routes.append(route['addr'])
                first = False
            else:
                if (min_dist > route['dist']):
                    min_dist = route['dist']
                    routes = [route['addr']]
                if (min_dist == route['dist']):
                    routes.append(route['addr'])
        print(routes)
        n = random.randint(0, len(routes)-1)
        return routes[n]
    
    def get_dist_dict(self, to_addr):
        min_dist = -1
        first = True
        for route in self._routes:
            if(to_addr != route['learn_from']):
                if(first):
                    min_dist = route['dist']
                elif (min_dist > route['dist'] ):
                    min_dist = route['dist']
        if ( min_dist > 0 ):
            return { self._address : min_dist }
        return {}
    
    def get_dist(self):
        min_dist = -1
        first = True
        for route in self._routes:
            if(first):
                min_dist = route['dist']
                first = False
            elif (min_dist > route['dist'] ):
                min_dist = route['dist']
        return min_dist

class Routers: 
     #vetor de roteadores (class Router) para armazenar a lista de roteadores 
     #e definir as funções para utiliza-lo
    def __init__(self):
        self._routers = []

    def add(self, router):
        self._routers.append(router)

    def update(self, addr, route_addr, dist):
        find = False
        for router in self._routers:
            if(router._address == addr):
                router.update_route(route_addr, dist, route_addr)
                find = True
        if( not find):
            router = Router(addr,route_addr,dist,route_addr)
            self.add(router)
        
    def remove(self, addr):
        for router in self._routers:
            if(router._address == addr):
                router.remove_route(addr)
                if(not router.exist_routes()):
                    self._routers.remove(router)
            
    def get_distances(self, to_addr):
        distances = {}
        for router in self._routers:
            if(router._address != to_addr):
                distances.update(router.get_dist_dict(to_addr))
        return distances

    def get_router_route(self,dest_addr):
        for router in self._routers:
            if (router._address == dest_addr):
                return router.get_route_addr()
        return ''
    
    def get_router_dist(self,dest_addr):
        for router in self._routers:
            if (router._address == dest_addr):
                return router.get_dist()
    
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)      


def send_message(message, addr):
    if(addr == '' or addr == None ): 
        print('no route found')
        return
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        message_txt = message.toJSON()
        message_txt = message_txt.encode('ascii')
        print(message_txt)
        sock.sendto(message_txt,(addr,PORT))

def send_updates(r, this_addr, PERIOD):
    #essa função deve iterar sobre os vizinhos e enviar a tabela de para cada
    for router in r._routers:
        if(router.is_neigh()):
            distances = { this_addr : 0}
            distances.update(r.get_distances(router._address))
            message = Message('update',this_addr, router._address, distances = distances)   
            send_message(message, router._address)
    t = Timer(PERIOD, send_updates, args = (r, ADDR, PERIOD)).start()

def ask_trace(r, destination,this_addr):
    message = Message('trace',this_addr, destination,hops = [this_addr])
    next_router = r.get_router_route(destination)
    send_message(message, next_router)

def resp_trace(r,this_addr, message):
    message['hops'].append(this_addr)
    resp_message = Message('data',this_addr,message['source'], payload = message)
    next_router = r.get_router_route(resp_message.destination)
    send_message(resp_message, next_router)

def pass_trace(r,this_addr, message):
    message = Message(message['type'],message['source'],message['destination'],hops = message['hops'])    
    message.hops.append(this_addr)
    next_router = r.get_router_route(message.destination)
    send_message(message, next_router)

def pass_message(r,message):
    if(message['type'] == 'data'):
        message = Message(message['type'],message['source'],message['destination'],payload = message['payload'])
    else:
        message = Message(message['type'],message['source'],message['destination'],distances = message['distances'])  
    next_router = r.get_router_route(message.destination)
    send_message(message, next_router)

def update_routers(r, message, this_addr):
    distances = message['distances']
    print(distances)
    dist_source = r.get_router_dist(message['source'])   
    for addr,dist in distances.items():
        if( addr != this_addr):
            r.update(addr, message['source'], dist+dist_source)

def process_command(r, text, this_addr):
    # essa função deve verificar o comando recebido e executa-lo
    text = text.split()
    comm = text[0]
    #print(text)
    if( comm  ==  'add'):
        router = Router(text[1],text[1],int(text[2]),text[1])
        r.add(router)
        print(r.toJSON())
    elif( comm == 'del'):
        r.remove(text[1])
    elif (comm == 'trace'):
        ask_trace(r,text[1],this_addr)
    elif (comm == 'quit'):
        print(r.toJSON())
        sys.exit()

def process_message(r, message, this_addr):
    print(message)
    if(message['destination'] == this_addr ):
        if (message['type'] == 'data'):
            print( message['payload'])
        elif (message['type'] == 'update' ):
            update_routers(r,message, this_addr)
            print('update')
            print(r.toJSON())
        elif (message['type'] == 'trace'):
            resp_trace(r, this_addr, message)
    elif (message['type'] == 'trace'):
        pass_trace(r,this_addr,message) #adicionar this_addr in hops
    else:
        pass_message(r,message)

def read_file(r, file_name, this_addr):
    with open(file_name, 'r') as f:
        lines = f.readlines()
        for line in lines:
            process_command(r, line, this_addr)


class read_commands(Thread):
    def __init__(self, r, this_addr):
        Thread.__init__(self)
        self.r = r
        self.this_addr = this_addr
        self.start()
    
    def run(self):
        while True:
            command = input()
            process_command(self.r,command,self.this_addr)
        
class receive_messages(Thread):
    def __init__(self, r, ADDR, PORT):
        Thread.__init__(self)
        self.r = r
        self.addr = ADDR
        self.port = PORT
        self.start()
    
    def run(self):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.addr, self.port))
            while True:
                data, addr_from = sock.recvfrom(MAX)
                data = data.decode()
                process_message(self.r,json.loads(data),self.addr)

if __name__ == '__main__':
    if(len(sys.argv) < 3):
        print("Wrong initialization expected parameters <ADDR> <PERIOD>")
        sys.exit(-1)
    
    ADDR = sys.argv[1]
    sys.stdout = open('output_'+ADDR, 'w')
    sys.stderr = open('error_'+ADDR, 'w')
    PERIOD = float(sys.argv[2])

    r = Routers()
    
    if(len(sys.argv) > 3):
        read_file(r, sys.argv[3],ADDR)

    read_commands(r,ADDR)

    receive_messages(r,ADDR,PORT)

    t = Timer(PERIOD, send_updates, args = (r, ADDR,PERIOD)).start()

 