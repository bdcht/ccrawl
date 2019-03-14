from click import echo,secho
from ccrawl import conf
from ccrawl.formatters.ctypes_ import toCTypes
from ccrawl.utils import c_type,fargs
import ctypes

def mk_ctypes(t,Types):
    i = t.lbase
    if t.lunsigned: i = 'unsigned '+i
    r = toCTypes.get(i, i.replace('?_','').replace(' ','_'))
    P = t.pstack[:]
    if r in ('c_void','c_char','c_wchar') and t.is_ptr:
        if P[0].is_ptr:
            r = r+'_p'
            P.pop(0)
    if r=='c_void':
        r = None
    elif hasattr(ctypes,r):
        r = getattr(ctypes,r)
    else:
        r = Types[r]
    while P:
        p = P.pop(0)
        if p.is_ptr:
            for x in p.p:
                r = ctypes.POINTER(r)
        elif isinstance(p,fargs):
            r = formatproto(r,p,Types)
            x = P.pop(0)
            assert x.is_ptr
        else:
            r = r * p.a
    return r

def formatproto(res,proto,Types):
    params = [mk_ctypes(c_type(x),Types) for x in proto.args]
    params.insert(0,res)
    return ctypes.CFUNCTYPE(*params)

def build(obj,Types={}):
    for subtype in obj.subtypes:
        build(subtype,Types)
    if obj._is_typedef:
        t = c_type(obj)
        Types[obj.identifier] = mk_ctypes(t,Types)
        return Types[obj.identifier]
    if obj._is_macro:
        v = obj.strip()
        try:
            v = int(v,base=0)
        except ValueError:
            v = v
        globals()[obj.identifier] = v
        return v
    x = str(obj.identifier.replace('?_','').replace(' ','_'))
    if obj._is_enum:
        Types[x] = ctypes.c_int
        globals()[x] = {}.update(obj)
    elif obj._is_struct:
        Types[x] = type(x,(ctypes.Structure,),{})
        fmt = []
        for t,n,c in obj:
            r = c_type(t)
            r = mk_ctypes(r,Types)
            fmt.append((str(n),r))
        Types[x]._fields_ = fmt
    elif obj._is_union:
        Types[x] = type(x,(ctypes.Union,),{})
        fmt = []
        for n,tc in obj.items():
            t,c = tc
            r = c_type(t)
            r = mk_ctypes(r,Types)
            fmt.append((str(n),r))
        Types[x]._fields_ = fmt
    else:
        raise NotImplementedError
    return Types[x]
