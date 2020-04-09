#!/usr/bin/env python3

# TODO:
# - colors in error messages
# - random colors for usernames
# - encryption for messages

import argparse
import asyncio
import base64
import datetime
import hashlib
import platform
import select
import signal
import socket
import sys
import time
from cryptography.fernet import Fernet
from json import dumps, loads
from optparse import OptionParser
from termcolor import colored, cprint

bind_addr = '0.0.0.0'
bind_port = 31337 # default UDP port
mcst_addr = '10.255.255.255'
mcst_mask = '255.255.255.255'

def logo():
    print(colored(' _____     _____ _       _____ _____ __ __ ',  'cyan'))
    print(colored('|     |___|     | |_ ___|_   _|_   _|  |  |',  'cyan'))
    print(colored('| | | |  _|   --|   | .\'| | |   | | |_   _|', 'cyan'))
    print(colored('|_|_|_|_| |_____|_|_|__,| |_|   |_|   |_|  ',  'cyan'))
    print(colored('Coded by: Riccardo Mollo', 'cyan'))
    print()

def exception_handler(exception_type, exception, traceback):
    print("%s: %s" % (exception_type.__name__, exception))

def signal_handler(signal, frame):
    if signal == 2: # Ctrl+C (SIGINT)
        print()
        print('You pressed Ctrl+C! Goodbye!')
        print()

        sys.exit()

def get_key_hash(key):
    key_md5 = hashlib.md5()
    key_md5.update(key.encode('utf-8'))
    b64_key_hash = base64.b64encode(key_md5.hexdigest().encode('ascii')).decode('ascii')

    return Fernet(b64_key_hash)

def encrypt_message(decrypted_message, key):
    return get_key_hash(key).encrypt(decrypted_message.encode('utf-8'))

def decrypt_message(encrypted_message, key):
    return get_key_hash(key).decrypt(encrypted_message).decode('utf-8')

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.connect((mcst_addr, 1))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()

    return ip

class Chat:
    def __init__(self, port, render_message, username, host):
        self.port = port
        self.render_message = render_message
        self.username = username
        self.host = host

        try:
            self.sock_to_read = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_to_read.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_to_read.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock_to_read.bind((bind_addr, port))
            self.sock_to_write = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_to_write.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except PermissionError as pe:
            raise ConnectionError(colored('Permission denied (binding failed for port ' + str(port) + '/UDP)', 'red', attrs = ['bold']))
        except Exception as e:
            raise ConnectionError(colored('Unable to connect.', 'red', attrs = ['bold']))

    def send_request(self, sock_to_write, action, data = None):
        object_to_send = {'action': action, 'data': data, 'username': self.username, 'host': self.host}
        sock_to_write.sendto(bytes(dumps(object_to_send), 'utf-8'), (mcst_mask, self.port))

    def iterate(self):
        socket_list = [self.sock_to_read]
        ready_to_read, _, _ = select.select(socket_list, [], [], 0)

        for sock in ready_to_read:
            if sock == self.sock_to_read:
                data = sock.recv(4096).decode('utf-8')

                if not data:
                    raise ConnectionAbortedError(colored('Connection aborted.', 'red', attrs = ['bold']))
                else:
                    self.render_message(data)

    def send_announcement(self, message):
        self.send_request(self.sock_to_write, 'announcement', message)

    def send_message(self, message):
        self.send_request(self.sock_to_write, 'message', message)

class MrChaTTY:
    def __init__(self, port, username, host):
        self.chat = Chat(port, self.render_message, username, host)
        self.chat.send_announcement('')

    def iterate(self):
        self.chat.iterate()

        data = self.get_input()

        if data is not None:
            if (len(data) == 0): # Ctrl+D
                print()
                print('You pressed Ctrl+D! Goodbye!')
                print()

                sys.exit()
            elif data[0] == '/':
                command = data[1:].rstrip()

                if (command == 'date'):
                    print(colored(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 'magenta'))
            else:
                self.chat.send_message(data)

    @staticmethod
    def render_message(message):
        sys.stdout.write('\r')

        message = loads(message)
        u = message['username']
        a = message['action']
        h = message['host']
        d = message['data']

        if (u != username): # print only if user is not myself
            if (a == 'announcement'):
                sys.stdout.write('{} {} {}\n'.format(colored(u, 'green', attrs = ['bold']), colored('joined the chat from', 'green'), colored(h, 'green', attrs = ['bold'])))
            else:
                sys.stdout.write('<{}> {}'.format(colored(u, attrs = ['bold']), d))

        sys.stdout.flush()

    @staticmethod
    def get_input():
        stdin = [sys.stdin]
        ready_to_read, _, _ = select.select(stdin, [], [], 0)

        if len(ready_to_read) == 0:
            return None

        message = sys.stdin.readline()

        sys.stdout.flush()

        return message

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help = 'Username of your choice', required = True)
#    parser.add_argument('-k', '--key', help = 'Group-defined secret key', required = True)
    parser.add_argument('-d', '--debug', help = 'Debug messages for errors and exceptions', action = 'store_false')
    args = parser.parse_args()
    username = args.user
#    key = args.key
    debug = args.debug

    if (debug):
        sys.tracebacklimit = 0
        sys.excepthook = exception_handler

    host = platform.node()
    ip = get_ip()

    logo()
    print('Username: ' + colored(username, attrs = ['bold']))
    print('Local IP: ' + colored(ip, attrs = ['bold']))
    print(colored('-------------------------------------------',  'yellow'))

    mrchatty = MrChaTTY(bind_port, username, ip)

    while True:
        mrchatty.iterate()
