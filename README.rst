======
Ccrawl
======

.. image:: http://readthedocs.org/projects/ccrawl/badge/?version=latest
    :target: http://ccrawl.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/lgtm/grade/python/g/bdcht/ccrawl.svg?logo=lgtm&logoWidth=18
    :target: https://lgtm.com/projects/g/bdcht/ccrawl/context:python
    :alt: Code Quality

+-----------+--------------------------------------------------+
| Status:   | Under Development                                |
+-----------+--------------------------------------------------+
| Location: | https://github.com/bdcht/ccrawl                  |
+-----------+--------------------------------------------------+
| Version:  | 1.x                                              |
+-----------+--------------------------------------------------+
|  Doc:     | http://ccrawl.readthedocs.io/en/latest/index.html|
+-----------+--------------------------------------------------+

Description
===========

Ccrawl uses clang_ to build a database related to various C/C++ data structures
(struct, union, class, enum, typedef, prototypes and macros) which allows to identify
data types and constants/macros by querying this database for specific properties, including
properties related to the struct/class memory layout.

Basically it allows for example to

- **"find all structures that have a pointer to char at offset 8 and an unsigned integer at offset 56 ?**
- **"find types with a total size of 96 bytes ?"**  or
- **"find every macro that define value 0x1234 ?"** or
- **"find the mask of values from enum X that correspond to 0xabcd ?"**
- **"find all functions that return 'size_t' and have 'struct X' as first argument ?"**

Ccrawl then allows to output found structures in many formats: C/C++ of course,
but also ctypes_, or amoco_. The ctypes_ output of a C++ class corresponds to
an instance (object) layout in memory, including all virtual table pointers (or VTT)
that result from possibly multiple parent (possibly virtual) classes.

Finally, Ccrawl allows to compute various statistics about a library API, and allows to
compute the dependency graph of all collected types.

User documentation and API can be found at
`http://ccrawl.readthedocs.io/en/latest/index.html`

Examples
========

Consider the following C struct from file *samples/simple.h* ::

  struct S {
    char c;
    int  n;
    union {
      unsigned char x[2];
      unsigned short s;
    } u;
    char (*PtrCharArrayOf3[2])[3];
    void (*pfunc)(int, int);
  };

First, collect the structure definition in a local database::

  $ ccrawl -b None -l test.db -g 'test0' collect samples/simple.h
  [100%] simple.h                                                [  2]
  --------------------------------------------------------------------
  saving database...                                            [   2]

Then, its possible to translate the full structure in ctypes_ ::

  $ ccrawl -b None -l test.db show -r -f ctypes 'struct S'
  struct_S = type('struct_S',(Structure,),{})
  union_b0eccf67 = type('union_b0eccf67',(Union,),{})
  union_b0eccf67._fields_ = [("x", c_ubyte*2),
                             ("s", c_ushort)]

  struct_S._anonymous_ = ("u",)
  struct_S._fields_ = [("c", c_byte),
                       ("n", c_int),
                       ("u", union_b0eccf67),
                       ("PtrCharArrayOf3", POINTER(c_byte*3)*2),
                       ("pfunc", POINTER(CFUNCTYPE(None, c_int, c_int)))]

Or simply to compute the fields offsets ::

  $ ccrawl -b None -l test.db info 'struct S'
  identifier: struct S
  class     : cStruct
  source    : simple.h
  tag       : test0
  size      : 40
  offsets   : [(0, 1), (4, 4), (8, 2), (16, 16), (32, 8)]

Now let's deal with a more tricky C++ example::

  $ ccrawl -b None -l test.db -g 'c++' collect -a samples/shahar.cpp
  [100%] shahar.cpp                                              [ 18]
  --------------------------------------------------------------------
  saving database...                                            [  18]

We can show a *full* (recursive) definition of a class::

  $ ccrawl -b None -l test.db show -r 'class Child'
  class Grandparent {
    public:
      virtual void grandparent_foo();
      int grandparent_data;
  };
  
  class Parent1 : virtual public Grandparent {
    public:
      virtual void parent1_foo();
      int parent1_data;
  };
  class Parent2 : virtual public Grandparent {
    public:
      virtual void parent2_foo();
      int parent2_data;
  };

  class Child : public Parent1, public Parent2 {
    public:
      virtual void child_foo();
      int child_data;
  };

And its ctypes_ memory layout::

  $ ccrawl -b None -l test.db show -f ctypes 'class Child'
  class_Child = type('class_Child',(Structure,),{})
  
  class_Child._fields_ = [("__vptr$Parent1", c_void_p),
                          ("parent1_data", c_int),
                          ("__vptr$Parent2", c_void_p),
                          ("parent2_data", c_int),
                          ("child_data", c_int),
                          ("__vptr$Grandparent", c_void_p),
                          ("grandparent_data", c_int)]

See the documentation for more examples.

Todo
====

- add support for C++ template formatters
- add web frontend
- plugin for Ghidra
- plugin for IDA Pro
- add support for parsing functions bodies (number/types of local vars, blocks?)

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

.. _clang: https://pypi.org/project/clang/
.. _ctypes: https://docs.python.org/3.7/library/ctypes.html
.. _amoco: https://github.com/bdcht/amoco
.. _v1.0: https://github.com/bdcht/ccrawl/releases/tag/v1.0

