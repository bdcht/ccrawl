import pdb
import os
import re
from click import echo,secho
from clang.cindex import CursorKind,TokenKind,TranslationUnit,Index
import clang.cindex
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

spec_chars = (',','*','::','&','(',')','[',']')

# cursor types that will be parsed to instanciate ccrawl
# objects:
TYPEDEF_DECL  = CursorKind.TYPEDEF_DECL
STRUCT_DECL   = CursorKind.STRUCT_DECL
UNION_DECL    = CursorKind.UNION_DECL
ENUM_DECL     = CursorKind.ENUM_DECL
FUNCTION_DECL = CursorKind.FUNCTION_DECL
MACRO_DEF     = CursorKind.MACRO_DEFINITION
CLASS_DECL    = CursorKind.CLASS_DECL
FUNC_TEMPLATE = CursorKind.FUNCTION_TEMPLATE
CLASS_TEMPLATE= CursorKind.CLASS_TEMPLATE
CLASS_TPSPEC  = CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION
NAMESPACE     = CursorKind.NAMESPACE

# handlers:

@declareHandler(FUNCTION_DECL)
def FuncDecl(cur,cxx,errors=None):
    identifier = cur.spelling
    t = cur.type.spelling
    proto = fix_type_conversion(cur,t,cxx,errors)
    return identifier,cFunc(proto)

@declareHandler(MACRO_DEF)
def MacroDef(cur,cxx,errors=None):
    if cur.extent.start.file:
        identifier = cur.spelling
        toks = []
        for t in list(cur.get_tokens())[1:]:
            pre = '' if t.spelling in spec_chars else ' '
            toks.append(pre+t.spelling)
        s = ''.join(toks)
        return identifier,cMacro(s.replace('( ','('))

@declareHandler(TYPEDEF_DECL)
def TypeDef(cur,cxx,errors=None):
    identifier = cur.type.spelling
    dt = cur.underlying_typedef_type
    if '(anonymous' in dt.spelling: dt = dt.get_canonical()
    t = fix_type_conversion(cur,dt.spelling,cxx,errors)
    t = get_uniq_typename(t)
    if conf.DEBUG: echo('\t'*g_indent+'make unique: %s'%t)
    return identifier,cTypedef(t)

@declareHandler(STRUCT_DECL)
def StructDecl(cur,cxx,errors=None):
    typename = cur.type.spelling
    if cxx:
        typename = cur.type.get_canonical().spelling
        typename = 'struct '+typename
    else:
        typename = get_uniq_typename(typename)
        if conf.DEBUG: echo('\t'*g_indent+'make unique: %s'%typename)
    S = cClass() if cxx else cStruct()
    SetStructured(cur,S,errors)
    return typename,S

@declareHandler(UNION_DECL)
def UnionDecl(cur,cxx,errors=None):
    typename = cur.type.spelling
    if cxx:
        typename = cur.type.get_canonical().spelling
        typename = 'union '+typename
    else:
        typename = get_uniq_typename(typename)
        if conf.DEBUG: echo('\t'*g_indent+'make unique: %s'%typename)
    S = cClass() if cxx else cUnion()
    SetStructured(cur,S,errors)
    return typename,S

@declareHandler(CLASS_DECL)
def ClassDecl(cur,cxx,errors=None):
    typename = "class %s"%(cur.type.get_canonical().spelling)
    if conf.DEBUG: echo('\t'*g_indent+'%s'%typename)
    S = cClass()
    SetStructured(cur,S,errors)
    return typename,S

@declareHandler(ENUM_DECL)
def EnumDecl(cur,cxx,errors=None):
    global g_indent
    typename = cur.type.spelling
    if cxx:
        typename = cur.type.get_canonical().spelling
        typename = 'enum '+typename
    else:
        typename = get_uniq_typename(typename)
        if conf.DEBUG: echo('\t'*g_indent+'make unique: %s'%typename)
    S = cEnum()
    S._in = str(cur.extent.start.file)
    a = 0
    g_indent += 1
    for f in cur.get_children():
        if conf.DEBUG: echo('\t'*g_indent + str(f.kind))
        if not f.is_definition():
            if a: raise ValueError
        if f.kind is CursorKind.ENUM_CONSTANT_DECL:
            S[f.spelling] = f.enum_value
    g_indent -= 1
    return typename,S

@declareHandler(FUNC_TEMPLATE)
def FuncTemplate(cur,cxx,errors=None):
    identifier = cur.displayname
    proto = cur.type.spelling
    TF = template_fltr
    p = [x.spelling for x in filter(TF,cur.get_children())]
    f = re.sub('__attribute__.*','',proto)
    return identifier,cTemplate(params=p,cFunc=cFunc(f))

@declareHandler(CLASS_TEMPLATE)
def ClassTemplate(cur,cxx,errors=None):
    identifier = cur.displayname
    TF = template_fltr
    p = [x.spelling for x in filter(TF,cur.get_children())]
    # damn libclang...children should be a STRUCT_DECL or CLASS_DECL !
    # (if not, there should be a STRUCT_TEMPLATE as well...)
    toks = [x.spelling for x in cur.get_tokens()]
    try:
        i = toks.index(cur.spelling)
        k = toks[i-1]
    except ValueError:
        k = 'struct'
    identifier  = "%s %s"%(k,identifier)
    if conf.DEBUG: echo('\t'*g_indent + str(identifier))
    if   k == 'struct':
        S = cStruct()
    elif k == 'union':
        S = cUnion()
    else:
        S = cClass()
    SetStructured(cur,S,errors)
    return identifier,cTemplate(params=p,cClass=S)

def template_fltr(x):
    if x.kind==CursorKind.TEMPLATE_TYPE_PARAMETER: return True
    if x.kind==CursorKind.TEMPLATE_NON_TYPE_PARAMETER: return True
    return False

@declareHandler(CLASS_TPSPEC)
def ClassTemplatePartialSpec(cur,cxx,errors=None):
    return ClassTemplate(cur,cxx,errors)

@declareHandler(NAMESPACE)
def NameSpace(cur,cxx,errors=None):
    namespace = cur.spelling
    S = cNamespace()
    S.local = {}
    for f in cur.get_children():
        if f.kind in CHandlers:
            i,obj = CHandlers[f.kind](f,cxx,errors)
            S.append(i)
            S.local[i] = obj
    return namespace,S

def SetStructured(cur,S,errors=None):
    global g_indent
    S._in = str(cur.extent.start.file)
    local = {}
    attr_x = False
    if errors is None: errors=[]
    g_indent += 1
    for f in cur.get_children():
        if conf.DEBUG: echo('\t'*g_indent + str(f.kind)+'='+str(f.spelling))
        errs = []
        for i,r in enumerate(errors):
            if (f.extent.start.line<=r.location.line<=f.extent.end.line):
                if (f.extent.start.line!=f.extent.end.line) or\
                   (f.extent.start.column<=r.location.column<=f.extent.end.column):
                    errs.append(r)
        # in-structuted type definition of another structured type:
        if f.kind in (STRUCT_DECL,UNION_DECL,CLASS_DECL,ENUM_DECL):
            identifier,slocal = CHandlers[f.kind](f,S._is_class,errs)
            local[identifier] = slocal
            attr_x = True
            if not S._is_class: S.append([identifier, '',''])
        # c++ parent class:
        elif f.kind is CursorKind.CXX_BASE_SPECIFIER:
            is_virtual = clang.cindex.conf.lib.clang_isVirtualBase(f)
            virtual = 'virtual' if is_virtual else ''
            S.append( (('parent',virtual),('',f.spelling),(f.access_specifier.name,'')) )
        # c++ 'using' declaration:
        elif f.kind is CursorKind.USING_DECLARATION:
            I = list(f.get_children())
            S.append( (('using',''),('',[x.spelling for x in I]),('','')) )
        # structured type member:
        else:
            comment = f.brief_comment or f.raw_comment
            # type spelling is our member type only if this type is defined already,
            # otherwise clang takes the default 'int' type here and we can't access
            # the wanted type unless we access f's tokens.
            # field/member declaration:
            if f.kind in (CursorKind.FIELD_DECL,
                          CursorKind.VAR_DECL,
                          CursorKind.CONSTRUCTOR,
                          CursorKind.DESTRUCTOR,
                          CursorKind.CXX_METHOD):
                t = f.type.spelling
                if '(anonymous' in t:
                    if not S._is_class:
                        t = f.type.get_canonical().spelling
                else:
                    if S._is_class:
                        kind = get_kind_type(t)
                        t = f.type.get_canonical().spelling
                        if kind: t = "%s %s"%(kind,t)
                    t = fix_type_conversion(f,t,S._is_class,errs)
                t = get_uniq_typename(t)
                if S._is_class:
                    attr = ''
                    if f.kind==CursorKind.VAR_DECL: attr = 'static'
                    if f.is_virtual_method(): attr = 'virtual'
                    if conf.DEBUG: echo('\t'*g_indent + str(t))
                    member = ((attr,t),
                              (f.mangled_name,f.spelling),
                              (f.access_specifier.name,comment))
                else:
                    if attr_x and t==S[-1][0]: S.pop()
                    attr_x = False
                    if conf.DEBUG: echo('\t'*g_indent + str(t))
                    member = (t,
                              f.spelling,
                              comment)
                S.append(member)
            elif f.kind == CursorKind.FRIEND_DECL:
                for frd in f.get_children():
                    member = (('friend',frd.type.spelling),
                              (frd.mangled_name,frd.spelling),
                              ('',comment))
                    S.append(member)
    S.local = local
    g_indent -= 1

def get_kind_type(t):
    if  'struct ' in t: kind='struct'
    elif 'union ' in t: kind='union'
    elif 'enum '  in t: kind='enum'
    else: kind=''
    return kind

def get_uniq_typename(t):
    if not '(anonymous' in t: return t
    kind = get_kind_type(t)
    # anon types inside *named* struct/union are prefixed by
    # the struct/union namespace, we don't keep this since
    # we are creating a unique typename anyway
    if '::' in t:
        t = "%s %s"%(kind,t.split('::')[-1])
    x = re.compile('\(anonymous .*\)')
    s = x.search(t).group(0)
    h = hashlib.sha256(s.encode('ascii')).hexdigest()[:8]
    return re.sub('\(anonymous .*\)','?_%s'%h,t,count=1)

def fix_type_conversion(f,t,cxx,errs):
    # this type might be a prototype a structured type or a
    # "complex" type (as opposed to simple) in which a unknown
    # type (denoted ut hereafter) as been replaced by 'int'.
    # Typename ut is fully provided in errs but
    # unfortunately, type t might contain several 'int' keywords,
    # some of which being really 'ints' and not the result of the
    # ut->int replacement.
    # In a previous version of ccrawl, we used a trick: since ut
    # is known by catching error messages, we'd add a fake typedef
    # string in a private include and then recompile our file.
    # The drawback was that we'd need several recompilations.
    # In this version we will detect which ints have been replaced
    # and switch them back to ut...
    if re.search('(?<!\w)int(?!\w)',t):
        #there is at least one int occurence in t...
        candidates = []
        for r in errs:
            if 'unknown type' in r.spelling:
                candidates.append(re.findall("'(.*)'",r.spelling)[0])
        marks = ['']
        # for every occurence of int type in t:
        T = [x for x in f.get_tokens()]
        for m in re.finditer('(?<!\w)int(?!\w)',t):
            # lets see if this was diag-ed has an 'unknown type' error:
            # now we only need to replace some 'int' token be ut in t...
            # to be extracting the missing types
            # from the errs and replacing the 'int' identifier in t by its
            # corresponding type. Either based on error location (column) or
            # by counting 'int' occurences within f's tokens up to the point
            # where the type string is located...
            while len(T)>0:
                x = T.pop(0)
                #if conf.DEBUG: secho("%s: %s"%(x.kind, x.spelling),fg='red')
                if x.kind == TokenKind.KEYWORD:
                    if x.spelling == 'int':
                        marks.append('int')
                        break
                elif x.kind == TokenKind.IDENTIFIER:
                    for c in candidates:
                        if x.spelling in c:
                            marks.append(c)
                            break
        st = re.split('(?<!\w)int(?!\w)',t)
        d = len(st)-len(marks)
        if d>0: marks = marks+(['int']*d)
        ct = ''
        for m,s in zip(marks,st):
            ct = ct+m+s
        t = ct
    if conf.DEBUG: echo('\t'*g_indent+'type: %s'%t)
    return t

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
        # (detailed processing allows to get macros in iterated cursors)
        options  = TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        options |= TranslationUnit.PARSE_INCOMPLETE
        options |= TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
    if args is None:
        # clang: keep comments in parser output and get template definition
        _args = ['-ferror-limit=0',
                 '-fparse-all-comments',
                ]
    else:
        _args = args[:]
    if conf.config.Collect.cxx:
        if filename.endswith('.hpp') or filename.endswith('.cpp'):
            _args.extend(['-x','c++','-std=c++11', '-fno-delayed-template-parsing'])
    cxx = 'c++' in _args
    if not conf.config.Collect.strict:
        # in non strict mode, we allow missing includes
        fd,depf = tempfile.mkstemp(prefix='ccrawl-')
        os.close(fd)
        _args += ['-M', '-MG', '-MF%s'%depf]
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
        for err in tu.diagnostics:
            if conf.DEBUG: secho(err.format(),fg='yellow')
            if err.severity==3:
                # common errors when parsing c++ as c:
                if ("expected ';'" in err.spelling) or\
                   ("'namespace'" in err.spelling):
                    if conf.config.Collect.cxx:
                        A = ['-x','c++','-std=c++11']
                        tu = index.parse(filename,_args+A,unsaved_files,options)
                        break
                    else:
                        secho('[c++]'.rjust(8), fg='yellow')
                        return []
            elif err.severity==4:
                # this should not happen anymore thanks to -M -MG opts...
                # we keep it here just in case.
                if conf.VERBOSE: secho(err.format(),bg='red')
                raise StandardError
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
    # walk down all AST to get all cursors:
    pool = [(c,[]) for c in tu.cursor.get_children()]
    # map diagnostics to cursors:
    for cur,errs in pool:
        if cur.location.file is None: continue
        for r in tu.diagnostics:
            if (str(cur.location.file) == str(r.location.file)) and\
               (cur.extent.start.line<=r.location.line<=cur.extent.end.line):
                if (cur.extent.start.line!=cur.extent.end.line) or\
                   (cur.extent.start.column<=r.location.column<=cur.extent.end.column):
                    if 'unknown type name' in r.spelling or\
                       'type specifier missing' in r.spelling or\
                       'has incomplete' in r.spelling or\
                       'no type named' in r.spelling or\
                       'function cannot return function type' in r.spelling or\
                       'no template named' in r.spelling:
                        errs.append(r)
    # now finally call the handlers:
    for cur,errs in pool:
        if conf.DEBUG and cur.location.file:
            echo('-'*80)
            echo('%s: %s [%d errors]'%(cur.kind,cur.spelling,len(errs)))
        if cur.kind in kind:
            kv = CHandlers[cur.kind](cur,cxx,errs)
            # fill defs with collected cursors:
            if kv:
                ident,cobj = kv
                if cobj:
                    for x in cobj.to_db(ident, tag, cur.location.file.name):
                        defs[x['id']] = x
    if not conf.QUIET:
        secho(('[%3d]'%len(defs)).rjust(8), fg='green')
    return defs.values()

def parse_string(s,args=None,options=0):
    """ Crawl wrapper to parse an input string rather than file.
    """
    # create a tmp filename (file can be removed immediately)
    tmph = tempfile.mkstemp(prefix='ccrawl-',suffix='.h')[1]
    os.remove(tmph)
    return parse(tmph,args,[(tmph,s)],options)

