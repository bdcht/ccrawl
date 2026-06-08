from functools import cache
from collections import OrderedDict
from itertools import pairwise
from re import escape
from ccrawl.utils import pp, struct_letters, c_type_instance, c_type, cxx_type
from ccrawl.db import where,Query

class ccore(object):
    """
    Generic class dedicated to a collected object,
    used as parent class for all C/C++ items collected
    by ccrawl:

      - typedef
      - struct
      - union
      - enum
      - macro
      - func
      - class     (c++)
      - template  (c++)
      - namespace (c++)
      - alias     (c++)

    Attributes:
        formatter (function): a function used to print the object
                              in various formats.
        _cache_ (dict): a global (parent class level) dict of all types
                        that have been fetched from the database so far.
    """

    _is_typedef = False
    _is_struct = False
    _is_union = False
    _is_enum = False
    _is_macro = False
    _is_func = False
    _is_class = False
    _is_template = False
    _is_namespace = False
    formatter = None
    _cache_ = {}

    def show(self, db=None, form=None):
        """
        Generic method that possibly defines and
        ultimately calls the internal formatter function.

        Attributes:
            db [opt] (Proxy): database used for recursive mode
            form [opt] (str): name of the chosen formatter module
        """
        if (not self.formatter) or form:
            self.set_formatter(form)
        return self.formatter(db)

    def unfold(self, db, ctx=None):
        """
        Generic method that fetches recursively from the given database
        all other types on which this type depends. The method is recursive
        in the sense that all subtypes are unfolded as well until they only
        depend on primitive types (int, short, float, etc.)
        """
        self.subtypes = OrderedDict()
        return self

    def build(self, db):
        """
        Generic method for building a ctypes instance for this type.
        Basically just a wrapper for the :mod:`ctypes_.build` function.

        Parameters:
            db (Proxy): database used to get any other type on which
                        this type depends.
        """
        self.unfold(db)
        from ccrawl.ext import ctypes_

        return ctypes_.build(self, db)

    def add_subtype(self, db, elt, ctx):
        """
        Generic method that fetches item 'elt' from the database and
        adds it to the subtypes of this type before unfolding it.
        (takes into account the namespaces and templates that possibly describe
        this underlying type in c++.)
        """
        if elt not in ctx:
            xt = cxx_type(elt)
            t = xt.show_base(kw=False,ns=False,tp=False)
            # we start by adding the needed namespace(s).
            # This is needed because a namespace could actually be a
            # type or template-specialization in which case we wont
            # necessary get them from just unfolding our base type.
            for e in xt.ns:
                self.add_subtype(db, e, ctx)
                last_ns = ctx[e]
                while last_ns and last_ns._is_typedef:
                    last_ns = last_ns.subtypes[str(last_ns)]
            # let's search at least for the most basic typename:
            # but allow any keywords and namespace:
            r = r"(?:(?:class|struct|enum)\s+)?(?:.*::)?%s"%escape(t)
            if xt.tp:
                # add any template args if we are searching for a template
                # or fully specialized class
                r += r"(?:<.*>)$"
                Q = where("cls").one_of(("cTemplate","cClass"))
                Q &= where("id").matches(r)
                for e in (arg for arg in xt.tp.args if str(arg) not in ctx):
                    if isinstance(e.value,c_type_instance):
                        et = e.value.show_base(kw=True,ns=True)
                        self.add_subtype(db, et, ctx)
            else:
                r += r"(?:<.*>)?$"
                Q = where("id").matches(r)
            L = db.search(Q)
            data = None
            candidates = []
            # now we want the best match...
            for e in L:
                et = cxx_type(e['id'])
                # any exact match wins the race:
                if et == xt:
                    candidates = [e]
                    break
                # skip template args count mismatch:
                etpargs = et.tp_args()
                if xt.tp and len(xt.tp.args)!=len(etpargs):
                    if not etpargs or etpargs[-1].endswith('...'):
                        continue
                if e["cls"]=="cTemplate":
                    c = e["val"].get("cClass",[])
                    if len(c)==0:
                        # skip func- or primary- template declarations
                        continue
                    candidates.append(e)
                else:
                    # full spec (classes) are prepended to have
                    # higher priority:
                    if xt.tp:
                        candidates.insert(0,e)
            if len(candidates)>1:
                # if we have several candidates, probably template-based,
                # we have to choose the correct specialisation...
                # TODO
                pass
            for data in candidates:
                break
            if data:
                x = ccore.from_db(data)
                ctx[elt] = x
                # add variant w/o keyword w/namespace etc
                ctx[xt.show_base(kw=False,ns=True)] = x
                # add name from the exact identifier found in db
                et = cxx_type(x.identifier)
                ctx[et.show_base(kw=False,ns=True)] = x
                # also add the bare template name to cache:
                if x._is_template and not x["partial_specialization"]:
                    ctx[et.show_base(kw=False,ns=True,tp=False)] = x
                if not x._is_namespace:
                    self.subtypes[elt] = x.unfold(db, ctx)
            else:
                ctx[elt] = {}
                self.subtypes[elt] = None
        else:
            ctx.move_to_end(elt)
            self.subtypes[elt] = ctx[elt]

    def graph(self,db,V=None,g=None):
        """
        Generic method that returns the types-dependency graph
        associated with this type.
        Basically just a wrapper for the graphs.build function.

        Parameters:
            db (Proxy): database used to get any other type on which
                        this type depends.
        """
        from ccrawl.graphs import build
        return build(self,db,V,g)

    @classmethod
    def set_formatter(cls, form):
        """
        Selects the formatter to be used for the entire class from
        the available :mod:`formatters`.

        Parameters:
            form (str): name of a module in the formatters sub-package.
                        If the module is not found, 'raw' is used.
        """
        ff = "{}_{}".format(cls.__name__, form)
        from ccrawl import formatters
        try:
            cls.formatter = getattr(formatters, ff)
        except AttributeError:
            cls.formatter = formatters.default

    @staticmethod
    def getcls(name):
        match name:
            case "cTypedef"  : return cTypedef
            case "cStruct"   : return cStruct
            case "cUnion"    : return cUnion
            case "cEnum"     : return cEnum
            case "cMacro"    : return cMacro
            case "cFunc"     : return cFunc
            case "cClass"    : return cClass
            case "cTemplate" : return cTemplate
            case "cNamespace": return cNamespace
            case "cTypealias": return cTypealias

    def to_db(self, identifier, tag, src):
        """
        Generic method that returns a list of database-insertable "documents"
        for the current item.
        """
        doc = {
            "id": identifier,
            "val": self,
            "cls": self.__class__.__name__,
            "src": src,
        }
        if tag:
            doc["tag"] = tag
        data = [doc]
        if hasattr(self, "local"):
            try:
                ns = cxx_type(identifier)
                lsrc = "%s::%s"%(src,ns.show(kw=False))
            except Exception:
                lsrc = "%s::"%src
            for i, x in self.local.items():
                if x:
                    data.extend(x.to_db(i, tag, lsrc))
        return data

    @staticmethod
    def from_db(data):
        """
        Generic method that returns a specialized ccore instance from a given
        document data usually obtained from the database.

        Parameters:
            data (dict): must have "id", "cls" and "val" keys where cls is
                         one of the below ccore specialized class name.
        """
        identifier = data["id"]
        val = ccore.getcls(data["cls"])(data["val"])
        val.identifier = identifier
        val.subtypes = None
        val.tag = data["tag"]
        par = data["src"].find("::")
        val.ns = data["src"][par+2:] if par>0 else ""
        val.src = data["src"]
        return val


# ------------------------------------------------------------------------------


class cTypedef(str, ccore):
    """
    Specialized ccore class that is also a 'str' representing a C/C++ typedef.
    
    Attributes:
        identifier: the new typename associated to this typedef.
    """
    _is_typedef = True

    def unfold(self, db, ctx=None):
        """
        Unfolding a typedef simply adds its underlying type definition to subtypes.
        """
        ctx = ctx or OrderedDict(struct_letters)
        ctx[self.identifier] = self
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            ctype = cxx_type(self) # cxx_type is a child of c_type
            elt = ctype.show_base(kw=True,ns=True)
            # add_subtype is always given the more complete elt string
            # incuding keyword, namespace and/or template. It will
            # manage to fill the ctx with variants
            self.add_subtype(db, elt, ctx)
        return self

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))


class cTypealias(cTypedef):
    """A c++ "using" alias declaration is nothing more than a typedef."""
    pass


# ------------------------------------------------------------------------------


class cStruct(list, ccore):
    """
    Specialized ccore class that is also a 'list' representing a C struct.

    Attributes:
        identifier: the typename associated to this C struct.

    Items of the list represent fields of the structure and are formatted as
    triplet of the form (t,n,c) where
    
       - t is a string that represents the type the field
       - n is a string that represents the name of the field
       - c is a string that represents a comment for the field
    """
    _is_struct = True

    def unfold(self, db, ctx=None):
        """
        Unfolding a struct adds all its fields' types to subtypes.
        """
        ctx = ctx or OrderedDict(struct_letters)
        ctx[self.identifier] = self
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            for (t, n, c) in self:
                ctype = c_type(t)
                elt = ctype.show_base()
                self.add_subtype(db, elt, ctx)
        return self

    def index_of(self,n):
        i=0
        for f in self:
            if f[1]==n:
                return i
            i += 1
        return None

    def __eq__(self, other):
        return list(self) == list(other)


# ------------------------------------------------------------------------------


class cClass(list, ccore):
    """
    Specialized ccore class that is also a 'list' representing a C++ class.

    Attributes:
        identifier: the name associated to this C++ class, as it appears
                    in the definition source file.

    Items of the list represent attributes of the class and are formatted as
    triplet of the form (x,y,z) where

       - x is a tuple (q,t) where q is a "parent", "using" or "virtual" keyword
         and t is "virtual" or a type name,
       - y is a tuple (mn,n) where mn is the mangled name and n is the full name
         of the class attribute,
       - z is a tuple (p,c) where p is a "public"/"protected"/"private"/"friend"
         indicator and c is a string that represents a comment.
    """
    _is_class = True

    def unfold(self, db, ctx=None):
        # ctx is our internal list of known types, so we start with
        # the raw types and ourself
        ctx = ctx or OrderedDict(struct_letters)
        n = cxx_type(self.identifier).show_base(kw=False,ns=True)
        ctx[n] = self
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            # now for each field we will search db for a matching type:
            for (x, y, _) in self:
                qal, t = x
                mn, n = y
                if qal == "parent":
                    elts = [n]
                elif qal == "using":
                    elts = t
                else:
                    if mn or ("virtual" in qal):
                        # we skip types related to methods since they
                        # have no influence of the class layout
                        continue
                    elts = [t]
                for t in elts:
                    xxt = cxx_type(t)
                    elt = xxt.show_base(kw=False,ns=True)
                    self.add_subtype(db, elt, ctx)
        return self

    def build(self, db):
        from ccrawl.ext import ctypes_

        x = self.as_cStruct(db)
        x.unfold(db)
        return ctypes_.build(x, db)

    def cStruct_build_info(self, db):
        """Defines the structure layout for this class,
           according to the gcc cxx ABI for virtual classes.

           The returned value is a triplet, (vptr, M, V) where

             - vptr is a virtual indicator,
             - M is the list of non-virtual fields,
             - V is the ordered dict of virtual fields.

           This triplet is used to create a cStruct instance
           that correspond to an instance of this C++ class in memory.
        """
        self.unfold(db)
        M, V = [], OrderedDict()
        vptr = 0
        # iterate over classes' fields
        for (x, y, _) in self:
            qal, t = x
            mn, n = y
            # we don't care about scope & comments
            # we start by handling parent classes:
            if qal == "parent":
                n = cxx_type(n)
                nn = n.show_base(ns=True)
                x = self.subtypes.get(nn, None)
                try:
                    if x._is_typedef:
                        x = x.subtypes.get(x, None)
                except Exception:
                    pass
                if x is None:
                    raise TypeError("unkown type '%s'" % nn)
                assert x._is_class
                # get layout of the parent class:
                vtbl, m, v = x.cStruct_build_info(db)
                if t == "virtual":
                    vptr = 2
                    if nn not in V:
                        V[nn] = (vtbl, m)
                else:
                    if vtbl:
                        vptr += vtbl
                        if len(m) > 0:
                            if not m[0][1].startswith("__vptr"):
                                t = cxx_type("void *")
                                M.append((t, "__vptr$%s" % nn))
                    M.extend(m)
                V.update(v)
            elif qal == "using":
                continue
            elif "virtual" in qal:
                vptr = 1
            else:
                t = cxx_type(t)
                if not t.is_method:
                    M.append((t, n))
        return (vptr, M, V)

    def as_cStruct(self, db):
        """
        Creates a cStruct instance that correspond to this C++ class,
        according the gcc cxx ABI for virtual classes.
        """
        if self.identifier.startswith("union "):
            x = cUnion()
        else:
            x = cStruct()
        name = cxx_type(self.identifier)
        x.identifier = "struct __layout$%s"%(name.show_base(kw=False,ns=True))
        # now get the structure information for this class:
        x.subtypes = None
        vptr, M, V = self.cStruct_build_info(db)
        if len(M) > 0 and vptr:
            if not M[0][1].startswith("__vptr"):
                x.append(("void *", "__vptr$%s" % name.show_base(), ""))
        for t, n in M:
            x.append((t.show(), n, ""))
        for nn, v in V.items():
            vptr, m = v
            if vptr:
                x.append(("void *", "__vptr$%s" % nn, ""))
            for t, n in m:
                x.append((t.show(), n, ""))
        return x

    def has_virtual_members(self):
        """
        Returns True if the C++ class has virtual members.
        """
        for x, _, _ in self:
            qal, t = x
            if "virtual" in qal:
                return True
        return False

    def base_specifier_list(self):
        """
        Returns the list of C++ parent (possibly virtual) classes.
        """
        spe = []
        for x, y, z in self:
            qal, t = x
            if "parent" in qal:
                mn, n = y
                n = cxx_type(n)
                p, _ = z
                s = ""
                if t:
                    s += " virtual"
                s += " %s %s" % (p.lower(), n.show_base())
                spe.append(s)
        if len(spe) > 0:
            return " :" + (",".join(spe))
        else:
            return ""

    def __eq__(self, other):
        return list(self) == list(other)


# ------------------------------------------------------------------------------


class cUnion(list, ccore):
    """
    Specialized ccore class that is also a 'list' representing a C union.
    """
    _is_union = True

    def unfold(self, db, ctx=None):
        ctx = ctx or OrderedDict(struct_letters)
        ctx[self.identifier] = self
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            for (t, n, c) in self:
                ctype = c_type(t)
                elt = ctype.show_base()
                self.add_subtype(db, elt, ctx)
        return self

    def index_of(self,n):
        i=0
        for f in self:
            if f[1]==n:
                return i
            i += 1
        return None

    def __eq__(self, other):
        return list(self) == list(other)


# ------------------------------------------------------------------------------


class cEnum(dict, ccore):
    """
    Specialized ccore class that is also a 'dict' representing a C enum.
    """
    _is_enum = True


# ------------------------------------------------------------------------------


class cMacro(str, ccore):
    """
    Specialized ccore class that is also a 'str' representing a C macro.
    """
    _is_macro = True


# ------------------------------------------------------------------------------


class cFunc(dict, ccore):
    """
    Specialized ccore class that is also a 'dict' representing a C/C++ function.
    """
    _is_func = True

    def restype(self):
        t = c_type(self["prototype"])
        if len(t.pstack)>0:
            t.pstack.pop()
        return t.show()

    def argtypes(self):
        t = c_type(self["prototype"])
        if len(t.pstack)>0:
            return [str(arg) for arg in t.pstack[-1].args]
        return []

    def unfold(self, db, ctx=None):
        ctx = ctx or OrderedDict(struct_letters)
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            rett = self.restype()
            args = self.argtypes()
            args.insert(0, rett)
            for elt in args:
                et = cxx_type(elt).show_base(kw=True,ns=True)
                self.add_subtype(db, et, ctx)
        return self

    def __eq__(self, other):
        return str(self) == str(other)


# ------------------------------------------------------------------------------


class cTemplate(dict, ccore):
    """
    Specialized ccore class that is also a 'dict' representing a C++ template.
    """
    def __init__(self,*args,**kargs):
        for arg in args:
            self.update(arg)
        self.update(kargs)
        P = self['params']
        for i,p in enumerate(P):
            if   'tp' in p:
                P[i] = self.template_template_param(p)
            elif 'ty' in p:
                P[i] = self.template_non_type_param(p)
            else:
                P[i] = self.template_type_param(p)

    _is_template = True
    class template_type_param(dict):
        def __str__(self):
            s = "typename"
            if self['pack']:
                s+='...'
            if tn:=self.get('tn',None):
                s += " %s"%tn
            if df:=self.get('df',None):
                s += " = %s"%df
            return s

    class template_template_param(dict):
        def __str__(self):
            s = "template <%s> typename"%self['tp']
            if self['pack']:
                s+='...'
            s += " %s"%self['tn']
            if df:=self.get('df',None):
                s += " = %s"%df
            return s

    class template_non_type_param(dict):
        def __str__(self):
            s = self['ty']
            if self['pack']:
                s+='...'
            if nm:=self.get('nm',None):
                s += " %s"%nm
            if df:=self.get('df',None):
                s += " = %s"%df
            return s

    def get_basename(self):
        if self.get("partial_specialization", False):
            return self.identifier
        i = self.identifier.rfind("<")
        assert i > 0
        return self.identifier[:i]

    def get_template(self):
        return "<%s>" % (", ".join((p['src'] for p in self["params"])))

    def get_typenames(self):
        TN = []
        for p in self['params']:
            if tn:=p.get('tn',None):
                TN.append(tn)
        return TN

    def unfold(self, db, ctx=None):
        ctx = ctx or OrderedDict(struct_letters)
        n = cxx_type(self.identifier).show_base(kw=False, ns=True)
        ctx[n] = self
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            for t in self.get_typenames():
                ctx[t] = True
            for (x, y, _) in self['cClass']:
                qal, t = x
                mn, n = y
                if qal == "parent":
                    elts = [n]
                elif qal == "using":
                    elts = t
                elif qal == "friend":
                    # we skip friend decl since they only indicate
                    # that those friends can access our attributes
                    continue
                else:
                    if mn or ("virtual" in qal) :
                        # we skip types related to methods since they
                        # have no influence of the class layout
                        continue
                    elts = [t]
                for t in elts:
                    xxt = cxx_type(t)
                    elt = xxt.show_base(kw=False, ns=True)
                    btn = xxt.show_base(kw=False, ns=False, tp=False)
                    if btn in ctx:
                        continue
                    self.add_subtype(db, elt, ctx)
            for t in self.get_typenames():
                if t in ctx:
                    del ctx[t]
        return self


# ------------------------------------------------------------------------------


class cNamespace(list, ccore):
    """
    Specialized ccore class that is also a 'list' representing a C++ namespace.
    """
    _is_namespace = True

    def unfold(self, db, ctx=None):
        ctx = ctx or OrderedDict(struct_letters)
        ctx[self.identifier] = self
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            for elt in self:
                self.add_subtype(db, elt, ctx)
        return self

    def __eq__(self, other):
        return list(self) == list(other)
