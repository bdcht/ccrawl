======
Ccrawl
======

.. image:: http://readthedocs.org/projects/ccrawl/badge/?version=latest
    :target: http://ccrawl.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

+-----------+--------------------------------------------------+
| Status:   | Under Development                                |
+-----------+--------------------------------------------------+
| Location: | https://github.com/bdcht/ccrawl                  |
+-----------+--------------------------------------------------+
| Version:  | 1.0                                              |
+-----------+--------------------------------------------------+
|  Doc:     | http://ccrawl.readthedocs.io/en/latest/index.html|
+-----------+--------------------------------------------------+

Description
===========

Ccrawl is a clang-based tool that builds a database related to various C/C++ data structures
(struct, union, class, enum, typedef, prototypes and macros). It then allows to identify
data types and constants/macros by querying this database for specific properties, including
"memory-layout" properties. Basically it allows for example
to

- **"find all structures that have a pointer to char at offset 8 and an
unsigned integer at offset 56 with total size of 96 bytes ?"**  or
- **"find every macro that define value 0x1234 ?"** or
- **"find the mask of values from enum X that correspond to 0xabcd ?"**
- **"find all functions that return 'size_t' and have 'struct X' has first argument ?"**

Ccrawl then allows to output found structures in many formats: C/C++ of course,
but also ctypes_, or amoco_. The ctypes_ output of a C++ class corresponds to
an instance (object) layout in memory, including all virtual table pointers (or VTT)
that result from possibly multiple parent (possibly virtual) classes.

Finally, Ccrawl allows to compute various statistics about a library API, and allows to
draw the dependency graph of all types.

User documentation and API can be found at
`http://ccrawl.readthedocs.io/en/latest/index.html`

Todo
====

- plugin for IDA Pro
- plugin for Ghidra
- collect infos about functions internals (number/types of local vars, blocks?)
- add support for C++ template formatters

Changelog
=========

- `v1.0`_

  * support for mongodb database backend
  * support for local tinydb databases
  * c_type and cxx_type parsers for C/C++ types
  * support anonymous types in C structs/unions
  * support C++ multiple inheritance, including virtual parents
  * basic support for C++ class & function templates
  * support bitfield structures
  * support user-defined alignment policies

.. _ctypes: https://docs.python.org/3.7/library/ctypes.html
.. _amoco: https://github.com/bdcht/amoco
.. _v1.0: https://github.com/bdcht/ccrawl/releases/tag/v1.0

