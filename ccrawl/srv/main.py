from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restful import reqparse, abort, Api, Resource

from ccrawl import conf
from ccrawl.parser import ccore, c_type
from ccrawl.db import where, Query

import re

app = Flask(__name__)
app.config.from_object(conf.config.Database)
app.config["MONGO_URI"] = conf.config.Database.url

CORS(app, resources={r"/*": {"origins": "*"}})

api = Api(app)

g_ctx = None


class Tags(Resource):
    def get(self):
        db = g_ctx.obj["db"]
        L = set()
        for l in db.search():
            if "tag" in l:
                L.add(l["tag"])
        return [{"tag": t} for t in L]


class Sources(Resource):
    def get(self):
        db = g_ctx.obj["db"]
        L = set()
        for l in db.search():
            if "src" in l:
                L.add(l["src"])
        return [{"src": s} for s in L]


class Stats(Resource):
    def get(self):
        db = g_ctx.obj["db"]
        D = {"database": str(db.rdb)}
        for x in (
            "cFunc",
            "cClass",
            "cStruct",
            "cUnion",
            "cEnum",
            "cTypedef",
            "cMacro",
            "cTemplate",
        ):
            D[x] = len(db.search(where("cls") == x))
        return D


class Search(Resource):
    def get(self):
        return {"verbose": False, "tag": "", "ignorecase": False, "rex": ""}

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("verbose", type=bool)
        parser.add_argument("tag")
        parser.add_argument("ignorecase", type=bool)
        parser.add_argument("rex")
        args = parser.parse_args()
        db = g_ctx.obj["db"]
        if args["tag"]:
            db.set_tag(args["tag"])
        if args["verbose"]:
            keys = ("cls", "tag", "src", "use")
        flg = re.MULTILINE
        if args["ignorecase"]:
            flg |= re.IGNORECASE
        rex = args["rex"]
        Q = where("id").matches(rex, flags=flg)
        Q |= where("val").matches(rex, flags=flg)
        L = []
        for l in db.search(Q):
            d = {"id": l["id"], "val": l["val"]}
            if args["verbose"]:
                for k in keys:
                    d[k] = l[k]
            L.append(d)
        return L


class Show(Resource):
    def get(self):
        return {
            "verbose": False,
            "tag": "",
            "recursive": False,
            "fmt": "C",
            "identifier": "",
        }

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("verbose", type=bool)
        parser.add_argument("recursive", type=bool)
        parser.add_argument("tag")
        parser.add_argument("fmt")
        parser.add_argument("identifier")
        args = parser.parse_args()
        db = g_ctx.obj["db"]
        if args["tag"]:
            db.set_tag(args["tag"])
        if verbose := args["verbose"]:
            keys = ("cls", "tag", "src", "use")
        fmt = args["fmt"] or "C"
        recursive = args["recursive"]
        identifier = args["identifier"]
        Q = where("id") == identifier
        L = []
        for l in db.search(Q):
            x = ccore.from_db(l)
            d = {"id": l["id"], "val": x.show(db, recursive, form=fmt)}
            if verbose:
                for k in keys:
                    d[k] = l[k]
            L.append(d)
        return L


class Select(Resource):
    def get(self):
        return {"verbose": False, "tag": "", "key": "", "match": ""}

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("verbose", type=bool)
        parser.add_argument("tag")
        parser.add_argument("key")
        parser.add_argument("match")
        args = parser.parse_args()
        db = g_ctx.obj["db"]
        if args["tag"]:
            db.set_tag(args["tag"])
        if verbose := args["verbose"]:
            keys = ("cls", "tag", "src", "use")
        key = args["key"]
        rex = args["match"] or ".*"
        Q = where(key).matches(rex)
        L = []
        for l in db.search(Q):
            d = {"id": l["id"], key: l[key]}
            if verbose:
                for k in keys:
                    d[k] = l[k]
            L.append(d)
        return L


class Select_Prototype(Resource):
    def get(self):
        return {
            "verbose": False,
            "tag": "",
            "key": "",
            "match": "",
            "format": "C",
            "proto": "",
        }

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("verbose", type=bool)
        parser.add_argument("tag")
        parser.add_argument("key")
        parser.add_argument("match")
        parser.add_argument("proto")
        parser.add_argument("format")
        args = parser.parse_args()
        db = g_ctx.obj["db"]
        if args["tag"]:
            db.set_tag(args["tag"])
        if verbose := args["verbose"]:
            keys = ("src", "tag")
        if args["key"] and args["match"]:
            Q = where(args["key"]).matches(args["match"])
        else:
            Q = Query().noop()
        proto = args["proto"].split(";")
        fmt = args.get("format", "C")
        reqs = {}
        try:
            for p in proto:
                pos, t = p.split(":")
                pos = int(pos)
                reqs[pos] = c_type(t).show()
        except Exception:
            return abort(400, reason="bad prototype request")
        L = []
        for l in db.search(Q & (where("cls") == "cFunc")):
            x = ccore.from_db(l)
            P = [c_type(t).show() for t in x.argtypes()]
            P.insert(0, c_type(x.restype()).show())
            if max(reqs) >= len(P):
                continue
            if not all(((t == P[i]) for (i, t) in reqs.items())):
                continue
            d = {"id": l["id"], "val": x.show(db, form=fmt)}
            if verbose:
                for k in keys:
                    d[k] = l[k]
            L.append(d)
        return L


class Select_Constant(Resource):
    def get(self):
        return {
            "verbose": False,
            "tag": "",
            "key": "",
            "match": "",
            "mask": False,
            "prefix": "",
            "val": "",
        }

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("verbose", type=bool)
        parser.add_argument("tag")
        parser.add_argument("key")
        parser.add_argument("match")
        parser.add_argument("mask", type=bool)
        parser.add_argument("prefix")
        parser.add_argument("val")
        args = parser.parse_args()
        db = g_ctx.obj["db"]
        if args["tag"]:
            db.set_tag(args["tag"])
        if verbose := args["verbose"]:
            keys = ("src", "tag")
        if args["key"] and args["match"]:
            Q = where(args["key"]).matches(args["match"])
        else:
            Q = Query().noop()
        try:
            value = int(args["val"], 0)
        except (ValueError, TypeError):
            abort(400, reason="invalid value")
        mask = args["mask"]
        pfx = args["prefix"] or ""
        Q &= (where("cls") == "cMacro") | (where("cls") == "cEnum")
        L = []
        for l in db.search(Q):
            x = ccore.from_db(l)
            out = ""
            if x._is_macro:
                if pfx not in x.identifier:
                    continue
                try:
                    v = int(x, 0)
                except Exception:
                    continue
                else:
                    if v == value:
                        out = x.identifier
                    elif mask and (pfx in x.identifier):
                        if v < value and v & value:
                            out = x.identifier + " | "
            else:
                for k, v in x.items():
                    if v == value and (pfx in k):
                        out = k
                        break
                    elif mask and (pfx in k):
                        if v < value and v & value:
                            out = k + " | "
            if out:
                d = {"val": out}
                if verbose:
                    for k in keys:
                        d[k] = l[k]
                L.append(d)
        return L


class Select_Struct(Resource):
    def get(self):
        return {
            "verbose": False,
            "tag": "",
            "key": "",
            "match": "",
            "def": False,
            "format": "C",
            "conds": "",
        }

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("verbose", type=bool)
        parser.add_argument("tag")
        parser.add_argument("key")
        parser.add_argument("match")
        parser.add_argument("def", type=bool)
        parser.add_argument("format")
        parser.add_argument("conds")
        args = parser.parse_args()
        db = g_ctx.obj["db"]
        if args["tag"]:
            db.set_tag(args["tag"])
        if verbose := args["verbose"]:
            keys = ("src", "tag")
        if args["key"] and args["match"]:
            Q = where(args["key"]).matches(args["match"])
        else:
            Q = Query().noop()
        fmt = args["format"] or "C"
        conds = args["conds"].split(";")
        pdef = args["def"]
        reqs = {}
        try:
            for p in conds:
                off, t = p.split(":")
                if off == "*":
                    sz = int(t)
                    reqs[off] = sz
                else:
                    off = int(off)
                    if t[0] == "+":
                        reqs[off] = int(t)
                    elif t[0] == "?":
                        reqs[off] = t
                    else:
                        reqs[off] = c_type(t)
        except Exception:
            abort(400, reason="invalid constraints")
        L = []
        for l in db.search(
            Q & ((where("cls") == "cStruct") | (where("cls") == "cClass"))
        ):
            x = ccore.from_db(l)
            out = ""
            ctcls = c_type
            try:
                if x._is_class:
                    x = x.as_cStruct(db)
                t = x.build(db)
            except Exception:
                continue
            F = []
            for i, f in enumerate(t._fields_):
                field = getattr(t, f[0])
                F.append((field.offset, field.size, ctcls(x[i][0])))
            if F:
                xsize = F[-1][0] + F[-1][1]
                if "*" in reqs and reqs["*"] != xsize:
                    continue
                F = dict(((f[0], f[1:3]) for f in F))
                ok = []
                for o, s in reqs.items():
                    if o == "*":
                        continue
                    cond = o in F
                    ok.append(cond)
                    if not cond:
                        break
                    if s == "?":
                        continue
                    if s == "*":
                        cond = F[o][1].is_ptr
                    elif isinstance(s, c_type):
                        cond = F[o][1].show() == s.show()
                    else:
                        cond = F[o][0] == s
                    ok.append(cond)
                    if not cond:
                        break
                if all(ok):
                    if not pdef:
                        out = x.identifier
                    else:
                        out = x.show(db, form=fmt)
            if out:
                d = {"val": out}
                if verbose:
                    for k in keys:
                        d[k] = l[k]
                L.append(d)
        return L


api.add_resource(Search, "/api/search")
api.add_resource(Tags, "/api/tags")
api.add_resource(Sources, "/api/sources")
api.add_resource(Stats, "/api/stats")
api.add_resource(Show, "/api/show")
api.add_resource(Select, "/api/select")
api.add_resource(Select_Prototype, "/api/select/prototype")
api.add_resource(Select_Constant, "/api/select/constant")
api.add_resource(Select_Struct, "/api/select/struct")


def run(ctx):
    global g_ctx
    g_ctx = ctx
    app.run(debug=False)
