import sys

if hasattr(sys, 'ps1') or sys.flags.interactive:
    import re
    from click import echo,secho
    from . import conf

    conf.config = c = conf.Config()
    from .core import ccore

    from .db import Proxy,Query,where
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
        # fixup for click.[s]echo to stdout in ghidra's pyconsole:
        from click._compat import _default_text_stdout
        console = _default_text_stdout()
        # hacky fix of click/pyghidra(PyConsole) inconsistency:
        setattr(console._stream._stream,'flush',console._stream._out.flush)
        secho("Hi Ghidra!", fg="green")
        # set verbose mode for pyghidra interpreter
        c.Terminal.verbose = True
        # loading our external ghidra utils:
        from .ext.ghidra import *

        def import(ldbfile, identifier):
            db.load(ldbfile)
            l = db.ldb.get(db.tag & (where("id")==identifier))
            build(ccore.from_db(l),db)

    __all__ = ["core","parser","utils"]

else:
    __all__ = []
