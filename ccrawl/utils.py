import pdb
import pyparsing as pp

struct_letters = {
    "...": None,
    "void": "?",
    "char": "s",
    "short": "h",
    "int": "i",
    "long": "l",
    "long long": "q",
    "float": "f",
    "double": "d",
    "ssize_t": "n",
    "size_t": "N",
    "wchar_t": "L",
    "bool": "?",
    "float complex": "F",
    "double complex": "D",
}

import pyparsing as pp

# Basics
ident = pp.Regex(r"[?]?[A-Za-z_][A-Za-z0-9_$]*")
specifiers = pp.oneOf("const volatile unsigned signed struct class enum")
pstars = pp.Combine(pp.OneOrMore('*')) + pp.Optional("const",default="")
pstars.set_parse_action(lambda r: ptr(*r))
ampers = pp.Combine(pp.OneOrMore('&'))
ampers.set_parse_action(lambda r: ptr(*r,''))
ellipsis = pp.Literal("...")
cvqual = pp.OneOrMore(specifiers) | pp.Keyword("noexcept")
cvref = cvqual | ampers

# Expressions and Operators
# We need to handle basic math/logic used in template params
# Note: we use pp.infixNotation or a simple word set for expressions
binary_ops = pp.oneOf("<< >> + - * / % & | ^ == != <= >= && ||")
expr_term = pp.Word(pp.alphanums + "_") | pp.Regex(r"'.*'") | pp.Regex(r'".*"')

# A basic expression can be a single term or terms joined by operators
# This handles <N + 1> or <1 << 3>
expression = pp.Combine(expr_term + pp.ZeroOrMore(binary_ops + expr_term))

# 2. Forward Declarations
type_instance = pp.Forward()
template_spec = pp.Forward()

# Base Type & Declarators
base_name = pp.Combine(pp.Optional("::") + ident + pp.ZeroOrMore("::" + ident))
base_type = pp.Group(
    pp.Optional(ellipsis) + pp.ZeroOrMore(specifiers) +
    base_name("base_name") +
    pp.Optional(template_spec)("template")
)("base_type")
base_type.set_parse_action(lambda r: c_base_type(r[0]))

# Suffixes
array_spec = (pp.Suppress("[") +
              pp.Optional(pp.Word(pp.alphanums + "_"),default=None) +
              pp.Suppress("]"))
array_spec.set_parse_action(lambda r: arr(r[0]) if r[0] is not None else ptr('*',''))

# Updated params_spec to handle C-style variadics (...,)
params_spec = pp.Group(
    pp.Suppress("(") +
    pp.Optional(
        pp.delimitedList(type_instance | ellipsis)) +
    pp.Suppress(")")
)
params_spec.set_parse_action(lambda r: fargs(r[0]))

# Declarator (Handling pointers and pack expansion suffix)
declarator = pp.Forward()
nested_decl = (pp.Group(pp.Suppress("(") + declarator + pp.Suppress(")")) +
                       pp.ZeroOrMore(array_spec | params_spec))
# We add ellipsis here to handle "Args..."
declarator << pp.OneOrMore(pstars | ampers | nested_decl | array_spec)

# The Unified Argument (Type or Expression)
# We allow the argument to be a full type_instance OR a mathematical expression
arg_value = pp.Group(type_instance("ti") | expression | pp.Word(pp.nums))

# Default Values (e.g., T = int)
# An argument can be "Value" or "Value = DefaultValue"
template_arg = (
    arg_value("arg") +
    pp.Optional(pp.Suppress("=") + arg_value("default"))
    ).set_parse_action(lambda r: c_template_arg(r))

template_spec << (
    pp.Suppress("<") +
    pp.Optional(pp.delimitedList(template_arg | ellipsis)) +
    pp.Suppress(">")
)
template_spec.set_parse_action(lambda r: c_template(r.as_list()))

pstack_spec = pp.Group(pp.Optional(declarator) +
               pp.ZeroOrMore(array_spec | params_spec)
              ) + pp.Optional(cvref)("cvref")
def create_pstack(r):
    s = pstack(r[0].as_list())
    if r.cvref:
        s[-1].cvr = r[1]
    return s
pstack_spec.set_parse_action(create_pstack)

# Our final top-level element: the type_instance.
type_instance << pp.Group(
    base_type +
    pp.Optional(pstack_spec, default=None)("pstack") +
    pp.Optional(ellipsis)("pack_expansion")
    )

class c_base_type:
    def __init__(self, x):
        lbase = []
        self.lconst = self.lunsigned = self.lvolatile = False
        self.kw = ''
        for w in x:
            match w:
                case "const":
                    self.lconst = True
                case "unsigned":
                    self.lunsigned = True
                case "signed":
                    pass
                case "volatile":
                    self.lvolatile = True
                case str():
                    if w in ("struct", "union", "enum", "class"):
                        self.kw = w
                    lbase.append(w)
        self.tp = x.template
        self.lbase = " ".join(lbase)
        self.ns = x.base_name.split("::")[:-1]
    def __str__(self):
        s = self.lbase+str(self.tp)
        if self.lunsigned:
            s = "unsigned "+s
        if self.lconst:
            s = "const "+s
        return s
    def __repr__(self):
        return "<%s '%s'>"%(self.__class__.__name__,str(self))
    def __eq__(self,other):
        return str(self)==str(other)

class c_type_instance:
    def __init__(self, x):
        self._pr = x
        self.base_type = x.base_type
        self.pack_expansion = x.pack_expansion
        # now deal with the ptr/arr/fargs stack:
        self.pstack = x.pstack.as_list() if x.pstack else []

    @property
    def lbase(self):
        return self.base_type.lbase
    @property
    def lconst(self):
        return self.base_type.lconst
    @property
    def lunsigned(self):
        return self.base_type.lunsigned
    @property
    def lvolatile(self):
        return self.base_type.lvolatile

    def __str__(self):
        base = str(self.base_type)
        if self.pack_expansion:
            base += self.pack_expansion
        return "{} {}".format(base, self.show_ptr('')).strip()

    def show_base(self, kw=False, ns=False, tp=True):
        return str(self.base_type)

    def show_ptr(self, name):
        """
        returns the string that represents the pointers stack,
        with optional name parameter used as the name of the
        function (in case of a prototype).
        """
        s = name
        stripok = False
        for p in reversed(self.pstack):
            match p:
                case ptr():
                    s = "({}{})".format(p, s)
                    stripok = True
                case arr():
                    s = "{}{}".format(s, str(p))
                    stripok = False
                case fargs():
                    s = "{}{}".format(s, str(p))
                    stripok = False
        if stripok:
            s = s[1:-1]
        return s

    @property
    def is_ptr(self):
        return ptr in [type(p) for p in self.pstack]

    @property
    def dim(self):
        if self.pstack:
            p = self.pstack[-1]
            if isinstance(p, arr):
                return p.a
        return 0

    def __repr__(self):
        s = ["<%s" % self.__class__.__name__]
        s.extend(reversed([str(p) for p in self.pstack]))
        s.append(str(self.base_type)+">")
        return " ".join(s)

class c_type(c_type_instance):
    def __init__(self, decl):
        bf = decl.rfind("#")
        if bf>0:
            bitfield = (base_type +
                        pp.Suppress("#") + pp.Regex(r"[1-9][0-9]*"))
            try:
                x = bitfield.parseString(decl)
            except Exception:
                x, r = (type_instance + pp.restOfLine).parse_string(decl[:bf])
                self.lbfw = 0
            else:
                r = ""
                self.lbfw = int(x.pop(),0)
        else:
            x, r = (type_instance + pp.restOfLine).parse_string(decl)
            self.lbfw = 0
        # set the parsed type_instance:
        super().__init__(x)

    def show_base(self, kw=False, ns=False, tp=True):
        """
        returns the string that represents the base type
        with possibly additional 'const' and 'unsigned'
        keywords (if kw is True) and namespace(s) indicators
        (if ns is True).
        """
        return str(self.base_type)

    def show(self, name=""):
        """
        returns the string that represents full type with optional
        name parameter for a function's prototype.
        """
        extra = " : %d" % self.lbfw if self.lbfw else ""
        s = ("%s %s" % (self.show_base(), self.show_ptr(name))).strip()
        return s + extra

class cxx_type(c_type):
    def __init__(self, decl):
        super().__init__(decl)
        self.kw = self.base_type.kw
        self.ns = self.base_type.ns
        self.tp = self.base_type.tp

    @property
    def is_method(self):
        return fargs in [type(p) for p in self.pstack]

    def show_base(self, kw=False, ns=False, tp=True):
        lbase = str(self.base_type)
        if not kw:
            lbase = lbase.replace(self.kw, "", 1)
        if not ns and self.ns:
            ns = "::".join(self.ns) + "::"
            lbase = lbase.replace(ns, "", 1)
        if not tp:
            lbase = lbase.replace(str(self.tp), "", 1)
        return lbase.strip()

    def show(self, name="", kw=True, ns=True):
        extra = " : %d" % self.lbfw if self.lbfw else ""
        s = ("%s %s" % (self.show_base(kw, ns), self.show_ptr(name))).strip()
        return s + extra

    def tp_args(self):
        return [str(a) for a in self.tp.args] if self.tp else []

    def __eq__(self, other):
        et = self.show_base(ns=True)
        ot = other.show_base(ns=True)
        return et==ot

class c_template:
    def __init__(self, args):
        self.args = args
    def __str__(self):
        return "<%s>"%(", ".join((str(arg) for arg in self.args)))
    def __repr__(self):
        return "<%s '%s'>"%(self.__class__.__name__,str(self))

class c_template_arg:
    def __init__(self, x):
        self.value = c_type_instance(x.arg.ti) if x.arg.ti else x.arg
        self.default = x.default
        if hasattr(x.default,'ti'):
            self.default = c_type_instance(x.default.ti)
    def __str__(self):
        s = str(self.value)
        if self.default:
            s += " = %s"%self.default
        return s
    def __repr__(self):
        return "<%s '%s'>"%(self.__class__.__name__,str(self))

class ptr(object):
    """
    Object that represents a series of pointer (aka stars) possibly with
    additional 'const' keyword.

    Attributes:
        p (str): list of '*' chars that represent the C pointers
        const (str): 'const' keyword or None.
    """
    def __init__(self, p, c):
        self.is_ptr = True
        self.p, self.const = p, c

    def __str__(self):
        sfx = "%s " % self.const if self.const else ""
        return "{}{}".format(self.p, sfx)
    def __repr__(self):
        return "<%s '%s'>"%(self.__class__.__name__,str(self))


class arr(object):
    """
    Object that represents an array indicator.

    Attributes:
        a (int): dimension of the array
    """
    def __init__(self, a):
        self.is_ptr = False
        try:
            self.a = int(a,0)
        except ValueError:
            self.a = a

    def __str__(self):
        return "[%s]" % self.a
    def __repr__(self):
        return "<%s '%s'>"%(self.__class__.__name__,str(self))

class fargs(object):
    """
    Object that represents the arguments list of a function prototype.

    Attributes:
        f (str): the arguments part of a function prototype
        args (list): the list of arguments
    """
    def __init__(self, args):
        self.is_ptr = False
        self.args = []
        for arg in args:
            if arg == '...':
                self.args.append(arg)
                break
            self.args.append(c_type_instance(arg))

    def __str__(self):
        s = "(%s)"%(", ".join((str(arg) for arg in self.args)).strip())
        if hasattr(self, "cvr"):
            s += " %s"%self.cvr
        return s
    def __repr__(self):
        return "<%s '%s'>"%(self.__class__.__name__,str(self))

def pstack(plist):
    S = []
    off = 0
    for i,e in enumerate(plist):
        match e:
            case ptr():
                S.append(e)
                off = i+1
            case arr():
                S.insert(off,e)
            case fargs() if off==0:
                S.append(e)
            case _:
                break
    plist = plist[len(S):]
    while len(plist)>1:
        e = plist.pop()
        S.append(e)
    if plist:
        if isinstance(plist[0],list):
            # this must be a nested parenthesis:
            plist = plist[0]
        S.extend(pstack(plist))
    return S
