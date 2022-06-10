from ccrawl import conf
from ccrawl.formatters.ctypes_ import toCTypes
from ccrawl.utils import c_type, cxx_type, fargs, pp
from click import secho
import ctypes


def mk_ctypes(t, Types):
    i = t.lbase
    if t.lunsigned:
        i = "unsigned " + i
    r = toCTypes.get(i, i.replace("?_", "").replace(" ", "_"))
    P = t.pstack[:]
    if r in ("c_void", "c_char", "c_wchar") and t.is_ptr:
        if P[0].is_ptr:
            r = r + "_p"
            P.pop(0)
    if r == "c_void":
        r = None
    elif hasattr(ctypes, r):
        r = getattr(ctypes, r)
    else:
        try:
            r = Types[r]
        except KeyError:
            if not conf.QUIET:
                secho("type {} not in database ? (replaced by int)".format(r), fg="red")
            r = ctypes.c_int
    while P:
        p = P.pop(0)
        if p.is_ptr:
            for _ in p.p:
                r = ctypes.POINTER(r)
        elif isinstance(p, fargs):
            r = formatproto(r, p, Types)
            if len(P) > 0:
                x = P.pop(0)
                assert x.is_ptr
                r = ctypes.POINTER(r)
        else:
            r = r * p.a
    return r


def formatproto(res, proto, Types):
    params = filter(None, [mk_ctypes(get_c_or_cxx_type(t), Types) for t in proto.args])
    return ctypes.CFUNCTYPE(res, *params)

def get_c_or_cxx_type(x):
    if not ('&' in x):
        try:
            t = c_type(x)
        except pp.ParseException:
            pass
        else:
            return t
    t = cxx_type(x)
    return t

def build(obj, db, Types={}, _bstack=[]):
    if obj._is_class:
        x = obj.as_cStruct(db)
        x.unfold(db)
        return build(x, db, Types, _bstack)
    x = str(obj.identifier.replace("?_", "").replace(" ", "_"))
    if x in Types:
        return Types[x]
    early_exit = False
    if obj.identifier in _bstack:
        if obj._is_struct or obj._is_union:
            early_exit = True
    _bstack.append(obj.identifier)
    if obj.subtypes is None:
        obj.unfold(db)
    for subtype in obj.subtypes.values() or []:
        if early_exit or (subtype is None):
            continue
        build(subtype, db, Types, _bstack)
    if obj._is_typedef:
        t = get_c_or_cxx_type(obj)
        Types[obj.identifier] = mk_ctypes(t, Types)
        _bstack.pop()
        return Types[obj.identifier]
    if obj._is_macro:
        _bstack.pop()
        v = obj.strip()
        try:
            v = int(v, base=0)
        except ValueError:
            try:
                t = mk_ctypes(get_c_or_cxx_type(v),Types)
            except pp.ParseException:
                globals()[obj.identifier] = v
                return v
            else:
                Types[obj.identifier] = t
                return Types[obj.identifier]
        else:
            return v
    if obj._is_enum:
        if len(obj) < 256:
            Types[x] = ctypes.c_byte
        elif len(obj) < (1 << 16):
            Types[x] = ctypes.c_short
        else:
            Types[x] = ctypes.c_int
        globals()[x] = {}.update(obj)
    elif obj._is_func:
        Types[x] = mk_ctypes(get_c_or_cxx_type(obj["prototype"]), Types)
    elif obj._is_struct or obj._is_union:
        parent = ctypes.Structure
        if obj._is_union:
            parent = ctypes.Union
        Types[x] = type(x, (parent,), {})
        if not early_exit:
            fmt = []
            anon = []
            for t, n, c in iter(obj):
                r = get_c_or_cxx_type(t)
                if "?_" in r.lbase:
                    if r.lbase.startswith("struct ") or r.lbase.startswith("union "):
                        anon.append(n)
                if not n and not r.lbase.startswith("union "):
                    continue
                bfw = r.lbfw
                r = mk_ctypes(r, Types)
                if bfw > 0:
                    fmt.append((str(n), r, bfw))
                else:
                    fmt.append((str(n), r))
            if len(anon) > 0:
                Types[x]._anonymous_ = tuple(anon)
            Types[x]._fields_ = fmt
    else:
        raise NotImplementedError
    _bstack.pop()
    return Types[x]
