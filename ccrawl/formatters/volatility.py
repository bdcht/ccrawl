from ccrawl.utils import struct_letters
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


def cMacro_volatility(obj, db, recursive):
    return u"{} = {}".format(obj.identifier, obj)


def cFunc_volatility(obj, db, recursive):
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


def cTypedef_volatility(obj, db, recursive):
    obj.unfold(db)
    t = c_type(obj)
    S = [u"{} = {}".format(obj.identifier, ctype_to_volatility(t))]
    R = []
    if isinstance(recursive, set):
        for t in obj.subtypes.values() or []:
            if t is None:
                continue
            if not t.identifier in recursive:
                recursive.add(t.identifier)
                R.append(t.show(db, recursive, form="volatility"))
        if len(R) > 0:
            R.append("")
    return u"\n".join(R + S)


def cEnum_volatility(obj, db, recursive):
    obj.unfold(db)
    n = obj.identifier.replace(" ", "_")
    return u"{0} = ['Enumeration', dict(choices={1})]".format(n, obj)


def cStruct_volatility(obj, db, recursive):
    obj.unfold(db)
    n = obj.identifier.replace("?_", "").replace(" ", "_")
    t = build(obj)
    S = [u"{0} = [ {1}, {{".format(n, sizeof(t))]
    for i, f in enumerate(obj):
        ft, fn, fc = f
        if not fn:
            continue
        r = c_type(ft)
        off = getattr(t, fn).offset
        S.append(u"  '{0}': [{2}, {1}],".format(fn, ctype_to_volatility(r), off))
    S.append("}]")
    R = []
    if isinstance(recursive, set):
        for t in obj.subtypes.values() or []:
            if t is None:
                continue
            if not t.identifier in recursive:
                recursive.add(t.identifier)
                R.append(t.show(db, recursive, form="volatility"))
        if len(R) > 0:
            R.append("")
    return u"\n".join(R + S)


cUnion_volatility = cStruct_volatility
