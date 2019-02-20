import requests
import ctypes
from crawl.parser import ccore
from tinydb.storages import JSONStorage,MemoryStorage
from tinydb.middlewares import CachingMiddleware
from tinydb import TinyDB, Query, where

class Proxy(object):
    def __init__(self,config):
        self.c = config
        self.ldb = None
        self.rdb = None
        self.tag = Query()
        self.req = None
        if config.local:
            try:
                self.ldb = TinyDB(config.local,
                                  storage=CachingMiddleware(JSONStorage))
            except:
                self.ldb = TinyDB(storage=MemoryStorage)
        if config.url:
            auth = None
            if config.user:
                auth = (config.user,click.prompt('password',hide_input=True))
            try:
                self.rdb = CouchDB(config.url,auth=auth,verify=config.verify)
            except:
                self.rdb = None

    def set_tag(self,tag=None):
        self.tag = (where('tag').search(tag)) if tag else Query()

    def insert_multiple(self,docs):
        self.ldb.insert_multiple(docs)

    def contains(self,q=None,**kargs):
        if self.rdb:
            return self.rdb.contains(q,**kargs)
        if q is None: q = Query()
        for k in kargs:
            q &= (where(k)==kargs[k])
        return self.ldb.contains(self.tag & q)

    def search(self,q=None,**kargs):
        if self.rdb:
            return self.rdb.search(q,**kargs)
        if q is None: q = Query()
        for k in kargs:
            q &= (where(k)==kargs[k])
        return self.ldb.search(self.tag & q)

    def get(self,q=None,**kargs):
        if self.rdb:
            return self.rdb.get(q,**kargs)
        if q is None: q = Query()
        for k in kargs:
            q &= (where(k)==kargs[k])
        return self.ldb.get(self.tag & q)

    def close(self):
        self.ldb.close()

#------------------------------------------------------------------------------

class CouchDB(object):
    def __init__(self,url,auth=None,verify=True):
        self.url = url
        self.verify = verify
        self.session = requests.Session()
        if auth: self.session.auth = auth
        r = self.session.get(self.url,verify=self.verify)
        r.raise_for_status()

