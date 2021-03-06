#!/usr/bin/env python
# encoding: utf-8

import argparse
import base64
import multiprocessing
import time
import urlparse

from httplib import HTTPConnection, HTTPSConnection, HTTPException

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:    
    import xml.etree.ElementTree as ElementTree


def _wrap_with(code):
    
    def inner(text, bold=False):
        c = code
        if bold:
            c = "1;{}".format(c)
        cast = unicode if isinstance(text, unicode) else str
        return cast("\033[{}m{}\033[0m").format(c, text)
    
    return inner


red = _wrap_with('31')
green = _wrap_with('32')


class DeliciousError(Exception):
    
    def __init__(self, message):
        super(DeliciousError, self).__init__()
        self.__message = message
    
    @property
    def message(self):
        return self.__message
    
    def __str__(self):
        return self.__message


class Post(object):
    """Un post sur Delicious"""
    
    def __init__(self, url, description):
        super(Post, self).__init__()
        self.__url = url
        self.__description = description
        
    @property
    def url(self):
        return self.__url
    
    @property
    def description(self):
        return self.__description
    
    def __str__(self):
        return "Post for URL {}".format(self.__url)


class DeliciousClient(object):
    """Client Delicious"""
    
    BASE_URL = 'https://api.del.icio.us/v1'
    
    THROTTLE_INTERVAL = 1
    
    def __init__(self, user, password):
        super(DeliciousClient, self).__init__()
        self.__user = user
        self.__password = password
        
        url_components = urlparse.urlparse(self.BASE_URL)
        self.__root_path = url_components.path
        self.__connection = HTTPSConnection(url_components.hostname)
        self.__last_call_timestamp = 0
    
    def close(self):
        self.__connection.close()
    
    def get_all_posts(self):
        self.__throttle()
        
        url = '{}/posts/all'.format(self.__root_path)
        headers = self.__build_base_headers()
        self.__connection.request('GET', url, headers=headers)
        response = self.__connection.getresponse()
        self.__check_no_error(response)
        content = response.read()
        
        posts = []
        xml_posts = ElementTree.fromstring(content)
        for xml_post in xml_posts.iter('post'):
            post_url = xml_post.attrib['href']
            post_description = xml_post.attrib['description']
            post = Post(url=post_url, description=post_description)
            posts.append(post)
        return posts
    
    def delete_post(self, post):
        self.__throttle()
        
        url = '{}/posts/delete?url={}'.format(self.__root_path, post.url)
        headers = self.__build_base_headers()
        self.__connection.request('GET', url, headers=headers)
        response = self.__connection.getresponse()
        self.__check_no_error(response)
        content = response.read()
        
        result = ElementTree.fromstring(content)
        code = result.attrib["code"]
        if code != 'done':
            raise DeliciousError("Can't delete post {} : {}".format(post.url, code))
    
    def __enter__(self):
        pass
    
    def __exit__(self, ex_type, ex_value, traceback):
        self.close()
    
    def __throttle(self):
        now = time.time()
        elapsed = now - self.__last_call_timestamp
        if elapsed < self.THROTTLE_INTERVAL:
            time.sleep(self.THROTTLE_INTERVAL - elapsed)
        self.__last_call_timestamp = now
    
    def __build_base_headers(self):
        auth = 'Basic ' + base64.b64encode('{}:{}'.format(self.__user, self.__password))
        return { 'Authorization': auth }
    
    @staticmethod
    def __check_no_error(response):
        status = response.status
        if status in xrange(400, 600):
            reason = response.reason
            raise DeliciousError("Delicious error (HTTP code: {}, reason: {})".format(status, reason))


def url_exists(url):
    url_components = urlparse.urlparse(url)
    scheme = url_components.scheme
    hostname = url_components.hostname
    port = url_components.port
    timeout = 10
    
    if scheme == 'http':
        connection = HTTPConnection(hostname, port, timeout=timeout)
    elif scheme == 'https':
        connection = HTTPSConnection(hostname, port, timeout=timeout)
    else:
        raise ValueError('{}: not an HTTP/HTTPS URL'.format(url))
    
    try:
        path = url_components.path
        query = url_components.query
        relative_url = path
        if query:
            relative_url += '?' + query
        connection.request('GET', relative_url)
        response = connection.getresponse()
        status = response.status
        return status not in xrange(400, 600)
    except Exception:
        return False
    finally:
        connection.close()


def check_post(client, post, delete):
    url = post.url
    
    print u"Contrôle de {} ({}) ->".format(url, post.description),
    if url_exists(url):
        print green(u'OK')
    else:
        if delete:
            client.delete_post(post)
            print red(u'Supprimé')
        else:
            print red(u'KO')


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=u'Contrôler les favoris sur Delicious')
    arg_parser.add_argument('user', help=u"Nom d'utilisateur")
    arg_parser.add_argument('password', help=u'Mot de passe')
    arg_parser.add_argument('--delete', action='store_true', help=u'Supprimer les posts injoignables')
    args = arg_parser.parse_args()
    
    client = DeliciousClient(args.user, args.password)
    with client:
        print "Recherche des posts..."
        posts = client.get_all_posts()
        print "Tous les posts ont ete recuperes"
    
    for post in posts:
        check_post(client, post, args.delete)
