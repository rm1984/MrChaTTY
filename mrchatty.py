#!/usr/bin/env python3

import argparse
import asyncio
import platform
import select
import signal
import socket
import sys
import time
from json import dumps, loads
from optparse import OptionParser
from termcolor import colored, cprint

port = 31337
users = []

def logo():
    print(colored(' _____     _____ _       _____ _____ __ __ ',  'cyan'))
    print(colored('|     |___|     | |_ ___|_   _|_   _|  |  |',  'cyan'))
    print(colored('| | | |  _|   --|   | .\'| | |   | | |_   _|', 'cyan'))
    print(colored('|_|_|_|_| |_____|_|_|__,| |_|   |_|   |_|  ',  'cyan'))
    print(colored('Coded by: Riccardo Mollo', 'cyan'))
    print()

def signal_handler(signal, frame):
    if signal == 2: # SIGINT
        print()
        print('You pressed Ctrl+C! Goodbye!')
        print()
        sys.exit()

class Chat:
    def __init__(self, port, render_message, username):
        self.render_message = render_message
        self.username = username
        self.port = port

        try:
            self.sock_to_read = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_to_read.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_to_read.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock_to_read.bind(('0.0.0.0', port))
            self.sock_to_write = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_to_write.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception as e:
            raise ConnectionError('Unable to connect')

    def send_request(self, sock_to_write, action, data=None):
        object_to_send = {'action': action, 'data': data, 'username': self.username}
        sock_to_write.sendto(bytes(dumps(object_to_send), 'UTF-8'), ('255.255.255.255', self.port))

    def iterate(self):
        socket_list = [self.sock_to_read]
        ready_to_read, _, _ = select.select(socket_list, [], [], 0)

        for sock in ready_to_read:
            # incoming message from server
            if sock == self.sock_to_read:
                data = sock.recv(4096).decode('utf-8')
                if not data:
                    raise ConnectionAbortedError('Disconnected from chat server')
                else:
                    self.render_message(data)

    def send_message(self, message):
        self.send_request(self.sock_to_write, 'message', message)

class MrChaTTY:
    def __init__(self, port, username):
        self.chat = Chat(port, self.render_message, username)

    def iterate(self):
        self.chat.iterate()

        data = self.get_input()

        if data is not None:
            self.chat.send_message(data)

    @staticmethod
    def render_message(message):
        sys.stdout.write('\r')
        message = loads(message)
        sys.stdout.write('[{}] {}\n'.format(message['username'], message['data']))
#        sys.stdout.write('$ ')
        sys.stdout.flush()

    @staticmethod
    def get_input():
        stdin = [sys.stdin]
        ready_to_read, _, _ = select.select(stdin, [], [], 0)

        if len(ready_to_read) == 0:
            return None

        message = sys.stdin.readline()

        #sys.stdout.write('\x1b[1A\r# ')
        sys.stdout.flush()

        return message

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help = 'Username of your choice', required = True)
#    parser.add_argument('-k', '--key', help = 'Group-defined secret key', required = True)
    args = parser.parse_args()
    username = args.user
#    key = args.key

    host = platform.node()
    ip = socket.gethostbyname(host)

    logo()
    print('Username: ' + colored(username, attrs=['bold']))
    print('Local IP: ' + colored(ip, attrs=['bold']))
    print('----')

#    mrchatty = MrChaTTY(port, username + '@' + ip)
    mrchatty = MrChaTTY(port, colored(username, attrs=['bold']) + '@' + ip)

    while True:
        mrchatty.iterate()
