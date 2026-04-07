import pyparsing as pp


# ccrawl low-level utilities:
# ------------------------------------------------------------------------------

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

# C and C++ type declaration parsers:
# ------------------------------------------------------------------------------
# notes:
# this part of ccrawl was a coding nightmare...I was aware that parsing C is
# difficult and this was precisely why I'd use clang. Still, libclang's AST
# only provides the C type string. I first thought it was going to be easy to
# correctly parse this "simple" subpart of C...well, its not. And for C++ its
# even worse! Try playing with cdecl.org and see how funny this can be ;)
#
# ccrawl C type parser is implemented with below 'nested_c' pyparsing object.
# It captures nested parenthesis expressions that allows to define complex C
# types that represent pointer-to array-of ... function prototypes returning a
# C type.
#
# definitions for objecttype --------------------------------------------------
# the elementary type related to the parsed string.
# define 'raw' types:
unsigned = pp.Keyword("unsigned") | pp.Keyword("signed")
const = pp.Keyword("const")
volatile = pp.Keyword("volatile")
noexcept = pp.Keyword("noexcept")
prefix = pp.ZeroOrMore(pp.Or((const, volatile, unsigned)))
cvqual = pp.Or((const, volatile, const + volatile, noexcept))
T = [pp.Keyword(t) for t in struct_letters]
rawtypes = pp.Optional(prefix) + pp.Or(T)
# define pointer indicators:
pstars = pp.Group(pp.Regex(r"\*+") + pp.Optional(const, default=""))
ampers = pp.Regex("&+")
# define template indicators:
tpl_ignored = pp.Regex(r"\(.*\)")('ign_exp')|pp.Regex('".*"')('ign_str')
tpl = pp.nested_expr("<",">", ignore_expr=tpl_ignored)
# define generic symbol with optional template:
symbol = pp.Regex(r"[?]?[A-Za-z_][A-Za-z0-9_$]*")+pp.Optional(tpl,default="")
def flatten_symbol(r):
    if not r[1]:
        return r[0]
    else:
        return r[0]+flatten(r[1].asList(),'<%s>','')
symbol.setParseAction(flatten_symbol)
# define structured types (struct,union,enum):
structured = pp.oneOf("struct union enum class")
strucdecl =  pp.Optional(prefix) + pp.Optional(structured) 
strucdecl += pp.DelimitedList(symbol,'::',combine=True)
# define objecttype:
objecttype = pp.Or([rawtypes, strucdecl])
# define arrays:
intp = pp.Regex(r"[1-9][0-9]*")
intp.setParseAction(lambda r: int(r[0]))
bitfield = pp.Optional(prefix) + symbol + pp.Suppress("#") + intp
arraydecl = pp.Suppress("[") + intp + pp.Suppress("]")
arrazdecl = pp.Suppress("[") + pp.Or((intp, symbol)) + pp.Suppress("]")
arraylist = pp.OneOrMore(arraydecl)
arrazlist = pp.OneOrMore(arrazdecl)
pointer = pp.Optional(pstars, default="") + pp.Optional(arraylist)
pointerxx = pp.Optional(ampers, default="") + pp.Optional(arrazlist)
cvref = pp.Or((cvqual, ampers))
#
# definitions for nested_c ----------------------------------------------------
# nested_c captures "pointer to function/array" part of the declaration.
# this is the tricky part due to the nesting mix of pointer grouping vs.
# function prototyping using both parenthesis as delimiters!
nested_par = pp.nested_expr(content=pp.Regex(r"[^()]+"))
nested_c = pp.OneOrMore(nested_par)


class c_type(object):
    """
    The c_type object parses a C type string and decomposes it into
    several parts. 

    The parser is implemented with below 'nested_c' pyparsing object.
    It captures nested parenthesis expressions that allows to define complex C
    types that represent pointer-to array-of ... function prototypes returning a
    C type.

    Attributes:
        lbase (str): base typename
        lbfw (int): type has a bitfield length (0 means type is not a bitfield)
        lconst (bool): type has a 'const' keyword
        unsigned (bool): type has an 'unsigned' keyword
        volatile (bool): type has a 'volatile' keyword
        pstack (list): list of "pointers stack" (see :ref:`pstack` function)
        is_ptr (bool): True if the pstack contains a :class:`ptr` object.
        dim (int): dimension if the type is an array (or 0.)
    """

    def __init__(self, decl):
        # get final element type:
        bf = decl.rfind("#")
        if bf > 0:
            try:
                x = bitfield.parseString(decl)
            except Exception:
                x, r = (pp.Group(objecttype) + pp.restOfLine).parseString(decl[:bf])
                self.lbfw = 0
            else:
                r = ""
                self.lbfw = x.pop()
        else:
            x, r = (pp.Group(objecttype) + pp.restOfLine).parseString(decl)
            self.lbfw = 0
        lbase = []
        self.lconst = self.lunsigned = self.lvolatile = False
        for w in x:
            if w == "const":
                self.lconst = True
            elif w == "unsigned":
                self.lunsigned = True
            elif w == "signed":
                pass
            elif w == "volatile":
                self.lvolatile = True
            elif isinstance(w,list):
                # on a template arguments
                lbase.insert(-1,flatten(w,sep="<%s>",pad=""))
            else:
                lbase.append(w)
                lbase.append(" ")
        self.lbase = "".join(lbase).strip()
        r = r.replace("[]", "*")
        r = "(%s)" % r
        try:
            nest = nested_c.parseString(r).asList()[0]
        except Exception as e:
            print("c_type: error while parsing '%s'" % r)
            raise e
        self.pstack = pstack(nest, self.__class__)

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
        if self.lconst:
            s.append("const ")
        if self.lunsigned:
            s.append("unsigned ")
        s.append("{0.lbase}>".format(self))
        return " ".join(s)

    def show_base(self, kw=False, ns=False, tp=True):
        """
        returns the string that represents the base type
        with possibly additional 'const' and 'unsigned'
        keywords (if kw is True) and namespace(s) indicators
        (if ns is True).
        """
        s = [self.lbase]
        if self.lunsigned:
            s.insert(0, "unsigned")
        if self.lconst:
            s.insert(0, "const")
        return " ".join(s)

    def show_ptr(self, name):
        """
        returns the string that represents the pointers stack,
        with optional name parameter used as the name of the
        function (in case of a prototype).
        """
        s = name
        stripok = False
        for p in reversed(self.pstack):
            if p.is_ptr:
                s = "({}{})".format(p, s)
                stripok = True
            else:
                s = "{}{}".format(s, str(p))
                stripok = False
        if stripok:
            s = s[1:-1]
        return s

    def show(self, name=""):
        """
        returns the string that represents full type with optional
        name parameter for a function's prototype.
        """
        extra = " : %d" % self.lbfw if self.lbfw else ""
        s = ("%s %s" % (self.show_base(), self.show_ptr(name))).strip()
        return s + extra


# C++ type declaration parser:
# ------------------------------------------------------------------------------

class cxx_type(c_type):
    """
    cxx_type extends c_type with extracting the namespace parts of the fully
    qualified name of the C++ type.
    """
    def __init__(self, decl):
        super().__init__(decl)
        full_typename = pp.DelimitedList(symbol,'::')
        # get namespaces:
        self.kw = ""
        self.ns = []
        self.tp = ""
        try:
            self.kw = structured.parse_string(self.lbase)[0]
            k = self.lbase.find(" ")
        except Exception:
            k = -1
        r = full_typename.parse_string(self.lbase[k+1:]).asList()
        t = r.pop()
        self.ns = r
        sta = t.find('<')
        sto = t.rfind('>')
        if sta>0 and sto>0:
            self.tp = t[sta:sto+1]

    @property
    def is_method(self):
        return fargs in [type(p) for p in self.pstack]

    def show_base(self, kw=False, ns=False, tp=True):
        lbase = self.lbase
        if not kw:
            lbase = lbase.replace(self.kw, "", 1)
        if not ns and self.ns:
            ns = "::".join(self.ns) + "::"
            lbase = lbase.replace(ns, "", 1)
        if not tp:
            lbase = lbase.replace(self.tp, "", 1)
        s = [lbase]
        if self.lunsigned:
            s.insert(0, "unsigned")
        if self.lconst:
            s.insert(0, "const")
        return " ".join(s).strip()

    def show_ptr(self, name):
        s = name
        stripok = False
        for p in reversed(self.pstack):
            if p.is_ptr:
                s = "({}{})".format(p, s)
                stripok = True
            else:
                s = "{}{}".format(s, str(p))
                stripok = False
        if stripok:
            s = s[1:-1]
        return s

    def show(self, name="", kw=True, ns=True):
        extra = " : %d" % self.lbfw if self.lbfw else ""
        s = ("%s %s" % (self.show_base(kw, ns), self.show_ptr(name))).strip()
        return s + extra

    def tp_args(self):
        if self.tp:
            R = []
            for r in tpl.parseString(self.tp).asList()[0]:
                if isinstance(r,list):
                    R[-1] = R[-1]+flatten(r,'<%s>','')
                else:
                    el = strucdecl|intp|tpl_ignored|pp.Empty()
                    R += pp.DelimitedList(el).parse_string(r).as_list()
            return R
        return None

    def __eq__(self, other):
        et = self.show_base(ns=True)
        ot = other.show_base(ns=True)
        return et==ot


# ------------------------------------------------------------------------------


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


class arr(object):
    """
    Object that represents an array indicator.

    Attributes:
        a (int): dimension of the array
    """
    def __init__(self, a):
        self.is_ptr = False
        self.a = a

    def __str__(self):
        return "[%s]" % self.a


class fargs(object):
    """
    Object that represents the arguments list of a function prototype.

    Attributes:
        f (str): the arguments part of a function prototype
        args (list): the list of arguments
    """
    def __init__(self, f):
        self.is_ptr = False
        self.f = f

    @property
    def args(self):
        f = nested_par.parseString(self.f)
        A = []
        for x in f.asList()[0]:
            if not isinstance(x, list):
                A.extend(x.split(","))
            else:
                r = A.pop()
                r += flatten(x)
                A.append(r)
        return list(filter(None, A))

    def __str__(self):
        if hasattr(self, "cvr"):
            return "%s %s" % (self.f, self.cvr)
        return self.f

# one tricky function ;)

def pstack(plist, cls=c_type):
    """returns the 'stack' of pointers-to array-N-of pointer-to
    function() returning pointer to function() returning ..."""
    cxx = cls == cxx_type
    S = []
    cvr = ""
    if plist:
        if not isinstance(plist[0], list):
            # we are declaring either a pointer or array,
            # or an array of pointers to previously stacked objs
            p0 = plist[0]
            p, *A = pointer.parseString(p0)
            if p:
                S.append(ptr(*p))
            for a in reversed(A):
                S.append(arr(a))
            if not (p or A):
                if cxx:
                    r, *A = pointerxx.parseString(p0)
                    if r:
                        S.append(ptr(r[0], ""))
                    for a in reversed(A):
                        S.append(arr(a))
                    plist.pop(0)
                else:
                    S.append(fargs(flatten(plist)))
                    plist = []
            else:
                plist.pop(0)
        if len(plist) == 1 and len(plist[0]) == 0:
            S.append(fargs("()"))
            return S
    if len(plist) > 1:
        r = plist.pop()
        if not isinstance(r, list):
            try:
                for a in reversed(arraylist.parseString(r)):
                    S.append(arr(a))
            except pp.ParseException:
                if cxx:
                    cvr = cvref.parseString(r)[0]
        else:
            S.append(fargs(flatten(r)))
    if plist:
        if len(plist) == 1 and not cvr:
            plist = plist[0]
        S.extend(pstack(plist))
    if cvr:
        if len(S) > 0:
            S[-1].cvr = cvr
        else:
            print("cvr %s but S is empty!" % cvr)
    return S


def flatten(args,sep='(%s)',pad=" "):
    s = []
    for x in args:
        if not isinstance(x, list):
            s.append(x)
        else:
            s.append(flatten(x,sep,pad))
    return sep % (pad.join(s))


def indent(txt, l=4):
    L = []
    for x in txt.split("\n"):
        if x:
            x = l + x
        L.append(x)
    return "\n".join(L)
