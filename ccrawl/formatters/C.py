from click import secho
from collections import OrderedDict
from ccrawl.core import ccore
from ccrawl.utils import struct_letters, c_type, cxx_type
from tinydb import where
import re

__all__ = [
    "cTypedef_C",
    "cMacro_C",
    "cFunc_C",
    "cEnum_C",
    "cStruct_C",
    "cUnion_C",
    "cClass_C",
    "cTemplate_C",
    "cNamespace_C",
]

def unfoldable(f):
    def wrapper(obj,db):
        if db is None:
            return f(obj,db)
        ctx = OrderedDict(struct_letters)
        obj.unfold(db,ctx)
        # when unfolding, ctx items are ordered in a way that ensures if a type
        # is used several times in further definitions, it will be indexed after
        # all these definitions.
        out = []
        def cond(k,v):
            if isinstance(v,ccore):
                t = cxx_type(v.identifier)
                if k==t.show(kw=False) and not "std" in t.ns:
                    return True
            return False
        for v in (v for (k,v) in reversed(ctx.items()) if cond(k,v)):
            if "?_" in v.identifier:
                continue
            out.append(v.show(None, form="C"))
        # if t base is an anonymous type, we replace its anon name
        # by its struct/union definition in t:
        return "\n\n".join(out)
    return wrapper


# C formatters:
# ------------------------------------------------------------------------------

@unfoldable
def cTypedef_C(obj, db):
    t = cxx_type(obj)
    if t.is_anon and obj.subtypes:
        out = obj.subtypes[obj].show(form="C").strip(";")
    else:
        out = t.show(kw=True)
    return u"typedef {} {};".format(out,obj.identifier)


def cMacro_C(obj, db):
    return u"#define {} {};".format(obj.identifier, obj)


def cFunc_C(obj, db):
    fptr = c_type(obj["prototype"])
    return fptr.show(obj.identifier) + ";"


def cEnum_C(obj, db):
    S = []
    for k, v in sorted(obj.items(), key=lambda t: t[1]):
        S.append("  {} = {:d}".format(k, v))
    S = ",\n".join(S)
    name = re.sub(r"\?_.*", "", obj.identifier)
    return u"%s {\n%s\n};" % (name, S)


@unfoldable
def cStruct_C(obj, db):
    # declare structure:
    name = obj.identifier
    # if anonymous, remove anonymous name:
    if "?_" in name:
        name = "union" if obj._is_union else "struct"
    # S holds obj title and fields declaration strings
    out = [u"%s {" % name]
    # iterate through all fields:
    for i in obj:
        # get type, name, comment:
        t, n, c = i
        # decompose C-type t into specific parts:
        r = cxx_type(t)
        # get "element base" part of type t:
        e = r.lbase
        if not n and not e.startswith("union "):
            # -> union field are allowed to have no name...
            continue
        if r.is_anon and obj.subtypes:
            r = obj.subtypes[t].show(None,form="C").strip(";")
            out.append(u"    {} {};".format(r, n))
        else:
            out.append(u"  {};".format(r.show(n)))
    out.append("};")
    return "\n".join(out)


cUnion_C = cStruct_C


@unfoldable
def cClass_C(obj, db):
    # get the cxx type object:
    tn = cxx_type(obj.identifier)
    # get the current class name without keyword or namespace:
    classname = tn.show_base(kw=False, ns=False)
    # we need obj.identifier here and not tn.show() because
    # template specialization need to keep the template string.
    out = [u"%s%s {" % (obj.identifier, obj.base_specifier_list())]
    # P holds lists for each public/protected/private/friend members
    P = {"": [], "PUBLIC": [], "PROTECTED": [], "PRIVATE": []}
    # now, iterate through all fields:
    for (x, y, z) in obj:
        qal, t = x  # parent/virtual qualifier & type
        mn, n = y  # mangled name & name
        p, c = z  # public/protected/private & comment
        match qal:
            case "parent":
                continue
            case "using":
                # inherited type of attribute from parent is provided as a list in t:
                what = "::".join((cxx_type(u).show_base(kw=False) for u in t))
                using = "  using %s" % what
                # inherited name of attribute from parent is provided in n:
                # we append the attribute name unless its the class constructor
                using += "::%s;" % n if n != classname else ";"
                out.append(using)
                continue
            case s if s.startswith("template<"):
                P[p].append("    " + qal)
                qal = ""
            case "friend":
                out.append("  friend %s" % n)
                continue
        # decompose C-type t into specific parts:
        r = cxx_type(t)
        # get "element base" part of type t:
        e = r.lbase
        # is t a nested class ?
        nested = False
        L = r.ns
        if len(L)>1 and L[-2]==classname:
            nested = True
        # is t a nested enum ?
        nested |= e.startswith("enum ?_")
        # finally add field type and name to the structure lines:
        fo = ""
        if qal:
            if "," in qal:
                qal, fo = qal.split(",")
            qal = "%s " % qal
        P[p].append(u"    {}{}{};".format(qal, r.show(n, kw=nested), fo))
    # access specifier (empty is for friend members):
    for p in ("PUBLIC", "PROTECTED", "PRIVATE", ""):
        if len(P[p]) > 0:
            if p:
                out.append("  %s:" % p.lower())
            for v in P[p]:
                out.append(v)
    out.append("};")
    return "\n".join(out)


def cTemplate_C(obj, db):
    identifier = obj.get_basename()
    template = obj.get_template()
    # get the cxx type object, for namespaces:
    tn = cxx_type(identifier)
    # namespace = tn.show_base(kw=False,ns=False)
    # S holds template output lines:
    out = [u"template%s" % template]
    if "cClass" in obj:
        from ccrawl.core import cClass

        o = cClass(obj["cClass"])
        o.identifier = identifier
        o.subtypes = None
        o.tag = obj.tag
        o.src = obj.src
        x = cClass_C(o, db)
    if "cFunc" in obj:
        from ccrawl.core import cFunc

        o = cFunc(obj["cFunc"])
        o.identifier = identifier
        o.subtypes = None
        o.tag = obj.tag
        o.src = obj.src
        x = cFunc_C(o, db)
    x = x.split("\n\n")
    out.append(x.pop())
    x.append("\n".join(out))
    return "\n\n".join(x)


def cNamespace_C(obj, db):
    out = []
    if db is not None:
        identifier = obj.identifier
        out.append("namespace %s {" % obj.identifier)
        ctx = OrderedDict(struct_letters)
        obj.unfold(db,ctx)
        for t in obj:
            t = ctx.get(t,None)
            if t is None:
                continue
            R = t.show(db,form="C").split("\n\n")
            out.append(R.pop())
            out.insert(0,"\n\n".join(R) + "\n")
        out.append("};")
    return "\n".join(out)

