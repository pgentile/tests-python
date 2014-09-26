#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import gc
import os
import socket
from contextlib import closing, contextmanager
from multiprocessing import Process


@contextmanager
def disabled_gc():
    gc.disable()
    yield
    gc.enable()


def serve(accept_socket, num):
    # gc.set_threshold(10, 2, 2)
    # gc.set_debug(gc.DEBUG_STATS)
    
    print 'FORKED [PID={:05d}, NUM=#{:02d}]'.format(os.getpid(), num)
    
    try:
        while True:
            with disabled_gc():
                accept_and_handle(accept_socket, num)
    except KeyboardInterrupt:
        print 'END [PID={:05d}, NUM=#{:02d}]'.format(os.getpid(), num)


def accept_and_handle(accept_socket, num):
    connection, addr = accept_socket.accept()
    print 'ACCEPT [PID={:05d}, NUM=#{:02d}, CNX={!r}]'.format(
        os.getpid(),
        num,
        addr,
    )
    with closing(silently(connection)):
        handle(connection, addr, num)


def handle(connection, addr, num):
    data = connection.recv(4096)
    print 'DATA [PID={:05d}, NUM=#{:02d}, CNX={!r}] {!r}'.format(
        os.getpid(),
        num,
        addr,
        data[0:100] + '...',
    )
    print 'CLOSED [PID={:05d}, NUM=#{:02d}, CNX={!r}]'.format(
        os.getpid(),
        num,
        addr,
    )


class SilentCaller(object):

    __slots__ = ('__obj', '__root')

    def __init__(self, obj, root=Exception):
        super(SilentCaller, self).__init__()
        self.__obj = obj
        self.__root = root

    def __getattr__(self, name):
        method = getattr(self.__obj, name)
        if not callable(method):
            raise ValueError("{!r} is not callable".format(method))
            
        def wrapper(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except self.__root:
                pass
        return wrapper


def silently(*args, **kwargs):
    return SilentCaller(*args, **kwargs)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=u'Lancer un serveur en mode fork')
    arg_parser.add_argument('port', type=int, help=u'Port')
    arg_parser.add_argument('--workers', '-w', type=int, help=u'Nombre de workers', default=5)
    arg_parser.add_argument('--backlog', type=int, help=u'Taille du backlog de connexions', default=0)
    arg_parser.add_argument('--bind', '-b', help=u'Adresse sur laquelle écouter', default='0.0.0.0')
    args = arg_parser.parse_args()
    
    accept_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with closing(silently(accept_socket)):
        accept_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        accept_socket.bind((args.bind, args.port))
        accept_socket.listen(args.backlog)
        
        print 'LISTENING [PID={:05d}] Port = {}, bind to {}'.format(os.getpid(), args.port, args.bind)

        processes = []
        for num in xrange(1, 1 + args.workers):
            p = Process(target=serve, args=(accept_socket, num))
            processes.append(p)
        
        try:
            for num, p in enumerate(processes, start=1):
                print 'STARING WORKER #{1:02d} [PID={0:05d}]'.format(os.getpid(), num)
                p.start()
        finally:
            timeout = 0.5
            while processes:
                for index, p in enumerate(processes):
                    silently(p, root=BaseException).join(timeout)
                    if not p.is_alive():
                        print 'STOPPED WORKER WITH PID {1:05d} [PID={0:05d}]'.format(os.getpid(), p.pid)
                        del processes[index]
                        break
