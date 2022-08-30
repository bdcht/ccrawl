.. _ext:

The ccrawl.ext package
======================

Modules of this package implements the *build* function that allows
to create an instance of an "external" object from a given type definition.
The package currently supports building :mod:`ctypes`, and :mod:`amoco` objects and
also allows to export chosen types to a running :mod:`ghidra` DataTypeManager.

.. automodule:: ext.ctypes_
   :members:

.. automodule:: ext.amoco
   :members:

.. automodule:: ext.ghidra
   :members:
