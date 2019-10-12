import os
import clang.cindex

from traitlets.config import Configurable
from traitlets.config import PyFileConfigLoader
from traitlets import Integer, Unicode, Bool, observe

__version__ = "0.9.6"

# default clang library file:
if os.name == 'posix':
    clang_library_file = 'libclang-6.0.so'
else:
    clang_library_file = 'libclang-6.0.dll'

# ccrawl globals:
#------------------------------------------------------------------------------

config  = None

VERBOSE = False
DEBUG   = False
QUIET   = False
BANNER  = \
"""
                             _ 
  ___ ___ _ __ __ ___      _| |
 / __/ __| '__/ _` \ \ /\ / / |
| (_| (__| | | (_| |\ V  V /| |
 \___\___|_|  \__,_| \_/\_/ |_| v%s
"""%__version__

# ccrawl configuration:
#------------------------------------------------------------------------------

class Terminal(Configurable):
    "configurable parameters related to ui/output"
    debug = Bool(DEBUG,config=True)
    verbose = Bool(VERBOSE,config=True)
    quiet = Bool(False,config=True)
    console = Unicode('python',config=True)
    banner = Unicode(BANNER)
    timer = Bool(False,config=True)
    @observe('debug')
    def _debug_changed(self,change):
        global DEBUG
        DEBUG = change['new']
    @observe('verbose')
    def _verbose_changed(self,change):
        global VERBOSE
        VERBOSE = change['new']
    @observe('quiet')
    def _quiet_changed(self,change):
        global QUIET
        QUIET = change['new']

class Database(Configurable):
    "configurable parameters related to the database"
    local  = Unicode('ccrawl.db',config=True)
    url    = Unicode('',config=True)
    user   = Unicode('',config=True)
    verify = Bool(True,config=True)

class Collect(Configurable):
    "configurable parameters related to the collect command"
    strict = Bool(False,config=True)
    cxx = Bool(True,config=True)
    tmp = Unicode()
    lib = Unicode(clang_library_file,config=True)
    @observe('lib')
    def _lib_changed(self,change):
        clang.cindex.Config.library_file = change['new']

class Formats(Configurable):
    "configurable parameters related to formatters"
    default = Unicode('C',config=True)
    callcon = Unicode('cdecl',config=True)

class Config(object):

    def __init__(self,f=None):
        if f is None: f='.ccrawlrc'
        self.f = f
        cl = PyFileConfigLoader(filename=f,path=('.',os.getenv('HOME')))
        try:
            c = cl.load_config()
        except:
            c = None
        self.Terminal = Terminal(config=c)
        self.Database = Database(config=c)
        self.Collect  = Collect(config=c)
        self.Formats  = Formats(config=c)
        self.src = c

    def __str__(self):
        s = []
        for c in filter(lambda x: isinstance(getattr(self,x),Configurable),
                       dir(self)):
            pfx = "c.%s"%c
            c = getattr(self,c)
            for t in c.trait_names():
                if t in ('config','parent'): continue
                s.append('{}.{}: {}'.format(pfx,t,getattr(c,t)))
        return u'\n'.join(s)

