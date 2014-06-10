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
    with closing(connection):
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

    __slots__ = ('__obj', )

    def __init__(self, obj):
        super(SilentCaller, self).__init__()
        self.__obj = obj

    def __getattr__(self, name):
        method = getattr(self.__obj, name)
        def wrapper(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except:
                pass
        return wrapper


def silently(obj):
    return SilentCaller(obj)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=u'Lancer un serveur en mode fork')
    arg_parser.add_argument('port', type=int, help=u'Port')
    arg_parser.add_argument('--workers', type=int, help=u'Nombre de workers', default=5)
    arg_parser.add_argument('--backlog', type=int, help=u'Taille du backlog de connexions', default=0)
    args = arg_parser.parse_args()
    
    accept_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with closing(accept_socket):
        accept_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        accept_socket.bind(('', args.port))
        accept_socket.listen(args.backlog)
        
        print 'LISTENING [PID={:05d}] Port = {}'.format(os.getpid(), args.port)

        processes = []
        for num in xrange(1, 1 + args.workers):
            p = Process(target=serve, args=(accept_socket, num))
            processes.append(p)
        
        try:
            for num, p in enumerate(processes, start=1):
                print 'STARING [PID={:05d}, NUM=#{:02d}]'.format(os.getpid(), num)
                p.start()
        finally:
            for p in processes:
                silently(p).join()
