from collections import OrderedDict
from ccrawl.utils import *
from ccrawl import conf
from click import secho
from tinydb import Query, where

toCTypes = {
    'void'               : 'c_void',
    '_Bool'              : 'c_bool',
    'char'               : 'c_char',
    'wchar_t'            : 'c_wchar',
    'char'               : 'c_byte',
    'unsigned char'      : 'c_ubyte',
    'short'              : 'c_short',
    'unsigned short'     : 'c_ushort',
    'int'                : 'c_int',
    'unsigned int'       : 'c_uint',
    'long'               : 'c_long',
    'unsigned long'      : 'c_ulong',
    'float'              : 'c_float',
    'double'             : 'c_double',
    'ssize_t'            : 'c_ssize_t',
    'size_t'             : 'c_size_t',
    'long long'          : 'c_longlong',
    '__int64'            : 'c_longlong',
    'unsigned long long' : 'c_ulonglong',
    'unsigned __int64'   : 'c_ulonglong',
}

def id_ctypes(t):
    i = t.lbase
    if t.lunsigned: i = 'unsigned '+i
    r = toCTypes.get(i, i.replace('?_','').replace(' ','_'))
    P = t.pstack[:]
    if r in ('c_void','c_char','c_wchar') and t.is_ptr:
        if P[0].is_ptr:
            r = r+'_p'
            P.pop(0)
    while P:
        p = P.pop(0)
        if p.is_ptr:
            for x in p.p:
                r = 'POINTER(%s)'%r
        elif isinstance(p,fargs):
            r = formatproto(r,p)
            x = P.pop(0)
            assert x.is_ptr
            r = 'POINTER(%s)'%r
        else:
            r = '%s*%d'%(r,p.a)
    if r=='c_void': return 'None'
    return r

def formatproto(res,proto):
    f = 'CFUNCTYPE'
    params = [id_ctypes(c_type(x)) for x in proto.args]
    if res=='c_void': res='None'
    params.insert(0,res)
    return '{}({})'.format(f,', '.join(params))

def cTypedef_ctypes(obj,db,recursive):
    pre = ''
    t = c_type(obj)
    if isinstance(recursive,set) and (t.lbase not in struct_letters):
        Q = (where('id')==t.lbase)
        if db.contains(Q):
            x = obj.from_db(db.get(Q))
            pre = x.show(db,recursive,form='ctypes')
            pre += '\n\n'
        else:
            secho("identifier %s not found"%t.lbase,fg='red',err=True)
    return u'{}{} = {}'.format(pre, obj.identifier, id_ctypes(t))

def cMacro_ctypes(obj,db,recursive):
    v = obj.strip()
    try:
        v = int(v,base=0)
    except ValueError:
        v = v
    return '{} = {}'.format(obj.identifier,v)

def cFunc_ctypes(obj,db,recursive):
    f = 'CFUNCTYPE'
    pre = ''
    res = obj.restype()
    args = obj.argtypes()
    if isinstance(recursive,set):
        for t in [res]+args:
            t = c_type(t)
            if t.lbase not in struct_letters:
                Q = (where('id')==t.lbase)
                if db.contains(Q):
                    x = obj.from_db(db.get(Q))
                    pre = x.show(db,recursive,form='ctypes')
                    pre += '\n\n'
                else:
                    secho("identifier %s not found"%t.lbase,fg='red',err=True)
    params = [id_ctypes(c_type(x)) for x in args]
    res = id_ctypes(c_type(res))
    if res=='c_void': res='None'
    params.insert(0,res)
    return '{} = {}({})'.format(obj.identifier,f,', '.join(params))

def cEnum_ctypes(obj,db,recursive):
    n = obj.identifier.replace(' ','_')
    S = ['{} = c_int'.format(n)]
    S.extend(('{} = {}'.format(k,v) for (k,v) in obj.items()))
    return '\n'.join(S)

def cStruct_ctypes(obj,db,recursive):
    if isinstance(recursive,set):
        Q = True
        recursive.update(struct_letters)
    else:
        Q = None
    name = id_ctypes(c_type(obj.identifier))
    cls = 'Union' if obj._is_union else 'Structure'
    R = ["{0} = type('{0}',({1},),{{}})\n".format(name,cls)]
    S = []
    fld = '%s._fields_ = ['%name
    S.append(fld)
    pad = ' '*len(fld)
    padded = False
    for i in obj:
        t,n,c = i
        if not n: continue
        r = c_type(t)
        if Q and (r.lbase not in recursive):
            if r.lbase == obj.identifier:
                recursive.add(r.lbase)
            else:
                q = (where('id')==r.lbase)
                if '?_' in r.lbase:
                    q &= (where('src')==obj.identifier)
                if db.contains(q):
                    x = obj.from_db(db.get(q)).show(db,recursive,form='ctypes')
                    x = x.split('\n')
                    for xrl in x:
                        if (xrl+'\n' in R) and not xrl.startswith(' '):
                            continue
                        if xrl: R.append(xrl+'\n')
                    recursive.add(r.lbase)
                else:
                    secho('identifier %s not found'%r.lbase,fg='red',err=True)
        t = id_ctypes(r)
        S.append('("{}", {}),\n'.format(n,t)+pad)
        padded = True
    if padded: S.append(S.pop().strip()[:-1])
    S.append(']')
    return ''.join(R)+'\n'+''.join(S)

cUnion_ctypes = cStruct_ctypes

def cClass_ctypes(obj,db,recursive):
    # recursive is forced for c++ classes
    if not isinstance(recursive,set):
        recursive = set()
        recursive.update(struct_letters)
    return cStruct_ctypes(obj.as_cStruct(db),db,recursive)
