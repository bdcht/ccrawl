from click import secho
from ccrawl.formatters.amoco import id_amoco, c_type, cxx_type, fieldformat
from pyparsing import ParseException

try:
    import os
    os.environ["AMOCO_LOG_LEVEL"]=u"ERROR"
    from amoco.system.structs import (
        Alltypes,
        Consts,
        TypeDefine,
        StructDefine,
        UnionDefine,
        StructFormatter,
    )
except ImportError:
    secho("amoco package not found", fg="red")

    def build(t, db, _bstack=[]):
        raise NotImplementedError

else:

    def build(obj, db, _bstack=[]):
        if obj._is_class:
            x = obj.as_cStruct(db)
            x.unfold(db)
            return build(x, db)
        name = id_amoco(obj.identifier)
        if obj.identifier in _bstack:
            return Alltypes.get(name, None)
        else:
            _bstack.append(obj.identifier)
        if obj.subtypes is None:
            obj.unfold(db)
        for subtype in (obj.subtypes.values() or []):
            if subtype is None:
                continue
            build(subtype, db, _bstack)
        if obj._is_typedef:
            t = c_type(obj)
            rn, n = fieldformat(t)
            TypeDefine(name, rn or n)
            return Alltypes[name]
        if obj._is_macro:
            v = obj.strip()
            try:
                v = int(v, base=0)
            except ValueError:
                pass
            try:
                t = c_type(v)
                rn, n = fieldformat(t)
                TypeDefine(name, rn or n)
                return Alltypes[name]
            except ParseException:
                pass
            globals()[name] = v
            return v
        if obj._is_enum:
            if len(obj) < 256:
                sz = "b"
            elif len(obj) < (1 << 16):
                sz = "h"
            else:
                sz = "i"
            TypeDefine(name, sz)
            Consts.All[name] = {}.update(obj)
        elif obj._is_struct or obj._is_union:
            define = StructDefine
            if obj._is_union:
                define = UnionDefine
            cls = type(name, (StructFormatter,), {})
            fmt = []
            # if the structure is a bitfield, we
            # gather fields as long as they are part of
            # the bitfield...
            bfmt = []
            for t, n, c in iter(obj):
                if c and c.count("\n") > 0:
                    c = None
                r = c_type(t)
                if r.lbfw > 0:
                    bfmt.append((r, n))
                    continue
                else:
                    fmt.extend(format_bitfield(bfmt))
                if not n and not r.lbase.startswith("union "):
                    continue
                rt, t = fieldformat(r)
                fmt.append("{} : {} ;{}".format(rt or t, n, c or ""))
            fmt.extend(format_bitfield(bfmt))
            fmt = "\n".join(fmt)
            define(fmt)(cls)
        else:
            raise NotImplementedError
        return Alltypes[name]

    def format_bitfield(bfmt):
        fmt = []
        while bfmt:
            cur = [bfmt.pop(0)]
            basetype = cur[0][0].lbase
            sz = Alltypes[cur[0][0].lbase].size() * 8
            tot = cur[0][0].lbfw
            while bfmt:
                if bfmt[0][0].lbase == cur[0][0].lbase:
                    if (tot + (bfmt[0][0].lbfw)) <= sz:
                        tot += bfmt[0][0].lbfw
                        cur.append(bfmt.pop(0))
                    else:
                        break
                else:
                    break
            lt, ln = list(zip(*cur))
            r = lt[0]
            rt, t = fieldformat(r)
            n = "/".join(ln)
            t += "".join(["/%d" % x.lbfw for x in lt[1:]])
            fmt.append("{} : {} ;{}".format(t, n, ""))
        return fmt

def get_c_or_cxx_type(x):
    if not (('&' in x) or ('::' in x)):
        try:
            t = c_type(x)
        except pp.ParseException:
            pass
        else:
            return t
    t = cxx_type(x)
    return t

