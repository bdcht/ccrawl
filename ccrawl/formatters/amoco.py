# from amoco.system import structs
from ccrawl.utils import c_type, cxx_type
from click import secho
from tinydb import where

__all__ = [
    "cTypedef_amoco",
    "cMacro_amoco",
    "cFunc_amoco",
    "cEnum_amoco",
    "cStruct_amoco",
    "cUnion_amoco",
]

tostruct = {
    "void": "x",
    "_Bool": "?",
    "char": "c",
    "unsigned char": "B",
    "short": "h",
    "unsigned short": "H",
    "int": "i",
    "unsigned int": "I",
    "long": "l",
    "unsigned long": "L",
    "float": "f",
    "ssize_t": "n",
    "size_t": "N",
    "double": "d",
    "long long": "q",
    "unsigned long long": "Q",
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
            out.append(v.show(None, form="amoco"))
        # if t base is an anonymous type, we replace its anon name
        # by its struct/union definition in t:
        return "\n\n".join(out)
    return wrapper

def id_amoco(s):
    s = s.replace("$","_").replace(":","_")
    return s.replace("?_", "").replace(" ", "_")


def fieldformat(r):
    t = r.lbase
    if r.is_ptr:
        rt = "P"
    else:
        rt = tostruct.get(t, None)
    if rt is None:
        t = id_amoco(t)
    if r.dim > 0:
        if rt == "x":
            raise TypeError(r)
        if rt in ("c", "B"):
            rt = "s"
        if rt:
            rt = "{} * {:d}".format(rt, r.dim)
        else:
            t = "{} * {:d}".format(t, r.dim)
    elif r.lbfw > 0:
        if rt:
            rt = "{} *#{:d}".format(rt, r.lbfw)
        else:
            t = "{} *#{:d}".format(t, r.lbfw)
    return rt, t


@unfoldable
def cTypedef_amoco(obj, db):
    t = cxx_type(obj)
    rn, n = fieldformat(t)
    return u"TypeDefine('{}','{}')".format(obj.identifier, rn or n)


def cMacro_amoco(obj, db):
    v = obj.strip()
    try:
        v = int(v, base=0)
        return "{} = 0x{:x}".format(obj.identifier, v)
    except ValueError:
        pass
    return "{} = '{}'".format(obj.identifier, v)


def cFunc_amoco(obj, db):
    pass


def cEnum_amoco(obj, db):
    n = obj.identifier.replace(" ", "_")
    s = ["TypeDefine('{}','i')".format(n)]
    s.extend(("{} = {}".format(k, v) for (k, v) in obj.items()))
    return "\n".join(s)


def cClass_amoco(obj, db):
    return cStruct_amoco(obj.as_cStruct(db), db)

@unfoldable
def cStruct_amoco(obj, db):
    name = id_amoco(obj.identifier)
    clsn = "UnionDefine" if obj._is_union else "StructDefine"
    out = ['@{}("""'.format(clsn)]
    for i in obj:
        t, n, c = i
        r = cxx_type(t)
        if not n and not r.lbase.startswith("union "):
            continue
        rt, t = fieldformat(r)
        if rt:
            t = rt
        if c and c.count("\n") > 0:
            c = None
        out.append("{} : {} ;{}".format(t, n, c or ""))
    out.append('""")\nclass %s(StructFormatter):' % name)
    # add methods:
    out.append('    def __init__(self,data="",offset=0):')
    out.append('        if data: self.unpack(data,offset)\n')
    return "\n".join(out)


cUnion_amoco = cStruct_amoco
