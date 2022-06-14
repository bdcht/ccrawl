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
# define structured types (struct,union,enum):
symbol = pp.Regex(r"[?]?[A-Za-z_:<>][A-Za-z0-9_:<>$]*")
structured = pp.oneOf("struct union enum class")
strucdecl = pp.Optional(prefix) + pp.Optional(structured) + symbol
# define objecttype:
objecttype = pp.Or([rawtypes, strucdecl])
# define arrays:
intp = pp.Regex(r"[1-9][0-9]*")
intp.setParseAction(lambda r: int(r[0]))
bitfield = pp.Optional(prefix) + symbol + pp.Suppress("#") + intp
arraydecl = pp.Suppress("[") + intp + pp.Suppress("]")
arrazdecl = pp.Suppress("[") + pp.Or((intp, symbol)) + pp.Suppress("]")
pointer = pp.Optional(pstars, default="") + pp.Optional(arraydecl, default=0)
pointerxx = pp.Optional(ampers, default="") + pp.Optional(arrazdecl, default=0)
cvref = pp.Or((cvqual, ampers))
#
# definitions for nested_c ----------------------------------------------------
# nested_c captures "pointer to function/array" part of the declaration.
# this is the tricky part due to the nesting mix of pointer grouping vs.
# function prototyping using both parenthesis as delimiters!
nested_par = pp.nestedExpr(content=pp.Regex(r"[^()]+"), ignoreExpr=None)
nested_c = pp.OneOrMore(nested_par)


class c_type(object):
    """The c_type object parses a C type string and decomposes it into
    several parts
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
            else:
                lbase.append(w)
        self.lbase = " ".join(lbase)
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

    def show_base(self, kw=False, ns=False):
        s = [self.lbase]
        if self.lunsigned:
            s.insert(0, "unsigned")
        if self.lconst:
            s.insert(0, "const")
        return " ".join(s)

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

    def show(self, name=""):
        extra = " : %d" % self.lbfw if self.lbfw else ""
        s = ("%s %s" % (self.show_base(), self.show_ptr(name))).strip()
        return s + extra


# C++ type declaration parser:
# ------------------------------------------------------------------------------
# cxx_type extends c_type with extracting the namespace parts of the fully
# qualified name of the C++ type.
class cxx_type(c_type):
    def __init__(self, decl):
        super().__init__(decl)
        # get namespaces:
        self.kw = ""
        self.ns = ""
        k = self.lbase.find(" ")
        if k > 0:
            self.kw = self.lbase[:k]
        x = self.lbase.rfind("::")
        if x > 0:
            self.ns = self.lbase[k + 1 : x + 2]

    @property
    def is_method(self):
        return fargs in [type(p) for p in self.pstack]

    def show_base(self, kw=False, ns=False):
        lbase = self.lbase
        if not kw:
            lbase = lbase.replace(self.kw, "", 1)
        if not ns:
            lbase = lbase.replace(self.ns, "", 1)
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


# ------------------------------------------------------------------------------


class ptr(object):
    def __init__(self, p, c):
        self.is_ptr = True
        self.p, self.const = p, c

    def __str__(self):
        sfx = "%s " % self.const if self.const else ""
        return "{}{}".format(self.p, sfx)


class arr(object):
    def __init__(self, a):
        self.is_ptr = False
        self.a = a

    def __str__(self):
        return "[%s]" % self.a


class fargs(object):
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
            p, a = pointer.parseString(p0)
            if p:
                S.append(ptr(*p))
            if a:
                S.append(arr(a))
            if not (p or a):
                if cxx:
                    r, a = pointerxx.parseString(p0)
                    if r:
                        S.append(ptr(r[0], ""))
                    if a:
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
                r = arraydecl.parseString(r)[0]
                S.append(arr(r))
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


def flatten(args):
    s = []
    for x in args:
        if not isinstance(x, list):
            s.append(x)
        else:
            s.append(flatten(x))
    return "(%s)" % (" ".join(s))


def indent(txt, l=4):
    L = []
    for x in txt.split("\n"):
        if x:
            x = l + x
        L.append(x)
    return "\n".join(L)
