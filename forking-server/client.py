#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import socket
from contextlib import closing


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=u'Lancer un serveur en mode fork')
    arg_parser.add_argument('port', type=int, help=u'Port')
    args = arg_parser.parse_args()
    
    client = socket.create_connection(('localhost', args.port))
    with closing(client):
        client.sendall('La peche ?')
