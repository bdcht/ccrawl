.. crawl documentation master file

=====
Crawl
=====
-----------------------------------
REquests in the world of structures
-----------------------------------


Crawl allows to extract, collect and search features related to C data structures (and macros).

Motivation
==========

In the context of binary code analysis, tools like IDA Pro [1] provide an initial
representation of the code in assembly language and usually enhance this simple representation
with features extracted from the analysis of the control flow graph (executable code) and the
analysis of how the data manipulated by instructions is structured.
These various features ideally provide a kind of "decompiled" representation of the program.

Plugins like "Hex-Rays" [2] perform an analysis of the control flow that leads to a decompiled
representation much closer to an equivalent C source code than the initial assembly instruction
listing or CFG. However, informations related to the nature and structure of manipulated data
are still mostly unidentified. Althrough some dedicated tools like FLIRT [3] or support for
importing this kind of information from windows PDB [4] files exist, this time consuming
identification is still largely performed manually by the user.
This is specially true in the case of embedded systems.

Crawl aims at providing a kind of search engine related to data structures ideally automating
the identification of data types as well as constants/macros identifiers. Basically the idea
is to allow queries like "find known structures that have a pointer to char at offset 8 and an
unsigned integer at offset 56 and total size of 96 bytes ?"  or "find every macro that define
value 0x1234 ?" or even "find the mask of values from enum X that correspond to 0xabcd ?"

Finally, once collected in its database(s), crawl allows to output queried structures in
various dedicated formats: C of course, but also ctypes [5], VTypes (used by Volatility [6]),
kaitaistruct [7], protobuf [8] or amoco [9]. The minimal subset of types required to fully
define a given structure can also be outputed as well.

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
   :maxdepth: 1
   :caption: API

   overview
   main
   code
   cfg
   arch
   system
   cas
   ui
   db
   config
   logger


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`



.. _[1]: https://www.hex-rays.com/products/ida/index.shtml
.. _[2]: https://www.hex-rays.com/products/decompiler/index.shtml
.. _[3]: https://www.hex-rays.com/products/ida/tech/flirt/index.shtml
.. _[4]: https://github.com/Microsoft/microsoft-pdb
.. _[5]: https://docs.python.org/3.7/library/ctypes.html
.. _[6]: https://volatility-labs.blogspot.com/2014/01/the-art-of-memory-forensics.html
.. _[7]: https://kaitai.io
.. _[8]: https://developers.google.com/protocol-buffers/
.. _[9]: https://github.com/bdcht/amoco
