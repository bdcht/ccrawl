Usage
=====

We now provide a description of the ccrawl command-line tool which defines several sub-commands.
Of course, the ccrawl package can be used as well as a traditional package within Python scripts.

ccrawl's initial command consist in building a local database from C/C++ (header) files.
The libclang_ library is used to extract the following features ::

 - definitions of macros (#define)
 - definitions of simple types (typedef)
 - definitions of structured types (struct, union, enum, class & template)
 - definitions of function types (prototypes)

Since files are only parsed and not compiled by libclang, the set of included files can be
imcomplete and syntax errors only lead to ignored definitions. Of course, many queries do
require ultimately that all subtypes of a structure have been collected but this is not enforced
by ccrawl at parsing time. ccrawl will also try to extract comments associated to these features
when possible.

The local database is a TinyDB JSON Storage file. For performance and scaling reasons, ccrawl
supports also the use of a remote MongoDB database allowing massive indexing of
the samples built locally.

Commands
--------

These global options which apply to all commands are::

    $ ccrawl [-v, --verbose]                display more infos
             [-q, --quiet]                  don't display anything
             [-c, --config <file>]          path to configuration file
             [-l, --local <file>]           path to local database file
             [-b, --db <url>]               url for the remote database
             [-g, --tag <name>]             filter queries with given tag
             [--help]                       show this message
             [<command> [options] [args]]

All default parameters are possibly overwritten by a configuration file (which defaults to
*$HOME/.ccrawlrc* unless provided with the -c option.) The format of the configuration file is
based on the traitlets_ python package.
Parameters allow to set the default python interpreter, the mandatory pathname of the
libclang_ library required by the libclang python wrapper, the default local database path
or remote database url.

Documents of the local database are stored with the following format::

    {'cls': '<class>',
     'id' : '<identifier>',
     'src': '<path>',
     'tag': '<name>',
     'val': <object>}

For example, structure ``struct _mystruct`` in file *"samples/header.h"* is stored as::

     {'cls': 'cStruct',
        'id': 'struct _mystruct',
        'src': 'samples/header.h',
        'tag': '1549141214.805588',
        'val': [['myinteger', 'I', 'comment for field I'],
                ['int [12]', 'tab', 'modern comment for tab'],
                ['unsigned char [16]', 'p', None],
                ['short *', 's', None],
                ['struct _mystruct *', 'next', None],
                ['foo', 'func', None],
                ['struct _bar [2]', 'bar', None]
               ]}

(Notice that if no ``--tag`` global option is provided, the default tag name is constructed from
the current collect time.)

Collect
+++++++

The ``collect`` command locally extracts definitions from the provided sources <src>::

    $ ccrawl [global options] collect [options] <src>

      options: [-a, --all]        by default, only header files with '*.h' extension are
                                  considered, this option forces extraction from all provided 
                                  files.
               [-t, --types]      extraction is limited to types (typedefs, struct, union, enum)
               [-f, --functions]  extraction is limited to function prototypes
               [-m, --macros]     extraction is limited to macros

               [-s, --strict]     collect in "strict" mode: in this mode, all errors reported by
                                  libclang are blocking. It is thus mandatory to provide the
                                  complete set of input files and precise clang options such that
                                  clang is able to compile successfully the provided <src> files.
               [--clang "<opts>"] pass <opts> string directly to clang as options

               <src> ...          directory name(s) or file name(s) of C source(s) from which
                                  selected definitions shall be extracted and collected in the
                                  local database.


For example::

    $ cd tests/
    $ ccrawl -b None -l test.db collect samples/
    [  9%] samples/cxxabi.h                                            [ 13]
    [ 18%] samples/derived.hpp                                         [  4]
    [ 27%] samples/stru.h                                              [  0]
    [ 36%] samples/c_linkage.hpp                                       [  1]
    [ 45%] samples/00_empty.h                                          [  0]
    [ 54%] samples/templates.hpp                                       [352]
    [ 63%] samples/wonza.hpp                                           2326]
    [ 81%] samples/header.h                                            [ 25]
    [ 90%] samples/fwd_decl.hpp                                        [  2]
    [100%] samples/xxx/yyy/somewhere.h                                 [ 10]
    ------------------------------------------------------------------------
    saving database...                                                 2393]


Search
++++++

The ``search`` command performs a regular expression search within database 'id' and 'val' keys::

    $ ccrawl [global options] search <rex>

               <rex>              python (re) regular expression matched against local database
                                  documents keys 'id' and 'val'. Documents are filtered with
                                  'tag' as well if the --tag global options is used.

For example::

    $ ccrawl -b None -l test.db search "_my"
    found cStruct identifer "struct ?_7e12ea0f" with matching value
    found cTypedef identifer "mystruct" with matching value
    found cTypedef identifer "myunion" with matching value
    found cUnion identifer "union _myunion"
    found cStruct identifer "struct _mystruct" with matching value



Select
++++++

The ``select`` command performs advanced queries within the local database::

    $ ccrawl [global options] select [-a, --ands <str>]
                                     [-o, --ors  <str>]
                                     [<find_command> [options] [args]]

               [-a, --ands <str>] filters <str> of the form "key=value" added to current query
                                  with operator AND:
                                  Equivalent to "Q &= where(key).search(value)".
               [-o, --ors <str>]  same form, but added to current query with operator OR:
                                  Equivalent to "Q |= where(key).search(value)".

               <find_command>:

               prototype "<pos>:<type>" ...
                         Find prototypes (cls=cFunc) for which constraints of the form 
                         "<pos>:<type>" matches. Such constraint indicates that
                         argument located at <pos> index has C type <type>
                         (position index 0 designates the return value of the function).

               constant [-m, --mask] <value>
                         Find which macro definition or enum field name matches constant <value>.
                         Option --mask allows to look for the set of macros or enum symbols
                         that equals <value> when OR-ed.

               struct [-n, --name] "<offset>:<type>" ...
                         Find structures (cls=cStruct) satisfying constraints of the form:
                         "<offset>:<type>" where offset indicates a byte offset value (or '*')
                         and type is a C type name, symbol '?', '*' or a byte size value:
                         If <type> is "?", match any type at given offset,
                         If <type> is "*", match any pointer type at given offset,
                         If <type> is "+<val>", match if sizeof(type)==val at given offset.
                         If "*:+<val>", match struct only if sizeof(struct)==val.


For example::

    $ ccrawl -b None -l test.db select constant -s "MY" 0x10
    MYCONST
    $ ccrawl -b None -l test.db select struct -n "*:+104"
    [####################################]  100%
    struct _mystruct



Show
++++

The ``show`` command allows to recursively output a given identifier in various formats::

    $ ccrawl [global options] show [options] <identifier>

      options: [-r, --recursive]     recursively include all required definitions in the output
                                     such that type <identifier> is fully defined.
               [-f, --format <fmt>]  use output format <fmt>. Defaults to C, other formats are
                                     "ctypes", "amoco".

For example::

    $ ccrawl -b None -l test.db show -r 'struct _mystruct'
    typedef unsigned char xxx;
    typedef xxx myinteger;
    struct _mystruct;
    typedef int (*foo)(int, char, unsigned int, void *);
    enum X {
      X_0 = 0,
      X_1 = 1,
      X_2 = 2,
      X_3 = 3
    };
    
    struct _bar {
      enum X x;
    };
    
    struct _mystruct {
      myinteger I;
      int tab[12];
      unsigned char p[16];
      short *s;
      struct _mystruct *next;
      foo func;
      struct _bar bar[2];
    };




Info
++++

The ``info`` command provides meta-data information about a given identifier. For structures
the offsets and sizes of every field is displayed if all subtypes are defined::

    $ ccrawl [global options] info <identifier>


For example::

    $ ccrawl -b None -l test.db info 'struct _mystruct'
    identifier: struct _mystruct
    class     : cStruct
    source    : samples/header.h
    tag       : 1576426279.643788
    size      : 104
    offsets   : [(0, 1), (4, 48), (52, 16), (72, 8), (80, 8), (88, 8), (96, 8)]






.. _libclang: https://clang.llvm.org/doxygen/group__CINDEX.html
.. _traitlets: https://traitlets.readthedocs.io/en/stable/
