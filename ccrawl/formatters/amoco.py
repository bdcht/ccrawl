#from amoco.system import structs
from ccrawl.utils import *
from ccrawl import conf
from click import secho
from tinydb import Query, where

tostruct = {
    'void'               : 'x',
    '_Bool'              : '?',
    'char'               : 'c',
    'unsigned char'      : 'B',
    'short'              : 'h',
    'unsigned short'     : 'H',
    'int'                : 'i',
    'unsigned int'       : 'I',
    'long'               : 'l',
    'unsigned long'      : 'L',
    'float'              : 'f',
    'ssize_t'            : 'n',
    'size_t'             : 'N',
    'double'             : 'd',
    'long long'          : 'q',
    'unsigned long long' : 'Q',
}

def id_amoco(s):
    return s.replace('?_','').replace(' ','_')

def fieldformat(r):
    t = r.lbase
    if r.is_ptr:
        rt = 'P'
    else:
        rt = tostruct.get(t,None)
    if rt is None:
        t = id_amoco(t)
    if r.dim>0:
        if rt=='x': raise TypeError(r)
        if rt in ('c','B'): rt='s'
        if rt:
            rt = '{} * {:d}'.format(rt,r.dim)
        else:
            t = '{} * {:d}'.format(t,r.dim)
    return rt,t

def cTypedef_amoco(obj,db,recursive):
    pre = ''
    t = c_type(obj)
    if isinstance(recursive,set) and (t.lbase not in tostruct):
        Q = (where('id')==t.lbase)
        if db.contains(Q):
            x = obj.from_db(db.get(Q))
            pre = x.show(db,recursive,form='amoco')
            pre += '\n\n'
        else:
            secho("identifier {} not found".format(t.lbase),fg="red")
    rn,n = fieldformat(t)
    return u"{}TypeDefine('{}','{}')".format(pre,obj.identifier, rn or n)

def cMacro_amoco(obj,db,recursive):
    v = obj.strip()
    try:
        v = int(v,base=0)
        return '{} = 0x{:x}'.format(obj.identifier,v)
    except ValueError:
        v = v
    return "{} = '{}'".format(obj.identifier,v)

def cFunc_amoco(obj,db,recursive):
    pass

def cEnum_amoco(obj,db,recursive):
    n = obj.identifier.replace(' ','_')
    s = ["TypeDefine('{}','i')".format(n)]
    s.extend(('{} = {}'.format(k,v) for (k,v) in obj.items()))
    return '\n'.join(s)

def cStruct_amoco(obj,db,recursive):
    if isinstance(recursive,set):
        Q = True
        recursive.update(tostruct)
    else:
        Q = None
    name = id_amoco(obj.identifier)
    cls = 'UnionDefine' if obj._is_union else 'StructDefine'
    R = []
    S = ['@{}("""\n'.format(cls)]
    for i in obj:
        if obj._is_struct:
            t,n,c = i
        elif obj._is_union:
            n,tc = i,obj[i]
            t,c  = tc
        r = c_type(t)
        if Q and (r.lbase not in recursive):
            if r.lbase == obj.identifier:
                recursive.add(r.lbase)
            else:
                q = (where('id')==r.lbase)
                if r.lbase.startswith('?_'):
                    q &= (where('src')==obj.identifier)
                if db.contains(q):
                    x = obj.from_db(db.get(q))
                    if x._is_typedef:
                        pass
                    x = x.show(db,recursive,form='amoco')
                    x = x.split('\n')
                    for xrl in x:
                        if xrl: R.append(xrl+'\n')
                    recursive.add(r.lbase)
                else:
                    secho('identifier %s not found'%r.lbase,fg='red')
        rt,t = fieldformat(r)
        if rt: t = rt
        S.append('{} : {} ;{}\n'.format(t,n,c or ''))
    if len(R)>0: R.append('\n')
    S.append('""")\nclass %s(StructFormatter):'%name)
    # add methods:
    S.append("""
    def __init__(self,data="",offset=0):
        if data: self.unpack(data,offset)
    """)
    return ''.join(R)+''.join(S)

cUnion_amoco = cStruct_amoco

