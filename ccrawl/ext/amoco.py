from click import secho
from ccrawl.formatters.amoco import id_amoco,c_type,fieldformat
try:
    from amoco.system.structs import Consts,
                                     TypeDefine,
                                     StructDefine,UnionDefine,
                                     StructFormatter
except ImportError:
    secho("amoco package not found",fg="red")
    def build(t,db):
        raise NotImplementedError
else:
    def build(obj,db):
        for subtype in (obj.subtypes.values() or []):
            if subtype is None: continue
            build(subtype,db)
        if obj._is_typedef:
            t = c_type(obj)
            rn,n = fieldformat(t)
            TypeDefine(obj.identifier, rn or n)
            return StructDefine.All[obj.identifier]
        if obj._is_macro:
            v = obj.strip()
            try:
                v = int(v,base=0)
            except ValueError:
                pass
            globals()[obj.identifier] = v
            return v
        x = id_amoco(obj.identifier)
        if obj._is_enum:
            TypeDefine(x,'i')
            Consts.All[x] = {}.update(obj)
        elif obj._is_struct or obj._is_union:
            define = StructDefine
            if obj._is_union: define = UnionDefine
            cls = type(x,(StructFormatter,),{})
            fmt = []
            for t,n,c in obj:
                r = c_type(t)
                rt,t = fieldformat(r)
                fmt.append('{} : {} ;{}'.format(rt or t,n,c or ''))
            fmt = '\n'.join(fmt)
            define(fmt)(cls)
        elif obj._is_class:
            x = obj.as_cStruct(db)
            x.unfold(db)
            return build(x,db)
        else:
            raise NotImplementedError
        return StructDefine.All[x]
