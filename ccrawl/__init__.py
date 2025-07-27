import sys

if hasattr(sys, 'ps1') or sys.flags.interactive:
    import re
    from click import echo,secho
    from . import conf

    conf.config = c = conf.Config()
    from .core import ccore

    from .db import Proxy,TinyDB,Query,where
    from .utils import c_type
    db = Proxy(c.Database)

    def search(rex, ignorecase=False):
        if ignorecase:
            flg |= re.IGNORECASE
        else:
            flg = 0
        try:
            cx = re.compile(rex, flags=flg)
        except re.error as err:
            secho(f"bad regular expression: {err=}", fg="red")
            return None
        look = lambda v: cx.search(str(v))
        Q = where("id").matches(rex, flags=flg)
        if db.rdb and not db.c.localonly :
            Q |= where("val").matches(rex, flags=flg)
            Q |= where("use").matches(rex, flags=flg)
        else:
            Q |= where("val").test(look)
        L = db.search(db.tag & Q)
        for l in L:
            echo("found ", nl=False)
            secho("%s " % l["cls"], nl=False, fg="cyan")
            echo("identifer ", nl=False)
            secho('"%s"' % l["id"], nl=False, fg="magenta")
            if look(l["val"]):
                echo(" with matching value", nl=False)
            echo("")
        return L

    if 'ghidra.pyghidra.interpreter' in sys.modules:
        from .ext.ghidra import *
    __all__ = ["core","db","parser","utils"]

else:
    __all__ = []
