#!/usr/bin/env python3
import sys
import socket
import json

class Message:
    _type = '' #o tipo deve ser: 'data' | 'update' | 'trace'
    _source = '' #endereço de origem da mensagem
    _destination = '' #endereço de destino da mensagem
    _payload = '' #resposta final de uma mensagem de trace 
    _distances = '' #dicionário de distâncias para o vizinho: { 'addr': dist , ...} 
    _hops = '' #vetor de endereços de roteadores pelo qual uma mensagem de trace passou: ['addr1','addr2', ...] 

class Router:
    _address = '' #endereço do roteador 
    _next = [] #endereços de roteadores que possuem o menor caminho para o roteador acima
    _dist = 0 #distância total até o roteador

class Routers: 
    _routers = [] #vetor de roteadores (class Router) para armazenar a lista de roteadores 
                  #e definir as funções para utiliza-lo
    def add(self, router):
        pass
    def update(self, router, next_addr, dist):
        pass
    def remove(self, router):
        pass

def send_update():
    #essa função deve iterar sobre os vizinho e enviar a tabela de para cada
    pass

def process_command(comm, args):
    # essa função deve verificar o comando recebido e executa-lo
    if( comm  ==  'add'):
        pass
    elif( comm == 'del'):
        pass
    elif (comm == 'trace'):
        pass
    elif (comm == 'quit'):
        pass

if __name__ == '__main__':
    ADDRESS = '127.0.0.1'
    PORT = 55151
    #por enquanto só testa uma conexão udp
    if(sys.argv[1] == 's'):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((ADDRESS, PORT))
            while True:
                data, addr_from = sock.recvfrom(1024)
                print(data.decode() +' | '+ str(addr_from))
    else:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.sendto('Hi!'.encode(),(ADDRESS,PORT))
            