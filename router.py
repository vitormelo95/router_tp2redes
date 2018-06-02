#!/usr/bin/env python3
import sys
import socket



if __name__ == '__main__':
    ADDRESS = '127.0.0.1'
    PORT = 5005
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
            