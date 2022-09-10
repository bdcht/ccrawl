from collections import OrderedDict
from ccrawl import formatters
from ccrawl.utils import struct_letters, c_type, cxx_type
from ccrawl.db import where


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
      - class
      - template
      - namespace

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

    def show(self, db=None, r=None, form=None):
        """
        Generic method that possibly defines and
        ultimately calls the internal formatter function.

        Attributes:
            db [opt] (Proxy): database used in recursive mode
        """
        if (not self.formatter) or form:
            self.set_formatter(form)
        return self.formatter(db, r)

    def unfold(self, db, limit=None):
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
        Basically just a wrapper for the :mod:`ctypes_`.build function.

        Parameters:
            db (Proxy): database used to get any other type on which
                        this type depends.
        """
        self.unfold(db)
        from ccrawl.ext import ctypes_

        return ctypes_.build(self, db)

    def add_subtype(self, db, elt, limit=None):
        """
        Generic method that fetches item 'elt' from the database and
        adds it to the subtypes of this type before unfolding it.
        """
        x = ccore._cache_.get(elt, None)
        if x is None:
            data = db.get(where("id") == elt)
            if data:
                x = ccore.from_db(data)
                ccore._cache_[elt] = x
            else:
                self.subtypes[elt] = None
                return
        self.subtypes[elt] = x.unfold(db, limit)

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
        try:
            cls.formatter = getattr(formatters, ff)
        except AttributeError:
            cls.formatter = formatters.default

    @staticmethod
    def getcls(name):
        if name == "cTypedef":
            return cTypedef
        if name == "cStruct":
            return cStruct
        if name == "cUnion":
            return cUnion
        if name == "cEnum":
            return cEnum
        if name == "cMacro":
            return cMacro
        if name == "cFunc":
            return cFunc
        if name == "cClass":
            return cClass
        if name == "cTemplate":
            return cTemplate
        if name == "cNamespace":
            return cNamespace

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
            for i, x in iter(self.local.items()):
                if x:
                    data.extend(x.to_db(i, tag, identifier))
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
        return val


# ------------------------------------------------------------------------------


class cTypedef(str, ccore):
    """
    Specialized ccore class that is also a 'str' representing a C/C++ typedef.
    
    Attributes:
        identifier: the new typename associated to this typedef.
    """
    _is_typedef = True

    def unfold(self, db, limit=None, ctx=None):
        """
        Unfolding a typedef simply adds its underlying type definition to subtypes.
        """
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            ctype = c_type(self)
            if limit != None:
                if limit <= 0 and ctype.is_ptr:
                    return self
            elt = ctype.lbase
            if elt not in struct_letters:
                if limit:
                    limit -= 1
                self.add_subtype(db, elt, limit)
        return self

    def __eq__(self, other):
        return str(self) == str(other)


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

    def unfold(self, db, limit=None):
        """
        Unfolding a struct adds all its fields' types to subtypes.
        """
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            T = list(struct_letters.keys())
            T.append(self.identifier)
            for (t, n, c) in self:
                ctype = c_type(t)
                if limit != None:
                    if limit <= 0 and ctype.is_ptr:
                        continue
                elt = ctype.lbase
                if elt not in T:
                    T.append(elt)
                    if limit:
                        limit -= 1
                    self.add_subtype(db, elt, limit)
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
        identifier: the name associated to this C++ class.

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

    def unfold(self, db, limit=None):
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            T = list(struct_letters.keys())
            T.append(self.identifier)
            for (x, y, _) in self:
                qal, t = x
                mn, n = y
                if qal == "parent":
                    elt = [n]
                elif qal == "using":
                    elt = t
                else:
                    if mn or ("virtual" in qal):
                        continue
                    elt = cxx_type(t)
                    elt = elt.show_base(kw=True, ns=True)
                    elt = [elt]
                for e in elt:
                    if e not in T:
                        T.append(e)
                        self.add_subtype(db, e, limit)
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
                nn = n.show_base()
                name = n.show_base(True, True)
                x = ccore._cache_.get(name, None)
                try:
                    if x._is_typedef:
                        x = ccore._cache_.get(x, None)
                except Exception:
                    pass
                if x is None:
                    raise TypeError("unkown type '%s'" % n)
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
                n = cxx_type(self.identifier)
                x.append(("void *", "__vptr$%s" % n.show_base(), ""))
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

    def unfold(self, db, limit=None):
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            T = list(struct_letters.keys())
            T.append(self.identifier)
            for (t, n, c) in self:
                ctype = c_type(t)
                if limit != None:
                    if limit <= 0 and ctype.is_ptr:
                        continue
                elt = ctype.lbase
                if elt not in T:
                    T.append(elt)
                    if limit:
                        limit -= 1
                    self.add_subtype(db, elt, limit)
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
            return t.pstack[-1].args
        return []

    def unfold(self, db, limit=None):
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            T = list(struct_letters.keys())
            rett = self.restype()
            args = self.argtypes()
            args.insert(0, rett)
            for t in args:
                elt = c_type(t).lbase
                if elt not in T:
                    T.append(elt)
                    self.add_subtype(db, elt)
        return self

    def __eq__(self, other):
        return str(self) == str(other)


# ------------------------------------------------------------------------------


class cTemplate(dict, ccore):
    """
    Specialized ccore class that is also a 'dict' representing a C++ template.
    """
    _is_template = True

    def get_basename(self):
        if self.get("partial_specialization", False):
            return self.identifier
        i = self.identifier.rfind("<")
        assert i > 0
        return self.identifier[:i]

    def get_template(self):
        return "<%s>" % (",".join(self["params"]))


# ------------------------------------------------------------------------------


class cNamespace(list, ccore):
    """
    Specialized ccore class that is also a 'list' representing a C++ namespace.
    """
    _is_namespace = True

    def unfold(self, db, limit=None):
        if self.subtypes is None:
            self.subtypes = OrderedDict()
            T = list(struct_letters.keys())
            T.append(self.identifier)
            for elt in self:
                self.add_subtype(db, elt)
        return self

    def __eq__(self, other):
        return list(self) == list(other)
