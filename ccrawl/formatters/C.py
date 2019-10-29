from click import secho
from ccrawl.utils import *
from tinydb import where

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
        else:
            secho('identifier %s not found'%t.lbase,fg='red')
    # if t base is an anonymous type, we replace is anon name
    # by its struct/union definition in t:
    if recursive and '?_' in t.lbase:
        pre = pre.split('\n\n')
        t.lbase = pre.pop().strip(';\n')
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
        t,n,c = i
        if not n: continue
        #decompose C-type t into specific parts:
        r = c_type(t)
        #get "element base" part of type t:
        e = r.lbase
        #query field element base type if recursive:
        if Q and (r.lbase not in recursive):
            # check if we are about to query the current struct type...
            if r.lbase == obj.identifier:
                #insert pre-declaration of struct
                #R.insert(0,'%s;'%r.lbase)
                R.append('%s;'%r.lbase)
                recursive.add(r.lbase)
            else:
                #prepare query
                #(deal with the case of querying an anonymous type)
                q = (where('id')==r.lbase)
                if '?_' in r.lbase:
                    q &= (where('src')==obj.identifier)
                #do the query and update R:
                if db.contains(q):
                    #retreive the field type:
                    x = obj.from_db(db.get(q)).show(db,recursive,form='C')
                    if not '?_' in r.lbase:
                        #if not anonymous, insert it directly in R
                        #R.insert(0,x)
                        R.append(x)
                        recursive.add(r.lbase)
                    else:
                        # anonymous struct/union: we need to transfer
                        # any predefs into R
                        x = x.split('\n\n')
                        r.lbase = x.pop().replace('\n','\n  ').strip(';')
                        if len(x):
                            xr = x[0].split('\n')
                            for xrl in xr:
                                if xrl and xrl not in R:
                                    #R.insert(0,xrl)
                                    R.append(xrl)
                else:
                    secho('identifier %s not found'%r.lbase,fg='red')
        #finally add field type and name to the structure lines:
        S.append(u'  {};'.format(r.show(n)))
    #join R and S:
    if len(R)>0: R.append('\n')
    S.append('};')
    return '\n'.join(R)+'\n'.join(S)

cUnion_C = cStruct_C

def cClass_C(obj,db,recursive):
    # get the cxx type object, for namespaces:
    tn = cxx_type(obj.identifier)
    namespace = tn.show_base(kw=False,ns=False)
    #prepare query if recursion is needed:
    if isinstance(recursive,set):
        Q = True
        recursive.update(struct_letters)
        recursive.add(tn.lbase)
    else:
        Q = None
    #R holds recursive definition strings needed for obj
    R = []
    #S holds obj title and fields declaration strings
    S = [u'%s {'%(tn.show())]
    P = {'':[],'PUBLIC':[], 'PROTECTED':[], 'PRIVATE':[]}
    #iterate through all fields:
    for (x,y,z) in obj:
        qal,t = x # parent/virtual qualifier & type
        mn,n  = y # mangled name & name
        p,c   = z # public/protected/private & comment
        if qal == 'parent':
            r = cxx_type(n)
            e = r.lbase
            S[0] = S[0][:-1]+': %s {'%(r.show_base())
            if Q and (e not in recursive):
                q = (where('id')==e)
                x = obj.from_db(db.get(q)).show(db,recursive,form='C')
                R.append(x)
                recursive.add(e)
            continue
        elif qal == 'using':
            what = '::'.join((cxx_type(u).show_base() for u in t))
            using = '  using %s'%what
            using +='::%s;'%n if n!=namespace else ';'
            S.append(using)
            continue
        #decompose C-type t into specific parts:
        r = cxx_type(t)
        #get "element base" part of type t:
        e = r.lbase
        #query field element raw base type if needed:
        nested = r.ns.startswith(namespace)
        if Q and ((e not in recursive) or nested):
            #prepare query
            q = (where('id')==e)
            #deal with nested type:
            if nested:
                q &= (where('src')==tn.lbase)
            if db.contains(q):
                #retreive the field type:
                x = obj.from_db(db.get(q)).show(db,recursive,form='C')
                if not nested:
                    #if not nested, insert it directly in R
                    R.append(x)
                    recursive.add(e)
                else:
                    x = x.replace('%s::'%namespace,'')
                    # nested struct/union/class: we need to transfer
                    # any predefs into R
                    x = x.split('\n\n')
                    r.lbase = x.pop().replace('\n','\n    ').strip(';')
                    if len(x):
                        xr = x[0].split('\n')
                        for xrl in xr:
                            if xrl and xrl not in R:
                                R.append(xrl)
            else:
                secho('identifier %s not found'%r.lbase,fg='red')
        #finally add field type and name to the structure lines:
        fo = ''
        if qal:
            if ',' in qal: qal,fo = qal.split(',')
            qal = '%s '%qal
        P[p].append(u'    {}{}{};'.format(qal,r.show(n,kw=nested),fo))
    # access specifier (empty is for friend members):
    for p in ('PUBLIC','PROTECTED','PRIVATE',''):
        if len(P[p])>0:
            if p: S.append('  %s:'%p.lower())
            for v in P[p]:
                S.append(v)
    #join R and S:
    if len(R)>0: R.append('\n')
    S.append('};')
    return '\n'.join(R)+'\n'.join(S)

def cTemplate_C(obj,db,recursive):
    # get the cxx type object, for namespaces:
    tn = cxx_type(obj.identifier)
    namespace = tn.show_base(kw=False,ns=False)
    #prepare query if recursion is needed:
    if isinstance(recursive,set):
        Q = True
        recursive.update(struct_letters)
        recursive.add(tn.lbase)
    else:
        Q = None
