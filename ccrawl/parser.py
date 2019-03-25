import os
import re
from click import echo,secho
from clang.cindex import CursorKind,TranslationUnit,Index
import tempfile
import hashlib
from collections import OrderedDict
from ccrawl import conf
from ccrawl.core import *

g_indent = 0

CHandlers = {}

# ccrawl classes for clang parser:
#------------------------------------------------------------------------------

def declareHandler(kind):
    """ Decorator used to register a handler associated to
        a clang cursor kind/type. The decorated handler function
        will be called to process each cursor of this kind.
    """
    def decorate(f):
        CHandlers[kind] = f
        return f
    return decorate

# cursor types that will be parsed to instanciate ccrawl
# objects:
TYPEDEF_DECL  = CursorKind.TYPEDEF_DECL
STRUCT_DECL   = CursorKind.STRUCT_DECL
UNION_DECL    = CursorKind.UNION_DECL
ENUM_DECL     = CursorKind.ENUM_DECL
FUNCTION_DECL = CursorKind.FUNCTION_DECL
MACRO_DEF     = CursorKind.MACRO_DEFINITION

# handlers:

@declareHandler(FUNCTION_DECL)
def FuncDecl(cur):
    identifier = cur.spelling
    proto = cur.type.spelling
    f = re.sub('__attribute__.*','',proto)
    #f = c_type(f)
    #args = f.pstack[-1].f
    #f.pstack.pop()
    #t = f.show()
    return identifier,cFunc(f)

@declareHandler(MACRO_DEF)
def MacroDef(cur):
    if cur.extent.start.file:
        identifier = cur.spelling
        toks = []
        for t in list(cur.get_tokens())[1:]:
            pre = '' if t.spelling in (',','*','#','(',')') else ' '
            toks.append(pre+t.spelling)
        s = ''.join(toks)
        return identifier,cMacro(s.replace('( ','('))

@declareHandler(TYPEDEF_DECL)
def TypeDef(cur):
    dt = cur.underlying_typedef_type
    if '(anonymous' in dt.spelling:
        dt = dt.get_canonical().spelling
    else:
        dt = dt.spelling
    dt = get_uniq_typename(dt)
    return cur.type.spelling,cTypedef(dt)

@declareHandler(STRUCT_DECL)
def StructDecl(cur):
    return Struct_Union(cur,'struct')

@declareHandler(UNION_DECL)
def UnionDecl(cur):
    return Struct_Union(cur,'union')

@declareHandler(ENUM_DECL)
def EnumDecl(cur):
    typename = cur.type.spelling
    if not typename.startswith('enum'):
        typename = 'enum %s'%typename
    typename = get_uniq_typename(typename)
    S = cEnum()
    S._in = str(cur.extent.start.file)
    a = 0
    global g_indent
    g_indent += 1
    for f in cur.get_children():
        #if conf.DEBUG: echo('\t'*g_indent + str(f.kind))
        if not f.is_definition():
            if a: raise ValueError
        if f.kind is CursorKind.ENUM_CONSTANT_DECL:
            S[f.spelling] = f.enum_value
    g_indent -= 1
    return typename,S

def Struct_Union(cur,cat):
    typename = cur.type.spelling
    if not typename.startswith(cat):
        typename = '%s %s'%(cat,typename)
    typename = get_uniq_typename(typename)
    if   cat=='struct': S = cStruct()
    elif cat =='union': S = cUnion()
    S._in = str(cur.extent.start.file)
    local = {}
    global g_indent
    g_indent += 1
    for f in cur.get_children():
        #if conf.DEBUG: echo('\t'*g_indent + str(f.kind)+'='+str(f.spelling))
        if not f.is_definition():
            continue
        if f.kind in (STRUCT_DECL,UNION_DECL,ENUM_DECL):
            identifier,slocal = CHandlers[f.kind](f)
            local[identifier] = slocal
        elif f.kind == CursorKind.FIELD_DECL:
            comment = f.brief_comment or f.raw_comment
            t = f.type.spelling
            if '(anonymous' in t:
                t = get_uniq_typename(f.type.get_canonical().spelling)
            if cat=='struct':
                S.append((t, f.spelling, comment))
            elif cat=='union':
                S[f.spelling] = (t,comment)
    S.local = local
    g_indent -= 1
    return typename,S

def get_uniq_typename(t):
    if not '(anonymous' in t: return t
    kind,t = t.split(' ',1)
    x = re.compile('\(anonymous .*\)')
    s = x.search(t).group(0)
    h = hashlib.sha256(s.encode('ascii')).hexdigest()[:8]
    return '%s ?_%s'%(kind,h)

# ccrawl 'parse' function(s), wrapper of clang index.parse;
#------------------------------------------------------------------------------

def parse(filename,
          args=None,unsaved_files=None,options=None,
          kind=None,
          tag=None):
    """ Function that parses the input filename and returns the
    dictionary of name:object
    """
    # clang parser cindex options:
    if options is None:
        # detailed processing allows to get macros in iterated cursors:
        options  = TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        # allow incomplete files
        options |= TranslationUnit.PARSE_INCOMPLETE
        # ignore functions bodies
        options |= TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
    if args is None:
        # clang: keep comments in parser output
        _args = ['-ferror-limit=0','-fparse-all-comments']
    else:
        _args = args[:]
    if not conf.config.Collect.strict:
        # in non strict mode, we allow types to be undefined by catching
        # the missing type from diagnostics and defining a fake type instead
        # rather than letting clang use its default int type directly.
        fd,tmpf = tempfile.mkstemp(prefix='ccrawl-')
        os.close(fd)
        fd,depf = tempfile.mkstemp(prefix='ccrawl-')
        os.close(fd)
        _args += ['-M', '-MG', '-MF%s'%depf,'-include%s'%tmpf]
    if conf.DEBUG: echo('\nfilename: %s, args: %s'%(filename,_args))
    if unsaved_files is None:
        unsaved_files = []
    if kind is None:
        kind = CHandlers
    else:
        for k in kind: assert (k in CHandlers)
    defs = OrderedDict()
    index = Index.create()
    # call clang parser:
    try:
        tu = index.parse(filename,_args,unsaved_files,options)
    except:
        if not conf.QUIET:
            secho('[err]',fg='red')
            if conf.VERBOSE:
                secho('clang index.parse error',fg='red')
        return []
    else:
        if conf.VERBOSE:
            echo(':')
    name = tu.cursor.extent.start.file.name
    # get diagnostics and check if a reparse is needed
    # to handle unknown types (due to missing headers)
    ok = False
    reparse = 0
    while not ok:
        # normally we don't loop unless we have errors in diagnostics
        ok = True
        trycplusplus = False
        # so lets check errors:
        for err in tu.diagnostics:
            if err.severity==3:
                if conf.VERBOSE: secho(err.format(),fg='yellow')
                # if its a missing typename, we add it and ask for reparse:
                if 'unknown type name' in err.spelling or \
                   'has incomplete' in err.spelling:
                    tn = re.findall("'(.*)'",err.spelling)
                    if conf.config.Collect.strict: return None
                    add_fake_type(tmpf,tn[0])
                    ok = False
                # otherwise we will check if input is C++
                elif ("expected ';'" in err.spelling) or\
                     ("'namespace'" in err.spelling):
                    trycplusplus = True
                    ok = True
                    break
            elif err.severity==4:
                # this should not happen anymore thanks to -M -MG opts...
                # we keep it here just in case.
                if conf.VERBOSE: secho(err.format(),bg='red')
                if conf.config.Collect.strict: return None
                if 'file not found' in err.spelling:
                    uf = re.findall("'(.*)'",err.spelling)
                    unsaved_files.append(('%s/%s'%(tmpf,uf[0]),''))
                    ok = False
        if trycplusplus:
            A = ['-x','c++','-std=c++11']
            try:
                tu = index.parse(filename,_args+A,unsaved_files,options)
            except:
                if not conf.QUIET:
                    secho('[err]'.rjust(8),fg='red')
                    if conf.VERBOSE:
                        secho('clang index.parse error (c++)',fg='red')
            else:
                # seems like a C++ file...lets skip it
                if not conf.QUIET:
                    secho('[c++]'.rjust(8),fg='yellow')
                tu = None
        if not ok:
            try:
                tu.reparse(unsaved_files,options)
            except:
                if not conf.QUIET:
                    secho('[err]'.rjust(8),fg='red')
                    if conf.VERBOSE:
                        secho('clang reparse error, file ignored',fg='red')
                tu = None
            else:
                reparse += 1
                if reparse==3:
                    if conf.VERBOSE: secho('parsed x3 limit!',fg='red')
                    ok = True
    # cleanup tempfiles
    if not conf.config.Collect.strict:
        for f in (tmpf,depf):
            if conf.DEBUG: secho('removing tmp file %s'%f,fg='magenta')
            if os.path.exists(f): os.remove(f)
    if tu is None: return []
    # walk down all AST to get all cursors:
    pool = [c for c in tu.cursor.get_children()]
    # fill defs with collected cursors:
    while len(pool)>0:
        cur = pool.pop(0)
        #if conf.DEBUG: echo('%s'%cur.kind)
        if not conf.config.Collect.strict and \
           cur.location.file and cur.location.file.name == tmpf:
            continue
        if cur.kind in kind:
            kv = CHandlers[cur.kind](cur)
            if kv:
                ident,cobj = kv
                if cobj:
                    for x in cobj.to_db(ident, tag, cur.location.file.name):
                        defs[x['id']] = x
    if not conf.QUIET:
        secho(('[%3d]'%len(defs)).rjust(8), fg='green' if reparse<3 else 'yellow')
        if reparse==3 and conf.VERBOSE:
            secho('too many errors...parser stopped',fg='yellow')
    return defs.values()

def parse_string(s,args=None,options=0):
    """ Crawl wrapper to parse an input string rather than file.
    """
    # create a tmp filename (file can be removed immediately)
    tmph = tempfile.mkstemp(prefix='ccrawl-',suffix='.h')[1]
    os.remove(tmph)
    return parse(tmph,args,[(tmph,s)],options)

def add_fake_type(f,t):
    if t in ('void',): return
    with open(f,'a') as i:
        if 'struct ' in t: i.write('%s {int dummy};'%t)
        elif 'union ' in t: i.write('%s {int dummy};'%t)
        elif 'enum ' in t: i.write('%s {dummy=0};'%t)
        else: i.write('typedef int %s;\n'%t)
        i.flush()
        if conf.VERBOSE: secho("fake type '%s' added"%t,fg='green')
