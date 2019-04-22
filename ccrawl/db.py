import ctypes
from ccrawl.parser import ccore
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
            if config.url.startswith('http'):
                dbclass = CouchDB
            elif config.url.startswith('mongodb'):
                dbclass = MongoDB
            try:
                self.rdb = dbclass(config.url,auth=auth,verify=config.verify)
            except:
                self.rdb = None

    def set_tag(self,tag=None):
        self.tag = (where('tag').search(tag)) if tag else Query()

    def insert_multiple(self,docs):
        self.ldb.insert_multiple(docs)

    def contains(self,q=None,**kargs):
        if q is None: q = self.tag
        for k in kargs:
            q &= (where(k)==kargs[k])
        if self.rdb:
            return self.rdb.contains(q.hashval,**kargs)
        return self.ldb.contains(q)

    def search(self,q=None,**kargs):
        if q is None: q = self.tag
        for k in kargs:
            q &= (where(k)==kargs[k])
        if self.rdb:
            return list(self.rdb.search(q.hashval,**kargs))
        return self.ldb.search(q)

    def get(self,q=None,**kargs):
        if q is None: q = self.tag
        for k in kargs:
            q &= (where(k)==kargs[k])
        if self.rdb:
            return self.rdb.get(q.hashval,**kargs)
        return self.ldb.get(q)

    def close(self):
        self.ldb.close()

#------------------------------------------------------------------------------

class CouchDB(object):
    def __init__(self,url,auth=None,verify=True):
        import requests
        self.url = url
        self.verify = verify
        self.session = requests.Session()
        if auth: self.session.auth = auth
        r = self.session.get(self.url,verify=self.verify)
        r.raise_for_status()

#------------------------------------------------------------------------------

class MongoDB(object):
    def __init__(self,url,auth=None,verify=True):
        from pymongo import MongoClient
        self.url = url
        self.client = MongoClient(url)
        self.db = self.client['ccrawl']

    def __repr__(self):
        return u'<MongoDB [%s]>'%self.url

    def _where(self,q):
        res = dict()
        op = q[0]
        if op=='exists':
            res[q[1][0]] = {'$exists':True}
        elif op=='==':
            l,r = q[1][0],q[2]
            res[l] = r
        elif op=='matches':
            l,r = q[1][0],q[2]
            res[l] = {'$regex': r}
        elif op=='search':
            l,r = q[1][0],q[2]
            res[l] = {'$regex': r}
        elif op=='and':
            for x in q[1]:
                res.update(self._where(x))
        elif op=='or':
            res['$or'] = [self._where(x) for x in q[1]]
        return res

    def insert_multiple(self,docs):
        col = self.db['nodes']
        return col.insert_many(docs)

    def contains(self,q,**kargs):
        col = self.db['nodes']
        return len(list(col.find(self._where(q)).limit(1)))>0

    def search(self,q,**kargs):
        col = self.db['nodes']
        return list(col.find(self._where(q)))

    def get(self,q,**kargs):
        col = self.db['nodes']
        return col.find_one(self._where(q))
