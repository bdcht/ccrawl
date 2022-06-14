import os
import re
from click import echo, secho
from clang.cindex import CursorKind, TokenKind, TranslationUnit, Index
import clang.cindex
import tempfile
import hashlib
from itertools import chain
from collections import Iterable, OrderedDict, defaultdict
from ccrawl import conf
from ccrawl.core import (
    cFunc,
    cMacro,
    cTypedef,
    cStruct,
    cUnion,
    cClass,
    cTemplate,
    cEnum,
    cNamespace,
)

g_indent = 0

CHandlers = {}

# ccrawl classes for clang parser:
# ------------------------------------------------------------------------------


def declareHandler(kind):
    """Decorator used to register a handler associated to
    a clang cursor kind/type. The decorated handler function
    will be called to process each cursor of this kind.
    """

    def decorate(f):
        CHandlers[kind] = f
        return f

    return decorate


spec_chars = (",", "*", "::", "&", "(", ")", "[", "]")

# cursor types that will be parsed to instanciate ccrawl
# objects:
TYPEDEF_DECL = CursorKind.TYPEDEF_DECL
STRUCT_DECL = CursorKind.STRUCT_DECL
UNION_DECL = CursorKind.UNION_DECL
ENUM_DECL = CursorKind.ENUM_DECL
FUNCTION_DECL = CursorKind.FUNCTION_DECL
MACRO_DEF = CursorKind.MACRO_DEFINITION
CLASS_DECL = CursorKind.CLASS_DECL
FUNC_TEMPLATE = CursorKind.FUNCTION_TEMPLATE
CLASS_TEMPLATE = CursorKind.CLASS_TEMPLATE
CLASS_TPSPEC = CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION
NAMESPACE = CursorKind.NAMESPACE

# handlers:


@declareHandler(FUNCTION_DECL)
def FuncDecl(cur, cxx, errors=None):
    identifier = cur.spelling
    t = cur.type.spelling
    proto = fix_type_conversion(cur, t, cxx, errors)
    params = []
    locs = []
    calls = []
    f = cFunc(prototype=proto)
    for e in cur.get_children():
        if conf.DEBUG:
            echo("%s: %s" % (e.kind, e.spelling))
        if e.kind == CursorKind.PARM_DECL:
            params.append(e.spelling)
        elif e.kind == CursorKind.COMPOUND_STMT:
            locs, calls = CodeDef(e, cxx, errors)
    f["params"] = params
    f["locs"] = locs
    f["calls"] = calls
    if conf.VERBOSE:
        secho("  cFunc: %s" % identifier)
    return identifier, f


@declareHandler(MACRO_DEF)
def MacroDef(cur, cxx, errors=None):
    if cur.extent.start.file:
        identifier = cur.spelling
        toks = []
        for t in list(cur.get_tokens())[1:]:
            pre = "" if t.spelling in spec_chars else " "
            toks.append(pre + t.spelling)
        s = "".join(toks)
        if conf.VERBOSE:
            secho("  cMacro: %s" % identifier)
        return identifier, cMacro(s.replace("( ", "("))


@declareHandler(TYPEDEF_DECL)
def TypeDef(cur, cxx, errors=None):
    identifier = cur.type.spelling
    dt = cur.underlying_typedef_type
    if "(anonymous" in dt.spelling:
        dt = dt.get_canonical()
    if "(unnamed" in dt.spelling:
        dt = dt.get_canonical()
    t = fix_type_conversion(cur, dt.spelling, cxx, errors)
    t = get_uniq_typename(t)
    if conf.DEBUG:
        echo("\t" * g_indent + "make unique: %s" % t)
    if conf.VERBOSE:
        secho("  cTypedef: %s" % identifier)
    return identifier, cTypedef(t)


@declareHandler(CursorKind.TYPE_REF)
def TypeRef(cur, cxx, errors=None):
    echo("\t" * g_indent + cur.spelling)
    return cur.spelling, None


@declareHandler(STRUCT_DECL)
def StructDecl(cur, cxx, errors=None):
    typename = cur.type.spelling
    if cxx:
        typename = cur.type.get_canonical().spelling
    if not typename.startswith("struct "):
        typename = "struct " + typename
    typename = get_uniq_typename(typename)
    if conf.DEBUG:
        echo("\t" * g_indent + "make unique: %s" % typename)
    S = cClass() if cxx else cStruct()
    SetStructured(cur, S, errors)
    if conf.VERBOSE:
        secho("  %s: %s" % (S.__class__.__name__, typename))
    return typename, S


@declareHandler(UNION_DECL)
def UnionDecl(cur, cxx, errors=None):
    typename = cur.type.spelling
    if cxx:
        typename = cur.type.get_canonical().spelling
    if not typename.startswith("union "):
        typename = "union " + typename
    typename = get_uniq_typename(typename)
    if conf.DEBUG:
        echo("\t" * g_indent + "make unique: %s" % typename)
    S = cClass() if cxx else cUnion()
    SetStructured(cur, S, errors)
    if conf.VERBOSE:
        secho("  %s: %s" % (S.__class__.__name__, typename))
    return typename, S


@declareHandler(CLASS_DECL)
def ClassDecl(cur, cxx, errors=None):
    typename = "class %s" % (cur.type.get_canonical().spelling)
    if conf.DEBUG:
        echo("\t" * g_indent + "%s" % typename)
    S = cClass()
    SetStructured(cur, S, errors)
    if conf.VERBOSE:
        secho("  %s: %s" % (S.__class__.__name__, typename))
    return typename, S


@declareHandler(ENUM_DECL)
def EnumDecl(cur, cxx, errors=None):
    global g_indent
    typename = cur.type.spelling
    if cxx:
        typename = cur.type.get_canonical().spelling
    if not typename.startswith("enum "):
        typename = "enum " + typename
    typename = get_uniq_typename(typename)
    if conf.DEBUG:
        echo("\t" * g_indent + "make unique: %s" % typename)
    S = cEnum()
    S._in = str(cur.extent.start.file)
    # a = 0
    g_indent += 1
    for f in cur.get_children():
        if conf.DEBUG:
            echo("\t" * g_indent + "%s: " % (f.kind), nl=False)
        # if not f.is_definition():
        #    if a: raise ValueError
        if f.kind is CursorKind.ENUM_CONSTANT_DECL:
            S[f.spelling] = f.enum_value
            if conf.DEBUG:
                echo(str(f.enum_value), nl=False)
        elif conf.DEBUG:
            echo("%s:%s" % (f.kind, f.spelling))
    g_indent -= 1
    if conf.VERBOSE:
        secho("  %s: %s" % (S.__class__.__name__, typename))
    return typename, S


@declareHandler(CLASS_TEMPLATE)
def ClassTemplate(cur, cxx, errors=None):
    identifier = cur.displayname
    p = []
    for x in cur.get_children():
        if x.kind == CursorKind.TEMPLATE_TYPE_PARAMETER:
            p.append("typename %s" % x.spelling)
        elif x.kind == CursorKind.TEMPLATE_NON_TYPE_PARAMETER:
            p.append("%s %s" % (x.type.spelling, x.spelling))
    # now we need this to distinguish struct/union/class template:
    # damn libclang!! children here should really allow for
    # this by having a STRUCT_DECL, UNION_DECL or CLASS_DECL !
    # Or, if implicit CLASS_DECL due to being a CLASS_TEMPLATE,
    # then there should be a STRUCT_TEMPLATE as well.
    toks = [x.spelling for x in cur.get_tokens()]
    try:
        i = toks.index(cur.spelling)
        k = toks[i - 1]
    except ValueError:
        k = "struct"
    identifier = "%s %s" % (k, identifier)
    if conf.DEBUG:
        echo("\t" * g_indent + str(identifier))
    # ok so now proceed with the "class" parsing:
    S = cClass()
    SetStructured(cur, S, errors)
    if conf.VERBOSE:
        secho("  cTemplate/%s: %s" % (S.__class__.__name__, identifier))
    return identifier, cTemplate(params=p, cClass=S)


@declareHandler(FUNC_TEMPLATE)
def FuncTemplate(cur, cxx, errors=None):
    identifier = cur.spelling
    if conf.DEBUG:
        echo("\t" * g_indent + identifier)
    proto = cur.type.spelling
    if conf.DEBUG:
        echo("\t" * g_indent + proto)
    p = []
    for x in cur.get_children():
        if x.kind == CursorKind.TEMPLATE_TYPE_PARAMETER:
            p.append("typename %s" % x.spelling)
        elif x.kind == CursorKind.TEMPLATE_NON_TYPE_PARAMETER:
            p.append("%s %s" % (x.type.spelling, x.spelling))
    f = re.sub(r"__attribute__.*", "", proto)
    if conf.VERBOSE:
        secho("  cTemplate/cFunc: %s" % identifier)
    return identifier, cTemplate(params=p, cFunc=cFunc(prototype=f))


@declareHandler(CLASS_TPSPEC)
def ClassTemplatePartialSpec(cur, cxx, errors=None):
    identifier, obj = ClassTemplate(cur, cxx, errors)
    obj["partial_specialization"] = True
    return identifier, obj


@declareHandler(NAMESPACE)
def NameSpace(cur, cxx, errors=None):
    namespace = cur.spelling
    S = cNamespace()
    S.local = {}
    # check if namespace is inlined:
    toks = [t.spelling for t in cur.get_tokens()]
    try:
        i = toks.index(namespace)
        S.inline = toks[i - 2] == "inline"
        S.parent = cur.lexical_parent.spelling if S.inline else ""
    except ValueError:
        S.inline = False
        S.parent = ""
    for f in cur.get_children():
        if f.kind in CHandlers:
            i, obj = CHandlers[f.kind](f, cxx, errors)
            if S.inline:
                i = i.replace("%s::" % namespace, "")
            S.append(i)
            S.local[i] = obj
    if conf.VERBOSE:
        secho("  %s: %s" % (S.__class__.__name__, namespace))
    return namespace, S


def CodeDef(cur, cxx, errors=None):
    global g_indent
    g_indent += 1
    locs = []
    calls = []
    # for f in deepflatten(cur):
    for f in cur.walk_preorder():
        if conf.DEBUG:
            echo("\t" * g_indent + "%s: %s" % (f.kind, f.spelling))
        if f.kind == CursorKind.VAR_DECL:
            locs.append((f.type.spelling, f.spelling))
            if conf.DEBUG:
                echo("\t" * g_indent + "var: (%s,%s)" % locs[-1])
        elif f.kind == CursorKind.CALL_EXPR:
            calls.append(f.spelling)
    g_indent -= 1
    return locs, calls


def SetStructured(cur, S, errors=None):
    global g_indent
    S._in = str(cur.extent.start.file)
    local = {}
    alltoks = [
        (t.kind, t.spelling, t.location) for t in cur._tu.get_tokens(extent=cur.extent)
    ]
    attr_x = False
    if errors is None:
        errors = []
    g_indent += 1
    bitfield_error = False
    if errors:
        for (k, s, l) in alltoks:
            if k == TokenKind.PUNCTUATION and s == ":":
                if conf.DEBUG:
                    secho("bitfield structure with errors...", fg="yellow")
                bitfield_error = True
                break
    for f in cur.get_children():
        if conf.DEBUG:
            echo("\t" * g_indent + str(f.kind) + "=" + str(f.spelling))
        errs = []
        for i, r in enumerate(errors):
            if f.extent.start.line <= r.location.line <= f.extent.end.line:
                if (f.extent.start.line != f.extent.end.line) or (
                    f.extent.start.column <= r.location.column <= f.extent.end.column
                ):
                    errs.append(r)
        if errs and bitfield_error:
            # fixing the extent. Clang is buggy and has forgotten the bitfield tokens...
            T = [(t.kind, t.spelling, t.location) for t in f.get_tokens()]
            off = alltoks.index(T[0])
            fix = None
            for k, s, l in alltoks[off:]:
                if k == TokenKind.PUNCTUATION and s == ";":
                    if l.offset > T[-1][2].offset:
                        fix = l.offset
                        break
            if fix is not None:
                x = f._extent
                e = clang.cindex.SourceLocation.from_offset(f._tu, x.end.file, fix)
                x = clang.cindex.SourceRange.from_locations(x.start, e)
                f._extent = x
        # nested type definition of another structured type:
        if f.kind in (
            STRUCT_DECL,
            UNION_DECL,
            ENUM_DECL,
            CLASS_DECL,
            FUNC_TEMPLATE,
            CLASS_TEMPLATE,
        ):
            identifier, slocal = CHandlers[f.kind](f, S._is_class, errs)
            if f.kind == FUNC_TEMPLATE:
                S.append(
                    (
                        ("template%s" % slocal.get_template(), slocal["cFunc"]["prototype"]),
                        ("", identifier),
                        (f.access_specifier.name, ""),
                    )
                )
            else:
                local[identifier] = slocal
                attr_x = True
                if not S._is_class:
                    S.append([identifier, "", ""])
        # c++ parent class:
        elif f.kind is CursorKind.CXX_BASE_SPECIFIER:
            is_virtual = clang.cindex.conf.lib.clang_isVirtualBase(f)
            virtual = "virtual" if is_virtual else ""
            # the spelling seems to always includes the 'class'/'struct' keyword...
            S.append(
                (("parent", virtual), ("", f.spelling), (f.access_specifier.name, ""))
            )
        # c++ 'using' declaration:
        elif f.kind is CursorKind.USING_DECLARATION:
            uses = []
            name = ""
            for x in f.get_children():
                if x.kind == CursorKind.TYPE_REF:
                    uses.append(x.spelling)
                if x.kind == CursorKind.OVERLOADED_DECL_REF:
                    name = x.spelling
            if conf.DEBUG:
                echo("\t" * g_indent + "%s : %s" % (name, uses))
            S.append((("using", uses), ("", name), ("", "")))
        # structured type member:
        else:
            try:
                comment = f.brief_comment or f.raw_comment
            except UnicodeDecodeError:
                comment = ""
            # type spelling is our member type only if this type is defined already,
            # otherwise clang takes the default 'int' type here and we can't access
            # the wanted type unless we access f's tokens.
            # field/member declaration:
            if f.kind in (
                CursorKind.FIELD_DECL,
                CursorKind.VAR_DECL,
                CursorKind.CONSTRUCTOR,
                CursorKind.DESTRUCTOR,
                CursorKind.CXX_METHOD,
            ):
                t = f.type.spelling
                if "(anonymous" in t:
                    if not S._is_class:
                        t = f.type.get_canonical().spelling
                elif "(unnamed" in t:
                    if not S._is_class:
                        t = f.type.get_canonical().spelling
                else:
                    if S._is_class:
                        kind = get_kind_type(t)
                        t = f.type.get_canonical().spelling
                        if "type-parameter" in t:
                            t = f.type.spelling
                        if kind:
                            t = "%s %s" % (kind, t)
                    t = fix_type_conversion(f, t, S._is_class, errs)
                t = get_uniq_typename(t)
                attr = ""
                if f.kind == CursorKind.VAR_DECL:
                    attr = "static"
                if f.is_virtual_method():
                    attr = "virtual"
                if f.is_bitfield():
                    bw = f.get_bitfield_width()
                    if conf.DEBUG:
                        echo("\t" * g_indent + "bitfield size:%d" % bw)
                    t += "# %d" % bw
                for w in f.get_children():
                    if conf.DEBUG:
                        g_indent += 1
                        subk = w.kind
                        subs = w.spelling
                        echo("\t" * g_indent + "%s: %s" % (subk, subs))
                        g_indent -= 1
                    if w.kind == CursorKind.CXX_FINAL_ATTR:
                        attr += ", final"
                    if w.kind == CursorKind.CXX_OVERRIDE_ATTR:
                        attr += ", override"
                if S._is_class:
                    # a C++ class member is stored as:
                    # [ (static/virtual?, type definition),
                    #   (mangled name, source name),
                    #   (access specifier, comment) ]
                    member = (
                        (attr, t),
                        (f.mangled_name, f.spelling),
                        (f.access_specifier.name, comment),
                    )
                else:
                    if attr_x and t == S[-1][0]:
                        S.pop()
                    attr_x = False
                    member = (t, f.spelling, comment)
                S.append(member)
            elif f.kind == CursorKind.FRIEND_DECL:
                for frd in f.get_children():
                    member = (
                        ("friend", frd.type.spelling),
                        (frd.mangled_name, frd.spelling),
                        ("", comment),
                    )
                    S.append(member)
    S.local = local
    g_indent -= 1


def get_kind_type(t):
    if "struct " in t:
        kind = "struct"
    elif "union " in t:
        kind = "union"
    elif "enum " in t:
        kind = "enum"
    else:
        kind = ""
    return kind


def get_uniq_typename(t):
    if not (("(anonymous" in t) or ("(unnamed" in t)):
        return t
    kind = get_kind_type(t)
    # anon types inside *named* struct/union are prefixed by
    # the struct/union namespace, we don't keep this since
    # we are creating a unique typename anyway
    if "::" in t:
        t = "%s %s" % (kind, t.split("::")[-1])
    x = re.compile(r"\((anonymous|unnamed) .*\)")
    s = x.search(t).group(0)
    h = hashlib.sha256(s.encode("ascii")).hexdigest()[:8]
    if not t.startswith(kind):
        t = "%s %s" % (kind, t)
    return re.sub(r"\((anonymous|unnamed) .*\)", "?_%s" % h, t, count=1)


def fix_type_conversion(f, t, cxx, errs):
    if not errs:
        return t
    # type t might be a prototype, a structured type, or a
    # "complex" type (as opposed to simple) in which an unknown
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
    if conf.DEBUG:
        secho("fix_type_conversion:", fg="yellow")
    if re.search(r"(?<!\w)int(?!\w)", t):
        # there is at least one int occurence in t...
        candidates = []
        for r in errs:
            if "unknown type" in r.spelling:
                candidates.append(re.findall(r"'(.*)'", r.spelling)[0])
            elif "no type named" in r.spelling:
                l = re.findall(r"'(\w+)'", r.spelling)
                candidates.append("::".join(reversed(l)))
            elif "undeclared identifier" in r.spelling:
                l = re.findall(r"'(\w+)'", r.spelling)
                candidates.append("::".join(reversed(l)) + "~")
        if not candidates:
            return t
        marks = [""]
        if conf.DEBUG:
            secho("candidates: %s" % candidates, fg="magenta")
        # for every occurence of int type in t:
        T = [x for x in f.get_tokens()]
        fixbitfield = ""
        for _ in re.finditer(r"(?<!\w)int(?!\w)", t):
            # lets see if this was diag-ed has an 'unknown type' error:
            # now we only need to replace some 'int' token be ut in t...
            # to be extracting the missing types
            # from the errs and replacing the 'int' identifier in t by its
            # corresponding type. Either based on error location (column) or
            # by counting 'int' occurences within f's tokens up to the point
            # where the type string is located...
            while len(T) > 0:
                x = T.pop(0)
                if conf.DEBUG:
                    secho("%s: %s" % (x.kind, x.spelling), fg="red")
                if x.kind == TokenKind.KEYWORD:
                    if x.spelling == "int":
                        marks.append("int")
                        break
                elif x.kind == TokenKind.IDENTIFIER:
                    for c in candidates:
                        if x.spelling in c:
                            if c.endswith("~"):
                                c = c[:-1]
                                while len(T) > 0 and T[0].spelling == "::":
                                    x = T.pop(0)
                                    x = T.pop(0)
                                    c += "::%s" % (x.spelling)
                            marks.append(c)
                            break
                elif x.kind == TokenKind.PUNCTUATION and x.spelling == ":":
                    fixbitfield = "#{}".format(T[0].spelling)
        st = re.split(r"(?<!\w)int(?!\w)", t)
        d = len(st) - len(marks)
        if d > 0:
            marks = marks + (["int"] * d)
        ct = ""
        for m, s in zip(marks, st):
            ct = ct + m + s
        t = ct + fixbitfield
    if conf.DEBUG:
        echo("\t" * g_indent + "type: %s" % t)
    return t


# ccrawl 'parse' function(s), wrapper of clang index.parse;
# ------------------------------------------------------------------------------


def parse(filename, args=None, unsaved_files=None, options=None, kind=None, tag=None):
    """Function that parses the input filename and returns the
    dictionary of name:object
    """
    # clang parser cindex options:
    if options is None:
        # (detailed processing allows to get macros in iterated cursors)
        options = TranslationUnit.PARSE_NONE
        options = TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        options |= TranslationUnit.PARSE_INCOMPLETE
        options |= TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION
        # (preprocessor options not exported in the python bindings):
        RetainExcludedConditionalBlocks = 0x8000
        KeepGoing = 0x200
        options |= RetainExcludedConditionalBlocks
        options |= KeepGoing
    if args is None:
        # mandatory if only libclang python binding is installed, since then the llvm-headers
        # are probably missing we need to use the builtin modulemap:
        _args = [
            "-ferror-limit=0",
            "-fmodules",
            "-fbuiltin-module-map",
        ]
    else:
        _args = args[:]
    if conf.config is None:
        conf.config = conf.Config()
    cxx_args = ["-x", "c++", "-std=c++11", "-fno-delayed-template-parsing"]
    if conf.config.Collect.cxx:
        if filename.endswith(".hpp") or filename.endswith(".cpp"):
            _args.extend(cxx_args)
    cxx = "c++" in _args
    if not conf.config.Collect.strict:
        # in non strict mode, we allow missing includes
        fd, depf = tempfile.mkstemp(prefix="ccrawl-")
        os.close(fd)
        _args += ["-M", "-MG", "-MF%s" % depf]
    if conf.DEBUG:
        echo("\nfilename: %s, args: %s" % (filename, _args))
    if unsaved_files is None:
        # unsaved files are also used to replace existing files by these if the
        # filename matches,
        # TODO: allowing to "preload" headers like stddef.h for example...
        unsaved_files = []
    if kind is None:
        kind = CHandlers
    else:
        for k in kind:
            assert k in CHandlers
    if conf.config.Collect.allc is False:
        options |= TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
    defs = OrderedDict()
    index = Index.create()
    # call clang parser:
    try:
        tu = index.parse(filename, _args, unsaved_files, options)
        for err in tu.diagnostics:
            if conf.DEBUG:
                secho(err.format(), fg="yellow")
            if err.severity == 3:
                # common errors when parsing c++ as c:
                if ("expected ';'" in err.spelling) or ("'namespace'" in err.spelling):
                    if conf.config.Collect.cxx:
                        if conf.DEBUG:
                            secho("reparse as c++ input...",fg="cyan")
                        cxx = True
                        tu = index.parse(filename, _args + cxx_args, unsaved_files, options)
                        break
                    else:
                        secho("[c++]".rjust(12), fg="yellow")
                        return []
            elif err.severity == 4:
                # this should not happen anymore thanks to -M -MG opts...
                # we keep it here just in case.
                if conf.VERBOSE:
                    secho(err.format(), bg="red", err=True)
                raise StandardError
    except Exception:
        if not conf.QUIET:
            secho("[err]", fg="red")
            if conf.VERBOSE:
                secho("clang index.parse error", fg="red", err=True)
        return []
    else:
        if conf.VERBOSE:
            echo(":")
    if not conf.config.Collect.strict:
        os.remove(depf)
    # walk down all AST to get all top-level cursors:
    pool = [(c, []) for c in tu.cursor.get_children()]
    #name = str(tu.cursor.extent.start.file.name)
    diag = {}
    for r in tu.diagnostics:
        if selected_errs(r):
            if not r.location.file.name in diag:
                diag[r.location.file.name] = defaultdict(list)
            diag[r.location.file.name][r.location.line].append(r)
    # map diagnostics to cursors:
    for cur, errs in pool:
        if cur.location.file is None or (cur.location.file.name not in diag):
            continue
        span = range(cur.extent.start.line, cur.extent.end.line + 1)
        if cur.location.line not in span:
            span = range(cur.location.line, cur.location.line + 1)
        for l in span:
            errs.extend(diag.get(cur.location.file.name, None)[l])
    # now finally call the handlers:
    for cur, errs in pool:
        if conf.DEBUG and cur.location.file:
            echo("-" * 80)
            echo("%s: %s [%d errors]" % (cur.kind, cur.spelling, len(errs)))
        if cur.kind in kind:
            kv = CHandlers[cur.kind](cur, cxx, errs)
            # fill defs with collected cursors:
            if kv:
                ident, cobj = kv
                if cobj:
                    for x in cobj.to_db(ident, tag, cur.location.file.name):
                        defs[x["id"]] = x
    if not conf.QUIET:
        secho(("[%3d]" % len(defs)).rjust(12), fg="green" if not cxx else "cyan")
    return defs.values()


def parse_string(s, args=None, options=0):
    """Crawl wrapper to parse an input string rather than file."""
    # create a tmp filename (file can be removed immediately)
    fd, tmph = tempfile.mkstemp(prefix="ccrawl-", suffix=".h")
    os.close(fd)
    os.remove(tmph)
    return parse(tmph, args, [(tmph, s)], options)


def selected_errs(r):
    if (
        "unknown type name" in r.spelling
        or "use of undeclared identifier" in r.spelling
        or "type specifier missing" in r.spelling
        or "has incomplete" in r.spelling
        or "no type named" in r.spelling
        or "function cannot return function type" in r.spelling
        or "no template named" in r.spelling
    ):
        return True
    else:
        return False


def parse_debug(filename, cxx=False):
    old = conf.DEBUG
    conf.DEBUG = True
    options = TranslationUnit.PARSE_NONE
    options = TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
    options |= TranslationUnit.PARSE_INCOMPLETE
    options |= TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION
    ## (preprocessor options not exported in the python bindings):
    RetainExcludedConditionalBlocks = 0x8000
    KeepGoing = 0x200
    options |= RetainExcludedConditionalBlocks
    options |= KeepGoing
    _args = [
        "-ferror-limit=0",
        "-fmodules",
        "-fbuiltin-module-map",
    ]
    _args += ["-M", "-MG", "-MF%s" % ".depf"]
    if cxx:
        _args += ["-x", "c++", "-std=c++11", "-fno-delayed-template-parsing"]
    _args += [
        "-I.",
        "-I./xxx",
        "-I./other",
    ]
    unsaved_files = []
    index = Index.create()
    if conf.DEBUG:
        echo(_args)
    tu = index.parse(filename, _args, unsaved_files, options)
    for err in tu.diagnostics:
        secho(err.format(), fg="yellow")
    pool = [(c, []) for c in tu.cursor.get_children()]
    #name = str(tu.cursor.extent.start.file.name)
    diag = {}
    for r in tu.diagnostics:
        if selected_errs(r):
            if not r.location.file.name in diag:
                diag[r.location.file.name] = defaultdict(list)
            diag[r.location.file.name][r.location.line].append(r)
    for cur, errs in pool:
        if cur.location.file is None or (cur.location.file.name not in diag):
            continue
        span = range(cur.extent.start.line, cur.extent.end.line + 1)
        if cur.location.line not in span:
            span = range(cur.location.line, cur.location.line + 1)
        for l in span:
            errs.extend(diag.get(cur.location.file.name, None)[l])
    defs = OrderedDict()
    for cur, errs in pool:
        if conf.DEBUG and cur.location.file:
            echo("-" * 80)
            echo("%s: %s [%d errors]" % (cur.kind, cur.spelling, len(errs)))
        if cur.kind in CHandlers:
            kv = CHandlers[cur.kind](cur, cxx, errs)
            if kv:
                ident, cobj = kv
                if cobj:
                    for x in cobj.to_db(ident, "debug", cur.location.file.name):
                        defs[x["id"]] = x
    conf.DEBUG = old
    return pool, defs


def deepflatten(cur, ltypes=Iterable):
    r = cur.get_children()
    while True:
        try:
            c = next(r)
        except StopIteration:
            break
        else:
            sub = c.get_children()
            r = chain(sub, r)
            yield c
