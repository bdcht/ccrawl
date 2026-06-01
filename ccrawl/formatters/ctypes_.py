from ccrawl.utils import struct_letters, c_type, cxx_type, fargs
from click import secho
from tinydb import where

__all__ = [
    "cTypedef_ctypes",
    "cMacro_ctypes",
    "cFunc_ctypes",
    "cEnum_ctypes",
    "cStruct_ctypes",
    "cUnion_ctypes",
    "cClass_ctypes",
]

toCTypes = {
    "void": "c_void",
    "_Bool": "c_bool",
    "wchar_t": "c_wchar",
    "char": "c_byte",
    "unsigned char": "c_ubyte",
    "short": "c_short",
    "unsigned short": "c_ushort",
    "int": "c_int",
    "unsigned int": "c_uint",
    "long": "c_long",
    "unsigned long": "c_ulong",
    "float": "c_float",
    "double": "c_double",
    "ssize_t": "c_ssize_t",
    "size_t": "c_size_t",
    "long long": "c_longlong",
    "__int64": "c_longlong",
    "unsigned long long": "c_ulonglong",
    "unsigned __int64": "c_ulonglong",
}

def unfoldable(f):
    def wrapper(obj,db):
        if db is None:
            return f(obj,db)
        ctx = OrderedDict(struct_letters)
        obj.unfold(db,ctx)
        # when unfolding, ctx items are ordered in a way that ensures if a type
        # is used several times in further definitions, it will be indexed after
        # all these definitions.
        out = []
        def cond(k,v):
            if isinstance(v,ccore):
                t = cxx_type(v.identifier)
                if k==t.show(kw=False) and not "std" in t.ns:
                    return True
            return False
        for v in (v for (k,v) in reversed(ctx.items()) if cond(k,v)):
            if "?_" in v.identifier:
                continue
            out.append(v.show(None, form="ctypes"))
        # if t base is an anonymous type, we replace its anon name
        # by its struct/union definition in t:
        return "\n\n".join(out)
    return wrapper

def id_ctypes(t):
    i = t.lbase
    if t.lunsigned:
        i = "unsigned " + i
    r = toCTypes.get(i, i.replace("?_", "").replace(" ", "_"))
    P = t.pstack[:]
    if r in ("c_void", "c_char", "c_wchar") and t.is_ptr:
        if P[0].is_ptr:
            r = r + "_p"
            P.pop(0)
    while P:
        p = P.pop(0)
        if p.is_ptr:
            for _ in p.p:
                r = "POINTER(%s)" % r
        elif isinstance(p, fargs):
            r = formatproto(r, p)
            x = P.pop(0)
            assert x.is_ptr
            r = "POINTER(%s)" % r
        else:
            r = "%s*%d" % (r, p.a)
    if r == "c_void":
        return "None"
    return r


def formatproto(res, proto):
    f = "CFUNCTYPE"
    params = [id_ctypes(x) for x in proto.args]
    if res == "c_void":
        res = "None"
    params.insert(0, res)
    return "{}({})".format(f, ", ".join(params))

@unfoldable
def cTypedef_ctypes(obj, db):
    t = cxx_type(obj)
    if t.is_anon and obj.subtypes:
        out = obj.subtypes[obj].show(form="ctypes")
    else:
        out = t.show(kw=True)
    return u"{} = {}".format(obj.identifier, id_ctypes(t))


def cMacro_ctypes(obj, db):
    v = obj.strip()
    try:
        v = int(v, base=0)
    except ValueError:
        pass
    return "{} = {}".format(obj.identifier, v)


def cFunc_ctypes(obj, db):
    f = "CFUNCTYPE"
    pre = ""
    res = obj.restype()
    args = obj.argtypes()
    if db is not None:
        for t in [res] + args:
            t = cxx_type(t)
            if t.lbase not in struct_letters:
                Q = db.tag & (where("id") == t.show(kw=True))
                if db.contains(Q):
                    x = obj.from_db(db.get(Q))
                    pre = x.show(db, form="ctypes")
                    pre += "\n\n"
                else:
                    secho("identifier %s not found" % t.lbase, fg="red", err=True)
    params = [id_ctypes(cxx_type(x)) for x in args]
    res = id_ctypes(cxx_type(res))
    if res == "c_void":
        res = "None"
    params.insert(0, res)
    return "{} = {}({})".format(obj.identifier, f, ", ".join(params))


def cEnum_ctypes(obj, db):
    n = obj.identifier.replace(" ", "_")
    S = ["{} = c_int".format(n)]
    S.extend(("{} = {}".format(k, v) for (k, v) in obj.items()))
    return "\n".join(S)


@unfoldable
def cStruct_ctypes(obj, db):
    name = id_ctypes(cxx_type(obj.identifier))
    clsn = "Union" if obj._is_union else "Structure"
    out = ["{0} = type('{0}',({1},),{{}})\n".format(name, clsn)]
    fld = "%s._fields_ = [" % name
    out.append(fld)
    for i in obj:
        t, n, c = i
        r = cxx_type(t)
        e = r.lbase
        if not n and not r.lbase.startswith("union "):
            continue
        t = id_ctypes(r)
        if r.lbfw:
            t += ", %d" % r.lbfw
        out.append('    ("{}", {}),'.format(n, t))
    out.append("]")
    return "\n".join(out)


cUnion_ctypes = cStruct_ctypes


def cClass_ctypes(obj, db):
    return cStruct_ctypes(obj.as_cStruct(db), db)
