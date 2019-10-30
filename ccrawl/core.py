from ccrawl import formatters
from ccrawl.utils import *

class ccore(object):
    """ Generic class dedicated to a collected object
    used as parent of all types"""
    _is_typedef   = False
    _is_struct    = False
    _is_union     = False
    _is_enum      = False
    _is_macro     = False
    _is_func      = False
    _is_class     = False
    _is_template  = False
    _is_namespace = False
    formatter     = None
    _cache_       = {}

    def show(self,db=None,r=None,form=None):
        if (not self.formatter) or form:
            self.set_formatter(form)
        return self.formatter(db,r)

    def unfold(self,db,limit=None):
        self.subtypes = []
        return self

    def add_subtype(self,db,elt,limit=None):
        x = ccore._cache_.get(elt,None)
        if x is None:
            data = db.get(id=elt)
            if data:
                x = ccore.from_db(data)
                ccore._cache_[elt] = x
            else:
                self.subtypes.append(None)
                return
        self.subtypes.append(x.unfold(db,limit))

    @classmethod
    def set_formatter(cls,form):
        ff = '{}_{}'.format(cls.__name__,form)
        try:
            cls.formatter = getattr(formatters,ff)
        except AttributeError:
            cls.formatter = formatters.default

    @staticmethod
    def getcls(name):
        if name == 'cTypedef'   : return cTypedef
        if name == 'cStruct'    : return cStruct
        if name == 'cUnion'     : return cUnion
        if name == 'cEnum'      : return cEnum
        if name == 'cMacro'     : return cMacro
        if name == 'cFunc'      : return cFunc
        if name == 'cClass'     : return cClass
        if name == 'cTemplate'  : return cTemplate
        if name == 'cNamespace' : return cNamespace

    def to_db(self,identifier,tag,src):
        doc = {'id':identifier,
               'val':self,
               'cls':self.__class__.__name__,
               'src':src}
        if tag: doc['tag'] = tag
        data = [doc]
        if hasattr(self,'local'):
            for i,x in iter(self.local.items()):
                data.extend(x.to_db(i,tag,identifier))
        return data

    @staticmethod
    def from_db(data):
        identifier = data['id']
        val = ccore.getcls(data['cls'])(data['val'])
        val.identifier = identifier
        val.subtypes = None
        return val

class cTypedef(str,ccore):
    _is_typedef = True
    def unfold(self,db,limit=None,ctx=None):
        if self.subtypes is None:
            self.subtypes = []
            ctype = c_type(self)
            if limit!=None:
                if limit<=0 and ctype.is_ptr:
                    return self
            elt = ctype.lbase
            if elt not in struct_letters:
                if limit: limit-=1
                self.add_subtype(db,elt,limit)
        return self

class cStruct(list,ccore):
    _is_struct = True
    def unfold(self,db,limit=None):
        if self.subtypes is None:
            self.subtypes = []
            T = list(struct_letters.keys())
            T.append(self.identifier)
            for (t,n,c) in self:
                ctype = c_type(t)
                if limit!=None:
                    if limit<=0 and ctype.is_ptr:
                        continue
                elt = ctype.lbase
                if (elt not in T):
                    T.append(elt)
                    if limit: limit-=1
                    self.add_subtype(db,elt,limit)
        return self

class cClass(list,ccore):
    _is_class = True
    def unfold(self,db,limit=None):
        if self.subtypes is None:
            self.subtypes = []
            T = list(struct_letters.keys())
            T.append(self.identifier)
            for (t,N,a,c) in self:
                raise NotImplementedError
        return self

class cUnion(list,ccore):
    _is_union = True
    def unfold(self,db,limit=None):
        if self.subtypes is None:
            self.subtypes = []
            T = list(struct_letters.keys())
            T.append(self.identifier)
            for (t,n,c) in self:
                ctype = c_type(t)
                if limit!=None:
                    if limit<=0 and ctype.is_ptr:
                        continue
                elt = ctype.lbase
                if (elt not in T):
                    T.append(elt)
                    if limit: limit-=1
                    self.add_subtype(db,elt,limit)
        return self

class cEnum(dict,ccore):
    _is_enum = True

class cMacro(str,ccore):
    _is_macro = True

class cFunc(str,ccore):
    _is_func = True
    def restype(self):
        t = c_type(self)
        t.pstack.pop()
        return t.show()
    def argtypes(self):
        t = c_type(self)
        return t.pstack[-1].args
    def unfold(self,db,limit=None):
        if self.subtypes is None:
            self.subtypes = []
            T = list(struct_letters.keys())
            rett = self.restype()
            args = self.argtypes()
            args.insert(0,rett)
            for t in args:
                elt = c_type(t).lbase
                if (elt not in T):
                    T.append(elt)
                    self.add_subtype(db,elt)
        return self

class cTemplate(dict,ccore):
    _is_template = True

    def get_basename(self):
        if self.get('partial_specialization',False):
            return self.identifier
        i = self.identifier.rfind('<')
        assert i>0
        return self.identifier[:i]
    def get_template(self):
        return '<%s>'%(','.join(self['params']))

class cNamespace(list,ccore):
    _is_namespace = True
    def unfold(self,db,limit=None):
        if self.subtypes is None:
            self.subtypes = []
            T = list(struct_letters.keys())
            T.append(self.identifier)
            for elt in self:
                self.add_subtype(db,elt)
        return self

