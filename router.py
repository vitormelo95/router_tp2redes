#!/usr/bin/env python3
import sys
import socket
import json
import random
from threading import *

PORT = 55151
MAX = 4096
EXIT = Event()

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
    def __init__(self, address, route_addr, dist):
        self._address = address
        self._routes = []
        self.add_route(route_addr,dist)
    
    def add_route(self, route_addr, dist):
        route = { 'addr' : route_addr , 'dist': dist, 'last_update': 0 }
        self._routes.append(route) 

    def update_route(self, route_addr, dist):
        find = False
        #atualiza rota para o roteador, se a rota não existir adiciona ela
        #o programa mantém todas as rotas conhecidas por mensagem de update
        for route in self._routes:
            if(route['addr'] == route_addr):
                route['dist'] = dist
                route['last_update'] = 0
                find = True
        if(not find):
            self.add_route(route_addr,dist)
        
    def remove_route(self,route_addr):
        #remove a rota que passa pelo endereço passado
        for route in self._routes:
            if(route['addr'] == route_addr):
                self._routes.remove(route)

    def exist_routes(self):
        if(len(self._routes) > 0):
            return True
        return False
    
    def is_neigh(self):
        #se o endereço do roteador for igual ao de um caminho o roteador é vizinho
        for route in self._routes:
            if(route['addr'] == self._address):
                return True
        return False

    def get_route_addr(self):
        #retorna o endereço do próximo roteador
        #se tiver mais de uma rota com a mesma distância é feito um sorteio 
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
        n = random.randint(0, len(routes)-1)
        return routes[n]
    
    def get_dist_dict(self, to_addr):
        #utilizada na formação do vetor de update 
        #verifica qual endereço estamos enviando a mensagem
        #retorna a menor distância conhecida que não passa por quem estamos enviando
        min_dist = -1
        first = True
        for route in self._routes:
            if(to_addr != route['addr']):
                if(first):
                    min_dist = route['dist']
                    first = False
                elif (min_dist > route['dist'] ):
                    min_dist = route['dist']
        if ( min_dist > 0 ):
            return { self._address : min_dist }
        return {}
    
    def get_dist(self):
        #pega a menor distância para o roteador
        min_dist = -1
        first = True
        for route in self._routes:
            if(first):
                min_dist = route['dist']
                first = False
            elif (min_dist > route['dist'] ):
                min_dist = route['dist']
        return min_dist
    
    def incr_last_update(self):
        #incrementa o last_update, se ele for maior que três remove a rota
        for route in self._routes:
            if(self._address != route['addr']):
                route['last_update'] += 1
                if(route['last_update'] > 3):
                    self._routes.remove(route)

class Routers: 
     #dicionário de roteadores {'addrs': Router, ...} para armazenar a lista de roteadores e rotas 
     #define as funções para utilizar a lista
    def __init__(self):
        self._routers = {}

    def add(self, router):
        self._routers.update({ router._address: router})

    def update(self, addr, route_addr, dist):
        #atualiza as rotas dos roteadores, se o roteador não for conhecido adiciona ele
        if( addr in self._routers):
            self._routers[addr].update_route(route_addr, dist)
        else:
            router = Router(addr,route_addr, dist)
            self.add(router)
        
    def remove(self, addr):
        #remove todas as rotas aprendidas pelo endereço deletado
        for router_addr,route in self._routers.items():
            route.remove_route(addr)
            
    def get_distances(self, to_addr):
        #monta o dicionário de distâncias para o roteador (to_addr)
        distances = {}
        for addr,router in self._routers.items():
            if(addr!= to_addr):
                distances.update(router.get_dist_dict(to_addr))
        return distances

    def get_router_route(self,dest_addr):
        #pega o próximo roteador para chegar em no roteador do endereço passado
        if( dest_addr in self._routers):
            return self._routers[dest_addr].get_route_addr()
        return ''
    
    def get_router_dist(self,dest_addr):
        #pega a distância para o roteador (dest_addr)
        if( dest_addr in self._routers):
            return self._routers[dest_addr].get_dist()

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)       

def send_message(message, addr):
    #envia a mensagem, addr é o endereço do próximo roteador
    if(addr == '' or addr == None ):
        print('no route found to: '+ message.destination)
        return
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        message_txt = message.toJSON()
        message_txt = message_txt.encode('ascii')
        print('>> SENDING: ' + str(message_txt), file=sys.stderr)
        sock.sendto(message_txt,(addr,PORT))

def send_updates(r, this_addr, PERIOD):
    #essa função itera sobre os roteadores conhecidos e monta uma mensagem de update para cada roteador vizinho
    if EXIT.is_set():
        sys.exit()
    for addr,router in r._routers.items():
        if(router.is_neigh()):
            distances = { this_addr : 0}#inicia o dicionário com o próprio endereço
            #atualiza o dicionário com as distâncias conhecidas
            distances.update(r.get_distances(addr))
            message = Message('update',this_addr, addr, distances = distances)   
            send_message(message, addr)
    t = Timer(PERIOD, send_updates, args = (r, ADDR, PERIOD)).start()

def incr_routes(r, PERIOD):
    #incrementa o campo last_update de todas as rotas conhecidas
    try:
        if EXIT.is_set():
            sys.exit()
        for addr,router in r._routers.items():
            router.incr_last_update()
    except Exception as e:
        print(str(e),file=sys.stderr)
    
    Timer(PERIOD, incr_routes, args = (r,PERIOD)).start()

def ask_trace(r, destination,this_addr):
    #cria uma mensagem de trace e envia
    message = Message('trace',this_addr, destination,hops = [this_addr])
    next_router = r.get_router_route(destination)
    send_message(message, next_router)

def resp_trace(r,this_addr, message):
    #se a mensagem de trace for para o roteador responde ela com uma mensagem de data
    message['hops'].append(this_addr)
    resp_message = Message('data',this_addr,message['source'], payload = message)
    next_router = r.get_router_route(resp_message.destination)
    send_message(resp_message, next_router)

def pass_trace(r,this_addr, message):
    #adiciona o endereço do roteador no hops e repassa a mensagem ao destino
    message = Message(message['type'],message['source'],message['destination'],hops = message['hops'])    
    message.hops.append(this_addr)
    next_router = r.get_router_route(message.destination)
    send_message(message, next_router)

def pass_message(r,message):
    #repassa uma mensagem recebida ao seu destino
    if(message['type'] == 'data'):
        message = Message(message['type'],message['source'],message['destination'],payload = message['payload'])
    else:
        message = Message(message['type'],message['source'],message['destination'],distances = message['distances'])  
    next_router = r.get_router_route(message.destination)
    send_message(message, next_router)

def update_routers(r, message, this_addr):
    #itera sobre o dicionário de distâncias recebido na mensagem e atualiza as rotas e distâncias
    try:
        distances = message['distances']
        source_addr = message['source']
        if( source_addr in r._routers and r._routers[source_addr].is_neigh() ): 
            #verifica se o roteador de origem da mensagem é vizinho para aceitar o update
            dist_source = r.get_router_dist(source_addr)
            for addr,dist in distances.items():
                if( addr != this_addr):
                    r.update(addr, message['source'], dist+dist_source)
    except Exception as e:
        print(str(e),file=sys.stderr)
    

def process_command(r, text, this_addr):
    # essa função verifica o comando recebido e executa-lo
    try:
        text = text.split()
        comm = text[0]
        if (comm  ==  'add'):
            router = Router(text[1],text[1],int(text[2]))
            r.add(router)
        elif (comm == 'del'):
            r.remove(text[1])
        elif (comm == 'trace'):
            ask_trace(r,text[1],this_addr)
        elif (comm == 'quit'):
            print(r.toJSON())
            print('Ending...')
            EXIT.set()
            sys.exit()
        elif (comm == 'print'):
            print(r.toJSON())
    except Exception as e:
        print(str(e),file=sys.stderr)
   

def process_message(r, message, this_addr):
    #verifica o tipo da mensagem recebida e chama uma função para trata-lá
    try:
        if(message['destination'] == this_addr ):
            if (message['type'] == 'data'):
                print( message['payload'])
            elif (message['type'] == 'update' ):
                update_routers(r,message, this_addr)
            elif (message['type'] == 'trace'):
                resp_trace(r, this_addr, message)
        elif (message['type'] == 'trace'):
            pass_trace(r,this_addr,message) 
        else:
            pass_message(r,message)
    except Exception as e:
        print(str(e),file=sys.stderr)
    

def read_file(r, file_name, this_addr):
    #ler os comandos de um arquivo
    with open(file_name, 'r') as f:
        lines = f.readlines()
        for line in lines:
            process_command(r, line, this_addr)


class read_commands(Thread):
    #essa classe executa em uma thread o recebimento de comandos dos usuários
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
    #essa classe executa em uma thread o recebimento de mensagens
    def __init__(self, r, ADDR, PORT):
        Thread.__init__(self)
        self.r = r
        self.addr = ADDR
        self.port = PORT
        self.start()
    
    def run(self):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(2)
            sock.bind((self.addr, self.port))
            while True:
                if EXIT.is_set():
                    sys.exit()
                try:
                    data, addr_from = sock.recvfrom(MAX)
                    data = data.decode()
                    print('<< RECEIVING: ' + str(data), file=sys.stderr)
                    #quando uma mensagem é recebida chama a função em outra thread para processa-la
                    Thread(target=process_message,args=(self.r,json.loads(data),self.addr)).start()
                except Exception as e:
                    print(str(e),file=sys.stderr)
                    
                

if __name__ == '__main__':
    if(len(sys.argv) < 3):
        print("Wrong initialization expected parameters <ADDR> <PERIOD>")
        sys.exit(-1)
    
    r = Routers()
    ADDR = ''
    PERIOD = ''
    if (sys.argv[1] == '--addr' ):
        ADDR = sys.argv[2]
        PERIOD = float(sys.argv[4])
        if(len(sys.argv) > 6):
            read_file(r, sys.argv[6],ADDR)
    else:
        ADDR = sys.argv[1]
        PERIOD = float(sys.argv[2])
        if(len(sys.argv) > 3):
            read_file(r, sys.argv[3],ADDR)

    
    sys.stderr = open('logs_'+ADDR, 'w')
    
    read_commands(r,ADDR)
    receive_messages(r,ADDR,PORT)
    Timer(PERIOD, send_updates, args = (r, ADDR,PERIOD)).start()
    Timer(PERIOD, incr_routes, args = (r,PERIOD)).start()
 