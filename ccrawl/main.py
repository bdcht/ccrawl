import os
import re
import time
import click
from ccrawl import conf
from ccrawl.formatters import formats
from ccrawl.parser import TYPEDEF_DECL, STRUCT_DECL, UNION_DECL
from ccrawl.parser import FUNCTION_DECL, MACRO_DEF
from ccrawl.parser import parse
from ccrawl.core import ccore
from ccrawl.utils import c_type
from ccrawl.db import Proxy, Query, where

# ccrawl commands utilities:
# ------------------------------------------------------------------------------


def spawn_console(ctx):
    """Crawl console for interactive mode.
    The console is based on IPython if found, or uses CPython otherwise.
    When interactive, ccrawl is configured in non strict collect mode.
    """
    c = conf.config
    if not ctx.obj["db"]:
        ctx.obj["db"] = Proxy(c.Database)
    cvars = dict(globals(), **locals())
    cvars.update(ctx.obj)
    # c.Collect.strict=False
    if c.Terminal.console.lower() == "ipython":
        try:
            from IPython import start_ipython
        except ImportError:
            if conf.VERBOSE:
                click.echo("ipython not found", err=True)
            c.Terminal.console = "python"
        else:
            ic = c.src.__class__()
            ic.TerminalTerminalIPythonApp.display_banner = False
            ic.InteractiveShellApp.exec_lines = ["print(conf.BANNER)"]
            start_ipython(argv=[], config=ic, user_ns=cvars)
    if c.Terminal.console.lower() == "python":
        from code import interact

        try:
            import readline, rlcompleter

            readline.set_completer(rlcompleter.Completer(cvars).complete)
            readline.parse_and_bind("Tab: complete")
            del readline, rlcompleter
        except ImportError:
            click.echo("readline not found", err=True)
        interact(banner=conf.BANNER + "\n", local=cvars)


# ------------------------------------------------------------------------------
# ccrawl Commands :
# ------------------------------------------------------------------------------


@click.group(invoke_without_command=True)
@click.option("-v", "--verbose", is_flag=True, default=False, help="display more infos")
@click.option(
    "-q", "--quiet", is_flag=True, default=False, help="don't display anything"
)
@click.option("-b", "--db", help="url for the remote database")
@click.option(
    "-l",
    "--local",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
    help="path to the local database",
)
@click.option(
    "-c",
    "--config",
    "configfile",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="path to configuration file",
)
@click.option("-g", "--tag", help="filter queries with given tag")
@click.pass_context
def cli(ctx, verbose, quiet, db, local, configfile, tag):
    ctx.obj = {}
    c = conf.config = conf.Config(configfile)
    if quiet:
        verbose = False
    if verbose:
        quiet = False
    debug = c.Terminal.debug
    c.Terminal.verbose = verbose | debug
    c.Terminal.quiet |= quiet
    c.Terminal.width = click.get_terminal_size()[0]
    if conf.VERBOSE:
        if c.src:
            click.echo("config file '%s' loaded" % c.f)
        else:
            click.echo("default config loaded (file '%s' not found)" % c.f)
    if db:
        c.Database.url = db
    if local:
        c.Database.local = local
    if conf.VERBOSE:
        click.echo("loading local database %s ..." % c.Database.local, nl=False)
    try:
        ctx.obj["db"] = Proxy(c.Database)
        if tag:
            ctx.obj["db"].set_tag(tag)
    except Exception:
        click.secho("failed", fg="red", err=True)
        exit(1)
    if conf.VERBOSE:
        click.echo("done")
        if c.Database.url and ctx.obj["db"].rdb:
            click.echo("remote database is: %s" % c.Database.url)
        elif c.Database.url:
            click.secho(
                "remote database (%s) not connected" % c.Database.url,
                fg="red",
                err=True,
            )
        else:
            click.echo("no remote database")
    if ctx.invoked_subcommand is None:
        spawn_console(ctx)
    else:
        if conf.DEBUG:
            click.echo("COMMAND: %s" % ctx.invoked_subcommand)


# Collect command:
# ------------------------------------------------------------------------------


def do_collect(ctx, src):
    ctx.invoke(
        collect,
        allc=False,
        types=False,
        functions=False,
        macros=False,
        strict=False,
        xclang="",
        src=src,
    )


@cli.command()
@click.option(
    "-a",
    "--all",
    "allc",
    is_flag=True,
    # help='collect data from all files rather than headers only'
)
@click.option("-t", "--types", is_flag=True, help="collect types")
@click.option("-f", "--functions", is_flag=True, help="collect functions")
@click.option("-m", "--macros", is_flag=True, help="collect macros")
@click.option("-s", "--strict", is_flag=True, help="strict mode")
@click.option("--auto-include", "autoinclude", is_flag=True,
        help="try to guess -I path(s) for each input file")
@click.option("--clang", "xclang", help="parameters passed to clang")
@click.argument(
    "src",
    nargs=-1,
    type=click.Path(exists=True, file_okay=True, readable=True),
    # help='directory/files with definitions to collect',
)
@click.pass_context
def collect(ctx, allc, types, functions, macros, strict, autoinclude, xclang, src):
    """Collects types (struct,union,class,...) definitions,
    functions prototypes and/or macro definitions from SRC files/directory.
    Collected definitions are stored in a local database,
    tagged with the global 'tag' option if present or with a timestamp.

    The extraction is performed using libclang parser which can receive
    specific parameters through the --clang option.
    By default, only header files are parsed (the --all option allows to
    collect from all input files) and all implemented collectors are used.

    In strict mode, the clang options need to conform to the makefile
    that lead to the compilation of all input source (i.e. clang diagnostics
    errors are not bypassed).
    """
    c = conf.config
    cxx = c.Collect.cxx
    F = lambda f: f.endswith(".h") or (cxx and f.endswith(".hpp"))
    K = None
    c.Collect.strict |= strict
    if allc is True:
        F = lambda f: (f.endswith(".c") or (cxx and f.endswith(".cpp")) or F(f))
    if types or functions or macros:
        K = []
        if types:
            K += [TYPEDEF_DECL, STRUCT_DECL, UNION_DECL]
        if functions:
            K += [FUNCTION_DECL]
        if macros:
            K += [MACRO_DEF]
    tag = ctx.obj["db"].tag._hash or None
    if tag is None:
        tag = str(time.time())
    # filters:
    ctx.obj["F"] = F
    # selected kinds of cursors to collect:
    ctx.obj["K"] = K
    # temporary database cache:
    dbo = {}
    # if no clang params is provided, use defaults:
    if xclang is None:
        # keep comments in parser output:
        args = [
            "-ferror-limit=0",
            "-fparse-all-comments",
        ]
        # add header directories:
        for i in (D for D in src if os.path.isdir(D)):
            args.append("-I%s" % i)
    else:
        args = xclang.split(" ")
    # count source files:
    FILES = set()
    INCLUDES = set()
    for D in src:
        if os.path.isdir(D):
            for dirname, subdirs, files in os.walk(D.rstrip("/")):
                INCLUDES.add("-I%s/"%dirname)
                for f in filter(F,files):
                    filename = "%s/%s" % (dirname, f)
                    FILES.add(filename)
        elif os.path.isfile(D) and F(D):
            FILES.add(D)
    total = len(FILES)
    W = c.Terminal.width - 12
    # parse and collect all sources:
    if autoinclude:
        args.extend(list(INCLUDES))
    while len(FILES) > 0:
        t0 = time.time()
        filename = FILES.pop()
        if not c.Terminal.quiet:
            p = ((total - len(FILES)) * 100.0) / total
            click.echo(("[%3d%%] %s " % (p, filename)).ljust(W), nl=False)
        l = parse(filename, args, kind=K, tag=tag[-1])
        t1 = time.time()
        if c.Terminal.timer:
            click.secho("(%.2f+" % (t1 - t0), nl=False, fg="cyan")
        if l is None:
            return -1
        if len(l) > 0:
            # remove already processed/included files
            FILES.difference_update([el["src"] for el in l])
            # remove duplicates into dbo:
            for x in l:
                dbo[x["id"] + x["src"]] = x
        t2 = time.time()
        if c.Terminal.timer:
            click.secho("%.2f)" % (t2 - t1), fg="cyan")
    db = ctx.obj["db"]
    if not c.Terminal.quiet:
        click.echo("-" * (c.Terminal.width))
        click.echo("saving database...".ljust(W), nl=False)
    N = len(dbo)
    db.insert_multiple(dbo.values())
    db.close()
    if not c.Terminal.quiet:
        click.secho(("[%4d]" % N).rjust(12), fg="green")
    return 0


# search command:
# ------------------------------------------------------------------------------


@cli.command()
@click.option("-i", "--ignorecase", is_flag=True, default=False)
@click.argument("rex", nargs=1, type=click.STRING)
@click.pass_context
def search(ctx, ignorecase, rex):
    """Search for documents in the remote database
    (or the local database if no remote is found) with either name
    or definition matching the provided regular expression.
    """
    db = ctx.obj["db"]
    flg = re.MULTILINE
    if ignorecase:
        flg |= re.IGNORECASE
    try:
        cx = re.compile(rex, flags=flg)
    except re.error as err:
        click.secho(f"bad regular expression: {err=}", fg="red")
        return None
    look = lambda v: cx.search(str(v))
    Q = where("id").matches(rex, flags=flg)
    if db.rdb:
        Q |= where("val").matches(rex, flags=flg)
    else:
        Q |= where("val").test(look)
    L = db.search(Q)
    for l in L:
        click.echo("found ", nl=False)
        click.secho("%s " % l["cls"], nl=False, fg="cyan")
        click.echo("identifer ", nl=False)
        click.secho('"%s"' % l["id"], nl=False, fg="magenta")
        if look(l["val"]):
            click.echo(" with matching value", nl=False)
        click.echo("")
    return L


# find commands:
# ------------------------------------------------------------------------------


@cli.group(invoke_without_command=True)
@click.option("-a", "--and", "ands", type=click.STRING, multiple=True)
@click.option("-o", "--or", "ors", type=click.STRING, multiple=True)
@click.pass_context
def select(ctx, ands, ors):
    """Get document(s) from the remote database
    (or the local database if no remote is found) matching
    multiple constraints.
    """
    Q = Query().noop()
    try:
        for x in ands:
            k, v = x.split("=")
            Q &= where(k).search(v)
        for x in ors:
            k, v = x.split("=")
            Q |= where(k).search(v)
    except Exception:
        click.secho("invalid options (ignored)", fg="yellow", err=True)
    ctx.obj["select"] = Q
    if ctx.invoked_subcommand is None:
        db = ctx.obj["db"]
        L = db.search(Q)
        for l in L:
            click.echo("found ", nl=False)
            click.secho("%s " % l["cls"], nl=False, fg="cyan")
            click.echo("identifer ", nl=False)
            click.secho('"%s"' % l["id"], fg="magenta")
    else:
        if conf.DEBUG:
            click.echo("FIND_COMMAND: %s" % ctx.invoked_subcommand)


@select.command()
@click.argument("proto", nargs=-1, type=click.STRING)
@click.pass_context
def prototype(ctx, proto):
    """Get prototype definitions from the remote database
    (or the local database if no remote is found) matching
    constraints on name of its return type or specific
    arguments.
    """
    reqs = {}
    try:
        for p in proto:
            pos, t = p.split(":")
            pos = int(pos)
            reqs[pos] = c_type(t).show()
    except Exception:
        click.secho("invalid arguments", fg="red", err=True)
        return
    db = ctx.obj["db"]
    Q = ctx.obj.get("select", Query().noop())
    L = db.search(Q, cls="cFunc")
    R = []
    with click.progressbar(L) as pL:
        for l in L:
            x = ccore.from_db(l)
            P = [c_type(t).show() for t in x.argtypes()]
            P.insert(0, c_type(x.restype()).show())
            if max(reqs) >= len(P):
                continue
            if not all(((t == P[i]) for (i, t) in reqs.items())):
                continue
            R.append(x.show(db, form="C"))
    if R:
        click.echo("\n".join(R))


@select.command()
@click.option("-m", "--mask", is_flag=True, default=False)
@click.option("-s", "--symbol", default="")
@click.argument("val")
@click.pass_context
def constant(ctx, mask, symbol, val):
    """Get constant definitions (macros or enums)
    from the remote database (or the local database if no remote is found) matching
    constraints on value (possibly representing a mask of several symbols) and
    symbol prefix.
    """
    value = int(val, 0)
    db = ctx.obj["db"]
    Q = ctx.obj.get("select", Query().noop())
    Q &= (where("cls") == "cMacro") | (where("cls") == "cEnum")
    L = db.search(Q)
    R = []
    with click.progressbar(L) as pL:
        for l in pL:
            x = ccore.from_db(l)
            if x._is_macro:
                if not (symbol in x.identifier):
                    continue
                try:
                    v = int(x, 0)
                except Exception:
                    continue
                else:
                    if v == value:
                        R.append(x.identifier + "\n")
                    elif mask and (symbol in x.identifier):
                        if v < value and v & value:
                            R.append(x.identifier + " | ")
            else:
                for k, v in x.items():
                    if v == value and (symbol in k):
                        R.append(k + "\n")
                        break
                    elif mask and (symbol in k):
                        if v < value and v & value:
                            R.append(k + " | ")
    if R:
        s = "".join(R)
        click.echo(s.strip(" |\n"))


@select.command()
@click.option("-d", "--def", "pdef", is_flag=True, default=False)
@click.argument("conds", nargs=-1, type=click.STRING)
@click.pass_context
def struct(ctx, pdef, conds):
    """Get structured definitions (struct, union or class)
    from the remote database (or the local database if no remote is found) matching
    constraints on total size or specific type name or size at given offset within
    the structure.
    """
    reqs = {}
    try:
        for p in conds:
            off, t = p.split(":")
            if off == "*":
                sz = int(t)
                reqs[off] = sz
            else:
                off = int(off)
                if t[0] == "+":
                    reqs[off] = int(t)
                elif t[0] == "?":
                    reqs[off] = t
                else:
                    reqs[off] = c_type(t)
    except Exception:
        click.secho("invalid arguments", fg="red", err=True)
        return
    db = ctx.obj["db"]
    Q = ctx.obj.get("select", Query().noop())
    L = db.search(Q & ((where("cls") == "cStruct") | (where("cls") == "cClass")))
    R = []
    fails = []
    with click.progressbar(L) as pL:
        for l in pL:
            x = ccore.from_db(l)
            ctcls = c_type
            try:
                if x._is_class:
                    x = x.as_cStruct(db)
                t = x.build(db)
            except Exception:
                fails.append("can't build %s" % x.identifier)
                continue
            F = []
            for i, f in enumerate(t._fields_):
                field = getattr(t, f[0])
                F.append((field.offset, field.size, ctcls(x[i][0])))
            if F:
                xsize = F[-1][0] + F[-1][1]
                if "*" in reqs and reqs["*"] != xsize:
                    continue
                F = dict(((f[0], f[1:3]) for f in F))
                ok = []
                for o, s in reqs.items():
                    if o == "*":
                        continue
                    cond = o in F
                    ok.append(cond)
                    if not cond:
                        break
                    if s == "?":
                        continue
                    if s == "*":
                        cond = F[o][1].is_ptr
                    elif isinstance(s, c_type):
                        cond = F[o][1].show() == s.show()
                    else:
                        cond = F[o][0] == s
                    ok.append(cond)
                    if not cond:
                        break
                if all(ok):
                    if not pdef:
                        res = x.identifier
                    else:
                        res = x.show(db, form="C")
                    R.append(res)
    if conf.VERBOSE:
        click.secho("\n".join(fails), fg="red", err=True)
    if R:
        click.echo("\n".join(R))


# show command:
# ------------------------------------------------------------------------------


@cli.command()
@click.option(
    "-f",
    "--format",
    "form",
    type=click.Choice(formats),
    default="C",
    show_default=True,
    help="output identifier data translated in chosen format",
)
@click.option(
    "-r", "--recursive", is_flag=True, help="recursively search for all types"
)
@click.argument("identifier", nargs=1, type=click.STRING)
@click.pass_context
def show(ctx, form, recursive, identifier):
    """Print a definition
    from the remote database (or the local database if no remote is found) in
    C/C++ (default) format or other supported format (ctypes, amoco, raw).
    If the recursive option is used, the printed definitions include all
    other types required by the topmost definition.
    """
    db = ctx.obj["db"]
    if recursive is True:
        recursive = set()
    Q = where("id") == identifier
    if db.contains(Q):
        for l in db.search(Q):
            x = ccore.from_db(l)
            click.echo(x.show(db, recursive, form=form))
    else:
        click.secho("identifier '%s' not found" % identifier, fg="red", err=True)


# info command:
# ------------------------------------------------------------------------------


@cli.command()
@click.argument("identifier", nargs=1, type=click.STRING)
@click.pass_context
def info(ctx, identifier):
    """Get database internal informations about a definition."""
    db = ctx.obj["db"]
    Q = where("id") == identifier
    if db.contains(Q):
        from ctypes import sizeof
        for l in db.search(Q):
            x = ccore.from_db(l)
            click.echo("identifier: {}".format(identifier))
            click.secho("class     : {}".format(l["cls"]), fg="cyan")
            click.echo("source    : {}".format(l["src"]))
            click.secho("tag       : {}".format(l["tag"]), fg="magenta")
            if x._is_struct or x._is_union or x._is_class:
                try:
                    t = x.build(db)
                except (TypeError, KeyError) as e:
                    what = e.args[0]
                    click.secho(
                        "can't build %s:\nmissing type: '%s'" % (x.identifier, what),
                        fg="red",
                        err=True,
                    )
                    click.echo("", err=True)
                    continue
                F = []
                for i, f in enumerate(t._fields_):
                    field = getattr(t, f[0])
                    if (field.size>>16):
                        o = float("%d.%d"%(field.offset,field.size&0xffff))
                        s = float(".%d"%(field.size>>16))
                        F.append((o,s))
                        o,s = field.offset,sizeof(f[1])
                    else:
                        o,s = field.offset,field.size
                        F.append((o,s))
                xsize = o+s
                click.secho("size      : {}".format(xsize), fg="yellow")
                click.secho(
                    "offsets   : {}".format([(f[0], f[1]) for f in F]), fg="yellow"
                )

    else:
        click.secho("identifier '%s' not found" % identifier, fg="red", err=True)


# store command:
# ------------------------------------------------------------------------------


@cli.command()
@click.option(
    "-u", "--update", is_flag=False, help="update local base with all subtypes"
)
@click.pass_context
def store(ctx, update):
    """Update the remote database with definitions from the current local database.
    If the update option flag is set, the dependency graph of local definitions
    is computed before pushing definitions to the remote database.
    """
    db = ctx.obj["db"]
    rdb = db.rdb
    # force all operations to occur on local database:
    db.rdb = None
    Done = []
    for l in db.search(db.tag):
        x = ccore.from_db(l)
        if not conf.QUIET:
            click.echo("unfolding '%s'..." % x.identifier, nl=False)
        try:
            l["use"] = list(x.unfold(db).subtypes.keys())
        except:
            if not conf.QUIET:
                click.secho("failed.", fg="red")
        else:
            if not conf.QUIET:
                click.secho("ok.", fg="green")
            if update is True:
                db.ldb.update(l)
        Done.append(l)
    if rdb:
        if not conf.QUIET:
            click.echo("remote db insert multiple ...", nl=False)
        try:
            rdb.insert_multiple(Done)
        except Exception:
            if not conf.QUIET:
                click.secho("failed.", fg="red")
        else:
            if not conf.QUIET:
                click.secho("done.", fg="green")
            if not update:
                db.ldb.remove(doc_ids=[l.doc_id for l in Done])
    # restore remote database operations:
    db.rdb = rdb


# fetch command:
# ------------------------------------------------------------------------------


@cli.command()
@click.pass_context
def fetch(ctx):
    """Fetch a collection of definitions from the remote database into
    the local database.
    """
    # db = ctx.obj['db']
    raise NotImplementedError


# tags command:
# ------------------------------------------------------------------------------


@cli.command()
@click.pass_context
def tags(ctx):
    """Get the list of all tags in the remote (or local if remote is not found)
    database.
    """
    db = ctx.obj["db"]
    T = set()
    for l in db.search(where("tag").exists()):
        if "tag" in l:
            T.add(l["tag"])
    for t in T:
        click.echo("%s" % t)


# sources command:
# ------------------------------------------------------------------------------


@cli.command()
@click.pass_context
def sources(ctx):
    """Get the list of all source files referenced in the remote (or local if
    remote is not found) database.
    """
    db = ctx.obj["db"]
    T = set()
    for l in db.search(where("tag").exists()):
        T.add(l["src"])
    for t in T:
        if "?_" in t:
            continue
        if t.startswith("struct "):
            continue
        if t.startswith("union "):
            continue
        click.echo("%s" % t)


# stats command:
# ------------------------------------------------------------------------------


@cli.command()
@click.pass_context
def stats(ctx):
    """Show some statistics about the remote (or local if
    remote is not found) database.
    """
    db = ctx.obj["db"]
    click.echo("database: ")
    click.echo("       .local     : %s" % str(db.ldb))
    click.echo("       .url       : %s" % str(db.rdb))
    click.echo("documents:")
    F = db.search(where("cls") == "cFunc")
    click.echo("       .cFunc     : %d" % len(F))
    C = db.search(where("cls") == "cClass")
    click.echo("       .cClass    : %d" % len(C))
    S = db.search(where("cls") == "cStruct")
    click.echo("       .cStruct   : %d" % len(S))
    U = db.search(where("cls") == "cUnion")
    click.echo("       .cUnion    : %d" % len(U))
    E = db.search(where("cls") == "cEnum")
    click.echo("       .cEnum     : %d" % len(E))
    T = db.search(where("cls") == "cTypedef")
    click.echo("       .cTypedef  : %d" % len(T))
    M = db.search(where("cls") == "cMacro")
    click.echo("       .cMacro    : %d" % len(M))
    P = db.search(where("cls") == "cTemplate")
    click.echo("       .cTemplate : %d" % len(P))
    click.echo("structures:")
    l, s = max(((len(s["val"]), s["id"]) for s in S))
    click.echo("  max fields: %d (in '%s')" % (l, s))


@cli.command()
@click.pass_context
def server(ctx):
    db = ctx.obj["db"]
    click.echo("starting server mode...")
    from ccrawl.srv.main import run

    run(ctx)
