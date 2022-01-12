Overview
========

Ccrawl is composed of several python modules and sub-packages:

- Module :mod:`main` defines all commands of the *ccrawl* command line tool. All commands
  are handled by the python *click* package which deals with options and arguments.

- Module :mod:`core` defines all internal classes used to represent collected objects,
  ie. typedefs, structs, unions, C++ classes, functions' prototypes, macros, etc.

- Module :mod:`parser` implements ccrawl's interface to the clang compiler by relying
  on the libclang python package. This interface allows to collect C/C++ definitions
  from input (header) files inside a database.

- Module :mod:`db` defines ccrawl's interface with the underlying databases, allowing to
  query for various properties of stored C/C++ definitions and to output the full definition
  of a chosen structure (all needed types recusively) or to instanciate an "external"
  object associated with the chosen definition (for example a ctypes instance, an amoco struct
  or a ghidra data type instance.) Sub-packages :ref:`formatters` deals with translating
  the queried definitions into a specific language (raw, C/C++, amoco, ctypes, etc) and
  sub-package :ref:`ext` deals with instanciating the queried definitions into specific
  python tools (amoco, ctypes, ghidra, etc.)

- Module :mod:`conf` provides the global configuration based on the traitlets package.

- Module :mod:`utils` implements the pyparsing utilities for
  decomposing a C/C++ type into a ccrawl object.
