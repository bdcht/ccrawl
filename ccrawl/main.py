import os
import re
import time
import click
from ccrawl import conf
from ccrawl.formatters import formats
from ccrawl.parser import TYPEDEF_DECL, STRUCT_DECL, UNION_DECL
from ccrawl.parser import FUNCTION_DECL, MACRO_DEF
from ccrawl.parser import parse,ccore,c_type
from ccrawl.db import Proxy,Query,where

# ccrawl commands utilities:
#------------------------------------------------------------------------------

def spawn_console(ctx):
    """ Crawl console for interactive mode.
    The console is based on IPython if found, or uses CPython otherwise.
    When interactive, ccrawl is configured in non strict collect mode.
    """
    c = conf.config
    if not ctx.obj['db']:
        ctx.obj['db'] = Proxy(c.Database)
    cvars = dict(globals(),**locals())
    cvars.update(ctx.obj)
    #c.Collect.strict=False
    if c.Terminal.console.lower() == 'ipython':
        try:
            from IPython import start_ipython
        except ImportError:
            if conf.VERBOSE: click.echo('ipython not found')
            c.Terminal.console = 'python'
        else:
            ic = c.src.__class__()
            ic.TerminalTerminalIPythonApp.display_banner = False
            ic.InteractiveShellApp.exec_lines = ["print(conf.BANNER)"]
            start_ipython(argv=[],config=ic,user_ns=cvars)
    if c.Terminal.console.lower() == 'python':
        from code import interact
        try:
            import readline,rlcompleter
            readline.set_completer(rlcompleter.Completer(cvars).complete)
            readline.parse_and_bind("Tab: complete")
            del readline,rlcompleter
        except ImportError:
            click.echo('readline not found')
        interact(banner=conf.BANNER+"\n",
                 local=cvars)

#------------------------------------------------------------------------------
# Crawl Commands :
#------------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.option('-v','--verbose',
              is_flag=True,default=False)
@click.option('-q','--quiet',
              is_flag=True,default=False)
@click.option('-b','--db')
@click.option('-l','--local',
              type=click.Path(exists=False,file_okay=True,dir_okay=False))
@click.option('-c','--configfile',
              type=click.Path(exists=True,file_okay=True,dir_okay=False))
@click.option('-g','--tag',help='use given tag in all commands')
@click.pass_context
def cli(ctx,verbose,quiet,db,local,configfile,tag):
    ctx.obj = {}
    c = conf.config = conf.Config(configfile)
    if quiet:
        verbose = False
    debug = c.Terminal.debug
    c.Terminal.verbose = verbose | debug
    c.Terminal.quiet = quiet
    c.Terminal.width = click.get_terminal_size()[0]
    if conf.VERBOSE:
        if c.src:
            click.echo("config file '%s' loaded"%c.f)
        else:
            click.echo("default config loaded (file '%s' not found)"%c.f)
    if db:
        c.Database.url = db
    if local:
        c.Database.local = local
    if conf.VERBOSE:
        click.echo('loading local database %s ...'%c.Database.local,nl=False)
    try:
        ctx.obj['db'] = Proxy(c.Database)
        if tag: ctx.obj['db'].set_tag(tag)
    except:
        click.secho('failed',fg='red')
        exit(1)
    if conf.VERBOSE:
        click.echo('done')
        if c.Database.url and ctx.obj['db'].rdb:
            click.echo('remote database is: %s'%c.Database.url)
        elif c.Database.url:
            click.secho('remote database (%s) not connected'%c.Database.url,fg='red')
        else:
            click.echo('no remote database')
    if ctx.invoked_subcommand is None:
        spawn_console(ctx)
    else:
        if conf.DEBUG:
            click.echo('COMMAND: %s'%ctx.invoked_subcommand)

# Collect command:
#------------------------------------------------------------------------------

def do_collect(ctx,src):
    ctx.invoke(collect,allc=False,types=False,functions=False,macros=False,
                       strict=False,xclang='',src=src)

@cli.command()
@click.option('-a','--all' ,'allc',is_flag=True,
              help='collect data from all files rather than headers only')
@click.option('-t','--types'      ,is_flag=True,help='collect types')
@click.option('-f','--functions'  ,is_flag=True,help='collect functions')
@click.option('-m','--macros'     ,is_flag=True,help='collect macros')
@click.option('-s','--strict'     ,is_flag=True,help='strict mode')
@click.option('--clang','xclang', help='pass parameters to clang')
@click.argument('src', nargs=-1, type=click.Path(exists=True,
                                                 file_okay=True,
                                                 readable=True))
@click.pass_context
def collect(ctx,allc,types,functions,macros,strict,xclang,src):
    """ Command that collects type/union/enum definitions, functions prototypes
    or macro definitions from SRC path into a local database. The collected
    definitions are tagged with the global option TAG string or with a timestamp.

    The extraction is performed using libclang parser which can receive
    specific parameters through the --clang option.
    By default, only header files are parsed (the --all option allows to
    collect from all input files) and all implemented collectors are used.

    In strict mode, the clang options need to conform to the makefile
    that lead to the compilation of all input source (i.e. clang diagnostics
    errors are not bypassed with fake types).
    """
    c = conf.config
    F = lambda f:f.endswith('.h') or f.endswith('.hpp')
    K = None
    c.Collect.strict |= strict
    if allc is True:
        F = lambda f: (f.endswith('.c') or f.endswith('.cpp') or F(f))
    if types or functions or macros:
        K = []
        if types: K += [TYPEDEF_DECL, STRUCT_DECL, UNION_DECL]
        if functions: K += [FUNCTION_DECL]
        if macros: K += [MACRO_DEF]
    tag = ctx.obj['db'].tag.hashval[-1] or None
    if tag is None:
        tag = str(time.time())
    # filters:
    ctx.obj['F'] = F
    # selected kinds of cursors to collect:
    ctx.obj['K'] = K
    # temporary database cache:
    dbo = {}
    # if no clang params is provided, use defaults:
    if xclang is None:
        # keep comments in parser output:
        args  = ['-ferror-limit=0',
                 '-fparse-all-comments',
                ]
        # add header directories:
        for i in (D for D in src if os.path.isdir(D)):
            args.append('-I%s'%i)
    else:
        args = xclang.split(' ')
    # count source files:
    FILES = set()
    for D in src:
        if os.path.isdir(D):
            for dirname,subdirs,files in os.walk(D.rstrip('/')):
                for f in filter(F,files):
                    filename = '%s/%s'%(dirname,f)
                    FILES.add(filename)
        elif os.path.isfile(D) and F(D):
            FILES.add(D)
    total = len(FILES)
    W = c.Terminal.width-12
    # parse and collect all sources:
    while len(FILES)>0:
        t0 = time.time()
        filename = FILES.pop()
        if not c.Terminal.quiet:
            p = (((total-len(FILES))*100.)/total)
            click.echo(('[%3d%%] %s '%(p,filename)).ljust(W),nl=False)
        l = parse(filename,args,kind=K,tag=tag)
        t1 = time.time()
        if c.Terminal.timer:
            click.secho('(%.2f+'%(t1-t0),nl=False,fg='cyan')
        if l is None:
            return -1
        if len(l)>0:
            # remove already processed/included files
            FILES.difference_update([el['src'] for el in l])
            # remove duplicates into dbo:
            for x in l: dbo[x['id']+x['src']] = x
        t2 = time.time()
        if c.Terminal.timer:
            click.secho('%.2f)'%(t2-t1),fg='cyan')
    db = ctx.obj['db']
    if not c.Terminal.quiet:
        click.echo('-'*(c.Terminal.width-1))
        click.echo('saving database...'.ljust(W),nl=False)
    N = len(dbo)
    db.insert_multiple(dbo.values())
    db.close()
    if not c.Terminal.quiet:
        click.secho(('[%4d]'%N).rjust(12),fg='green')
    return 0

# match command:
#------------------------------------------------------------------------------

@cli.command()
@click.argument('rex',nargs=1,type=click.STRING)
@click.pass_context
def match(ctx,rex):
    db = ctx.obj['db']
    if db.rdb:
        L = db.rdb.match(rex)
    else:
        cx = re.compile(rex)
        look = (lambda v: cx.search(str(v)))
        Q = (where('id').search(rex)) | (where('val').test(look))
        L = db.search(Q)
    for l in L:
        click.echo('found ',nl=False)
        click.secho('%s '%l['cls'],nl=False,fg='cyan')
        click.echo('identifer ',nl=False)
        click.secho('"%s"'%l['id'],nl=False,fg='magenta')
        if look(l['val']):
            click.echo(' with matching value',nl=False)
        click.echo('')
    return L

# find commands:
#------------------------------------------------------------------------------

@cli.group(invoke_without_command=True)
@click.option('-a','--and','ands',type=click.STRING,multiple=True)
@click.option('-o','--or' ,'ors', type=click.STRING,multiple=True)
@click.pass_context
def find(ctx,ands,ors):
    Q = Query()
    try:
        for x in ands:
            k,v = x.split('=')
            Q &= (where(k).search(v))
        for x in ors:
            k,v = x.split('=')
            Q |= (where(k).search(v))
    except:
        click.secho('invalid options (ignored)',fg='yellow')
    ctx.obj['find'] = Q
    if ctx.invoked_subcommand is None:
        db = ctx.obj['db']
        L = db.search(Q)
        for l in L:
            click.echo('found ',nl=False)
            click.secho('%s '%l['cls'],nl=False,fg='cyan')
            click.echo('identifer ',nl=False)
            click.secho('"%s"'%l['id'],fg='magenta')
    else:
        if conf.DEBUG:
            click.echo('FIND_COMMAND: %s'%ctx.invoked_subcommand)

@find.command()
@click.argument('proto',nargs=-1,type=click.STRING)
@click.pass_context
def prototype(ctx,proto):
    reqs = {}
    try:
        for p in proto:
            pos,t = p.split(':')
            pos = int(pos)
            reqs[pos] = c_type(t).show()
    except:
        click.secho('invalid arguments',fg='red')
        return
    db = ctx.obj['db']
    Q  = ctx.obj.get('find',Query())
    L = db.search(Q,cls='cFunc')
    R = []
    with click.progressbar(L) as pL:
        for l in pL:
            x = ccore.from_db(l)
            P = [c_type(t).show() for t in x.argtypes()]
            P.insert(0,c_type(x.restype()).show())
            if max(reqs)>=len(P): continue
            if not all(((t==P[i]) for (i,t) in reqs.items())):
                continue
            R.append(x.show(db,form='C'))
    if R:
        click.echo('\n'.join(R))

@find.command()
@click.option('-m','--mask',is_flag=True)
@click.option('-s','--symbol',default='')
@click.argument('val')
@click.pass_context
def constant(ctx,mask,symbol,val):
    value = int(val,0)
    db = ctx.obj['db']
    Q  = ctx.obj['find']
    Q &= ((where('cls')=='cMacro')|(where('cls')=='cEnum'))
    L = db.search(Q)
    R = []
    with click.progressbar(L) as pL:
        for l in pL:
            x = ccore.from_db(l)
            if x._is_macro:
                if not (symbol in x.identifier):
                    continue
                try:
                    v = int(x,0)
                except:
                    continue
                else:
                    if v==value:
                        R.append(x.identifier+'\n')
                    elif mask and (symbol in x.identifier):
                        if v<value and v&value:
                            R.append(x.identifier+' | ')
            else:
                for k,v in x.items():
                    if v==value and (symbol in k):
                        R.append(k+'\n')
                        break
                    elif mask and (symbol in k):
                        if v<value and v&value:
                            R.append(k+' | ')
    if R:
        s = ''.join(R)
        click.echo(s.strip(' |\n'))

@find.command()
@click.argument('conds',nargs=-1,type=click.STRING)
@click.pass_context
def struct(ctx,conds):
    reqs = {}
    try:
        for p in conds:
            off,t = p.split(':')
            if off=='*':
                sz = int(t)
                reqs[off] = sz
            else:
                off = int(off)
                reqs[off] = int(t) if t[0]=='+' else c_type(t).show()
    except:
       click.secho('invalid arguments',fg='red')
       return
    db = ctx.obj['db']
    Q  = ctx.obj['find']
    L = db.search(Q,cls='cStruct')
    R = []
    with click.progressbar(L) as pL:
        for l in pL:
            x = ccore.from_db(l)
            #x.unfold(db,limit=0)
            try:
                t = x.build(db)
            except:
                click.secho("can't build %s..skipping."%x.identifier,fg='red')
                continue
            F = []
            for i,f in enumerate(t._fields_):
                field = getattr(t,f[0])
                F.append((field.offset,field.size,c_type(x[i][0]).show()))
            xsize = F[-1][0]+F[-1][1]
            if '*' in reqs:
                if not (reqs.pop('*')==xsize): continue
            F = dict(((f[0],f[1:3]) for f in F))
            ok = True
            for o,s in reqs.items():
                if not (o in F):
                    ok = False
                    break
                if not (s in F[o]):
                    ok = False
                    break
            if ok:
                R.append(x.show(db,form='C'))
    if R:
        click.echo('\n'.join(R))


# show command:
#------------------------------------------------------------------------------

@cli.command()
@click.option('-f','--format','form',
              type=click.Choice(formats),default='C',show_default=True,
              help='output identifier data translated in chosen format')
@click.option('-r','--recursive',is_flag=True,
              help='recursively search for all types')
@click.argument('identifier',nargs=1,type=click.STRING)
@click.pass_context
def show(ctx,form,recursive,identifier):
    db = ctx.obj['db']
    if recursive is True:
        recursive = set()
    Q = where('id')==identifier
    if db.contains(Q):
        for l in db.search(Q):
            x = ccore.from_db(l)
            click.echo(x.show(db,recursive,form=form))
    else:
        click.secho("identifier '%s' not found"%identifier,fg='red')

# info command:
#------------------------------------------------------------------------------

@cli.command()
@click.argument('identifier',nargs=1,type=click.STRING)
@click.pass_context
def info(ctx,identifier):
    db = ctx.obj['db']
    Q = where('id')==identifier
    if db.contains(Q):
        for l in db.search(Q):
            x = ccore.from_db(l)
            click.echo ("identifier: {}".format(identifier))
            click.secho("class     : {}".format(l['cls']),fg='cyan')
            click.echo ("source    : {}".format(l['src']))
            click.secho("tag       : {}".format(l['tag']),fg='magenta')
            if x._is_struct or x._is_union:
                try:
                    t = x.build(db)
                except:
                    click.secho("can't build %s..skipping."%x.identifier,fg='red')
                    click.echo('')
                    continue
                F = []
                for i,f in enumerate(t._fields_):
                    field = getattr(t,f[0])
                    F.append((field.offset,field.size,c_type(x[i][0]).show()))
                xsize = F[-1][0]+F[-1][1]
                click.secho("size      : {}".format(xsize),fg='yellow')
                click.secho("offsets   : {}".format([(f[0],f[1]) for f in F]),fg='yellow')

    else:
        click.secho("identifier '%s' not found"%identifier,fg='red')

# store command:
#------------------------------------------------------------------------------

@cli.command()
@click.option('-u','--update',is_flag=False,
              help='update local base with all subtypes')
@click.pass_context
def store(ctx,update):
    db = ctx.obj['db']
    rdb = db.rdb
    db.rdb = None
    Done = []
    for l in db.search(db.tag):
        x = ccore.from_db(l)
        if conf.VERBOSE:
            click.echo("unfolding '%s'..."%x.identifier,nl=False)
        l['use'] = [t.identifier for t in filter(None,x.unfold(db).subtypes)]
        if conf.VERBOSE:
            click.echo('done')
        if update is True:
            db.ldb.update(l)
        Done.append(l)
    if rdb:
        if conf.VERBOSE:
            click.echo('remote db insert multiple ...',nl=False)
        rdb.insert_multiple(Done)
        if conf.VERBOSE:
            click.echo('done')
        if not update:
            db.ldb.remove(doc_ids=[l.doc_id for l in Done])
    db.rdb = rdb

# fetch command:
#------------------------------------------------------------------------------

@cli.command()
@click.pass_context
def fetch(ctx):
    db = ctx.obj['db']

# tags command:
#------------------------------------------------------------------------------

@cli.command()
@click.pass_context
def tags(ctx):
    db = ctx.obj['db']
    T = set()
    for l in db.search():
        if 'tag' in l: T.add(l['tag'])
    for t in T:
        click.echo("%s"%t)

# sources command:
#------------------------------------------------------------------------------

@cli.command()
@click.pass_context
def sources(ctx):
    db = ctx.obj['db']
    T = set()
    for l in db.search():
        T.add(l['src'])
    for t in T:
        if '?_' in t: continue
        if t.startswith('struct '): continue
        if t.startswith('union '): continue
        click.echo("%s"%t)

# stats command:
#------------------------------------------------------------------------------

@cli.command()
@click.pass_context
def stats(ctx):
    db = ctx.obj['db']
    click.echo('database: ')
    click.echo('       .local: %s'%str(db.ldb))
    click.echo('       .url  : %s'%str(db.rdb))
    click.echo('documents:')
    F = db.search(where('cls')=='cFunc')
    click.echo('       .cFunc   : %d'%len(F))
    C = db.search(where('cls')=='cClass')
    click.echo('       .cClass  : %d'%len(C))
    S = db.search(where('cls')=='cStruct')
    click.echo('       .cStruct : %d'%len(S))
    U = db.search(where('cls')=='cUnion')
    click.echo('       .cUnion  : %d'%len(U))
    E = db.search(where('cls')=='cEnum')
    click.echo('       .cEnum   : %d'%len(E))
    T = db.search(where('cls')=='cTypedef')
    click.echo('       .cTypedef: %d'%len(T))
    M = db.search(where('cls')=='cMacro')
    click.echo('       .cMacro  : %d'%len(M))
    click.echo('structures:')
    l,s = max(((len(s['val']),s['id']) for s in S))
    click.echo("  max fields: %d (in '%s')"%(l,s))
