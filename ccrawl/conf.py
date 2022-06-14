import os
import clang.cindex

from traitlets.config import Configurable
from traitlets.config import PyFileConfigLoader
from traitlets import Unicode, Bool, observe

__version__ = "1.7.0"

# default clang library file: NOT REQUIRED for >libclang-12
# if os.name == 'posix':
#    clang_library_file = '/usr/lib/llvm-10/lib/libclang-12.so.1'
# else:
#    clang_library_file = 'libclang-12.dll'

# ccrawl globals:
# ------------------------------------------------------------------------------

config = None

VERBOSE = False
DEBUG = False
QUIET = False
BANNER = (
    r"""
                             _ 
  ___ ___ _ __ __ ___      _| |
 / __/ __| '__/ _` \ \ /\ / / |
| (_| (__| | | (_| |\ V  V /| |
 \___\___|_|  \__,_| \_/\_/ |_| v%s
"""
    % __version__
)

# ccrawl configuration:
# ------------------------------------------------------------------------------


class Terminal(Configurable):
    "configurable parameters related to ui/output"
    debug = Bool(DEBUG, config=True)  # don't show debug output
    verbose = Bool(VERBOSE, config=True)  # don't show verbose output
    quiet = Bool(QUIET, config=True)  # don't show no output
    console = Unicode(
        "python", config=True
    )  # use python interpreter is interactive mode
    banner = Unicode(BANNER)  # show above banner
    timer = Bool(False, config=True)  # don't time file parsing

    @observe("debug")
    def _debug_changed(self, change):
        global DEBUG
        DEBUG = change["new"]

    @observe("verbose")
    def _verbose_changed(self, change):
        global VERBOSE
        VERBOSE = change["new"]

    @observe("quiet")
    def _quiet_changed(self, change):
        global QUIET
        QUIET = change["new"]


class Database(Configurable):
    "configurable parameters related to the database"
    local = Unicode(
        "/tmp/ccrawl.db", config=True
    )  # local tiny database name is ccrawl.db
    url = Unicode("mongodb://localhost:27017", config=True)  # use mongodb server
    user = Unicode("", config=True)  # don't define a mongodb user
    verify = Bool(True, config=True)  # don't authenticate mongodb user


class Collect(Configurable):
    "configurable parameters related to the collect command"
    strict = Bool(False, config=True)  # don't block on missing headers/types
    cxx = Bool(True, config=True)  # try detecting c++ inputs
    allc = Bool(False, config=True)  # parse everything including function bodies
    tmp = Unicode()  # don't change temp directory
    lib = Unicode("", config=True)  # allow to choose clang_library_file

    @observe("lib")
    def _lib_changed(self, change):
        clang.cindex.Config.library_file = change["new"]


class Formats(Configurable):
    "configurable parameters related to formatters"
    default = Unicode("C", config=True)  # show results formatted as C code
    callcon = Unicode("cdecl", config=True)  # assume cdecl calling convention


class Ghidra(Configurable):
    "configurable parameters related to ghidra"
    manager = Unicode("program", config=True)  # use ghidra_bridge on currentProgram
    category = Unicode("ccrawl", config=True)  # import types into ccrawl category


class Config(object):
    def __init__(self, f=None):
        if f is None:
            f = ".ccrawlrc"
        self.f = f
        cl = PyFileConfigLoader(filename=f, path=(".", os.getenv("HOME")))
        try:
            c = cl.load_config()
        except Exception:
            c = None
        self.Terminal = Terminal(config=c)
        self.Database = Database(config=c)
        self.Collect = Collect(config=c)
        self.Formats = Formats(config=c)
        self.Ghidra = Ghidra(config=c)
        self.src = c
        if self.Collect.lib:
            clang.cindex.Config.library_file = self.Collect.lib

    def __str__(self):
        s = []
        for c in filter(
            lambda x: isinstance(getattr(self, x), Configurable), dir(self)
        ):
            pfx = "c.%s" % c
            c = getattr(self, c)
            for t in c.trait_names():
                if t in ("config", "parent"):
                    continue
                s.append("{}.{}: {}".format(pfx, t, getattr(c, t)))
        return u"\n".join(s)
