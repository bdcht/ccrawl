from click import secho

try:
    from idc import parse_decls, Til2Idb
except ImportError:
    secho("IDAPython IDC package not found", fg="red")

    def build(obj):
        raise NotImplementedError

else:

    def build(obj):
        err = parse_decls(obj.show(db, set(), form="C"))
        if err:
            secho("parse_decls returns with %d errors" % err)
            return None
        name = obj.identifier
        for x in ("struct ", "union ", "enum "):
            if x in name:
                name = name.replace(x, "")
        return Til2Idb(-1, name.strip())
