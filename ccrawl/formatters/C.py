from tinydb import Query, where
from click import secho
from ccrawl.utils import *

# C formatters:
#------------------------------------------------------------------------------

def cTypedef_C(obj,db,recursive):
    pre = ''
    t = c_type(obj)
    if isinstance(recursive,set) and (t.lbase not in struct_letters):
        Q = (where('id')==t.lbase)
        if db.contains(Q):
            x = obj.from_db(db.get(Q))
            pre = x.show(db,recursive,form='C')+'\n'
    if recursive and '?_' in t.lbase:
        pre = pre.split('\n\n')
        t.lbase = pre.pop().strip()
        pre.append('')
        pre = '\n\n'.join(pre)
    return u'{}typedef {};'.format(pre,t.show(obj.identifier))

def cMacro_C(obj,db,recursive):
    return u'#define {} {};'.format(obj.identifier,obj)

def cFunc_C(obj,db,recursive):
    fptr = c_type(obj)
    return fptr.show(obj.identifier)+';'

def cEnum_C(obj,db,recursive):
    S = []
    for k,v in sorted(obj.items(),key=lambda t:t[1]):
        S.append('  {} = {:d}'.format(k,v))
    S = ',\n'.join(S)
    return u"%s {\n%s\n};"%(obj.identifier,S)

def cStruct_C(obj,db,recursive):
    #prepare query if recursion is needed:
    if isinstance(recursive,set):
        Q = True
        recursive.update(struct_letters)
    else:
        Q = None
    #declare structure:
    name = obj.identifier
    tn = 'union ' if obj._is_union else 'struct '
    #if anonymous, remove anonymous name:
    if '?_' in name:
        name = tn
    #R holds recursive definition strings needed for obj
    R = []
    #S holds obj title and fields declaration strings
    S = [u'%s {'%name]
    #iterate through all fields:
    for i in obj:
        #get type, name, comment:
        if obj._is_struct:
            t,n,c = i
        elif obj._is_union:
            n,tc = i,obj[i]
            t,c  = tc
        #decompose C-type t into specific parts:
        r = c_type(t)
        #get "element base" part of type t:
        e = r.lbase
        #query field element raw base type if needed:
        if Q and (r.lbase not in recursive):
            # check if querying the current struct type...
            if r.lbase == obj.identifier:
                #insert pre-declaration of struct
                R.insert(0,'%s;'%r.lbase)
                recursive.add(r.lbase)
            else:
                #prepare query
                q = (where('id')==r.lbase)
                #deal with anonymous type:
                if '?_' in r.lbase:
                    q &= (where('src')==obj.identifier)
                if db.contains(q):
                    #retreive the field type:
                    x = obj.from_db(db.get(q)).show(db,recursive,form='C')
                    if not '?_' in r.lbase:
                        #if not anonymous, insert it directly in R
                        R.insert(0,x)
                        recursive.add(r.lbase)
                    else:
                        # anonymous struct/union: we need to transfer
                        # any predefs into R
                        x = x.split('\n\n')
                        r.lbase = x.pop().replace('\n','\n  ').strip(';')
                        if len(x):
                            xr = x[0].split('\n')
                            for xrl in xr:
                                if xrl and xrl not in R: R.insert(0,xrl)
                else:
                    secho('identifier %s not found'%r.lbase,fg='red')
        #finally add field type and name to the structure lines:
        S.append(u'  {};'.format(r.show(n)))
    #join R and S:
    if len(R)>0: R.append('\n')
    S.append('};')
    return '\n'.join(R)+'\n'.join(S)

cUnion_C = cStruct_C
