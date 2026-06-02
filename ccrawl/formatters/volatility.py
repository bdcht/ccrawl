from ccrawl.utils import struct_letters, cxx_type
from ccrawl.ext.ctypes_ import build
from ctypes import sizeof

__all__ = [
    "cMacro_volatility",
    "cFunc_volatility",
    "cTypedef_volatility",
    "cEnum_volatility",
    "cStruct_volatility",
    "cUnion_volatility",
]

# volatility VTypes formatters:
# ------------------------------------------------------------------------------

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
            out.append(v.show(None, form="volatility"))
        # if t base is an anonymous type, we replace its anon name
        # by its struct/union definition in t:
        return "\n\n".join(out)
    return wrapper

def cMacro_volatility(obj, db):
    return u"{} = {}".format(obj.identifier, obj)


def cFunc_volatility(obj, db):
    raise NotImplementedError


def ctype_to_volatility(t):
    b = t.lbase
    if b not in struct_letters:
        res = b.replace("?_", "").replace(" ", "_")
        if res.startswith("struct_") or res.startswith("union_"):
            res = "['{}']".format(res)
    else:
        t.lconst = False  # const keyword not supported by volatility
        res = "['{}']".format(t.show_base())
    for p in t.pstack:
        if isinstance(p, arr):
            res = "['array', %d, %s]" % (p.a, res)
        elif isinstance(p, ptr):
            res = "['pointer', %s]" % res
        else:
            # prototypes are ignored...
            res = "['void']"
    return res


@unfoldable
def cTypedef_volatility(obj, db):
    t = cxx_type(obj)
    out = [u"{} = {}".format(obj.identifier, ctype_to_volatility(t))]
    return u"\n".join(out)


def cEnum_volatility(obj, db):
    n = obj.identifier.replace(" ", "_")
    return u"{0} = ['Enumeration', dict(choices={1})]".format(n, obj)


@unfoldable
def cStruct_volatility(obj, db):
    n = obj.identifier.replace("?_", "").replace(" ", "_")
    t = build(obj)
    out = [u"{0} = [ {1}, {{".format(n, sizeof(t))]
    for i, f in enumerate(obj):
        ft, fn, fc = f
        if not fn:
            continue
        r = cxx_type(ft)
        off = getattr(t, fn).offset
        out.append(u"  '{0}': [{2}, {1}],".format(fn, ctype_to_volatility(r), off))
    out.append("}]")
    return u"\n".join(out)

cUnion_volatility = cStruct_volatility
