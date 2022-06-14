import requests
import click
from tinydb.storages import JSONStorage, MemoryStorage
from tinydb.middlewares import CachingMiddleware
from tinydb import TinyDB, Query, where


class Proxy(object):
    def __init__(self, config):
        self.c = config
        self.ldb = None
        self.rdb = None
        self.tag = Query().noop()
        self.req = None
        if config.local:
            try:
                self.ldb = TinyDB(config.local, storage=CachingMiddleware(JSONStorage))
            except Exception:
                self.ldb = TinyDB(storage=MemoryStorage)
        else:
            self.ldb = TinyDB(storage=MemoryStorage)
        if config.url:
            auth = None
            if config.user:
                auth = (config.user, click.prompt("password", hide_input=True))
            if config.url.startswith("http"):
                dbclass = CouchDB
            elif config.url.startswith("mongodb"):
                dbclass = MongoDB
            try:
                self.rdb = dbclass(config.url, auth=auth, verify=config.verify)
            except Exception:
                self.rdb = None

    def set_tag(self, tag=None):
        self.tag = (where("tag") == tag) if (tag is not None) else Query().noop()

    def insert_multiple(self, docs):
        self.ldb.insert_multiple(docs)

    def contains(self, q=None, **kargs):
        if q is None:
            q = self.tag
        for k in kargs:
            q &= where(k) == kargs[k]
        if self.rdb:
            return self.rdb.contains(q._hash, **kargs)
        return self.ldb.contains(q)

    def search(self, q=None, **kargs):
        if q is None:
            q = self.tag
        else:
            q = self.tag & q
        for k in kargs:
            q &= where(k) == kargs[k]
        if self.rdb:
            return list(self.rdb.search(q._hash, **kargs))
        return self.ldb.search(q)

    def get(self, q=None, **kargs):
        if q is None:
            q = self.tag
        for k in kargs:
            q &= where(k) == kargs[k]
        if self.rdb:
            return self.rdb.get(q._hash, **kargs)
        return self.ldb.get(q)

    def cleanup_local(self):
        D = {}
        for e in self.ldb.search(self.tag):
            k = "%s := %s" % (e["id"], e["val"])
            if not k in D:
                D[k] = [e.doc_id]
            else:
                D[k].append(e.doc_id)
        for v in D.values():
            if len(v) > 1:
                self.ldb.remove(doc_ids=v[1:])

    def cleanup(self):
        self.rdb.cleanup(self)

    def find_matching_types(self, Locs, req=None, psize=0):
        if self.rdb is not None:
            self.rdb.find_matching_types(Locs, req, psize)
        return Locs

    def close(self):
        self.ldb.close()


# ------------------------------------------------------------------------------


class CouchDB(object):
    def __init__(self, url, auth=None, verify=True):
        self.url = url
        self.verify = verify
        self.session = requests.Session()
        if auth:
            self.session.auth = auth
        r = self.session.get(self.url, verify=self.verify)
        r.raise_for_status()


# ------------------------------------------------------------------------------


class MongoDB(object):
    def __init__(self, url, auth=None, verify=True):
        from pymongo import MongoClient

        self.url = url
        self.client = MongoClient(url)
        self.db = self.client.get_database("ccrawl")

    def __repr__(self):
        return u"<MongoDB [%s]>" % self.url

    def _where(self, q):
        res = dict()
        if len(q) > 1:
            op = q[0]
            if op == "exists":
                res[q[1][0]] = {"$exists": True}
            elif op == "==":
                l, r = q[1][0], q[2]
                res[l] = r
            elif op == "matches":
                l, r = q[1][0], q[2]
                if l in ("val", "use"):
                    res[l] = {"$all": [r]}
                else:
                    res[l] = {"$regex": r}
            elif op == "search":
                l, r = q[1][0], q[2]
                res[l] = {"$regex": r}
            elif op == "and":
                for x in q[1]:
                    res.update(self._where(x))
            elif op == "or":
                res["$or"] = [self._where(x) for x in q[1]]
        return res

    def insert_multiple(self, docs):
        col = self.db.get_collection("nodes")
        return col.insert_many(docs)

    def contains(self, q, **kargs):
        col = self.db.get_collection("nodes")
        return len(list(col.find(self._where(q)).limit(1))) > 0

    def search(self, q, **kargs):
        col = self.db.get_collection("nodes")
        return list(col.find(self._where(q)))

    def get(self, q, **kargs):
        col = self.db.get_collection("nodes")
        return col.find_one(self._where(q))

    def cleanup(self, proxy):
        from pymongo import TEXT

        click.echo("removing duplicates...", nl=False)
        self.remove_duplicates()
        click.echo("done.")
        click.echo("updating collections of offsets/size for structs...", nl=False)
        self.cleanup_structs()
        self.update_structs(proxy)
        click.echo("done.")
        col = self.db.get_collection("nodes")
        click.echo("indexing 'id' and 'val' fields...", nl=False)
        col.create_index([("id", TEXT), ("val", TEXT)])
        click.echo("done.")

    def cleanup_structs(self, **kargs):
        for col in (self.db["structs_ptr32"], self.db["structs_ptr64"]):
            L = []
            for s in col.find():
                o = self.db["nodes"].find_one({"_id": s["_id"]})
                if (o is None) or all((o[k] == v for (k, v) in kargs.items())):
                    L.append(s["_id"])
            col.delete_many({"_id": {"$in": L}})

    def cleanup_selected(self, **kargs):
        L = []
        S = []
        for s in self.db["nodes"].find(kargs):
            L.append(s["_id"])
            if s["cls"] == "cStruct":
                S.append(s["_id"])
        if len(S) > 0:
            self.db["structs_ptr32"].delete_many({"_id": {"$in": S}})
            self.db["structs_ptr64"].delete_many({"_id": {"$in": S}})
        if len(L) > 0:
            self.db["nodes"].delete_many({"_id": {"$in": L}})

    def update_structs(self, proxydb, req=None):
        from ccrawl.core import ccore
        from ccrawl.ext import amoco

        col = self.db.get_collection("nodes")
        req = req or {}
        req.update({"cls": "cStruct"})
        s_32 = self.db["structs_ptr32"]
        s_64 = self.db["structs_ptr64"]
        for s in col.find(req):
            click.echo("updating {}".format(s["id"]))
            i = s["_id"]
            x = ccore.from_db(s)
            try:
                ax = amoco.build(x, proxydb)()
                off32 = ax.offsets(psize=4)
                tot32 = ax.size(psize=4)
                off64 = ax.offsets(psize=8)
                tot64 = ax.size(psize=8)
            except Exception:
                continue
            s_32.update_one(
                {"_id": i},
                {"$set": {"_id": i, "size": tot32, "offsets": off32}},
                upsert=True,
            )
            s_64.update_one(
                {"_id": i},
                {"$set": {"_id": i, "size": tot64, "offsets": off64}},
                upsert=True,
            )

    def remove_duplicates(self, **kargs):
        col = self.db.get_collection("nodes")
        L = [{"$match": kargs}] if kargs else []
        L += [
            {
                "$group": {
                    "_id": {"id": "$id", "val": "$val"},
                    "count": {"$sum": 1},
                    "tbd": {"$push": "$$ROOT._id"},
                }
            },
            {"$match": {"count": {"$gt": 1}}},
        ]
        res = col.aggregate(L)
        for x in res:
            # click.echo("found {} occurences for {}".format(x["count"],
            #                                               x["_id"]))
            col.delete_many({"_id": {"$in": x["tbd"][1:]}})

    def find_matching_types(self, Locs, req=None, psize=0):
        if req is None:
            req = {}
        psize = psize // 8 or psize
        if psize == 0:
            self.find_matching_types(Locs, req, psize=4)
            self.find_matching_types(Locs, req, psize=8)
            return
        col = self.db["structs_ptr%2d" % (psize * 8)]
        for n, S in Locs.items():
            res = col.aggregate(
                [
                    {"$match": {"offsets": {"$all": S}}},
                    {
                        "$lookup": {
                            "from": "nodes",
                            "localField": "_id",
                            "foreignField": "_id",
                            "as": "node",
                        }
                    },
                    {
                        "$replaceRoot": {
                            "newRoot": {
                                "$mergeObjects": [
                                    {"$arrayElemAt": ["$node", 0]},
                                    "$$ROOT",
                                ]
                            }
                        }
                    },
                    {"$project": {"node": 0}},
                    {"$match": req},
                ]
            )
            Locs[n] = (S, [x["id"] for x in res])
