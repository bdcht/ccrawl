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
            r = ctypes.POINTER(r)
        else:
            r = r * p.a
    return r

def formatproto(res,proto,Types):
    params = [mk_ctypes(c_type(x),Types) for x in proto.args]
    params.insert(0,res)
    return ctypes.CFUNCTYPE(*params)

def build(obj,db,Types={}):
    for subtype in (obj.subtypes.values() or []):
        if subtype is None: continue
        build(subtype,db,Types)
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
    elif obj._is_struct or obj._is_union:
        parent = ctypes.Structure
        if obj._is_union: parent = ctypes.Union
        Types[x] = type(x,(parent,),{})
        fmt = []
        anon = []
        for t,n,c in obj:
            if not n: continue
            r = c_type(t)
            if '?_' in r.lbase:
                anon.append(n)
            bfw = r.lbfw
            r = mk_ctypes(r,Types)
            if bfw>0: fmt.append((str(n),r,bfw))
            else:     fmt.append((str(n),r))
        if len(anon)>0:
            Types[x]._anonymous_ = tuple(anon)
        Types[x]._fields_ = fmt
    elif obj._is_class:
        x = obj.as_cStruct(db)
        x.unfold(db)
        return build(x,db)
    else:
        raise NotImplementedError
    return Types[x]
