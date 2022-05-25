#!/usr/bin/env python3

# TODO:
# - colors in error messages
# - random colors for usernames
# - encryption for messages
# - handle users with same username

import argparse
import datetime
import platform
import select
import signal
import socket
import sys
from json import dumps, loads
from termcolor import colored
import cryptocode

BIND_ADDR = '0.0.0.0' # listen on any address
BIND_PORT = 31337     # default UDP port
MCST_ADDR = '10.255.255.255'
MCST_MASK = '255.255.255.255'

def logo():
    print(colored(' _____     _____ _       _____ _____ __ __ ',  'cyan'))
    print(colored('|     |___|     | |_ ___|_   _|_   _|  |  |',  'cyan'))
    print(colored('| | | |  _|   --|   | .\'| | |   | | |_   _|', 'cyan'))
    print(colored('|_|_|_|_| |_____|_|_|__,| |_|   |_|   |_|  ',  'cyan'))
    print(colored('                Coded by: Riccardo Mollo', 'cyan'))
    print()

def exception_handler(exception_type, exception, traceback):
    print("%s: %s\n%s" % (exception_type.__name__, exception, traceback))

def signal_handler(sig, frame):
    if sig == 2: # Ctrl+C (SIGINT)
        print()
        print('You pressed Ctrl+C! Goodbye!')
        print()

        sys.exit()

def get_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect((MCST_ADDR, 1))
        ip_addr = sock.getsockname()[0]
    except Exception:
        ip_addr = '127.0.0.1'
    finally:
        sock.close()

    return ip_addr

class Chat:
    def __init__(self, port, render_message, username, host, key):
        self.port = port
        self.render_message = render_message
        self.username = username
        self.host = host
        self.key = key
        self.users = []

        try:
            self.sock_to_read = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_to_read.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_to_read.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock_to_read.bind((BIND_ADDR, port))
            self.sock_to_write = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_to_write.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.users.append(self.username)
        except PermissionError as permission_error:
            raise ConnectionError(colored('Permission denied (binding failed for port ' + str(port) + '/UDP)', 'red', attrs = ['bold'])) from permission_error
        except Exception as exception:
            raise ConnectionError(colored('Unable to connect.', 'red', attrs = ['bold'])) from exception

    def send_request(self, sock_to_write, action, data = None):
        object_to_send = {'action': action, 'data': data, 'username': self.username, 'host': self.host}
        sock_to_write.sendto(bytes(dumps(object_to_send), 'utf-8'), (MCST_MASK, self.port))

    def iterate(self):
        socket_list = [self.sock_to_read]
        ready_to_read, _, _ = select.select(socket_list, [], [], 0)

        for sock in ready_to_read:
            if sock == self.sock_to_read:
                data = sock.recv(4096).decode('utf-8')

                if not data:
                    raise ConnectionAbortedError(colored('Connection aborted.', 'red', attrs = ['bold']))

                self.render_message(self, data)

    def send_announcement(self):
        self.send_request(self.sock_to_write, 'announcement', '')

    def send_message(self, message, key):
        if key is None:
            self.send_request(self.sock_to_write, 'message', message)
        else:
            self.send_request(self.sock_to_write, 'message', cryptocode.encrypt(message, key))

    def send_bye(self):
        self.send_request(self.sock_to_write, 'bye', '')

    def send_users_local_list(self, users_list):
        self.send_request(self.sock_to_write, 'users_list', users_list)

class MrChaTTY:
    def __init__(self, port, username, host, key):
        self.chat = Chat(port, self.render_message, username, host, key)
        self.chat.send_announcement()
        self.chat.send_users_local_list(self.chat.users)

    def iterate(self):
        self.chat.iterate()

        data = self.get_input()

        if data is not None:
            if len(data) == 0: # Ctrl+D
                print()
                print('You pressed Ctrl+D! Goodbye!')
                print()

                self.chat.send_bye()
                sys.exit()
            elif data[0] == '/':
                command = data[1:].rstrip()

                if command in 'date':
                    print(colored(datetime.datetime.now().strftime("%d/%m/%Y"), 'magenta'))
                elif command in 'time':
                    print(colored(datetime.datetime.now().strftime("%H:%M:%S"), 'magenta'))
                elif command in 'datetime':
                    print(colored(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), 'magenta'))
                elif command in ('bye', 'exit', 'leave', 'quit'):
                    self.chat.send_bye()
                    sys.exit()
                elif command in 'users':
                    print(colored('There are ' + str(len(self.chat.users)) + ' users in this room:', 'magenta'))
                    for user in self.chat.users:
                        print(colored('- ' + user, 'magenta'))
                else:
                    print(colored('Invalid command: ' + command, 'magenta'))
            else:
                self.chat.send_message(data, key)

    @staticmethod
    def render_message(chat, message):
        sys.stdout.write('\r')

        message = loads(message)
        nickname = message['username']
        action = message['action']
        origin_host = message['host']
        message = message['data']

        if nickname != username: # print only if user is not myself
            if action == 'announcement':
                sys.stdout.write('{} {} {}\n'.format(colored(nickname, 'green', attrs = ['bold']), colored('joined the chat from', 'green'), colored(origin_host, 'green', attrs = ['bold'])))
                chat.users.append(nickname)
                chat.send_users_local_list(chat.users)
            elif action == 'bye':
                sys.stdout.write('{} {}\n'.format(colored(nickname, 'green', attrs = ['bold']), colored('left the chat. Bye!', 'green')))
                chat.users.remove(nickname)
            elif action == 'users_list':
                chat.users = sorted(list(set(chat.users) | set(message)))
            else:
                if chat.key is None:
                    sys.stdout.write('<{}> {}'.format(colored(nickname, attrs = ['bold']), message))
                else:
                    message = cryptocode.decrypt(message, key)

                    if message is not False:
                        sys.stdout.write('<{}> {}'.format(colored(nickname, attrs = ['bold']), message))
                    else:
                        sys.stdout.write('<{}> {}'.format(colored(nickname, attrs = ['bold']), colored('UNREADABLE MESSAGE\n', 'red'))) # tofix

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
    parser.add_argument('-k', '--key', help = 'Group-defined secret key', required = False)
    parser.add_argument('-d', '--debug', help = 'Debug messages for errors and exceptions', action = 'store_false')
    args = parser.parse_args()
    username = args.user
    key = args.key
    debug = args.debug

    if debug:
        sys.tracebacklimit = 0
        sys.excepthook = exception_handler

    host = platform.node()
    ipAddr = get_ip()

    logo()
    print('Username: ' + colored(username, attrs = ['bold']))
    print('Local IP: ' + colored(ipAddr, attrs = ['bold']))
    print(colored('-------------------------------------------', 'yellow'))

    mrchatty = MrChaTTY(BIND_PORT, username, ipAddr, key)

    while True:
        mrchatty.iterate()