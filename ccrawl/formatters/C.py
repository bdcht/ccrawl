from click import secho
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
]

# C formatters:
# ------------------------------------------------------------------------------


def cTypedef_C(obj, db, recursive):
    pre = ""
    t = c_type(obj)
    if isinstance(recursive, set) and (t.lbase not in struct_letters):
        recursive.add(obj.identifier)
        Q = db.tag & (where("id") == t.lbase)
        if db.contains(Q):
            x = obj.from_db(db.get(Q))
            pre = x.show(db, recursive, form="C") + "\n"
        else:
            secho("identifier %s not found" % t.lbase, fg="red", err=True)
    # if t base is an anonymous type, we replace its anon name
    # by its struct/union definition in t:
    if recursive and "?_" in t.lbase:
        pre = pre.split("\n\n")
        t.lbase = pre.pop().strip(";\n")
        pre.append("")
        pre = "\n\n".join(pre)
    return u"{}typedef {};".format(pre, t.show(obj.identifier))


def cMacro_C(obj, db, recursive):
    return u"#define {} {};".format(obj.identifier, obj)


def cFunc_C(obj, db, recursive):
    fptr = c_type(obj["prototype"])
    return fptr.show(obj.identifier) + ";"


def cEnum_C(obj, db, recursive):
    S = []
    for k, v in sorted(obj.items(), key=lambda t: t[1]):
        S.append("  {} = {:d}".format(k, v))
    S = ",\n".join(S)
    name = re.sub(r"\?_.*", "", obj.identifier)
    return u"%s {\n%s\n};" % (name, S)


def cStruct_C(obj, db, recursive):
    # declare structure:
    name = obj.identifier
    # prepare query if recursion is needed:
    if isinstance(recursive, set):
        # if we are on a loop, just declare the struct name:
        if name in recursive:
            return "%s;" % name
        Q = True
        recursive.update(struct_letters)
        recursive.add(name)
    else:
        Q = None
    tn = "union " if obj._is_union else "struct "
    # if anonymous, remove anonymous name:
    if "?_" in name:
        name = tn
    # R holds recursive definition strings needed for obj
    R = []
    # S holds obj title and fields declaration strings
    S = [u"%s {" % name]
    # iterate through all fields:
    for i in obj:
        # get type, name, comment:
        t, n, c = i
        # decompose C-type t into specific parts:
        r = c_type(t)
        # get "element base" part of type t:
        e = r.lbase
        if not n and not e.startswith("union "):
            # -> union field are allowed to have no name...
            continue
        # query field element base type if recursive:
        # check if we are about to query the current struct type...
        if Q and (r.lbase == obj.identifier):
            R.append("%s;" % r.lbase)
        elif Q and (r.lbase not in recursive):
            # prepare query
            # (deal with the case of querying an anonymous type)
            q = db.tag & (where("id") == r.lbase)
            if "?_" in r.lbase:
                q &= where("src") == obj.identifier
            # do the query and update R:
            if db.contains(q):
                # retreive the field type:
                x = obj.from_db(db.get(q)).show(db, recursive, form="C")
                if not "?_" in r.lbase:
                    # if not anonymous, insert it directly in R
                    # R.insert(0,x)
                    R.append(x)
                    recursive.add(r.lbase)
                else:
                    # anonymous struct/union: we need to transfer
                    # any predefs into R
                    x = x.split("\n\n")
                    r.lbase = x.pop().replace("\n", "\n  ").strip(";")
                    if len(x):
                        xr = x[0].split("\n")
                        for xrl in xr:
                            if xrl and xrl not in R:
                                # R.insert(0,xrl)
                                R.append(xrl)
            else:
                secho("identifier %s not found" % r.lbase, fg="red", err=True)
        # finally add field type and name to the structure lines:
        S.append(u"  {};".format(r.show(n)))
    # join R and S:
    if len(R) > 0:
        R.append("\n")
    S.append("};")
    return "\n".join(R) + "\n".join(S)


cUnion_C = cStruct_C


def cClass_C(obj, db, recursive):
    # get the cxx type object:
    tn = cxx_type(obj.identifier)
    # get the current class name without keyword or namespace:
    classname = tn.show_base(kw=False, ns=False)
    # prepare query if recursion is needed:
    if isinstance(recursive, set):
        Q = True
        recursive.update(struct_letters)
        recursive.add(tn.lbase)
    else:
        Q = None
    # R holds recursive definition strings needed for obj
    R = []
    # S holds obj title and fields declaration strings
    # we need obj.identifier here and not tn.show() because
    # template specialization need to keep the template string.
    S = [u"%s%s {" % (obj.identifier, obj.base_specifier_list())]
    # P holds lists for each public/protected/private/friend members
    P = {"": [], "PUBLIC": [], "PROTECTED": [], "PRIVATE": []}
    # now, iterate through all fields:
    for (x, y, z) in obj:
        qal, t = x  # parent/virtual qualifier & type
        mn, n = y  # mangled name & name
        p, c = z  # public/protected/private & comment
        if qal == "parent":
            # the parent class name is found in n:
            r = cxx_type(n)
            e = r.lbase
            if Q and (e not in recursive):
                q = db.tag & (where("id") == e)
                x = obj.from_db(db.get(q)).show(db, recursive, form="C")
                R.append(x)
                recursive.add(e)
            continue
        elif qal == "using":
            # inherited type of attribute from parent is provided as a list in t:
            what = "::".join((cxx_type(u).show_base(kw=False) for u in t))
            using = "  using %s" % what
            # inherited name of attribute from parent is provided in n:
            # we append the attribute name unless its the class constructor
            using += "::%s;" % n if n != classname else ";"
            S.append(using)
            continue
        elif qal.startswith("template<"):
            P[p].append("    " + qal)
            qal = ""
        # decompose C-type t into specific parts:
        r = cxx_type(t)
        # get "element base" part of type t:
        e = r.lbase
        # is t a nested class ?
        nested = r.ns.split("::")[-1].startswith(classname)
        # is t a nested enum ?
        nested |= e.startswith("enum ?_")
        # query field element raw base type if needed:
        if Q and ((e not in recursive) or nested):
            # prepare query
            q = db.tag & (where("id") == e)
            # deal with nested type:
            if nested:
                q &= where("src") == tn.lbase
            if db.contains(q):
                # retreive the field type:
                x = obj.from_db(db.get(q))
                x = x.show(db, recursive, form="C")
                if not nested:
                    # if not nested, insert it directly in R
                    R.append(x)
                    recursive.add(e)
                else:
                    x = x.replace("%s::" % classname, "")
                    # nested struct/union/class: we need to transfer
                    # any predefs into R
                    x = x.split("\n\n")
                    r.lbase = x.pop().replace("\n", "\n    ").strip(";")
                    if len(x):
                        xr = x[0].split("\n")
                        for xrl in xr:
                            if xrl and xrl not in R:
                                R.append(xrl)
            else:
                secho("identifier %s not found" % r.lbase, fg="red", err=True)
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
                S.append("  %s:" % p.lower())
            for v in P[p]:
                S.append(v)
    # join R and S:
    if len(R) > 0:
        R.append("\n")
    S.append("};")
    return "\n".join(R) + "\n".join(S)


def cTemplate_C(obj, db, recursive):
    identifier = obj.get_basename()
    template = obj.get_template()
    # get the cxx type object, for namespaces:
    tn = cxx_type(identifier)
    # namespace = tn.show_base(kw=False,ns=False)
    # prepare query if recursion is needed:
    if isinstance(recursive, set):
        # Q = True
        recursive.update(struct_letters)
        recursive.add(tn.lbase)
        for t in obj["params"]:
            if t.startswith("typename "):
                t = t.replace("typename ", "")
                recursive.add(t)
    else:
        # Q = None
        pass
    R = []
    # S holds template output lines:
    S = [u"template%s" % template]
    if "cClass" in obj:
        from ccrawl.core import cClass

        o = cClass(obj["cClass"])
        o.identifier = identifier
        x = cClass_C(o, db, recursive)
    if "cFunc" in obj:
        from ccrawl.core import cFunc

        o = cFunc(obj["cFunc"])
        o.identifier = identifier
        x = cFunc_C(o, db, recursive)
    x = x.split("\n\n")
    S.append(x.pop())
    if len(x):
        R.append(x[0])
    return "\n".join(R) + "\n".join(S)
