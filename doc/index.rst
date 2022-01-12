.. ccrawl documentation master file

======
ccrawl
======
---------------------------------------
Search Engine for C/C++ data structures
---------------------------------------


ccrawl allows to search features related to C/C++ data structures extracted from
known sources in order to identify data structures within disassembled/decompiled
code. Using libclang, It collects everthing related to the definitions of
structs, unions, classes, templates, enums, typedefs, prototypes and macros found
in a set of source files and helps identifying the usage of these definitions by
querying the resulting database.

Motivation
==========

In the context of binary code analysis, tools like IDAPro_ and Ghidra_ provide an initial
representation of the code in assembly language and usually enhance this simple representation
with features extracted from the analysis of the control flow graph and the
analysis of how the data manipulated by instructions is structured.
These various features ideally provide a kind of "decompiled" representation of the program.

Plugins like HexRays_ perform an analysis of the control flow that leads to a decompiled
representation much closer to an equivalent C source code than the initial assembly instruction
listing. However, informations related to the nature and structure of manipulated data
are still mostly unidentified. Althrough some dedicated tools like TILIB or FLIRT_
or plugins to import this kind of information from windows PDB_ files exist,
this time consuming identification is still largely performed manually by the user.
This is particularly true in the case of embedded systems' firmware analysis.

ccrawl aims to provide a kind of search engine related to data structures ideally automating
the identification of data types as well as constants/macros identifiers. Basically the idea
is to allow queries like "find known structures that have a pointer to char at offset 8 and an
unsigned integer at offset 56 with total size of 96 bytes ?"  or "find every macro that define
value 0x1234 ?" or even "find the mask of values from enum X that correspond to 0xabcd ?"

Finally, once collected in its database(s), ccrawl allows to output queried structures in
various dedicated formats: C of course, but also ctypes_, VTypes (used by Volatility_),
or amoco_. The subset of all types required to fully define a given structure can also
be shown as well.

.. ----------------------------------------------------------------------------  
.. _user-docs:

.. toctree::
   :maxdepth: 1
   :caption: User Manual

   usage
   installation
   examples
   configuration
   advanced

.. ----------------------------------------------------------------------------  
.. _devel-docs:

.. toctree::
   :maxdepth: 2
   :caption: Python API

   overview
   core
   parser
   db
   formatters
   ext
   utils
   config
   main


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`



.. _IDAPro: https://www.hex-rays.com/products/ida/index.shtml
.. _Ghidra: https://ghidra-sre.org/
.. _HexRays: https://www.hex-rays.com/products/decompiler/index.shtml
.. _FLIRT: https://www.hex-rays.com/products/ida/tech/flirt/index.shtml
.. _PDB: https://github.com/Microsoft/microsoft-pdb
.. _ctypes: https://docs.python.org/3.7/library/ctypes.html
.. _Volatility: https://volatility-labs.blogspot.com/2014/01/the-art-of-memory-forensics.html
.. _kaitai: https://kaitai.io
.. _protobuf: https://developers.google.com/protocol-buffers/
.. _amoco: https://github.com/bdcht/amoco
